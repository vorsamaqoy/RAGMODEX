"""ECFP / MACCS Visualizer page — paginated molecule grid with fingerprint drill-down."""

import streamlit as st
import numpy as np
import base64
from io import BytesIO
from typing import Optional

import streamlit.components.v1 as components

from ui.components import (
    smiles_to_mol,
    render_maccs_grid,
    render_ecfp_grid,
    render_bit_detail,
)


@st.cache_data(show_spinner=False)
def _compute_train_probs(_model, _X_train):
    """Predict P(active) for all training molecules (cached)."""
    return _model.predict_proba(_X_train)[:, 1]


def _render_probability_histogram(train_probs, train_targets, test_probs=None, test_targets=None):
    """Histogram of P(active) for training (and optionally test) molecules, dark-themed."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y_arr = np.array(train_targets)
    active_mask = y_arr == 1
    inactive_mask = y_arr == 0

    fig, ax = plt.subplots(figsize=(10, 3))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafafa")

    bins = np.linspace(0, 1, 40)

    ax.hist(train_probs[inactive_mask], bins=bins, alpha=0.75,
            color="#b83245", label=f"Train Inactive (n={inactive_mask.sum()})",
            edgecolor="#e0e0e0", linewidth=0.5)
    ax.hist(train_probs[active_mask], bins=bins, alpha=0.75,
            color="#23775a", label=f"Train Active (n={active_mask.sum()})",
            edgecolor="#e0e0e0", linewidth=0.5)

    if test_probs is not None and test_targets is not None:
        y_test = np.array(test_targets)
        test_active = y_test == 1
        test_inactive = y_test == 0
        ax.hist(test_probs[test_inactive], bins=bins, alpha=0.5,
                color="#b83245", label=f"Test Inactive (n={test_inactive.sum()})",
                edgecolor="#b83245", linewidth=0.8, histtype="step", linestyle="--")
        ax.hist(test_probs[test_active], bins=bins, alpha=0.5,
                color="#23775a", label=f"Test Active (n={test_active.sum()})",
                edgecolor="#23775a", linewidth=0.8, histtype="step", linestyle="--")

    ax.axvline(0.5, color="#b86020", linestyle="--", linewidth=1.2,
               label="Decision boundary")

    ax.set_xlabel("P(active)", color="#65656f", fontsize=9, fontfamily="sans-serif")
    ax.set_ylabel("Count", color="#65656f", fontsize=9, fontfamily="sans-serif")
    ax.set_title("Prediction Distribution — Training & Test",
                 color="#1e1c24", fontsize=11, fontfamily="sans-serif", pad=10)

    ax.tick_params(axis="both", colors="#65656f", labelsize=8)
    ax.legend(fontsize=8, facecolor="#f4f4f4", edgecolor="#e0e0e0",
              labelcolor="#1e1c24", loc="upper center")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#e0e0e0")
    ax.spines["left"].set_color("#e0e0e0")
    ax.grid(axis="y", alpha=0.4, color="#e0e0e0")
    ax.set_xlim(0, 1)

    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="PNG", dpi=150, facecolor="#ffffff", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    st.image(buf, width="stretch")

    n_correct = ((train_probs > 0.5) == y_arr).sum()
    accuracy = n_correct / len(y_arr) * 100

    stats_parts = [
        f"<span>Train mols: <strong style='color:var(--color-text);'>{len(y_arr)}</strong></span>",
        f"<span>Active: <strong style='color:var(--color-success);'>{active_mask.sum()}</strong></span>",
        f"<span>Inactive: <strong style='color:var(--color-danger);'>{inactive_mask.sum()}</strong></span>",
        f"<span>Train accuracy: <strong style='color:var(--color-accent);'>{accuracy:.1f}%</strong></span>",
    ]
    if test_probs is not None and test_targets is not None:
        y_test = np.array(test_targets)
        test_active_n = (y_test == 1).sum()
        test_inactive_n = (y_test == 0).sum()
        test_acc = ((test_probs > 0.5) == y_test).sum() / len(y_test) * 100
        stats_parts += [
            f"<span>Test mols: <strong style='color:var(--color-text);'>{len(y_test)}</strong></span>",
            f"<span>Test active: <strong style='color:var(--color-success);'>{test_active_n}</strong></span>",
            f"<span>Test inactive: <strong style='color:var(--color-danger);'>{test_inactive_n}</strong></span>",
            f"<span>Test accuracy: <strong style='color:var(--color-accent);'>{test_acc:.1f}%</strong></span>",
        ]

    st.markdown(
        f"<div style='display:flex;gap:1.5rem;flex-wrap:wrap;justify-content:center;"
        f"font-family:var(--font-main);font-size:0.875rem;"
        f"color:var(--color-text-muted);margin-bottom:1rem;font-variant-numeric:tabular-nums;'>"
        + "".join(stats_parts)
        + "</div>",
        unsafe_allow_html=True,
    )


# ── Local cache (grid thumbnails only) ────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _mol_image_b64(smiles: str, size=(250, 200)) -> Optional[str]:
    """Render SMILES to base64 PNG (cached per SMILES string)."""
    from rdkit import Chem
    from rdkit.Chem import Draw
    mol = Chem.MolFromSmiles(str(smiles)) if smiles else None
    if mol is None:
        return None
    img = Draw.MolToImage(mol, size=size)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _get_training_data():
    """Return (smiles, targets, probs) for training set, or (None, None, None)."""
    smiles_train = st.session_state.get("smiles_train")
    y_train = st.session_state.get("y_train")
    if not smiles_train or y_train is None:
        return None, None, None

    smiles = np.array(smiles_train, dtype=str)
    targets = np.array(y_train, dtype=float)
    probs = None

    model = st.session_state.get("rf_model")
    X_train = st.session_state.get("X_train")
    if model is not None and X_train is not None:
        probs = _compute_train_probs(model, X_train)

    return smiles, targets, probs


def _get_test_data():
    """Return (smiles, targets, probs) for test set, or (None, None, None)."""
    test_df = st.session_state.get("test_df")
    meta = st.session_state.get("test_df_meta", {})
    smiles_col = meta.get("smiles_col")
    label_col = meta.get("label_col")
    if test_df is None or not smiles_col:
        return None, None, None
    try:
        smiles = test_df[smiles_col].astype(str).values
        targets = test_df[label_col].values.astype(float) if label_col and label_col in test_df.columns else np.full(len(smiles), np.nan)
        probs = test_df["_pred_proba"].values if "_pred_proba" in test_df.columns else None
        return smiles, targets, probs
    except Exception:
        return None, None, None


MOLS_PER_PAGE = 48  # divisible by 3


# ── Main entry point ──────────────────────────────────────────────────────────

def render_visualizer_page():
    """Render the ECFP / MACCS Visualizer page."""
    st.markdown(
        "<style>html { scroll-behavior: auto; }</style>"
        "<div id='viz-top'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(":material/biotech: **ECFP / MACCS Visualizer**")

    train_smiles, train_targets, train_probs = _get_training_data()
    if train_smiles is None:
        st.warning("Upload training data and build the bit database first (sidebar → Training Data).")
        return

    test_smiles, test_targets, test_probs = _get_test_data()
    has_test = test_smiles is not None

    # ── Prediction distribution histogram ─────────────────────────────────────
    if train_probs is not None:
        _render_probability_histogram(
            train_probs, train_targets,
            test_probs if has_test else None,
            test_targets if has_test else None,
        )
        st.divider()

    # ── Build unified molecule list ────────────────────────────────────────────
    # Each entry: (smiles, target, prob, source)  source = "train" | "test"
    all_smiles = list(train_smiles)
    all_targets = list(train_targets)
    all_probs = list(train_probs) if train_probs is not None else [None] * len(train_smiles)
    all_sources = ["train"] * len(train_smiles)

    if has_test:
        for i in range(len(test_smiles)):
            all_smiles.append(str(test_smiles[i]))
            try:
                t = float(test_targets[i])
                all_targets.append(-1 if np.isnan(t) else t)
            except (TypeError, ValueError):
                all_targets.append(-1)
            all_probs.append(float(test_probs[i]) if test_probs is not None else None)
            all_sources.append("test")

    all_smiles = np.array(all_smiles, dtype=str)
    all_targets = np.array(all_targets, dtype=float)
    all_probs_arr = np.array([p if p is not None else np.nan for p in all_probs], dtype=float)
    all_sources = np.array(all_sources)

    # ── Filters ───────────────────────────────────────────────────────────────
    filter_cols = st.columns([3, 2, 2, 3])

    with filter_cols[0]:
        search = st.text_input(":material/search: Filter SMILES", key="viz_search",
                               placeholder="Type to filter…", label_visibility="collapsed")

    with filter_cols[1]:
        class_filter = st.segmented_control(
            "Class", ["All", "Active", "Inactive"],
            default="All", key="viz_class", label_visibility="collapsed",
        )
        if class_filter is None:
            class_filter = "All"

    with filter_cols[2]:
        dataset_options = ["All", "Train"] + (["Test"] if has_test else [])
        dataset_filter = st.segmented_control(
            "Dataset", dataset_options,
            default="All", key="viz_dataset", label_visibility="collapsed",
        )
        if dataset_filter is None:
            dataset_filter = "All"

    with filter_cols[3]:
        sort_options = ["Default", "P(active) ↑", "P(active) ↓"]
        sort_order = st.selectbox("Sort", sort_options, key="viz_sort",
                                  label_visibility="collapsed")

    # Build mask
    mask = np.ones(len(all_smiles), dtype=bool)
    if search:
        mask &= np.array([search.lower() in s.lower() for s in all_smiles])
    if class_filter == "Active":
        mask &= (all_targets == 1)
    elif class_filter == "Inactive":
        mask &= (all_targets == 0)
    if dataset_filter == "Train":
        mask &= (all_sources == "train")
    elif dataset_filter == "Test":
        mask &= (all_sources == "test")

    filtered_idx = np.where(mask)[0]

    # Sort
    if sort_order == "P(active) ↑":
        sort_key = all_probs_arr[filtered_idx]
        order = np.argsort(np.where(np.isnan(sort_key), -1, sort_key))
        filtered_idx = filtered_idx[order]
    elif sort_order == "P(active) ↓":
        sort_key = all_probs_arr[filtered_idx]
        order = np.argsort(np.where(np.isnan(sort_key), -1, sort_key))[::-1]
        filtered_idx = filtered_idx[order]

    n_total = len(filtered_idx)
    n_pages = max(1, (n_total + MOLS_PER_PAGE - 1) // MOLS_PER_PAGE)

    col_info, col_page = st.columns([4, 2])
    with col_page:
        page = st.number_input("Page", min_value=1, max_value=n_pages,
                               value=1, key="viz_page", label_visibility="collapsed")

    page_start = (int(page) - 1) * MOLS_PER_PAGE + 1
    page_end = min(int(page) * MOLS_PER_PAGE, n_total)
    with col_info:
        st.caption(
            f"Showing {page_start}–{page_end} of {n_total} molecules · "
            f"Page {int(page)}/{n_pages}"
        )

    start = (int(page) - 1) * MOLS_PER_PAGE
    end = min(start + MOLS_PER_PAGE, n_total)
    page_idx = filtered_idx[start:end]

    _render_molecule_grid(page_idx, all_smiles, all_targets, all_probs_arr, all_sources)

    # ── Detail section ────────────────────────────────────────────────────────
    st.divider()
    _render_molecule_detail(all_smiles, all_targets, all_probs_arr, all_sources)


# ── Molecule grid ─────────────────────────────────────────────────────────────

def _render_molecule_grid(page_idx, smiles_list, targets, probs, sources):
    """Render the molecule grid using components.html so copy buttons work."""
    import html as _html_lib

    if len(page_idx) == 0:
        st.info("No molecules match the current filters.")
        return

    # Build CSS + card HTML
    css = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: transparent; font-family: 'Space Grotesk', sans-serif; }
.mol-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    padding: 4px;
}
.mol-card {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    overflow: hidden;
    position: relative;
}
.mol-card img {
    width: 100%;
    display: block;
    background: #f5f3ee;
}
.mol-card-body {
    padding: 5px 7px 6px;
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.mol-card-row {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-wrap: wrap;
}
.mol-idx { color: #a8a8b0; font-size: 10px; }
.badge-train {
    background: #f0f0f0; color: #65656f;
    border: 1px solid #cccccc;
    border-radius: 4px; font-size: 9px;
    padding: 1px 5px; font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-test {
    background: #fef5e7; color: #b86020;
    border: 1px solid #f0d8a0;
    border-radius: 4px; font-size: 9px;
    padding: 1px 5px; font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-active {
    background: #edf7f3; color: #23775a;
    border: 1px solid #b8dece;
    border-radius: 4px; font-size: 9px;
    padding: 1px 5px; font-weight: 700;
}
.badge-inactive {
    background: #faeaed; color: #b83245;
    border: 1px solid #e8b8c2;
    border-radius: 4px; font-size: 9px;
    padding: 1px 5px; font-weight: 700;
}
.badge-unknown {
    background: #f4f4f4; color: #65656f;
    border: 1px solid #e0e0e0;
    border-radius: 4px; font-size: 9px;
    padding: 1px 5px;
}
.mol-prob { color: #65656f; font-size: 10px; }
.mol-prob strong { color: #1e1c24; }
.mol-card-border-active  { border-bottom: 3px solid #23775a; }
.mol-card-border-inactive { border-bottom: 3px solid #b83245; }
.copy-row {
    display: flex;
    align-items: center;
    gap: 4px;
    background: #f4f4f4;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 2px 5px;
    margin-top: 2px;
}
.copy-smi {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
    color: #1e1c24;
    font-size: 9px;
}
.copy-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 12px;
    padding: 0;
    color: #65656f;
    flex-shrink: 0;
    line-height: 1;
}
.copy-btn:hover { color: #b86020; }
</style>
"""

    cards_html = ""
    for idx in page_idx:
        smi = str(smiles_list[idx])
        target = float(targets[idx])
        prob = float(probs[idx]) if not np.isnan(probs[idx]) else None
        source = str(sources[idx])

        b64 = _mol_image_b64(smi)
        if b64 is None:
            continue

        safe_smi = _html_lib.escape(smi, quote=True)
        display_smi = _html_lib.escape(smi[:38] + "…" if len(smi) > 38 else smi)
        uid = abs(hash(smi + str(idx))) % 9_999_999

        # Source badge
        if source == "test":
            source_badge = '<span class="badge-test">TEST</span>'
        else:
            source_badge = '<span class="badge-train">TRAIN</span>'

        # Target badge
        if target == 1:
            target_badge = '<span class="badge-active">Active</span>'
            border_cls = "mol-card-border-active"
        elif target == 0:
            target_badge = '<span class="badge-inactive">Inactive</span>'
            border_cls = "mol-card-border-inactive"
        else:
            target_badge = '<span class="badge-unknown">—</span>'
            border_cls = ""

        # Probability
        if prob is not None:
            prob_html = f'<span class="mol-prob">P(act): <strong>{prob:.3f}</strong></span>'
        else:
            prob_html = ""

        cards_html += f"""
<div class="mol-card {border_cls}" data-smi="{safe_smi}">
  <img src="data:image/png;base64,{b64}" alt="Molecule {idx}"/>
  <div class="mol-card-body">
    <div class="mol-card-row">
      <span class="mol-idx">#{idx}</span>
      {source_badge}
      {target_badge}
      {prob_html}
    </div>
    <div class="copy-row" id="cr_{uid}" title="{safe_smi}">
      <span class="copy-smi">{display_smi}</span>
      <button class="copy-btn" onclick="doCopy_{uid}()" title="Copy SMILES">&#128203;</button>
    </div>
  </div>
</div>
<script>
(function(){{
  function doCopy_{uid}(){{
    var s=document.querySelector('#cr_{uid}').closest('.mol-card').getAttribute('data-smi');
    var btn=document.querySelector('#cr_{uid} .copy-btn');
    function flash(){{btn.innerHTML='&#10003;';btn.style.color='#50c896';setTimeout(function(){{btn.innerHTML='&#128203;';btn.style.color='#8890c4';}},1500);}}
    if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(s).then(flash,function(){{fb(s,btn,flash);}});}}else{{fb(s,btn,flash);}}
  }}
  function fb(s,btn,cb){{var ta=document.createElement('textarea');ta.value=s;ta.style.cssText='position:fixed;opacity:0;top:0;left:0;width:1px;height:1px;';document.body.appendChild(ta);ta.focus();ta.select();try{{document.execCommand('copy');cb();}}catch(e){{}}document.body.removeChild(ta);}}
  window['doCopy_{uid}']=doCopy_{uid};
}})();
</script>
"""

    n_rows = max(1, (len(page_idx) + 2) // 3)
    # Each row: image ~160px + info ~55px + gap = ~215px; plus top padding
    grid_height = n_rows * 230 + 40

    full_html = css + '<div class="mol-grid">' + cards_html + '</div>'
    components.html(full_html, height=grid_height, scrolling=False)

    default_val = int(page_idx[0]) if len(page_idx) > 0 else 0
    selected = st.number_input(
        "Select molecule index to inspect:",
        min_value=0,
        max_value=len(smiles_list) - 1,
        value=default_val,
        key="viz_selected_mol",
    )
    st.session_state["selected_mol_idx"] = int(selected)


# ── Molecule detail ───────────────────────────────────────────────────────────

def _render_molecule_detail(smiles_list, targets, probs, sources):
    idx = st.session_state.get("selected_mol_idx")
    if idx is None:
        return
    idx = int(idx)
    if idx >= len(smiles_list):
        return

    smiles = str(smiles_list[idx])
    target = float(targets[idx])
    source = str(sources[idx])

    from rdkit import Chem
    from rdkit.Chem import AllChem, Draw, DataStructs
    from ui.clipboard import smiles_clipboard_widget

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        st.error(f"Invalid SMILES at index {idx}: {smiles}")
        return

    # ── Header: structure image + metadata ───────────────────────────────────
    col_img, col_info = st.columns([1, 2])

    with col_img:
        img = Draw.MolToImage(mol, size=(400, 350))
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        st.image(buf, width="stretch")

    with col_info:
        if target == 1:
            cls_color = "var(--color-success)"
            cls_label = "Active"
        elif target == 0:
            cls_color = "var(--color-danger)"
            cls_label = "Inactive"
        else:
            cls_color = "var(--color-text-muted)"
            cls_label = "Unknown"

        src_badge = "🔵 Train" if source == "train" else "🟡 Test"

        st.markdown(
            f"<div style='font-family:var(--font-main);'>"
            f"<div style='font-size:0.75rem;color:var(--color-text-dark);font-weight:500;"
            f"letter-spacing:0.04em;text-transform:uppercase;'>Molecule #{idx} · {src_badge}</div>"
            f"<div style='font-size:0.75rem;color:var(--color-text-muted);word-break:break-all;"
            f"margin:0.25rem 0;line-height:1.4;'>{smiles}</div>"
            f"<div style='color:{cls_color};font-weight:600;font-size:1.125rem;"
            f"line-height:1.2;margin-bottom:0.5rem;'>{cls_label}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        smiles_clipboard_widget(smiles, uid=f"viz_detail_{idx}")

        meta = st.session_state.get("bit_database_meta", {})
        radius = int(meta.get("radius", 3))
        n_bits = int(meta.get("n_bits", 2048))

        bi = {}
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits, bitInfo=bi)
        maccs = AllChem.GetMACCSKeysFingerprint(mol)

        shap_vals = None
        model = st.session_state.get("rf_model")
        explainer = st.session_state.get("shap_explainer")

        if model is not None:
            arr = np.zeros(n_bits, dtype=np.int32)
            DataStructs.ConvertToNumpyArray(fp, arr)
            prob = model.predict_proba(arr.reshape(1, -1))[0]
            p_active = prob[1]
            pred_label = "Active" if p_active >= 0.5 else "Inactive"
            st.markdown(f"**Predicted:** {pred_label} · P(active) = `{p_active:.4f}`")

            if explainer is not None:
                try:
                    sv = explainer.shap_values(arr.reshape(1, -1))
                    if isinstance(sv, list):
                        shap_vals = sv[1][0]
                    elif hasattr(sv, "ndim") and sv.ndim == 3:
                        shap_vals = sv[0, :, 1]
                    else:
                        shap_vals = sv[0]
                except Exception:
                    shap_vals = None

        ecfp_on = len(bi)
        maccs_on = sum(1 for i in range(167) if maccs.GetBit(i))
        st.markdown(f"ECFP{2 * radius} bits ON: **{ecfp_on}** / {n_bits}")
        st.markdown(f"MACCS keys ON: **{maccs_on}** / 166")

    bit_db = st.session_state.get("bit_database") or {}

    render_maccs_grid(maccs, key_prefix="viz_", smiles=smiles)
    render_ecfp_grid(bi, bit_db, shap_vals, key_prefix="viz_")
    render_bit_detail(bit_db, shap_vals, key_prefix="viz_")
