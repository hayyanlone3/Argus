# backend/layers/layer4_response/routes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import Quarantine, Whitelist, Incident
from backend.database.schemas import (
    QuarantineCreate, QuarantineRestore, QuarantineResponse,
    WhitelistCreate, WhitelistResponse, FeedbackCreate
)
from .quarantine import QuarantineService
from .whitelist import WhitelistService
from .isolation import IsolationService
from .feedback import FeedbackService
from backend.shared.logger import setup_logger
from backend.shared.exceptions import ValidationError

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Layer 4: Response Engine health check."""
    return {
        "layer": 4,
        "name": "Response Engine",
        "status": "operational",
        "features": [
            "File quarantine (safe isolation)",
            "3-tier whitelist (path, path+hash, hash-only)",
            "Process isolation (kill)",
            "Analyst feedback collection"
        ]
    }

# QUARANTINE ENDPOINTS
@router.post("/quarantine")
async def quarantine_file(
    quarantine_data: QuarantineCreate,
    db: Session = Depends(get_db)
):
    """
    Quarantine a suspicious file.
    
    Example:
        POST /api/layer4/quarantine
        {
            "original_path": "C:\\malware.exe",
            "hash_sha256": "abc123...",
            "detection_layer": "Layer0_Bouncer",
            "confidence": 0.95
        }
    """
    try:
        quarantine = QuarantineService.quarantine_file(
            quarantine_data.original_path,
            db,
            quarantine_data
        )
        return QuarantineResponse.from_orm(quarantine)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"  Quarantine failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quarantine")
async def list_quarantine(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000)
):

    try:
        result = QuarantineService.list_quarantine(db, limit)
        return {
            "total": result["total"],
            "quarantine": [QuarantineResponse.from_orm(q) for q in result["quarantined"]]
        }
    except Exception as e:
        logger.error(f"  Failed to list quarantine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quarantine/{quarantine_id}/restore")
async def restore_file(
    quarantine_id: int,
    restore_data: QuarantineRestore,
    db: Session = Depends(get_db)
):

    try:
        quarantine = QuarantineService.restore_file(quarantine_id, db, restore_data)
        return QuarantineResponse.from_orm(quarantine)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"  Restore failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quarantine/stats")
async def get_quarantine_stats(db: Session = Depends(get_db)):
    try:
        stats = QuarantineService.get_quarantine_stats(db)
        return stats
    except Exception as e:
        logger.error(f"  Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WHITELIST ENDPOINTS
@router.post("/whitelist")
async def add_whitelist(
    whitelist_data: WhitelistCreate,
    db: Session = Depends(get_db)
):

    try:
        whitelist = WhitelistService.add_whitelist(db, whitelist_data)
        return WhitelistResponse.from_orm(whitelist)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"  Failed to add whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whitelist")
async def list_whitelist(
    db: Session = Depends(get_db),
    tier: int = Query(None, ge=1, le=3),
    limit: int = Query(100, ge=1, le=1000)
):

    try:
        query = db.query(Whitelist)
        
        if tier:
            query = query.filter(Whitelist.tier == tier)
        
        entries = query.limit(limit).all()
        
        return {
            "total": len(entries),
            "whitelist": [WhitelistResponse.from_orm(e) for e in entries]
        }
    except Exception as e:
        logger.error(f"  Failed to list whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whitelist/check")
async def check_whitelist(
    file_path: str,
    file_hash: str = None,
    db: Session = Depends(get_db)
):

    try:
        is_whitelisted, tier, reason = WhitelistService.check_whitelist(
            db, file_path, file_hash
        )
        
        return {
            "is_whitelisted": is_whitelisted,
            "tier": tier,
            "reason": reason
        }
    except Exception as e:
        logger.error(f"  Whitelist check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/whitelist/{whitelist_id}")
async def remove_whitelist(
    whitelist_id: int,
    db: Session = Depends(get_db)
):

    try:
        WhitelistService.remove_whitelist(db, whitelist_id)
        logger.info(f"Removed whitelist: {whitelist_id}")
        return {"deleted": True, "id": whitelist_id}
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"  Failed to remove whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whitelist/stats")
async def get_whitelist_stats(db: Session = Depends(get_db)):
    """Get whitelist statistics."""
    try:
        stats = WhitelistService.get_whitelist_stats(db)
        return stats
    except Exception as e:
        logger.error(f"  Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ISOLATION ENDPOINTS
@router.post("/isolate/process/{process_id}")
async def isolate_process(
    process_id: int,
    force: bool = Query(False)
):

    try:
        success = IsolationService.kill_process(process_id, force=force)
        
        if success:
            return {"killed": True, "process_id": process_id}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to kill process {process_id}")
    
    except HTTPException as he:
        # Don't wrap HTTPException, just log and re-raise
        logger.error(f"  Isolation failed for PID {process_id}: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"  Isolation failed for PID {process_id} with unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/isolate/process-name/{process_name}")
async def isolate_process_by_name(
    process_name: str,
    force: bool = Query(False)
):

    try:
        success = IsolationService.kill_process_by_name(process_name, force=force)
        
        if success:
            return {"killed": True, "process_name": process_name}
        else:
            return {"killed": False, "process_name": process_name, "message": "Process not found or could not be killed"}
    
    except Exception as e:
        logger.error(f"  Isolation failed for process name {process_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# FEEDBACK ENDPOINTS
@router.post("/incidents/{incident_id}/feedback")
async def submit_incident_feedback(
    incident_id: int,
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db)
):

    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        feedback = FeedbackService.submit_feedback(db, incident_id, feedback_data)
        
        return {
            "feedback_id": feedback.id,
            "incident_id": incident_id,
            "feedback_type": feedback_data.feedback_type
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats")
async def get_feedback_stats(db: Session = Depends(get_db)):
    """Get feedback statistics (for model learning)."""
    try:
        stats = FeedbackService.get_feedback_stats(db)
        return stats
    except Exception as e:
        logger.error(f"  Failed to get feedback stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))