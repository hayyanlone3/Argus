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

SYS_CHANNEL = "Microsoft-Windows-Sysmon/Operational"
try:
    import win32evtlog
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
            logger.info("SysmonCollector disabled (non-Windows)")
            return
        
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SysmonCollector", daemon=True)
        self._thread.start()
        logger.info(f"SysmonCollector started (poll={self.poll_seconds}s)")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("SysmonCollector stopped")

    def _open_query(self):
        """Open the Sysmon EvtQuery handle. Returns handle or None on failure."""
        query_str = f"*[System/Provider/@Name='{PROVIDER_NAME}']"
        flags = win32evtlog.EvtQueryReverseDirection
        try:
            return win32evtlog.EvtQuery(SYS_CHANNEL, flags, query_str)
        except Exception:
            try:
                return win32evtlog.EvtQuery("Sysmon/Operational", flags, query_str)
            except Exception:
                return None

    def _run(self):
        iterations = 0
        consecutive_errors = 0

        # Open the query handle ONCE — not on every loop iteration
        q = self._open_query()
        if q is None:
            logger.warning("Sysmon event log not available, disabling collector")
            self.enabled = False
            return

        while not self._stop.is_set():
            try:
                iterations += 1
                if iterations % 300 == 0:
                    logger.debug("Telemetry sensor heartbeat: Polling...")

                events = win32evtlog.EvtNext(q, 128)

                if not events:
                    time.sleep(self.poll_seconds)
                    continue

                new_events = []
                for evt in events:
                    try:
                        xml = _evt_xml(evt)
                        if not xml:
                            continue
                        parsed = _parse_sysmon_xml(xml)
                        rid = int(parsed["record_id"])

                        if self._last_record_id is None:
                            self._last_record_id = rid - 100
                            logger.info(f"Telemetry sensor BOOTSTRAPPED with 100-event lookback at RID: {rid}")

                        if rid <= self._last_record_id:
                            break

                        new_events.append(parsed)
                    except Exception:
                        continue

                if new_events:
                    consecutive_errors = 0
                    if len(new_events) > 10:
                        logger.info(f"[COLLECTOR] Found {len(new_events)} NEW events")
                    self._last_record_id = int(new_events[0]["record_id"])
                    for p in reversed(new_events):
                        try:
                            self._handle(p["event_id"], p["data"])
                        except Exception as handle_err:
                            logger.debug(f"Error handling event {p['event_id']}: {handle_err}")

                time.sleep(self.poll_seconds)

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"SysmonCollector error #{consecutive_errors}: {e}")

                backoff_time = min(30, self.poll_seconds * (2 ** min(consecutive_errors, 5)))
                time.sleep(backoff_time)

                if consecutive_errors > 5:
                    logger.error("Too many consecutive errors, disabling SysmonCollector")
                    self.enabled = False
                    break

                # Re-open the query handle after error — old handle may be stale
                q = self._open_query()
                if q is None:
                    logger.error("Could not re-open Sysmon query, disabling collector")
                    self.enabled = False
                    break

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
            
            suspicious_processes = ["cmd.exe", "powershell.exe", "wscript.exe", "cscript.exe", "rundll32.exe", "regsvr32.exe"]
            if any(proc in image.lower() for proc in suspicious_processes):
                logger.info(f"[SYSMON] PROCESS_CREATE: {image} ({pid})")
            
            publish_event(TelemetryEvent(
                event_id=new_event_id(),
                ts=time.time(),
                source="sysmon",
                kind="PROCESS_CREATE",
                
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
            
            # Only log suspicious file operations to reduce noise
            suspicious_extensions = [".exe", ".dll", ".ps1", ".bat", ".cmd", ".vbs", ".js"]
            suspicious_paths = ["temp", "appdata", "programdata", "startup"]
            
            if (any(ext in path.lower() for ext in suspicious_extensions) or 
                any(sp in path.lower() for sp in suspicious_paths)):
                logger.debug(f"[SYSMON] FILE_CREATE: {path}")
            
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
            
            suspicious_reg_paths = ["run", "runonce", "services", "winlogon", "image file execution options"]
            
            if any(sp in key.lower() for sp in suspicious_reg_paths):
                logger.debug(f"[SYSMON] REG_SET: {key}")
            
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