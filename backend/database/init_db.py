import sys
import os
from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine, SessionLocal
from database.models import Base
from shared.logger import setup_logger
from config import settings

logger = setup_logger(__name__)


def init_database():
    try:
        logger.info("=" * 80)
        logger.info("INITIALIZING DATABASE")
        logger.info("=" * 80)
        logger.info(f"Database Type: {settings.database_type}")
        logger.info(f"Database URL: {settings.database_url[:60]}...")
        logger.info("")
        
        # Create all tables
        logger.info("Creating all tables...")
        from database.connection import init_db
        init_db()
        logger.info("All tables created successfully")
        logger.info("")
        
        # Verify tables exist
        logger.info("Verifying tables...")
        from database.connection import engine as conn_engine
        inspector = inspect(conn_engine)
        tables = inspector.get_table_names()
        
        expected_tables = {
            'nodes', 'edges', 'incidents', 'quarantine', 
            'whitelist', 'vt_cache', 'feedback'
        }
        
        created_tables = set(tables)
        
        for table in expected_tables:
            if table in created_tables:
                logger.info(f"{table}")
            else:
                logger.error(f"{table} (MISSING)")
                return False
        
        logger.info("")
        logger.info(f"All {len(expected_tables)} tables verified")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def verify_connection():
    try:
        logger.info("")
        logger.info("Testing database connection...")
        
        db = connection.SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        logger.info("Database connection verified")
        return True
    
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def create_sample_data():
    try:
        from database.models import Node
        from shared.enums import NodeType
        
        logger.info("")
        logger.info("Creating sample data...")
        
        db = connection.SessionLocal()
        
        # Check if sample data already exists
        existing = db.query(Node).first()
        if existing:
            logger.info("Sample data already exists, skipping")
            db.close()
            return True
        
        # Create sample process node
        sample_node = Node(
            type=NodeType.PROCESS,
            name="explorer.exe",
            path="C:\\Windows\\explorer.exe",
            hash_sha256="abc123def456",
            path_risk=0.0
        )
        
        db.add(sample_node)
        db.commit()
        
        logger.info("Sample data created successfully")
        db.close()
        return True
    
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        return False


if __name__ == "__main__":
    logger.info("")
    logger.info("ARGUS v2.2 Database Initialization")
    logger.info("=" * 80)
    logger.info("")
    
    # Initialize database
    if not init_database():
        sys.exit(1)
    
    # Verify connection
    if not verify_connection():
        sys.exit(1)
    
    # Create sample data
    create_sample_data()
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("DATABASE READY!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Start backend: python -m uvicorn main:app --reload")
    logger.info("  2. Access API: http://localhost:8000/docs")
    logger.info("  3. Check health: curl http://localhost:8000/health")
    logger.info("")