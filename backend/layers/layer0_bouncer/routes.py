from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.schemas import VTCacheResponse
from backend.database.models import VTCache
from backend.shared.logger import setup_logger
from .services import BouncerService
import os
from pathlib import Path

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "layer": 0,
        "name": "Bouncer (Fast-Path Rejection)",
        "status": "operational",
        "features": [
            "VirusTotal hash lookup",
            "Entropy analysis (Tier 2/3)",
            "Digital signature verification",
            "Known packer detection"
        ]
    }


@router.post("/vt-lookup")
async def vt_lookup(
    file_hash: str,
    db: Session = Depends(get_db)
):

    try:
        if not file_hash or len(file_hash) != 64:
            raise HTTPException(status_code=400, detail="Invalid SHA256 hash")
        
        result = await BouncerService.vt_hash_lookup(file_hash, db)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  VT lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entropy-check")
async def entropy_check(
    file_path: str,
    file_size: int
):

    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        status, entropy_val = BouncerService.entropy_check(file_path, file_size)
        
        return {
            "status": status,
            "entropy": round(entropy_val, 2),
            "threshold": 7.9,
            "file_path": file_path,
            "file_size": file_size,
            "interpretation": {
                "PASS": "Normal entropy, likely benign",
                "WARN": "High entropy, requires further analysis",
                "CRITICAL": "Highly suspicious entropy signature"
            }.get(status, "Unknown")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Entropy check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-file")
async def analyze_file(
    file_path: str,
    db: Session = Depends(get_db)
):

    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        logger.info(f"  Analyzing file: {file_path}")
        logger.info(f"   Size: {file_size / 1024 / 1024:.2f} MB")
        
        # Calculate file hash first
        from .utils import calculate_file_hash
        file_hash = calculate_file_hash(file_path)
        
        # VT lookup with actual hash
        vt_score = 0.0
        if file_hash and len(file_hash) == 64:
            vt_result = await BouncerService.vt_hash_lookup(file_hash, db)
            vt_score = vt_result.get("score", 0.0)
        
        # Bouncer decision
        decision = BouncerService.bouncer_decision(file_path, file_size, vt_score, db)
        
        return decision
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  File analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vt-cache")
async def get_vt_cache(
    db: Session = Depends(get_db),
    limit: int = 100
):

    try:
        caches = db.query(VTCache).limit(limit).all()
        return {
            "total": len(caches),
            "caches": [
                {
                    "hash_sha256": c.hash_sha256,
                    "score": c.score,
                    "queried_at": c.queried_at.isoformat(),
                    "status": "malicious" if c.score > 0.5 else "suspicious" if c.score > 0.1 else "clean"
                }
                for c in caches
            ]
        }
    
    except Exception as e:
        logger.error(f"  Failed to fetch VT cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from backend.database.models import VTCache, AuditLog

@router.get("/recent-analysis")
async def get_recent_analysis(
    db: Session = Depends(get_db),
    limit: int = 50
):

    try:
        from backend.database.models import AuditLog
        logs = db.query(AuditLog).filter(
            AuditLog.source == "layer0.auto_scan"
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "path": log.path,
                "status": log.payload.get("status") if log.payload else "UNKNOWN",
                "entropy": log.payload.get("entropy") if log.payload else 0.0,
                "vt_score": log.payload.get("vt_score") if log.payload else 0.0,
                "signals": log.payload.get("signals") if log.payload else [],
                "message": log.message
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"  Failed to fetch recent analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vt-cache/{hash_sha256}")
async def delete_vt_cache_entry(
    hash_sha256: str,
    db: Session = Depends(get_db)
):

    try:
        cache_entry = db.query(VTCache).filter(VTCache.hash_sha256 == hash_sha256).first()
        
        if not cache_entry:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        db.delete(cache_entry)
        db.commit()
        
        logger.info(f"Deleted VT cache: {hash_sha256[:16]}...")
        return {"deleted": True, "hash": hash_sha256}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Failed to delete cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))