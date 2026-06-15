"""molecular_evolution_path.py — Molecular Evolution Path visualization.

Renders an interactive wrapped timeline of molecules showing the guided design
optimization trajectory. Consecutive molecules are connected by structural diff
boxes (added = green, removed = red). The timeline wraps at ROW_SIZE = 5
molecules per row.
"""
from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional

import streamlit as st

# Maximum molecules per timeline row before wrapping to a new row
_ROW_SIZE = 5


# ---------------------------------------------------------------------------
# Structural diff via MCS
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def compute_structural_diff(smiles_a: str, smiles_b: str) -> dict:
    """Compute structural diff between two SMILES using MCS.

    Returns:
        dict with keys:
            added_frags:     list[str]  — fragment SMILES in mol_b but not mol_a
            removed_frags:   list[str]  — fragment SMILES in mol_a but not mol_b
            scaffold_change: bool       — True if MCS coverage < 0.40 or MCS failed
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import rdFMCS

        mol_a = Chem.MolFromSmiles(smiles_a)
        mol_b = Chem.MolFromSmiles(smiles_b)
        if mol_a is None or mol_b is None:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        mcs = rdFMCS.FindMCS([mol_a, mol_b], timeout=5)

        if mcs.canceled or mcs.numAtoms == 0:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        min_atoms = min(mol_a.GetNumAtoms(), mol_b.GetNumAtoms())
        if mcs.numAtoms / max(min_atoms, 1) < 0.40:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        mcs_mol = Chem.MolFromSmarts(mcs.smartsString)
        if mcs_mol is None:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        def _non_mcs_frags(mol: "Chem.Mol") -> list[str]:
            match = mol.GetSubstructMatch(mcs_mol)
            if not match:
                return []
            non_mcs = [i for i in range(mol.GetNumAtoms()) if i not in set(match)]
            if not non_mcs:
                return []
            try:
                frag_smi = Chem.MolFragmentToSmiles(mol, atomsToUse=non_mcs)
                if not frag_smi:
                    return []
                parts = [p.strip() for p in frag_smi.split(".") if p.strip()]
                valid: list[str] = []
                for p in parts:
                    m = Chem.MolFromSmiles(p)
                    if m and m.GetNumAtoms() >= 1:
                        valid.append(Chem.MolToSmiles(m))
                return valid[:3]  # cap at 3 boxes per side
            except Exception:
                return []

        return {
            "added_frags":   _non_mcs_frags(mol_b),
            "removed_frags": _non_mcs_frags(mol_a),
            "scaffold_change": False,
        }
    except Exception:
        return {"added_frags": [], "removed_frags": [], "scaffold_change": True}


# ---------------------------------------------------------------------------
# Molecule image rendering
# ---------------------------------------------------------------------------

def mol_to_img_bytes(smiles: str, width: int, height: int) -> Optional[bytes]:
    """Render SMILES as PNG bytes via RDKit Draw."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        img = Draw.MolToImage(mol, size=(width, height))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


# ---------------------------------------------------------------------------
# Adaptive sizing
# ---------------------------------------------------------------------------

def _get_sizes(n_steps: int) -> tuple[int, int, int, int]:
    """Return (mol_w, mol_h, frag_w, frag_h) based on total step count."""
    if n_steps <= 3:
        return 250, 200, 150, 120
    elif n_steps <= 6:
        return 180, 150, 108, 90
    else:
        return 130, 110, 78, 66


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _frag_box_html(smiles: str, frag_w: int, frag_h: int, border: str, bg: str) -> str:
    """Return HTML for a single fragment image box, or empty string on failure."""
    png = mol_to_img_bytes(smiles, frag_w, frag_h)
    if png is None:
        return ""
    return (
        f'<div style="display:inline-block;border:1.5px solid {border};background:{bg};'
        f'border-radius:10px;padding:4px;margin:2px 0;">'
        f'<img src="data:image/png;base64,{_b64(png)}" style="display:block;border-radius:6px;"/>'
        f'</div>'
    )


def _dashed_v(height: int = 14) -> str:
    return (
        f'<div style="width:1px;height:{height}px;border-left:1px dashed var(--color-text-dim);'
        f'margin:0 auto;"></div>'
    )


def _spacer(height: int) -> str:
    return f'<div style="height:{height}px;"></div>'


# ---------------------------------------------------------------------------
# Early-stopping truncation (Change 4)
# ---------------------------------------------------------------------------

def _truncate_early_stopping(history: list[dict]) -> tuple[list[dict], bool]:
    """Remove trailing repeated steps caused by early stopping.

    Finds the FIRST consecutive duplicate canonical SMILES and truncates there.
    Example: [A, B, C, C, C] → ([A, B, C], True)
    Example: [A, B, C, B, C] → ([A, B, C, B, C], False)  # no trailing repeat
    """
    if len(history) <= 1:
        return history, False

    try:
        from rdkit import Chem

        def _canon(s: str) -> str:
            try:
                m = Chem.MolFromSmiles(s)
                return Chem.MolToSmiles(m) if m else s
            except Exception:
                return s

        cutoff = len(history)
        for i in range(1, len(history)):
            if _canon(history[i]["best_smiles"]) == _canon(history[i - 1]["best_smiles"]):
                cutoff = i
                break
        return history[:cutoff], cutoff < len(history)
    except Exception:
        # Fallback: plain string comparison
        cutoff = len(history)
        for i in range(1, len(history)):
            if history[i]["best_smiles"] == history[i - 1]["best_smiles"]:
                cutoff = i
                break
        return history[:cutoff], cutoff < len(history)


# ---------------------------------------------------------------------------
# Main rendering function
# ---------------------------------------------------------------------------

def render_evolution_path(
    history: list[dict],
    start_smiles: str = "",
    has_train_filter: bool = False,
) -> None:
    """Render the molecular evolution path timeline.

    Args:
        history:           List of dicts from run_guided_pipeline, each with
                           keys: iteration, n_generated, best_prob, ad_score,
                           best_smiles.
        start_smiles:      Unused (step 0 is already in history); kept for
                           API compatibility.
        has_train_filter:  If True, adds a note about training-set exclusion.
    """
    if not history:
        st.info("No evolution history available.")
        return

    # ── Change 4: truncate early-stopping plateau ─────────────────────────
    history, was_truncated = _truncate_early_stopping(history)
    n_steps = len(history)

    # ── Caption ────────────────────────────────────────────────────────────
    train_note = (
        " Molecules already present in the training set are automatically "
        "excluded from results."
        if has_train_filter
        else ""
    )
    st.markdown(
        f"<p style='color:var(--color-text-muted);font-size:0.875rem;margin-bottom:10px;line-height:1.55;'>"
        f"Each step shows the highest-scoring molecule in the beam at that iteration. "
        f"Green fragments were added; red fragments were removed relative to the previous step. "
        f"A 🔀 scaffold change label indicates a major structural reorganization where a "
        f"fragment-level diff is not meaningful.{train_note}"
        f"</p>",
        unsafe_allow_html=True,
    )

    if n_steps == 1:
        mol_w, mol_h, _, _ = _get_sizes(1)
        _render_single(history[0], mol_w, mol_h)
        return

    mol_w, mol_h, frag_w, frag_h = _get_sizes(n_steps)
    n_transitions = n_steps - 1

    # Precompute all diffs (cached)
    all_diffs = [
        compute_structural_diff(
            history[i]["best_smiles"],
            history[i + 1]["best_smiles"],
        )
        for i in range(n_transitions)
    ]

    # ── Change 3: split into rows of _ROW_SIZE ────────────────────────────
    chunks = [history[i : i + _ROW_SIZE] for i in range(0, n_steps, _ROW_SIZE)]

    for chunk_idx, chunk in enumerate(chunks):
        chunk_start = chunk_idx * _ROW_SIZE

        if chunk_idx > 0:
            # Continuation header
            st.markdown(
                '<div style="color:var(--color-text-dark);font-size:0.75rem;margin:6px 0 2px;">'
                "↩ continued from previous row"
                "</div>",
                unsafe_allow_html=True,
            )
            # Cross-row diff (last mol of previous chunk → first mol of current chunk)
            cross_diff = all_diffs[chunk_start - 1]
            _render_cross_row_diff(cross_diff, frag_w, frag_h)

        # Diffs within this chunk
        chunk_diffs = [all_diffs[chunk_start + i] for i in range(len(chunk) - 1)]

        _render_timeline_html(chunk, chunk_diffs, mol_w, mol_h, frag_w, frag_h)

        if chunk_idx < len(chunks) - 1:
            st.markdown(
                '<div style="color:var(--color-text-dark);font-size:0.75rem;margin:2px 0 4px;text-align:right;">'
                "↪ continues below"
                "</div>",
                unsafe_allow_html=True,
            )

    # ── Load-molecule buttons (one per step) ─────────────────────────────
    st.markdown(
        '<div style="color:var(--color-text-muted);font-size:0.75rem;text-align:center;margin:8px 0 4px;">'
        "Click a button to load that molecule for analysis"
        "</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(n_steps)
    for i, (col, step) in enumerate(zip(cols, history)):
        with col:
            label = "Base" if step["iteration"] == 0 else f"Step {step['iteration']}"
            if st.button(f"📋 {label}", key=f"_evo_load_{i}", width="stretch"):
                st.session_state["current_smiles"] = step["best_smiles"]
                st.session_state["design_smiles_input_pending"] = step["best_smiles"]
                st.rerun()

    # ── Truncation note (Change 4) ─────────────────────────────────────────
    if was_truncated:
        st.markdown(
            "<p style='color:var(--color-text-dark);font-size:0.75rem;font-style:italic;margin-top:6px;'>"
            "Timeline truncated at first repeated step (early stopping detected). "
            "See the line plot above for the full iteration history."
            "</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Cross-row diff renderer (Change 3)
# ---------------------------------------------------------------------------

def _render_cross_row_diff(diff: dict, frag_w: int, frag_h: int) -> None:
    """Render the structural diff for the transition between two timeline rows."""
    if diff["scaffold_change"]:
        st.markdown(
            '<div style="color:var(--color-text-dark);font-size:0.75rem;font-style:italic;margin:2px 0 4px;">'
            "🔀 scaffold change between rows"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    added_boxes = "".join(
        _frag_box_html(f, frag_w, frag_h, "var(--color-success)", "var(--color-success-a08)")
        for f in diff["added_frags"]
    )
    removed_boxes = "".join(
        _frag_box_html(f, frag_w, frag_h, "var(--color-danger)", "var(--color-danger-a08)")
        for f in diff["removed_frags"]
    )

    if not added_boxes and not removed_boxes:
        return

    parts: list[str] = []
    if added_boxes:
        parts.append(
            f'<div style="display:flex;flex-direction:column;align-items:flex-start;gap:2px;">'
            f'<span style="color:var(--color-success);font-size:0.65rem;">+ added</span>'
            f'{added_boxes}</div>'
        )
    if removed_boxes:
        parts.append(
            f'<div style="display:flex;flex-direction:column;align-items:flex-start;gap:2px;">'
            f'<span style="color:var(--color-danger);font-size:0.65rem;">− removed</span>'
            f'{removed_boxes}</div>'
        )

    html = (
        '<div style="display:flex;gap:14px;align-items:flex-start;'
        'margin:2px 0 6px;padding:4px 0;">'
        + "".join(parts)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Per-row HTML table builder
# ---------------------------------------------------------------------------

def _render_timeline_html(
    chunk: list[dict],
    chunk_diffs: list[dict],
    mol_w: int,
    mol_h: int,
    frag_w: int,
    frag_h: int,
) -> None:
    """Build one timeline row as a 3-row HTML table (top/mid/bot)."""
    n_mols = len(chunk)
    n_trans = len(chunk_diffs)

    top_cells: list[str] = []
    mid_cells: list[str] = []
    bot_cells: list[str] = []

    for i, step in enumerate(chunk):
        # ── Molecule cell ────────────────────────────────────────────────
        png = mol_to_img_bytes(step["best_smiles"], mol_w, mol_h)
        step_label = "Base" if step["iteration"] == 0 else f"Step {step['iteration']}"

        if png:
            img_tag = (
                f'<img src="data:image/png;base64,{_b64(png)}" '
                f'style="display:block;border-radius:8px;" '
                f'title="Click a button below to load this molecule"/>'
            )
        else:
            img_tag = (
                f'<div style="width:{mol_w}px;height:{mol_h}px;color:#666;'
                f'font-size:0.7rem;text-align:center;'
                f'line-height:{mol_h}px;">Invalid SMILES</div>'
            )

        mol_td = (
            f'<td style="vertical-align:middle;text-align:center;padding:4px 6px;">'
            f'<div style="display:inline-block;border:1px solid #aaaaaa;border-radius:10px;'
            f'background:rgba(255,255,255,0.04);padding:6px;">{img_tag}</div>'
            f'<div style="color:#8890c4;font-size:0.6875rem;margin-top:3px;">{step_label}</div>'
            f'<div style="color:#eceaf8;font-size:0.75rem;margin-top:1px;">'
            f'P&nbsp;=&nbsp;<b>{step["best_prob"]:.3f}</b>&nbsp;|&nbsp;'
            f'AD&nbsp;=&nbsp;<b>{step["ad_score"]:.2f}</b>'
            f'</div></td>'
        )
        top_cells.append("<td></td>")
        mid_cells.append(mol_td)
        bot_cells.append("<td></td>")

        # ── Transition cell (only between molecules) ─────────────────────
        if i >= n_trans:
            continue

        diff = chunk_diffs[i]

        if diff["scaffold_change"]:
            top_cells.append("<td></td>")
            mid_cells.append(
                "<td style='vertical-align:middle;text-align:center;"
                "padding:0 8px;min-width:80px;'>"
                "<div style='height:1px;background:#555555;width:100%;'></div>"
                "<div style='color:#888888;font-size:0.75rem;font-style:italic;"
                "margin-top:5px;'>🔀 scaffold<br>change</div>"
                "</td>"
            )
            bot_cells.append("<td></td>")
        else:
            # — Added fragments (green, top row) —
            added_html = "".join(
                _frag_box_html(f, frag_w, frag_h, "var(--color-success)", "var(--color-success-a08)")
                for f in diff["added_frags"]
            )
            has_added = bool(added_html.strip())

            top_cells.append(
                f"<td style='vertical-align:bottom;text-align:center;padding:0 6px;'>"
                f"<div style='display:flex;flex-direction:column;align-items:center;'>"
                f"{added_html}"
                f"{_dashed_v(14) if has_added else _spacer(14)}"
                f"</div></td>"
            )

            # — Removed fragments (red, bottom row) —
            removed_html = "".join(
                _frag_box_html(f, frag_w, frag_h, "var(--color-danger)", "var(--color-danger-a08)")
                for f in diff["removed_frags"]
            )
            has_removed = bool(removed_html.strip())

            bot_cells.append(
                f"<td style='vertical-align:top;text-align:center;padding:0 6px;'>"
                f"<div style='display:flex;flex-direction:column;align-items:center;'>"
                f"{_dashed_v(14) if has_removed else _spacer(14)}"
                f"{removed_html}"
                f"</div></td>"
            )

            # — Horizontal connector (mid row) —
            top_dash = _dashed_v(10) if has_added else _spacer(10)
            bot_dash = _dashed_v(10) if has_removed else _spacer(10)
            mid_cells.append(
                f"<td style='vertical-align:middle;padding:0 4px;"
                f"min-width:50px;text-align:center;'>"
                f"{top_dash}"
                f"<div style='height:1px;background:#aaaaaa;width:100%;'></div>"
                f"{bot_dash}"
                f"</td>"
            )

    html = (
        "<div style='overflow-x:auto;padding-bottom:4px;'>"
        "<table style='border-collapse:collapse;width:max-content;margin:0 auto;'>"
        f"<tr>{''.join(top_cells)}</tr>"
        f"<tr>{''.join(mid_cells)}</tr>"
        f"<tr>{''.join(bot_cells)}</tr>"
        "</table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Single-molecule fallback
# ---------------------------------------------------------------------------

def _render_single(step: dict, mol_w: int, mol_h: int) -> None:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        png = mol_to_img_bytes(step["best_smiles"], mol_w, mol_h)
        if png:
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<div style='display:inline-block;border:1px solid #aaaaaa;"
                f"border-radius:10px;background:rgba(255,255,255,0.04);padding:6px;'>"
                f"<img src='data:image/png;base64,{_b64(png)}' "
                f"style='display:block;border-radius:8px;'/>"
                f"</div>"
                f"<div style='color:#8890c4;font-size:0.6875rem;margin-top:4px;'>Base molecule</div>"
                f"<div style='color:#eceaf8;font-size:0.75rem;margin-top:2px;'>"
                f"P&nbsp;=&nbsp;<b>{step['best_prob']:.3f}</b>&nbsp;|&nbsp;"
                f"AD&nbsp;=&nbsp;<b>{step['ad_score']:.2f}</b>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        if st.button("📋 Load Base Molecule", key="_evo_load_0"):
            st.session_state["current_smiles"] = step["best_smiles"]
            st.session_state["design_smiles_input_pending"] = step["best_smiles"]
            st.rerun()
