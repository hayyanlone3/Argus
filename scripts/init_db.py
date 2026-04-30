import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.connection import init_db
from database.init_db import init_database, verify_connection, create_sample_data
from shared.logger import setup_logger

logger = setup_logger(__name__)


if __name__ == "__main__":
    try:
        # Initialize database connection and create tables
        init_db()
        
        # Verify tables were created
        if not init_database():
            sys.exit(1)
        
        # Verify connection works
        if not verify_connection():
            sys.exit(1)
        
        # Create sample data
        create_sample_data()
        
    except Exception as e:
        logger.error(f"  Initialization failed: {e}")
        sys.exit(1)