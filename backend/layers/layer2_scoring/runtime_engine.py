# backend/layers/layer2_scoring/runtime_engine.py
import os
import math
import threading
import time
import subprocess
import hashlib
import warnings
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

warnings.filterwarnings("ignore", message="Field .* has conflict with protected namespace")

from backend.shared.logger import setup_logger
from backend.layers.layer2_scoring.event_stream import SCORING_QUEUE, TelemetryEvent, to_dict
from backend.layers.layer4_response.isolation import IsolationService

from backend.database import connection
from backend.database.schemas import QuarantineCreate
from backend.layers.layer4_response.quarantine import QuarantineService
from backend.layers.layer0_bouncer.services import BouncerService
from backend.database.models import PolicyConfig

logger = setup_logger(__name__)

RIVER_AVAILABLE = False
try:
    from river import anomaly
    RIVER_AVAILABLE = True
except Exception:
    RIVER_AVAILABLE = False

_ML_LOCK = threading.Lock()
_ML_MODEL = None
_ML_SEEN = 0

def load_trained_river_model():
    """Load the trained River model from BETH dataset."""
    global _ML_MODEL
    
    if not RIVER_AVAILABLE:
        return False
    
    model_path = "backend/ml/models/river_windows_baseline.pkl"  # Use Windows baseline
    
    try:
        import pickle
        with open(model_path, 'rb') as f:
            _ML_MODEL = pickle.load(f)
        return True
    except FileNotFoundError:
        # Fallback to fresh model if trained model not found
        _ML_MODEL = anomaly.HalfSpaceTrees(
            n_trees=int(os.getenv("ARGUS_RIVER_TREES", "25")),
            height=int(os.getenv("ARGUS_RIVER_HEIGHT", "15")),
            window_size=int(os.getenv("ARGUS_RIVER_WINDOW", "250")),
            seed=int(os.getenv("ARGUS_RIVER_SEED", "42")),
        )
        return False
    except Exception as e:
        # Fallback to fresh model on any error
        _ML_MODEL = anomaly.HalfSpaceTrees(
            n_trees=int(os.getenv("ARGUS_RIVER_TREES", "25")),
            height=int(os.getenv("ARGUS_RIVER_HEIGHT", "15")),
            window_size=int(os.getenv("ARGUS_RIVER_WINDOW", "250")),
            seed=int(os.getenv("ARGUS_RIVER_SEED", "42")),
        )
        return False

# DO NOT load the trained model at import time - causes startup hang!
# Model will be loaded lazily in Layer2RuntimeEngine._run() instead

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
    if not original_path:
        return {"quarantined": False, "reason": "path_missing"}

    safe_prefixes = [
        "c:\\windows",
        "c:\\program files",
        "c:\\program files (x86)",
        "d:\\applications",
    ]
    lower_path = original_path.lower()
    for prefix in safe_prefixes:
        if lower_path.startswith(prefix):
            return {"quarantined": False, "reason": "protected_system_path"}

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

# Layer A: Statistical
def score_layer_a(evt: TelemetryEvent) -> Dict[str, Any]:
    score = 0.0
    reasons = []

    # Layer A: Statistical Scoring (File & Registry Bursts + Process Entropy + Command Line)
    if (evt.kind == "FILE_CREATE" and evt.target_path) or (evt.kind == "REG_SET") or (evt.kind == "PROCESS_CREATE" and evt.child_process):
        
        # 0. COMMAND LINE ANALYSIS (for PROCESS_CREATE)
        if evt.kind == "PROCESS_CREATE" and evt.child_cmd:
            cmd = (evt.child_cmd or "").lower()
            
            # Malicious PowerShell patterns
            if "powershell" in (evt.child_process or "").lower():
                if any(pattern in cmd for pattern in [
                    "-executionpolicy bypass",
                    "-exec bypass",
                    "-ep bypass",
                    "downloadstring",
                    "downloadfile",
                    "invoke-webrequest",
                    "iwr",
                    "wget",
                    "curl",
                    "invoke-expression",
                    "iex",
                    "frombase64string",
                    "-encodedcommand",
                    "-enc",
                    "-windowstyle hidden",
                    "-w hidden",
                    "noprofile",
                ]):
                    score += 0.90
                    reasons.append("malicious_powershell_pattern")
            
            # Malicious cmd patterns
            if "cmd.exe" in (evt.child_process or "").lower():
                if any(pattern in cmd for pattern in [
                    "whoami",
                    "net user",
                    "net localgroup",
                    "tasklist",
                    "systeminfo",
                    "ipconfig /all",
                    "netstat",
                    "reg query",
                    "reg add",
                ]):
                    score += 0.70
                    reasons.append("reconnaissance_command")
        
        # 1. Entropy (File Only & Process Launch)
        file_to_check = evt.target_path if evt.kind == "FILE_CREATE" else (evt.child_process if evt.kind == "PROCESS_CREATE" else None)
        
        # Use provided entropy first, then try to read from disk
        ent = evt.file_entropy
        if ent is None and file_to_check:
            ent = best_effort_file_entropy(file_to_check, max_bytes=int(os.getenv("ARGUS_ENTROPY_MAX_BYTES", "524288")))
            if ent is not None:
                evt.file_entropy = ent
        
        if ent is not None:
            if ent >= 7.9:
                score += 0.85
                reasons.append(f"high_entropy={ent:.2f}")
            elif ent >= 7.2:
                score += 0.50
                reasons.append(f"mid_entropy={ent:.2f}")

        # 2. Activity Bursts (File or Registry)
        if evt.kind in ("FILE_CREATE", "REG_SET"):
            window = float(os.getenv("ARGUS_BURST_WINDOW", "10.0"))
            rate = record_write(evt.child_process or "system", evt.ts, window_sec=window)
            
            burst_threshold = 30 if evt.kind == "REG_SET" else 50
            if rate >= burst_threshold:
                score += 0.95
                reasons.append(f"behavioral_burst_{evt.kind}={rate}")
            elif rate >= (burst_threshold / 2):
                score += 0.60
                reasons.append(f"behavioral_spike_{evt.kind}={rate}")

    return {"score": clamp01(score), "reasons": reasons}

# Layer B: P-matrix
class PMatrixModel:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {}          # (parent, child) -> count
        self.parent_totals = {}   # parent -> total outgoing
        self.vocab_children = set()
        self.min_observations = int(os.getenv("PMATRIX_MIN_OBSERVATIONS", "10"))

    def update_and_score(self, parent: str, child: str) -> float:
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

            if total < self.min_observations:
                # Reduce score during learning phase
                warmup_factor = total / self.min_observations
                prob = (c + 1.0) / (total + V)
                rarity = 1.0 - prob
                return clamp01(rarity * warmup_factor)
            
            prob = (c + 1.0) / (total + V)
            rarity = 1.0 - prob
            return clamp01(rarity)

P_MATRIX = PMatrixModel()

def score_layer_b(evt: TelemetryEvent) -> Dict[str, Any]:
    if evt.kind != "PROCESS_CREATE":
        return {"score": 0.0, "reasons": []}

    parent = (evt.parent_process or "").lower()
    child = (evt.child_process or "").lower()
    
    parent_name = parent.split("\\")[-1] if "\\" in parent else parent
    child_name = child.split("\\")[-1] if "\\" in child else child
    
    # Trusted system paths - reduce score significantly
    trusted_paths = [
        "c:\\windows\\system32",
        "c:\\windows\\syswow64",
        "c:\\program files",
        "c:\\program files (x86)",
    ]
    
    child_is_trusted = any(child.startswith(path) for path in trusted_paths)
    parent_is_trusted = any(parent.startswith(path) for path in trusted_paths)
    
    # CRITICAL FIX: Only reduce score if BOTH are trusted AND it's a common spawn
    # Unusual spawns (notepad → cmd, calc → notepad) should still be flagged!
    common_system_spawns = [
        ("explorer.exe", "notepad.exe"),
        ("explorer.exe", "calc.exe"),
        ("svchost.exe", "dllhost.exe"),
        ("services.exe", "svchost.exe"),
    ]
    
    is_common_spawn = any(
        parent_name == p and child_name == c 
        for p, c in common_system_spawns
    )
    
    # Only give low score if it's a known common system spawn
    if child_is_trusted and parent_is_trusted and is_common_spawn:
        return {"score": 0.05, "reasons": ["trusted_system_path"]}
    
    # Self-spawn is usually legitimate
    if parent_name == child_name:
        return {"score": 0.1, "reasons": ["self_spawn"]}

    s = P_MATRIX.update_and_score(parent, child)
    
    # Reduce score for trusted child processes (only if common spawn)
    if child_is_trusted and is_common_spawn:
        s = s * 0.3
        
    reasons = []
    
    # BOOST SCORE for highly unusual spawns
    # Examples: notepad → cmd, calc → anything, malware.exe → calc
    unusual_parents = ["notepad.exe", "calc.exe", "mspaint.exe", "wordpad.exe"]
    lolbins = ["cmd.exe", "powershell.exe", "wscript.exe", "cscript.exe", "mshta.exe"]
    
    if any(up in parent_name for up in unusual_parents):
        if any(lb in child_name for lb in lolbins):
            s = max(s, 0.85)  # Force high score for unusual parent → LOLBin
            reasons.append("unusual_parent_to_lolbin")
        else:
            s = max(s, 0.70)  # Force medium-high score for unusual parent
            reasons.append("unusual_parent_spawn")
    
    # BOOST for unknown parent (not in system paths)
    if not parent_is_trusted and any(lb in child_name for lb in lolbins):
        s = max(s, 0.80)  # Unknown process spawning LOLBin
        reasons.append("unknown_parent_to_lolbin")
    
    # CRITICAL: Check command line for malicious patterns
    # Even if spawn is common (cmd → powershell), malicious command = high score
    cmd = (evt.child_cmd or "").lower()
    if cmd and any(lb in child_name for lb in lolbins):
        malicious_patterns = [
            "-executionpolicy bypass", "-exec bypass", "-ep bypass",
            "downloadstring", "downloadfile", "invoke-webrequest",
            "invoke-expression", "iex", "frombase64string",
            "-encodedcommand", "-enc", "-windowstyle hidden",
            "whoami", "net user", "net localgroup", "reg query", "reg add"
        ]
        if any(pattern in cmd for pattern in malicious_patterns):
            s = max(s, 0.85)  # Force high score for malicious command
            reasons.append("malicious_command_line")
    
    if s >= 0.7:
        if "rare_transition" not in reasons:
            reasons.append("rare_transition")
    return {"score": s, "reasons": reasons}

# Layer C: Online ML
def layer_c_features(evt: TelemetryEvent, a_score: float, b_score: float) -> Dict[str, float]:
    
    kind = evt.kind or ""
    child = (evt.child_process or "").lower()
    parent = (evt.parent_process or "").lower()
    cmd = (evt.child_cmd or "").lower()
    target_path = (evt.target_path or "").lower()
    
    # Basic event type features
    features = {
        "is_process_create": 1.0 if kind == "PROCESS_CREATE" else 0.0,
        "is_file_create": 1.0 if kind == "FILE_CREATE" else 0.0,
        "is_reg_set": 1.0 if kind == "REG_SET" else 0.0,
    }
    
    # Mathematical layer scores (critical for trained model)
    features.update({
        "a_score": float(a_score),
        "b_score": float(b_score),
        "entropy": float(evt.file_entropy or 0.0),
    })
    
    # Command line analysis (calculate first)
    cmd = (evt.child_cmd or "").lower()
    features.update({
        "cmd_has_base64": 1.0 if any(x in cmd for x in ["-enc", "base64", "frombase64"]) else 0.0,
        "cmd_has_download": 1.0 if any(x in cmd for x in ["downloadstring", "wget", "curl", "invoke-webrequest"]) else 0.0,
        "cmd_has_bypass": 1.0 if any(x in cmd for x in ["bypass", "unrestricted", "hidden", "windowstyle"]) else 0.0,
        "cmd_length": min(len(cmd) / 100.0, 10.0),
    })

    is_lolbin = ("powershell" in child) or ("cmd" in child)
    is_susp_cmd = (features["cmd_has_base64"] or features["cmd_has_download"] or features["cmd_has_bypass"] or features["cmd_length"] > 1.5)
    
    features.update({
        "is_suspicious_lolbin": 1.0 if is_lolbin and is_susp_cmd else 0.0,
        "child_is_cmd": 1.0 if "cmd.exe" in child and is_susp_cmd else 0.0,
        "child_is_powershell": 1.0 if "powershell" in child and is_susp_cmd else 0.0,
        "child_is_system32": 1.0 if "system32" in child else 0.0,
        "parent_is_explorer": 1.0 if "explorer.exe" in parent else 0.0,
        "parent_is_system": 1.0 if any(x in parent for x in ["system32", "windows"]) else 0.0,
    })
    
    features.update({
        "path_is_temp": 1.0 if any(x in target_path for x in ["temp", "tmp"]) else 0.0,
        "path_is_appdata": 1.0 if "appdata" in target_path else 0.0,
        "path_is_startup": 1.0 if "startup" in target_path else 0.0,
        "path_is_suspicious": 1.0 if any(x in target_path for x in ["programdata", "public"]) else 0.0,
    })
    
    # Entropy-based features (enhanced)
    entropy = evt.file_entropy or 0.0
    features.update({
        "entropy_high": 1.0 if entropy > 7.5 else 0.0,
        "entropy_medium": 1.0 if 6.0 <= entropy <= 7.5 else 0.0,
        "entropy_low": 1.0 if entropy < 6.0 else 0.0,
        "entropy_normalized": min(entropy / 8.0, 1.0),
    })
    
    # Combined risk indicators
    features.update({
        "combined_risk": min((a_score + b_score + (entropy / 8.0)) / 3.0, 1.0),
        "is_high_risk_combo": 1.0 if (a_score > 0.7 and entropy > 7.0) else 0.0,
    })
    
    return features

def score_layer_c(evt: TelemetryEvent, a_score: float, b_score: float) -> Dict[str, Any]:
    global _ML_SEEN

    if not RIVER_AVAILABLE or _ML_MODEL is None:
        return {"score": 0.0, "reasons": ["river_not_available"]}

    feats = layer_c_features(evt, a_score=a_score, b_score=b_score)
    
    # WHITELIST: Reduce ML scoring for legitimate processes
    child = (evt.child_process or "").lower()
    child_name = child.split("\\")[-1] if "\\" in child else child
    
    legitimate_apps = [
        # System processes
        "svchost.exe", "csrss.exe", "smss.exe", "wininit.exe",
        "services.exe", "lsass.exe", "spoolsv.exe", "conhost.exe",
        "dwm.exe", "winlogon.exe", "taskmgr.exe", "taskhost.exe",
        
        # Common applications
        "explorer.exe", "notepad.exe", "notepad++.exe",
        
        # Browsers
        "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe", 
        "opera.exe", "iexplore.exe",
        
        # Development tools
        "code.exe", "devenv.exe", "kiro.exe", "git.exe", 
        "node.exe", "npm.exe", "python.exe", "java.exe",
        
        # Communication
        "slack.exe", "teams.exe", "zoom.exe", "discord.exe",
        "skype.exe", "outlook.exe",
        
        # Utilities
        "winrar.exe", "7z.exe", "winzip.exe", "vlc.exe",
        "spotify.exe", "steam.exe",
        
        # Database & Servers
        "postgres.exe", "mysqld.exe", "mongod.exe", "redis-server.exe",
    ]
    
    is_legitimate = any(app in child_name for app in legitimate_apps)

    with _ML_LOCK:
        try:
            raw_river = float(_ML_MODEL.score_one(feats))
            
            river_contribution = clamp01(raw_river)

            math_avg = (a_score + b_score) / 2.0
            final_score = math_avg * 0.6 + river_contribution * 0.4
            
            _ML_MODEL.learn_one(feats)
            _ML_SEEN += 1
            
        except Exception as e:
            final_score = (a_score + b_score) / 2.0
            raw_river = 0.0
            river_contribution = 0.0

    final_score = clamp01(final_score)
    
    reasons = ["windows_baseline_model"]
    
    # WHITELIST: Reduce score for legitimate processes
    if is_legitimate:
        final_score = final_score * 0.5  # 50% reduction for known legitimate apps
        reasons.append("legitimate_process_reduction")
        
    if final_score > 0.8:
        reasons.append("high_risk_detected")
    elif final_score > 0.5:
        reasons.append("moderate_risk")
    else:
        reasons.append("low_risk")
    
    # Add specific detection reasons
    if feats.get("is_high_risk_combo", 0.0) > 0.5:
        reasons.append("high_entropy_with_math_scores")
    if feats.get("is_suspicious_lolbin", 0.0) > 0.5:
        reasons.append("suspicious_lolbin_execution")
    if feats.get("cmd_has_base64", 0.0) > 0.5:
        reasons.append("base64_encoding")
    
    return {
        "score": final_score, 
        "reasons": reasons, 
        "raw_river": raw_river,
        "river_contribution": river_contribution,
        "seen": _ML_SEEN,
        "model_type": "windows_baseline_model"
    }

# Fusion
def fuse(a: float, b: float, c: float) -> Dict[str, Any]:
    a, b, c = clamp01(a), clamp01(b), clamp01(c)

    # Get thresholds from environment (configurable to reduce false positives)
    override_a = float(os.getenv("FUSION_OVERRIDE_A_THRESHOLD", "0.80"))  # Lowered from 0.90
    override_b = float(os.getenv("FUSION_OVERRIDE_B_THRESHOLD", "0.85"))  # Lowered from 0.98
    override_c = float(os.getenv("FUSION_OVERRIDE_C_THRESHOLD", "0.80"))  # Lowered from 0.95
    
    malware_threshold = float(os.getenv("FUSION_MALWARE_THRESHOLD", "0.85"))  # Lowered from 0.95
    suspicious_threshold = float(os.getenv("FUSION_SUSPICIOUS_THRESHOLD", "0.65"))  # Lowered from 0.75

    # HIGH CONFIDENCE OVERRIDE: All 3 channels must agree VERY strongly
    if b > override_b and c > override_c and a > override_a:
        return {"decision": "MALWARE ALERT", "final_score": 1.0, "rule": "triple_high_override"}

    final = 0.4 * a + 0.3 * b + 0.3 * c
    
    # BOOST: If both A and B agree strongly (even without C), increase confidence
    if a >= 0.70 and b >= 0.70:
        boost = min(0.15, (a + b) / 10)  # Up to +0.15 boost
        final = min(final + boost, 1.0)

    if final >= malware_threshold:
        dec = "MALWARE ALERT"
    elif final >= suspicious_threshold:
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
        logger.info("Layer2RuntimeEngine started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._pool.shutdown(wait=False)
        logger.info("Layer2RuntimeEngine stopped")

    def _run(self):
        global _ML_SEEN, _POLICY_LAST_REFRESH, _POLICY_CACHE, _ML_MODEL

        warmup = int(os.getenv("ARGUS_ML_WARMUP_EVENTS", "500"))

        # fast path thresholds (immediate containment without waiting for ML warmup)
        fast_a = float(os.getenv("ARGUS_FAST_A_ALERT", "0.85"))
        fast_b = float(os.getenv("ARGUS_FAST_B_ALERT", "0.90"))
        fast_river = float(os.getenv("ARGUS_FAST_RIVER_ALERT", "0.90"))  # River fast-path

        # LAZY LOAD: Load ML model on first engine run (not at import time to avoid startup hang)
        if RIVER_AVAILABLE and _ML_MODEL is None:
            logger.info("Loading ML model on first run (lazy initialization)...")
            load_trained_river_model()

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
                evt: TelemetryEvent = SCORING_QUEUE.get(timeout=0.5)
                
                # FORCE LOG EVERY EVENT
                logger.info(f"[DEBUG] ===== EVENT RECEIVED =====")
                logger.info(f"[DEBUG] Kind: {evt.kind}")
                logger.info(f"[DEBUG] Child: {evt.child_process}")
                logger.info(f"[DEBUG] Parent: {evt.parent_process}")
                logger.info(f"[DEBUG] Cmd: {evt.child_cmd[:100] if evt.child_cmd else 'None'}")
                logger.info(f"[DEBUG] PID: {evt.child_pid}")
                
                # Only log high-priority events to reduce noise
                if evt.kind in ["PROCESS_CREATE"] and any(x in (evt.child_process or "").lower() for x in ["cmd.exe", "powershell", "wscript", "cscript"]):
                    logger.info(f"[ENGINE] Processing suspicious: {evt.kind} - {evt.child_process}")
            except Exception as e:
                # Don't silently ignore - log the error!
                if "timed out" not in str(e).lower():
                    logger.error(f"[ENGINE] Error getting event from queue: {e}")
                continue

            try:
                # A and B in parallel
                fa = self._pool.submit(score_layer_a, evt)
                fb = self._pool.submit(score_layer_b, evt)

                a = fa.result(timeout=1.0)
                b = fb.result(timeout=1.0)
                
                # Layer 0 Flagging Logic (cheap, synchronous check)
                layer0_flagged = False
                
                # Check BOTH file creation and process execution
                target_for_layer0 = evt.target_path or evt.child_process
                
                if target_for_layer0:
                    # Trigger Layer0 if suspicious extension
                    if is_suspicious_extension(target_for_layer0):
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
                if layer0_flagged and target_for_layer0:
                    db0 = None
                    try:
                        if connection.SessionLocal is not None:
                            db0 = connection.SessionLocal()
                        
                        try:
                            file_size = os.path.getsize(target_for_layer0)
                        except Exception:
                            file_size = 0
                            
                        file_hash = sha256_file(target_for_layer0)
                        
                        decision = BouncerService.bouncer_decision(
                            target_for_layer0,
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
                
                # Debug logging for all scored events (helps tune thresholds)
                if a["score"] > 0.3 or b["score"] > 0.3 or c["score"] > 0.3:
                    logger.info(f"[SCORING] {evt.kind} | {evt.child_process or evt.target_path}")
                    logger.info(f"   Layers: A={a['score']:.2f}, B={b['score']:.2f}, C={c['score']:.2f}")
                    logger.info(f"   Final: {fused.get('final_score'):.3f} → {fused.get('decision')}")
                
                # Enhanced logging for malware detection
                if fused.get("decision") == "MALWARE ALERT":
                    logger.error(f"🚨 MALWARE ALERT DETECTED!")
                    logger.error(f"   Process: {evt.child_process or evt.target_path}")
                    logger.error(f"   Session: {evt.session_id}")
                    logger.error(f"   Score: {fused.get('final_score'):.3f}")
                    logger.error(f"   Layers: A={a['score']:.2f}, B={b['score']:.2f}, C={c['score']:.2f}")
                elif fused.get("decision") == "SUSPICIOUS":
                    logger.warning(f"⚠️  SUSPICIOUS activity detected")
                    logger.warning(f"   Process: {evt.child_process or evt.target_path}")
                    logger.warning(f"   Session: {evt.session_id}")
                    logger.warning(f"   Score: {fused.get('final_score'):.3f}")
                
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

                # Only log significant detections to reduce noise
                if fused.get("final_score", 0) > 0.5:
                    logger.warning(f"[DETECTION] {evt.kind} | Score: {fused.get('final_score')} | Decision: {fused.get('decision')} | Process: {evt.child_process or evt.target_path}")
                    if fused.get("final_score", 0) > 0.7:
                        logger.warning(f"[REASONS] {a['reasons'] + b['reasons'] + c['reasons']}")
                
                # Auto-response logic
                ml_ready = (not RIVER_AVAILABLE) or (_ML_MODEL is None) or (_ML_SEEN >= warmup)

                should_kill = False
                killed = False
                err = None
                fast_path = False
                fast_reason = None
                
                if fused.get("decision") == "MALWARE ALERT":
                    should_kill = True
                    fast_reason = "fusion_malware_alert"
                
                river_score = c.get("raw_river", 0.0)
                
                if layer0_result and layer0_result.get("decision", {}).get("status") in ("CRITICAL", "BLOCK"):
                    should_kill = True
                    fast_path = True
                    fast_reason = "layer0_security_override"

                is_auto_response = policy.get("auto_response_enabled", False)
                is_kill_enabled = policy.get("kill_on_alert", False)
                is_quarantine_enabled = policy.get("quarantine_on_warn", True)
                
                # OPTION 2: Enable Quarantine + Suspend (Recommended)
                # Processes will be SUSPENDED (not killed)
                # Files will be QUARANTINED
                # IDE/Terminal processes are PROTECTED
                is_kill_enabled = True  # Enable (uses suspend, not kill)
                is_quarantine_enabled = True  # Enable quarantine
                
                logger.info(f"[AUTO-RESPONSE] Quarantine + Suspend ENABLED - Malware will be suspended and quarantined")
                
                # CRITICAL: Never auto-kill in development/testing environments
                # Auto-kill is DISABLED by default for safety
                # Only enable in production with careful testing
                
                # WHITELIST: Never auto-kill critical system processes
                safe_processes = [
                    "explorer.exe", "svchost.exe", "csrss.exe", "smss.exe", 
                    "wininit.exe", "services.exe", "lsass.exe", "spoolsv.exe", 
                    "conhost.exe", "winlogon.exe", "taskmgr.exe",
                    "python.exe", "postgres.exe", "node.exe", "chrome.exe",
                    "firefox.exe", "code.exe", "kiro.exe"
                ]
                
                # WHITELIST: Never kill shells spawned by development tools
                safe_parent_processes = [
                    "code.exe", "kiro.exe", "devenv.exe", "pycharm",
                    "idea", "webstorm", "rider", "goland",
                    "windowsterminal.exe", "conhost.exe"
                ]
                
                child_name = (evt.child_process or "").split("\\")[-1].lower()
                parent_name = (evt.parent_process or "").split("\\")[-1].lower()
                
                # Check if child is protected
                if child_name in safe_processes or any(app in child_name for app in safe_processes):
                    if should_kill:
                        logger.warning(f"🛡️  Protected process {child_name} flagged for kill but was spared.")
                    should_kill = False
                
                # Check if parent is a development tool (CRITICAL FIX)
                if any(safe_parent in parent_name for safe_parent in safe_parent_processes):
                    if should_kill:
                        logger.warning(f"🛡️  Process spawned by IDE/terminal ({parent_name}) was spared from kill.")
                    should_kill = False

                # Protect VS Code terminal integration
                child_cmd_lower = (evt.child_cmd or "").lower()
                if child_name in ["powershell.exe", "pwsh.exe", "cmd.exe"]:
                    if "vscode" in child_cmd_lower or "shellintegration" in child_cmd_lower or "kiro" in child_cmd_lower:
                        if should_kill:
                            logger.warning("🛡️  Protected IDE terminal shell from being killed.")
                        should_kill = False
                
                # SAFETY: Log kill attempts for review
                if should_kill:
                    logger.error(f"⚠️  AUTO-RESPONSE TRIGGERED: Process={child_name}, PID={evt.child_pid}, Parent={parent_name}")
                    logger.error(f"   Command: {evt.child_cmd[:100] if evt.child_cmd else 'N/A'}")
                    logger.error(f"   Score: {fused.get('final_score')}, Decision: {fused.get('decision')}")

                # IMPROVED: Suspend + Quarantine instead of Kill
                suspended = False
                if is_kill_enabled and should_kill:
                    pid = evt.child_pid
                    if pid:
                        try:
                            # SUSPEND the process first (safer than kill)
                            logger.error(f"🛑 SUSPENDING PROCESS: {child_name} (PID={pid})")
                            suspended = IsolationService.suspend_process(int(pid))
                            
                            if suspended:
                                logger.error(f"✅ Process SUSPENDED successfully: {child_name} (PID={pid})")
                                logger.info(f"   Process can be resumed with: IsolationService.resume_process({pid})")
                            else:
                                logger.error(f"❌ Failed to suspend process: {child_name} (PID={pid})")
                                # Fallback to kill only if suspend fails AND it's critical
                                if fused.get("final_score", 0) >= 0.95:
                                    logger.error(f"⚠️  CRITICAL THREAT - Attempting to KILL process")
                                    killed = IsolationService.kill_process(int(pid), force=True)
                                    if killed:
                                        logger.error(f"✅ Process KILLED: {child_name} (PID={pid})")
                                    else:
                                        logger.error(f"❌ Failed to kill process: {child_name} (PID={pid})")
                        except Exception as k_ex:
                            err = str(k_ex)
                            logger.error(f"❌ Exception during auto-response: {k_ex}")
                    else:
                         err = "pid_missing"
                         logger.error(f"❌ Cannot suspend/kill process: PID missing")

                quarantine_result = {"quarantined": False, "reason": "not_attempted"}
                
                if is_quarantine_enabled:
                    paths_to_check = []
                    if evt.target_path: paths_to_check.append(evt.target_path)
                    
                    if evt.child_process and "system32" not in evt.child_process.lower(): 
                        paths_to_check.append(evt.child_process)

                    # Only quarantine on HIGH confidence MALWARE_ALERT
                    for path in paths_to_check:
                        if fused.get("decision") == "MALWARE ALERT" and fused.get("final_score", 0) >= 0.85:
                            res = try_quarantine_path(
                                original_path=path,
                                detection_layer="Layer2_Containment",
                                confidence=fused.get("final_score", 0.8),
                                session_id=evt.session_id,
                                mitre_stage=None,
                            )
                            if res.get("quarantined"):
                                quarantine_result = res
                                break

                    # Layer0 override only on CRITICAL (not WARN)
                    if not quarantine_result.get("quarantined") and (
                        layer0_result 
                        and layer0_result.get("decision", {}).get("status") == "CRITICAL"
                        and evt.target_path 
                        and is_suspicious_extension(evt.target_path)
                    ):
                         quarantine_result = try_quarantine_path(
                            original_path=evt.target_path,
                            detection_layer="Layer0_Bouncer",
                            confidence=0.95,
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

                # Store results and create incident if needed
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

                # CREATE OR UPDATE INCIDENT FOR LAYER 5 LEARNING
                if connection.SessionLocal is not None and fused.get("final_score", 0) >= policy.get("min_final_score_incident", 0.5):
                    try:
                        from backend.database.models import Incident
                        from backend.shared.enums import Severity
                        
                        db = connection.SessionLocal()
                        
                        # Determine severity based on decision
                        if fused.get("decision") == "MALWARE ALERT":
                            severity = Severity.CRITICAL
                        elif fused.get("decision") == "SUSPICIOUS":
                            severity = Severity.WARNING
                        else:
                            severity = Severity.UNKNOWN
                        
                        # Check if incident already exists for this session
                        existing_incident = db.query(Incident).filter(Incident.session_id == evt.session_id).first()
                        
                        if existing_incident:
                            # Update existing incident if new severity is higher or confidence increased
                            severity_order = {"BENIGN": 0, "UNKNOWN": 1, "WARNING": 2, "CRITICAL": 3}
                            current_severity_level = severity_order.get(existing_incident.severity.value, 0)
                            new_severity_level = severity_order.get(severity.value, 0)
                            
                            if new_severity_level > current_severity_level:
                                existing_incident.severity = severity
                                logger.warning(f"🔺 Escalated incident {evt.session_id}: {existing_incident.severity.value} → {severity.value}")
                            
                            # Always update confidence to latest score
                            new_confidence = float(fused.get("final_score", 0))
                            if new_confidence > existing_incident.confidence:
                                existing_incident.confidence = new_confidence
                            
                            # Update narrative with latest event
                            existing_incident.narrative = f"{existing_incident.narrative}\n{evt.kind}: {evt.child_process or evt.target_path}"
                            
                            db.commit()
                            logger.info(f"✏️  Updated incident: {evt.session_id} (confidence={new_confidence:.2f})")
                        else:
                            # Create new incident record
                            incident = Incident(
                                session_id=evt.session_id,
                                confidence=float(fused.get("final_score", 0)),
                                severity=severity,
                                mitre_stage=None,
                                narrative=f"{evt.kind}: {evt.child_process or evt.target_path}",
                            )
                            
                            db.add(incident)
                            db.commit()
                            logger.warning(f"🚨 Created incident: {evt.session_id} ({severity.value}, confidence={incident.confidence:.2f})")
                        
                    except Exception as incident_error:
                        logger.error(f"❌ Failed to create/update incident: {incident_error}")
                        if 'db' in locals():
                            try:
                                db.rollback()
                            except:
                                pass
                    finally:
                        if 'db' in locals():
                            try:
                                db.close()
                            except:
                                pass

            except Exception:
                logger.exception("Layer2RuntimeEngine event processing failed")
                # Prevent rapid error loops
                time.sleep(0.1)



                
# parallel, non-blocking and safe because it doesn’t writes DB. 