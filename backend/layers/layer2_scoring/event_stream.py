# backend/layers/layer2_scoring/event_stream.py
import time
import uuid
import threading
from dataclasses import dataclass, asdict
from queue import Queue
from typing import Any, Dict, Optional
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)

# shared queue for telemetry events (sysmon → layer2 workers)
# shared queues for telemetry events
EVENT_QUEUE: "Queue[TelemetryEvent]" = Queue(maxsize=5000)      # Original (legacy/mixed)
SCORING_QUEUE: "Queue[TelemetryEvent]" = Queue(maxsize=5000)    # For Layer 2
GRAPH_QUEUE: "Queue[TelemetryEvent]" = Queue(maxsize=5000)      # For Layer 1

@dataclass
class TelemetryEvent:
    event_id: str
    ts: float
    source: str               # "sysmon"
    kind: str                 # "PROCESS_CREATE" | "FILE_CREATE" | "REG_SET"
    session_id: str
    # common process fields
    parent_process: Optional[str] = None
    child_process: Optional[str] = None
    parent_cmd: Optional[str] = None
    child_cmd: Optional[str] = None
    parent_guid: Optional[str] = None
    child_guid: Optional[str] = None
    parent_pid: Optional[str] = None
    child_pid: Optional[str] = None
    # file/reg fields
    target_path: Optional[str] = None
    reg_target: Optional[str] = None
    reg_details: Optional[str] = None
    # extra numeric signals (may be filled later)
    file_entropy: Optional[float] = None

def new_event_id(prefix: str = "evt") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"

def publish_event(evt: TelemetryEvent) -> None:
    """
    Non-blocking best-effort publish.
    If queue is full, event is dropped to avoid blocking ingestion.
    """
    try:
        print(f"[COLLECTOR] Emitting event: {evt.kind}")
        logger.info(f"🚀 [EVENT_STREAM] Publishing {evt.kind} (ID: {evt.event_id})")
        EVENT_QUEUE.put_nowait(evt)
        SCORING_QUEUE.put_nowait(evt)
        GRAPH_QUEUE.put_nowait(evt)
    except Exception as e:
        print(f"❌ [EVENT_STREAM] Failed to publish: {e}")

def to_dict(evt: TelemetryEvent) -> Dict[str, Any]:
    return asdict(evt)