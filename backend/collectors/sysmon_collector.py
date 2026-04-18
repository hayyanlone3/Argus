# backend/collectors/sysmon_collector.py

import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any

import win32evtlog
import xml.etree.ElementTree as ET

from backend.shared.logger import setup_logger
from backend.shared.enums import NodeType, EdgeType
from backend.shared.audit import AuditLogger

from backend.database import connection
from backend.database.schemas import NodeCreate, EdgeCreate
from backend.layers.layer1_graph_engine.services import GraphService
from backend.layers.layer2_scoring.event_stream import TelemetryEvent, publish_event, new_event_id

logger = setup_logger(__name__)

SYS_CHANNEL = "Microsoft-Windows-Sysmon/Operational"
PROVIDER_NAME = "Microsoft-Windows-Sysmon"

EV_PROCESS_CREATE = 1
EV_FILE_CREATE = 11
EV_REG_VALUE_SET = 13


def _session_id(prefix: str, key: str) -> str:
    # keep within String(100) constraint
    minute = datetime.utcnow().strftime("%Y%m%d-%H%M")
    s = f"{prefix}:{minute}:{key}"
    return s[:95]


def _evt_xml(evt) -> Optional[str]:
    try:
        return win32evtlog.EvtRender(evt, win32evtlog.EvtRenderEventXml)
    except Exception:
        return None


def _parse_sysmon_xml(xml: str) -> Dict[str, Any]:
    root = ET.fromstring(xml)
    ns = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}

    event_id = int(root.findtext("e:System/e:EventID", default="0", namespaces=ns))
    record_id = root.findtext("e:System/e:EventRecordID", default="", namespaces=ns)
    system_time = ""
    try:
        system_time = root.find("e:System/e:TimeCreated", ns).attrib.get("SystemTime", "")
    except Exception:
        pass

    data = {}
    for d in root.findall("e:EventData/e:Data", ns):
        name = d.attrib.get("Name")
        if name:
            data[name] = (d.text or "")

    return {
        "event_id": event_id,
        "record_id": record_id,
        "system_time": system_time,
        "data": data,
    }


class SysmonCollector:
    """
    Poll Sysmon Operational log and convert events into ARGUS Layer 1 nodes/edges.

    Event ID 1  -> SPAWNED
    Event ID 11 -> WROTE
    Event ID 13 -> MODIFIED_REG
    """

    def __init__(self, enabled: bool = True, poll_seconds: float = 1.0, audit_enabled: bool = True):
        self.enabled = enabled
        self.poll_seconds = max(0.2, float(poll_seconds))
        self.audit_enabled = audit_enabled

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

        self._last_record_id: Optional[int] = None

    def start(self):
        if not self.enabled:
            logger.warning("🟡 SysmonCollector disabled")
            return
        if connection.SessionLocal is None:
            raise RuntimeError("DB not initialized. Call init_db() before SysmonCollector.start().")

        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SysmonCollector", daemon=True)
        self._thread.start()
        logger.warning(f"🟢 SysmonCollector started (poll={self.poll_seconds}s)")

        self._audit("started", {"channel": SYS_CHANNEL})

    def stop(self):
        if not self._thread:
            return
        self._stop.set()
        self._thread.join(timeout=5)
        self._thread = None
        logger.warning("🛑 SysmonCollector stopped")
        self._audit("stopped")

    def _audit(self, action: str, payload: Optional[dict] = None):
        if not self.audit_enabled or connection.SessionLocal is None:
            return
        try:
            db = connection.SessionLocal()
            try:
                AuditLogger.log(
                    db,
                    source="collector.sysmon",
                    action=action,
                    message=f"SysmonCollector {action}",
                    payload=payload or {},
                )
            finally:
                db.close()
        except Exception:
            pass

    def _run(self):
        query = f"*[System/Provider/@Name='{PROVIDER_NAME}']"

        while not self._stop.is_set():
            try:
                flags = win32evtlog.EvtQueryReverseDirection
                q = win32evtlog.EvtQuery(SYS_CHANNEL, flags, query)

                events = win32evtlog.EvtNext(q, 64)
                if not events:
                    time.sleep(self.poll_seconds)
                    continue

                for evt in reversed(events):
                    xml = _evt_xml(evt)
                    if not xml:
                        continue

                    parsed = _parse_sysmon_xml(xml)
                    rid = parsed["record_id"]
                    if not rid:
                        continue

                    rid_i = int(rid)
                    if self._last_record_id is not None and rid_i <= self._last_record_id:
                        continue

                    self._handle(parsed["event_id"], parsed["data"])
                    self._last_record_id = rid_i

            except Exception:
                logger.exception("❌ SysmonCollector loop error")
                time.sleep(self.poll_seconds)

    def _handle(self, event_id: int, data: Dict[str, Any]):
        if event_id == EV_PROCESS_CREATE:
            self._handle_process_create(data)
        elif event_id == EV_FILE_CREATE:
            self._handle_file_create(data)
        elif event_id == EV_REG_VALUE_SET:
            self._handle_reg_set(data)

    def _handle_process_create(self, data: Dict[str, Any]):
        db = connection.SessionLocal()
        try:
            child_image = data.get("Image") or ""
            parent_image = data.get("ParentImage") or ""

            child_pid = data.get("ProcessId") or ""
            parent_pid = data.get("ParentProcessId") or ""
            child_guid = data.get("ProcessGuid") or ""
            parent_guid = data.get("ParentProcessGuid") or ""

            sid = _session_id("sysmon", f"spawn:{child_pid}")

            # publish to Layer2 stream (non-blocking)
            publish_event(TelemetryEvent(
                event_id=new_event_id("sysmon1"),
                ts=time.time(),
                source="sysmon",
                kind="PROCESS_CREATE",
                session_id=sid,
                parent_process=parent_image,
                child_process=child_image,
                parent_cmd=data.get("ParentCommandLine"),
                child_cmd=data.get("CommandLine"),
                parent_guid=parent_guid,
                child_guid=child_guid,
                parent_pid=parent_pid,
                child_pid=child_pid,
            ))

            parent = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(parent_image.split("\\")[-1] or "parent"), path=parent_image, hash_sha256=None, path_risk=0.0),
            )
            child = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(child_image.split("\\")[-1] or "child"), path=child_image, hash_sha256=None, path_risk=0.0),
            )

            GraphService.create_edge(
                db,
                EdgeCreate(
                    source_id=parent.id,
                    target_id=child.id,
                    edge_type=EdgeType.SPAWNED,
                    session_id=sid,
                    edge_metadata={
                        "collector": "sysmon",
                        "event_id": 1,
                        "child_pid": child_pid,
                        "parent_pid": parent_pid,
                        "child_guid": child_guid,
                        "parent_guid": parent_guid,
                        "child_cmd": data.get("CommandLine"),
                        "parent_cmd": data.get("ParentCommandLine"),
                    },
                ),
            )

            if self.audit_enabled:
                AuditLogger.log(
                    db,
                    source="collector.sysmon",
                    action="process_create",
                    message=f"ProcessCreate: {child_image}",
                    entity_type="process",
                    entity_id=child.id,
                    session_id=sid,
                    path=child_image,
                    payload={"child_pid": child_pid, "parent_pid": parent_pid, "child_guid": child_guid, "parent_guid": parent_guid},
                )

        except Exception:
            logger.exception("❌ Sysmon ProcessCreate handling failed")
        finally:
            db.close()

    def _handle_file_create(self, data: Dict[str, Any]):
        db = connection.SessionLocal()
        try:
            image = data.get("Image") or ""
            pid = data.get("ProcessId") or ""
            guid = data.get("ProcessGuid") or ""
            target = data.get("TargetFilename") or ""

            sid = _session_id("sysmon", f"write:{pid}")

            # publish to Layer2 stream (non-blocking)
            publish_event(TelemetryEvent(
                event_id=new_event_id("sysmon11"),
                ts=time.time(),
                source="sysmon",
                kind="FILE_CREATE",
                session_id=sid,
                child_process=image,
                child_guid=guid,
                child_pid=pid,
                target_path=target,
            ))

            proc = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(image.split("\\")[-1] or "process"), path=image, hash_sha256=None, path_risk=0.0),
            )
            file_node = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.FILE, name=(target.split("\\")[-1] or "file"), path=target, hash_sha256=None, path_risk=0.0),
            )

            GraphService.create_edge(
                db,
                EdgeCreate(
                    source_id=proc.id,
                    target_id=file_node.id,
                    edge_type=EdgeType.WROTE,
                    session_id=sid,
                    edge_metadata={
                        "collector": "sysmon",
                        "event_id": 11,
                        "pid": pid,
                        "guid": guid,
                        "target": target,
                    },
                ),
            )

            if self.audit_enabled:
                AuditLogger.log(
                    db,
                    source="collector.sysmon",
                    action="file_create",
                    message=f"FileCreate: {target}",
                    entity_type="file",
                    entity_id=file_node.id,
                    session_id=sid,
                    path=target,
                    payload={"process_image": image, "pid": pid, "guid": guid},
                )

        except Exception:
            logger.exception("❌ Sysmon FileCreate handling failed")
        finally:
            db.close()

    def _handle_reg_set(self, data: Dict[str, Any]):
        db = connection.SessionLocal()
        try:
            image = data.get("Image") or ""
            pid = data.get("ProcessId") or ""
            guid = data.get("ProcessGuid") or ""
            target_obj = data.get("TargetObject") or ""
            details = data.get("Details") or ""

            sid = _session_id("sysmon", f"reg:{pid}")

            # publish to Layer2 stream (non-blocking)
            publish_event(TelemetryEvent(
                event_id=new_event_id("sysmon13"),
                ts=time.time(),
                source="sysmon",
                kind="REG_SET",
                session_id=sid,
                child_process=image,
                child_guid=guid,
                child_pid=pid,
                reg_target=target_obj,
                reg_details=details,
            ))

            proc = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(image.split("\\")[-1] or "process"), path=image, hash_sha256=None, path_risk=0.0),
            )
            reg_node = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.REG_KEY, name=(target_obj.split("\\")[-1] or "reg"), path=target_obj, hash_sha256=None, path_risk=0.0),
            )

            GraphService.create_edge(
                db,
                EdgeCreate(
                    source_id=proc.id,
                    target_id=reg_node.id,
                    edge_type=EdgeType.MODIFIED_REG,
                    session_id=sid,
                    edge_metadata={
                        "collector": "sysmon",
                        "event_id": 13,
                        "pid": pid,
                        "guid": guid,
                        "target_object": target_obj,
                        "details": details,
                    },
                ),
            )

            if self.audit_enabled:
                AuditLogger.log(
                    db,
                    source="collector.sysmon",
                    action="reg_set",
                    message=f"RegistrySet: {target_obj}",
                    entity_type="reg_key",
                    entity_id=reg_node.id,
                    session_id=sid,
                    path=target_obj,
                    payload={"process_image": image, "pid": pid, "guid": guid, "details": details},
                )

        except Exception:
            logger.exception("❌ Sysmon RegistrySet handling failed")
        finally:
            db.close()