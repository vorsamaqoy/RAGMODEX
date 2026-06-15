"""design_panel.py — "🧪 Design Suggestions" panel (Guided-only mode).

Changes vs previous version:
- Standard mode removed; only Guided (iterative beam-search) is available.
- Cards rendered via CSS grid → always uniform 3-column layout regardless of count.
- Base molecule preview shown immediately on SMILES entry.
- Progress bar updates per iteration.
- Light lab theme: all hardcoded dark colors replaced with CSS variables or
  light-theme equivalents. Plotly and Matplotlib charts use light themes.
- MMR weight selector replaced: clickable ternary plot (Plotly) removed in
  favour of a Streamlit custom component (SVG + vanilla JS) that renders an
  interactive ternary triangle, snaps to a 0.05 grid, and fires exactly one
  Python rerun per mouseup/touchend — no Plotly selection events, no
  curveNumber guards, no st.rerun() loop. Preset buttons added below.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional

import streamlit as st

from core.design_engine import (
    DesignCandidate,
    run_guided_pipeline,
    find_similar_molecules,
    compute_ad_score,
    _mol_to_fp,
)
from ui.molecular_evolution_path import render_evolution_path
from ui.clipboard import smiles_clipboard_widget
from components.ternary_weights import ternary_weights

# Card image height (px) — keep fixed so all cards have identical height
_IMG_H = 130

# Session-state keys and defaults for MMR beam-selection weights
MMR_W_PROB_KEY = "mmr_w_prob"
MMR_W_DIV_KEY  = "mmr_w_div"
MMR_W_AD_KEY   = "mmr_w_ad"

DEFAULT_W_PROB = 0.50
DEFAULT_W_DIV  = 0.25
DEFAULT_W_AD   = 0.25


# ---------------------------------------------------------------------------
# Training-set canonical SMILES cache
# ---------------------------------------------------------------------------

def _get_canonical_train_set() -> set[str]:
    from rdkit import Chem
    key = "_design_canonical_train"
    smiles_train = st.session_state.get("smiles_train") or []
    cached = st.session_state.get(key)
    if cached is None or cached.get("_len") != len(smiles_train):
        canon: set[str] = set()
        for smi in smiles_train:
            m = Chem.MolFromSmiles(smi)
            if m:
                canon.add(Chem.MolToSmiles(m))
        st.session_state[key] = {"_len": len(smiles_train), "set": canon}
    return st.session_state[key]["set"]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_design_panel(smiles_override: Optional[str] = None) -> None:
    st.markdown("""
<style>
[data-testid="stMain"] [data-testid="column"] {
    min-width: 0 !important;
    overflow: hidden !important;
}
</style>""", unsafe_allow_html=True)

    title_col, help_col = st.columns([10, 1])
    with title_col:
        st.markdown(":material/science: **Design Suggestions**")
        st.caption(
            "Iterative beam-search that maximises P(active) while staying within "
            "the model's applicability domain. Each round seeds from the best "
            "structurally diverse molecules found so far."
        )
    with help_col:
        with st.popover(":material/help_outline:", use_container_width=True):
            st.markdown(_HELP_MD)

    model = st.session_state.get("rf_model")
    if model is None:
        st.info("Upload a trained model in the sidebar (**Model** section) to enable design.")
        return

    meta         = st.session_state.get("bit_database_meta") or {}
    radius       = int(meta.get("radius", st.session_state.get("fp_radius", 3)))
    n_bits       = int(meta.get("n_bits",   st.session_state.get("fp_nbits", 2048)))
    has_training = st.session_state.get("X_train") is not None

    if "design_smiles_input_pending" in st.session_state:
        st.session_state["design_smiles_input"] = st.session_state.pop("design_smiles_input_pending")

    input_smiles = st.text_input(
        "Input SMILES",
        value=smiles_override or st.session_state.get("current_smiles", ""),
        placeholder="O=C(Nc1cnn(Cc2ccccc2)c1)c1ccnc2ccccc12",
        key="design_smiles_input",
        label_visibility="collapsed",
    )

    if input_smiles:
        _render_base_preview(input_smiles, model, radius, n_bits, has_training)

    settings = _render_settings_box(has_training)

    run_btn = st.button(
        ":material/play_arrow: Run Guided Optimization",
        key="design_run_btn",
        width="stretch",
        type="primary",
    )

    if run_btn:
        if not input_smiles:
            st.error("Enter a SMILES string first.")
            return

        progress_bar  = st.progress(0.0, text="Starting…")
        status_holder = st.empty()

        def _on_progress(frac: float, msg: str) -> None:
            progress_bar.progress(min(frac, 0.99), text=msg)
            status_holder.caption(msg)

        result = run_guided_pipeline(
            smiles=input_smiles,
            model=model,
            radius=radius,
            n_bits=n_bits,
            n_variants_per_iter=settings["n_per_iter"],
            n_iterations=settings["n_iterations"],
            beam_size=settings["beam_size"],
            dataset_fps=st.session_state.get("X_train"),
            train_smiles=st.session_state.get("smiles_train"),
            top_k=settings["top_k"],
            patience=settings["patience"],
            shap_explainer=st.session_state.get("shap_explainer"),
            bit_db=st.session_state.get("bit_database") or {},
            w_prob=settings["w_prob"],
            w_div=settings["w_div"],
            w_ad=settings["w_ad"],
            use_druglikeness=settings["use_druglikeness"],
            preserve_core=settings["preserve_core"],
            progress_callback=_on_progress,
        )

        progress_bar.progress(1.0, text="Done.")
        progress_bar.empty()
        status_holder.empty()

        if "error" in result:
            st.error(result["error"])
            return

        if result.get("all_in_train_warning"):
            st.warning(
                "⚠️ All candidates at this step are present in the training set. "
                "Showing best available — consider increasing beam width."
            )

        st.session_state["_design_cache"] = {
            "smiles": input_smiles,
            "result": result,
            "top_k":  settings["top_k"],
        }
        _display_results(result, settings["top_k"], radius, n_bits)
        return

    cached = st.session_state.get("_design_cache")
    if cached and cached.get("smiles") == input_smiles:
        _display_results(cached["result"], cached.get("top_k", settings["top_k"]), radius, n_bits)
    elif not input_smiles:
        st.markdown(
            "<div style='color:var(--color-text-dim);font-size:0.875rem;"
            "margin-top:0.5rem;line-height:1.4;'>"
            "Enter a SMILES and press <b>Run</b> to start the guided optimisation."
            "</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Base molecule preview
# ---------------------------------------------------------------------------

def _render_base_preview(smiles, model, radius, n_bits, has_training) -> None:
    from rdkit import Chem
    from rdkit.Chem import Draw

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        st.error("Invalid SMILES — cannot parse molecule.")
        return

    fp = _mol_to_fp(mol, radius, n_bits)
    if fp is None:
        return
    try:
        prob = float(model.predict_proba(fp.reshape(1, -1))[0, 1])
    except Exception:
        return

    dataset_fps = st.session_state.get("X_train") if has_training else None
    ad   = compute_ad_score(fp, dataset_fps) if dataset_fps is not None else None
    canon = Chem.MolToSmiles(mol)
    in_train = has_training and (canon in _get_canonical_train_set())

    img = Draw.MolToImage(mol, size=(260, 160))
    buf = BytesIO(); img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    p_col = "var(--color-success)" if prob >= 0.5 else "var(--color-danger)"
    if ad is not None:
        ad_col = ("var(--color-success)" if ad >= 0.4
                  else ("var(--color-warning)" if ad >= 0.2 else "var(--color-danger)"))
        ad_html = (f'<div style="font-size:0.875rem;color:{ad_col};margin-top:0.1rem;">'
                   f'DA = {ad:.3f}'
                   f'<span style="color:var(--color-text-dim);font-size:0.8em;margin-left:0.4em;">'
                   f'(thr 0.40)</span></div>')
    else:
        ad_html = ('<div style="font-size:0.875rem;color:var(--color-text-dim);margin-top:0.1rem;">'
                   'DA — (no training set)</div>')

    match_html = (
        '<div style="font-size:0.75rem;color:var(--color-warning);margin-top:0.08rem;">'
        '🎯 In training set</div>'
    ) if in_train else ""

    st.markdown(
        '<div style="display:flex;gap:0.9rem;align-items:center;'
        'background:var(--color-card);border:1px solid var(--color-border);border-radius:8px;'
        'padding:0.55rem 0.8rem;margin-bottom:0.55rem;">'
        f'<img src="data:image/png;base64,{b64}" '
        'alt="Starting molecule" '
        'style="height:90px;width:auto;background:#f5f3ee;border-radius:4px;'
        'object-fit:contain;flex-shrink:0;"/>'
        '<div style="flex:1;">'
        '<div style="font-size:0.6875rem;color:var(--color-text-dim);font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.08em;line-height:1.2;">Starting molecule</div>'
        f'<div style="font-size:1.125rem;font-weight:700;color:{p_col};margin-top:0.1rem;'
        f'font-variant-numeric:tabular-nums;letter-spacing:-0.01em;">'
        f'P(active) = {prob:.3f}</div>'
        f'{ad_html}{match_html}'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Settings box
# ---------------------------------------------------------------------------

_HELP_MD = """
**Iterations**
Number of optimisation rounds. Each round uses the best diverse molecules from the previous round as new starting points.
↑ deeper search, more compute · ↓ faster but shallower.

**Variants / iteration**
How many new structural modifications to generate per round from the current beam.
↑ broader exploration of chemical space.

**Beam size**
How many molecules are carried forward as seeds to the next round.
Uses **Maximum Marginal Relevance** — picks seeds that are both active *and* structurally different from each other, preventing the search from stalling at a local optimum.
↑ wider exploration · ↓ faster convergence around one optimum.

**Top results shown**
Number of candidate cards displayed in the results grid.

**Early stop (patience)**
Stop the optimisation if P(active) does not improve for this many consecutive iterations.
↑ higher = more thorough exploration but longer runtime; set to 6 to always run all iterations.

**Drug-likeness filter**
Excludes generated molecules that fall outside Lipinski-extended bounds
(MW 150–650, logP −2–6, HBA ≤ 12, HBD ≤ 7, RotB ≤ 12). A relaxed fallback
(MW ≤ 800, logP ≤ 7) kicks in if the strict filter removes all candidates.
Disable to allow unconstrained exploration.

**MMR score weights**
Three sliders control the Activity / Diversity / AD trade-off in the MMR
beam-selection score. The values are automatically renormalized so they always
sum to 1.0 — moving one slider redistributes the remainder proportionally
between the other two.
Use the preset buttons for common configurations, or set fine-grained values
with the sliders. The ternary diagram on the right shows the current position
as a visual reference (read-only).
↑ Activity → greedier selection of high-P(active) molecules;
↑ Diversity → wider structural exploration;
↑ AD → stays closer to training-set chemical space.
"""

def _render_settings_box(has_training: bool) -> dict:
    qc1, qc2 = st.columns([2, 2])
    with qc1:
        n_iterations = st.slider(
            "Iterations", 2, 10, 5, key="design_n_iter",
            help="Optimisation rounds. More = deeper search, longer runtime.",
        )
    with qc2:
        top_k = st.slider(
            "Show top", 3, 18, 9, step=3, key="design_top_k",
            help="Number of candidate results to display.",
        )

    show_adv = st.toggle(
        ":material/tune: Advanced settings",
        value=False,
        key="design_show_advanced",
    )

    if show_adv:
        with st.container(border=True):
            st.markdown("**Beam search**")
            bc1, bc2 = st.columns(2)
            with bc1:
                st.slider("Beam size", 1, 6, 3, key="design_beam_size",
                          help="Molecules carried forward each round (MMR diversity selection).")
            with bc2:
                st.slider("Variants / iteration", 50, 300, 100, step=50,
                          key="design_n_per_iter",
                          help="Structural mutations generated per round.")
            bc3, bc4 = st.columns(2)
            with bc3:
                st.slider("Early stop patience", 1, 6, 3, key="design_patience",
                          help="Stop after N consecutive iterations with no P(active) improvement.")
            with bc4:
                st.number_input(
                    "Random seed",
                    min_value=0, max_value=99999, value=None,
                    placeholder="Random (leave empty)",
                    step=1, key="design_random_seed",
                    help=(
                        "Fix seed for reproducible results. "
                        "Seeds Python random + NumPy — RDKit's C++ RNG is NOT seeded, "
                        "so results may vary slightly across RDKit versions."
                    ),
                )

        with st.container(border=True):
            st.markdown(
                "**MMR score weights** "
                "<span style='color:var(--color-text-muted);font-size:0.8em;'>"
                "— Activity / Diversity / AD trade-off for beam-member selection."
                "</span>",
                unsafe_allow_html=True,
            )
            if not has_training:
                st.caption(":material/info: No training set — AD weight is fixed at 0.")
            w_p, w_d, w_ad = render_mmr_weights(has_training)

        with st.container(border=True):
            st.markdown("**Filters**")
            with st.container(horizontal=True):
                st.toggle(
                    "Drug-likeness filter", value=True, key="design_druglikeness",
                    help="Exclude molecules outside Lipinski-extended bounds.",
                )
                st.toggle(
                    "Preserve pharmacophore", value=True, key="design_preserve_core",
                    help=(
                        "Restrict mutations to peripheral atoms only "
                        "(SHAP bits or Murcko scaffold). "
                        "Disable for unconstrained exploration."
                    ),
                )

    beam_size  = int(st.session_state.get("design_beam_size", 3))
    n_per_iter = int(st.session_state.get("design_n_per_iter", 100))
    patience   = int(st.session_state.get("design_patience", 3))
    use_druglikeness = bool(st.session_state.get("design_druglikeness", True))
    preserve_core    = bool(st.session_state.get("design_preserve_core", True))

    # weights already read and validated by render_mmr_weights above
    if not show_adv:
        # Advanced block was hidden; sliders were never rendered — read from state
        w_p  = float(st.session_state.get(MMR_W_PROB_KEY, DEFAULT_W_PROB))
        w_d  = float(st.session_state.get(MMR_W_DIV_KEY,  DEFAULT_W_DIV))
        w_ad = float(st.session_state.get(MMR_W_AD_KEY,   DEFAULT_W_AD if has_training else 0.0))

    return {
        "n_iterations":     n_iterations,
        "n_per_iter":       n_per_iter,
        "beam_size":        beam_size,
        "top_k":            top_k,
        "patience":         patience,
        "use_druglikeness": use_druglikeness,
        "preserve_core":    preserve_core,
        "w_prob":           w_p,
        "w_div":            w_d,
        "w_ad":             w_ad,
    }


# ---------------------------------------------------------------------------
# MMR weight UI — interactive SVG custom component + preset buttons
# ---------------------------------------------------------------------------

def render_mmr_weights(has_training: bool) -> tuple[float, float, float]:
    """Render the MMR weight selector and return (w_prob, w_div, w_ad).

    Uses a bidirectional Streamlit custom component (SVG ternary triangle).
    Clicking or dragging the marker snaps to the 0.05 grid and triggers
    exactly one Python rerun on mouseup. No Plotly events, no rerun guards.
    Session-state keys: mmr_w_prob, mmr_w_div, mmr_w_ad.
    """
    # Initialize with defaults on first call
    for key, default in (
        (MMR_W_PROB_KEY, DEFAULT_W_PROB),
        (MMR_W_DIV_KEY,  DEFAULT_W_DIV),
        (MMR_W_AD_KEY,   DEFAULT_W_AD if has_training else 0.0),
    ):
        if key not in st.session_state:
            st.session_state[key] = default

    # Lock AD weight to zero when no training set is loaded
    if not has_training:
        st.session_state[MMR_W_AD_KEY] = 0.0
        s = float(st.session_state[MMR_W_PROB_KEY]) + float(st.session_state[MMR_W_DIV_KEY])
        if s > 1e-9:
            st.session_state[MMR_W_PROB_KEY] = float(st.session_state[MMR_W_PROB_KEY]) / s
            st.session_state[MMR_W_DIV_KEY]  = float(st.session_state[MMR_W_DIV_KEY])  / s
        else:
            st.session_state[MMR_W_PROB_KEY] = 0.5
            st.session_state[MMR_W_DIV_KEY]  = 0.5

    wp = float(st.session_state[MMR_W_PROB_KEY])
    wd = float(st.session_state[MMR_W_DIV_KEY])
    wa = float(st.session_state[MMR_W_AD_KEY])

    # Render the interactive component; fires a rerun only on mouseup/touchend
    wp_new, wd_new, wa_new = ternary_weights(
        w_prob=wp, w_div=wd, w_ad=wa,
        locked_c=not has_training,
        key="mmr_ternary",
    )

    # Persist returned weights when they differ from the current values
    if (wp_new, wd_new, wa_new) != (wp, wd, wa):
        st.session_state[MMR_W_PROB_KEY] = wp_new
        st.session_state[MMR_W_DIV_KEY]  = wd_new
        st.session_state[MMR_W_AD_KEY]   = wa_new
        wp, wd, wa = wp_new, wd_new, wa_new

    # One-click presets
    _PRESETS = [
        ("Activity-focused",  0.80, 0.10, 0.10, "mmr_preset_activity"),
        ("Balanced",          0.50, 0.25, 0.25, "mmr_preset_balanced"),
        ("Diversity-focused", 0.10, 0.80, 0.10, "mmr_preset_diversity"),
    ]
    pc1, pc2, pc3 = st.columns(3)
    for col, (label, p_wp, p_wd, p_wa, btn_key) in zip([pc1, pc2, pc3], _PRESETS):
        with col:
            if st.button(label, key=btn_key, use_container_width=True):
                if not has_training:
                    p_wa = 0.0
                    s = p_wp + p_wd
                    p_wp /= s; p_wd /= s
                st.session_state[MMR_W_PROB_KEY] = p_wp
                st.session_state[MMR_W_DIV_KEY]  = p_wd
                st.session_state[MMR_W_AD_KEY]   = p_wa
                st.rerun()

    st.caption(f"Sum: {wp + wd + wa:.3f}  (constrained to 1.000)")
    return wp, wd, wa


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

def _display_results(result: dict, top_k: int, radius: int, n_bits: int) -> None:
    base_prob  = result["base_prob"]
    all_cands  = result.get("candidates", [])
    n_gen      = result.get("n_generated", 0)
    improvers  = result.get("top_improvers", [])
    n_better   = sum(1 for c in all_cands if c.delta > 0)
    best_delta = improvers[0].delta if improvers else 0.0

    p_col = "var(--color-success)" if base_prob >= 0.5 else "var(--color-danger)"
    d_col = "var(--color-success)" if best_delta > 0 else "var(--color-danger)"
    st.markdown(
        f"<div style='font-size:0.875rem;color:var(--color-text-muted);"
        f"font-variant-numeric:tabular-nums;line-height:1.4;"
        f"padding:0.35rem 0.1rem 0.6rem;border-bottom:1px solid var(--color-border);'>"
        f"Base P(active) <b style='color:{p_col};'>{base_prob:.3f}</b>"
        f"&nbsp;&nbsp;→&nbsp;&nbsp;"
        f"Best Δ <b style='color:{d_col};'>{best_delta:+.3f}</b>"
        f"&nbsp;&nbsp;·&nbsp;&nbsp;{n_gen:,} generated"
        f"&nbsp;&nbsp;·&nbsp;&nbsp;{n_better:,} improved"
        f"</div>",
        unsafe_allow_html=True,
    )

    history = result.get("history")
    if history and len(history) >= 2:
        _render_optimization_plot(
            history,
            st.session_state.get("X_train") is not None,
        )

    timeline_path = result.get("timeline_path") or history
    if timeline_path:
        with st.expander("🧬 Molecular Evolution Path", expanded=False):
            render_evolution_path(
                timeline_path,
                has_train_filter=bool(st.session_state.get("smiles_train")),
            )
            top_prob = result.get("top_candidate_prob")
            top_iter = result.get("top_candidate_iteration")
            if top_prob is not None and top_iter is not None:
                st.caption(
                    f"Showing path to best candidate "
                    f"(P = {top_prob:.3f}) found at iteration {top_iter}."
                )

    tab_labels = ["⬆ Top Improvements", "📊 Top by Probability"]
    if st.session_state.get("X_train") is not None:
        tab_labels.append("🔍 Similar in Dataset")
    tabs = st.tabs(tab_labels)

    canonical_train = _get_canonical_train_set()

    with tabs[0]:
        if improvers:
            _render_card_grid(improvers[:top_k], base_prob, "imp", canonical_train)
        else:
            st.info("No variants with higher P(active). Increase iterations or variants/iter.")

    with tabs[1]:
        top_total = result.get("top_total", [])
        if top_total:
            _render_card_grid(top_total[:top_k], base_prob, "tot", canonical_train)
        else:
            st.info("No variants generated.")

    if len(tab_labels) == 3:
        with tabs[2]:
            _render_dataset_similar(result["base_smiles"], radius, n_bits)

    _render_strategy_summary(all_cands)


# ---------------------------------------------------------------------------
# Optimization progress plot — LIGHT THEME
# ---------------------------------------------------------------------------

def _render_optimization_plot(history, has_training) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("Install plotly to view the optimisation plot.")
        return

    n_gen     = [h["n_generated"] for h in history]
    best_prob = [h["best_prob"]   for h in history]
    ad_scores = [h["ad_score"]    for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=n_gen, y=best_prob, name="Best P(active)",
        mode="lines+markers",
        line=dict(color="#23775a", width=2.5), marker=dict(size=6),
        yaxis="y1",
    ))

    if has_training:
        fig.add_trace(go.Scatter(
            x=n_gen, y=ad_scores, name="AD score",
            mode="lines+markers",
            line=dict(color="#b87830", width=2, dash="dot"), marker=dict(size=5),
            yaxis="y2",
        ))

    layout: dict = dict(
        title=dict(text="Guided optimisation progress", font=dict(size=13, color="#1e1c24")),
        xaxis=dict(title="Molecules generated", color="#65656f", gridcolor="#e8e8e8"),
        yaxis=dict(title="P(active)", range=[0, 1], tickformat=".2f",
                   color="#23775a", gridcolor="#e8e8e8"),
        template="plotly_white",
        paper_bgcolor="#fafafa",
        plot_bgcolor="#f4f4f4",
        legend=dict(x=0.01, y=0.99, font=dict(size=10), bgcolor="rgba(255,255,255,0.8)"),
        margin=dict(l=55, r=55, t=40, b=40), height=255,
    )
    if has_training:
        layout["yaxis2"] = dict(
            title="AD score", range=[0, 1], tickformat=".2f",
            overlaying="y", side="right", color="#b87830", showgrid=False,
        )
    fig.update_layout(**layout)
    st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------------
# Comparison workspace — featured top result + ranked compact list
# ---------------------------------------------------------------------------

def _render_card_grid(
    candidates: list[DesignCandidate],
    base_prob: float,
    tab_id: str,
    canonical_train: set[str],
) -> None:
    """Featured top candidate + compact ranked rows for the rest."""
    if not candidates:
        return
    _render_featured_candidate(candidates[0], base_prob, tab_id, canonical_train)
    if len(candidates) > 1:
        st.markdown(
            "<div class='section-header' style='margin-top:1rem;'>"
            "All candidates — ranked by P(active)</div>",
            unsafe_allow_html=True,
        )
        for cand in candidates[1:]:
            _render_compact_row(cand, base_prob, tab_id, canonical_train)


def _delta_style(delta: float) -> tuple[str, str, str]:
    """Return (bg_tint, border_color, delta_color) for a given delta."""
    if delta > 0.10:
        return "rgba(35,119,90,0.06)", "rgba(35,119,90,0.25)", "var(--color-success)"
    if delta > 0.01:
        return "rgba(184,120,48,0.06)", "rgba(184,120,48,0.25)", "var(--color-accent)"
    if delta >= -0.01:
        return "transparent", "var(--color-border)", "var(--color-text-dim)"
    return "rgba(184,50,69,0.06)", "rgba(184,50,69,0.25)", "var(--color-danger)"


def _delta_label(delta: float) -> str:
    if delta > 0.10:   return "Strong improvement"
    if delta > 0.01:   return "Improved"
    if delta >= -0.01: return "Neutral"
    return "Worse"


def _origin_badge_html(source: str, size: str = "0.68rem") -> str:
    color, label = _ORIGIN_BADGE.get(source, ("var(--color-text-dim)", source or "—"))
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
        f'border-radius:3px;font-size:{size};font-weight:600;padding:1px 5px;">{label}</span>'
    )


def _ad_html_inline(cand: DesignCandidate, size: str = "0.75rem") -> str:
    if not (hasattr(cand, "ad_score") and cand.ad_score < 0.999):
        return ""
    ad_c = ("var(--color-success)" if cand.ad_score >= 0.4
            else ("var(--color-warning)" if cand.ad_score >= 0.2 else "var(--color-danger)"))
    return (f'<span style="color:{ad_c};font-size:{size};margin-left:0.5rem;">'
            f'DA={cand.ad_score:.2f}'
            f'<span style="color:var(--color-text-dim);font-size:0.85em;margin-left:0.25em;">'
            f'(thr 0.40)</span></span>')


@st.cache_data(show_spinner=False)
def _mol_png_b64(smiles: str, w: int, h: int) -> str | None:
    """Render SMILES to base64 PNG. Cached by SMILES + dimensions."""
    from rdkit import Chem
    from rdkit.Chem import Draw
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    img = Draw.MolToImage(mol, size=(w, h))
    buf = BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _build_card_html(
    cand: DesignCandidate, base_prob: float, canonical_train: set[str],
) -> str:
    """Return self-contained HTML for a vertical molecule card (used by virtual screening grid)."""
    b64 = _mol_png_b64(cand.smiles, _IMG_H * 2, _IMG_H)
    if b64 is None:
        return ""

    bg_tint, border_col, delta_col = _delta_style(cand.delta)
    p_col = "var(--color-success)" if cand.probability >= 0.5 else "var(--color-danger)"
    train_html = (
        '<div style="font-size:0.6875rem;color:var(--color-warning);margin-top:0.15rem;">'
        '🎯 In training set</div>'
    ) if cand.smiles in canonical_train else ""

    return (
        f'<div style="background:{bg_tint};border:1px solid {border_col};border-radius:10px;'
        f'overflow:hidden;margin-bottom:0.25rem;">'
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="Candidate {cand.rank}" '
        f'style="width:100%;height:{_IMG_H}px;object-fit:contain;display:block;background:#f5f3ee;"/>'
        f'<div style="padding:0.5rem 0.6rem;">'
        f'<div style="display:flex;align-items:center;gap:0.3rem;flex-wrap:wrap;margin-bottom:0.2rem;">'
        f'{_origin_badge_html(cand.source)}'
        f'</div>'
        f'<div style="font-size:1rem;font-weight:700;color:{p_col};'
        f'font-variant-numeric:tabular-nums;letter-spacing:-0.01em;line-height:1.2;">'
        f'P = {cand.probability:.3f}'
        f'<span style="font-size:0.75rem;font-weight:600;color:{delta_col};margin-left:0.4rem;">'
        f'Δ {cand.delta:+.3f}</span>'
        f'{_ad_html_inline(cand, "0.75rem")}'
        f'</div>'
        f'<div style="font-size:0.75rem;color:var(--color-text-muted);margin-top:0.2rem;'
        f'line-height:1.4;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;'
        f'-webkit-line-clamp:2;-webkit-box-orient:vertical;">'
        f'{cand.transformation or "—"}</div>'
        f'{train_html}'
        f'</div></div>'
    )


def _render_featured_candidate(
    cand: DesignCandidate, base_prob: float, tab_id: str, canonical_train: set[str],
) -> None:
    """Full-width horizontal card for the #1 ranked candidate."""
    b64 = _mol_png_b64(cand.smiles, 320, 220)
    if b64 is None:
        return

    bg_tint, border_col, delta_col = _delta_style(cand.delta)
    p_col = "var(--color-success)" if cand.probability >= 0.5 else "var(--color-danger)"
    train_html = (
        '<span style="color:var(--color-warning);font-size:0.7rem;margin-left:0.5rem;">'
        '🎯 In training set</span>'
    ) if cand.smiles in canonical_train else ""
    short_smi = cand.smiles[:56] + "…" if len(cand.smiles) > 56 else cand.smiles

    st.markdown(
        f'<div style="display:flex;gap:0;background:{bg_tint};'
        f'border:1px solid {border_col};border-radius:10px;'
        f'overflow:hidden;margin-bottom:0.4rem;">'
        f'<div style="flex-shrink:0;width:210px;background:#f5f3ee;">'
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="Top candidate #{cand.rank}: {short_smi}" '
        f'style="width:210px;height:155px;object-fit:contain;display:block;"/>'
        f'</div>'
        f'<div style="flex:1;padding:0.7rem 0.9rem;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;'
        f'margin-bottom:0.35rem;">'
        f'<span style="font-size:0.6875rem;font-weight:600;color:var(--color-text-muted);'
        f'text-transform:uppercase;letter-spacing:0.08em;line-height:1.2;">'
        f'#1 — {_delta_label(cand.delta)}</span>'
        f'{_origin_badge_html(cand.source)}{train_html}'
        f'</div>'
        f'<div style="font-size:1.125rem;font-weight:700;color:{p_col};margin-bottom:0.1rem;'
        f'font-variant-numeric:tabular-nums;letter-spacing:-0.01em;">'
        f'P(active) = {cand.probability:.3f}'
        f'<span style="color:{delta_col};font-size:0.875rem;font-weight:600;'
        f'margin-left:0.55rem;">Δ {cand.delta:+.3f}</span>'
        f'{_ad_html_inline(cand)}'
        f'</div>'
        f'<div style="font-size:0.875rem;color:var(--color-text);line-height:1.5;'
        f'margin:0.3rem 0 0.2rem;word-break:break-word;">'
        f'{cand.transformation or "—"}'
        f'</div>'
        f'<div style="font-size:0.75rem;color:var(--color-text-dim);'
        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'
        f'font-variant-numeric:tabular-nums;">'
        f'{short_smi}'
        f'</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    smiles_clipboard_widget(cand.smiles, uid=f"dc_{tab_id}_feat")


def _render_compact_row(
    cand: DesignCandidate, base_prob: float, tab_id: str, canonical_train: set[str],
) -> None:
    """Slim horizontal row for non-featured candidates."""
    b64 = _mol_png_b64(cand.smiles, 120, 90)
    if b64 is None:
        return

    _, _, delta_col = _delta_style(cand.delta)
    p_col = "var(--color-success)" if cand.probability >= 0.5 else "var(--color-danger)"
    train_marker = " 🎯" if cand.smiles in canonical_train else ""
    transf = (cand.transformation or "—")[:90]

    img_col, detail_col, action_col = st.columns([1, 7, 2])
    with img_col:
        st.markdown(
            f'<img src="data:image/png;base64,{b64}" '
            f'alt="Candidate #{cand.rank}" '
            f'style="width:100%;max-height:64px;object-fit:contain;background:#f5f3ee;'
            f'border-radius:4px;display:block;margin-top:3px;"/>',
            unsafe_allow_html=True,
        )
    with detail_col:
        st.markdown(
            f'<div style="padding:0.15rem 0;border-bottom:1px solid var(--color-border);">'
            f'<div style="display:flex;align-items:baseline;gap:0.45rem;flex-wrap:wrap;">'
            f'<span style="font-size:0.75rem;font-weight:600;color:var(--color-text-muted);">'
            f'#{cand.rank}</span>'
            f'<span style="font-size:0.875rem;font-weight:600;color:{p_col};'
            f'font-variant-numeric:tabular-nums;">'
            f'P = {cand.probability:.3f}</span>'
            f'<span style="font-size:0.75rem;color:{delta_col};font-variant-numeric:tabular-nums;">'
            f'Δ {cand.delta:+.3f}</span>'
            f'{_ad_html_inline(cand, "0.75rem")}'
            f'{_origin_badge_html(cand.source, "0.6875rem")}'
            f'<span style="color:var(--color-warning);font-size:0.6875rem;">{train_marker}</span>'
            f'</div>'
            f'<div style="font-size:0.75rem;color:var(--color-text-muted);margin-top:0.1rem;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.4;">{transf}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with action_col:
        smiles_clipboard_widget(cand.smiles, uid=f"dc_{tab_id}_{cand.rank}")


# Origin badge colors — readable on light backgrounds
_ORIGIN_BADGE: dict[str, tuple[str, str]] = {
    "shap_guided":      ("#2a7d9e", "SHAP"),         # accent teal — analytically meaningful
    "bioisostere":      ("#23775a", "Bioisostere"),  # success green — chemically sound
    "terminal_removal": ("#b86020", "Terminal"),     # warning amber — terminal edit
    "brics_cross":      ("#6b6477", "BRICS"),        # muted purple — combinatorial
    "peripheral":       ("#8c8c98", "Peripheral"),   # grey — generic peripheral
    "standard":         ("#a8a8b0", "Standard"),     # light grey — least specific
}


# ---------------------------------------------------------------------------
# Strategy summary chart — LIGHT THEME
# ---------------------------------------------------------------------------

_STRATEGY_ORDER = [
    "brics_cross", "standard", "bioisostere",
    "terminal_removal", "shap_guided", "peripheral",
]
_STRATEGY_DISPLAY = {
    "brics_cross":      "BRICS",
    "standard":         "Standard",
    "bioisostere":      "Bioisostere",
    "terminal_removal": "Terminal",
    "shap_guided":      "SHAP",
    "peripheral":       "Peripheral",
}


def _render_strategy_summary(candidates: list[DesignCandidate]) -> None:
    """Render a compact bar chart showing candidate count per generation strategy."""
    if not candidates:
        return

    from collections import Counter
    counts = Counter(c.source for c in candidates if c.source)
    if not counts:
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels  = [_STRATEGY_DISPLAY.get(k, k) for k in _STRATEGY_ORDER if counts.get(k, 0) > 0]
        values  = [counts[k] for k in _STRATEGY_ORDER if counts.get(k, 0) > 0]
        colors  = [_ORIGIN_BADGE.get(k, ("#a8a8b0", ""))[0]
                   for k in _STRATEGY_ORDER if counts.get(k, 0) > 0]

        fig, ax = plt.subplots(figsize=(5, 1.4))
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f7f7f7")
        bars = ax.barh(labels, values, color=colors, height=0.55)
        ax.set_xlabel("Candidates", color="#65656f", fontsize=7)
        ax.tick_params(colors="#65656f", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#e0e0e0")
        ax.xaxis.label.set_color("#65656f")
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", color="#65656f", fontsize=6,
            )
        plt.tight_layout(pad=0.3)

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                    facecolor="#ffffff", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()

        st.markdown(
            '<div style="margin-top:0.6rem;">'
            '<div style="font-size:0.6875rem;color:var(--color-text-muted);font-weight:600;'
            'text-transform:uppercase;letter-spacing:0.08em;line-height:1.2;margin-bottom:0.25rem;">'
            'Generation strategy breakdown</div>'
            f'<img src="data:image/png;base64,{b64}" '
            'style="width:100%;max-width:420px;display:block;"/>'
            '</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Dataset similarity tab
# ---------------------------------------------------------------------------

def _render_dataset_similar(base_smi: str, radius: int, n_bits: int) -> None:
    from rdkit import Chem
    from rdkit.Chem import AllChem, DataStructs
    import numpy as np

    X_train   = st.session_state.get("X_train")
    smi_train = st.session_state.get("smiles_train") or []
    y_train   = st.session_state.get("y_train")

    if X_train is None:
        st.info("Training fingerprints not available.")
        return

    mol = Chem.MolFromSmiles(base_smi)
    if mol is None:
        return
    try:
        fp  = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        arr = np.zeros(n_bits, dtype=np.int32)
        DataStructs.ConvertToNumpyArray(fp, arr)
    except Exception:
        st.warning("Could not compute fingerprint.")
        return

    top_k = st.slider("Neighbours to show", 3, 15, 5, key="design_sim_k")
    similar = find_similar_molecules(
        query_fp=arr, dataset_fps=X_train, top_k=top_k,
        dataset_smiles=smi_train or None,
        dataset_labels=list(y_train) if y_train is not None else None,
    )
    if not similar:
        st.info("No similar molecules found.")
        return

    st.caption("Training-set molecules nearest to the input (Tanimoto similarity).")

    items = [{
        "smiles": e.get("smiles"), "tc": e.get("tanimoto", 0.0),
        "label_str": (" · Active" if e.get("label") == 1
                      else " · Inactive" if e.get("label") == 0 else ""),
    } for e in similar]

    per_row = 4
    for row_start in range(0, len(items), per_row):
        row  = items[row_start : row_start + per_row]
        cols = st.columns(per_row)
        for i, item in enumerate(row):
            with cols[i]:
                _render_sim_card(item)


def _render_sim_card(item: dict) -> None:
    from rdkit import Chem
    from rdkit.Chem import Draw

    smi = item.get("smiles")
    if not smi:
        return
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return
    img = Draw.MolToImage(mol, size=(160, 120))
    buf = BytesIO(); img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    tc  = item["tc"]
    lbl = item["label_str"]
    col = ("var(--color-success)" if "Active" in lbl
           else ("var(--color-danger)" if "Inactive" in lbl
                 else "var(--color-text-muted)"))
    st.markdown(
        f'<div style="background:var(--color-card);border:1px solid var(--color-border);'
        f'border-radius:8px;overflow:hidden;">'
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:100%;height:90px;object-fit:contain;display:block;background:#f5f3ee;"/>'
        f'<div style="padding:0.2rem 0.4rem;">'
        f'<div style="font-size:0.75rem;color:var(--color-accent);font-variant-numeric:tabular-nums;line-height:1.3;">Tc = {tc:.3f}</div>'
        f'<div style="font-size:0.6875rem;color:{col};font-weight:600;line-height:1.3;">{lbl or "—"}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
