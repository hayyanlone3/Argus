# backend/database/connection.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from config import settings
from shared.logger import setup_logger

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
        
        # Create engine
        engine = create_engine(
            settings.database_url,
            echo=settings.sqlalchemy_echo,
            poolclass=NullPool,  # Single-threaded for ETW collection
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
        from database.models import Base
        Base.metadata.create_all(bind=engine)
        
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