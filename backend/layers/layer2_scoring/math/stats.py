"""
Statistical baselines and anomaly detection
"""

from scipy import stats
from shared.logger import setup_logger

logger = setup_logger(__name__)


def calculate_spawn_baseline() -> tuple:
    try:
        mean = 1.0
        std = 0.5
        
        logger.debug(f"  Spawn baseline: mean={mean}, std={std}")
        return (mean, std)
    
    except Exception as e:
        logger.error(f"  Failed to get spawn baseline: {e}")
        return (1.0, 0.5)


def calculate_z_score(value: float, mean: float, std: float) -> float:
    try:
        if std == 0:
            return 0.0
        return (value - mean) / std
    except Exception as e:
        logger.error(f"  Z-score calculation failed: {e}")
        return 0.0


def calculate_p_value(z_score: float) -> float:
    try:
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        return p_value
    except Exception as e:
        logger.error(f"  P-value calculation failed: {e}")
        return 1.0