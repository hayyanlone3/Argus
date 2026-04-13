# backend/layers/layer3_correlator/__init__.py
"""
Layer 3: Incident Correlator
Groups related edges into high-context incidents:
- 2-of-3 signals: graph proximity, process tree root, file hash
- MITRE ATT&CK stage assignment
- Plain-English narrative generation
"""

from .services import CorrelatorService
from .narrative import NarrativeGenerator

__all__ = ["CorrelatorService", "NarrativeGenerator"]