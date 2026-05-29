"""Model evaluation metrics endpoint."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException

from backend.state import app_state

router = APIRouter()


def _enrichment_factor(labels, probs, pct: float) -> float:
    labels = np.asarray(labels, dtype=int)
    probs = np.asarray(probs, dtype=float)
    n_total = len(labels)
    total_actives = int(labels.sum())
    if n_total == 0 or total_actives == 0:
        return float("nan")
    top_n = max(1, int(np.ceil(n_total * pct)))
    order = np.argsort(probs)[::-1]
    top_rate = float(labels[order[:top_n]].mean())
    prevalence = total_actives / n_total
    return top_rate / prevalence


def _bootstrap_ci(metric_fn, labels, probs, n_iter: int = 1000) -> list[float | None]:
    labels = np.asarray(labels, dtype=int)
    probs = np.asarray(probs, dtype=float)
    n = len(labels)
    if n == 0:
        return [None, None]
    rng = np.random.default_rng(42)
    values = []
    for _ in range(n_iter):
        idx = rng.choice(n, size=n, replace=True)
        try:
            value = float(metric_fn(labels[idx], probs[idx]))
            if np.isfinite(value):
                values.append(value)
        except Exception:
            continue
    if not values:
        return [None, None]
    lo, hi = np.percentile(values, [2.5, 97.5])
    return [float(lo), float(hi)]


def _metric_payload(value: float, ci: list[float | None]) -> dict:
    return {
        "value": None if not np.isfinite(value) else float(value),
        "ci": ci,
    }


def compute_imbalance_metrics(y_true, y_pred_proba) -> dict:
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import average_precision_score, brier_score_loss

    labels = np.asarray(y_true, dtype=int)
    probs = np.asarray(y_pred_proba, dtype=float)
    assert len(labels) == len(probs)
    assert probs.min() >= 0.0 and probs.max() <= 1.0
    assert set(np.unique(labels)).issubset({0, 1})

    def average_precision_metric(y, p):
        if len(np.unique(y)) < 2 or int(np.sum(y)) == 0:
            return float("nan")
        return average_precision_score(y, p)

    def brier_metric(y, p):
        return brier_score_loss(y, p)

    def ece_metric(y, p):
        prob_true, prob_pred = calibration_curve(y, p, n_bins=10, strategy="quantile")
        if len(prob_true) == 0:
            return float("nan")
        quantiles = np.linspace(0, 1, 11)
        edges = np.unique(np.quantile(p, quantiles))
        if len(edges) <= 1:
            return float(np.mean(np.abs(prob_pred - prob_true)))
        edges[0] = -np.inf
        edges[-1] = np.inf
        bin_ids = np.digitize(p, edges[1:-1], right=True)
        counts = np.array([np.sum(bin_ids == i) for i in range(len(edges) - 1)], dtype=float)
        counts = counts[counts > 0]
        if len(counts) != len(prob_true):
            counts = np.full(len(prob_true), len(y) / max(len(prob_true), 1), dtype=float)
        return float(np.sum((counts / len(y)) * np.abs(prob_pred - prob_true)))

    metrics = {
        "average_precision": _metric_payload(
            float(average_precision_metric(labels, probs)),
            _bootstrap_ci(average_precision_metric, labels, probs),
        ),
        "brier_score": _metric_payload(
            float(brier_metric(labels, probs)),
            _bootstrap_ci(brier_metric, labels, probs),
        ),
        "ece": _metric_payload(
            float(ece_metric(labels, probs)),
            _bootstrap_ci(ece_metric, labels, probs),
        ),
        "ef_1": _metric_payload(
            float(_enrichment_factor(labels, probs, 0.01)),
            _bootstrap_ci(lambda y, p: _enrichment_factor(y, p, 0.01), labels, probs),
        ),
        "ef_5": _metric_payload(
            float(_enrichment_factor(labels, probs, 0.05)),
            _bootstrap_ci(lambda y, p: _enrichment_factor(y, p, 0.05), labels, probs),
        ),
        "ef_10": _metric_payload(
            float(_enrichment_factor(labels, probs, 0.10)),
            _bootstrap_ci(lambda y, p: _enrichment_factor(y, p, 0.10), labels, probs),
        ),
    }

    prob_true, prob_pred = calibration_curve(labels, probs, n_bins=10, strategy="quantile")
    return {
        "metrics": metrics,
        "reliability": {
            "mean_predicted": prob_pred.tolist(),
            "observed_rate": prob_true.tolist(),
        },
    }


@router.get("")
def evaluate():
    """Return ROC-AUC, PR-AUC, confusion matrix and ROC/PR curve data."""
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded.")
    if not app_state.has_training_data():
        raise HTTPException(status_code=400, detail="No training data loaded.")
    if not app_state.has_test_data():
        raise HTTPException(
            status_code=422,
            detail="Test set not loaded: imbalance metrics require an external test set uploaded via the Evaluation module.",
        )

    from sklearn.metrics import (
        roc_auc_score, average_precision_score,
        roc_curve, precision_recall_curve, confusion_matrix,
    )

    fps = app_state.training_fps
    labels = app_state.training_labels
    model = app_state.model

    try:
        probs = model.predict_proba(fps)[:, 1]
        preds = (probs >= 0.5).astype(int)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    roc_auc = float(roc_auc_score(labels, probs))
    pr_auc = float(average_precision_score(labels, probs))
    cm = confusion_matrix(labels, preds).tolist()
    imbalance_metrics = compute_imbalance_metrics(labels, probs)

    fpr, tpr, _ = roc_curve(labels, probs)
    prec, rec, _ = precision_recall_curve(labels, probs)

    # ── Test set metrics (optional) ───────────────────────────────────────────
    test_roc_auc = None
    test_pr_auc = None
    test_confusion_matrix = None
    test_roc_curve = None
    test_pr_curve = None
    test_imbalance_metrics = None
    test_n_active = None
    test_n_inactive = None

    try:
        t_fps = app_state.test_fps
        t_labels = app_state.test_labels
        t_probs = model.predict_proba(t_fps)[:, 1]
        t_preds = (t_probs >= 0.5).astype(int)

        test_confusion_matrix = confusion_matrix(t_labels, t_preds).tolist()
        test_n_active = int(t_labels.sum())
        test_n_inactive = int((t_labels == 0).sum())
        test_imbalance_metrics = compute_imbalance_metrics(t_labels, t_probs)

        if len(np.unique(t_labels)) >= 2:
            test_roc_auc = float(roc_auc_score(t_labels, t_probs))
            test_pr_auc = float(average_precision_score(t_labels, t_probs))
            t_fpr, t_tpr, _ = roc_curve(t_labels, t_probs)
            t_prec, t_rec, _ = precision_recall_curve(t_labels, t_probs)
            test_roc_curve = {"fpr": t_fpr.tolist(), "tpr": t_tpr.tolist()}
            test_pr_curve = {"precision": t_prec.tolist(), "recall": t_rec.tolist()}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Test set imbalance metrics failed: {exc}") from exc

    return {
        "evaluation_api_version": 2,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "confusion_matrix": cm,
        "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "pr_curve": {"precision": prec.tolist(), "recall": rec.tolist()},
        "n_active": int(labels.sum()),
        "n_inactive": int((labels == 0).sum()),
        "imbalance_metrics": imbalance_metrics,
        "test_roc_auc": test_roc_auc,
        "test_pr_auc": test_pr_auc,
        "test_confusion_matrix": test_confusion_matrix,
        "test_roc_curve": test_roc_curve,
        "test_pr_curve": test_pr_curve,
        "test_imbalance_metrics": test_imbalance_metrics,
        "test_n_active": test_n_active,
        "test_n_inactive": test_n_inactive,
    }
