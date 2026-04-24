"""
Statistical baselines and anomaly detection
"""

from scipy import stats
from shared.logger import setup_logger

logger = setup_logger(__name__)


def calculate_spawn_baseline() -> tuple:
    """
    Get baseline spawn rate statistics from BETH dataset.
    
    Returns:
        (mean: float, std: float)
    """
    try:
        # BETH baseline: normal processes spawn 0.5-1.5 children
        # Standard deviation: 0.5
        mean = 1.0
        std = 0.5
        
        logger.debug(f"  Spawn baseline: mean={mean}, std={std}")
        return (mean, std)
    
    except Exception as e:
        logger.error(f"  Failed to get spawn baseline: {e}")
        return (1.0, 0.5)


def calculate_z_score(value: float, mean: float, std: float) -> float:
    """
    Calculate Z-score (standard deviations from mean).
    
    Args:
        value: Data point
        mean: Population mean
        std: Population standard deviation
        
    Returns:
        Z-score value
    """
    try:
        if std == 0:
            return 0.0
        return (value - mean) / std
    except Exception as e:
        logger.error(f"  Z-score calculation failed: {e}")
        return 0.0


def calculate_p_value(z_score: float) -> float:
    """
    Calculate p-value from Z-score (probability of observing this value).
    
    Args:
        z_score: Z-score value
        
    Returns:
        P-value 0.0-1.0
    """
    try:
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        return p_value
    except Exception as e:
        logger.error(f"  P-value calculation failed: {e}")
        return 1.0