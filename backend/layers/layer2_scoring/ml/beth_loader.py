"""
BETH (Benign, Malicious & High-Risk Enterprise Threats) dataset loader
For Phase 1: stubbed, returns pre-computed baseline
"""

from shared.logger import setup_logger

logger = setup_logger(__name__)


def load_beth_model() -> dict:
    """
    Load pre-trained BETH baseline model.
    
    For Phase 1: returns hardcoded baseline
    For Phase 2+: loads actual model from disk
    
    Returns:
        {
            "process_baseline": {...},
            "file_baseline": {...},
            "edge_baseline": {...}
        }
    """
    try:
        # Stubbed BETH baseline
        beth_baseline = {
            "process_baseline": {
                "mean_children": 1.0,
                "std_children": 0.5,
                "mean_files_written": 2.0,
                "std_files_written": 1.0
            },
            "file_baseline": {
                "mean_entropy": 5.0,
                "std_entropy": 1.0
            },
            "edge_baseline": {
                "common_edge_types": ["SPAWNED", "READ", "WROTE"],
                "rare_edge_types": ["INJECTED_INTO", "DISABLED_AMSI"]
            }
        }
        
        logger.info("📦 BETH baseline loaded (Phase 1 stub)")
        return beth_baseline
    
    except Exception as e:
        logger.error(f"  Failed to load BETH model: {e}")
        return {}