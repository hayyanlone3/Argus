# backend/layers/layer2_scoring/runtime_engine.py
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

from shared.logger import setup_logger
from layers.layer2_scoring.event_stream import EVENT_QUEUE, TelemetryEvent, to_dict

logger = setup_logger(__name__)

# In-memory latest results (safe start; DB persistence can come later)
LATEST_DECISIONS: Dict[str, Dict[str, Any]] = {}  # event_id -> payload
LATEST_LOCK = threading.Lock()

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

# ---------------------------
# Layer A: Statistical
# ---------------------------
def score_layer_a(evt: TelemetryEvent) -> Dict[str, Any]:
    """
    Statistical anomaly: entropy + simple burst placeholders.
    For now: only uses entropy if provided; later we can compute entropy from file bytes/path.
    """
    score = 0.0
    reasons = []

    ent = evt.file_entropy
    if ent is not None:
        if ent >= 7.9:
            score += 0.6
            reasons.append(f"high_entropy={ent:.2f}")
        elif ent >= 7.2:
            score += 0.3
            reasons.append(f"mid_entropy={ent:.2f}")

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
# Layer C: Online ML (placeholder-safe)
# ---------------------------
def score_layer_c(evt: TelemetryEvent) -> Dict[str, Any]:
    """
    Safe placeholder that returns 0 until River model is wired in.
    This keeps the system stable while we add River next.
    """
    return {"score": 0.0, "reasons": ["ml_not_enabled_yet"]}

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
                # Parallel scoring (non-blocking ingestion is preserved because sysmon only enqueues)
                fa = self._pool.submit(score_layer_a, evt)
                fb = self._pool.submit(score_layer_b, evt)
                fc = self._pool.submit(score_layer_c, evt)

                a = fa.result(timeout=1.0)
                b = fb.result(timeout=1.0)
                c = fc.result(timeout=1.0)

                fused = fuse(a["score"], b["score"], c["score"])

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