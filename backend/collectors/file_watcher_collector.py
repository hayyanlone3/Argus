import os
import hashlib
from datetime import datetime
from typing import List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileMovedEvent

from backend.shared.logger import setup_logger
from backend.shared.enums import NodeType, EdgeType
from backend.shared.audit import AuditLogger

from backend.database import connection
from backend.database.schemas import NodeCreate, EdgeCreate
from backend.layers.layer1_graph_engine.services import GraphService

logger = setup_logger(__name__)


def _safe_sha256(path: str, max_bytes: int) -> Optional[str]:
    """Hash file if it exists and is not too large. Returns None on failure."""
    try:
        if not os.path.isfile(path):
            return None
        size = os.path.getsize(path)
        if size > max_bytes:
            return None

        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _session_id_for_path(path: str) -> str:
    """Simple correlation key: minute bucket + directory."""
    minute = datetime.utcnow().strftime("%Y%m%d-%H%M")
    directory = os.path.dirname(path).lower().encode("utf-8", errors="ignore")
    d_hash = hashlib.sha1(directory).hexdigest()[:12]  # 12 chars
    return f"fsw:{minute}:{d_hash}"  # ~4+1+13+1+12 = under 100


class _Handler(FileSystemEventHandler):
    def __init__(
        self,
        process_node_id: int,
        hash_max_bytes: int,
        ignore_prefixes: List[str],
        audit_enabled: bool,
    ):
        self.process_node_id = process_node_id
        self.hash_max_bytes = hash_max_bytes
        self.ignore_prefixes = [p.lower() for p in ignore_prefixes]
        self.audit_enabled = audit_enabled

    def _ignore(self, path: str) -> bool:
        p = path.lower()
        return any(p.startswith(pref) for pref in self.ignore_prefixes)

    def _record_write(self, file_path: str):
        # Temporary debug signal (you can change to logger.debug later)
        logger.info(f"📄 FS event: {file_path}")

        if not file_path or self._ignore(file_path):
            return

        # Ignore directories
        if os.path.isdir(file_path):
            return

        # Create DB session at runtime (after init_db)
        db = connection.SessionLocal()
        try:
            sha = _safe_sha256(file_path, self.hash_max_bytes)
            session_id = _session_id_for_path(file_path)

            node = GraphService.create_or_update_node(
                db,
                NodeCreate(
                    type=NodeType.FILE,
                    name=os.path.basename(file_path),
                    path=file_path,
                    hash_sha256=sha,
                    path_risk=0.0,  # neutral for now
                ),
            )

            GraphService.create_edge(
                db,
                EdgeCreate(
                    source_id=self.process_node_id,
                    target_id=node.id,
                    edge_type=EdgeType.WROTE,
                    session_id=session_id,
                    edge_metadata={
                        "collector": "watchdog",
                        "event": "write",
                    },
                ),
            )

            if self.audit_enabled:
                AuditLogger.log(
                    db,
                    source="collector.file_watcher",
                    action="file_write",
                    level="INFO",
                    message=f"File modified: {file_path}",
                    entity_type="file",
                    entity_id=node.id,
                    session_id=session_id,
                    path=file_path,
                    hash_sha256=sha,
                    payload={"collector": "watchdog"},
                )

        except Exception as e:
            # Full stack trace in logs
            logger.exception(f"❌ File watcher failed for {file_path}")

            # Best-effort audit of failure (don’t let this raise)
            try:
                if self.audit_enabled:
                    AuditLogger.log(
                        db,
                        source="collector.file_watcher",
                        action="file_write_failed",
                        level="ERROR",
                        message=str(e),
                        path=file_path,
                        payload={"collector": "watchdog"},
                        commit=True,
                    )
            except Exception:
                pass

        finally:
            db.close()

    # watchdog callbacks
    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self._record_write(event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self._record_write(event.src_path)

    def on_moved(self, event: FileMovedEvent):
        if not event.is_directory:
            self._record_write(event.dest_path)


class FileWatcherCollector:
    """
    In-process collector:
    Watches user directories and writes FILE nodes + WROTE edges into Layer 1.
    Also writes audit logs to PostgreSQL (audit_logs table) if enabled.
    """

    def __init__(
        self,
        paths: List[str],
        enabled: bool = True,
        hash_max_mb: int = 10,
        ignore_prefixes: Optional[List[str]] = None,
        audit_enabled: bool = True,
    ):
        self.enabled = enabled
        self.paths = paths
        self.hash_max_bytes = int(hash_max_mb) * 1024 * 1024
        self.ignore_prefixes = ignore_prefixes or []
        self.audit_enabled = audit_enabled

        self._observer: Optional[Observer] = None
        self._process_node_id: Optional[int] = None

    def start(self):
        if not self.enabled:
            logger.info("🟡 FileWatcherCollector disabled (enabled=false)")
            return

        if connection.SessionLocal is None:
            raise RuntimeError("DB not initialized: SessionLocal is None. Call init_db() before starting collector.")

        # Create a synthetic process node representing this collector
        db = connection.SessionLocal()
        try:
            proc = GraphService.create_or_update_node(
                db,
                NodeCreate(
                    type=NodeType.PROCESS,
                    name="fs_watcher",
                    path="ARGUS",
                    hash_sha256=None,
                    path_risk=0.0,
                ),
            )
            self._process_node_id = proc.id

            if self.audit_enabled:
                AuditLogger.log(
                    db,
                    source="collector.file_watcher",
                    action="started",
                    message="FileWatcherCollector started",
                    entity_type="process",
                    entity_id=proc.id,
                    payload={"paths": self.paths, "hash_max_bytes": self.hash_max_bytes},
                )
        finally:
            db.close()

        handler = _Handler(
            process_node_id=self._process_node_id,
            hash_max_bytes=self.hash_max_bytes,
            ignore_prefixes=self.ignore_prefixes,
            audit_enabled=self.audit_enabled,
        )

        self._observer = Observer()
        watched = 0
        for p in self.paths:
            if p and os.path.isdir(p):
                self._observer.schedule(handler, p, recursive=True)
                watched += 1
                logger.info(f"👁️ Watching: {p}")
            else:
                logger.warning(f"⚠️ Skipping missing watch path: {p}")

        if watched == 0:
            logger.warning("⚠️ No valid watch paths. Collector will not start.")
            return

        self._observer.start()
        logger.info("🚀 FileWatcherCollector started")

    def stop(self):
        if self._observer:
            logger.info("🛑 Stopping FileWatcherCollector...")
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            finally:
                self._observer = None
            logger.info("✅ FileWatcherCollector stopped")

        # best-effort audit stop
        try:
            if self.audit_enabled and connection.SessionLocal is not None:
                db = connection.SessionLocal()
                try:
                    AuditLogger.log(
                        db,
                        source="collector.file_watcher",
                        action="stopped",
                        message="FileWatcherCollector stopped",
                    )
                finally:
                    db.close()
        except Exception:
            pass