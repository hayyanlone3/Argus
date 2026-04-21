# backend/config.py
from pydantic_settings import BaseSettings
from typing import Literal
import os


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    api_workers: int = 1

    database_type: Literal["sqlite", "postgresql"] = "postgresql"
    database_url: str = "postgresql://argus:8888@localhost:5432/argus_db"
    sqlalchemy_echo: bool = False
    
    secret_key: str = "your-secret-key-change-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    virustotal_api_key: str = ""
    vt_cache_ttl_days: int = 7
    

    quarantine_dir: str = r"C:\ProgramData\ARGUS\quarantine"
    log_dir: str = r"C:\ProgramData\ARGUS\logs"
    db_backup_dir: str = r"C:\ProgramData\ARGUS\backups"
    
    bouncer_entropy_threshold: float = 7.9
    bouncer_pmatrix_threshold: float = 0.001
    
    scoring_2a_spawn_anomaly_sigma: float = 3.0
    scoring_2b_pmatrix_threshold: float = 0.001
    scoring_2c_ml_threshold: float = 0.60
    

    correlation_max_hops: int = 2
    correlation_require_signals: int = 2
    
    graph_active_window_hours: int = 24
    graph_archive_retention_days: int = 30
    
    learning_retraining_day: str = "Friday"
    learning_retraining_time: str = "23:00"
    learning_fp_rate_threshold: float = 0.05
    learning_retrain_batch_size: int = 500
    
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    log_file: str = "argus_backend.log"
    

    testing: bool = False
    test_database_url: str = "sqlite:///./test.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # IMPORTANT: Allow extra fields from .env (like SERVICE_NAME)
        extra = "ignore"  # Ignore unknown variables in .env


# Load settings from .env
settings = Settings()

# Ensure directories exist
import os
os.makedirs(settings.log_dir, exist_ok=True)
os.makedirs(settings.quarantine_dir, exist_ok=True)
os.makedirs(settings.db_backup_dir, exist_ok=True)