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
        passed_enabled = kwargs.get('enabled', True)
        self.enabled = (os.name == 'nt') and passed_enabled
        self._stop = threading.Event()
        self._thread = None
        self._last_record_id = None
        self._query = None  # Persistent query handle

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

    def _save_record_id(self, rid: int):
        state_file = os.path.join(os.path.dirname(__file__), ".sysmon_last_rid")
        try:
            with open(state_file, "w") as f:
                f.write(str(rid))
        except Exception as e:
            logger.debug(f"[COLLECTOR] Failed to save RID: {e}")

    def _open_query(self):
        """Open a forward-direction query filtered to events after last_rid."""
        if self._last_record_id and self._last_record_id > 0:
            query_str = f"*[System[(EventRecordID > {self._last_record_id}) and Provider/@Name='{PROVIDER_NAME}']]"
        else:
            query_str = f"*[System/Provider/@Name='{PROVIDER_NAME}']"
        for channel in [SYS_CHANNEL, "Sysmon/Operational"]:
            try:
                q = win32evtlog.EvtQuery(channel, win32evtlog.EvtQueryForwardDirection, query_str)
                self._query = q
                logger.info(f"[COLLECTOR] Opened query on {channel}, RID > {self._last_record_id}")
                return q
            except Exception as e:
                logger.warning(f"[COLLECTOR] Failed to open {channel}: {e}")
        self._query = None
        return None

    def _fetch_new_events(self):
        """Fetch the next batch of new events in forward order."""
        if self._query is None:
            self._open_query()
        if self._query is None:
            return []
        try:
            batch = win32evtlog.EvtNext(self._query, 512)
            if batch:
                parsed_events = []
                for evt in batch:
                    try:
                        xml = _evt_xml(evt)
                        if xml:
                            parsed = _parse_sysmon_xml(xml)
                            rid = int(parsed["record_id"])
                            parsed_events.append((rid, parsed))
                    except Exception:
                        continue
                parsed_events.sort(key=lambda x: x[0])
                return [p for _, p in parsed_events]
            self._query = None
            return []
        except Exception as e:
            self._query = None
            return []

    def _run(self):
        iterations = 0
        consecutive_errors = 0

        # Load last processed RID from state file
        state_file = os.path.join(os.path.dirname(__file__), ".sysmon_last_rid")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    self._last_record_id = int(f.read().strip())
        except Exception:
            pass
        if not self._last_record_id:
            self._last_record_id = 0

        if self._last_record_id:
            logger.info(f"[COLLECTOR] Bootstrap: resuming from RID {self._last_record_id}")
        else:
            logger.info("[COLLECTOR] Bootstrap: no prior state, starting from oldest")

        # Open persistent query
        self._open_query()
        if self._query is None:
            logger.error("[COLLECTOR] CRITICAL: Sysmon event log not available, disabling collector")
            self.enabled = False
            return

        while not self._stop.is_set():
            try:
                iterations += 1
                if iterations % 300 == 0:
                    logger.debug("Telemetry sensor heartbeat: Polling...")

                events = self._fetch_new_events()

                if not events:
                    if iterations % 100 == 0:
                        logger.debug("[COLLECTOR] No new events in this poll")
                    time.sleep(self.poll_seconds)
                    continue

                if events:
                    consecutive_errors = 0
                    logger.info(f"[COLLECTOR] Processing {len(events)} NEW events")
                    self._last_record_id = int(events[-1]["record_id"])
                    self._save_record_id(self._last_record_id)
                    for p in events:
                        try:
                            self._handle(p["event_id"], p["data"])
                        except Exception as handle_err:
                            logger.debug(f"[COLLECTOR] Error handling event {p['event_id']}: {handle_err}")

                time.sleep(self.poll_seconds)

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"[COLLECTOR] ❌ Error #{consecutive_errors}: {e}")

                backoff_time = min(30, self.poll_seconds * (2 ** min(consecutive_errors, 5)))
                time.sleep(backoff_time)

                if consecutive_errors > 5:
                    logger.error("[COLLECTOR] ❌ Too many consecutive errors, disabling SysmonCollector")
                    self.enabled = False
                    break

                # Re-open the query handle after error — old handle may be stale
                q = self._open_query()
                if q is None:
                    logger.error("[COLLECTOR] ❌ Could not re-open Sysmon query, disabling collector")
                    self.enabled = False
                    break

    def _handle(self, event_id: int, data: Dict[str, Any]):
        if event_id == EV_PROCESS_CREATE:
            self._handle_process_create(data)
        elif event_id == EV_FILE_CREATE:
            path = data.get("TargetFilename", "unknown")
            with open(os.path.join(os.path.dirname(__file__), "_debug_fc.log"), "a") as f:
                f.write(f"{time.time()} FILE_CREATE: {path}\n")
            self._handle_file_create(data)
        elif event_id in [EV_REG_SET, EV_REG_SET_2, EV_REG_SET_3]:
            self._handle_reg_set(data)
        elif event_id == EV_NET_CONN:
            self._handle_net_conn(data)
        elif event_id == 5:
            pass  # Process terminate - ignore
        else:
            if event_id not in (2, 4, 6, 7, 9, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26):
                with open(os.path.join(os.path.dirname(__file__), "_debug_fc.log"), "a") as f:
                    f.write(f"{time.time()} OTHER event_id={event_id}\n")

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
                logger.info(f"[SYSMON]   Parent: {parent_image}")
                logger.info(f"[SYSMON]   Command: {cmd[:100] if cmd else 'N/A'}")
            
            logger.debug(f"[COLLECTOR] Publishing PROCESS_CREATE event: {image}")
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
            logger.info(f"[COLLECTOR] ✅ Event published to queues")
        except Exception as e:
             logger.exception(f"[COLLECTOR] ❌ Error in process_create handler: {e}")

    def _handle_file_create(self, data: Dict[str, Any]):
        try:
            path = data.get("TargetFilename", "unknown")
            image = data.get("Image", "unknown")
            pid = data.get("ProcessId")
            proc_guid = data.get("ProcessGuid")
            
            # Skip known legitimate temporary files
            if "__psscriptpolicytest_" in path.lower():
                return
            
            suspicious_extensions = [".exe", ".dll", ".ps1", ".bat", ".cmd", ".vbs", ".js"]
            suspicious_paths = ["temp", "appdata", "programdata", "startup", "simulations"]
            
            if (any(ext in path.lower() for ext in suspicious_extensions) or 
                any(sp in path.lower() for sp in suspicious_paths)):
                logger.info(f"[SYSMON] FILE_CREATE: {path}")
            
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