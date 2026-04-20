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
    """Initialize database connection and create all tables."""
    global engine, SessionLocal
    
    try:
        logger.info("🔌 Connecting to database...")
        logger.info(f"   Database Type: {settings.database_type}")
        logger.info(f"   Database URL: {settings.database_url[:50]}...")
        
        # Create engine with robust connection pooling for high-throughput collectors
        engine = create_engine(
            settings.database_url,
            echo=settings.sqlalchemy_echo,
            pool_size=20,          # Keep 20 connections open
            max_overflow=50,       # Allow up to 50 bursts
            pool_timeout=30,
            pool_recycle=1800,     # Recycle connections every 30m
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        
        logger.info("✅ Database connection successful")
        
        # Create sessionmaker
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
        
        # Create all tables
        logger.info("📊 Creating database tables...")
        from backend.database.models import Base, PolicyConfig
        Base.metadata.create_all(bind=engine)
        
        # Insert default policy row if missing
        session = SessionLocal()
        try:
            if not session.query(PolicyConfig).filter_by(id=1).first():
                # Default to enabled in local/demo so suspicious activity auto-contains
                policy = PolicyConfig(
                    id=1,
                    auto_response_enabled=True,
                    kill_on_alert=True,
                    quarantine_on_warn=True,
                    min_final_score_incident=0.5,
                )
                session.add(policy)
                session.commit()
                logger.info("✅ Default PolicyConfig initialized")
            else:
                # FORCE ENABLE for Demo
                policy = session.query(PolicyConfig).filter_by(id=1).first()
                policy.auto_response_enabled = True
                policy.kill_on_alert = True
                policy.quarantine_on_warn = True
                session.commit()
                logger.info("✅ PolicyConfig FORCE-ENABLED for demo")
        except Exception as e:
            logger.error(f"❌ Error seeding default policy: {e}")
            session.rollback()
        finally:
            session.close()
        
        logger.info("✅ All tables created successfully")
        
        return engine
    
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def get_db() -> Session:
    """Get database session for dependency injection in FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db():
    """Close database connection."""
    if engine:
        engine.dispose()
        logger.info("✅ Database connection closed")