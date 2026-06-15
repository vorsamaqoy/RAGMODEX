"""evaluation_page.py — Model evaluation on an uploaded test set.

Sections
--------
1. Performance Metrics  — ROC-AUC, Precision, Recall, Specificity, F1, MCC,
                          Balanced Accuracy + ROC curve + Precision-Recall curve
2. Prediction Distribution — histogram split by true class
3. Scaffold Analysis  — Murcko scaffold enrichment grid
"""

from __future__ import annotations

import base64
import html as _html_lib
import math
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ---------------------------------------------------------------------------
# Helpers — matplotlib style
# ---------------------------------------------------------------------------

_BG = "#090b18"       # --color-bg
_CARD_BG = "#141728"  # --color-card
_BORDER = "#1c2040"   # --color-border
_GRID = "#1c2040"     # --color-border
_TEXT = "#8890c4"     # --color-text-muted
_TITLE = "#eceaf8"    # --color-text
_ACCENT = "#e0a85a"   # --color-accent (warm amber)
_GREEN = "#50c896"    # --color-success
_RED = "#e05070"      # --color-danger
_ORANGE = "#d4804a"   # --color-warning
_GRAY = "#484c7a"     # --color-text-dim


def _style_ax(ax, fig):
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.tick_params(colors=_TEXT, labelsize=8)
    ax.xaxis.label.set_color(_TEXT)
    ax.yaxis.label.set_color(_TEXT)
    ax.title.set_color(_TITLE)
    for spine in ax.spines.values():
        spine.set_edgecolor(_BORDER)
    ax.grid(True, color=_GRID, linewidth=0.5, alpha=0.8)


# ---------------------------------------------------------------------------
# Cached scaffold computation
# ---------------------------------------------------------------------------

@st.cache_data
def _compute_scaffold_stats(
    test_df: pd.DataFrame,
    smiles_col: str,
    label_col: str,
    train_df: pd.DataFrame | None = None,
    train_smiles_col: str | None = None,
    train_label_col: str | None = None,
) -> pd.DataFrame:
    """Compute Murcko scaffold enrichment stats from test (+ optional train). Cached."""
    try:
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold

        def _extract_rows(df, sc, lc, source):
            rows = []
            for _, row in df.iterrows():
                smi = str(row[sc]).strip()
                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    continue
                try:
                    scaffold_mol = MurckoScaffold.GetScaffoldForMol(mol)
                    scaffold_smi = Chem.MolToSmiles(scaffold_mol)
                except Exception:
                    continue
                rows.append({
                    "scaffold": scaffold_smi,
                    "true_label": int(row[lc]),
                    "pred_proba": float(row["_pred_proba"]) if "_pred_proba" in row.index else float("nan"),
                    "source": source,
                })
            return rows

        rows = _extract_rows(test_df, smiles_col, label_col, "test")
        if train_df is not None and train_smiles_col and train_label_col:
            rows += _extract_rows(train_df, train_smiles_col, train_label_col, "train")

        if not rows:
            return pd.DataFrame()

        sdf = pd.DataFrame(rows)

        def _sources(x):
            s = set(x)
            if "train" in s and "test" in s:
                return "both"
            return next(iter(s))

        grouped = (
            sdf.groupby("scaffold")
            .agg(
                total_count=("true_label", "count"),
                active_count=("true_label", "sum"),
                mean_pred_proba=("pred_proba", "mean"),   # NaN for train-only scaffolds
                source=("source", _sources),
            )
            .reset_index()
        )
        grouped["active_rate"] = grouped["active_count"] / grouped["total_count"]
        grouped = grouped[grouped["total_count"] >= 2].copy()
        grouped = grouped.sort_values(
            ["active_rate", "active_count"], ascending=[False, False]
        ).reset_index(drop=True)
        return grouped

    except Exception as exc:
        return pd.DataFrame({"_error": [str(exc)]})


# ---------------------------------------------------------------------------
# Section 1 — Performance Metrics
# ---------------------------------------------------------------------------

def _plot_roc(fpr, tpr, auc, y_true, y_pred):
    import matplotlib.pyplot as plt
    from sklearn.metrics import confusion_matrix

    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    _style_ax(ax, fig)

    ax.plot(fpr, tpr, color=_ACCENT, lw=2, label=f"AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], color=_GRAY, lw=1, linestyle="--", alpha=0.6)

    try:
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        op_fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        op_tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        ax.scatter(
            [op_fpr], [op_tpr],
            color=_RED, s=55, zorder=5,
            label="Threshold = 0.5",
        )
    except Exception:
        pass

    ax.set_xlabel("False Positive Rate", fontsize=9)
    ax.set_ylabel("True Positive Rate", fontsize=9)
    ax.set_title("ROC Curve", fontsize=11)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.02])
    ax.legend(
        facecolor=_CARD_BG, edgecolor=_BORDER,
        labelcolor=_TITLE, fontsize=8,
    )
    fig.tight_layout()
    return fig


def _plot_pr(prec_vals, rec_vals, ap):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    _style_ax(ax, fig)

    ax.plot(rec_vals, prec_vals, color=_GREEN, lw=2, label=f"AP = {ap:.3f}")
    ax.fill_between(rec_vals, prec_vals, alpha=0.08, color=_GREEN)

    ax.set_xlabel("Recall", fontsize=9)
    ax.set_ylabel("Precision", fontsize=9)
    ax.set_title("Precision-Recall Curve", fontsize=11)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.legend(
        facecolor=_CARD_BG, edgecolor=_BORDER,
        labelcolor=_TITLE, fontsize=8,
    )
    fig.tight_layout()
    return fig


def _format_ci(value: float, ci: tuple[float, float]) -> str:
    lo, hi = ci
    if np.isnan(value) or np.isnan(lo) or np.isnan(hi):
        return "n/a"
    return f"{value:.3f} [{lo:.3f}, {hi:.3f}]"


def _test_set_hash(y_true, y_pred_proba) -> str:
    import hashlib

    y_true_arr = np.asarray(y_true, dtype=np.int8)
    y_proba_arr = np.asarray(y_pred_proba, dtype=np.float64)
    h = hashlib.sha256()
    h.update(y_true_arr.tobytes())
    h.update(y_proba_arr.tobytes())
    return h.hexdigest()


def _enrichment_factor(y_true, y_pred_proba, pct: float) -> float:
    y_true_arr = np.asarray(y_true, dtype=int)
    y_proba_arr = np.asarray(y_pred_proba, dtype=float)
    n_total = len(y_true_arr)
    if n_total == 0:
        return float("nan")
    total_actives = int(np.sum(y_true_arr == 1))
    if total_actives == 0:
        return float("nan")
    top_n = max(1, int(np.ceil(n_total * pct)))
    order = np.argsort(y_proba_arr)[::-1]
    top = y_true_arr[order[:top_n]]
    top_rate = float(np.mean(top == 1))
    prevalence = total_actives / n_total
    return top_rate / prevalence if prevalence > 0 else float("nan")


def _ece_score(y_true, y_pred_proba, n_bins: int = 10) -> float:
    from sklearn.calibration import calibration_curve

    y_true_arr = np.asarray(y_true, dtype=int)
    y_proba_arr = np.asarray(y_pred_proba, dtype=float)
    if len(y_true_arr) == 0:
        return float("nan")
    prob_true, prob_pred = calibration_curve(
        y_true_arr,
        y_proba_arr,
        n_bins=n_bins,
        strategy="quantile",
    )
    try:
        quantiles = np.linspace(0, 1, n_bins + 1)
        edges = np.quantile(y_proba_arr, quantiles)
        edges[0] = -np.inf
        edges[-1] = np.inf
        edges = np.unique(edges)
        bin_ids = np.digitize(y_proba_arr, edges[1:-1], right=True)
        counts = np.array([np.sum(bin_ids == i) for i in range(len(edges) - 1)], dtype=float)
        counts = counts[counts > 0]
        if len(counts) != len(prob_true):
            counts = np.full(len(prob_true), len(y_true_arr) / max(len(prob_true), 1), dtype=float)
        weights = counts / len(y_true_arr)
        return float(np.sum(weights * np.abs(prob_pred - prob_true)))
    except Exception:
        return float(np.mean(np.abs(prob_pred - prob_true))) if len(prob_true) else float("nan")


def bootstrap_ci(metric_fn, y_true, y_proba, n_iter=1000) -> tuple[float, float]:
    y_true_arr = np.asarray(y_true)
    y_proba_arr = np.asarray(y_proba)
    n = len(y_true_arr)
    if n == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(42)
    values = []
    for _ in range(n_iter):
        idx = rng.choice(n, size=n, replace=True)
        try:
            value = float(metric_fn(y_true_arr[idx], y_proba_arr[idx]))
            if not np.isnan(value) and np.isfinite(value):
                values.append(value)
        except Exception:
            continue
    if not values:
        return (float("nan"), float("nan"))
    lo, hi = np.percentile(values, [2.5, 97.5])
    return (float(lo), float(hi))


def compute_imbalance_metrics(y_true, y_pred_proba) -> dict:
    from sklearn.metrics import average_precision_score, brier_score_loss

    y_true_arr = np.asarray(y_true, dtype=int)
    y_proba_arr = np.asarray(y_pred_proba, dtype=float)
    assert len(y_true_arr) == len(y_proba_arr)
    assert y_proba_arr.min() >= 0.0 and y_proba_arr.max() <= 1.0
    assert set(np.unique(y_true_arr)).issubset({0, 1})

    def average_precision_metric(yt, yp):
        if len(np.unique(yt)) < 2 or np.sum(yt == 1) == 0:
            return float("nan")
        return average_precision_score(yt, yp)

    metric_fns = {
        "average_precision": average_precision_metric,
        "brier_score": lambda yt, yp: brier_score_loss(yt, yp),
        "ece": lambda yt, yp: _ece_score(yt, yp),
        "ef_1": lambda yt, yp: _enrichment_factor(yt, yp, 0.01),
        "ef_5": lambda yt, yp: _enrichment_factor(yt, yp, 0.05),
        "ef_10": lambda yt, yp: _enrichment_factor(yt, yp, 0.10),
    }

    metrics = {}
    for name, fn in metric_fns.items():
        try:
            value = float(fn(y_true_arr, y_proba_arr))
        except Exception:
            value = float("nan")
        metrics[name] = {
            "value": value,
            "ci": bootstrap_ci(fn, y_true_arr, y_proba_arr),
        }

    return metrics


@st.cache_data(show_spinner=False)
def _compute_imbalance_metrics_cached(test_set_hash: str, y_true, y_pred_proba) -> dict:
    return compute_imbalance_metrics(y_true, y_pred_proba)


def _plot_reliability_diagram(y_true, y_proba, ece: float):
    import matplotlib.pyplot as plt
    from sklearn.calibration import calibration_curve

    prob_true, prob_pred = calibration_curve(
        y_true,
        y_proba,
        n_bins=10,
        strategy="quantile",
    )
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    _style_ax(ax, fig)
    ax.scatter(prob_pred, prob_true, color=_GREEN, s=46, zorder=5, label="Quantile bins")
    ax.plot([0, 1], [0, 1], color=_GRAY, lw=1, linestyle="--", alpha=0.6, label="Perfect calibration")
    ax.set_xlabel("Mean Predicted Probability", fontsize=9)
    ax.set_ylabel("Observed Active Rate", fontsize=9)
    ax.set_title(f"Reliability Diagram · ECE = {ece:.3f}", fontsize=11)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.0])
    ax.set_aspect("equal", adjustable="box")
    ax.legend(
        facecolor=_CARD_BG, edgecolor=_BORDER,
        labelcolor=_TITLE, fontsize=8,
    )
    fig.tight_layout()
    return fig


def _render_imbalance_section(y_true, y_proba):
    import matplotlib.pyplot as plt

    st.subheader("Class Imbalance Metrics")
    st.caption(
        "These metrics emphasize ranking quality, calibration, and early enrichment when active molecules are rare."
    )

    test_set_hash = _test_set_hash(y_true, y_proba)
    metrics = _compute_imbalance_metrics_cached(
        test_set_hash,
        tuple(map(int, y_true)),
        tuple(map(float, y_proba)),
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(
        "Average Precision (PR-AUC)",
        _format_ci(metrics["average_precision"]["value"], metrics["average_precision"]["ci"]),
    )
    c2.metric(
        "Brier Score",
        _format_ci(metrics["brier_score"]["value"], metrics["brier_score"]["ci"]),
    )
    c3.metric(
        "Expected Calibration Error",
        _format_ci(metrics["ece"]["value"], metrics["ece"]["ci"]),
    )
    c4.metric("Enrichment Factor @1%", _format_ci(metrics["ef_1"]["value"], metrics["ef_1"]["ci"]))
    c5.metric("Enrichment Factor @5%", _format_ci(metrics["ef_5"]["value"], metrics["ef_5"]["ci"]))
    c6.metric("Enrichment Factor @10%", _format_ci(metrics["ef_10"]["value"], metrics["ef_10"]["ci"]))

    st.markdown("")

    try:
        fig = _plot_reliability_diagram(y_true, y_proba, metrics["ece"]["value"])
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    except Exception as exc:
        st.error(f"Reliability diagram: {exc}")


def _render_metrics_section(y_true, y_pred, y_proba):
    import matplotlib.pyplot as plt
    from sklearn.metrics import (
        average_precision_score,
        balanced_accuracy_score,
        confusion_matrix,
        f1_score,
        matthews_corrcoef,
        precision_recall_curve,
        precision_score,
        recall_score,
        roc_auc_score,
        roc_curve,
    )

    try:
        auc = roc_auc_score(y_true, y_proba)
    except Exception:
        auc = float("nan")

    try:
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        mcc = matthews_corrcoef(y_true, y_pred)
        bal_acc = balanced_accuracy_score(y_true, y_pred)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    except Exception as exc:
        st.error(f"Error computing metrics: {exc}")
        return

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("ROC-AUC",      f"{auc:.3f}")
    c2.metric("Precision",    f"{precision:.3f}")
    c3.metric("Recall",       f"{recall:.3f}")
    c4.metric("Specificity",  f"{specificity:.3f}")
    c5.metric("F1 Score",     f"{f1:.3f}")
    c6.metric("MCC",          f"{mcc:.3f}")
    c7.metric("Balanced Acc", f"{bal_acc:.3f}")

    st.markdown("")

    col_roc, col_pr = st.columns(2)
    with col_roc:
        try:
            fpr, tpr, _ = roc_curve(y_true, y_proba)
            fig = _plot_roc(fpr, tpr, auc, y_true, y_pred)
            st.pyplot(fig, width="stretch")
            plt.close(fig)
        except Exception as exc:
            st.error(f"ROC curve: {exc}")

    with col_pr:
        try:
            prec_vals, rec_vals, _ = precision_recall_curve(y_true, y_proba)
            ap = average_precision_score(y_true, y_proba)
            fig = _plot_pr(prec_vals, rec_vals, ap)
            st.pyplot(fig, width="stretch")
            plt.close(fig)
        except Exception as exc:
            st.error(f"PR curve: {exc}")


# ---------------------------------------------------------------------------
# Section 2 — Prediction Distribution
# ---------------------------------------------------------------------------

def _render_distribution_section(y_true, y_proba):
    import matplotlib.pyplot as plt

    try:
        n_active = int(np.sum(y_true == 1))
        n_inactive = int(np.sum(y_true == 0))
        proba_active = y_proba[y_true == 1]
        proba_inactive = y_proba[y_true == 0]

        fig, ax = plt.subplots(figsize=(9, 3.5))
        _style_ax(ax, fig)
        ax.grid(True, color=_GRID, linewidth=0.5, alpha=0.8, axis="y")

        bins = np.linspace(0, 1, 21)
        ax.hist(
            proba_active, bins=bins, alpha=0.6, color=_GREEN,
            label=f"Active (n={n_active})", edgecolor="none",
        )
        ax.hist(
            proba_inactive, bins=bins, alpha=0.6, color=_RED,
            label=f"Inactive (n={n_inactive})", edgecolor="none",
        )
        ax.axvline(x=0.5, color=_TEXT, linestyle="--", lw=1.5, label="Threshold = 0.5")

        ax.set_xlabel("Predicted Probability of Activity", fontsize=9)
        ax.set_ylabel("Count", fontsize=9)
        ax.set_title("Distribution of Predicted Probabilities", fontsize=11)
        ax.set_xlim([0.0, 1.0])
        ax.legend(
            facecolor=_CARD_BG, edgecolor=_BORDER,
            labelcolor=_TITLE, fontsize=9,
        )
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)

    except Exception as exc:
        st.error(f"Distribution plot error: {exc}")


# ---------------------------------------------------------------------------
# Section 3 — Scaffold Analysis
# ---------------------------------------------------------------------------

def _scaffold_img_b64(smiles: str, size=(150, 120)) -> str | None:
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        img = Draw.MolToImage(mol, size=size)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


_SOURCE_BADGE = {
    "test":  ("#102040", "#5bc4f5", "Test"),
    "train": ("#182040", "#50c896", "Train"),
    "both":  ("#2a2010", "#e0a85a", "Train + Test"),
}


def _scaffold_card_html(row: pd.Series) -> str:
    scaffold_smi = str(row["scaffold"])
    active_rate = float(row["active_rate"])
    active_count = int(row["active_count"])
    total_count = int(row["total_count"])
    raw_proba = row.get("mean_pred_proba", float("nan"))
    mean_proba = float(raw_proba) if pd.notna(raw_proba) else None
    source = str(row.get("source", "test"))
    pct = int(round(active_rate * 100))

    if active_rate >= 0.6:
        bar_color = _GREEN
    elif active_rate >= 0.3:
        bar_color = _ORANGE
    else:
        bar_color = _RED

    badge_bg, badge_fg, badge_label = _SOURCE_BADGE.get(source, ("#1c2040", "#8890c4", source))

    img_b64 = _scaffold_img_b64(scaffold_smi)
    if img_b64:
        img_html = (
            f'<div style="position:relative;">'
            f'<img src="data:image/png;base64,{img_b64}" '
            f'style="width:100%;display:block;background:#f5f3ee;" />'
            f'<span style="position:absolute;top:6px;right:6px;'
            f'background:{badge_bg};color:{badge_fg};font-size:0.6rem;'
            f'font-weight:600;padding:2px 6px;border-radius:4px;'
            f'font-family:sans-serif;letter-spacing:0.04em;">{badge_label}</span>'
            f'</div>'
        )
    else:
        img_html = (
            '<div style="height:120px;background:#141728;display:flex;'
            'align-items:center;justify-content:center;color:#8890c4;'
            f'font-size:0.75rem;position:relative;">—'
            f'<span style="position:absolute;top:6px;right:6px;'
            f'background:{badge_bg};color:{badge_fg};font-size:0.6rem;'
            f'font-weight:600;padding:2px 6px;border-radius:4px;">{badge_label}</span>'
            f'</div>'
        )

    safe_smi = _html_lib.escape(scaffold_smi, quote=True)
    display_smi = scaffold_smi[:37] + "…" if len(scaffold_smi) > 40 else scaffold_smi
    safe_display = _html_lib.escape(display_smi)
    uid = str(abs(hash(scaffold_smi)) % 99_999_999)

    avg_p_html = (
        f'<div style="color:{_TITLE};font-size:0.81rem;margin-top:4px;">'
        f'Avg P(test) = {mean_proba:.3f}</div>'
        if mean_proba is not None
        else f'<div style="color:{_GRAY};font-size:0.75rem;margin-top:4px;">Avg P — test only</div>'
    )

    return f"""
<div style="background:{_CARD_BG};border:1px solid {_BORDER};
            border-radius:10px;overflow:hidden;font-family:sans-serif;">
  {img_html}
  <div style="padding:10px;">
    <div style="background:#1c2040;border-radius:4px;height:8px;
                margin:4px 0 5px;overflow:hidden;">
      <div style="width:{pct}%;height:100%;background:{bar_color};
                  border-radius:4px;"></div>
    </div>
    <div style="color:{_TEXT};font-size:0.75rem;line-height:1.4;">
      {pct}% active &nbsp;({active_count}/{total_count} molecules)
    </div>
    {avg_p_html}
    <div id="cw_{uid}" data-smi="{safe_smi}"
         style="display:flex;align-items:center;gap:4px;margin-top:7px;
                font-family:'Space Grotesk',sans-serif;font-size:0.75rem;color:#8890c4;
                background:rgba(255,255,255,0.03);border:1px solid #2a2a2a;
                border-radius:6px;padding:3px 6px;box-sizing:border-box;">
      <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
                   flex:1;min-width:0;" title="{safe_smi}">{safe_display}</span>
      <button id="cb_{uid}" onclick="doCopy_{uid}()"
              style="background:none;border:none;cursor:pointer;font-size:0.9rem;
                     padding:0 1px;color:#aaa;flex-shrink:0;line-height:1;"
              title="Copy SMILES">&#128203;</button>
    </div>
  </div>
</div>
<script>
(function(){{
  function doCopy_{uid}(){{
    var s=document.getElementById('cw_{uid}').getAttribute('data-smi');
    var btn=document.getElementById('cb_{uid}');
    function flash(){{
      btn.innerHTML='&#10003;';btn.style.color='{_GREEN}';
      setTimeout(function(){{btn.innerHTML='&#128203;';btn.style.color='{_TEXT}';}},1500);
    }}
    if(navigator.clipboard&&navigator.clipboard.writeText){{
      navigator.clipboard.writeText(s).then(flash,function(){{_fb_{uid}(s,flash);}});
    }}else{{_fb_{uid}(s,flash);}}
  }}
  function _fb_{uid}(s,cb){{
    var ta=document.createElement('textarea');
    ta.value=s;ta.style.cssText='position:fixed;opacity:0;top:0;left:0;width:1px;height:1px;';
    document.body.appendChild(ta);ta.focus();ta.select();
    try{{document.execCommand('copy');cb();}}catch(e){{}}
    document.body.removeChild(ta);
  }}
  window['doCopy_{uid}']=doCopy_{uid};
}})();
</script>"""


def _render_scaffold_section(test_df: pd.DataFrame, smiles_col: str, label_col: str):
    # Pull training data from session state if available
    train_df = st.session_state.get("_bit_db_pending_df")
    train_meta = st.session_state.get("bit_database_meta", {})
    train_smiles_col = train_meta.get("smiles_col")
    train_label_col = train_meta.get("label_col")
    has_train = (
        train_df is not None
        and train_smiles_col
        and train_label_col
        and train_smiles_col in train_df.columns
        and train_label_col in train_df.columns
    )

    try:
        with st.spinner("Computing Murcko scaffolds…"):
            scaffold_df = _compute_scaffold_stats(
                test_df, smiles_col, label_col,
                train_df if has_train else None,
                train_smiles_col if has_train else None,
                train_label_col if has_train else None,
            )
    except Exception as exc:
        st.error(f"Scaffold computation failed: {exc}")
        return

    if scaffold_df.empty:
        if "_error" in scaffold_df.columns:
            st.error(f"Scaffold error: {scaffold_df['_error'].iloc[0]}")
        else:
            st.info("No scaffolds with ≥ 2 molecules found.")
        return

    n_total_unique = len(scaffold_df)
    n_filtered = len(scaffold_df[scaffold_df["total_count"] >= 2])
    top_rate = int(round(scaffold_df.iloc[0]["active_rate"] * 100)) if n_filtered else 0

    source_note = " (train + test)" if has_train else " (test only)"
    st.markdown(
        f"Found **{n_total_unique}** unique scaffolds{source_note} "
        f"(showing those with ≥ 2 molecules). "
        f"Top scaffold active rate: **{top_rate}%**."
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    fc1, fc2 = st.columns([2, 3])
    with fc1:
        min_rate_label = st.selectbox(
            "Active rate ≥",
            options=["0%", "30%", "50%", "70%"],
            index=0,
            key="scaffold_min_rate",
        )
    with fc2:
        source_opts = ["All"]
        if has_train:
            source_opts += ["Train only", "Test only", "Train + Test"]
        source_filter = st.segmented_control(
            "Source",
            source_opts,
            default="All",
            key="scaffold_source_filter",
            label_visibility="collapsed",
        ) or "All"

    min_rate = int(min_rate_label.rstrip("%")) / 100.0
    display_df = scaffold_df[scaffold_df["active_rate"] >= min_rate].copy()
    if source_filter == "Train only":
        display_df = display_df[display_df["source"] == "train"]
    elif source_filter == "Test only":
        display_df = display_df[display_df["source"] == "test"]
    elif source_filter == "Train + Test":
        display_df = display_df[display_df["source"] == "both"]
    display_df = display_df.reset_index(drop=True)

    if display_df.empty:
        st.info(f"No scaffolds match the selected filters.")
        return

    # Build 3-column card grid as one HTML component
    cards = [_scaffold_card_html(row) for _, row in display_df.iterrows()]
    n = len(cards)
    n_rows = math.ceil(n / 3)

    # Pad to a multiple of 3 so the grid looks clean
    while len(cards) % 3 != 0:
        cards.append("<div></div>")

    items_html = "".join(f"<div>{c}</div>" for c in cards)
    grid_html = f"""
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;
            padding:4px 0;">
  {items_html}
</div>
"""
    card_height = 300   # px per card row
    component_height = n_rows * card_height + 30
    components.html(grid_html, height=component_height, scrolling=False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render_evaluation_page():
    st.markdown(":material/assessment: **Evaluation — Test Set Performance**")

    # ── Guard rails ────────────────────────────────────────────────────────
    model = st.session_state.get("rf_model")
    if model is None:
        st.warning("Please load a trained model first.")
        return

    test_df = st.session_state.get("test_df")
    if test_df is None:
        st.info("Upload a test set in the sidebar to view evaluation results.")
        return

    test_meta = st.session_state.get("test_df_meta", {})
    smiles_col = test_meta.get("smiles_col", "")
    label_col = test_meta.get("label_col", "")

    # Validate required columns are present
    for col in (label_col, "_pred_proba", "_pred_label"):
        if col not in test_df.columns:
            st.error(
                f"Column '{col}' not found in test set. "
                "Please re-upload the test set from the sidebar."
            )
            return

    y_true = test_df[label_col].values.astype(int)
    y_pred = test_df["_pred_label"].values.astype(int)
    y_proba = test_df["_pred_proba"].values.astype(float)

    if len(test_df) < 10:
        st.warning(
            f"Test set has only **{len(test_df)}** molecules — "
            "metrics may be unreliable. At least 10 are recommended."
        )

    # ── Section 1: Metrics ─────────────────────────────────────────────────
    st.markdown("### Performance Metrics")
    try:
        _render_metrics_section(y_true, y_pred, y_proba)
    except Exception as exc:
        st.error(f"Metrics section error: {exc}")

    st.markdown("")

    try:
        _render_imbalance_section(y_true, y_proba)
    except Exception as exc:
        st.error(f"Class imbalance metrics section error: {exc}")

    st.divider()

    # ── Section 2: Distribution ────────────────────────────────────────────
    st.markdown("### Prediction Distribution")
    try:
        _render_distribution_section(y_true, y_proba)
    except Exception as exc:
        st.error(f"Distribution section error: {exc}")

    st.divider()

    # ── Section 3: Scaffolds ───────────────────────────────────────────────
    st.markdown("### Scaffold Analysis")
    if smiles_col not in test_df.columns:
        st.warning("SMILES column not found — cannot compute scaffolds.")
    else:
        try:
            _render_scaffold_section(test_df, smiles_col, label_col)
        except Exception as exc:
            st.error(f"Scaffold section error: {exc}")
