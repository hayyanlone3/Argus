# backend/layers/layer1_graph_engine/ingestion.py
import threading
import time
from datetime import datetime
from backend.database import connection
from backend.layers.layer2_scoring.event_stream import GRAPH_QUEUE, TelemetryEvent
from backend.layers.layer1_graph_engine.services import GraphService
from backend.database.schemas import NodeCreate, EdgeCreate
from backend.shared.enums import NodeType, EdgeType
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)

class GraphIngestionWorker:
    """
    Consumes TelemetryEvents from GRAPH_QUEUE and populates the DB.
    """
    def __init__(self):
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
             return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="GraphIngestionWorker", daemon=True)
        self._thread.start()
        logger.info("🟢 GraphIngestionWorker started - Synchronizing Provenance Graph...")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        while not self._stop.is_set():
            try:
                evt = GRAPH_QUEUE.get(timeout=1.0)
                logger.info(f"💾 [INGESTION] Writing: {evt.kind}")
            except:
                continue

            try:
                db = connection.SessionLocal()
                try:
                    self._process_event(db, evt)
                finally:
                    db.close()
            except Exception:
                logger.exception("❌ Graph Ingestion failed")

    def _process_event(self, db, evt: TelemetryEvent):
        # 1. Ensure nodes exist
        source_node = None
        target_node = None
        md = {
            "collector": evt.source,
            "telemetry_kind": evt.kind,
            "event_id": evt.event_id,
            "child_pid": evt.child_pid,
            "parent_pid": evt.parent_pid,
            "child_guid": evt.child_guid,
            "parent_guid": evt.parent_guid,
            "child_cmd": evt.child_cmd,
            "parent_cmd": evt.parent_cmd,
            "target_path": evt.target_path,
            "reg_target": evt.reg_target,
        }

        if evt.kind == "PROCESS_CREATE":
            # Parent process
            source_node = GraphService.create_or_update_node(db, NodeCreate(
                type=NodeType.PROCESS,
                name=evt.parent_process or "unknown",
                path=evt.parent_process
            ))
            # Child process
            target_node = GraphService.create_or_update_node(db, NodeCreate(
                type=NodeType.PROCESS,
                name=evt.child_process or "unknown",
                path=evt.child_process
            ))
            edge_type = EdgeType.SPAWNED
            
        elif evt.kind == "FILE_CREATE":
             # Actor process
            source_node = GraphService.create_or_update_node(db, NodeCreate(
                type=NodeType.PROCESS,
                name=evt.child_process or "unknown",
                path=evt.child_process
            ))
            # Target file
            target_node = GraphService.create_or_update_node(db, NodeCreate(
                type=NodeType.FILE,
                name=evt.target_path or "unknown",
                path=evt.target_path
            ))
            edge_type = EdgeType.WROTE

        elif evt.kind == "REG_SET":
            # Actor process
            source_node = GraphService.create_or_update_node(db, NodeCreate(
                type=NodeType.PROCESS,
                name=evt.child_process or "unknown",
                path=evt.child_process
            ))
            # Target key
            target_node = GraphService.create_or_update_node(db, NodeCreate(
                type=NodeType.REGISTRY,
                name=evt.reg_target or "registry_key",
                path=evt.reg_target
            ))
            edge_type = EdgeType.MODIFIED_REG
        
        # 2. Create edge (GraphService handles the timestamp and Layer 3 Correlator trigger)
        if source_node and target_node:
            GraphService.create_edge(db, EdgeCreate(
                source_id=source_node.id,
                target_id=target_node.id,
                edge_type=edge_type,
                session_id=evt.session_id,
                edge_metadata=md,
            ))
