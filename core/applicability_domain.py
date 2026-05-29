"""applicability_domain.py — Applicability Domain check using kNN (Jaccard) distance.

No Streamlit dependencies. Pure logic module.
"""

from __future__ import annotations

import numpy as np
from typing import Optional

from sklearn.neighbors import NearestNeighbors
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs

from core.model_pipeline import predict_and_interpret


# ---------------------------------------------------------------------------
# Build AD model
# ---------------------------------------------------------------------------

def build_ad_model(X_train: np.ndarray) -> tuple:
    """Build kNN model for AD assessment. Call ONCE, cache in session_state.

    Uses sklearn NearestNeighbors with metric='jaccard', n_neighbors=min(5, len(X_train)).
    Computes: threshold = mean(train distances) + 2*std(train distances)

    Returns (knn, threshold, train_mean, train_std) — all floats except knn.
    """
    n_neighbors = min(5, len(X_train))
    knn = NearestNeighbors(n_neighbors=n_neighbors, metric="jaccard", n_jobs=-1)
    # Jaccard requires boolean arrays — convert once here to silence DataConversionWarning
    X_bool = X_train.astype(bool)
    knn.fit(X_bool)

    # kneighbors on training data includes self (distance 0) — mean over all 5 neighbors
    dist_train, _ = knn.kneighbors(X_bool)
    mean_dist_train = dist_train.mean(axis=1)

    train_mean: float = float(np.mean(mean_dist_train))
    train_std: float = float(np.std(mean_dist_train))
    threshold: float = train_mean + 2.0 * train_std

    return knn, threshold, train_mean, train_std


# ---------------------------------------------------------------------------
# Check applicability domain
# ---------------------------------------------------------------------------

def check_applicability_domain(
    smiles: str,
    ad_tuple: tuple,
    model,
    explainer,
    bit_db: dict,
    radius: int = 3,
    n_bits: int = 2048,
) -> dict:
    """Check if molecule is within applicability domain.

    Also calls predict_and_interpret(top_n=5) for prediction context.

    Returns dict with:
        smiles, inside_ad (bool), mean_knn_distance, ad_threshold,
        train_mean_dist, train_std_dist, ad_confidence (str: HIGH/MODERATE/LOW/OUTSIDE AD),
        rf_prediction_std (float or None), prediction (result from predict_and_interpret)
    """
    knn, threshold, train_mean, train_std = ad_tuple

    # --- Fingerprint ---
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"Invalid SMILES: {smiles!r}"}

    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    fp_array = np.zeros(n_bits, dtype=np.int32)
    DataStructs.ConvertToNumpyArray(fp, fp_array)
    X_query = fp_array.reshape(1, -1)

    # --- kNN distance ---
    distances, _ = knn.kneighbors(X_query.astype(bool))
    mean_knn_distance: float = float(distances[0].mean())

    inside_ad: bool = mean_knn_distance <= threshold

    # --- AD confidence ---
    if inside_ad:
        margin_pct = (threshold - mean_knn_distance) / threshold * 100.0
        if margin_pct > 30.0:
            ad_confidence = "HIGH"
        elif margin_pct > 10.0:
            ad_confidence = "MODERATE"
        else:
            ad_confidence = "LOW"
    else:
        overshoot = (mean_knn_distance - threshold) / threshold * 100.0
        ad_confidence = f"OUTSIDE AD (+{overshoot:.1f}% beyond threshold)"

    # --- RF prediction std (tree variance) ---
    rf_prediction_std: Optional[float] = None
    if hasattr(model, "estimators_"):
        try:
            tree_preds = np.array(
                [est.predict_proba(X_query)[0][1] for est in model.estimators_]
            )
            rf_prediction_std = float(tree_preds.std())
        except Exception:
            rf_prediction_std = None

    # --- Full prediction + interpretation ---
    prediction = predict_and_interpret(
        smiles=smiles,
        model=model,
        explainer=explainer,
        bit_db=bit_db,
        radius=radius,
        n_bits=n_bits,
        top_n=5,
    )

    return {
        "smiles": smiles,
        "inside_ad": inside_ad,
        "mean_knn_distance": mean_knn_distance,
        "ad_threshold": threshold,
        "train_mean_dist": train_mean,
        "train_std_dist": train_std,
        "ad_confidence": ad_confidence,
        "rf_prediction_std": rf_prediction_std,
        "prediction": prediction,
    }


# ---------------------------------------------------------------------------
# Format AD context for LLM
# ---------------------------------------------------------------------------

def format_ad_context(result: dict) -> str:
    """Format AD check result as multi-line string for LLM.

    Starts with '=== APPLICABILITY DOMAIN ASSESSMENT ==='
    Includes: inside_ad, confidence, knn distance vs threshold,
    RF tree variance, prediction P(active), interpretation guidance.
    """
    if "error" in result:
        return f"=== APPLICABILITY DOMAIN ASSESSMENT ===\nError: {result['error']}"

    lines: list[str] = ["=== APPLICABILITY DOMAIN ASSESSMENT ===", ""]

    # Inside/outside summary
    status = "INSIDE" if result["inside_ad"] else "OUTSIDE"
    lines.append(f"Status: {status} applicability domain")
    lines.append(f"Confidence: {result['ad_confidence']}")
    lines.append("")

    # Distance metrics
    lines.append("--- kNN Distance Metrics ---")
    lines.append(f"Mean kNN distance (Jaccard): {result['mean_knn_distance']:.4f}")
    lines.append(f"AD threshold (mean + 2*std):  {result['ad_threshold']:.4f}")
    lines.append(f"Training mean distance:       {result['train_mean_dist']:.4f}")
    lines.append(f"Training std distance:        {result['train_std_dist']:.4f}")
    lines.append("")

    # RF tree variance
    lines.append("--- Random Forest Tree Variance ---")
    if result["rf_prediction_std"] is not None:
        std = result["rf_prediction_std"]
        consistency = "high" if std < 0.1 else "moderate" if std < 0.2 else "low"
        lines.append(
            f"Std of tree P(active) predictions: {std:.4f} "
            f"(tree agreement: {consistency})"
        )
    else:
        lines.append("Tree variance not available.")
    lines.append("")

    # Prediction summary
    pred = result.get("prediction", {})
    lines.append("--- Model Prediction ---")
    if "error" in pred:
        lines.append(f"Prediction error: {pred['error']}")
    else:
        p_active = pred.get("probability_active", None)
        p_inactive = pred.get("probability_inactive", None)
        prediction_label = pred.get("prediction", "unknown")
        lines.append(f"Predicted class: {prediction_label}")
        if p_active is not None:
            lines.append(f"P(active):   {p_active:.4f}")
        if p_inactive is not None:
            lines.append(f"P(inactive): {p_inactive:.4f}")
    lines.append("")

    # Interpretation guidance
    lines.append("--- Interpretation Guidance ---")
    if result["inside_ad"]:
        confidence = result["ad_confidence"]
        if confidence == "HIGH":
            lines.append(
                "The molecule is well within the training chemical space. "
                "Predictions are expected to be reliable."
            )
        elif confidence == "MODERATE":
            lines.append(
                "The molecule is within the training chemical space but near the boundary. "
                "Predictions should be treated with some caution."
            )
        else:  # LOW
            lines.append(
                "The molecule is at the edge of the training chemical space. "
                "Predictions may be less reliable; experimental validation is advised."
            )
    else:
        lines.append(
            "The molecule lies outside the training chemical space. "
            "Model predictions for this compound may not be reliable. "
            "Experimental validation is strongly recommended before drawing conclusions."
        )
    lines.append("")

    return "\n".join(lines)
