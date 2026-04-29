"""
ML Model Loader
Loads trained .pkl files from disk
"""

import joblib
import pickle
import os
from typing import Optional, Dict, Any
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)


class MLModelLoader:
    """Load and manage trained ML models from .pkl files."""
    
    def __init__(self, model_dir: str = "backend/ml/models/"):
        """
        Initialize model loader.
        
        Args:
            model_dir: Directory containing .pkl files
        """
        self.model_dir = model_dir
        self.models: Dict[str, Any] = {}
        self.scaler: Optional[Any] = None
        self.is_loaded = False
        
        # Try to load models, but don't fail if they don't exist
        self._load_all_models()
    
    def _load_all_models(self) -> bool:
        """
        Load all .pkl files from model directory.
        
        Returns:
            True if all models loaded successfully, False otherwise
        """
        try:
            # Check if model directory exists
            if not os.path.exists(self.model_dir):
                logger.debug(f"Model directory not found: {self.model_dir}")
                logger.debug("ML models will not be available (using fallback)")
                return False
            
            # Load Random Forest (P-Matrix)
            p_matrix_path = os.path.join(self.model_dir, 'p_matrix_model.pkl')
            if os.path.exists(p_matrix_path):
                self.models['p_matrix'] = joblib.load(p_matrix_path)
                logger.debug("Loaded P-Matrix model (Random Forest)")
            else:
                logger.debug(f"P-Matrix model not found: {p_matrix_path}")
            
            entropy_path = os.path.join(self.model_dir, 'entropy_classifier_model.pkl')
            if os.path.exists(entropy_path):
                self.models['entropy'] = joblib.load(entropy_path)
                logger.debug("Loaded Entropy Classifier model (XGBoost)")
            else:
                logger.debug(f"Entropy model not found: {entropy_path}")
            
            # Load River (HalfSpaceTrees)
            river_path = os.path.join(self.model_dir, 'river_halfspace_model.pkl')
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
        try:
            if 'p_matrix' not in self.models:
                logger.debug("P-Matrix model not available, returning 0.0")
                return 0.0
            
            if self.scaler is None:
                logger.debug("Feature scaler not available, using raw features")
                features_scaled = [features]
            else:
                features_scaled = self.scaler.transform([features])
            
            prob = self.models['p_matrix'].predict_proba(features_scaled)[0][1]
            return float(prob)
        
        except Exception as e:
            logger.error(f"  P-Matrix prediction failed: {e}")
            return 0.0
    
    def predict_entropy(self, features: list) -> float:
        try:
            if 'entropy' not in self.models:
                logger.debug("Entropy model not available, returning 0.0")
                return 0.0
            
            if self.scaler is None:
                logger.debug("Feature scaler not available, using raw features")
                features_scaled = [features]
            else:
                features_scaled = self.scaler.transform([features])
            
            prob = self.models['entropy'].predict_proba(features_scaled)[0][1]
            return float(prob)
        
        except Exception as e:
            logger.error(f"  Entropy prediction failed: {e}")
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
            p_matrix_score = self.predict_p_matrix(features)
            entropy_score = self.predict_entropy(features)
            river_score = self.predict_river(features_dict)
            
            # Ensemble: weighted average
            # P-Matrix: 40%, Entropy: 35%, River: 25%
            ensemble_score = (
                p_matrix_score * 0.40 +
                entropy_score * 0.35 +
                river_score * 0.25
            )
            
            return {
                "p_matrix": p_matrix_score,
                "entropy": entropy_score,
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


# Global instance
_ml_loader: Optional[MLModelLoader] = None


def get_ml_loader() -> MLModelLoader:
    """
    Get or create global ML model loader instance.
    
    Returns:
        MLModelLoader instance
    """
    global _ml_loader
    if _ml_loader is None:
        _ml_loader = MLModelLoader()
    return _ml_loader


def reload_models() -> bool:
    """
    Reload all ML models (useful for updates).
    
    Returns:
        True if reload successful
    """
    global _ml_loader
    _ml_loader = MLModelLoader()
    return _ml_loader.is_loaded
