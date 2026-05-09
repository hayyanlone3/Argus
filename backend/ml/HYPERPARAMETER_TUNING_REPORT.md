# Hyperparameter Tuning Report

## Objective
Optimize River HalfSpaceTrees hyperparameters (`n_trees`, `height`, `window_size`) to maximize anomaly detection performance on Windows telemetry data.

## Methodology

### Approach: RandomizedSearchCV
- **Why RandomizedSearchCV instead of GridSearchCV?**
  - Grid search: exhaustive (3×3×3 = 27 configs) – requires O(27 × training_time) which is slow
  - Randomized search: probabilistic sampling of N random configs – much faster O(N × training_time)
  - **Academic justification**: Sklearn documentation recommends RandomizedSearchCV for high-dimensional hyperparameter spaces. Bergstra & Bengio (2012) show that random search can find near-optimal parameters with only N=10-15 samples, achieving ~95% of best-possible performance
  - Random search is statistically sound: asymptotically, it's equivalent to grid search but computationally efficient for large search spaces

### Search Space
```python
n_trees:     Uniform[10, 50]    # Number of isolation trees
height:      Uniform[10, 20]    # Depth of each tree  
window_size: Uniform[100, 500]  # Sliding window for adaptation
seed:        Fixed = 42         # Reproducibility
```

### Data Split Strategy
- **Training**: 80% (56,770 samples) 
- **Validation**: 20% (14,193 samples)
- **Subsampling for search**: 15% of full data by default to accelerate each iteration
  - Rationale: Smaller search samples reduce runtime and lower the chance of resource pressure on the machine; the final model still trains on the full dataset once a good configuration is chosen
  - Final training uses full dataset with best config

### Evaluation Metric: PR AUC (Precision-Recall Area Under Curve)
- **Why PR AUC over ROC AUC?** 
  - Dataset is heavily imbalanced: 98.5% benign, 1.5% malicious
  - ROC AUC can be misleading with severe class imbalance (classifying everything as benign scores 0.5 ROC but 0 PR)
  - PR AUC directly measures model's ability to correctly identify rare malicious events
  - Industry standard for anomaly detection and fraud detection (see He & Garcia 2009)

### Iterations
- Total N=5 random hyperparameter configurations sampled by default
- Each config trained on 17,031 samples (80% of subsampled data)
- Evaluated on 4,258 validation samples (20% of subsampled data)
- Best config selected based on highest PR AUC

## Expected Results
- Best config will be saved to `hyperparam_best_config.json`
- All results saved to `hyperparam_search_results.json` for reproducibility
- Final retraining on full dataset (70,963 samples) with best config produces production model

## References
- Bergstra, J., & Bengio, Y. (2012). "Random Search for Hyper-Parameter Optimization". JMLR.
- He, H., & Garcia, E. A. (2009). "Learning from imbalanced data". IEEE TKDE.
