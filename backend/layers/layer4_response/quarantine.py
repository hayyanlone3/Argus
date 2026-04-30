# backend/layers/layer4_response/quarantine.py
"""
Layer 4: Quarantine Service
Isolates suspicious files from execution
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.models import Quarantine
from backend.database.schemas import QuarantineCreate, QuarantineRestore
from backend.config import settings
from backend.shared.logger import setup_logger
from backend.shared.exceptions import ValidationError, DatabaseError

logger = setup_logger(__name__)


class QuarantineService:
    """Layer 4: Quarantine Management Service"""
    
    @staticmethod
    def quarantine_file(
        file_path: str,
        db: Session,
        quarantine_data: QuarantineCreate
    ) -> Quarantine:
        """
        Move suspicious file to quarantine directory.
        Store metadata in database.
        
        Args:
            file_path: Path to file on disk
            db: Database session
            quarantine_data: Quarantine metadata
            
        Returns:
            Quarantine record
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise ValidationError(f"File not found: {file_path}")
            
            logger.info(f"Quarantining file: {file_path}")
            
            # Ensure quarantine directory exists
            quarantine_dir = Path(settings.quarantine_dir)
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate quarantine filename (hash_originalname)
            original_name = Path(file_path).name
            quarantine_filename = f"{quarantine_data.hash_sha256}_{original_name}"
            quarantine_path = quarantine_dir / quarantine_filename
            
            # Move file
            try:
                shutil.move(file_path, str(quarantine_path))
                logger.info(f"  File moved: {file_path} → {quarantine_path}")
            except PermissionError:
                logger.error(f"  Permission denied: cannot quarantine {file_path}")
                raise ValidationError(f"Cannot quarantine file (permission denied): {file_path}")
            except Exception as e:
                logger.error(f"  Failed to move file: {e}")
                raise ValidationError(f"Failed to quarantine file: {e}")
            
            # Store in database
            quarantine = Quarantine(
                original_path=file_path,
                hash_sha256=quarantine_data.hash_sha256,
                detection_layer=quarantine_data.detection_layer,
                confidence=quarantine_data.confidence,
                session_id=quarantine_data.session_id,
                mitre_stage=quarantine_data.mitre_stage,
                quarantine_path=str(quarantine_path),
                quarantined_at=datetime.utcnow(),
                status="QUARANTINED"
            )
            
            db.add(quarantine)
            db.commit()
            db.refresh(quarantine)
            
            logger.info(f"  Quarantine record created: {quarantine.id}")
            return quarantine
        
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"  Quarantine failed: {e}")
            db.rollback()
            raise DatabaseError(f"Failed to quarantine file: {e}")
    
    @staticmethod
    def restore_file(
        quarantine_id: int,
        db: Session,
        restore_data: QuarantineRestore
    ) -> Quarantine:
        """
        Restore quarantined file to original location.
        Only after analyst verification.
        
        Args:
            quarantine_id: Quarantine record ID
            db: Database session
            restore_data: Restore metadata
            
        Returns:
            Updated Quarantine record
        """
        try:
            quarantine = db.query(Quarantine).filter(Quarantine.id == quarantine_id).first()
            
            if not quarantine:
                raise ValidationError("Quarantine record not found")
            
            if quarantine.status != "QUARANTINED":
                raise ValidationError(f"Cannot restore: status is {quarantine.status}")
            
            logger.info(f"🔓 Restoring file: {quarantine.quarantine_path} → {quarantine.original_path}")
            
            # Move file back
            if os.path.exists(quarantine.quarantine_path):
                try:
                    # Ensure target directory exists
                    target_dir = Path(quarantine.original_path).parent
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    shutil.move(quarantine.quarantine_path, quarantine.original_path)
                    logger.info(f"  File restored: {quarantine.original_path}")
                except PermissionError:
                    raise ValidationError(f"Cannot restore: permission denied")
                except Exception as e:
                    raise ValidationError(f"Failed to restore: {e}")
            else:
                logger.warning(f"   Quarantined file not found: {quarantine.quarantine_path}")
            
            # Update database
            quarantine.status = "RESTORED"
            quarantine.restored_at = datetime.utcnow()
            quarantine.restore_reason = restore_data.restore_reason
            
            db.commit()
            db.refresh(quarantine)
            
            logger.info(f"  Restore completed: {quarantine_id}")
            return quarantine
        
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"  Restore failed: {e}")
            db.rollback()
            raise DatabaseError(f"Failed to restore file: {e}")
    
    @staticmethod
    def list_quarantine(db: Session, limit: int = 100) -> dict:

        try:
            quarantined = db.query(Quarantine).filter(
                Quarantine.status == "QUARANTINED"
            ).order_by(Quarantine.quarantined_at.desc()).limit(limit).all()
            
            logger.debug(f"📋 Listed {len(quarantined)} quarantined files")
            
            return {
                "total": len(quarantined),
                "quarantined": quarantined
            }
        
        except Exception as e:
            logger.error(f"  Failed to list quarantine: {e}")
            return {"total": 0, "quarantined": []}
    
    @staticmethod
    def get_quarantine_stats(db: Session) -> dict:
        """
        Get quarantine statistics.
        
        Args:
            db: Database session
            
        Returns:
            {
                "total_quarantined": int,
                "total_restored": int,
                "by_layer": {...}
            }
        """
        try:
            total_quarantined = db.query(Quarantine).filter(
                Quarantine.status == "QUARANTINED"
            ).count()
            
            total_restored = db.query(Quarantine).filter(
                Quarantine.status == "RESTORED"
            ).count()
            
            # Count by detection layer
            by_layer = {}
            layers = db.query(Quarantine.detection_layer).distinct().all()
            for (layer,) in layers:
                count = db.query(Quarantine).filter(
                    Quarantine.detection_layer == layer,
                    Quarantine.status == "QUARANTINED"
                ).count()
                if layer:
                    by_layer[layer] = count
            
            return {
                "total_quarantined": total_quarantined,
                "total_restored": total_restored,
                "by_detection_layer": by_layer
            }
        
        except Exception as e:
            logger.error(f"  Failed to get quarantine stats: {e}")
            return {}