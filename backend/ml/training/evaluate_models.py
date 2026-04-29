"""
Model Evaluation and Visualization
Generate performance metrics and plots
"""

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
    """Plot confusion matrices for both models."""
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
    """Plot ROC curves for both models."""
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
    print("  Saved: roc_curves.png")
    plt.close()


def plot_precision_recall_curves(y_test, rf_pred_proba, xgb_pred_proba):
    """Plot precision-recall curves."""
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
    """Generate complete evaluation report."""
    print("\n" + "="*60)
    print("GENERATING EVALUATION REPORT")
    print("="*60)
    
    # Confusion matrices
    print("\n  Plotting confusion matrices...")
    plot_confusion_matrices(y_test, rf_pred, xgb_pred)
    
    # ROC curves
    print("  Plotting ROC curves...")
    plot_roc_curves(y_test, rf_pred_proba, xgb_pred_proba)
    
    # Precision-recall curves
    print("  Plotting precision-recall curves...")
    plot_precision_recall_curves(y_test, rf_pred_proba, xgb_pred_proba)
    
    # Feature importance
    print("  Plotting feature importance...")
    plot_feature_importance(rf_model, xgb_model, feature_names)
    
    print("\n  All visualizations saved!")
    print("\nGenerated files:")
    print("  - confusion_matrices.png")
    print("  - roc_curves.png")
    print("  - precision_recall_curves.png")
    print("  - feature_importance.png")
