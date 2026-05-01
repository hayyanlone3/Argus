# backend/database/connection.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from backend.config import settings
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)

engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal
    
    try:
        logger.info("  Connecting to database...")
        logger.info(f"   Database Type: {settings.database_type}")
        logger.info(f"   Database URL: {settings.database_url[:50]}...")
        
        # Create engine with appropriate pooling based on backend type
        db_url = settings.database_url
        is_sqlite = settings.database_type == "sqlite" or db_url.startswith("sqlite")

        if is_sqlite:
            engine = create_engine(
                db_url,
                echo=settings.sqlalchemy_echo,
                poolclass=NullPool,
                connect_args={"check_same_thread": False},
            )
        else:
            engine = create_engine(
                db_url,
                echo=settings.sqlalchemy_echo,
                pool_size=20,
                max_overflow=50,
                pool_timeout=30,
                pool_recycle=1800,
            )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        
        logger.info("  Database connection successful")
        
        # Create sessionmaker
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
        
        # Create all tables
        logger.info("  Creating database tables...")
        from backend.database.models import Base, PolicyConfig
        Base.metadata.create_all(bind=engine)
        
        # Insert default policy row if missing
        session = SessionLocal()
        try:
            if not session.query(PolicyConfig).filter_by(id=1).first():
                # Default to DISABLED - user should enable via UI after review
                policy = PolicyConfig(
                    id=1,
                    auto_response_enabled=False,
                    kill_on_alert=False,
                    quarantine_on_warn=False,
                    min_final_score_incident=0.5,
                )
                session.add(policy)
                session.commit()
                logger.info("  Default PolicyConfig initialized (auto-response DISABLED)")
            else:
                # Keep existing policy - don't override user settings
                policy = session.query(PolicyConfig).filter_by(id=1).first()
                logger.info(f"  Existing PolicyConfig loaded: auto_response={policy.auto_response_enabled}")
        except Exception as e:
            logger.error(f"  Error seeding default policy: {e}")
            session.rollback()
        finally:
            session.close()
        
        logger.info("  All tables created successfully")
        
        return engine
    
    except Exception as e:
        logger.error(f"  Database initialization failed: {e}")
        raise


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db():
    if engine:
        engine.dispose()
        logger.info("  Database connection closed")