import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)
from river import anomaly
import joblib
import os
from pathlib import Path

def create_windows_baseline_dataset(n_samples: int = 5000) -> pd.DataFrame:
    np.random.seed(42)
    
    # Benign Windows behavior (85%)
    benign_samples = int(n_samples * 0.85)
    
    # Common benign parent-child relationships
    benign_patterns = [
        ('explorer.exe', 'chrome.exe', 5.2, 0.1),
        ('explorer.exe', 'notepad.exe', 4.8, 0.05),
        ('svchost.exe', 'svchost.exe', 5.5, 0.08),
        ('services.exe', 'svchost.exe', 5.3, 0.06),
        ('chrome.exe', 'chrome.exe', 5.4, 0.12),
        ('code.exe', 'node.exe', 5.6, 0.15),
        ('explorer.exe', 'cmd.exe', 5.0, 0.25),  # Normal user activity
        ('winlogon.exe', 'userinit.exe', 5.1, 0.05),
    ]
    
    benign_data = {
        'parent_process': [],
        'child_process': [],
        'entropy': [],
        'file_size': [],
        'path_risk': [],
        'is_system32': [],
        'is_lolbin': [],
        'cmd_length': [],
        'label': []
    }
    
    for _ in range(benign_samples):
        parent, child, base_entropy, base_risk = benign_patterns[np.random.randint(0, len(benign_patterns))]
        
        benign_data['parent_process'].append(parent)
        benign_data['child_process'].append(child)
        benign_data['entropy'].append(np.random.normal(base_entropy, 0.5))
        benign_data['file_size'].append(np.random.lognormal(10, 2))
        benign_data['path_risk'].append(np.random.uniform(0, base_risk))
        benign_data['is_system32'].append(1 if 'svc' in child or 'win' in child else 0)
        benign_data['is_lolbin'].append(1 if child in ['cmd.exe', 'powershell.exe'] else 0)
        benign_data['cmd_length'].append(np.random.uniform(0, 50))  # Short commands
        benign_data['label'].append(0)
    
    # Malicious Windows behavior (15%)
    malicious_samples = int(n_samples * 0.15)
    
    # Real Windows attack patterns
    malicious_patterns = [
        # LOLBin abuse
        ('explorer.exe', 'powershell.exe', 7.8, 0.85, 200),  # Encoded payload
        ('winword.exe', 'cmd.exe', 7.6, 0.80, 150),  # Macro execution
        ('excel.exe', 'powershell.exe', 7.9, 0.90, 250),  # Fileless malware
        
        # Suspicious spawns
        ('cmd.exe', 'powershell.exe', 7.7, 0.75, 180),  # Chained shells
        ('powershell.exe', 'cmd.exe', 7.5, 0.70, 160),  # Reverse chain
        
        # Temp folder execution
        ('explorer.exe', 'malware.exe', 7.9, 0.95, 50),  # Packed malware
        ('svchost.exe', 'trojan.exe', 8.0, 0.98, 40),  # Process injection
        
        # Persistence mechanisms
        ('cmd.exe', 'schtasks.exe', 6.5, 0.65, 120),  # Scheduled task
        ('powershell.exe', 'reg.exe', 6.8, 0.70, 100),  # Registry modification
    ]
    
    malicious_data = {
        'parent_process': [],
        'child_process': [],
        'entropy': [],
        'file_size': [],
        'path_risk': [],
        'is_system32': [],
        'is_lolbin': [],
        'cmd_length': [],
        'label': []
    }
    
    for _ in range(malicious_samples):
        parent, child, base_entropy, base_risk, cmd_len = malicious_patterns[np.random.randint(0, len(malicious_patterns))]
        
        malicious_data['parent_process'].append(parent)
        malicious_data['child_process'].append(child)
        malicious_data['entropy'].append(np.random.normal(base_entropy, 0.3))
        malicious_data['file_size'].append(np.random.lognormal(12, 1))
        malicious_data['path_risk'].append(np.random.uniform(base_risk - 0.1, base_risk + 0.05))
        malicious_data['is_system32'].append(0)  # Malware rarely in system32
        malicious_data['is_lolbin'].append(1 if child in ['cmd.exe', 'powershell.exe'] else 0)
        malicious_data['cmd_length'].append(np.random.uniform(cmd_len - 50, cmd_len + 100))
        malicious_data['label'].append(1)
    
    df_benign = pd.DataFrame(benign_data)
    df_malicious = pd.DataFrame(malicious_data)
    df = pd.concat([df_benign, df_malicious], ignore_index=True)
    
    return df.sample(frac=1).reset_index(drop=True)


def extract_features(df: pd.DataFrame) -> tuple:
    X = df[[
        'entropy',
        'file_size',
        'path_risk'
    ]].copy()
    
    # Encode categorical features
    parent_encoding = {
        'explorer.exe': 1, 'svchost.exe': 2, 'chrome.exe': 3,
        'cmd.exe': 4, 'powershell.exe': 5
    }
    child_encoding = {
        'cmd.exe': 1, 'powershell.exe': 2, 'notepad.exe': 3,
        'malware.exe': 4, 'ransomware.exe': 5, 'trojan.exe': 6
    }
    
    X['parent_encoded'] = df['parent_process'].map(parent_encoding).fillna(0)
    X['child_encoded'] = df['child_process'].map(child_encoding).fillna(0)
    
    y = df['label']
    
    return X, y


def train_models(X_train, X_test, y_train, y_test, output_dir: str = "backend/ml/models/"):
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Model 3: River HalfSpaceTrees 
    print("\nTraining River HalfSpaceTrees...")
    river_model = anomaly.HalfSpaceTrees(n_trees=25, height=15, seed=42)
    
    for idx, row in X_train.iterrows():
        features_dict = row.to_dict()
        river_model.learn_one(features_dict)
    
    print(f"River HalfSpaceTrees trained")
    
    # ========== Feature Scaler ==========
    print("\n  Fitting Feature Scaler...")
    scaler = StandardScaler()
    scaler.fit(X_train)
    print(f"  Feature Scaler fitted")
    
    import pickle
    with open(os.path.join(output_dir, 'river_halfspace_model.pkl'), 'wb') as f:
        pickle.dump(river_model, f)
    print(f"  Saved: river_halfspace_model.pkl")
    
    joblib.dump(scaler, os.path.join(output_dir, 'feature_scaler.pkl'))
    print(f"  Saved: feature_scaler.pkl")
    
    return {
        'river_model': river_model,
        'scaler': scaler,
        }


def main():
    # Check if real data exists
    real_data_file = "windows_training_data.csv"
    
    if os.path.exists(real_data_file):
        print(f"\nFound real Windows data: {real_data_file}")
        print("Loading REAL telemetry data...")
        df = pd.read_csv(real_data_file)
        print(f"Loaded {len(df)} real Windows events")
    else:
        print(f"\nNo real data found ({real_data_file})")
        print("Using synthetic Windows baseline for initial training")
        print("Run 'python collect_real_windows_data.py' to collect real data")
        print()
        df = create_windows_baseline_dataset(n_samples=5000)
    
    print(f"Dataset: {df.shape[0]} samples")
    print(f"Benign: {(df['label']==0).sum()}")
    print(f"Malicious: {(df['label']==1).sum()}")
    
    # Extract features
    print("\n  Extracting features...")
    X, y = extract_features(df)
    print(f"  Features extracted: {X.shape}")
    
    # Train/test split
    print("\nSplitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Training set: {X_train.shape}")
    print(f"  Test set: {X_test.shape}")
    
    # Train models
    results = train_models(X_train, X_test, y_train, y_test)
    
    print("\n" + "="*60)
    print("  TRAINING COMPLETE")
    print("="*60)
    print("\nModels saved to: backend/ml/models/")
    
    if os.path.exists(real_data_file):
        print("Models trained on REAL Windows telemetry")
    else:
        print("Models trained on synthetic data")
        print("Collect real data for better accuracy")
    
    print("\nReady for deployment!")


if __name__ == "__main__":
    main()
