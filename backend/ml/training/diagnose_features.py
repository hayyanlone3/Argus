import pandas as pd
import numpy as np
from pathlib import Path

def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for _ in range(6):
        if (current / 'windows_training_data.csv').exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return start.resolve()

repo_root = find_repo_root(Path(__file__).resolve().parent)
csv_path = repo_root / 'windows_training_data.csv'
test_path = repo_root / 'windows_test_data.csv'

print(f"Loading test data from {test_path}")
test_df = pd.read_csv(test_path)

print(f"\nTotal rows: {len(test_df)}")
print(f"Columns: {test_df.columns.tolist()}")

# Check labels
print(f"\nLabel distribution:")
print(test_df['label'].value_counts())

# Check feature statistics by label
feature_cols = ['entropy', 'path_risk', 'p_matrix_score', 'ml_anomaly_score']

for col in feature_cols:
    if col in test_df.columns:
        print(f"\n{col}:")
        print(f"  Benign (label=0):   mean={test_df[test_df['label']==0][col].mean():.4f}, std={test_df[test_df['label']==0][col].std():.4f}, min={test_df[test_df['label']==0][col].min():.4f}, max={test_df[test_df['label']==0][col].max():.4f}")
        print(f"  Malicious (label=1): mean={test_df[test_df['label']==1][col].mean():.4f}, std={test_df[test_df['label']==1][col].std():.4f}, min={test_df[test_df['label']==1][col].min():.4f}, max={test_df[test_df['label']==1][col].max():.4f}")

print("\n" + "="*70)
print("Sample rows with label=0 (benign):")
benign_cols = ['parent_process', 'child_process', 'entropy', 'label']
if 'path_risk' in test_df.columns:
    benign_cols.append('path_risk')
if 'p_matrix_score' in test_df.columns:
    benign_cols.append('p_matrix_score')
if 'ml_anomaly_score' in test_df.columns:
    benign_cols.append('ml_anomaly_score')
print(test_df[test_df['label']==0][benign_cols].head(3))

print("\nSample rows with label=1 (malicious):")
print(test_df[test_df['label']==1][benign_cols].head(3))
