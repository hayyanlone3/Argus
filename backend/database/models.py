# backend/database/models.py
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey,
    Enum, Index, JSON, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from shared.enums import NodeType, EdgeType, Severity

Base = declarative_base()


class Node(Base):
    """Graph node representing process, file, script, WMI, or registry."""
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(NodeType), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    path = Column(String(512), nullable=True, index=True)
    hash_sha256 = Column(String(64), nullable=True, index=True)
    content = Column(Text, nullable=True)  # Script content only
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    path_risk = Column(Float, default=0.0)

    # Relationships
    edges_from = relationship("Edge", foreign_keys="Edge.source_id", back_populates="source")
    edges_to = relationship("Edge", foreign_keys="Edge.target_id", back_populates="target")

    __table_args__ = (
        Index('idx_node_type_path_hash', 'type', 'path', 'hash_sha256'),
    )


class Edge(Base):
    """Graph edge representing relationships (SPAWNED, READ, WROTE, INJECTED, etc.)."""
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    edge_type = Column(Enum(EdgeType), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)

    # Scoring columns
    anomaly_score = Column(Float, default=0.0)
    bouncer_status = Column(String(50), nullable=True)
    entropy_value = Column(Float, nullable=True)
    p_matrix_score = Column(Float, nullable=True)
    ml_anomaly_score = Column(Float, nullable=True)
    final_severity = Column(Enum(Severity), nullable=True)

    # Edge metadata
    injection_type = Column(String(100), nullable=True)
    script_risk = Column(Float, nullable=True)
    reg_key_risk = Column(Float, nullable=True)
    wmi_type = Column(String(100), nullable=True)
    edge_metadata = Column(JSON, nullable=True) 

    # Relationships
    source = relationship("Node", foreign_keys=[source_id], back_populates="edges_from")
    target = relationship("Node", foreign_keys=[target_id], back_populates="edges_to")

    __table_args__ = (
        Index('idx_edge_timestamp_session', 'timestamp', 'session_id'),
        Index('idx_edge_severity', 'final_severity'),
    )


class Incident(Base):
    """Correlated incident (group of related edges)."""
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    confidence = Column(Float, nullable=False)
    severity = Column(Enum(Severity), nullable=False, index=True)

    mitre_stage = Column(String(255), nullable=True)
    narrative = Column(Text, nullable=True)

    status = Column(String(50), default="OPEN", nullable=False, index=True)
    analyst_notes = Column(Text, nullable=True)
    mtti_seconds = Column(Integer, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_incident_created_severity', 'created_at', 'severity'),
    )


class Quarantine(Base):
    """Quarantined files."""
    __tablename__ = "quarantine"

    id = Column(Integer, primary_key=True, index=True)
    original_path = Column(String(512), nullable=False)
    hash_sha256 = Column(String(64), nullable=False, index=True)
    detection_layer = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    session_id = Column(String(100), nullable=True)
    mitre_stage = Column(String(255), nullable=True)

    quarantined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    quarantine_path = Column(String(512), nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restore_reason = Column(String(255), nullable=True)
    status = Column(String(50), default="QUARANTINED", nullable=False)


class Whitelist(Base):
    """Whitelist entries (Tier 1/2/3)."""
    __tablename__ = "whitelist"

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Integer, nullable=False)  # 1, 2, or 3
    path = Column(String(512), nullable=False)
    hash_sha256 = Column(String(64), nullable=True)
    reason = Column(String(255), nullable=True)
    added_by = Column(String(100), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_whitelist_tier_path_hash', 'tier', 'path', 'hash_sha256'),
    )


class VTCache(Base):
    """VirusTotal cache."""
    __tablename__ = "vt_cache"

    hash_sha256 = Column(String(64), primary_key=True)
    score = Column(Float, nullable=False)
    queried_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Feedback(Base):
    """Analyst feedback on incidents."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, nullable=False)
    feedback_type = Column(String(50), nullable=False)  # TP, FP, UNKNOWN
    analyst_comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class PolicyConfig(Base):
    """Global auto-response policy configuration."""
    __tablename__ = "policy_config"

    id = Column(Integer, primary_key=True, default=1)
    auto_response_enabled = Column(Boolean, default=False, nullable=False)
    kill_on_alert = Column(Boolean, default=False, nullable=False)
    quarantine_on_warn = Column(Boolean, default=False, nullable=False)
    min_final_score_incident = Column(Float, default=0.50, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ═══════════════════════════════════════════════════════════════
# AUDIT LOGS (stored in PostgreSQL)
# ═══════════════════════════════════════════════════════════════

class AuditLog(Base):
    """Audit / event log stored in PostgreSQL for forensic trail."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # INFO | WARNING | ERROR
    level = Column(String(10), default="INFO", nullable=False, index=True)

    # e.g. "collector.file_watcher", "layer4.quarantine"
    source = Column(String(100), nullable=False, index=True)

    # e.g. "file_write", "quarantine_requested", "quarantine_failed"
    action = Column(String(100), nullable=False, index=True)

    message = Column(String(500), nullable=True)

    entity_type = Column(String(50), nullable=True, index=True)   # file/process/incident/quarantine
    entity_id = Column(Integer, nullable=True, index=True)

    session_id = Column(String(100), nullable=True, index=True)
    path = Column(String(512), nullable=True, index=True)
    hash_sha256 = Column(String(64), nullable=True, index=True)

    payload = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_audit_source_action_ts", "source", "action", "timestamp"),
    )

