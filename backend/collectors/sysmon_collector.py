# backend/collectors/sysmon_collector.py
import threading
import time
import win32evtlog
import win32evtlogutil
import win32event
from typing import Optional, List, Dict, Any, Callable
from backend.database import connection
from backend.shared.logger import setup_logger
from backend.layers.layer2_scoring.event_stream import publish_event, TelemetryEvent, new_event_id
import os

logger = setup_logger(__name__)

# Event IDs
EV_PROCESS_CREATE = 1
EV_NET_CONN = 3
EV_FILE_CREATE = 11
EV_REG_SET = 12
EV_REG_SET_2 = 13
EV_REG_SET_3 = 14
EV_CREATE_REMOTE_THREAD = 8
EV_PROCESS_ACCESS = 10

# Dynamic channel detection
SYS_CHANNEL = "Microsoft-Windows-Sysmon/Operational"
# Test channel on import (basic attempt)
try:
    import win32evtlog
    # Check if Microsoft-Windows-... exists, otherwise fallback to Sysmon/...
    # Note: Full check happens in _run, just defined here.
except:
    pass

PROVIDER_NAME = "Microsoft-Windows-Sysmon"

def _evt_xml(evt):
    return win32evtlog.EvtRender(evt, win32evtlog.EvtRenderEventXml)

def _parse_sysmon_xml(xml_str: str) -> Dict[str, Any]:
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_str)
    
    ns = "{http://schemas.microsoft.com/win/2004/08/events/event}"
    sys = root.find(f"{ns}System")
    edata = root.find(f"{ns}EventData")
    
    event_id = int(sys.find(f"{ns}EventID").text)
    record_id = sys.find(f"{ns}EventRecordID").text
    
    data = {}
    if edata is not None:
        for item in edata:
            name = item.get("Name")
            data[name] = item.text
            
    return {"event_id": event_id, "record_id": record_id, "data": data}

class SysmonCollector:
    def __init__(self, poll_seconds: float = 1.0, **kwargs):
        self.poll_seconds = poll_seconds
        # Accept 'enabled' if passed, otherwise default to Windows check
        passed_enabled = kwargs.get('enabled', True)
        self.enabled = (os.name == 'nt') and passed_enabled
        self._stop = threading.Event()
        self._thread = None
        self._last_record_id = None

    def start(self):
        if not self.enabled:
            logger.warning("🟡 SysmonCollector disabled (non-Windows)")
            return
        
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SysmonCollector", daemon=True)
        self._thread.start()
        logger.warning(f"🟢 SysmonCollector started (poll={self.poll_seconds}s)")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.warning("🛑 SysmonCollector stopped")

    def _run(self):
        query = f"*[System/Provider/@Name='{PROVIDER_NAME}']"
        iterations = 0
        
        while not self._stop.is_set():
            try:
                iterations += 1
                if iterations % 10 == 0:
                    logger.info("📡 Telemetry sensor heartbeat: Polling...")

                flags = win32evtlog.EvtQueryReverseDirection
                
                # TRY CHANNEL A
                try:
                   q = win32evtlog.EvtQuery(SYS_CHANNEL, flags, query)
                except:
                   # FALLBACK TO CHANNEL B
                   q = win32evtlog.EvtQuery("Sysmon/Operational", flags, query)

                events = win32evtlog.EvtNext(q, 128)

                if not events:
                    time.sleep(self.poll_seconds)
                    continue

                new_events = []
                for evt in events:
                    try:
                        xml = _evt_xml(evt)
                        if not xml: continue
                        parsed = _parse_sysmon_xml(xml)
                        rid = int(parsed["record_id"])
                        
                        if self._last_record_id is None:
                            # BOOTSTRAP: Look back 100 events to ensure we have context
                            self._last_record_id = rid - 100
                            logger.warning(f"🎯 Telemetry sensor BOOTSTRAPPED with 100-event lookback at RID: {rid}")

                        if rid <= self._last_record_id:
                            break
                        
                        new_events.append(parsed)
                    except:
                        continue

                if new_events:
                    logger.warning(f"🔍 [COLLECTOR] Found {len(new_events)} NEW events!")
                    self._last_record_id = int(new_events[0]["record_id"])
                    for p in reversed(new_events):
                        self._handle(p["event_id"], p["data"])

                time.sleep(self.poll_seconds)

            except Exception as e:
                logger.error(f"❌ SysmonCollector error: {e}")
                time.sleep(5)

    def _handle(self, event_id: int, data: Dict[str, Any]):
        if event_id == EV_PROCESS_CREATE:
            self._handle_process_create(data)
        elif event_id == EV_FILE_CREATE:
            self._handle_file_create(data)
        elif event_id in [EV_REG_SET, EV_REG_SET_2, EV_REG_SET_3]:
            self._handle_reg_set(data)
        elif event_id == EV_NET_CONN:
            self._handle_net_conn(data)

    def _handle_process_create(self, data: Dict[str, Any]):
        try:
            image = data.get("Image", "unknown")
            pid = data.get("ProcessId")
            parent_image = data.get("ParentImage", "unknown")
            parent_pid = data.get("ParentProcessId")
            cmd = data.get("CommandLine", "")
            proc_guid = data.get("ProcessGuid")
            parent_guid = data.get("ParentProcessGuid")
            
            logger.warning(f"🟢 [SYSMON] PROCESS_CREATE: {image} ({pid})")
            
            publish_event(TelemetryEvent(
                event_id=new_event_id(),
                ts=time.time(),
                source="sysmon",
                kind="PROCESS_CREATE",
                # Use Sysmon GUID as correlation key when available
                session_id=str(proc_guid or f"pid-{pid}"),
                child_pid=str(pid),
                child_process=image,
                child_cmd=cmd,
                parent_pid=str(parent_pid),
                parent_process=parent_image,
                child_guid=str(proc_guid) if proc_guid else None,
                parent_guid=str(parent_guid) if parent_guid else None,
            ))
        except Exception:
             logger.exception("Error in process_create handler")

    def _handle_file_create(self, data: Dict[str, Any]):
        try:
            path = data.get("TargetFilename", "unknown")
            image = data.get("Image", "unknown")
            pid = data.get("ProcessId")
            proc_guid = data.get("ProcessGuid")
            
            logger.warning(f"🔵 [SYSMON] FILE_CREATE: {path}")
            
            publish_event(TelemetryEvent(
                event_id=new_event_id(),
                ts=time.time(),
                source="sysmon",
                kind="FILE_CREATE",
                session_id=str(proc_guid or f"pid-{pid}"),
                child_pid=str(pid),
                child_process=image,
                target_path=path,
                child_guid=str(proc_guid) if proc_guid else None,
            ))
        except Exception:
            logger.exception("Error in file_create handler")

    def _handle_reg_set(self, data: Dict[str, Any]):
        try:
            key = data.get("TargetObject", "unknown")
            image = data.get("Image", "unknown")
            pid = data.get("ProcessId")
            proc_guid = data.get("ProcessGuid")
            
            logger.warning(f"🟡 [SYSMON] REG_SET: {key}")
            
            publish_event(TelemetryEvent(
                event_id=new_event_id(),
                ts=time.time(),
                source="sysmon",
                kind="REG_SET",
                session_id=str(proc_guid or f"pid-{pid}"),
                child_pid=str(pid),
                child_process=image,
                reg_target=key,
                child_guid=str(proc_guid) if proc_guid else None,
            ))
        except Exception:
            logger.exception("Error in reg_set handler")

    def _handle_net_conn(self, data: Dict[str, Any]):
        pass