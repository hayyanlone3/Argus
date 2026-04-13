# backend/layers/layer2_scoring/__init__.py
"""
Layer 2: Scoring Engine
Parallel anomaly detection via 3 channels:
- 2A: Math Certainty (entropy, spawn rate, rename burst)
- 2B: Statistical Impossibility (P-matrix baseline)
- 2C: ML Graph Anomaly (River HalfSpaceTrees)
Output: BENIGN | UNKNOWN | WARNING | CRITICAL
"""

from .scoring import ScoringEngine
from .voting_logic import VotingEngine

__all__ = ["ScoringEngine", "VotingEngine"]