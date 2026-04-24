# ML Training Guide

## Overview

This directory contains training scripts and notebooks for training ARGUS ML models.

## Files

- `ARGUS_ML_Training.ipynb` - Google Colab notebook for training
- `train_models.py` - Standalone training script
- `evaluate_models.py` - Model evaluation and visualization

## Quick Start

### Option 1: Google Colab (Recommended)

1. Open Google Colab: https://colab.research.google.com/
2. Upload `ARGUS_ML_Training.ipynb`
3. Run all cells
4. Download the 4 .pkl files:
   - `p_matrix_model.pkl`
   - `entropy_classifier_model.pkl`
   - `river_halfspace_model.pkl`
   - `feature_scaler.pkl`

### Option 2: Local Training

```bash
# Install dependencies
pip install scikit-learn xgboost river pandas numpy matplotlib seaborn joblib

# Run training
python train_models.py

# Evaluate
python evaluate_models.py
```

## Output

After training, you'll get 4 .pkl files:

```
backend/ml/models/
├── p_matrix_model.pkl              # Random Forest classifier
├── entropy_classifier_model.pkl    # XGBoost classifier
├── river_halfspace_model.pkl       # River anomaly detector
└── feature_scaler.pkl              # Feature normalization
```

## Using Trained Models

Copy the .pkl files to `backend/ml/models/` and they'll be automatically loaded at runtime.

```python
from backend.ml.inference.model_loader import get_ml_loader

ml_loader = get_ml_loader()
score = ml_loader.predict_p_matrix([7.9, 1024000, 0.8, 1234, 5678])
```

## Retraining

To retrain with new data:

1. Collect feedback from past week
2. Run training script with new data
3. Download updated .pkl files
4. Replace old files in `backend/ml/models/`
5. System automatically uses new models

## Expected Performance

- **Accuracy**: 92-98%
- **Precision**: 88-96%
- **Recall**: 85-95%
- **F1 Score**: 87-95%
- **AUC**: 0.95-0.99

## Troubleshooting

### Models not loading
- Check that .pkl files exist in `backend/ml/models/`
- Check file permissions
- Check logs for specific errors

### Poor accuracy
- Ensure BETH dataset is representative
- Check feature extraction
- Verify training data quality
- Consider retraining with more data

### Slow inference
- Models should predict in <10ms
- Check system resources
- Consider model optimization
