# backend/layers/layer2_scoring/ml/p_matrix.py

from shared.logger import setup_logger
import numpy as np
from scipy.stats import norm

logger = setup_logger(__name__)


def calculate_p_matrix(process_behavior: dict, baseline: dict) -> float:
    try:
        spawn_count = process_behavior.get("spawn_count", 0)
        spawn_mean = baseline.get("spawn_mean", 1.0)
        spawn_std = baseline.get("spawn_std", 0.5)
        
        if spawn_std == 0:
            return 0.5
        
        # Z-score for spawn count
        z = (spawn_count - spawn_mean) / spawn_std
        
        # P-value from normal distribution
        p_value = 2 * (1 - norm.cdf(abs(z)))
        
        logger.debug(f"P-Matrix: spawn_count={spawn_count}, p={p_value:.6f}")
        
        return max(0.0, min(p_value, 1.0))
    
    except Exception as e:
        logger.error(f"P-Matrix calculation failed: {e}")
        return 0.5