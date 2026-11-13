import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from platform_logic import summary
from scripts.train_fraud_model import FEATURES, chronological_split, make_features, operating_curve, metrics

ROOT = Path(__file__).resolve().parents[1]


def feature_frame():
    return pd.DataFrame([{**{f"V{i}": 0. for i in range(1, 29)}, "Amount": 10., "Class": 0, "Time": 100.}])


def test_target_and_time_never_enter_model_features():
    source = feature_frame()
    changed = source.assign(Class=1, Time=999999)
    np.testing.assert_array_equal(make_features(source), make_features(changed))
    assert make_features(source).shape == (1, 29)
    assert make_features(source)[0, -1] == pytest.approx(np.log1p(10))


@pytest.mark.parametrize("column,value", [("V1", float("nan")), ("V28", float("inf")), ("Amount", -1)])
def test_invalid_features_rejected(column, value):
    frame = feature_frame()
    frame[column] = value
    with pytest.raises(ValueError):
        make_features(frame)


def test_missing_feature_rejected():
    with pytest.raises(ValueError, match="Missing feature"):
        make_features(feature_frame().drop(columns="V14"))


def test_split_is_chronological_and_removes_exact_source_duplicates():
    frame = pd.DataFrame({"Time": np.repeat(np.arange(50), 2), "Class": np.tile([0, 1], 50), "Amount": 1.})
    frame = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    parts, info = chronological_split(frame)
    assert info["exact_duplicate_rows_removed"] == 1
    assert sum(len(p) for p in parts) == 100
    assert parts[0].Time.max() < parts[1].Time.min()
    assert parts[1].Time.max() < parts[2].Time.min()
    assert set(parts[0].Time).isdisjoint(set(parts[1].Time))


def test_curve_uses_inclusive_threshold_and_conserves_confusion_counts():
    curve = operating_curve([0, 1, 0], [.2, .8, .9])
    assert curve[800] == [.8, 1, 1, 0, 1]
    assert curve[0] == [0., 1, 2, 0, 0]
    assert curve[1000] == [1., 0, 0, 1, 2]
    assert metrics(curve[1000])["precision"] is None
    assert all(sum(row[1:]) == 3 for row in curve)


def test_committed_model_matches_report_and_does_not_use_source_label():
    report = json.loads((ROOT / "dashboard/data/model_evaluation.json").read_text())
    artifact = ROOT / "models/fraud_detector.joblib"
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == report["artifact_sha256"]
    model = joblib.load(artifact)
    source = feature_frame()
    np.testing.assert_array_equal(model.predict_proba(make_features(source)),
                                  model.predict_proba(make_features(source.assign(Class=1))))
    assert model.n_features_in_ == len(FEATURES)
    row = report["test_curve"][report["recommended_index"]]
    assert metrics(row) == report["test_at_recommended"]
    for row in report["test_curve"]:
        assert sum(row[1:]) == report["splits"]["test"]["count"]
        assert row[1] + row[3] == report["splits"]["test"]["source_fraud_count"]


def test_python_summary_weights_groups_without_relabeling():
    groups = pd.DataFrame([[0,0,0,1],[1,1,10000,2],[3,0,100000,1]],
                          columns=["elapsed_hour","is_fraud","amount_cents","transaction_count"])
    s = summary(groups)
    assert s["count"] == 4
    assert s["total"] == 120000
    assert s["median"] == 10000
    assert s["p95"] == pytest.approx(86500)
    assert s["fraud_rate"] == .5
