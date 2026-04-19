# backend/collectors/sysmon_collector.py

import time
import threading
import asyncio
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
from backend.layers.layer0_bouncer.services import BouncerService

logger = setup_logger(__name__)

SYS_CHANNEL = "Microsoft-Windows-Sysmon/Operational"
PROVIDER_NAME = "Microsoft-Windows-Sysmon"

EV_PROCESS_CREATE = 1
EV_CREATE_REMOTE_THREAD = 8
EV_PROCESS_ACCESS = 10
EV_FILE_CREATE = 11
EV_REG_VALUE_SET = 13

SUSPICIOUS_EXTENSIONS = (
    ".exe", ".dll", ".sys", ".scr", ".com",
    ".ps1", ".psm1", ".vbs", ".js", ".jse", ".wsf", ".hta", ".bat",
    ".cmd", ".lnk", ".docm", ".xlsm", ".pptm", ".txt"
)


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
        elif event_id == EV_CREATE_REMOTE_THREAD:
            self._handle_create_remote_thread(data)
        elif event_id == EV_PROCESS_ACCESS:
            self._handle_process_access(data)
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

            # === AUTO-TRIGGER .exe/.dll/... Bouncer Analysis HERE ===
            if target.lower().endswith(SUSPICIOUS_EXTENSIONS):
                logger.info(f"🚦 [Layer0 AutoScan] Analyzing suspicious file: {target}")
                try:
                    import os as _os
                    file_size = _os.path.getsize(target) if _os.path.exists(target) else 0
                    result = BouncerService.bouncer_decision(target, file_size, vt_score=0.0, db=db)
                    decision_status = result.get('status', 'UNKNOWN')
                    logger.info(f"🔍 [Layer0 Result] {target} → {decision_status}")

                    if decision_status in ["BLOCK", "CRITICAL"]:
                        logger.warning(f"🚨 [Layer0 Action] Auto-quarantining {target} due to {decision_status} verdict.")
                        from backend.layers.layer4_response.quarantine import QuarantineService
                        from backend.database.schemas import QuarantineCreate
                        try:
                            # Attempt to quarantine the file immediately
                            # Providing a dummy hash if None, though calculation should exist
                            f_hash = result.get('file_hash') or "unknown_hash"
                            QuarantineService.quarantine_file(
                                file_path=target,
                                db=db,
                                quarantine_data=QuarantineCreate(
                                    original_path=target,
                                    hash_sha256=f_hash,
                                    detection_layer="Layer 0",
                                    confidence=0.99 if decision_status == "BLOCK" else 0.85
                                )
                            )
                            logger.info(f"✅ [Layer0 Action] Success quarantining {target}")
                        except Exception as q_err:
                            logger.error(f"❌ [Layer0 Action] Failed to quarantine {target}: {q_err}")

                except Exception as e:
                    logger.error(f"❌ Layer0 auto-scan failed for {target}: {e}")

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

    def _handle_create_remote_thread(self, data: Dict[str, Any]):
        """Sysmon Event ID 8: CreateRemoteThread — strong injection signal."""
        db = connection.SessionLocal()
        try:
            source_image = data.get("SourceImage") or ""
            target_image = data.get("TargetImage") or ""
            source_pid = data.get("SourceProcessId") or ""
            target_pid = data.get("TargetProcessId") or ""
            source_guid = data.get("SourceProcessGuid") or ""
            target_guid = data.get("TargetProcessGuid") or ""
            new_thread_id = data.get("NewThreadId") or ""
            start_address = data.get("StartAddress") or ""
            start_function = data.get("StartFunction") or ""

            sid = _session_id("sysmon", f"inject:{source_pid}:{target_pid}")

            source_node = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(source_image.split("\\")[-1] or "source"), path=source_image, hash_sha256=None, path_risk=0.0),
            )
            target_node = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(target_image.split("\\")[-1] or "target"), path=target_image, hash_sha256=None, path_risk=0.0),
            )

            GraphService.create_edge(
                db,
                EdgeCreate(
                    source_id=source_node.id,
                    target_id=target_node.id,
                    edge_type=EdgeType.INJECTED_INTO,
                    session_id=sid,
                    injection_type="CreateRemoteThread",
                    edge_metadata={
                        "collector": "sysmon",
                        "event_id": 8,
                        "source_pid": source_pid,
                        "target_pid": target_pid,
                        "source_guid": source_guid,
                        "target_guid": target_guid,
                        "new_thread_id": new_thread_id,
                        "start_address": start_address,
                        "start_function": start_function,
                    },
                ),
            )

            logger.warning(f"🚨 [INJECTION] CreateRemoteThread: {source_image} → {target_image}")

            if self.audit_enabled:
                AuditLogger.log(
                    db,
                    source="collector.sysmon",
                    action="create_remote_thread",
                    level="WARNING",
                    message=f"CreateRemoteThread: {source_image} → {target_image}",
                    entity_type="process",
                    entity_id=target_node.id,
                    session_id=sid,
                    path=target_image,
                    payload={"source_pid": source_pid, "target_pid": target_pid, "start_address": start_address},
                )

        except Exception:
            logger.exception("❌ Sysmon CreateRemoteThread handling failed")
        finally:
            db.close()

    def _handle_process_access(self, data: Dict[str, Any]):
        """Sysmon Event ID 10: ProcessAccess — potential injection via OpenProcess."""
        db = connection.SessionLocal()
        try:
            source_image = data.get("SourceImage") or ""
            target_image = data.get("TargetImage") or ""
            source_pid = data.get("SourceProcessId") or ""
            target_pid = data.get("TargetProcessId") or ""
            granted_access = data.get("GrantedAccess") or ""
            call_trace = data.get("CallTrace") or ""

            # Only flag high-risk access masks (PROCESS_ALL_ACCESS, VM_WRITE+VM_OPERATION, etc.)
            risky_masks = {"0x1fffff", "0x1f0fff", "0x143a", "0x1410"}
            if granted_access.lower() not in risky_masks:
                return

            sid = _session_id("sysmon", f"access:{source_pid}:{target_pid}")

            source_node = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(source_image.split("\\")[-1] or "source"), path=source_image, hash_sha256=None, path_risk=0.0),
            )
            target_node = GraphService.create_or_update_node(
                db,
                NodeCreate(type=NodeType.PROCESS, name=(target_image.split("\\")[-1] or "target"), path=target_image, hash_sha256=None, path_risk=0.0),
            )

            GraphService.create_edge(
                db,
                EdgeCreate(
                    source_id=source_node.id,
                    target_id=target_node.id,
                    edge_type=EdgeType.INJECTED_INTO,
                    session_id=sid,
                    injection_type="ProcessAccess",
                    edge_metadata={
                        "collector": "sysmon",
                        "event_id": 10,
                        "source_pid": source_pid,
                        "target_pid": target_pid,
                        "granted_access": granted_access,
                        "call_trace": call_trace[:500],
                    },
                ),
            )

            logger.warning(f"🚨 [INJECTION] ProcessAccess({granted_access}): {source_image} → {target_image}")

            if self.audit_enabled:
                AuditLogger.log(
                    db,
                    source="collector.sysmon",
                    action="process_access",
                    level="WARNING",
                    message=f"ProcessAccess({granted_access}): {source_image} → {target_image}",
                    entity_type="process",
                    entity_id=target_node.id,
                    session_id=sid,
                    path=target_image,
                    payload={"source_pid": source_pid, "target_pid": target_pid, "granted_access": granted_access},
                )

        except Exception:
            logger.exception("❌ Sysmon ProcessAccess handling failed")
        finally:
            db.close()