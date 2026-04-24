# backend/layers/layer2_scoring/math/anomalies.py
"""
Anomaly detection patterns
"""

from shared.logger import setup_logger

logger = setup_logger(__name__)


def detect_burst(values: list, threshold: float = 3.0) -> bool:
    """
    Detect if list of values shows burst pattern (sudden spike).
    
    Args:
        values: List of numeric values
        threshold: Z-score threshold
        
    Returns:
        True if burst detected
    """
    try:
        if len(values) < 2:
            return False
        
        import numpy as np
        from scipy import stats
        
        # Check if last value is >3 sigma from mean
        mean = np.mean(values[:-1])
        std = np.std(values[:-1])
        
        if std == 0:
            return False
        
        z_score = (values[-1] - mean) / std
        
        is_burst = abs(z_score) > threshold
        
        if is_burst:
            logger.debug(f"  Burst detected: {values[-1]:.2f} (z={z_score:.2f})")
        
        return is_burst
    
    except Exception as e:
        logger.error(f"  Burst detection failed: {e}")
        return False


def detect_cycle(values: list) -> bool:
    """
    Detect if values show cyclic/repeating pattern.
    
    Args:
        values: List of values
        
    Returns:
        True if cycle detected
    """
    try:
        if len(values) < 4:
            return False
        
        # Simple: check if last 2 values match first 2
        if values[-2:] == values[:2]:
            logger.debug("  Cycle detected")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"  Cycle detection failed: {e}")
        return False