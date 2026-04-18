from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.database.models import AuditLog


class AuditLogger:
    @staticmethod
    def log(
        db: Session,
        *,
        source: str,
        action: str,
        level: str = "INFO",
        message: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        session_id: Optional[str] = None,
        path: Optional[str] = None,
        hash_sha256: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> AuditLog:
        row = AuditLog(
            level=level,
            source=source,
            action=action,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            session_id=session_id,
            path=path,
            hash_sha256=hash_sha256,
            payload=payload,
        )
        db.add(row)
        if commit:
            db.commit()
        return row