import os
from sqlalchemy.orm import Session
from backend.database.models import Edge, Node
from backend.shared.enums import Severity
from backend.shared.logger import setup_logger
from backend.shared.constants import (
    SUSPICIOUS_FILE_PATH_FRAGMENTS,
    SUSPICIOUS_FILE_EXTENSIONS,
    SPAWN_RATE_SIGMA,
    RENAME_BURST_THRESHOLD,
    EDGE_BURST_SIGMA,
    ML_THRESHOLD_HIGH,
    ML_THRESHOLD_MEDIUM,
    ML_THRESHOLD_LOW,
)
from backend.config import settings
import numpy as np
from scipy import stats
from typing import Optional

logger = setup_logger(__name__)


class ScoringEngine:
    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        return (value or "").replace("/", "\\").lower()

    @staticmethod
    def _score_registry_signal(registry_path: Optional[str], edge_type: Optional[str] = None, command_line: Optional[str] = None) -> tuple:
        path = ScoringEngine._normalize_text(registry_path)
        edge_kind = (edge_type or "").upper()
        cmd = (command_line or "").lower()

        if not path and not cmd and not edge_kind:
            return 0.0, {"matched": False, "reason": "no_registry_context"}

        score = 0.0
        matched_rules = []

        high_risk_paths = {
            r"hkcu\software\microsoft\windows\currentversion\run": 0.90,
            r"hkcu\software\microsoft\windows\currentversion\runonce": 0.90,
            r"hklm\software\microsoft\windows\currentversion\run": 0.94,
            r"hklm\software\microsoft\windows\currentversion\runonce": 0.94,
            r"hklm\system\currentcontrolset\services": 0.97,
            r"hkcu\software\microsoft\windows nt\currentversion\winlogon": 0.96,
            r"hklm\software\microsoft\windows nt\currentversion\image file execution options": 0.99,
            r"hkcu\software\microsoft\windows nt\currentversion\windows": 0.85,
        }

        for needle, weight in high_risk_paths.items():
            if needle in path:
                score = max(score, weight)
                matched_rules.append(needle)

        service_keywords = ["sc create", "new-service", "create service", "imagepath", "start= auto", "starttype automatic"]
        for keyword in service_keywords:
            if keyword in cmd:
                score = min(1.0, score + 0.18)
                matched_rules.append(keyword)

        rare_tool_keywords = ["regsvr32", "mshta", "rundll32", "wmic", "schtasks", "bitsadmin"]
        for keyword in rare_tool_keywords:
            if keyword in cmd:
                score = min(1.0, score + 0.12)
                matched_rules.append(keyword)

        if edge_kind == "MODIFIED_REG":
            score = min(1.0, score + 0.15)
            matched_rules.append("modified_reg_edge")

        if edge_kind == "SPAWNED" and any(keyword in cmd for keyword in ["reg add", "sc create", "schtasks", "bitsadmin"]):
            score = min(1.0, score + 0.20)
            matched_rules.append("spawned_persistence_helper")

        if len(matched_rules) >= 3:
            score = min(1.0, score + 0.10)

        return score, {
            "matched": bool(matched_rules),
            "rules": matched_rules,
            "registry_path": path or None,
            "edge_type": edge_kind or None,
        }

    @staticmethod
    def _score_file_signal(file_path: Optional[str], edge_entropy: float = 0.0, edge_type: Optional[str] = None) -> tuple:
        path = ScoringEngine._normalize_text(file_path)
        edge_kind = (edge_type or "").upper()

        if not path:
            return 0.0, {"matched": False, "reason": "no_file_path"}

        score = 0.0
        matched_rules = []

        for fragment in SUSPICIOUS_FILE_PATH_FRAGMENTS:
            if fragment in path:
                score = max(score, 0.60)
                matched_rules.append(fragment)

        file_ext = os.path.splitext(path)[1].lower()
        if file_ext in SUSPICIOUS_FILE_EXTENSIONS:
            score = max(score, 0.55)
            matched_rules.append(file_ext)

        if edge_kind == "FILE_CREATE":
            score = min(1.0, score + 0.15)
            matched_rules.append("file_create_edge")

        if file_ext == ".dll" and any(fragment in path for fragment in SUSPICIOUS_FILE_PATH_FRAGMENTS):
            score = max(score, 0.95)
            matched_rules.append("dll_in_suspicious_location")

        if edge_entropy >= 7.9:
            score = max(score, 0.98)
            matched_rules.append("high_entropy")
        elif edge_entropy >= 7.2:
            score = max(score, 0.80)
            matched_rules.append("mid_entropy")

        return score, {
            "matched": bool(matched_rules),
            "rules": matched_rules,
            "file_path": path,
            "edge_type": edge_kind or None,
        }

    # CHANNEL 2A: MATH CERTAINTY
    @staticmethod
    def calculate_spawn_rate_anomaly(db: Session, process_node_id: int) -> tuple:
        try:
            # Count children spawned by this process
            spawned_edges = db.query(Edge).filter(
                Edge.source_id == process_node_id,
                Edge.edge_type == "SPAWNED"
            ).count()
            
            # Get baseline from similar processes
            # For now: use simple threshold
            baseline_mean = 1.0  # Average process spawns 1 child
            baseline_std = 0.5
            
            # Z-score
            z_score = (spawned_edges - baseline_mean) / baseline_std if baseline_std > 0 else 0
            
            is_anomalous = abs(z_score) > SPAWN_RATE_SIGMA
            score = min(abs(z_score) / SPAWN_RATE_SIGMA, 1.0)  # Normalize to 0-1
            
            if is_anomalous:
                logger.info(f"Spawn rate anomaly: {spawned_edges} children (z={z_score:.2f})")
            
            return (is_anomalous, score, f"spawned {spawned_edges} processes")
        
        except Exception as e:
            logger.error(f"Failed to calculate spawn rate: {e}")
            return (False, 0.0, "error")
    
    @staticmethod
    def calculate_rename_burst(db: Session, source_node_id: int) -> tuple:
        try:
            # Get all WROTE edges from source
            wrote_edges = db.query(Edge).filter(
                Edge.source_id == source_node_id,
                Edge.edge_type == "WROTE"
            ).all()
            
            if not wrote_edges:
                return (False, 0.0, "no writes")
            
            # Count renames (hardcoded heuristic: path changes with same parent)
            total_writes = len(wrote_edges)
            rename_count = 0
            
            for edge in wrote_edges:
                # Get target file path
                target = db.query(Node).filter(Node.id == edge.target_id).first()
                if target and target.path:
                    # Heuristic: if path contains temp names, likely rename
                    if any(x in target.path.lower() for x in ['.tmp', '.bak', '.old', '~']):
                        rename_count += 1
            
            rename_ratio = rename_count / total_writes if total_writes > 0 else 0
            is_anomalous = rename_ratio > RENAME_BURST_THRESHOLD
            
            if is_anomalous:
                logger.info(f"Rename burst: {rename_ratio:.1%} of {total_writes} writes")
            
            return (is_anomalous, rename_ratio, f"{rename_ratio:.1%} rename burst")
        
        except Exception as e:
            logger.error(f"Failed to calculate rename burst: {e}")
            return (False, 0.0, "error")
    
    @staticmethod
    def calculate_edge_burst(db: Session, source_node_id: int) -> tuple:
        try:
            from datetime import datetime, timedelta
            
            # Get edges created in last minute
            cutoff_time = datetime.utcnow() - timedelta(minutes=1)
            recent_edges = db.query(Edge).filter(
                Edge.source_id == source_node_id,
                Edge.timestamp >= cutoff_time
            ).count()
            
            # Baseline: normal process creates ~1-2 edges per minute
            baseline_mean = 1.5
            baseline_std = 0.5
            
            z_score = (recent_edges - baseline_mean) / baseline_std if baseline_std > 0 else 0
            is_anomalous = abs(z_score) > EDGE_BURST_SIGMA
            score = min(abs(z_score) / EDGE_BURST_SIGMA, 1.0)
            
            if is_anomalous:
                logger.info(f"Edge burst: {recent_edges} edges in 1 minute (z={z_score:.2f})")
            
            return (is_anomalous, score, f"{recent_edges} edges/min burst")
        
        except Exception as e:
            logger.error(f"Failed to calculate edge burst: {e}")
            return (False, 0.0, "error")
    
    @staticmethod
    def score_channel_2a(db: Session, source_node_id: int) -> float:
        try:
            # Get individual signals
            spawn_anomaly, spawn_score, _ = ScoringEngine.calculate_spawn_rate_anomaly(db, source_node_id)
            rename_anomaly, rename_score, _ = ScoringEngine.calculate_rename_burst(db, source_node_id)
            edge_anomaly, edge_score, _ = ScoringEngine.calculate_edge_burst(db, source_node_id)
            
            # Weighted sum
            score_2a = (spawn_score * 0.4) + (rename_score * 0.3) + (edge_score * 0.3)
            
            logger.debug(f"Channel 2A score: {score_2a:.2f} (spawn={spawn_score:.2f}, rename={rename_score:.2f}, burst={edge_score:.2f})")
            
            return min(score_2a, 1.0)
        
        except Exception as e:
            logger.error(f"Failed to score channel 2A: {e}")
            return 0.0

    # CHANNEL 2B: STATISTICAL IMPOSSIBILITY (P-MATRIX)
    @staticmethod
    def score_channel_2b(
        edge_entropy: float = 0.0,
        baseline_entropy_mean: float = 5.0,
        registry_path: Optional[str] = None,
        edge_type: Optional[str] = None,
        command_line: Optional[str] = None,
        edge_metadata: Optional[dict] = None,
    ) -> float:
        try:
            # Primary path: score registry/service telemetry when available.
            md = edge_metadata or {}
            registry_context = registry_path or md.get("reg_target") or md.get("target_path") or ""
            command_context = command_line or md.get("child_cmd") or md.get("parent_cmd") or ""
            edge_kind = (edge_type or md.get("telemetry_kind") or md.get("edge_type") or "").upper()

            if edge_kind == "FILE_CREATE":
                score_2b, details = ScoringEngine._score_file_signal(
                    registry_context,
                    edge_entropy=edge_entropy,
                    edge_type=edge_kind,
                )

                if score_2b > 0:
                    logger.debug(
                        f"Channel 2B file score: {score_2b:.2f} "
                        f"(path={registry_context}, rules={details.get('rules', [])})"
                    )
                    return min(score_2b, 1.0)

            if registry_context:
                score_2b, details = ScoringEngine._score_registry_signal(
                    registry_context,
                    edge_type=edge_kind,
                    command_line=command_context,
                )

                if score_2b > 0:
                    logger.debug(
                        f"Channel 2B registry score: {score_2b:.2f} "
                        f"(path={registry_context}, rules={details.get('rules', [])})"
                    )
                    return min(score_2b, 1.0)

            # Fallback: entropy-based approximation for file samples.
            baseline_std = 1.0
            z_score = (edge_entropy - baseline_entropy_mean) / baseline_std
            
            # P-value approximation (how unlikely)
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            
            # Convert p-value to anomaly score
            # p < 0.001 = score 1.0, p > 0.05 = score 0.0
            if p_value < 0.001:
                score_2b = 1.0
            elif p_value > 0.05:
                score_2b = 0.0
            else:
                score_2b = 1.0 - (p_value / 0.05)
            
            logger.debug(f"Channel 2B entropy fallback score: {score_2b:.2f} (p-value={p_value:.6f})")
            
            return min(score_2b, 1.0)
        
        except Exception as e:
            logger.error(f"Failed to score channel 2B: {e}")
            return 0.0
    
    # CHANNEL 2C: ML GRAPH ANOMALY (RIVER)
    
    @staticmethod
    def score_channel_2c(graph_features: dict) -> float:
        try:
            node_count = graph_features.get("node_count", 0)
            edge_count = graph_features.get("edge_count", 0)
            branching_factor = graph_features.get("branching_factor", 0.0)
            
            # Heuristic: many edges = anomalous
            if edge_count > 10:
                score_2c = min(edge_count / 20, 1.0)
            elif branching_factor > 3:
                score_2c = min(branching_factor / 5, 1.0)
            else:
                score_2c = 0.0
            
            logger.debug(f"Channel 2C score: {score_2c:.2f} (edges={edge_count}, branching={branching_factor:.2f})")
            
            return score_2c
        
        except Exception as e:
            logger.error(f"Failed to score channel 2C: {e}")
            return 0.0