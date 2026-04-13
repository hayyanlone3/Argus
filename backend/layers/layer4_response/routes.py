# backend/layers/layer4_response/routes.py
"""
Layer 4: Response Engine API Endpoints
Quarantine, whitelist, and feedback management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Quarantine, Whitelist, Incident
from database.schemas import (
    QuarantineCreate, QuarantineRestore, QuarantineResponse,
    WhitelistCreate, WhitelistResponse, FeedbackCreate
)
from .quarantine import QuarantineService
from .whitelist import WhitelistService
from .isolation import IsolationService
from .feedback import FeedbackService
from shared.logger import setup_logger
from shared.exceptions import ValidationError

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


# ═══════════════════════════════════════════════════════════════
# QUARANTINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════

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
        logger.error(f"❌ Quarantine failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quarantine")
async def list_quarantine(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List quarantined files.
    
    Example:
        GET /api/layer4/quarantine?limit=50
    """
    try:
        result = QuarantineService.list_quarantine(db, limit)
        return {
            "total": result["total"],
            "quarantine": [QuarantineResponse.from_orm(q) for q in result["quarantined"]]
        }
    except Exception as e:
        logger.error(f"❌ Failed to list quarantine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quarantine/{quarantine_id}/restore")
async def restore_file(
    quarantine_id: int,
    restore_data: QuarantineRestore,
    db: Session = Depends(get_db)
):
    """
    Restore quarantined file (analyst approval required).
    
    Example:
        POST /api/layer4/quarantine/1/restore
        {
            "restore_reason": "Verified as benign (false positive)"
        }
    """
    try:
        quarantine = QuarantineService.restore_file(quarantine_id, db, restore_data)
        return QuarantineResponse.from_orm(quarantine)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quarantine/stats")
async def get_quarantine_stats(db: Session = Depends(get_db)):
    """Get quarantine statistics."""
    try:
        stats = QuarantineService.get_quarantine_stats(db)
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# WHITELIST ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/whitelist")
async def add_whitelist(
    whitelist_data: WhitelistCreate,
    db: Session = Depends(get_db)
):
    """
    Add path to whitelist.
    
    Tiers:
    - 1: Path only (e.g., C:\\Program Files\\...)
    - 2: Path + Hash (e.g., C:\\malware.exe + hash)
    - 3: Hash only (identify file by hash anywhere)
    
    Example:
        POST /api/layer4/whitelist
        {
            "tier": 2,
            "path": "C:\\Program Files\\WinRAR\\WinRAR.exe",
            "hash_sha256": "abc123...",
            "reason": "Trusted application",
            "added_by": "analyst@company.com"
        }
    """
    try:
        whitelist = WhitelistService.add_whitelist(db, whitelist_data)
        return WhitelistResponse.from_orm(whitelist)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Failed to add whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whitelist")
async def list_whitelist(
    db: Session = Depends(get_db),
    tier: int = Query(None, ge=1, le=3),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List whitelist entries (optionally filter by tier).
    
    Example:
        GET /api/layer4/whitelist?tier=2&limit=50
    """
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
        logger.error(f"❌ Failed to list whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whitelist/check")
async def check_whitelist(
    file_path: str,
    file_hash: str = None,
    db: Session = Depends(get_db)
):
    """
    Check if file is whitelisted.
    
    Example:
        POST /api/layer4/whitelist/check?file_path=C:\\WinRAR.exe&file_hash=abc123...
    """
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
        logger.error(f"❌ Whitelist check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/whitelist/{whitelist_id}")
async def remove_whitelist(
    whitelist_id: int,
    db: Session = Depends(get_db)
):
    """Remove whitelist entry."""
    try:
        WhitelistService.remove_whitelist(db, whitelist_id)
        logger.info(f"✏️  Removed whitelist: {whitelist_id}")
        return {"deleted": True, "id": whitelist_id}
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Failed to remove whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whitelist/stats")
async def get_whitelist_stats(db: Session = Depends(get_db)):
    """Get whitelist statistics."""
    try:
        stats = WhitelistService.get_whitelist_stats(db)
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# ISOLATION ENDPOINTS
# ═════════════════════════════════════════════════════════════��═

@router.post("/isolate/process/{process_id}")
async def isolate_process(
    process_id: int,
    force: bool = Query(False)
):
    """
    Kill a malicious process by PID.
    
    Example:
        POST /api/layer4/isolate/process/1234?force=true
    """
    try:
        success = IsolationService.kill_process(process_id, force=force)
        
        if success:
            return {"killed": True, "process_id": process_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to kill process")
    
    except Exception as e:
        logger.error(f"❌ Isolation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/isolate/process-name/{process_name}")
async def isolate_process_by_name(
    process_name: str,
    force: bool = Query(False)
):
    """
    Kill a process by name.
    
    Example:
        POST /api/layer4/isolate/process-name/malware.exe?force=true
    """
    try:
        success = IsolationService.kill_process_by_name(process_name, force=force)
        
        if success:
            return {"killed": True, "process_name": process_name}
        else:
            return {"killed": False, "process_name": process_name, "message": "Process not found"}
    
    except Exception as e:
        logger.error(f"❌ Isolation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# FEEDBACK ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/incidents/{incident_id}/feedback")
async def submit_incident_feedback(
    incident_id: int,
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    Submit analyst feedback on incident (TP/FP/UNKNOWN).
    
    Example:
        POST /api/layer4/incidents/1/feedback
        {
            "feedback_type": "FP",
            "analyst_comment": "Legitimate file, false alarm"
        }
    """
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
        logger.error(f"❌ Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats")
async def get_feedback_stats(db: Session = Depends(get_db)):
    """Get feedback statistics (for model learning)."""
    try:
        stats = FeedbackService.get_feedback_stats(db)
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get feedback stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))