from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from backend.shared.enums import NodeType, EdgeType, Severity, Status

# NODE SCHEMAS
class NodeCreate(BaseModel):
    type: NodeType
    name: str
    path: Optional[str] = None
    hash_sha256: Optional[str] = None
    content: Optional[str] = None
    path_risk: float = 0.0


class NodeResponse(BaseModel):
    id: int
    type: NodeType
    name: str
    path: Optional[str]
    hash_sha256: Optional[str]
    content: Optional[str]
    first_seen: datetime
    last_seen: datetime
    path_risk: float

    class Config:
        from_attributes = True

# EDGE SCHEMAS
class EdgeCreate(BaseModel):
    source_id: int
    target_id: int
    edge_type: EdgeType
    session_id: str
    injection_type: Optional[str] = None
    script_risk: Optional[float] = None
    reg_key_risk: Optional[float] = None
    wmi_type: Optional[str] = None
    edge_metadata: Optional[dict] = None


class EdgeResponse(BaseModel):
    id: int
    source_id: int
    target_id: int
    edge_type: EdgeType
    timestamp: datetime
    session_id: str
    anomaly_score: float
    bouncer_status: Optional[str]
    entropy_value: Optional[float]
    p_matrix_score: Optional[float]
    ml_anomaly_score: Optional[float]
    final_severity: Optional[Severity]
    injection_type: Optional[str]
    script_risk: Optional[float]
    reg_key_risk: Optional[float]
    wmi_type: Optional[str]
    edge_metadata: Optional[dict] = None

    class Config:
        from_attributes = True

# INCIDENT SCHEMAS
class IncidentCreate(BaseModel):
    session_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: Severity
    mitre_stage: Optional[str] = None
    narrative: Optional[str] = None


class IncidentUpdate(BaseModel):
    status: Optional[Status] = None
    analyst_notes: Optional[str] = None
    mtti_seconds: Optional[int] = None  # Analyst response time
    detection_seconds: Optional[float] = None  # AI detection time
    first_event_timestamp: Optional[datetime] = None  # First event time
    resolved_at: Optional[datetime] = None


class IncidentResponse(BaseModel):
    id: int
    session_id: str
    created_at: datetime
    confidence: float
    severity: Severity
    mitre_stage: Optional[str]
    narrative: Optional[str]
    status: str
    analyst_notes: Optional[str]
    mtti_seconds: Optional[int]  # Analyst response time
    detection_seconds: Optional[float]  # AI detection time
    first_event_timestamp: Optional[datetime]  # First event time
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

# QUARANTINE SCHEMAS
class QuarantineCreate(BaseModel):
    original_path: str
    hash_sha256: str
    detection_layer: Optional[str] = None
    confidence: Optional[float] = None
    session_id: Optional[str] = None
    mitre_stage: Optional[str] = None


class QuarantineRestore(BaseModel):
    restore_reason: str


class QuarantineResponse(BaseModel):
    id: int
    original_path: str
    hash_sha256: str
    detection_layer: Optional[str]
    confidence: Optional[float]
    session_id: Optional[str]
    mitre_stage: Optional[str]
    quarantined_at: datetime
    quarantine_path: Optional[str]
    restored_at: Optional[datetime]
    restore_reason: Optional[str]
    status: str

    class Config:
        from_attributes = True

# WHITELIST SCHEMAS
class WhitelistCreate(BaseModel):
    tier: int = Field(..., ge=1, le=3)
    path: str
    hash_sha256: Optional[str] = None
    reason: Optional[str] = None
    added_by: Optional[str] = None


class WhitelistResponse(BaseModel):
    id: int
    tier: int
    path: str
    hash_sha256: Optional[str]
    reason: Optional[str]
    added_by: Optional[str]
    added_at: datetime

    class Config:
        from_attributes = True

# FEEDBACK SCHEMAS
class FeedbackCreate(BaseModel):
    feedback_type: str = Field(..., pattern="^(TP|FP|UNKNOWN)$")
    analyst_comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    incident_id: int
    feedback_type: str
    analyst_comment: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

# VIRUSTOTAL CACHE SCHEMAS
class VTCacheCreate(BaseModel):
    hash_sha256: str
    score: float = Field(..., ge=0.0, le=1.0)


class VTCacheResponse(BaseModel):
    hash_sha256: str
    score: float
    queried_at: datetime

    class Config:
        from_attributes = True

# POLICY SCHEMAS
class PolicyConfigOut(BaseModel):
    auto_response_enabled: bool
    kill_on_alert: bool
    quarantine_on_warn: bool
    min_final_score_incident: float
    
    class Config:
        from_attributes = True

class PolicyConfigUpdate(BaseModel):
    auto_response_enabled: Optional[bool] = None
    kill_on_alert: Optional[bool] = None
    quarantine_on_warn: Optional[bool] = None
    min_final_score_incident: Optional[float] = None

# AGGREGATE RESPONSE SCHEMAS
class IncidentDetailResponse(BaseModel):
    incident: IncidentResponse
    edges: List[EdgeResponse]
    nodes: List[NodeResponse]
    narrative: str
    mitre_stage: str
    confidence: float


class DashboardStatsResponse(BaseModel):
    total_incidents: int
    critical_count: int
    warning_count: int
    unknown_count: int
    benign_count: int
    false_positive_count: int
    mtti_average: Optional[float]  # Analyst response time
    detection_time_average: Optional[float]  # AI detection time
    model_maturity: float

    class Config:
        protected_namespaces = ()