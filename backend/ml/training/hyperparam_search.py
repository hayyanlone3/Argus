import os
import time
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from river import anomaly
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
from sklearn.model_selection import train_test_split
from scipy.stats import randint, uniform


def load_data(csv_path: str, sample_fraction: float = 0.15):
    """Load CSV and optionally subsample for faster hyperparameter search."""
    df = pd.read_csv(csv_path)
    if 'label' not in df.columns and 'final_severity' in df.columns:
        df['label'] = df['final_severity'].isin(['CRITICAL', 'WARNING']).astype(int)

    if sample_fraction < 1.0:
        df = df.sample(frac=sample_fraction, random_state=42)
        print(f"  Subsampled to {len(df)} rows for faster search")

    # ensure features exist
    for col in ['entropy', 'path_risk', 'p_matrix_score', 'ml_anomaly_score', 'parent_process', 'child_process']:
        if col not in df.columns:
            df[col] = 0.0

    # simple encodings
    parent_encoding = {'explorer.exe': 1, 'svchost.exe': 2, 'chrome.exe': 3, 'cmd.exe': 4, 'powershell.exe': 5}
    child_encoding = {'cmd.exe': 1, 'powershell.exe': 2, 'notepad.exe': 3, 'malware.exe': 4, 'ransomware.exe': 5, 'trojan.exe': 6}

    X = pd.DataFrame()
    X['entropy'] = pd.to_numeric(df['entropy'], errors='coerce').fillna(0.0)
    X['path_risk'] = pd.to_numeric(df['path_risk'], errors='coerce').fillna(0.0)
    X['p_matrix_score'] = pd.to_numeric(df['p_matrix_score'], errors='coerce').fillna(0.0)
    X['ml_anomaly_score'] = pd.to_numeric(df['ml_anomaly_score'], errors='coerce').fillna(0.0)
    X['parent_encoded'] = df['parent_process'].map(parent_encoding).fillna(0).astype(int)
    X['child_encoded'] = df['child_process'].map(child_encoding).fillna(0).astype(int)

    y = df['label']
    return X, y


def eval_model_on_test(model, X_test):
    scores = []
    for _, row in X_test.iterrows():
        feats = row.to_dict()
        s = float(model.score_one(feats))
        s = max(0.0, min(1.0, s))
        scores.append(s)
    return np.array(scores)


def run_randomized_search(csv_path: str, out_dir: str, n_iter: int = 5, sample_fraction: float = 0.15):
    print(f"Starting RandomizedSearchCV with {n_iter} iterations...")
    
    X, y = load_data(csv_path, sample_fraction=sample_fraction)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    print(f"Training on {len(X_train)} samples, evaluating on {len(X_test)} samples\n")

    # Define hyperparameter distributions
    param_dist = {
        'n_trees': randint(10, 26),      # 10-25 keeps training lighter
        'height': randint(10, 15),       # 10-14 avoids very expensive trees
        'window_size': randint(100, 251) # 100-250 is enough for fast tuning
    }

    results = []
    t_start = time.time()
    
    for i in range(n_iter):
        # Random sample from distributions
        cfg = {
            'n_trees': np.random.randint(param_dist['n_trees'].a, param_dist['n_trees'].b + 1),
            'height': np.random.randint(param_dist['height'].a, param_dist['height'].b + 1),
            'window_size': np.random.randint(param_dist['window_size'].a, param_dist['window_size'].b + 1),
            'seed': 42
        }
        
        t0 = time.time()
        try:
            model = anomaly.HalfSpaceTrees(
                n_trees=cfg['n_trees'],
                height=cfg['height'],
                window_size=cfg['window_size'],
                seed=cfg['seed']
            )
            for _, row in X_train.iterrows():
                model.learn_one(row.to_dict())

            scores = eval_model_on_test(model, X_test)
            roc = None
            if len(set(y_test)) > 1:
                try:
                    roc = float(roc_auc_score(y_test, scores))
                except Exception:
                    roc = None
            prec, rec, _ = precision_recall_curve(y_test, scores)
            pr_auc = float(auc(rec, prec))
            dur = time.time() - t0

            results.append({
                'iteration': i + 1,
                'cfg': cfg,
                'roc_auc': roc,
                'pr_auc': pr_auc,
                'time_sec': dur
            })
            print(f"[{i+1}/{n_iter}] n_trees={cfg['n_trees']}, height={cfg['height']}, window_size={cfg['window_size']} | ROC_AUC={roc:.4f}, PR_AUC={pr_auc:.4f}, time={dur:.1f}s")
        except KeyboardInterrupt:
            print("\nSearch interrupted by user")
            break
        except Exception as e:
            print(f"[{i+1}/{n_iter}] Error: {e}")
            continue

    total_time = time.time() - t_start
    effective_iters = max(1, len(results))
    print(f"\nRandomized search completed in {total_time:.1f}s ({total_time/effective_iters:.1f}s per successful iteration)")

    # Save all results
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_file = Path(out_dir) / 'hyperparam_search_results.json'
    with open(out_file, 'w') as f:
        json.dump({
            'method': 'RandomizedSearchCV',
            'n_iterations': len(results),
            'total_time_sec': total_time,
            'results': results
        }, f, indent=2)

    # Pick best by PR_AUC
    if results:
        best = sorted(results, key=lambda r: r['pr_auc'], reverse=True)[0]
        with open(Path(out_dir) / 'hyperparam_best_config.json', 'w') as f:
            json.dump({
                'best_iteration': best['iteration'],
                'config': best['cfg'],
                'roc_auc': best['roc_auc'],
                'pr_auc': best['pr_auc'],
                'training_time_sec': best['time_sec'],
                'justification': 'Best config selected based on PR_AUC (appropriate for imbalanced dataset where positives are rare)'
            }, f, indent=2)

        print(f"\nBest config: {best['cfg']}")
        print(f"PR_AUC: {best['pr_auc']:.4f}")
        print(f"ROC_AUC: {best['roc_auc']:.4f}")
    
    print(f"Results saved to {out_file}")
    return results


if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[3]
    csv = repo / 'windows_training_data.csv'
    outdir = repo / 'backend' / 'ml' / 'models'
    if not csv.exists():
        raise SystemExit(f"Missing {csv}")
    n_iter = int(os.getenv('ARGUS_HYPERPARAM_N_ITER', '3'))
    sample_fraction = float(os.getenv('ARGUS_HYPERPARAM_SAMPLE_FRAC', '0.15'))
    run_randomized_search(str(csv), str(outdir), n_iter=n_iter, sample_fraction=sample_fraction)
