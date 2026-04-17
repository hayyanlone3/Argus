# backend/layers/layer2_scoring/runtime_engine.py
import os
import math
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

from shared.logger import setup_logger
from layers.layer2_scoring.event_stream import EVENT_QUEUE, TelemetryEvent, to_dict
from layers.layer4_response.isolation import IsolationService

logger = setup_logger(__name__)

# Optional River ML import for Layer C
RIVER_AVAILABLE = False
try:
    from river import anomaly
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


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def squash01(raw: float) -> float:
    """
    Smoothly map unbounded-ish anomaly scores into [0,1]
    """
    try:
        # logistic squashing
        return clamp01(1.0 / (1.0 + math.exp(-raw)))
    except Exception:
        return 0.0


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


# ---------------------------
# Layer A: Statistical
# ---------------------------
def score_layer_a(evt: TelemetryEvent) -> Dict[str, Any]:
    score = 0.0
    reasons = []

    # Only meaningful for file activity initially
    if evt.kind == "FILE_CREATE" and evt.target_path:
        # Entropy from disk (real signal)
        ent = best_effort_file_entropy(evt.target_path, max_bytes=512 * 1024)
        if ent is not None:
            evt.file_entropy = ent  # attach for UI/other layers
            if ent >= 7.9:
                score += 0.65
                reasons.append(f"high_entropy={ent:.2f}")
            elif ent >= 7.2:
                score += 0.35
                reasons.append(f"mid_entropy={ent:.2f}")
            else:
                reasons.append(f"entropy={ent:.2f}")

        # Burst: many writes in short window by same process image
        rate = record_write(evt.child_process or "", evt.ts, window_sec=10.0)
        if rate >= 20:
            score += 0.35
            reasons.append(f"write_burst_10s={rate}")
        elif rate >= 10:
            score += 0.20
            reasons.append(f"write_spike_10s={rate}")

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

    # hard override
    if b > 0.7 and c > 0.7:
        return {"decision": "MALWARE ALERT", "final_score": 1.0, "rule": "B>0.7 & C>0.7 override"}

    final = 0.4 * a + 0.3 * b + 0.3 * c

    if final >= 0.75:
        dec = "MALWARE ALERT"
    elif final >= 0.50:
        dec = "SUSPICIOUS"
    else:
        dec = "NORMAL"

    return {"decision": dec, "final_score": round(final, 3), "rule": "weighted_sum"}


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
        while not self._stop.is_set():
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

                # C depends on A/B (features include them)
                c = score_layer_c(evt, a_score=a["score"], b_score=b["score"])

                fused = fuse(a["score"], b["score"], c["score"])

                # Auto Kill logic for MALWARE ALERT
                auto_kill = os.getenv("ARGUS_AUTO_KILL_ON_ALERT", "false").lower() == "true"
                warmup = int(os.getenv("ARGUS_ML_WARMUP_EVENTS", "200"))
                ml_ready = True
                
                # If River is present, require warmup
                if RIVER_AVAILABLE and _ML_MODEL is not None:
                    ml_ready = _ML_SEEN >= warmup
                
                if auto_kill and ml_ready and fused.get("decision") == "MALWARE ALERT":
                    pid = evt.child_pid
                    killed = False
                    err = None
                    if pid:
                        try:
                            killed = IsolationService.kill_process(int(pid), force=True)
                        except Exception as ex:
                            err = str(ex)
                
                    fused["auto_response"] = {
                        "action": "kill_child",
                        "enabled": True,
                        "ml_ready": ml_ready,
                        "warmup": warmup,
                        "child_pid": pid,
                        "child_process": evt.child_process,
                        "child_cmd": evt.child_cmd,
                        "killed": bool(killed),
                        "error": err,
                    }
                else:
                    fused["auto_response"] = {
                        "action": "kill_child",
                        "enabled": auto_kill,
                        "ml_ready": ml_ready,
                        "warmup": warmup,
                        "killed": False,
                    }

                payload = {
                    "event": to_dict(evt),
                    "scores": {"A": a, "B": b, "C": c},
                    "fusion": fused,
                    "ts": time.time(),
                }

                with LATEST_LOCK:
                    LATEST_DECISIONS[evt.event_id] = payload
                    # keep memory bounded
                    if len(LATEST_DECISIONS) > 2000:
                        # drop oldest (simple)
                        for k in list(LATEST_DECISIONS.keys())[:500]:
                            LATEST_DECISIONS.pop(k, None)

            except Exception:
                logger.exception("❌ Layer2RuntimeEngine event processing failed")

# parallel, non-blocking and safe because it doesn’t writes DB. 