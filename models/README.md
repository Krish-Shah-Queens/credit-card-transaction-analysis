# Saved detector

`fraud_detector.joblib` is the project-generated histogram gradient boosting model described in [MODEL_CARD.md](../docs/MODEL_CARD.md). It was trained only on the chronological training split using V1–V28 and log-transformed Amount. It does not contain the raw dataset.

The app checks the artifact against the SHA-256 recorded in `dashboard/data/model_evaluation.json` before loading this known repository artifact. Predictions are separate from source labels. Rebuild with `python scripts/train_fraud_model.py`; use the pinned scikit-learn version in `requirements.txt`.

Training source: Worldline / ULB Machine Learning Group Credit Card Fraud Detection dataset, https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud . Original labels and dataset-derived evaluation examples remain subject to the source's separate ODbL / DbCL terms.
