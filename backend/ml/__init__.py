"""
Machine Learning Module for ARGUS
Handles model loading, inference, and training
"""

from .inference.model_loader import get_ml_loader, MLModelLoader

__all__ = ["get_ml_loader", "MLModelLoader"]
