# backend/collectors/fs_watcher.py
"""
ARGUS Plan-A in-process file-system collector.

Uses watchdog to monitor user directories for file create/modify/move events
and writes real provenance data into the Layer 1 graph:

  PROCESS(fs_watcher) --WROTE--> FILE(<path>)

Thread-safety: a brand-new SQLAlchemy session is opened *per event* so the
watchdog observer thread never shares a session with the FastAPI worker threads.

Configuration (see config.py / .env):
  COLLECTOR_ENABLED=true           # default: false
  COLLECTOR_WATCHED_PATHS=...      # comma-separated directory paths
  COLLECTOR_HASH_MAX_BYTES=...     # max file size to SHA-256 hash (default 10 MB)

Quick manual test plan:
  1. Set COLLECTOR_ENABLED=true in backend/.env
  2. Start backend: cd backend && uvicorn main:app --reload
  3. Drop any file into one of the watched directories.
  4. Check logs for "🗂️  FS event" and "✅ Ingested" lines.
  5. GET /api/layer1/nodes  → new FILE and PROCESS nodes should appear.
  6. GET /api/layer1/edges  → a WROTE edge should appear.
"""

import hashlib
import os
import threading
from datetime import datetime, timezone

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from database.connection import SessionLocal
from database.schemas import EdgeCreate, NodeCreate
from layers.layer1_graph_engine.services import GraphService
from shared.enums import EdgeType, NodeType
from shared.logger import setup_logger

logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

_WATCHER_PROCESS_PATH = "ARGUS"
_WATCHER_PROCESS_NAME = "fs_watcher"
_OBSERVER_SHUTDOWN_TIMEOUT_SECONDS = 5


def _session_id_for(path: str) -> str:
    """
    Generate a session_id that groups events by (directory, minute-bucket).
    This keeps related events in the same 60-second window correlated while
    avoiding an ever-growing number of sessions.
    """
    directory = os.path.dirname(path)
    minute_bucket = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M")
    return f"fswatcher:{directory}:{minute_bucket}"


def _sha256(path: str, max_bytes: int) -> str | None:
    """Return hex SHA-256 of *path* if the file is ≤ max_bytes, else None."""
    try:
        size = os.path.getsize(path)
        if size > max_bytes:
            return None
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _get_or_create_watcher_process(db) -> int:
    """
    Upsert the synthetic 'fs_watcher' PROCESS node and return its id.
    This node represents the OS / ARGUS watcher itself as the writer.
    """
    node = GraphService.create_or_update_node(
        db,
        NodeCreate(
            type=NodeType.PROCESS,
            name=_WATCHER_PROCESS_NAME,
            path=_WATCHER_PROCESS_PATH,
        ),
    )
    return node.id


# ─────────────────────────────────────────────────────────────────────────────
# Watchdog event handler
# ─────────────────────────────────────────────────────────────────────────────


class _ArgusEventHandler(FileSystemEventHandler):
    """Handle file-system events and ingest them into the provenance graph."""

    def __init__(self, hash_max_bytes: int) -> None:
        super().__init__()
        self._hash_max_bytes = hash_max_bytes
        # A lock only guards the _get_or_create_watcher_process call so that
        # concurrent rapid events don't race to create duplicate PROCESS nodes.
        self._process_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public watchdog callbacks
    # ------------------------------------------------------------------

    def on_created(self, event):
        if event.is_directory:
            return
        self._ingest(event.src_path, "created")

    def on_modified(self, event):
        if event.is_directory:
            return
        self._ingest(event.src_path, "modified")

    def on_moved(self, event):
        if event.is_directory:
            return
        # Record the *destination* path as the new file location
        dest = getattr(event, "dest_path", event.src_path)
        self._ingest(dest, "moved")

    # ------------------------------------------------------------------
    # Core ingestion logic
    # ------------------------------------------------------------------

    def _ingest(self, path: str, event_type: str) -> None:
        """
        Write one FILE node + WROTE edge into the Layer 1 graph.
        Opens and closes its own DB session so this is safe to call
        from the watchdog observer thread.
        """
        if SessionLocal is None:
            # DB not yet initialised – skip silently (shouldn't happen in
            # normal operation because the observer starts after init_db).
            logger.warning("⚠️  FS event before DB ready – skipping %s", path)
            return

        logger.debug("🗂️  FS event [%s]: %s", event_type, path)

        db = SessionLocal()
        try:
            # 1. Hash the file (best-effort; skip if too large or locked)
            sha256 = _sha256(path, self._hash_max_bytes)

            # 2. Upsert FILE node
            file_node = GraphService.create_or_update_node(
                db,
                NodeCreate(
                    type=NodeType.FILE,
                    name=os.path.basename(path),
                    path=path,
                    hash_sha256=sha256,
                ),
            )

            # 3. Upsert the synthetic watcher PROCESS node (lock to avoid race)
            with self._process_lock:
                process_id = _get_or_create_watcher_process(db)

            # 4. Create WROTE edge: PROCESS → FILE
            session_id = _session_id_for(path)
            GraphService.create_edge(
                db,
                EdgeCreate(
                    source_id=process_id,
                    target_id=file_node.id,
                    edge_type=EdgeType.WROTE,
                    session_id=session_id,
                    edge_metadata={"collector": "fs_watcher", "event": event_type},
                ),
            )

            logger.info(
                "✅ Ingested [%s] %s (sha256=%s, session=%s)",
                event_type,
                path,
                sha256[:8] + "…" if sha256 else "None",
                session_id,
            )

        except Exception as exc:
            logger.error("❌ Failed to ingest FS event for %s: %s", path, exc)
            db.rollback()
        finally:
            db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Public collector class
# ─────────────────────────────────────────────────────────────────────────────


class FileSystemCollector:
    """
    Manages the watchdog Observer and event handler lifecycle.

    Usage (handled automatically by backend/main.py lifespan):
        collector = FileSystemCollector(watched_paths=[...], hash_max_bytes=...)
        collector.start()
        ...
        collector.stop()
    """

    def __init__(self, watched_paths: list[str], hash_max_bytes: int) -> None:
        self._watched_paths = [p.strip() for p in watched_paths if p.strip()]
        self._hash_max_bytes = hash_max_bytes
        self._observer: Observer | None = None

    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the watchdog observer in a background thread."""
        if not self._watched_paths:
            logger.warning("⚠️  FileSystemCollector: no watched paths configured – skipping.")
            return

        handler = _ArgusEventHandler(self._hash_max_bytes)
        self._observer = Observer()

        scheduled = []
        for path in self._watched_paths:
            if os.path.isdir(path):
                self._observer.schedule(handler, path, recursive=False)
                scheduled.append(path)
            else:
                logger.warning(
                    "⚠️  Watched path does not exist or is not a directory: %s", path
                )

        if not scheduled:
            logger.warning("⚠️  FileSystemCollector: none of the configured paths exist – not starting.")
            return

        self._observer.start()
        logger.info(
            "🔍 FileSystemCollector started. Watching %d path(s): %s",
            len(scheduled),
            scheduled,
        )

    def stop(self) -> None:
        """Stop the watchdog observer and wait for it to finish."""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=_OBSERVER_SHUTDOWN_TIMEOUT_SECONDS)
            except Exception as exc:
                logger.error("❌ Error stopping FileSystemCollector: %s", exc)
            finally:
                self._observer = None
            logger.info("🛑 FileSystemCollector stopped.")
