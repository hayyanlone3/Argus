#!/usr/bin/env python
# scripts/init_db.py
"""
Database initialization script.
Creates all tables and verifies connection.

Usage:
    python scripts/init_db.py
"""

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
        print("\n" + "="*80)
        print("ARGUS v2.2 — Database Initialization")
        print("="*80 + "\n")
        
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
        
        print("\n" + "="*80)
        print("🎉 DATABASE INITIALIZATION COMPLETE!")
        print("="*80 + "\n")
        print("Next steps:")
        print("  1. Start backend: python -m uvicorn main:app --reload")
        print("  2. Access API: http://localhost:8000/docs")
        print("  3. Test health: curl http://localhost:8000/health")
        print("\n")
        
    except Exception as e:
        logger.error(f"  Initialization failed: {e}")
        sys.exit(1)