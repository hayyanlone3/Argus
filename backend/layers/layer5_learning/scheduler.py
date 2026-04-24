# backend/layers/layer5_learning/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from backend.database.connection import SessionLocal
from .retrainer import RetrainingService
from backend.shared.logger import setup_logger
from backend.config import settings

logger = setup_logger(__name__)

# Global scheduler instance
scheduler = None


class LearningScheduler:
    @staticmethod
    def init_scheduler():
        global scheduler
        
        try:
            if scheduler and scheduler.running:
                logger.warning(" Scheduler already running")
                return
            
            scheduler = BackgroundScheduler()
            
            # Parse schedule from config
            # Example: "Friday" + "23:00"
            day_name = settings.learning_retraining_day.lower()
            time_str = settings.learning_retraining_time
            
            hour, minute = map(int, time_str.split(":"))
            
            # Map day name to cron format
            day_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6
            }
            
            day_of_week = day_map.get(day_name, 4)  # Default: Friday
            
            logger.info(f"Scheduling retraining: {day_name.title()} at {time_str} UTC")
            
            # Add job: retrain weekly
            scheduler.add_job(
                LearningScheduler._retrain_job,
                CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
                id="weekly_retrain",
                name="Weekly Model Retraining",
                replace_existing=True
            )
            
            scheduler.start()
            logger.info("Learning scheduler started")
        
        except Exception as e:
            logger.error(f"Failed to init scheduler: {e}")
    
    @staticmethod
    def stop_scheduler():
        global scheduler
        
        try:
            if scheduler and scheduler.running:
                scheduler.shutdown()
                scheduler = None
                logger.info("Learning scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
    
    @staticmethod
    def _retrain_job():
        try:
            logger.info("Weekly retraining job triggered")
            
            db = SessionLocal()
            result = RetrainingService.retrain_model(db)
            db.close()
            
            logger.info(f"  Retraining job result: {result['status']}")
        
        except Exception as e:
            logger.error(f"  Retraining job failed: {e}")
    
    @staticmethod
    def trigger_manual_retrain():
        try:
            logger.info("  Manual retraining triggered")
            
            db = SessionLocal()
            result = RetrainingService.retrain_model(db)
            db.close()
            
            return result
        
        except Exception as e:
            logger.error(f"  Manual retrain failed: {e}")
            return {"status": "error", "reason": str(e)}