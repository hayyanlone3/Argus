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

# Event IDs we care about
EV_PROCESS_CREATE = 1
EV_FILE_CREATE = 11
EV_REG_SET = 12
EV_REG_SET_2 = 13
EV_REG_SET_3 = 14

SYS_CHANNEL = "Microsoft-Windows-Sysmon/Operational"
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
    def __init__(self, poll_seconds: float = 0.1, **kwargs):  # Reduced to 0.1s for near real-time
        self.poll_seconds = poll_seconds
        passed_enabled = kwargs.get('enabled', True)
        self.enabled = (os.name == 'nt') and passed_enabled
        self._stop = threading.Event()
        self._thread = None
        self._last_record_id = None
        self._query = None
        self._query_channel = None
        self._events_processed = 0
        self._last_log_time = time.time()
        self._last_fetch_time = None
        self._last_fetch_count = 0
        self._last_fetch_error = None
        self._last_event_id = None
        self._last_event_record_id = None

    def start(self):
        if not self.enabled:
            logger.info("SysmonCollector disabled (non-Windows)")
            return
        
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SysmonCollector", daemon=True)
        self._thread.start()
        logger.info(f"SysmonCollector started (poll={self.poll_seconds}s) - REAL-TIME MODE")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("SysmonCollector stopped")

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self.enabled),
            "poll_seconds": float(self.poll_seconds),
            "last_record_id": self._last_record_id,
            "events_processed": self._events_processed,
            "query_open": self._query is not None,
            "query_channel": self._query_channel,
            "last_fetch_time": self._last_fetch_time,
            "last_fetch_count": self._last_fetch_count,
            "last_fetch_error": self._last_fetch_error,
            "last_event_id": self._last_event_id,
            "last_event_record_id": self._last_event_record_id,
        }

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
                self._query_channel = channel
                logger.debug(f"[COLLECTOR] Opened query on {channel}, RID > {self._last_record_id}")
                return q
            except Exception as e:
                logger.warning(f"[COLLECTOR] Failed to open {channel}: {e}")
        self._query = None
        self._query_channel = None
        return None

    def _fetch_new_events(self):
        if self._query is None:
            self._open_query()
        if self._query is None:
            return []
        try:
            # Fetch smaller batches for lower latency
            batch = win32evtlog.EvtNext(self._query, 100)
            if batch:
                parsed_events = []
                for evt in batch:
                    try:
                        xml = _evt_xml(evt)
                        if xml:
                            parsed = _parse_sysmon_xml(xml)
                            rid = int(parsed["record_id"])
                            self._last_event_id = int(parsed.get("event_id", 0))
                            self._last_event_record_id = rid
                            parsed_events.append((rid, parsed))
                    except Exception:
                        continue
                parsed_events.sort(key=lambda x: x[0])
                self._last_fetch_time = time.time()
                self._last_fetch_count = len(parsed_events)
                self._last_fetch_error = None
                return [p for _, p in parsed_events]
            # Re-open the query to include newly appended events
            self._open_query()
            batch = win32evtlog.EvtNext(self._query, 100)
            if batch:
                parsed_events = []
                for evt in batch:
                    try:
                        xml = _evt_xml(evt)
                        if xml:
                            parsed = _parse_sysmon_xml(xml)
                            rid = int(parsed["record_id"])
                            self._last_event_id = int(parsed.get("event_id", 0))
                            self._last_event_record_id = rid
                            parsed_events.append((rid, parsed))
                    except Exception:
                        continue
                parsed_events.sort(key=lambda x: x[0])
                self._last_fetch_time = time.time()
                self._last_fetch_count = len(parsed_events)
                self._last_fetch_error = None
                return [p for _, p in parsed_events]

            self._last_fetch_time = time.time()
            self._last_fetch_count = 0
            self._last_fetch_error = None
            return []
        except Exception as e:
            self._query = None
            self._query_channel = None
            self._last_fetch_time = time.time()
            self._last_fetch_count = 0
            self._last_fetch_error = str(e)
            return []

    def get_recent_events(self, limit: int = 5) -> Dict[str, Any]:
        out = {
            "channel": SYS_CHANNEL,
            "items": [],
            "error": None,
        }
        try:
            q = win32evtlog.EvtQuery(
                SYS_CHANNEL,
                win32evtlog.EvtQueryReverseDirection,
                f"*[System/Provider/@Name='{PROVIDER_NAME}']",
            )
            batch = win32evtlog.EvtNext(q, max(1, int(limit)))
            for evt in batch:
                xml = _evt_xml(evt)
                if not xml:
                    continue
                parsed = _parse_sysmon_xml(xml)
                out["items"].append({
                    "event_id": int(parsed.get("event_id", 0)),
                    "record_id": int(parsed.get("record_id", 0)),
                })
        except Exception as e:
            out["error"] = str(e)
        return out

    def _run(self):
        consecutive_errors = 0

        # REAL-TIME MODE: Always start from current position, ignore history
        try:
            # Get most recent event RID
            temp_query = win32evtlog.EvtQuery(
                SYS_CHANNEL, 
                win32evtlog.EvtQueryReverseDirection,
                f"*[System/Provider/@Name='{PROVIDER_NAME}']"
            )
            recent = win32evtlog.EvtNext(temp_query, 1)
            if recent:
                xml = _evt_xml(recent[0])
                parsed = _parse_sysmon_xml(xml)
                self._last_record_id = int(parsed["record_id"])
                logger.info(f"[COLLECTOR] 🚀 REAL-TIME MODE: Starting from RID {self._last_record_id}")
                logger.info(f"[COLLECTOR] ⚡ Ignoring all historical events - only NEW events will be processed")
            else:
                self._last_record_id = 0
        except Exception as e:
            logger.warning(f"[COLLECTOR] Could not determine latest RID: {e}")
            self._last_record_id = 0

        # Open persistent query
        self._open_query()
        if self._query is None:
            logger.error("[COLLECTOR] CRITICAL: Sysmon event log not available")
            self.enabled = False
            return

        logger.info("[COLLECTOR] 🎯 READY - Waiting for new malware activity...")

        while not self._stop.is_set():
            try:
                events = self._fetch_new_events()

                if events:
                    consecutive_errors = 0
                    self._events_processed += len(events)
                    self._last_record_id = int(events[-1]["record_id"])
                    self._save_record_id(self._last_record_id)
                    
                    # Process events immediately
                    for p in events:
                        try:
                            self._handle(p["event_id"], p["data"])
                        except Exception as handle_err:
                            logger.debug(f"[COLLECTOR] Error handling event: {handle_err}")

                # Very short sleep for near real-time
                time.sleep(self.poll_seconds)

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"[COLLECTOR] Error: {e}")

                if consecutive_errors > 5:
                    logger.error("[COLLECTOR] Too many errors, disabling")
                    self.enabled = False
                    break

                # Re-open query
                q = self._open_query()
                if q is None:
                    logger.error("[COLLECTOR] Could not re-open query")
                    self.enabled = False
                    break
                
                time.sleep(min(5, self.poll_seconds * 2))

    def _handle(self, event_id: int, data: Dict[str, Any]):
        debug = os.getenv("ARGUS_SYSMON_DEBUG", "false").lower() == "true"
        # FILTER: Only process events we care about for malware detection
        if event_id == EV_PROCESS_CREATE:
            # Only process suspicious process creations
            image = data.get("Image", "").lower()
            if debug:
                logger.debug(f"[COLLECTOR] EV1 image={image} parent={data.get('ParentImage', '')} cmd={data.get('CommandLine', '')}")
            if any(proc in image for proc in ["cmd.exe", "powershell", "wscript", "cscript", "rundll32", "regsvr32", "mshta", "certutil", "bitsadmin"]):
                self._handle_process_create(data)
            elif debug:
                logger.debug(f"[COLLECTOR] EV1 skipped (not suspicious): {image}")
        elif event_id == EV_FILE_CREATE:
            # Only process suspicious file creations
            path = data.get("TargetFilename", "").lower()
            if debug:
                logger.debug(f"[COLLECTOR] EV11 path={path} image={data.get('Image', '')}")
            if any(ext in path for ext in [".exe", ".dll", ".ps1", ".bat", ".vbs", ".js"]) or \
               any(loc in path for loc in ["temp", "appdata", "programdata", "malware"]):
                self._handle_file_create(data)
            elif debug:
                logger.debug(f"[COLLECTOR] EV11 skipped (not suspicious): {path}")
        elif event_id in [EV_REG_SET, EV_REG_SET_2, EV_REG_SET_3]:
            # Only process persistence-related registry changes
            key = data.get("TargetObject", "").lower()
            if debug:
                logger.debug(f"[COLLECTOR] EV12/13/14 key={key} image={data.get('Image', '')}")
            if any(k in key for k in ["run", "runonce", "services", "winlogon"]):
                self._handle_reg_set(data)
            elif debug:
                logger.debug(f"[COLLECTOR] EV12/13/14 skipped (not persistence): {key}")
        # Ignore all other events for performance

    def _handle_process_create(self, data: Dict[str, Any]):
        try:
            image = data.get("Image", "unknown")
            pid = data.get("ProcessId")
            parent_image = data.get("ParentImage", "unknown")
            parent_pid = data.get("ParentProcessId")
            cmd = data.get("CommandLine", "")
            proc_guid = data.get("ProcessGuid")
            parent_guid = data.get("ParentProcessGuid")
            
            # Publish event immediately (no logging to reduce noise)
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
        except Exception as e:
             logger.error(f"[COLLECTOR] Error in process_create handler: {e}")

    def _handle_file_create(self, data: Dict[str, Any]):
        try:
            path = data.get("TargetFilename", "unknown")
            image = data.get("Image", "unknown")
            pid = data.get("ProcessId")
            proc_guid = data.get("ProcessGuid")
            
            # Skip known legitimate temporary files
            if "__psscriptpolicytest_" in path.lower():
                return
            
            # Publish event (no logging)
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
            
            # Publish event (no logging)
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