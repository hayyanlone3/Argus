# backend/layers/layer4_response/whitelist.py
"""
Layer 4: Whitelist Service
3-tier whitelist system for trusted software
"""

from sqlalchemy.orm import Session
from backend.database.models import Whitelist
from backend.database.schemas import WhitelistCreate
from backend.shared.constants import NEVER_TIER1_WHITELIST
from backend.shared.logger import setup_logger
from backend.shared.exceptions import ValidationError
from datetime import datetime

logger = setup_logger(__name__)


class WhitelistService:
    """Layer 4: Whitelist Management Service"""
    
    @staticmethod
    def add_whitelist(
        db: Session,
        whitelist_data: WhitelistCreate
    ) -> Whitelist:
        """
        Add path to whitelist (Tier 1/2/3).
        
        Tiers:
        - Tier 1: Path only (no hash), Microsoft-signed binaries, lowest false positive rate
        - Tier 2: Path + Hash binding, trusted applications with version control
        - Tier 3: Hash only, specific file versions, highest specificity
        
        Args:
            db: Database session
            whitelist_data: Whitelist creation data
            
        Returns:
            Whitelist record
        """
        try:
            # Validate Tier 1 constraints
            if whitelist_data.tier == 1:
                exe_name = whitelist_data.path.split("\\")[-1].lower()
                
                # High-risk executables cannot be Tier 1
                if exe_name in NEVER_TIER1_WHITELIST:
                    raise ValidationError(
                        f"Cannot Tier 1 whitelist '{exe_name}' — too risky. Use Tier 2 (path+hash) instead."
                    )
                
                # Tier 1 should not have hash (reduces false positives)
                if whitelist_data.hash_sha256:
                    logger.warning(f"   Tier 1 whitelist should not have hash: {whitelist_data.path}")
            
            # Validate Tier 2/3 constraints
            elif whitelist_data.tier in [2, 3]:
                if not whitelist_data.hash_sha256:
                    raise ValidationError(
                        f"Tier {whitelist_data.tier} whitelist requires hash_sha256 binding"
                    )
            
            else:
                raise ValidationError("Tier must be 1, 2, or 3")
            
            # Check for duplicates
            existing = db.query(Whitelist).filter(
                Whitelist.tier == whitelist_data.tier,
                Whitelist.path == whitelist_data.path,
                Whitelist.hash_sha256 == whitelist_data.hash_sha256
            ).first()
            
            if existing:
                logger.warning(f"   Whitelist entry already exists: {whitelist_data.path}")
                return existing
            
            # Create entry
            whitelist = Whitelist(
                tier=whitelist_data.tier,
                path=whitelist_data.path,
                hash_sha256=whitelist_data.hash_sha256,
                reason=whitelist_data.reason,
                added_by=whitelist_data.added_by,
                added_at=datetime.utcnow()
            )
            
            db.add(whitelist)
            db.commit()
            db.refresh(whitelist)
            
            logger.info(f"  Added whitelist (Tier {whitelist_data.tier}): {whitelist_data.path}")
            return whitelist
        
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"  Failed to add whitelist: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def check_whitelist(
        db: Session,
        file_path: str,
        file_hash: str = None
    ) -> tuple:
        """
        Check if file is whitelisted.
        
        Args:
            db: Database session
            file_path: File path
            file_hash: SHA256 hash (optional)
            
        Returns:
            (is_whitelisted: bool, tier: int or None, reason: str)
        """
        try:
            # Tier 1: Path-only match (highest priority - trusted locations)
            tier1 = db.query(Whitelist).filter(
                Whitelist.tier == 1,
                Whitelist.path == file_path
            ).first()
            
            if tier1:
                logger.debug(f"  Whitelist match (Tier 1): {file_path}")
                return (True, 1, tier1.reason or "Tier 1 path match")
            
            # Tier 2: Path + Hash match
            tier2 = db.query(Whitelist).filter(
                Whitelist.tier == 2,
                Whitelist.path == file_path,
                Whitelist.hash_sha256 == file_hash
            ).first()
            
            if tier2:
                logger.debug(f"  Whitelist match (Tier 2): {file_path} (hash verified)")
                return (True, 2, tier2.reason or "Tier 2 path+hash match")
            
            # Tier 3: Hash-only match (for files moved to different locations)
            if file_hash:
                tier3 = db.query(Whitelist).filter(
                    Whitelist.tier == 3,
                    Whitelist.hash_sha256 == file_hash
                ).first()
                
                if tier3:
                    logger.debug(f"  Whitelist match (Tier 3): {file_hash} (hash-only)")
                    return (True, 3, tier3.reason or "Tier 3 hash match")
            
            logger.debug(f"  No whitelist match: {file_path}")
            return (False, None, "Not whitelisted")
        
        except Exception as e:
            logger.error(f"  Whitelist check failed: {e}")
            return (False, None, "Error checking whitelist")
    
    @staticmethod
    def remove_whitelist(db: Session, whitelist_id: int) -> bool:
        """
        Remove whitelist entry.
        
        Args:
            db: Database session
            whitelist_id: Whitelist record ID
            
        Returns:
            True if successful
        """
        try:
            whitelist = db.query(Whitelist).filter(Whitelist.id == whitelist_id).first()
            
            if not whitelist:
                raise ValidationError("Whitelist entry not found")
            
            db.delete(whitelist)
            db.commit()
            
            logger.info(f"   Removed whitelist: {whitelist_id}")
            return True
        
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"  Failed to remove whitelist: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def get_whitelist_stats(db: Session) -> dict:
        """
        Get whitelist statistics.
        
        Args:
            db: Database session
            
        Returns:
            {
                "total": int,
                "by_tier": {...}
            }
        """
        try:
            total = db.query(Whitelist).count()
            
            by_tier = {}
            for tier in [1, 2, 3]:
                count = db.query(Whitelist).filter(Whitelist.tier == tier).count()
                by_tier[f"tier_{tier}"] = count
            
            return {
                "total_whitelisted": total,
                "by_tier": by_tier
            }
        
        except Exception as e:
            logger.error(f"  Failed to get whitelist stats: {e}")
            return {}