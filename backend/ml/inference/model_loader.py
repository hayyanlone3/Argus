import joblib
import pickle
import os
from typing import Optional, Dict, Any
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)

class MLModelLoader:    
    def __init__(self, model_dir: str = "backend/ml/models/"):
        self.model_dir = model_dir
        self.models: Dict[str, Any] = {}
        self.scaler: Optional[Any] = None
        self.is_loaded = False
        
        self._load_all_models()
    
    def _load_all_models(self) -> bool:
        try:
            # Check if model directory exists
            if not os.path.exists(self.model_dir):
                logger.debug(f"Model directory not found: {self.model_dir}")
                logger.debug("ML models will not be available (using fallback)")
                return False
            
            # Load River (HalfSpaceTrees)
            river_path = os.path.join(self.model_dir, 'river_windows_baseline.pkl')
            if os.path.exists(river_path):
                with open(river_path, 'rb') as f:
                    self.models['river'] = pickle.load(f)
                logger.debug("Loaded River HalfSpaceTrees model")
            else:
                logger.debug(f"River model not found: {river_path}")
            
            # Load Feature Scaler
            scaler_path = os.path.join(self.model_dir, 'feature_scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                logger.debug("Loaded Feature Scaler")
            else:
                logger.debug(f"Feature scaler not found: {scaler_path}")
            
            # Check if we loaded at least some models
            if self.models:
                self.is_loaded = True
                logger.info(f"ML Models loaded: {len(self.models)} models available")
                return True
            else:
                logger.debug("No ML models loaded - using fallback scoring")
                return False
        
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            logger.debug("Falling back to hardcoded scoring")
            return False
    
    def predict_p_matrix(self, features: list) -> float:
        logger.debug("P-Matrix model not wired, returning 0.0")
        return 0.0
    
    def predict_entropy(self, features: list) -> float:
        logger.debug("Entropy model not wired, returning 0.0")
        return 0.0
    
    def predict_river(self, features_dict: Dict[str, float]) -> float:
        try:
            if 'river' not in self.models:
                logger.debug("River model not available, returning 0.0")
                return 0.0
            
            score = self.models['river'].score_one(features_dict)
            return max(0.0, min(float(score), 1.0))
        
        except Exception as e:
            logger.error(f"  River prediction failed: {e}")
            return 0.0
    
    def ensemble_predict(self, features: list, features_dict: Dict[str, float]) -> Dict[str, float]:
        try:
            river_score = self.predict_river(features_dict)
            
            ensemble_score = river_score
            
            return {
                "p_matrix": 0.0,
                "entropy": 0.0,
                "river": river_score,
                "ensemble": ensemble_score
            }
        
        except Exception as e:
            logger.error(f"  Ensemble prediction failed: {e}")
            return {
                "p_matrix": 0.0,
                "entropy": 0.0,
                "river": 0.0,
                "ensemble": 0.0
            }

_ml_loader: Optional[MLModelLoader] = None

def get_ml_loader() -> MLModelLoader:
    global _ml_loader
    if _ml_loader is None:
        _ml_loader = MLModelLoader()
    return _ml_loader


def reload_models() -> bool:
    global _ml_loader
    _ml_loader = MLModelLoader()
    return _ml_loader.is_loaded
