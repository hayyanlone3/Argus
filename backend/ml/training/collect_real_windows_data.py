"""
Collect REAL Windows telemetry data for training.

This script collects actual Windows process events from your ARGUS database
to train the ML model on real behavior instead of synthetic data.
"""

import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import os

def collect_windows_telemetry(days_back: int = 30, min_samples: int = 1000):
    """
    Collect real Windows telemetry from ARGUS database.
    
    Args:
        days_back: How many days of history to collect
        min_samples: Minimum samples needed for training
    
    Returns:
        DataFrame with real Windows process events
    """
    
    # Connect to your PostgreSQL database
    db_url = os.getenv("DATABASE_URL", "postgresql://argus:8888@localhost:5432/argus_db")
    engine = create_engine(db_url)
    
    print(f"Collecting Windows telemetry from last {days_back} days...")
    
    # Query real process creation events from edges table
    query = f"""
    SELECT 
        parent.name as parent_process,
        child.name as child_process,
        e.entropy_value as entropy,
        e.p_matrix_score,
        e.ml_anomaly_score,
        e.final_severity,
        e.timestamp
    FROM edges e
    JOIN nodes parent ON e.source_id = parent.id
    JOIN nodes child ON e.target_id = child.id
    WHERE 
        e.edge_type = 'SPAWNED'
        AND e.timestamp >= NOW() - INTERVAL '{days_back} days'
    ORDER BY e.timestamp DESC
    """
    
    df = pd.read_sql(query, engine)
    
    print(f"  Collected {len(df)} real Windows events")
    
    if len(df) < min_samples:
        print(f"   WARNING: Only {len(df)} samples collected (need {min_samples})")
        print(f"   Options:")
        print(f"   1. Increase days_back parameter")
        print(f"   2. Let ARGUS run longer to collect more data")
        print(f"   3. Use synthetic data for initial training")
        return None
    
    # Label data based on final_severity
    df['label'] = df['final_severity'].apply(lambda x: 1 if x in ['CRITICAL', 'WARNING'] else 0)
    
    print(f"  Benign samples: {(df['label']==0).sum()}")
    print(f"  Malicious samples: {(df['label']==1).sum()}")
    
    return df


def collect_from_feedback(min_samples: int = 500):
    """
    Collect labeled data from analyst feedback.
    
    This is the BEST source of training data because analysts
    have manually verified true positives and false positives.
    """
    
    db_url = os.getenv("DATABASE_URL", "postgresql://argus:8888@localhost:5432/argus_db")
    engine = create_engine(db_url)
    
    print("Collecting analyst-labeled feedback...")
    
    query = """
    SELECT 
        i.session_id,
        i.confidence,
        i.severity,
        f.feedback_type,
        f.analyst_comment
    FROM incidents i
    JOIN feedback f ON i.id = f.incident_id
    WHERE f.feedback_type IN ('TP', 'FP')
    """
    
    df = pd.read_sql(query, engine)
    
    print(f"  Collected {len(df)} analyst-labeled samples")
    
    if len(df) < min_samples:
        print(f"   Not enough feedback data yet ({len(df)}/{min_samples})")
        print(f"   Analysts need to label more incidents in the UI")
        return None
    
    # TP = True Positive (malicious), FP = False Positive (benign)
    df['label'] = df['feedback_type'].apply(lambda x: 1 if x == 'TP' else 0)
    
    print(f"  True Positives: {(df['label']==1).sum()}")
    print(f"  False Positives: {(df['label']==0).sum()}")
    
    return df


def export_for_training(output_file: str = "windows_training_data.csv"):
    """
    Export collected data for training.
    """
    
    # Try feedback first (best quality)
    df = collect_from_feedback()
    
    # Fallback to telemetry
    if df is None or len(df) < 500:
        print("\nFalling back to telemetry data...")
        df = collect_windows_telemetry(days_back=30)
    
    if df is None:
        print("\nNot enough data collected!")
        print("Run ARGUS for at least 1 week to collect sufficient data")
        return False
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"\nExported {len(df)} samples to {output_file}")
    print(f"Use this file for training instead of synthetic data")
    
    return True


if __name__ == "__main__":
    success = export_for_training()
    
    if success:
        print("\n" + "="*60)
        print("  DATA COLLECTION COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("1. Review windows_training_data.csv")
        print("2. Update train_models.py to load this CSV")
        print("3. Run training: python train_models.py")
    else:
        print("\n" + "="*60)
        print("INSUFFICIENT DATA")
        print("="*60)
        print("\nOptions:")
        print("1. Let ARGUS run for 1-2 weeks")
        print("2. Use synthetic data for now (current approach)")
        print("3. Import existing Windows telemetry if available")
