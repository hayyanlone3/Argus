# backend/layers/layer0_bouncer/__init__.py
"""
Layer 0: Bouncer
Fast-path rejection of suspicious files via:
- VirusTotal hash lookup
- Entropy analysis (Tier 2/3)
- P-matrix statistical impossibility
- Digital signature verification
"""

from .services import BouncerService
from .utils import (
    calculate_shannon_entropy,
    calculate_sample_entropy,
    check_digital_signature,
    is_known_packer,
    get_file_code_section_entropy,
)

__all__ = [
    "BouncerService",
    "calculate_shannon_entropy",
    "calculate_sample_entropy",
    "check_digital_signature",
    "is_known_packer",
    "get_file_code_section_entropy",
]