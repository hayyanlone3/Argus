# backend/shared/enums.py
"""Shared enumerations for ARGUS."""

from enum import Enum


class NodeType(str, Enum):
    """Types of nodes in the provenance graph."""
    PROCESS = "process"
    FILE = "file"
    SCRIPT = "script"
    WMI_OBJECT = "wmi_object"
    REG_KEY = "reg_key"


class EdgeType(str, Enum):
    """Types of edges in the provenance graph."""
    SPAWNED = "SPAWNED"
    READ = "READ"
    WROTE = "WROTE"
    INJECTED_INTO = "INJECTED_INTO"
    EXECUTED_SCRIPT = "EXECUTED_SCRIPT"
    SUBSCRIBED_WMI = "SUBSCRIBED_WMI"
    MODIFIED_REG = "MODIFIED_REG"

class Severity(str, Enum):
    """Incident severity levels."""
    BENIGN = "BENIGN"
    UNKNOWN = "UNKNOWN"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Status(str, Enum):
    """Incident status values."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FP = "FP"
    TP = "TP"
    RESOLVED = "RESOLVED"


class BouncerStatus(str, Enum):
    """Layer 0 Bouncer status values."""
    PASS = "PASS"
    WARN = "WARN"
    CRITICAL = "CRITICAL"
    UNCERTAIN = "UNCERTAIN"
    BLOCK = "BLOCK"