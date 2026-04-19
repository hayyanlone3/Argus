import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import PolicyConfig
from backend.database.schemas import PolicyConfigOut, PolicyConfigUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/layer4/policy", response_model=PolicyConfigOut)
def get_policy(db: Session = Depends(get_db)):
    """Fetch the active policy. If none exists, create the default singleton."""
    policy = db.query(PolicyConfig).first()
    if not policy:
        # Create and commit the default row if table is empty
        policy = PolicyConfig(id=1, auto_response_enabled=False, kill_on_alert=False, quarantine_on_warn=False)
        db.add(policy)
        db.commit()
        db.refresh(policy)
        logger.info("🆕 Initialized default policy row in database.")
    return policy

@router.post("/api/layer4/policy", response_model=PolicyConfigOut)
def update_policy(payload: PolicyConfigUpdate, db: Session = Depends(get_db)):
    """Update existing policy or create it if missing."""
    policy = db.query(PolicyConfig).first()
    if not policy:
        policy = PolicyConfig(id=1)
        db.add(policy)
    
    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    
    db.commit()
    db.refresh(policy)
    logger.info(f"✅ Policy persisted: auto_response={policy.auto_response_enabled}, kill={policy.kill_on_alert}")
    return policy