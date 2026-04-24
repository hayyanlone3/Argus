import os
import math
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from backend.database.models import Edge, Node
from backend.shared.enums import EdgeType, NodeType, Severity
from backend.shared.logger import setup_logger
from backend.shared.audit import AuditLogger

logger = setup_logger(__name__)

# Extensions that commonly matter for malware/ransomware workflows
SUSPICIOUS_EXTENSIONS = {
    ".exe", ".dll", ".sys", ".scr", ".msi",
    ".ps1", ".psm1", ".vbs", ".js", ".jse",
    ".bat", ".cmd", ".hta", ".lnk",
}

# Path fragments that often represent high-risk write locations
RISKY_PATH_FRAGMENTS = [
    r"\appdata\local\temp",
    r"\appdata\roaming",
    r"\programdata",
    r"\users\public",
    r"\microsoft\windows\start menu\programs\startup",
]


def _shannon_entropy_from_bytes(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    ent = 0.0
    for c in freq:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent  # 0..8


def _file_entropy(path: str, max_bytes: int) -> Optional[float]:
    """
    Best-effort entropy for small files.
    Returns None if file missing/too large/unreadable.
    """
    try:
        if not path or not os.path.isfile(path):
            return None
        size = os.path.getsize(path)
        if size <= 0:
            return 0.0
        if size > max_bytes:
            return None

        with open(path, "rb") as f:
            data = f.read()  # <= max_bytes
        return _shannon_entropy_from_bytes(data)
    except Exception:
        return None


def _path_risk(path: Optional[str]) -> float:
    if not path:
        return 0.0
    p = path.lower()
    for frag in RISKY_PATH_FRAGMENTS:
        if frag in p:
            return 1.0
    return 0.0


def _extension_risk(path: Optional[str]) -> float:
    if not path:
        return 0.0
    ext = os.path.splitext(path)[1].lower()
    return 1.0 if ext in SUSPICIOUS_EXTENSIONS else 0.0


def _severity_from_score(score: float) -> Severity:
    # Simple mapping for demo/plan milestone
    if score >= 0.75:
        return Severity.CRITICAL
    if score >= 0.50:
        return Severity.WARNING
    if score >= 0.25:
        return Severity.UNKNOWN
    return Severity.BENIGN


class AutoScoringService:
    """
    Minimal automatic scoring for Layer 2:
    - Only scores WROTE edges (safe start)
    - Updates Edge scoring columns
    - Writes audit trail
    """

    @staticmethod
    def score_edge(db: Session, edge_id: int, *, max_file_bytes: int = 10 * 1024 * 1024) -> Optional[Edge]:
        edge = db.query(Edge).filter(Edge.id == edge_id).first()
        if not edge:
            return None

        # Avoid re-scoring if already scored
        if edge.final_severity is not None:
            return edge

        # Score both file writes AND process executions
        if edge.edge_type not in (EdgeType.WROTE, EdgeType.SPAWNED):
            return edge

        target = db.query(Node).filter(Node.id == edge.target_id).first()
        if not target:
            return edge

        # We only expect FILE targets for WROTE
        file_path = target.path
        pr = _path_risk(file_path)         # 0 or 1
        er = _extension_risk(file_path)    # 0 or 1
        ent = _file_entropy(file_path, max_file_bytes)

        # Base score
        score = 0.10

        # Risky locations + suspicious extensions are strong signals
        if pr > 0:
            score += 0.40
        if er > 0:
            score += 0.35

        # Entropy high => likely encrypted/packed content (best-effort)
        if ent is not None and ent >= 7.2:
            score += 0.25

        # Clamp
        score = max(0.0, min(1.0, score))
        
        # HEURISTIC OVERRIDE: Filename pattern match
        if file_path and "malware" in file_path.lower():
            score = 1.0
            logger.warning(f"  HEURISTIC MATCH in AutoScoring for: {file_path}")

        sev = _severity_from_score(score)

        edge.anomaly_score = float(score)
        edge.entropy_value = float(ent) if ent is not None else None
        edge.final_severity = sev

        # Optional: store a lightweight note in edge_metadata
        md = edge.edge_metadata or {}
        md.update({
            "layer2_auto_scored": True,
            "path_risk": pr,
            "extension_risk": er,
            "entropy_computed": ent is not None,
        })
        edge.edge_metadata = md

        db.commit()
        db.refresh(edge)

        # Audit trail (best-effort; should not break scoring)
        try:
            AuditLogger.log(
                db,
                source="layer2.scoring",
                action="edge_scored",
                level="INFO",
                message=f"Scored edge_id={edge.id} severity={sev.value} score={score:.3f}",
                entity_type="edge",
                entity_id=edge.id,
                session_id=edge.session_id,
                path=file_path,
                hash_sha256=target.hash_sha256,
                payload={
                    "edge_type": edge.edge_type.value,
                    "score": score,
                    "severity": sev.value,
                    "entropy": ent,
                    "path_risk": pr,
                    "extension_risk": er,
                },
                commit=True,
            )
        except Exception:
            # Don’t fail the request if audit logging fails
            pass

        return edge