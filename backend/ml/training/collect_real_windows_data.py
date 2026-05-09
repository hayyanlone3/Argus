import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import os

def collect_windows_telemetry(days_back: int = 30, min_samples: int = 1000):    
    db_url = os.getenv("DATABASE_URL", "postgresql://argus:8888@localhost:5432/argus_db")
    engine = create_engine(db_url)
    
    print(f"Collecting Windows telemetry from last {days_back} days...")
    
    # Query real process creation events from edges table
    query = f"""
    SELECT 
        parent.name as parent_process,
        child.name as child_process,
        e.entropy_value as entropy,
        child.path_risk as path_risk,
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
        print(f"WARNING: Only {len(df)} samples collected (need {min_samples})")
        print(f"Options:")
        print(f"1. Increase days_back parameter")
        print(f"2. Let ARGUS run longer to collect more data")
        print(f"3. Use synthetic data for initial training")
        return None
    
    # Label data based on final_severity
    df['label'] = df['final_severity'].apply(lambda x: 1 if x in ['CRITICAL', 'WARNING'] else 0)
    
    # Fill missing features with sensible defaults
    if 'path_risk' not in df.columns or df['path_risk'].isna().all():
        print(f"  WARNING: path_risk missing/null, using default 0.0")
        df['path_risk'] = 0.0
    else:
        df['path_risk'] = df['path_risk'].fillna(0.0)
    
    if 'p_matrix_score' not in df.columns:
        print(f"  WARNING: p_matrix_score missing, using default 0.0")
        df['p_matrix_score'] = 0.0
    else:
        df['p_matrix_score'] = df['p_matrix_score'].fillna(0.0)
    
    if 'ml_anomaly_score' not in df.columns:
        print(f"  WARNING: ml_anomaly_score missing, using default 0.0")
        df['ml_anomaly_score'] = 0.0
    else:
        df['ml_anomaly_score'] = df['ml_anomaly_score'].fillna(0.0)
    
    print(f"Benign samples: {(df['label']==0).sum()}")
    print(f"Malicious samples: {(df['label']==1).sum()}")
    print(f"Features: entropy range [{df['entropy'].min():.2f}-{df['entropy'].max():.2f}], path_risk range [{df['path_risk'].min():.2f}-{df['path_risk'].max():.2f}]")
    
    return df


def collect_from_feedback(min_samples: int = 500):

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
    
    print(f"Collected {len(df)} analyst-labeled samples")
    
    if len(df) < min_samples:
        print(f"Not enough feedback data yet ({len(df)}/{min_samples})")
        print(f"Analysts need to label more incidents in the UI")
        return None
    
    # TP = True Positive (malicious), FP = False Positive (benign)
    df['label'] = df['feedback_type'].apply(lambda x: 1 if x == 'TP' else 0)
    
    print(f"True Positives: {(df['label']==1).sum()}")
    print(f"False Positives: {(df['label']==0).sum()}")
    
    return df
    
def export_for_training(output_file: str = "windows_training_data.csv"):
    df = collect_from_feedback()
    
    # Fallback to telemetry
    if df is None or len(df) < 500:
        print("\nFalling back to telemetry data...")
        df = collect_windows_telemetry(days_back=30)
    
    if df is None:
        print("\nNot enough data collected!")
        print("Run ARGUS for at least 1 week to collect sufficient data")
        return False
    
    output_file = r"D:\FYP\Argus\windows_training_data.csv"

    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"\nExported {len(df)} samples to {output_file}")
    print(f"Use this file for training instead of synthetic data")
    
    return True


if __name__ == "__main__":
    success = export_for_training()
    
    if success:
        print("\nNext steps:")
        print("1. Review windows_training_data.csv")
        print("2. Update train_models.py to load this CSV")
        print("3. Run training: python train_models.py")
    else:
        print("\nOptions:")
        print("1. Let ARGUS run for 1-2 weeks")
        print("2. Use synthetic data for now (current approach)")
        print("3. Import existing Windows telemetry if available")
