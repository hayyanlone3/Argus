"""
Layer 2: Scoring Engine
Calculates anomaly scores from 3 independent channels
"""

from sqlalchemy.orm import Session
from backend.database.models import Edge, Node
from backend.shared.enums import Severity
from backend.shared.logger import setup_logger
from backend.shared.constants import (
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

logger = setup_logger(__name__)


class ScoringEngine:
    """Layer 2: Scoring Engine with 3 parallel channels"""
    
    # ═══════════════════════════════════════════════════════════════
    # CHANNEL 2A: MATH CERTAINTY
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def calculate_spawn_rate_anomaly(db: Session, process_node_id: int) -> tuple:
        """
        Calculate if spawn rate is anomalous (>3 sigma).
        
        Returns:
            (is_anomalous: bool, score: float, details: str)
        """
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
                logger.info(f"🔴 Spawn rate anomaly: {spawned_edges} children (z={z_score:.2f})")
            
            return (is_anomalous, score, f"spawned {spawned_edges} processes")
        
        except Exception as e:
            logger.error(f"❌ Failed to calculate spawn rate: {e}")
            return (False, 0.0, "error")
    
    @staticmethod
    def calculate_rename_burst(db: Session, source_node_id: int) -> tuple:
        """
        Calculate if process renamed files in burst (>80% of writes are renames).
        
        Returns:
            (is_anomalous: bool, score: float, details: str)
        """
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
                logger.info(f"🔴 Rename burst: {rename_ratio:.1%} of {total_writes} writes")
            
            return (is_anomalous, rename_ratio, f"{rename_ratio:.1%} rename burst")
        
        except Exception as e:
            logger.error(f"❌ Failed to calculate rename burst: {e}")
            return (False, 0.0, "error")
    
    @staticmethod
    def calculate_edge_burst(db: Session, source_node_id: int) -> tuple:
        """
        Calculate if process created edges in burst (>3 sigma from baseline).
        
        Returns:
            (is_anomalous: bool, score: float, details: str)
        """
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
                logger.info(f"🔴 Edge burst: {recent_edges} edges in 1 minute (z={z_score:.2f})")
            
            return (is_anomalous, score, f"{recent_edges} edges/min burst")
        
        except Exception as e:
            logger.error(f"❌ Failed to calculate edge burst: {e}")
            return (False, 0.0, "error")
    
    @staticmethod
    def score_channel_2a(db: Session, source_node_id: int) -> float:
        """
        Channel 2A: Math Certainty
        Combines spawn rate, rename burst, edge burst into single 0-1 score.
        
        Args:
            db: Database session
            source_node_id: Process node ID
            
        Returns:
            Anomaly score 0.0-1.0
        """
        try:
            # Get individual signals
            spawn_anomaly, spawn_score, _ = ScoringEngine.calculate_spawn_rate_anomaly(db, source_node_id)
            rename_anomaly, rename_score, _ = ScoringEngine.calculate_rename_burst(db, source_node_id)
            edge_anomaly, edge_score, _ = ScoringEngine.calculate_edge_burst(db, source_node_id)
            
            # Weighted sum
            score_2a = (spawn_score * 0.4) + (rename_score * 0.3) + (edge_score * 0.3)
            
            logger.debug(f"📊 Channel 2A score: {score_2a:.2f} (spawn={spawn_score:.2f}, rename={rename_score:.2f}, burst={edge_score:.2f})")
            
            return min(score_2a, 1.0)
        
        except Exception as e:
            logger.error(f"❌ Failed to score channel 2A: {e}")
            return 0.0
    
    # ═══════════════════════════════════════════════════════════════
    # CHANNEL 2B: STATISTICAL IMPOSSIBILITY (P-MATRIX)
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def score_channel_2b(edge_entropy: float, baseline_entropy_mean: float = 5.0) -> float:
        """
        Channel 2B: Statistical Impossibility
        Based on BETH baseline: how unlikely is this process behavior?
        
        Args:
            edge_entropy: Entropy of edge features (file hash, path risk, etc.)
            baseline_entropy_mean: Expected entropy from BETH dataset
            
        Returns:
            Anomaly score 0.0-1.0
        """
        try:
            # Simplified: if entropy is 3+ sigma from baseline, anomalous
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
            
            logger.debug(f"📊 Channel 2B score: {score_2b:.2f} (p-value={p_value:.6f})")
            
            return min(score_2b, 1.0)
        
        except Exception as e:
            logger.error(f"❌ Failed to score channel 2B: {e}")
            return 0.0
    
    # ═══════════════════════════════════════════════════════════════
    # CHANNEL 2C: ML GRAPH ANOMALY (RIVER)
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def score_channel_2c(graph_features: dict) -> float:
        """
        Channel 2C: ML Graph Anomaly
        Uses River HalfSpaceTrees for online anomaly detection.
        
        For now: stub that returns 0.0 (will be implemented with actual ML)
        
        Args:
            graph_features: {
                "node_count": int,
                "edge_count": int,
                "max_depth": int,
                "branching_factor": float
            }
            
        Returns:
            Anomaly score 0.0-1.0
        """
        try:
            # TODO: Implement actual River model
            # For Phase 1, return deterministic score based on heuristics
            
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
            
            logger.debug(f"📊 Channel 2C score: {score_2c:.2f} (edges={edge_count}, branching={branching_factor:.2f})")
            
            return score_2c
        
        except Exception as e:
            logger.error(f"❌ Failed to score channel 2C: {e}")
            return 0.0