from typing import Dict, Any, Optional
from backend.shared.logger import setup_logger
from .model_loader import get_ml_loader

logger = setup_logger(__name__)


class MLPredictor:
    """High-level ML prediction interface."""
    
    @staticmethod
    def extract_features(event_data: Dict[str, Any]) -> tuple:
        """
        Extract features from event data.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            (features_list, features_dict) for different model types
        """
        try:
            # Features for Random Forest and XGBoost
            features_list = [
                float(event_data.get('entropy', 0.0)),
                float(event_data.get('file_size', 0.0)),
                float(event_data.get('path_risk', 0.0)),
                float(hash(event_data.get('parent_process', '')) % 10000),
                float(hash(event_data.get('child_process', '')) % 10000),
            ]
            
            # Features for River (dictionary format)
            features_dict = {
                'entropy': float(event_data.get('entropy', 0.0)),
                'file_size': float(event_data.get('file_size', 0.0)),
                'path_risk': float(event_data.get('path_risk', 0.0)),
                'parent_hash': float(hash(event_data.get('parent_process', '')) % 10000),
                'child_hash': float(hash(event_data.get('child_process', '')) % 10000),
            }
            
            return features_list, features_dict
        
        except Exception as e:
            logger.error(f"  Feature extraction failed: {e}")
            return [0.0] * 5, {}
    
    @staticmethod
    def predict(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make ML predictions for an event.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            Dictionary with predictions and scores
        """
        try:
            ml_loader = get_ml_loader()
            
            # Extract features
            features_list, features_dict = MLPredictor.extract_features(event_data)
            
            # Get ensemble prediction
            scores = ml_loader.ensemble_predict(features_list, features_dict)
            
            # Determine severity based on ensemble score
            ensemble_score = scores['ensemble']
            
            if ensemble_score >= 0.80:
                severity = "CRITICAL"
            elif ensemble_score >= 0.60:
                severity = "WARNING"
            elif ensemble_score >= 0.40:
                severity = "UNKNOWN"
            else:
                severity = "BENIGN"
            
            return {
                "scores": scores,
                "severity": severity,
                "confidence": ensemble_score,
                "models_available": ml_loader.is_loaded
            }
        
        except Exception as e:
            logger.error(f"  ML prediction failed: {e}")
            return {
                "scores": {
                    "p_matrix": 0.0,
                    "entropy": 0.0,
                    "river": 0.0,
                    "ensemble": 0.0
                },
                "severity": "UNKNOWN",
                "confidence": 0.0,
                "models_available": False
            }
    
    @staticmethod
    def predict_p_matrix_only(event_data: Dict[str, Any]) -> float:
        try:
            ml_loader = get_ml_loader()
            features_list, _ = MLPredictor.extract_features(event_data)
            return ml_loader.predict_p_matrix(features_list)
        except Exception as e:
            logger.error(f"  P-Matrix prediction failed: {e}")
            return 0.0
    
    @staticmethod
    def predict_entropy_only(event_data: Dict[str, Any]) -> float:
        try:
            ml_loader = get_ml_loader()
            features_list, _ = MLPredictor.extract_features(event_data)
            return ml_loader.predict_entropy(features_list)
        except Exception as e:
            logger.error(f"  Entropy prediction failed: {e}")
            return 0.0
    
    @staticmethod
    def predict_river_only(event_data: Dict[str, Any]) -> float:
        try:
            ml_loader = get_ml_loader()
            _, features_dict = MLPredictor.extract_features(event_data)
            return ml_loader.predict_river(features_dict)
        except Exception as e:
            logger.error(f"  River prediction failed: {e}")
            return 0.0
