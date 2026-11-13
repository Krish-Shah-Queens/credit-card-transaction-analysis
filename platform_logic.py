"""Shared calculations for the Python dashboard; no Streamlit side effects."""
import numpy as np


def summary(groups):
    count = int(groups.transaction_count.sum())
    total = int((groups.amount_cents * groups.transaction_count).sum())
    fraud = int((groups.is_fraud * groups.transaction_count).sum())
    hist = groups.groupby("amount_cents").transaction_count.sum().sort_index()
    quantiles = []
    for p in [.5, .95]:
        if not count:
            quantiles.append(None)
            continue
        position = (count - 1) * p
        low, high = int(np.floor(position)), int(np.ceil(position))
        cumulative = hist.cumsum().to_numpy()
        values = hist.index.to_numpy()
        a, b = values[np.searchsorted(cumulative, [low, high], side="right")]
        quantiles.append(float(a + (b - a) * (position - low)))
    return {"count": count, "total": total, "fraud": fraud,
            "mean": total / count if count else None, "median": quantiles[0], "p95": quantiles[1],
            "maximum": int(hist.index.max()) if count else None,
            "zero": int(groups.loc[groups.amount_cents == 0, "transaction_count"].sum()),
            "fraud_rate": fraud / count if count else None}


def operating_metrics(row):
    threshold, tp, fp, fn, tn = row
    return {"threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "alerts": tp + fp, "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "alert_rate": (tp + fp) / (tp + fp + fn + tn) if tp + fp + fn + tn else None}
