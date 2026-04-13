"""
River HalfSpaceTrees wrapper for online anomaly detection
For Phase 1: stubbed, uses simple heuristics
"""

from shared.logger import setup_logger

logger = setup_logger(__name__)


class RiverAnomalyDetector:
    """
    Wrapper around River HalfSpaceTrees for online ML anomaly detection.
    
    For Phase 1: simple heuristics
    For Phase 2+: actual River implementation
    """
    
    def __init__(self):
        """Initialize detector."""
        try:
            import river
            self.river = river
            self.model = river.anomaly.HalfSpaceTrees(seed=42)
            logger.info("📦 River HalfSpaceTrees initialized")
        except ImportError:
            logger.warning("⚠️  River not installed, using simple heuristics")
            self.river = None
            self.model = None
    
    def predict(self, features: dict) -> float:
        """
        Predict anomaly score for features.
        
        Args:
            features: {
                "process_spawns": int,
                "files_written": int,
                "files_read": int,
                "registry_writes": int,
                "graph_size": int
            }
            
        Returns:
            Anomaly score 0.0-1.0
        """
        try:
            if self.model:
                # Use actual River model
                score = self.model.score_one(features)
                return max(0.0, min(score, 1.0))  # Clamp to 0-1
            else:
                # Heuristic: more activity = more anomalous
                total_activity = sum(features.values())
                score = min(total_activity / 50, 1.0)
                return score
        
        except Exception as e:
            logger.error(f"❌ Prediction failed: {e}")
            return 0.0
    
    def learn(self, features: dict, label: int):
        """
        Online learning: update model with (features, label).
        
        Args:
            features: Feature dictionary
            label: 1 (anomalous), 0 (benign)
        """
        try:
            if self.model:
                self.model.learn_one(features, label)
                logger.debug(f"📚 Learned: label={label}")
        
        except Exception as e:
            logger.error(f"❌ Learning failed: {e}")