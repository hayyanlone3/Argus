from shared.logger import setup_logger
logger = setup_logger(__name__)

class RiverAnomalyDetector:
    def __init__(self):
        try:
            import river
            self.river = river
            self.model = river.anomaly.HalfSpaceTrees(seed=42)
            logger.info("River HalfSpaceTrees initialized")
        except ImportError:
            logger.warning("River not installed, using simple heuristics")
            self.river = None
            self.model = None
    
    def predict(self, features: dict) -> float:
        try:
            if self.model:
                # Use actual River model
                score = self.model.score_one(features)
                return max(0.0, min(score, 1.0))
            else:
                total_activity = sum(features.values())
                score = min(total_activity / 50, 1.0)
                return score
        
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return 0.0
    
    def learn(self, features: dict, label: int):
        try:
            if self.model:
                self.model.learn_one(features, label)
                logger.debug(f"Learned: label={label}")
        
        except Exception as e:
            logger.error(f"Learning failed: {e}")