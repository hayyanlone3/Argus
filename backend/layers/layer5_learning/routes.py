# backend/layers/layer5_learning/routes.py
"""
Layer 5: Learning API Endpoints
Model statistics and retraining control
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Feedback, Incident
from .retrainer import RetrainingService
from .scheduler import LearningScheduler
from shared.logger import setup_logger
from datetime import datetime, timedelta

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Layer 5: Learning Engine health check."""
    return {
        "layer": 5,
        "name": "Learning Engine",
        "status": "operational",
        "features": [
            "Weekly automated retraining",
            "Feedback integration",
            "Model evaluation",
            "Quality metrics tracking"
        ],
        "next_retrain": "Friday 23:00 UTC"
    }


@router.get("/stats")
async def get_learning_stats(db: Session = Depends(get_db)):
    """
    Get learning model statistics.
    
    Example:
        GET /api/layer5/stats
    """
    try:
        # Get data from past week
        weekly_data = RetrainingService.get_weekly_data(db, days=7)
        
        # Get all-time data
        all_incidents = db.query(Incident).count()
        all_feedbacks = db.query(Feedback).count()
        
        # Evaluate quality
        quality = RetrainingService.evaluate_model_quality(weekly_data)
        
        return {
            "weekly_stats": {
                "incidents": len(weekly_data["incidents"]),
                "feedbacks": len(weekly_data["feedbacks"]),
                "tp_count": weekly_data["tp_count"],
                "fp_count": weekly_data["fp_count"],
                "unknown_count": weekly_data["unknown_count"],
                "fp_rate_percent": round(weekly_data["fp_rate"], 2),
                "data_quality_percent": round(weekly_data["data_quality"], 2)
            },
            "all_time_stats": {
                "total_incidents": all_incidents,
                "total_feedbacks": all_feedbacks
            },
            "model_quality": quality,
            "schedule": "Every Friday at 23:00 UTC"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain")
async def trigger_retraining(db: Session = Depends(get_db)):
    """
    Manually trigger retraining (normally runs Friday 23:00 UTC).
    
    Example:
        POST /api/layer5/retrain
    """
    try:
        logger.info("🔄 Manual retraining triggered via API")
        
        result = RetrainingService.retrain_model(db)
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Retraining failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info")
async def get_model_info():
    """
    Get current model information.
    
    Example:
        GET /api/layer5/model-info
    """
    try:
        return {
            "version": "2.2.0",
            "deployment_date": "2026-04-13",
            "days_deployed": 0,
            "model_maturity": "Early (Day 0-14)",
            "components": {
                "layer_2a": "Math Certainty (entropy, spawn rate)",
                "layer_2b": "Statistical Impossibility (P-matrix)",
                "layer_2c": "ML Anomaly (River HalfSpaceTrees)"
            },
            "retraining_schedule": {
                "day": "Friday",
                "time_utc": "23:00",
                "frequency": "Weekly"
            },
            "quality_thresholds": {
                "fp_rate_max_percent": 5.0,
                "data_quality_min_percent": 30.0,
                "min_tp_samples_per_week": 5
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback-quality")
async def get_feedback_quality(db: Session = Depends(get_db)):
    """
    Get feedback data quality metrics.
    
    Example:
        GET /api/layer5/feedback-quality
    """
    try:
        # Last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        feedbacks = db.query(Feedback).filter(Feedback.timestamp >= cutoff).all()
        incidents = db.query(Incident).filter(Incident.created_at >= cutoff).all()
        
        tp = len([f for f in feedbacks if f.feedback_type == "TP"])
        fp = len([f for f in feedbacks if f.feedback_type == "FP"])
        unknown = len([f for f in feedbacks if f.feedback_type == "UNKNOWN"])
        
        feedback_rate = (len(feedbacks) / len(incidents) * 100) if incidents else 0
        
        return {
            "period_days": 7,
            "feedback_count": len(feedbacks),
            "incident_count": len(incidents),
            "feedback_rate_percent": round(feedback_rate, 1),
            "breakdown": {
                "true_positives": tp,
                "false_positives": fp,
                "unknown": unknown
            },
            "false_positive_rate_percent": round((fp / len(feedbacks) * 100) if feedbacks else 0, 2),
            "quality_status": "Good" if feedback_rate > 50 else "Needs improvement"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get feedback quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-progress")
async def get_training_progress(db: Session = Depends(get_db)):
    """
    Get training progress metrics.
    
    Example:
        GET /api/layer5/training-progress
    """
    try:
        # Count incidents by severity
        incidents = db.query(Incident).all()
        
        critical = len([i for i in incidents if i.severity.value == "CRITICAL"])
        warning = len([i for i in incidents if i.severity.value == "WARNING"])
        unknown = len([i for i in incidents if i.severity.value == "UNKNOWN"])
        benign = len([i for i in incidents if i.severity.value == "BENIGN"])
        
        # Calculate model maturity (placeholder)
        days_deployed = 0
        if incidents:
            oldest = min(i.created_at for i in incidents)
            days_deployed = (datetime.utcnow() - oldest).days
        
        maturity_score = min(days_deployed / 14 * 100, 100)  # 100% at 14 days
        
        return {
            "days_deployed": days_deployed,
            "model_maturity_percent": round(maturity_score, 1),
            "incident_distribution": {
                "critical": critical,
                "warning": warning,
                "unknown": unknown,
                "benign": benign,
                "total": len(incidents)
            },
            "status": (
                "Mature (>14 days)" if days_deployed >= 14
                else "Growing (7-14 days)" if days_deployed >= 7
                else "Early (0-7 days)"
            )
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get training progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))