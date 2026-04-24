"""
Entropy calculations for anomaly detection
"""

import numpy as np
from scipy.stats import entropy as scipy_entropy
from shared.logger import setup_logger

logger = setup_logger(__name__)


def calculate_entropy(data: bytes) -> float:
    """
    Calculate Shannon entropy of byte data.
    
    Args:
        data: Raw bytes
        
    Returns:
        Entropy value 0.0-8.0
    """
    try:
        if not data:
            return 0.0
        
        byte_counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
        byte_probs = byte_counts / len(data)
        
        shannon = scipy_entropy(byte_probs, base=2)
        return float(shannon)
    
    except Exception as e:
        logger.error(f"  Entropy calculation failed: {e}")
        return 0.0


def calculate_edge_entropy(edge_features: dict) -> float:
    """
    Calculate entropy of edge features (process behavior).
    
    Args:
        edge_features: {
            "source_type": str,
            "target_type": str,
            "edge_type": str,
            "file_entropy": float,
            "path_risk": float
        }
        
    Returns:
        Feature entropy 0.0-8.0
    """
    try:
        # Simplified: combine feature values into bytes
        features = [
            hash(edge_features.get("source_type", "")) % 256,
            hash(edge_features.get("target_type", "")) % 256,
            hash(edge_features.get("edge_type", "")) % 256,
            int((edge_features.get("file_entropy", 0.0) * 255) % 256),
            int((edge_features.get("path_risk", 0.0) * 255) % 256),
        ]
        
        feature_bytes = bytes(features)
        return calculate_entropy(feature_bytes)
    
    except Exception as e:
        logger.error(f"  Edge entropy calculation failed: {e}")
        return 0.0