from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import get_db, SessionLocal
from backend.database.models import PolicyConfig
from backend.database.schemas import PolicyConfigOut, PolicyConfigUpdate

router = APIRouter()

@router.get("/api/layer4/policy", response_model=PolicyConfigOut)
def get_policy(db: Session = Depends(get_db)):
    policy = db.query(PolicyConfig).filter_by(id=1).first()
    if not policy:
        raise HTTPException(404, "PolicyConfig not found")
    return policy

@router.post("/api/layer4/policy", response_model=PolicyConfigOut)
def update_policy(payload: PolicyConfigUpdate, db: Session = Depends(get_db)):
    policy = db.query(PolicyConfig).filter_by(id=1).first()
    if not policy:
        raise HTTPException(404, "PolicyConfig not found")
    # Only update provided fields
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return policy