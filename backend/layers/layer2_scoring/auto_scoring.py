import os
import math
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from backend.database.models import Edge, Node
from backend.shared.enums import EdgeType, NodeType, Severity
from backend.shared.logger import setup_logger
from backend.layers.layer2_scoring.scoring import ScoringEngine

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
    # Aggressive thresholds for malware detection
    if score >= 0.35:
        return Severity.CRITICAL
    if score >= 0.20:
        return Severity.WARNING
    if score >= 0.10:
        return Severity.UNKNOWN
    return Severity.BENIGN


def _score_p_matrix(edge: Edge, source: Node | None, target: Node | None) -> tuple[float, dict]:
    """
    Score registry/service persistence behavior for Channel 2B.
    Returns a score plus compact metadata for diagnostics.
    """
    edge_kind = edge.edge_type.value if hasattr(edge.edge_type, "value") else str(edge.edge_type)
    metadata = edge.edge_metadata or {}
    registry_path = (
        metadata.get("reg_target")
        or metadata.get("target_path")
        or (target.path if target else None)
        or ""
    )
    command_line = (
        metadata.get("child_cmd")
        or metadata.get("parent_cmd")
        or ""
    )

    score, details = 0.0, {"matched": False, "rules": []}

    if edge.edge_type == EdgeType.MODIFIED_REG:
        score, details = ScoringEngine.score_channel_2b(
            edge_entropy=0.0,
            registry_path=registry_path,
            edge_type=edge_kind,
            command_line=command_line,
            edge_metadata=metadata,
        )
        return score, details

    if edge.edge_type == EdgeType.SPAWNED:
        service_keywords = [
            "new-service", "sc create", "schtasks", "bitsadmin",
            "reg add", "regsvr32", "mshta", "wmic",
            "control_rundll", "rundll32",
        ]
        matched = [keyword for keyword in service_keywords if keyword in command_line.lower()]
        if matched:
            score = 0.62
            if any(keyword in command_line.lower() for keyword in ["new-service", "sc create"]):
                score = 0.75
            details = {
                "matched": True,
                "rules": matched,
                "registry_path": registry_path or None,
                "edge_type": edge_kind,
            }
            return score, details

    # File writes into common persistence locations are also part of the p-matrix.
    if edge.edge_type == EdgeType.WROTE:
        path = (registry_path or "").lower()
        if any(fragment in path for fragment in [
            r"\appdata\roaming",
            r"\appdata\local\temp",
            r"\programdata",
            r"\users\public",
            r"\start menu\programs\startup",
        ]):
            score = 0.55
            details = {
                "matched": True,
                "rules": ["risky_drop_location"],
                "registry_path": registry_path,
                "edge_type": edge_kind,
            }
            return score, details

    return score, details


class AutoScoringService:
    """
    Automatic scoring for Layer 2:
    - Scores WROTE, SPAWNED, MODIFIED_REG, EXECUTED_SCRIPT edges
    - Updates Edge scoring columns
    - NO audit logging for speed
    """

    @staticmethod
    def score_edge(db: Session, edge_id: int, *, max_file_bytes: int = 10 * 1024 * 1024) -> Optional[Edge]:
        edge = db.query(Edge).filter(Edge.id == edge_id).first()
        if not edge:
            return None

        # Avoid re-scoring if already scored
        if edge.final_severity is not None:
            return edge

        # Score multiple edge types
        if edge.edge_type not in (EdgeType.WROTE, EdgeType.SPAWNED, EdgeType.MODIFIED_REG, EdgeType.EXECUTED_SCRIPT):
            return edge

        target = db.query(Node).filter(Node.id == edge.target_id).first()
        source = db.query(Node).filter(Node.id == edge.source_id).first()
        
        if not target:
            return edge

        # Initialize scoring variables
        file_path = target.path
        process_name = source.name if source else None
        pr = _path_risk(file_path)
        er = _extension_risk(file_path)
        ent = _file_entropy(file_path, max_file_bytes)

        # Base score
        score = 0.10

        # === EDGE TYPE SPECIFIC SCORING ===
        
        if edge.edge_type == EdgeType.MODIFIED_REG:
            # Registry modification - check for persistence keys
            reg_path = file_path.lower() if file_path else ""
            persistence_keys = ["run", "runonce", "services", "winlogon", "userinit", "shell"]
            
            if any(key in reg_path for key in persistence_keys):
                score += 0.60
            else:
                score += 0.30

            p_matrix_score, p_matrix_details = _score_p_matrix(edge, source, target)
            edge.p_matrix_score = float(p_matrix_score)
            if p_matrix_score > 0:
                score = max(score, p_matrix_score)
                md = edge.edge_metadata or {}
                md.update({
                    "p_matrix_score": p_matrix_score,
                    "p_matrix_rules": p_matrix_details.get("rules", []),
                })
                edge.edge_metadata = md
        
        elif edge.edge_type == EdgeType.EXECUTED_SCRIPT:
            # Script execution - PowerShell, VBScript, etc.
            score += 0.50
        
        elif edge.edge_type == EdgeType.SPAWNED:
            # Process spawning - check for suspicious processes
            process_lower = (target.name or "").lower()
            parent_lower = (source.name or "").lower()
            cmd_line = ""
            if edge.edge_metadata:
                cmd_line = (edge.edge_metadata.get("child_cmd") or edge.edge_metadata.get("parent_cmd") or "").lower()

            p_matrix_score, p_matrix_details = _score_p_matrix(edge, source, target)
            if p_matrix_score > 0:
                edge.p_matrix_score = float(p_matrix_score)
                score = max(score, p_matrix_score)
                md = edge.edge_metadata or {}
                md.update({
                    "p_matrix_score": p_matrix_score,
                    "p_matrix_rules": p_matrix_details.get("rules", []),
                })
                edge.edge_metadata = md
            
            # WHITELIST: Trusted parent processes spawning shells is LEGITIMATE
            trusted_parents = [
                "kiro.exe", "code.exe", "opencode.exe", "devenv.exe",
                "pycharm", "idea", "webstorm", "rider", "goland", "clion",
                "windowsterminal.exe", "wt.exe", "explorer.exe", "conhost.exe"
            ]
            
            is_trusted_parent = any(tp in parent_lower for tp in trusted_parents)
            is_shell = any(sh in process_lower for sh in ["cmd.exe", "powershell.exe", "pwsh.exe"])
            
            # If trusted parent spawning shell, check command line for malicious patterns
            if is_trusted_parent and is_shell:
                # Only flag if MALICIOUS command patterns present
                malicious_patterns = [
                    "downloadstring", "invoke-webrequest", "iwr ",
                    "invoke-expression", "iex(", "iex ",
                    "frombase64string", "-encodedcommand", "-enc ",
                    "new-object net.webclient", "curl ", "wget "
                ]
                
                has_malicious = any(p in cmd_line for p in malicious_patterns)
                
                if not has_malicious:
                    # Legitimate IDE/terminal spawn - minimal score
                    score = 0.05
                    sev = Severity.BENIGN
                    edge.anomaly_score = float(score)
                    edge.entropy_value = float(ent) if ent is not None else None
                    edge.final_severity = sev
                    
                    md = edge.edge_metadata or {}
                    md.update({
                        "layer2_auto_scored": True,
                        "path_risk": pr,
                        "extension_risk": er,
                        "whitelist_reason": "trusted_parent_legitimate_spawn"
                    })
                    edge.edge_metadata = md
                    db.commit()
                    db.refresh(edge)
                    return edge
            
            suspicious_processes = {
                "cmd.exe": 0.40,  # Increased from 0.35
                "powershell.exe": 0.50,  # Increased from 0.45
                "pwsh.exe": 0.50,
                "wscript.exe": 0.55,  # Increased from 0.50
                "cscript.exe": 0.55,
                "rundll32.exe": 0.45,  # Increased from 0.40
                "regsvr32.exe": 0.45,
                "mshta.exe": 0.55,
                "certutil.exe": 0.50,
                "bitsadmin.exe": 0.50,
            }
            
            for proc, proc_score in suspicious_processes.items():
                if proc in process_lower:
                    score += proc_score
                    break
            
            # Check command line for suspicious patterns
            cmd_line = ""
            if edge.edge_metadata:
                cmd_line = (edge.edge_metadata.get("child_cmd") or "").lower()
            
            if cmd_line:
                suspicious_patterns = {
                    "-noprofile": 0.25,
                    "-encodedcommand": 0.40,
                    "-enc": 0.40,
                    "-w hidden": 0.30,
                    "-windowstyle hidden": 0.30,
                    "invoke-expression": 0.35,
                    "iex": 0.35,
                    "downloadstring": 0.40,
                    "downloadfile": 0.40,
                    "bypass": 0.30,
                    "base64": 0.30,
                }
                
                for pattern, pattern_score in suspicious_patterns.items():
                    if pattern in cmd_line:
                        score += pattern_score
        
        elif edge.edge_type == EdgeType.WROTE:
            # File write - check for legitimate IDE/app writes first
            parent_lower = (source.name or "").lower()
            file_path_lower = (file_path or "").lower()
            
            # WHITELIST: Trusted applications writing to their own directories
            trusted_app_writes = [
                ("kiro.exe", "\\kiro\\"),
                ("code.exe", "\\code\\"),
                ("opencode.exe", "\\opencode\\"),
                ("chrome.exe", "\\chrome\\"),
                ("firefox.exe", "\\firefox\\"),
                ("msedge.exe", "\\microsoft\\edge\\"),
                ("explorer.exe", "\\microsoft\\windows\\"),
                ("svchost.exe", "\\microsoft\\windows\\"),
            ]
            
            is_legitimate_write = False
            for app, app_dir in trusted_app_writes:
                if app in parent_lower and app_dir in file_path_lower:
                    is_legitimate_write = True
                    break
            
            if is_legitimate_write:
                # Legitimate app writing to its own directory
                score = 0.05
                sev = Severity.BENIGN
                edge.anomaly_score = float(score)
                edge.entropy_value = float(ent) if ent is not None else None
                edge.final_severity = sev
                
                md = edge.edge_metadata or {}
                md.update({
                    "layer2_auto_scored": True,
                    "path_risk": pr,
                    "extension_risk": er,
                    "whitelist_reason": "trusted_app_legitimate_write"
                })
                edge.edge_metadata = md
                db.commit()
                db.refresh(edge)
                return edge
            
            # File write - original logic for non-whitelisted writes
            if pr > 0:
                score += 0.40
            if er > 0:
                score += 0.35
            
            # Entropy high => likely encrypted/packed content
            if ent is not None and ent >= 7.2:
                score += 0.25

        # Clamp
        score = max(0.0, min(1.0, score))
        
        # === BEHAVIORAL ANALYSIS ===
        
        # Check for rapid process spawning (multiple spawns in short time)
        if edge.edge_type == EdgeType.SPAWNED and edge.session_id:
            try:
                from datetime import timedelta
                recent_spawns = db.query(Edge).filter(
                    Edge.session_id == edge.session_id,
                    Edge.edge_type == EdgeType.SPAWNED,
                    Edge.timestamp >= edge.timestamp - timedelta(seconds=10)
                ).count()
                
                if recent_spawns >= 3:
                    score += 0.30
            except Exception:
                pass
        
        sev = _severity_from_score(score)

        edge.anomaly_score = float(score)
        edge.entropy_value = float(ent) if ent is not None else None
        edge.final_severity = sev
        if edge.p_matrix_score is None:
            edge.p_matrix_score = 0.0

        # Log detection immediately (console only, no DB)
        if sev in (Severity.CRITICAL, Severity.WARNING):
            logger.warning(f"[AUTO-SCORE] 🚨 {sev.value} | {edge.edge_type.value} | Score: {score:.2f} | {file_path or process_name}")

        # Store lightweight metadata
        md = edge.edge_metadata or {}
        md.update({
            "layer2_auto_scored": True,
            "path_risk": pr,
            "extension_risk": er,
        })
        edge.edge_metadata = md

        # Single commit - no audit logging for speed
        db.commit()
        db.refresh(edge)

        return edge
