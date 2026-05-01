# backend/layers/layer3_correlator/routes.py
"""
Layer 3: Correlator API Endpoints
Provides incident management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import Incident, Edge, Feedback
from backend.database.schemas import (
    IncidentResponse, IncidentUpdate, FeedbackCreate, FeedbackResponse
)
from .services import CorrelatorService
from .narrative import NarrativeGenerator
from backend.shared.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Layer 3: Correlator health check."""
    return {
        "layer": 3,
        "name": "Correlator",
        "status": "operational",
        "features": [
            "Incident grouping (2-of-3 signals)",
            "MITRE ATT&CK stage assignment",
            "Plain-English narrative generation",
            "Incident lifecycle management"
        ]
    }


@router.get("/incidents")
async def list_incidents(
    db: Session = Depends(get_db),
    severity: str = Query(None),
    status: str = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List all incidents with enriched process chain data.
    
    Example:
        GET /api/layer3/incidents?severity=CRITICAL&limit=50
    """
    try:
        from backend.database.models import Node
        
        query = db.query(Incident)
        
        if severity:
            query = query.filter(Incident.severity == severity)
        
        if status:
            query = query.filter(Incident.status == status)
        
        incidents = query.order_by(Incident.created_at.desc()).limit(limit).all()
        
        result_incidents = []
        for inc in incidents:
            edges = db.query(Edge).filter(Edge.session_id == inc.session_id).order_by(Edge.timestamp.asc()).all()
            
            process_chain = []
            max_score = 0.0
            for edge in edges:
                src = db.query(Node).filter(Node.id == edge.source_id).first()
                tgt = db.query(Node).filter(Node.id == edge.target_id).first()
                
                edge_score = 0.0
                if edge.anomaly_score and edge.anomaly_score > edge_score:
                    edge_score = edge.anomaly_score
                if edge.ml_anomaly_score and edge.ml_anomaly_score > edge_score:
                    edge_score = edge.ml_anomaly_score
                if edge_score > max_score:
                    max_score = edge_score
                
                chain_entry = {
                    "edge_type": edge.edge_type.value if edge.edge_type else "unknown",
                    "parent": src.name if src else "unknown",
                    "parent_path": src.path if src else None,
                    "child": tgt.name if tgt else "unknown",
                    "child_path": tgt.path if tgt else None,
                    "score": round(edge_score, 3),
                    "severity": edge.final_severity.value if edge.final_severity else "unknown",
                    "timestamp": edge.timestamp.isoformat() if edge.timestamp else None,
                }
                process_chain.append(chain_entry)
            
            result_incidents.append({
                **IncidentResponse.from_orm(inc).dict(),
                "edge_count": len(edges),
                "max_edge_score": round(max_score, 3),
                "process_chain": process_chain,
            })
        
        return {
            "total": len(result_incidents),
            "incidents": result_incidents
        }
    
    except Exception as e:
        logger.error(f"  Failed to list incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{session_id}")
async def get_incident(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get single incident with all related edges and nodes.
    
    Example:
        GET /api/layer3/incidents/abc123-def456
    """
    try:
        incident = db.query(Incident).filter(Incident.session_id == session_id).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Get related edges
        edges = db.query(Edge).filter(Edge.session_id == session_id).all()
        
        # Get related nodes
        node_ids = set()
        for edge in edges:
            node_ids.add(edge.source_id)
            node_ids.add(edge.target_id)
        
        from backend.database.models import Node
        nodes = db.query(Node).filter(Node.id.in_(list(node_ids))).all() if node_ids else []
        
        return {
            "incident": IncidentResponse.from_orm(incident),
            "edges_count": len(edges),
            "nodes_count": len(nodes),
            "edges": edges,
            "nodes": nodes
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Failed to get incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/incidents/{session_id}")
async def update_incident(
    session_id: str,
    update_data: IncidentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update incident (status, notes, etc.).
    
    Example:
        PATCH /api/layer3/incidents/abc123
        {
            "status": "ACKNOWLEDGED",
            "analyst_notes": "Verified as benign"
        }
    """
    try:
        incident = db.query(Incident).filter(Incident.session_id == session_id).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(incident, key, value)
        
        # Calculate MTTI (Mean Time To Identify)
        if incident.status in ["FP", "TP", "RESOLVED"] and not incident.mtti_seconds:
            mtti = (datetime.utcnow() - incident.created_at).total_seconds()
            incident.mtti_seconds = int(mtti)
        
        db.commit()
        db.refresh(incident)
        
        logger.info(f"✏️  Updated incident: {session_id} → {incident.status}")
        return IncidentResponse.from_orm(incident)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Failed to update incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incidents/{session_id}/feedback")
async def submit_feedback(
    session_id: str,
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    Submit analyst feedback (TP/FP/UNKNOWN).
    
    Example:
        POST /api/layer3/incidents/abc123/feedback
        {
            "feedback_type": "FP",
            "analyst_comment": "Legitimate file, false alarm"
        }
    """
    try:
        incident = db.query(Incident).filter(Incident.session_id == session_id).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Validate feedback type
        if feedback_data.feedback_type not in ["TP", "FP", "UNKNOWN"]:
            raise HTTPException(status_code=400, detail="Invalid feedback type")
        
        # Create feedback
        feedback = Feedback(
            incident_id=incident.id,
            feedback_type=feedback_data.feedback_type,
            analyst_comment=feedback_data.analyst_comment,
            timestamp=datetime.utcnow()
        )
        
        db.add(feedback)
        
        # Update incident status based on feedback
        incident.status = feedback_data.feedback_type
        
        db.commit()
        db.refresh(feedback)
        
        logger.info(f"  Feedback submitted: {session_id} = {feedback_data.feedback_type}")
        
        return {
            "feedback_id": feedback.id,
            "incident_id": incident.id,
            "feedback_type": feedback_data.feedback_type,
            "incident_status": incident.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_incident_stats(db: Session = Depends(get_db)):
    """
    Get incident statistics (counts, severity distribution, MTTI).
    
    Example:
        GET /api/layer3/stats
    """
    try:
        incidents = db.query(Incident).all()
        
        # Count by severity
        severity_counts = {
            "CRITICAL": len([i for i in incidents if i.severity.value == "CRITICAL"]),
            "WARNING": len([i for i in incidents if i.severity.value == "WARNING"]),
            "UNKNOWN": len([i for i in incidents if i.severity.value == "UNKNOWN"]),
            "BENIGN": len([i for i in incidents if i.severity.value == "BENIGN"]),
        }
        
        # Count by status
        status_counts = {
            "OPEN": len([i for i in incidents if i.status == "OPEN"]),
            "ACKNOWLEDGED": len([i for i in incidents if i.status == "ACKNOWLEDGED"]),
            "FP": len([i for i in incidents if i.status == "FP"]),
            "TP": len([i for i in incidents if i.status == "TP"]),
            "RESOLVED": len([i for i in incidents if i.status == "RESOLVED"]),
        }
        
        # Calculate MTTI (only for resolved)
        resolved_mtti = [i.mtti_seconds for i in incidents if i.mtti_seconds]
        avg_mtti = sum(resolved_mtti) / len(resolved_mtti) if resolved_mtti else 0
        
        # Calculate AI detection time average
        detection_times = [i.detection_seconds for i in incidents if i.detection_seconds]
        avg_detection = sum(detection_times) / len(detection_times) if detection_times else 0
        
        # FP rate
        total_feedback = len([i for i in incidents if i.status in ["FP", "TP"]])
        fp_count = len([i for i in incidents if i.status == "FP"])
        fp_rate = (fp_count / total_feedback * 100) if total_feedback > 0 else 0
        
        return {
            "total_incidents": len(incidents),
            "severity_distribution": severity_counts,
            "status_distribution": status_counts,
            "metrics": {
                "mean_time_to_identify_seconds": int(avg_mtti),
                "mean_detection_seconds": round(avg_detection, 2),
                "false_positive_rate_percent": round(fp_rate, 1),
                "analyst_feedback_count": total_feedback
            }
        }
    
    except Exception as e:
        logger.error(f"  Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))