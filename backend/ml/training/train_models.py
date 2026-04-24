"""
Standalone ML Training Script
Train models locally without Google Colab
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
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
import xgboost as xgb
from river import anomaly
import joblib
import os
from pathlib import Path


def create_synthetic_beth_dataset(n_samples: int = 5000) -> pd.DataFrame:
    """Create synthetic BETH-like dataset for demo."""
    np.random.seed(42)
    
    # Benign samples (80%)
    benign_samples = int(n_samples * 0.8)
    benign_data = {
        'parent_process': np.random.choice(
            ['explorer.exe', 'svchost.exe', 'chrome.exe'],
            benign_samples
        ),
        'child_process': np.random.choice(
            ['cmd.exe', 'powershell.exe', 'notepad.exe'],
            benign_samples
        ),
        'entropy': np.random.normal(5.0, 1.0, benign_samples),
        'file_size': np.random.lognormal(10, 2, benign_samples),
        'path_risk': np.random.uniform(0, 0.3, benign_samples),
        'label': 0  # Benign
    }
    
    # Malicious samples (20%)
    malicious_samples = int(n_samples * 0.2)
    malicious_data = {
        'parent_process': np.random.choice(
            ['cmd.exe', 'powershell.exe'],
            malicious_samples
        ),
        'child_process': np.random.choice(
            ['malware.exe', 'ransomware.exe', 'trojan.exe'],
            malicious_samples
        ),
        'entropy': np.random.normal(7.8, 0.3, malicious_samples),
        'file_size': np.random.lognormal(12, 1, malicious_samples),
        'path_risk': np.random.uniform(0.7, 1.0, malicious_samples),
        'label': 1  # Malicious
    }
    
    df_benign = pd.DataFrame(benign_data)
    df_malicious = pd.DataFrame(malicious_data)
    df = pd.concat([df_benign, df_malicious], ignore_index=True)
    
    return df.sample(frac=1).reset_index(drop=True)


def extract_features(df: pd.DataFrame) -> tuple:
    """Extract features from raw data."""
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
    """Train all models."""
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("TRAINING MODELS")
    print("="*60)
    
    # ========== Model 1: Random Forest (P-Matrix) ==========
    print("\n🔄 Training Random Forest (P-Matrix)...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    rf_pred = rf_model.predict(X_test)
    rf_pred_proba = rf_model.predict_proba(X_test)[:, 1]
    
    rf_accuracy = accuracy_score(y_test, rf_pred)
    rf_auc = roc_auc_score(y_test, rf_pred_proba)
    
    print(f"  Random Forest trained")
    print(f"   Accuracy: {rf_accuracy:.2%}")
    print(f"   AUC: {rf_auc:.2%}")
    
    # ========== Model 2: XGBoost (Entropy Classifier) ==========
    print("\n🔄 Training XGBoost (Entropy Classifier)...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    xgb_pred_proba = xgb_model.predict_proba(X_test)[:, 1]
    
    xgb_accuracy = accuracy_score(y_test, xgb_pred)
    xgb_auc = roc_auc_score(y_test, xgb_pred_proba)
    
    print(f"  XGBoost trained")
    print(f"   Accuracy: {xgb_accuracy:.2%}")
    print(f"   AUC: {xgb_auc:.2%}")
    
    # ========== Model 3: River HalfSpaceTrees ==========
    print("\n🔄 Training River HalfSpaceTrees...")
    river_model = anomaly.HalfSpaceTrees(n_trees=25, height=15, seed=42)
    
    for idx, row in X_train.iterrows():
        features_dict = row.to_dict()
        river_model.learn_one(features_dict)
    
    print(f"  River HalfSpaceTrees trained")
    
    # ========== Feature Scaler ==========
    print("\n🔄 Fitting Feature Scaler...")
    scaler = StandardScaler()
    scaler.fit(X_train)
    print(f"  Feature Scaler fitted")
    
    # ========== Save Models ==========
    print("\n" + "="*60)
    print("SAVING MODELS")
    print("="*60)
    
    joblib.dump(rf_model, os.path.join(output_dir, 'p_matrix_model.pkl'))
    print(f"  Saved: p_matrix_model.pkl")
    
    joblib.dump(xgb_model, os.path.join(output_dir, 'entropy_classifier_model.pkl'))
    print(f"  Saved: entropy_classifier_model.pkl")
    
    import pickle
    with open(os.path.join(output_dir, 'river_halfspace_model.pkl'), 'wb') as f:
        pickle.dump(river_model, f)
    print(f"  Saved: river_halfspace_model.pkl")
    
    joblib.dump(scaler, os.path.join(output_dir, 'feature_scaler.pkl'))
    print(f"  Saved: feature_scaler.pkl")
    
    # ========== Evaluation ==========
    print("\n" + "="*60)
    print("MODEL EVALUATION")
    print("="*60)
    
    print("\n📊 Random Forest Classification Report:")
    print(classification_report(y_test, rf_pred, target_names=['Benign', 'Malicious']))
    
    print("\n📊 XGBoost Classification Report:")
    print(classification_report(y_test, xgb_pred, target_names=['Benign', 'Malicious']))
    
    return {
        'rf_model': rf_model,
        'xgb_model': xgb_model,
        'river_model': river_model,
        'scaler': scaler,
        'metrics': {
            'rf_accuracy': rf_accuracy,
            'rf_auc': rf_auc,
            'xgb_accuracy': xgb_accuracy,
            'xgb_auc': xgb_auc
        }
    }


def main():
    """Main training pipeline."""
    print("\n" + "="*60)
    print("ARGUS ML TRAINING PIPELINE")
    print("="*60)
    
    # Load/create dataset
    print("\n📊 Loading dataset...")
    df = create_synthetic_beth_dataset(n_samples=5000)
    print(f"  Dataset loaded: {df.shape[0]} samples")
    print(f"   Benign: {(df['label']==0).sum()}")
    print(f"   Malicious: {(df['label']==1).sum()}")
    
    # Extract features
    print("\n🔧 Extracting features...")
    X, y = extract_features(df)
    print(f"  Features extracted: {X.shape}")
    
    # Train/test split
    print("\n📈 Splitting data...")
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
    print("Ready for deployment!")


if __name__ == "__main__":
    main()
