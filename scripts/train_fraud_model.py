"""Train on the past, select on validation, and evaluate once on a later holdout."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
FEATURES = [f"V{i}" for i in range(1, 29)] + ["Amount"]
THRESHOLDS = np.linspace(0, 1, 1001)


def make_features(frame):
    """Use only 28 source PCA values and log(1 + amount); never Time or Class."""
    missing = set(FEATURES) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing feature columns: {', '.join(sorted(missing))}")
    values = frame[FEATURES].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, -1] < 0).any():
        raise ValueError("Features must be finite numeric values and Amount must be non-negative.")
    values[:, -1] = np.log1p(values[:, -1])
    return values


def chronological_split(frame):
    """Remove exact source repeats and keep equal timestamps on the same side."""
    unique = frame.drop_duplicates().sort_values("Time", kind="stable")
    first = float(unique.Time.quantile(.6))
    second = float(unique.Time.quantile(.8))
    parts = [unique[unique.Time < first], unique[(unique.Time >= first) & (unique.Time < second)],
             unique[unique.Time >= second]]
    if any(part.empty or part.Class.nunique() != 2 for part in parts):
        raise ValueError("Each chronological split must contain both source labels.")
    return parts, {"validation_starts_at_elapsed_second": first,
                   "test_starts_at_elapsed_second": second,
                   "exact_duplicate_rows_removed": len(frame) - len(unique)}


def operating_curve(labels, scores):
    """Return exact confusion counts for each score threshold, using >= semantics."""
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    order = np.argsort(scores, kind="stable")
    ordered = scores[order]
    prefix = np.r_[0, np.cumsum(labels[order])]
    index = np.searchsorted(ordered, THRESHOLDS, side="left")
    fn = prefix[index]
    tp = labels.sum() - fn
    fp = len(labels) - index - tp
    tn = index - fn
    return [[round(float(t), 3), int(a), int(b), int(c), int(d)]
            for t, a, b, c, d in zip(THRESHOLDS, tp, fp, fn, tn)]


def metrics(row):
    threshold, tp, fp, fn, tn = row
    return {"threshold": threshold, "true_positives": tp, "false_positives": fp,
            "false_negatives": fn, "true_negatives": tn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f2": 5 * tp / (5 * tp + 4 * fn + fp) if tp + fp + fn else 0,
            "alert_count": tp + fp, "count": tp + fp + fn + tn}


def train(database, output, model_path):
    with duckdb.connect(str(database), read_only=True) as con:
        frame = con.execute('SELECT elapsed_seconds AS Time, amount AS Amount, is_fraud AS Class, '
                            + ', '.join(FEATURES[:-1]) + ' FROM transactions').fetchdf()
        quality = json.loads(con.execute("SELECT report_json FROM data_quality").fetchone()[0])
    parts, split_info = chronological_split(frame)
    train_frame, validation_frame, test_frame = parts
    x_train, x_valid, x_test = [make_features(part) for part in parts]
    y_train, y_valid, y_test = [part.Class.to_numpy(dtype=int) for part in parts]
    candidates = {
        "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42)),
        "Histogram gradient boosting": HistGradientBoostingClassifier(
            class_weight="balanced", max_iter=120, max_leaf_nodes=15,
            learning_rate=.08, l2_regularization=1., early_stopping=False, random_state=42),
    }
    validation_results = []
    for name, estimator in candidates.items():
        print(f"Training {name}…", flush=True)
        estimator.fit(x_train, y_train)
        score = estimator.predict_proba(x_valid)[:, 1]
        validation_results.append({"name": name, "average_precision": float(average_precision_score(y_valid, score))})
    selected = max(validation_results, key=lambda row: row["average_precision"])["name"]
    model = candidates[selected]
    valid_scores = model.predict_proba(x_valid)[:, 1]
    valid_curve = operating_curve(y_valid, valid_scores)
    # F2 gives recall more weight. This is an educational objective, not a financial cost model.
    best_index = max(range(len(valid_curve)), key=lambda i: (metrics(valid_curve[i])["f2"], i))
    recommended = valid_curve[best_index][0]
    test_scores = model.predict_proba(x_test)[:, 1]
    test_curve = operating_curve(y_test, test_scores)
    test_metrics = metrics(test_curve[best_index])
    prediction = test_scores >= recommended
    examples = []
    for truth, flagged in [(1, True), (0, True), (1, False), (0, False)]:
        positions = np.flatnonzero((y_test == truth) & (prediction == flagged))[:5]
        for position in positions:
            row = test_frame.iloc[int(position)]
            examples.append({"example_id": f"Holdout-{len(examples) + 1:02d}",
                             "elapsed_hour": int(row.Time // 3600), "amount": float(row.Amount),
                             "source_label": int(truth), "model_score": float(test_scores[position])})
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path, compress=3)
    artifact_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    report = {
        "schema_version": 1, "model_name": selected,
        "source_sha256": quality["source_sha256"], "sklearn_version": sklearn.__version__,
        "features": FEATURES, "feature_transform": "V1–V28 unchanged; log1p(Amount); no Time or Class input",
        "split_method": "Chronological 60/20/20 by source Time quantiles; equal timestamps stay together",
        "split_info": split_info,
        "splits": {name: {"count": len(part), "source_fraud_count": int(part.Class.sum()),
                         "first_second": float(part.Time.min()), "last_second": float(part.Time.max())}
                   for name, part in zip(["train", "validation", "test"], parts)},
        "selection": "Highest validation average precision; no test-based model selection",
        "validation_candidates": validation_results,
        "recommended_threshold": recommended, "recommended_index": best_index,
        "threshold_selection": "Maximum validation F2 on a fixed 0.001 threshold grid; ties choose higher threshold",
        "validation_at_recommended": metrics(valid_curve[best_index]),
        "test_at_recommended": test_metrics,
        "test_average_precision": float(average_precision_score(y_test, test_scores)),
        "test_roc_auc": float(roc_auc_score(y_test, test_scores)),
        "test_prevalence": float(y_test.mean()),
        "always_non_fraud_baseline": {"recall": 0., "accuracy": float(1 - y_test.mean()),
                                       "false_negatives": int(y_test.sum())},
        "curve_columns": ["threshold", "true_positives", "false_positives", "false_negatives", "true_negatives"],
        "test_curve": test_curve,
        "examples": examples,
        "example_selection": "Up to five examples of each outcome at the validation-selected threshold; not a representative sample",
        "artifact_sha256": artifact_hash,
        "limitations": [
            "Model scores are not calibrated fraud probabilities.",
            "Source labels are preserved; a model flag is a prediction, not a confirmed fraud finding.",
            "The test set covers a later part of the same two-day 2013 dataset, not future real-world performance.",
            "Source PCA features were already transformed; their original transformation cannot be refit on training data.",
            "There are no customer identifiers, so customer overlap across splits cannot be assessed.",
            "Changing the test threshold interactively is exploration; it does not create a new unbiased test result.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"model": selected, "recommended_threshold": recommended,
                      "test": test_metrics, "test_average_precision": report["test_average_precision"]}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/transactions.duckdb")
    parser.add_argument("--output", type=Path, default=ROOT / "dashboard/data/model_evaluation.json")
    parser.add_argument("--model", type=Path, default=ROOT / "models/fraud_detector.joblib")
    args = parser.parse_args()
    train(args.database, args.output, args.model)
