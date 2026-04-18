import os
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple

import psutil

from backend.shared.logger import setup_logger
from backend.shared.enums import NodeType, EdgeType
from backend.shared.audit import AuditLogger

from backend.database import connection
from backend.database.schemas import NodeCreate, EdgeCreate
from backend.layers.layer1_graph_engine.services import GraphService

logger = setup_logger(__name__)


def _session_id_for_process_event(pid: int) -> str:
    # Correlate by minute bucket (simple + stable)
    minute = datetime.utcnow().strftime("%Y%m%d-%H%M")
    return f"ps:{minute}:{pid}"


def _safe_proc_exe(p: psutil.Process) -> Optional[str]:
    try:
        return p.exe()
    except Exception:
        return None


def _safe_proc_name(p: psutil.Process) -> str:
    try:
        return p.name()
    except Exception:
        return f"pid_{p.pid}"


def _safe_ppid(p: psutil.Process) -> Optional[int]:
    try:
        return p.ppid()
    except Exception:
        return None


class ProcessSnapshotCollector:
    """
    Polling collector that snapshots processes every N seconds and:
    - Upserts PROCESS nodes
    - Emits SPAWNED edges for newly observed processes (ppid -> pid)
    - Writes audit logs (optional)

    NOTE: This is a pragmatic Plan-A bridge before ETW.
    """

    def __init__(
        self,
        enabled: bool = True,
        interval_seconds: int = 5,
        audit_enabled: bool = True,
    ):
        self.enabled = enabled
        self.interval_seconds = max(1, int(interval_seconds))
        self.audit_enabled = audit_enabled

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # pid -> (ppid, create_time)
        self._seen: Dict[int, Tuple[Optional[int], Optional[float]]] = {}

    def start(self):
        if not self.enabled:
            logger.info("🟡 ProcessSnapshotCollector disabled (enabled=false)")
            return

        if connection.SessionLocal is None:
            raise RuntimeError("DB not initialized: SessionLocal is None. Call init_db() before starting collector.")

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="ProcessSnapshotCollector", daemon=True)
        self._thread.start()
        logger.info(f"🚀 ProcessSnapshotCollector started (interval={self.interval_seconds}s)")

        # best-effort audit
        try:
            if self.audit_enabled:
                db = connection.SessionLocal()
                try:
                    AuditLogger.log(
                        db,
                        source="collector.process_snapshot",
                        action="started",
                        message=f"ProcessSnapshotCollector started interval={self.interval_seconds}s",
                    )
                finally:
                    db.close()
        except Exception:
            pass

    def stop(self):
        if not self._thread:
            return
        logger.info("🛑 Stopping ProcessSnapshotCollector...")
        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("✅ ProcessSnapshotCollector stopped")
        self._thread = None

        # best-effort audit
        try:
            if self.audit_enabled and connection.SessionLocal is not None:
                db = connection.SessionLocal()
                try:
                    AuditLogger.log(
                        db,
                        source="collector.process_snapshot",
                        action="stopped",
                        message="ProcessSnapshotCollector stopped",
                    )
                finally:
                    db.close()
        except Exception:
            pass

    def _run(self):
        # Initial baseline snapshot (no spawn edges on first pass)
        self._snapshot(emit_spawns=False)

        while not self._stop_event.is_set():
            time.sleep(self.interval_seconds)
            self._snapshot(emit_spawns=True)

    def _snapshot(self, emit_spawns: bool):
        # Iterate processes
        for p in psutil.process_iter(attrs=[], ad_value=None):
            pid = p.pid

            # process create_time helps reduce false spawn edges on PID reuse
            try:
                ctime = p.create_time()
            except Exception:
                ctime = None

            if pid in self._seen and self._seen[pid][1] == ctime:
                continue  # already known instance

            ppid = _safe_ppid(p)
            name = _safe_proc_name(p)
            exe = _safe_proc_exe(p)

            db = connection.SessionLocal()
            try:
                # Upsert child node
                child = GraphService.create_or_update_node(
                    db,
                    NodeCreate(
                        type=NodeType.PROCESS,
                        name=name,
                        path=exe,
                        hash_sha256=None,
                        path_risk=0.0,
                    ),
                )

                # Upsert parent node (if we can see it)
                parent_id = None
                if ppid and ppid > 0:
                    try:
                        pp = psutil.Process(ppid)
                        parent = GraphService.create_or_update_node(
                            db,
                            NodeCreate(
                                type=NodeType.PROCESS,
                                name=_safe_proc_name(pp),
                                path=_safe_proc_exe(pp),
                                hash_sha256=None,
                                path_risk=0.0,
                            ),
                        )
                        parent_id = parent.id
                    except Exception:
                        parent_id = None

                # Emit SPAWNED edge only when asked and parent is known
                if emit_spawns and parent_id is not None:
                    sid = _session_id_for_process_event(pid)
                    GraphService.create_edge(
                        db,
                        EdgeCreate(
                            source_id=parent_id,
                            target_id=child.id,
                            edge_type=EdgeType.SPAWNED,
                            session_id=sid,
                            edge_metadata={
                                "collector": "psutil_snapshot",
                                "pid": pid,
                                "ppid": ppid,
                                "exe": exe,
                                "name": name,
                                "create_time": ctime,
                            },
                        ),
                    )

                    if self.audit_enabled:
                        AuditLogger.log(
                            db,
                            source="collector.process_snapshot",
                            action="process_spawned",
                            message=f"Spawned: {name} (pid={pid})",
                            entity_type="process",
                            entity_id=child.id,
                            session_id=sid,
                            path=exe,
                            payload={"pid": pid, "ppid": ppid, "name": name, "exe": exe, "create_time": ctime},
                        )

                # Track seen
                self._seen[pid] = (ppid, ctime)

            except Exception:
                logger.exception(f"❌ Process snapshot failed for pid={pid}")
                # No audit on failure to avoid recursion storms
            finally:
                db.close()