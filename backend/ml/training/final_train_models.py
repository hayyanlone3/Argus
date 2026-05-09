import json
import pickle
from pathlib import Path
import pandas as pd
from river import anomaly
from sklearn.preprocessing import StandardScaler


def load_best_config(config_path: str) -> dict:
    """Load best hyperparameter configuration from search results."""
    with open(config_path, 'r') as f:
        data = json.load(f)
    return data.get('config', {})


def load_training_data(csv_path: str):
    """Load and prepare full Windows training dataset."""
    df = pd.read_csv(csv_path)
    
    # Map labels
    if 'label' not in df.columns and 'final_severity' in df.columns:
        df['label'] = df['final_severity'].isin(['CRITICAL', 'WARNING']).astype(int)
    
    # Ensure features exist
    for col in ['entropy', 'path_risk', 'p_matrix_score', 'ml_anomaly_score', 'parent_process', 'child_process']:
        if col not in df.columns:
            df[col] = 0.0
    
    # Encodings
    parent_encoding = {'explorer.exe': 1, 'svchost.exe': 2, 'chrome.exe': 3, 'cmd.exe': 4, 'powershell.exe': 5}
    child_encoding = {'cmd.exe': 1, 'powershell.exe': 2, 'notepad.exe': 3, 'malware.exe': 4, 'ransomware.exe': 5, 'trojan.exe': 6}
    
    # Feature extraction
    X = pd.DataFrame()
    X['entropy'] = pd.to_numeric(df['entropy'], errors='coerce').fillna(0.0)
    X['path_risk'] = pd.to_numeric(df['path_risk'], errors='coerce').fillna(0.0)
    X['p_matrix_score'] = pd.to_numeric(df['p_matrix_score'], errors='coerce').fillna(0.0)
    X['ml_anomaly_score'] = pd.to_numeric(df['ml_anomaly_score'], errors='coerce').fillna(0.0)
    X['parent_encoded'] = df['parent_process'].map(parent_encoding).fillna(0).astype(int)
    X['child_encoded'] = df['child_process'].map(child_encoding).fillna(0).astype(int)
    
    y = df['label']
    return X, y, df


def train_final_model(X_train, best_cfg: dict):
    """Train River HalfSpaceTrees with tuned hyperparameters."""
    model = anomaly.HalfSpaceTrees(
        n_trees=best_cfg.get('n_trees', 25),
        height=best_cfg.get('height', 15),
        window_size=best_cfg.get('window_size', 250),
        seed=best_cfg.get('seed', 42)
    )
    
    print(f"Training River HalfSpaceTrees with config: {best_cfg}")
    print(f"Total samples: {len(X_train)}")
    
    for i, (_, row) in enumerate(X_train.iterrows()):
        feats = row.to_dict()
        model.learn_one(feats)
        if (i + 1) % 10000 == 0:
            print(f"  Processed {i + 1} / {len(X_train)} samples")
    
    print(f"Training complete")
    return model


def main():
    repo = Path(__file__).resolve().parents[3]
    csv_path = repo / 'windows_training_data.csv'
    models_dir = repo / 'backend' / 'ml' / 'models'
    config_path = models_dir / 'hyperparam_best_config.json'
    
    if not csv_path.exists():
        raise SystemExit(f"Missing {csv_path}")
    
    if not config_path.exists():
        print(f"Warning: Best config not found at {config_path}")
        print("Using default hyperparameters")
        best_cfg = {'n_trees': 25, 'height': 15, 'window_size': 250, 'seed': 42}
    else:
        best_cfg = load_best_config(str(config_path))
        print(f"Loaded best config: {best_cfg}\n")
    
    # Load full dataset
    print(f"Loading full dataset from {csv_path}")
    X, y, df = load_training_data(str(csv_path))
    print(f"Dataset: {len(X)} samples, Benign: {(y==0).sum()}, Malicious: {(y==1).sum()}\n")
    
    # Train model
    model = train_final_model(X, best_cfg)
    
    # Fit scaler on same data (for inference compatibility)
    scaler = StandardScaler()
    scaler.fit(X)
    
    # Save model and scaler
    models_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = models_dir / 'river_windows_baseline.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"\nSaved model to {model_path}")
    
    scaler_path = models_dir / 'feature_scaler.pkl'
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"Saved scaler to {scaler_path}")
    
    # Save training metadata
    metadata = {
        'hyperparameters': best_cfg,
        'dataset_size': len(X),
        'benign_count': int((y == 0).sum()),
        'malicious_count': int((y == 1).sum()),
        'feature_names': list(X.columns)
    }
    meta_path = models_dir / 'river_model_metadata.json'
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {meta_path}")


if __name__ == '__main__':
    main()
