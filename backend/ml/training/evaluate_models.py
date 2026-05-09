import os
import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, auc,
    classification_report, confusion_matrix, accuracy_score,
    precision_score, recall_score, f1_score
)

def create_test_split(csv_path: str, test_path: str, test_size: float = 0.2, random_state: int = 42):
    df = pd.read_csv(csv_path)

    if 'label' not in df.columns and 'final_severity' in df.columns:
        df['label'] = df['final_severity'].isin(['CRITICAL', 'WARNING']).astype(int)

    if 'label' not in df.columns:
        raise RuntimeError('No label or final_severity column found in CSV')

    train, test = train_test_split(df, test_size=test_size, stratify=df['label'], random_state=random_state)
    test.to_csv(test_path, index=False)
    return train, test


def load_model(model_path: str):
    with open(model_path, 'rb') as f:
        return pickle.load(f)


def evaluate_river(model, X_test: pd.DataFrame, y_test: pd.Series, threshold: float = 0.8):
    # deep copy the model so scoring doesn't modify original
    model_copy = pickle.loads(pickle.dumps(model))

    scores = []
    for _, row in X_test.iterrows():
        feats = row.to_dict()
        s = float(model_copy.score_one(feats))
        s = max(0.0, min(1.0, s))
        scores.append(s)

    auc_roc = roc_auc_score(y_test, scores) if len(np.unique(y_test)) > 1 else None
    prec, rec, _ = precision_recall_curve(y_test, scores)
    pr_auc = auc(rec, prec)

    preds = (np.array(scores) >= threshold).astype(int)
    report = classification_report(y_test, preds, digits=4)
    cm = confusion_matrix(y_test, preds)

    metrics = {
        'roc_auc': None if auc_roc is None else float(auc_roc),
        'pr_auc': float(pr_auc),
        'accuracy': float(accuracy_score(y_test, preds)),
        'precision': float(precision_score(y_test, preds, zero_division=0)),
        'recall': float(recall_score(y_test, preds, zero_division=0)),
        'f1': float(f1_score(y_test, preds, zero_division=0)),
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'threshold': threshold
    }

    return metrics, scores

def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for _ in range(6):
        if (current / 'windows_training_data.csv').exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return start.resolve()


def main():
    repo_root = find_repo_root(Path(__file__).resolve().parent)
    csv_path = repo_root / 'windows_training_data.csv'
    test_path = repo_root / 'windows_test_data.csv'
    model_path = repo_root / 'backend' / 'ml' / 'models' / 'river_windows_baseline.pkl'

    if not csv_path.exists():
        raise SystemExit(f"Missing {csv_path}")
    if not model_path.exists():
        raise SystemExit(f"Missing model {model_path}")

    print(f"Loading data from {csv_path}")
    _, test = create_test_split(str(csv_path), str(test_path), test_size=0.2)
    print(f"Saved test split to {test_path} ({len(test)} rows)")

    print(f"Loading model from {model_path}")
    model = load_model(str(model_path))

    # Build feature frame matching training extractor
    feature_cols = ['entropy', 'path_risk', 'p_matrix_score', 'ml_anomaly_score', 'parent_process', 'child_process']
    X_test = pd.DataFrame(index=test.index)
    for col in ['entropy', 'path_risk', 'p_matrix_score', 'ml_anomaly_score']:
        if col in test.columns:
            X_test[col] = pd.to_numeric(test[col], errors='coerce').fillna(0.0)
        else:
            X_test[col] = 0.0

    parent_encoding = {'explorer.exe': 1, 'svchost.exe': 2, 'chrome.exe': 3, 'cmd.exe': 4, 'powershell.exe': 5}
    child_encoding = {'cmd.exe': 1, 'powershell.exe': 2, 'notepad.exe': 3, 'malware.exe': 4, 'ransomware.exe': 5, 'trojan.exe': 6}
    if 'parent_process' in test.columns:
        X_test['parent_encoded'] = test['parent_process'].map(parent_encoding).fillna(0)
    else:
        X_test['parent_encoded'] = 0
    if 'child_process' in test.columns:
        X_test['child_encoded'] = test['child_process'].map(child_encoding).fillna(0)
    else:
        X_test['child_encoded'] = 0

    y_test = test['label']

    print("Evaluating model on test set...")
    metrics, scores = evaluate_river(model, X_test[['entropy','path_risk','p_matrix_score','ml_anomaly_score','parent_encoded','child_encoded']], y_test)

    out = repo_root / 'backend' / 'ml' / 'models' / 'river_eval_report.json'
    with open(out, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"Evaluation complete. Report saved to {out}")
    print(json.dumps({k: metrics[k] for k in ['roc_auc','pr_auc','accuracy','precision','recall','f1']}, indent=2))
    
    threshold_sweep(model, X_test[['entropy','path_risk','p_matrix_score','ml_anomaly_score','parent_encoded','child_encoded']], y_test)


def threshold_sweep(model, X_test: pd.DataFrame, y_test: pd.Series):
    model_copy = pickle.loads(pickle.dumps(model))
    scores = []
    for _, row in X_test.iterrows():
        feats = row.to_dict()
        s = float(model_copy.score_one(feats))
        s = max(0.0, min(1.0, s))
        scores.append(s)

    scores = np.array(scores)
    print("\nScore Distribution")
    print(f"Min: {scores.min():.4f}, Max: {scores.max():.4f}, Mean: {scores.mean():.4f}, Median: {np.median(scores):.4f}")
    print(f"Positives (label=1): {(y_test==1).sum()}, Negatives (label=0): {(y_test==0).sum()}")

    print("\nThreshold Sweep (Finding Optimal Operating Point) ===")
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    for threshold in thresholds:
        preds = (scores >= threshold).astype(int)
        tp = ((preds == 1) & (y_test == 1)).sum()
        fp = ((preds == 1) & (y_test == 0)).sum()
        tn = ((preds == 0) & (y_test == 0)).sum()
        fn = ((preds == 0) & (y_test == 1)).sum()
        
        acc = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0
        
        print(f"  Threshold {threshold:.1f}: Prec={prec:.3f}, Rec={rec:.3f}, F1={f1:.3f} (TP={tp}, FP={fp}, FN={fn})")

if __name__ == '__main__':
    main()
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix,
    roc_curve,
    auc,
    precision_recall_curve,
    classification_report
)
import numpy as np

def plot_confusion_matrices(y_test, rf_pred, xgb_pred):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    cm_rf = confusion_matrix(y_test, rf_pred)
    sns.heatmap(cm_rf, annot=True, fmt='d', cmap='Blues', ax=axes[0])
    axes[0].set_title('Random Forest Confusion Matrix')
    axes[0].set_ylabel('Actual')
    axes[0].set_xlabel('Predicted')
    
    cm_xgb = confusion_matrix(y_test, xgb_pred)
    sns.heatmap(cm_xgb, annot=True, fmt='d', cmap='Greens', ax=axes[1])
    axes[1].set_title('XGBoost Confusion Matrix')
    axes[1].set_ylabel('Actual')
    axes[1].set_xlabel('Predicted')
    
    plt.tight_layout()
    plt.savefig('confusion_matrices.png', dpi=150, bbox_inches='tight')
    print("  Saved: confusion_matrices.png")
    plt.close()


def plot_roc_curves(y_test, rf_pred_proba, xgb_pred_proba):
    fig, ax = plt.subplots(figsize=(8, 6))
    
    fpr_rf, tpr_rf, _ = roc_curve(y_test, rf_pred_proba)
    auc_rf = auc(fpr_rf, tpr_rf)
    ax.plot(fpr_rf, tpr_rf, label=f'Random Forest (AUC={auc_rf:.2f})', linewidth=2)
    
    fpr_xgb, tpr_xgb, _ = roc_curve(y_test, xgb_pred_proba)
    auc_xgb = auc(fpr_xgb, tpr_xgb)
    ax.plot(fpr_xgb, tpr_xgb, label=f'XGBoost (AUC={auc_xgb:.2f})', linewidth=2)
    
    ax.plot([0, 1], [0, 1], 'k--', label='Random Classifier')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curves')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.savefig('roc_curves.png', dpi=150, bbox_inches='tight')
    print("Saved: roc_curves.png")
    plt.close()


def plot_precision_recall_curves(y_test, rf_pred_proba, xgb_pred_proba):
    fig, ax = plt.subplots(figsize=(8, 6))
    
    precision_rf, recall_rf, _ = precision_recall_curve(y_test, rf_pred_proba)
    ax.plot(recall_rf, precision_rf, label='Random Forest', linewidth=2)
    
    precision_xgb, recall_xgb, _ = precision_recall_curve(y_test, xgb_pred_proba)
    ax.plot(recall_xgb, precision_xgb, label='XGBoost', linewidth=2)
    
    ax.set_xlabel('Recall')
    ax.set_ylabel('Precision')
    ax.set_title('Precision-Recall Curves')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.savefig('precision_recall_curves.png', dpi=150, bbox_inches='tight')
    print("  Saved: precision_recall_curves.png")
    plt.close()


def plot_feature_importance(rf_model, xgb_model, feature_names):
    """Plot feature importance for both models."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    # Random Forest
    importances_rf = rf_model.feature_importances_
    indices_rf = np.argsort(importances_rf)[::-1]
    axes[0].bar(range(len(importances_rf)), importances_rf[indices_rf])
    axes[0].set_xticks(range(len(importances_rf)))
    axes[0].set_xticklabels([feature_names[i] for i in indices_rf], rotation=45, ha='right')
    axes[0].set_title('Random Forest Feature Importance')
    axes[0].set_ylabel('Importance')
    
    # XGBoost
    importances_xgb = xgb_model.feature_importances_
    indices_xgb = np.argsort(importances_xgb)[::-1]
    axes[1].bar(range(len(importances_xgb)), importances_xgb[indices_xgb])
    axes[1].set_xticks(range(len(importances_xgb)))
    axes[1].set_xticklabels([feature_names[i] for i in indices_xgb], rotation=45, ha='right')
    axes[1].set_title('XGBoost Feature Importance')
    axes[1].set_ylabel('Importance')
    
    plt.tight_layout()
    plt.savefig('feature_importance.png', dpi=150, bbox_inches='tight')
    print("  Saved: feature_importance.png")
    plt.close()


def generate_report(y_test, rf_pred, xgb_pred, rf_pred_proba, xgb_pred_proba, 
                   rf_model, xgb_model, feature_names):    
    # Confusion matrices
    print("\nPlotting confusion matrices...")
    plot_confusion_matrices(y_test, rf_pred, xgb_pred)
    
    # ROC curves
    print("Plotting ROC curves...")
    plot_roc_curves(y_test, rf_pred_proba, xgb_pred_proba)
    
    # Precision-recall curves
    print("Plotting precision-recall curves...")
    plot_precision_recall_curves(y_test, rf_pred_proba, xgb_pred_proba)
    
    # Feature importance
    print("Plotting feature importance...")
    plot_feature_importance(rf_model, xgb_model, feature_names)
    
    print("\nAll visualizations saved!")
    print("\nGenerated files:")
    print("confusion_matrices.png")
    print("roc_curves.png")
    print("precision_recall_curves.png")
    print("feature_importance.png")
