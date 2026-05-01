from sqlalchemy import create_engine, text
from backend.config import settings

# Connect to database
engine = create_engine(settings.database_url)

try:
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'incidents' 
            AND column_name IN ('detection_seconds', 'first_event_timestamp')
        """))
        existing_columns = [row[0] for row in result]
        
        print(f"\nExisting columns: {existing_columns}")
        
        # Add detection_seconds if it doesn't exist
        if 'detection_seconds' not in existing_columns:
            print("\n1. Adding 'detection_seconds' column...")
            conn.execute(text("""
                ALTER TABLE incidents 
                ADD COLUMN detection_seconds DOUBLE PRECISION
            """))
            conn.commit()
            print("   ✅ Added 'detection_seconds' column")
        else:
            print("\n1. Column 'detection_seconds' already exists ✓")
        
        # Add first_event_timestamp if it doesn't exist
        if 'first_event_timestamp' not in existing_columns:
            print("\n2. Adding 'first_event_timestamp' column...")
            conn.execute(text("""
                ALTER TABLE incidents 
                ADD COLUMN first_event_timestamp TIMESTAMP
            """))
            conn.commit()
            print("   ✅ Added 'first_event_timestamp' column")
        else:
            print("\n2. Column 'first_event_timestamp' already exists ✓")
        
        # Verify columns were added
        print("\n3. Verifying columns...")
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'incidents'
            ORDER BY ordinal_position
        """))
        
        print("\n   Incidents table columns:")
        for row in result:
            print(f"     - {row[0]}: {row[1]}")
        
        print("\n" + "=" * 80)
        print("✅ SUCCESS! Columns added to database")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Restart backend: cd backend && python main.py")
        print("2. Run simulation: python backend/simulations/aggressive_malware.py")
        print("3. Check dashboard: http://localhost:5173/layer3")
        print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL is running")
    print("2. Check database credentials in backend/.env")
    print("3. Verify database URL:", settings.database_url)
    exit(1)
