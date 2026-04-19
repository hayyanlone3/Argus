# backend/layers/layer2_scoring/runtime_engine.py
import os
import math
import threading
import time
import subprocess
import hashlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

from backend.shared.logger import setup_logger
from backend.layers.layer2_scoring.event_stream import EVENT_QUEUE, TelemetryEvent, to_dict
from backend.layers.layer4_response.isolation import IsolationService

from backend.database import connection
from backend.database.schemas import QuarantineCreate
from backend.layers.layer4_response.quarantine import QuarantineService
from backend.layers.layer0_bouncer.services import BouncerService
from backend.database.models import PolicyConfig

logger = setup_logger(__name__)

# Optional River ML import for Layer C
RIVER_AVAILABLE = False
try:
    from river import anomaly  # type: ignore
    RIVER_AVAILABLE = True
except Exception:
    RIVER_AVAILABLE = False

_ML_LOCK = threading.Lock()
_ML_MODEL = None
_ML_SEEN = 0

if RIVER_AVAILABLE:
    _ML_MODEL = anomaly.HalfSpaceTrees(
        n_trees=int(os.getenv("ARGUS_RIVER_TREES", "25")),
        height=int(os.getenv("ARGUS_RIVER_HEIGHT", "15")),
        window_size=int(os.getenv("ARGUS_RIVER_WINDOW", "250")),
        seed=int(os.getenv("ARGUS_RIVER_SEED", "42")),
    )

# In-memory latest results (safe start; DB persistence can come later)
LATEST_DECISIONS: Dict[str, Dict[str, Any]] = {}  # event_id -> payload
LATEST_LOCK = threading.Lock()


# ---- Policy Cache ----
_POLICY_CACHE = None
_POLICY_LAST_REFRESH = 0

def refresh_policy_cache():
    global _POLICY_CACHE, _POLICY_LAST_REFRESH
    if connection.SessionLocal is None:
        return
    try:
        db = connection.SessionLocal()
        policy = db.query(PolicyConfig).filter_by(id=1).first()
        if policy:
            _POLICY_CACHE = {
                "auto_response_enabled": policy.auto_response_enabled,
                "kill_on_alert": policy.kill_on_alert,
                "quarantine_on_warn": policy.quarantine_on_warn,
                "min_final_score_incident": policy.min_final_score_incident,
            }
            _POLICY_LAST_REFRESH = time.time()
    except Exception as e:
        logger.error(f"Failed to refresh policy cache: {e}")
    finally:
        if 'db' in locals() and db:
            db.close()


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def squash01(raw: float) -> float:
    # logistic squashing to [0,1]
    try:
        return clamp01(1.0 / (1.0 + math.exp(-raw)))
    except Exception:
        return 0.0


# ---- Helpers ----
def is_suspicious_extension(path: Optional[str]) -> bool:
    p = (path or "").lower()
    return p.endswith((
        ".exe", ".dll", ".sys", ".scr", ".com",
        ".ps1", ".psm1",
        ".vbs", ".js", ".jse", ".wsf", ".hta",
        ".bat", ".cmd", ".lnk",
        ".docm", ".xlsm", ".pptm",
    ))


# ---- Hashing ----
def sha256_file(path: str, max_bytes: int = 50 * 1024 * 1024) -> Optional[str]:
    """
    Best-effort SHA256, capped to max_bytes to avoid heavy reads.
    """
    try:
        if not path or not os.path.exists(path) or os.path.isdir(path):
            return None
        h = hashlib.sha256()
        read_total = 0
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                read_total += len(chunk)
                if read_total >= max_bytes:
                    break
        return h.hexdigest()
    except Exception:
        return None


# ---- Entropy ----
def shannon_entropy_bytes(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    ent = 0.0
    n = len(data)
    for c in freq:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def best_effort_file_entropy(path: str, max_bytes: int = 1024 * 1024) -> Optional[float]:
    try:
        if not path or not os.path.exists(path) or os.path.isdir(path):
            return None
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return float(shannon_entropy_bytes(data))
    except Exception:
        return None


# ---- Burst tracking (per process image) ----
_BURST_LOCK = threading.Lock()
_WRITES_BY_PROC = {}  # proc -> deque[timestamps]

def record_write(proc: str, ts: float, window_sec: float = 10.0) -> int:
    proc = (proc or "").lower()
    if not proc:
        return 0
    with _BURST_LOCK:
        q = _WRITES_BY_PROC.get(proc)
        if q is None:
            q = deque()
            _WRITES_BY_PROC[proc] = q
        q.append(ts)
        cutoff = ts - window_sec
        while q and q[0] < cutoff:
            q.popleft()
        return len(q)


# ---- Auto Response (Kill Process) ----
def try_kill_pid(pid: Optional[str]) -> bool:
    if not pid:
        return False
    try:
        # Windows taskkill (force)
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
        return True
    except Exception:
        return False


# ---- Auto Response (Quarantine) ----
def try_quarantine_path(
    original_path: Optional[str],
    detection_layer: str,
    confidence: float,
    session_id: Optional[str] = None,
    mitre_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Best-effort quarantine using Layer4 QuarantineService.
    Requires SessionLocal initialized via init_db().
    """
    if not original_path:
        return {"quarantined": False, "reason": "path_missing"}

    if connection.SessionLocal is None:
        return {"quarantined": False, "reason": "db_not_initialized"}

    file_hash = sha256_file(original_path)
    if not file_hash:
        return {"quarantined": False, "reason": "hash_failed"}

    db = connection.SessionLocal()
    try:
        qc = QuarantineCreate(
            original_path=original_path,
            hash_sha256=file_hash,
            detection_layer=detection_layer,
            confidence=float(confidence),
            session_id=session_id,
            mitre_stage=mitre_stage,
        )
        q = QuarantineService.quarantine_file(original_path, db, qc)
        return {
            "quarantined": True,
            "quarantine_id": getattr(q, "id", None),
            "original_path": original_path,
            "hash_sha256": file_hash,
            "quarantine_path": getattr(q, "quarantine_path", None),
            "status": getattr(q, "status", "QUARANTINED"),
        }
    except Exception as ex:
        # QuarantineService already rolls back on DatabaseError, but keep response informative
        try:
            db.rollback()
        except Exception:
            pass
        return {"quarantined": False, "reason": "exception", "error": str(ex), "hash_sha256": file_hash}
    finally:
        db.close()


# ---------------------------
# Layer A: Statistical
# ---------------------------
def score_layer_a(evt: TelemetryEvent) -> Dict[str, Any]:
    score = 0.0
    reasons = []

    # Layer A: Statistical Scoring (File & Registry Bursts)
    if (evt.kind == "FILE_CREATE" and evt.target_path) or (evt.kind == "REG_SET"):
        # 1. Entropy (File Only)
        if evt.kind == "FILE_CREATE" and evt.target_path:
            ent = best_effort_file_entropy(evt.target_path, max_bytes=int(os.getenv("ARGUS_ENTROPY_MAX_BYTES", "524288")))
            if ent is not None:
                evt.file_entropy = ent
                if ent >= 7.9:
                    score += 0.85
                    reasons.append(f"high_entropy={ent:.2f}")
                elif ent >= 7.2:
                    score += 0.50
                    reasons.append(f"mid_entropy={ent:.2f}")

        # 2. Activity Bursts (File or Registry)
        window = float(os.getenv("ARGUS_BURST_WINDOW", "10.0"))
        rate = record_write(evt.child_process or "system", evt.ts, window_sec=window)
        
        burst_threshold = 10 if evt.kind == "REG_SET" else 20
        if rate >= burst_threshold:
            score += 0.95
            reasons.append(f"behavioral_burst_{evt.kind}={rate}")
        elif rate >= (burst_threshold / 2):
            score += 0.60
            reasons.append(f"behavioral_spike_{evt.kind}={rate}")

    return {"score": clamp01(score), "reasons": reasons}


# ---------------------------
# Layer B: P-matrix
# ---------------------------
class PMatrixModel:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {}          # (parent, child) -> count
        self.parent_totals = {}   # parent -> total outgoing
        self.vocab_children = set()

    def update_and_score(self, parent: str, child: str) -> float:
        """
        Laplace-smoothed rarity score:
        probability = (count+1)/(total + |V|)
        rarity_score = 1 - probability
        """
        parent = (parent or "").lower()
        child = (child or "").lower()
        if not parent or not child:
            return 0.0

        with self.lock:
            key = (parent, child)
            self.counts[key] = self.counts.get(key, 0) + 1
            self.parent_totals[parent] = self.parent_totals.get(parent, 0) + 1
            self.vocab_children.add(child)

            c = self.counts[key]
            total = self.parent_totals[parent]
            V = max(1, len(self.vocab_children))

            prob = (c + 1.0) / (total + V)
            rarity = 1.0 - prob
            return clamp01(rarity)

P_MATRIX = PMatrixModel()

def score_layer_b(evt: TelemetryEvent) -> Dict[str, Any]:
    if evt.kind != "PROCESS_CREATE":
        return {"score": 0.0, "reasons": []}

    s = P_MATRIX.update_and_score(evt.parent_process or "", evt.child_process or "")
    reasons = []
    if s >= 0.7:
        reasons.append("rare_transition")
    return {"score": s, "reasons": reasons}


# ---------------------------
# Layer C: Online ML
# ---------------------------
def layer_c_features(evt: TelemetryEvent, a_score: float, b_score: float) -> Dict[str, float]:
    kind = evt.kind or ""
    child = (evt.child_process or "").lower()

    # A tiny feature set that is available now, without needing full graph features yet.
    # We can extend later with degree/depth/density once you compute them.
    return {
        "is_process_create": 1.0 if kind == "PROCESS_CREATE" else 0.0,
        "is_file_create": 1.0 if kind == "FILE_CREATE" else 0.0,
        "is_reg_set": 1.0 if kind == "REG_SET" else 0.0,
        "a_score": float(a_score),
        "b_score": float(b_score),
        "entropy": float(evt.file_entropy or 0.0),
        "child_is_cmd": 1.0 if child.endswith("\\cmd.exe") else 0.0,
        "child_is_powershell": 1.0 if child.endswith("\\powershell.exe") else 0.0,
    }

def score_layer_c(evt: TelemetryEvent, a_score: float, b_score: float) -> Dict[str, Any]:
    global _ML_SEEN

    if not RIVER_AVAILABLE or _ML_MODEL is None:
        return {"score": 0.0, "reasons": ["river_not_installed"]}

    feats = layer_c_features(evt, a_score=a_score, b_score=b_score)

    with _ML_LOCK:
        raw = float(_ML_MODEL.score_one(feats))
        _ML_MODEL.learn_one(feats)
        _ML_SEEN += 1

    return {"score": squash01(raw), "reasons": ["river_halfspacetrees"], "raw": raw, "seen": _ML_SEEN}


# ---------------------------
# Fusion
# ---------------------------
def fuse(a: float, b: float, c: float) -> Dict[str, Any]:
    a, b, c = clamp01(a), clamp01(b), clamp01(c)

    # hard override (strong confidence pattern)
    if b > 0.85 and c > 0.70:
        return {"decision": "MALWARE ALERT", "final_score": 1.0, "rule": "B>0.85 & C>0.70 override"}

    final = 0.4 * a + 0.3 * b + 0.3 * c

    if final >= 0.80:
        dec = "MALWARE ALERT"
    elif final >= 0.50:
        dec = "SUSPICIOUS"
    else:
        dec = "NORMAL"

    return {"decision": dec, "final_score": round(final, 3), "rule": "weighted_sum"}


def _child_is_lolbin(evt: TelemetryEvent) -> bool:
    child = (evt.child_process or "").lower()
    # basic LOLBins / shells
    for name in (
        "\\cmd.exe",
        "\\powershell.exe",
        "\\pwsh.exe",
        "\\wscript.exe",
        "\\cscript.exe",
        "\\mshta.exe",
        "\\rundll32.exe",
        "\\regsvr32.exe",
        "\\certutil.exe",
        "\\bitsadmin.exe",
    ):
        if child.endswith(name):
            return True
    return False


class Layer2RuntimeEngine:
    def __init__(self):
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pool = ThreadPoolExecutor(max_workers=3)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="Layer2RuntimeEngine", daemon=True)
        self._thread.start()
        logger.info("🟢 Layer2RuntimeEngine started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._pool.shutdown(wait=False)
        logger.info("🛑 Layer2RuntimeEngine stopped")

    def _run(self):
        global _ML_SEEN, _POLICY_LAST_REFRESH, _POLICY_CACHE

        warmup = int(os.getenv("ARGUS_ML_WARMUP_EVENTS", "500"))

        # fast path thresholds (immediate containment without waiting for ML warmup)
        fast_a = float(os.getenv("ARGUS_FAST_A_ALERT", "0.85"))
        fast_b = float(os.getenv("ARGUS_FAST_B_ALERT", "0.90"))

        while not self._stop.is_set():
            
            # Refresh policy every 5s
            if (time.time() - _POLICY_LAST_REFRESH) > 5 or _POLICY_CACHE is None:
                refresh_policy_cache()
            
            policy = _POLICY_CACHE or {
                "auto_response_enabled": False,
                "kill_on_alert": False,
                "quarantine_on_warn": True,
                "min_final_score_incident": 0.5
            }

            try:
                evt: TelemetryEvent = EVENT_QUEUE.get(timeout=0.5)
            except Exception:
                continue

            try:
                # A and B in parallel
                fa = self._pool.submit(score_layer_a, evt)
                fb = self._pool.submit(score_layer_b, evt)

                a = fa.result(timeout=1.0)
                b = fb.result(timeout=1.0)

                # Layer 0 Flagging Logic (cheap, synchronous check)
                layer0_flagged = False
                if evt.kind == "FILE_CREATE" and evt.target_path:
                    # Trigger Layer0 if suspicious extension
                    suspicious_ext = is_suspicious_extension(evt.target_path)

                    if suspicious_ext:
                        layer0_flagged = True
                    else:
                        # Otherwise trigger only if Layer A flagged entropy/burst
                        for r in (a.get("reasons") or []):
                            if (
                                r.startswith("high_entropy=")
                                or r.startswith("mid_entropy=")
                                or r.startswith("write_burst_")
                                or r.startswith("write_spike_")
                            ):
                                layer0_flagged = True
                                break
                
                layer0_result = None
                if layer0_flagged and evt.target_path:
                    db0 = None
                    try:
                        if connection.SessionLocal is not None:
                            db0 = connection.SessionLocal()
                        
                        try:
                            file_size = os.path.getsize(evt.target_path)
                        except Exception:
                            file_size = 0
                            
                        file_hash = sha256_file(evt.target_path)
                        
                        decision = BouncerService.bouncer_decision(
                            evt.target_path,
                            file_size,
                            vt_score=0.0,
                            db=db0,
                        )
                        
                        layer0_result = {
                            "flagged": True,
                            "decision": decision,
                            "file_size": file_size,
                            "hash_sha256": file_hash,
                            "vt_used": False,
                        }
                    except Exception as ex:
                        layer0_result = {"flagged": True, "error": str(ex)}
                    finally:
                        if db0:
                            db0.close()

                # C uses A/B
                c = score_layer_c(evt, a_score=a["score"], b_score=b["score"])

                fused = fuse(a["score"], b["score"], c["score"])
                
                # Apply Layer 0 overrides to fusion score/decision
                if layer0_result:
                    fused["layer0"] = layer0_result
                    
                    l0_status = layer0_result.get("decision", {}).get("status")
                    if l0_status in ("CRITICAL", "BLOCK"):
                        fused["decision"] = "MALWARE ALERT"
                        fused["final_score"] = 1.0
                        fused["rule"] = str(fused.get("rule", "")) + " + layer0_block_override"
                    elif l0_status == "WARN":
                        # Only upgrade to SUSPICIOUS if it wasn't already flagged higher
                        if fused.get("decision") == "NORMAL":
                            fused["decision"] = "SUSPICIOUS"
                        fused["final_score"] = max(float(fused.get("final_score", 0.0)), 0.50)
                        fused["rule"] = str(fused.get("rule", "")) + " + layer0_warn_override"

                # --- TACTICAL LOGGING (For Validation) ---
                if fused.get("final_score", 0) > 0.3:
                     print(f"\n[!] ARGUS DETECTION: {evt.kind} | Score: {fused.get('final_score')} | Decision: {fused.get('decision')}")
                     print(f"[!] Reasons: {a['reasons'] + b['reasons'] + c['reasons']}")
                
                # Auto-response logic
                ml_ready = (not RIVER_AVAILABLE) or (_ML_MODEL is None) or (_ML_SEEN >= warmup)

                should_kill = False
                killed = False
                err = None
                fast_path = False
                fast_reason = None
                
                if a["score"] >= fast_a:
                    fast_path = True
                    should_kill = True
                    fast_reason = "fast_path_A_high"
                
                # FORCE KILL for Registry Bursts (Override ML Warmup)
                if evt.kind == "REG_SET" and a["score"] >= 0.8:
                    should_kill = True
                    fast_path = True
                    fast_reason = "registry_burst_override"

                is_auto_response = policy.get("auto_response_enabled", False)
                is_kill_enabled = is_auto_response and policy.get("kill_on_alert", False)
                is_quarantine_enabled = is_auto_response and policy.get("quarantine_on_warn", False)
                
                if is_kill_enabled and should_kill:
                    pid = evt.child_pid
                    if pid:
                        print(f"🛑 [AUTO-RESPONSE] CRITICAL THREAT DETECTED. KILLING PID {pid}...")
                        try:
                            killed = IsolationService.kill_process(int(pid), force=True)
                            if killed: print(f"✅ [SUCCESS] PID {pid} HAS BEEN TERMINATED.")
                        except Exception as k_ex:
                            err = str(k_ex)
                            print(f"❌ [ERROR] Could not kill PID {pid}: {err}")
                    else:
                         err = "pid_missing"
                         print("⚠️ [AUTO-RESPONSE] Kill triggered but PID was missing.")

                quarantine_result = {"quarantined": False, "reason": "not_attempted"}
                
                if is_quarantine_enabled:
                    # If containment triggers (Layer2 fast path/ML) AND event contains a file path, quarantine it.
                    if should_kill and evt.target_path:
                        quarantine_result = try_quarantine_path(
                            original_path=evt.target_path,
                            detection_layer="Layer2_Containment",
                            confidence=1.0 if fused.get("decision") == "MALWARE ALERT" else 0.8,
                            session_id=evt.session_id,
                            mitre_stage=None,
                        )
                    # Or if Layer 0 Bouncer explicitly flags it
                    elif (
                        layer0_result 
                        and layer0_result.get("decision", {}).get("status") in ("WARN", "CRITICAL", "BLOCK") 
                        and evt.target_path 
                        and is_suspicious_extension(evt.target_path)
                    ):
                         quarantine_result = try_quarantine_path(
                            original_path=evt.target_path,
                            detection_layer="Layer0_Bouncer",
                            confidence=0.85 if layer0_result.get("decision", {}).get("status") == "WARN" else 0.95,
                            session_id=evt.session_id,
                            mitre_stage=None,
                        )

                fused["auto_response"] = {
                    "enabled": is_auto_response,
                    "action": "kill_child",
                    "should_kill": bool(is_kill_enabled and should_kill),
                    "killed": bool(killed),
                    "error": err,
                    "quarantine": quarantine_result,
                    "ml_ready": bool(ml_ready),
                    "warmup_events": warmup,
                    "ml_seen": _ML_SEEN,
                    "fast_path": bool(fast_path),
                    "fast_reason": fast_reason,
                    "child_pid": evt.child_pid,
                    "child_process": evt.child_process,
                    "child_cmd": evt.child_cmd,
                }

                payload = {
                    "event": to_dict(evt),
                    "scores": {"A": a, "B": b, "C": c},
                    "fusion": fused,
                    "ts": time.time(),
                }

                with LATEST_LOCK:
                    LATEST_DECISIONS[evt.event_id] = payload
                    if len(LATEST_DECISIONS) > 2000:
                        for k in list(LATEST_DECISIONS.keys())[:500]:
                            LATEST_DECISIONS.pop(k, None)

            except Exception:
                logger.exception("❌ Layer2RuntimeEngine event processing failed")



                
# parallel, non-blocking and safe because it doesn’t writes DB. 