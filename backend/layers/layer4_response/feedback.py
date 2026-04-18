# backend/layers/layer4_response/feedback.py
"""
Layer 4: Feedback Service
Collects analyst feedback for model improvement
"""

from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.models import Feedback
from backend.database.schemas import FeedbackCreate
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)


class FeedbackService:
    """Layer 4: Feedback Service (for Layer 5 learning)"""
    
    @staticmethod
    def submit_feedback(
        db: Session,
        incident_id: int,
        feedback_data: FeedbackCreate
    ) -> Feedback:
        """
        Submit analyst feedback on incident.
        
        Feedback types:
        - TP (True Positive): Correctly detected threat
        - FP (False Positive): Incorrectly flagged benign
        - UNKNOWN: Cannot determine
        
        Args:
            db: Database session
            incident_id: Incident ID
            feedback_data: Feedback data
            
        Returns:
            Feedback record
        """
        try:
            # Validate feedback type
            if feedback_data.feedback_type not in ["TP", "FP", "UNKNOWN"]:
                raise ValueError("Invalid feedback type")
            
            feedback = Feedback(
                incident_id=incident_id,
                feedback_type=feedback_data.feedback_type,
                analyst_comment=feedback_data.analyst_comment,
                timestamp=datetime.utcnow()
            )
            
            db.add(feedback)
            db.commit()
            db.refresh(feedback)
            
            logger.info(f"📝 Feedback submitted: incident {incident_id} = {feedback_data.feedback_type}")
            return feedback
        
        except Exception as e:
            logger.error(f"❌ Failed to submit feedback: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def get_feedback_stats(db: Session) -> dict:
        """
        Get feedback statistics for model learning.
        
        Args:
            db: Database session
            
        Returns:
            {
                "total_feedback": int,
                "tp_count": int,
                "fp_count": int,
                "fp_rate": float
            }
        """
        try:
            feedbacks = db.query(Feedback).all()
            
            tp_count = len([f for f in feedbacks if f.feedback_type == "TP"])
            fp_count = len([f for f in feedbacks if f.feedback_type == "FP"])
            total = len(feedbacks)
            
            fp_rate = (fp_count / total * 100) if total > 0 else 0
            
            return {
                "total_feedback": total,
                "tp_count": tp_count,
                "fp_count": fp_count,
                "fp_rate": round(fp_rate, 2)
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get feedback stats: {e}")
            return {}