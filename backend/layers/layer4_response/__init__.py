# backend/layers/layer4_response/__init__.py
"""
Layer 4: Response Engine
Automated threat containment:
- File quarantine (move to safe location)
- Whitelist management (3-tier system)
- Process isolation (kill malicious processes)
- Analyst feedback collection
"""

from .quarantine import QuarantineService
from .whitelist import WhitelistService
from .isolation import IsolationService
from .feedback import FeedbackService

__all__ = [
    "QuarantineService",
    "WhitelistService",
    "IsolationService",
    "FeedbackService",
]