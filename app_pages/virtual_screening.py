"""virtual_screening.py — Batch virtual screening against the loaded model."""

from __future__ import annotations

import hashlib
import io

import numpy as np
import pandas as pd
import streamlit as st
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs, Descriptors

from core.design_engine import DesignCandidate, _mol_to_fp, compute_ad_score
from ui.clipboard import smiles_clipboard_widget
from ui.design_panel import _IMG_H, _build_card_html


# ---------------------------------------------------------------------------
# Fingerprint batch computation — cached by SMILES content + fp params
# ---------------------------------------------------------------------------

@st.cache_data(max_entries=5)
def _compute_fps_batch(
    smiles_tuple: tuple[str, ...], radius: int, n_bits: int
) -> np.ndarray:
    """Compute Morgan fingerprints for a tuple of SMILES in one batch. Cached."""
    rows: list[np.ndarray] = []
    for smi in smiles_tuple:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            rows.append(np.zeros(n_bits, dtype=np.int32))
            continue
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        arr = np.zeros(n_bits, dtype=np.int32)
        DataStructs.ConvertToNumpyArray(fp, arr)
        rows.append(arr)
    return np.vstack(rows) if rows else np.empty((0, n_bits), dtype=np.int32)


# ---------------------------------------------------------------------------
# Canonical training-set cache (invalidated when smiles_train changes length)
# ---------------------------------------------------------------------------

def _get_canonical_train() -> set[str]:
    smiles_train = st.session_state.get("smiles_train") or []
    cache_key = "_vs_canonical_train_cache"
    cached = st.session_state.get(cache_key)
    if cached is None or cached.get("_len") != len(smiles_train):
        canon: set[str] = set()
        for smi in smiles_train:
            m = Chem.MolFromSmiles(smi)
            if m:
                canon.add(Chem.MolToSmiles(m))
        st.session_state[cache_key] = {"_len": len(smiles_train), "set": canon}
    return st.session_state[cache_key]["set"]


# ---------------------------------------------------------------------------
# SMILES validation helper
# ---------------------------------------------------------------------------

def _validate_smiles(raw: list[str]) -> tuple[list[tuple[str, object]], int]:
    """Return (valid_pairs, n_total). valid_pairs = [(canonical_smi, mol), ...]."""
    valid: list[tuple[str, object]] = []
    for smi in raw:
        smi = smi.strip()
        if not smi:
            continue
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            valid.append((smi, mol))
    return valid, len(raw)


# ---------------------------------------------------------------------------
# Section 1 — File upload
# ---------------------------------------------------------------------------

def _render_upload_section() -> None:
    uploaded = st.file_uploader(
        "Upload molecule library",
        type=["csv", "txt"],
        key="vs_file_uploader",
        help="CSV (SMILES column auto-detected) or TXT (one SMILES per line, no header).",
    )

    if uploaded is None:
        st.session_state.pop("vs_molecules", None)
        st.session_state.pop("vs_file_hash", None)
        st.session_state.pop("vs_parse_summary", None)
        st.session_state.pop("vs_pending_df", None)
        st.session_state.pop("vs_csv_candidates", None)
        return

    file_bytes = uploaded.read()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    if st.session_state.get("vs_file_hash") != file_hash:
        # New file — (re-)parse
        st.session_state["vs_file_hash"] = file_hash
        st.session_state.pop("vs_results", None)
        st.session_state.pop("vs_pending_df", None)
        st.session_state.pop("vs_csv_candidates", None)
        st.session_state.pop("vs_col_parse_key", None)

        ext = uploaded.name.rsplit(".", 1)[-1].lower()

        if ext == "txt":
            lines = file_bytes.decode("utf-8", errors="replace").splitlines()
            raw = [l.strip() for l in lines if l.strip()]
            valid_pairs, n_total = _validate_smiles(raw)
            st.session_state["vs_molecules"] = valid_pairs
            st.session_state["vs_parse_summary"] = (
                f"Loaded {n_total} molecules · "
                f"{n_total - len(valid_pairs)} invalid SMILES skipped"
            )
        else:
            df = pd.read_csv(io.BytesIO(file_bytes))
            candidates = [c for c in df.columns if "smiles" in c.lower()]
            st.session_state["vs_pending_df"] = df
            st.session_state["vs_csv_candidates"] = candidates

            if len(candidates) == 1:
                # Unambiguous — parse immediately
                raw = df[candidates[0]].dropna().astype(str).tolist()
                valid_pairs, n_total = _validate_smiles(raw)
                st.session_state["vs_molecules"] = valid_pairs
                st.session_state["vs_parse_summary"] = (
                    f"Loaded {n_total} molecules · "
                    f"{n_total - len(valid_pairs)} invalid SMILES skipped"
                )

    # Show column selector when there are 0 or 2+ candidates
    candidates = st.session_state.get("vs_csv_candidates")
    if candidates is not None and len(candidates) != 1:
        df = st.session_state.get("vs_pending_df")
        if df is not None:
            all_cols = list(df.columns)
            label = (
                "Multiple SMILES-like columns found — choose one:"
                if len(candidates) > 1
                else "SMILES column"
            )
            options = candidates if candidates else all_cols
            selected = st.selectbox(label, options, key="vs_smiles_col_select")

            parse_key = (st.session_state.get("vs_file_hash"), selected)
            if st.session_state.get("vs_col_parse_key") != parse_key:
                st.session_state["vs_col_parse_key"] = parse_key
                raw = df[selected].dropna().astype(str).tolist()
                valid_pairs, n_total = _validate_smiles(raw)
                st.session_state["vs_molecules"] = valid_pairs
                st.session_state["vs_parse_summary"] = (
                    f"Loaded {n_total} molecules · "
                    f"{n_total - len(valid_pairs)} invalid SMILES skipped"
                )

    summary = st.session_state.get("vs_parse_summary", "")
    if summary:
        st.caption(summary)


# ---------------------------------------------------------------------------
# Section 2 — Filters
# ---------------------------------------------------------------------------

def _render_filters() -> tuple[float, dict]:
    with st.expander("Filters", icon=":material/tune:", expanded=True):
        with st.container(border=True):
            st.markdown("**Activity threshold**")
            threshold = st.slider(
                "Minimum P(active)",
                min_value=0.50,
                max_value=0.99,
                value=st.session_state.get("vs_threshold", 0.50),
                step=0.01,
                format="%.2f",
                key="vs_threshold_slider",
                help="Only molecules with P(active) ≥ this value are shown.",
            )
            st.session_state["vs_threshold"] = threshold

        with st.container(border=True):
            st.markdown("**Drug-likeness filters**")
            left, right = st.columns([1, 1])
            with left:
                f_mw = st.toggle(
                    "MW ≤ 500 Da",
                    value=st.session_state.get("vs_filter_mw", True),
                    key="vs_filter_mw",
                )
                f_hbd = st.toggle(
                    "HBD ≤ 5",
                    value=st.session_state.get("vs_filter_hbd", True),
                    key="vs_filter_hbd",
                )
                f_rotb = st.toggle(
                    "Rotatable bonds ≤ 10",
                    value=st.session_state.get("vs_filter_rotb", True),
                    key="vs_filter_rotb",
                )
            with right:
                f_logp = st.toggle(
                    "LogP ≤ 5",
                    value=st.session_state.get("vs_filter_logp", True),
                    key="vs_filter_logp",
                )
                f_hba = st.toggle(
                    "HBA ≤ 10",
                    value=st.session_state.get("vs_filter_hba", True),
                    key="vs_filter_hba",
                )
                f_tpsa = st.toggle(
                    "TPSA ≤ 140 Å²",
                    value=st.session_state.get("vs_filter_tpsa", True),
                    key="vs_filter_tpsa",
                )

    return threshold, {
        "mw": f_mw, "logp": f_logp, "hbd": f_hbd,
        "hba": f_hba, "rotb": f_rotb, "tpsa": f_tpsa,
    }


# ---------------------------------------------------------------------------
# Section 3 — Screening pipeline (runs only on button click)
# ---------------------------------------------------------------------------

def _run_screening(
    vs_molecules: list,
    model,
    X_train,
    fp_radius: int,
    fp_nbits: int,
    threshold: float,
    filter_states: dict,
) -> None:
    n0 = len(vs_molecules)
    progress_bar = st.progress(0.0)
    status_holder = st.empty()

    # ── Step 1 — Property filters (cheapest) ───────────────────────────────
    status_holder.caption(
        f"Step 1/4 — Applying property filters ({n0} molecules)..."
    )
    progress_bar.progress(0.0, text=f"Step 1/4 — Applying property filters ({n0} molecules)...")

    prop_data: list[tuple] = []
    for smi, mol in vs_molecules:
        mw   = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd  = Descriptors.NumHDonors(mol)
        hba  = Descriptors.NumHAcceptors(mol)
        rotb = Descriptors.NumRotatableBonds(mol)
        tpsa = Descriptors.TPSA(mol)
        prop_data.append((smi, mol, mw, logp, hbd, hba, rotb, tpsa))

    filtered1: list[tuple] = []
    for row in prop_data:
        smi, mol, mw, logp, hbd, hba, rotb, tpsa = row
        if filter_states["mw"]   and mw   > 500:  continue
        if filter_states["logp"] and logp > 5:     continue
        if filter_states["hbd"]  and hbd  > 5:     continue
        if filter_states["hba"]  and hba  > 10:    continue
        if filter_states["rotb"] and rotb > 10:    continue
        if filter_states["tpsa"] and tpsa > 140:   continue
        filtered1.append(row)

    n1 = len(filtered1)
    progress_bar.progress(0.25, text=f"Step 1/4 — {n1}/{n0} passed property filters.")

    if n1 == 0:
        _finish_empty(progress_bar, status_holder, n0, n1, 0, 0)
        return

    # ── Step 2 — Fingerprint computation (batched, cached) ─────────────────
    progress_bar.progress(0.25, text=f"Step 2/4 — Computing fingerprints ({n1} molecules)...")
    status_holder.caption(f"Step 2/4 — Computing fingerprints ({n1} molecules)...")

    smiles_tuple = tuple(row[0] for row in filtered1)
    fps_matrix = _compute_fps_batch(smiles_tuple, fp_radius, fp_nbits)  # (n1, n_bits)

    progress_bar.progress(0.50, text=f"Step 2/4 — {n1} fingerprints computed.")

    # ── Step 3 — Model prediction + activity threshold ─────────────────────
    progress_bar.progress(0.50, text=f"Step 3/4 — Predicting activity ({n1} molecules)...")
    status_holder.caption(f"Step 3/4 — Predicting activity ({n1} molecules)...")

    probas = model.predict_proba(fps_matrix)[:, 1]  # single batch call
    passed_mask = probas >= threshold
    n2 = int(passed_mask.sum())

    filtered2 = [
        (*filtered1[i], float(probas[i]))
        for i in range(n1)
        if passed_mask[i]
    ]
    fps_step3 = fps_matrix[passed_mask]  # (n2, n_bits)

    progress_bar.progress(0.75, text=f"Step 3/4 — {n2} molecules passed activity threshold.")

    if n2 == 0:
        _finish_empty(progress_bar, status_holder, n0, n1, n2, 0)
        return

    # ── Step 4 — AD scoring + training/test membership (single Tanimoto pass)
    progress_bar.progress(0.75, text=f"Step 4/4 — Computing applicability domain ({n2} molecules)...")
    status_holder.caption(f"Step 4/4 — Computing applicability domain ({n2} molecules)...")

    # --- Training set Tanimoto (one matrix multiply) -----------------------
    if X_train is not None and len(X_train) > 0:
        Q  = fps_step3.astype(np.float32)         # (n2, n_bits)
        DB = X_train.astype(np.float32)           # (n_train, n_bits)
        inter = Q.dot(DB.T)                       # (n2, n_train)
        q_sum = Q.sum(axis=1, keepdims=True)      # (n2, 1)
        db_sum = DB.sum(axis=1)                   # (n_train,)
        union_mat = q_sum + db_sum[np.newaxis, :] - inter   # (n2, n_train)
        tan_train = np.where(union_mat > 0, inter / union_mat, 0.0)  # (n2, n_train)

        # AD score: mean of top-5 Tanimoto per molecule
        top5 = np.sort(tan_train, axis=1)[:, ::-1][:, :5]  # (n2, 5)
        ad_scores = top5.mean(axis=1)                       # (n2,)

        # Training membership: max Tanimoto >= 0.999
        in_training_arr = tan_train.max(axis=1) >= 0.999   # (n2,)
    else:
        ad_scores = np.ones(n2, dtype=np.float32)
        in_training_arr = np.zeros(n2, dtype=bool)

    # --- Test set Tanimoto -------------------------------------------------
    test_df = st.session_state.get("test_df")
    test_df_meta = st.session_state.get("test_df_meta", {})
    smiles_col_test = test_df_meta.get("smiles_col")

    in_test_arr = np.zeros(n2, dtype=bool)
    if test_df is not None and smiles_col_test and smiles_col_test in test_df.columns:
        test_smiles_list = test_df[smiles_col_test].dropna().astype(str).tolist()
        if test_smiles_list:
            X_test_fps = _compute_fps_batch(tuple(test_smiles_list), fp_radius, fp_nbits)
            if len(X_test_fps) > 0:
                Q   = fps_step3.astype(np.float32)
                DBt = X_test_fps.astype(np.float32)
                inter_t = Q.dot(DBt.T)
                q_sum   = Q.sum(axis=1, keepdims=True)
                dbt_sum = DBt.sum(axis=1)
                union_t = q_sum + dbt_sum[np.newaxis, :] - inter_t
                tan_test = np.where(union_t > 0, inter_t / union_t, 0.0)
                in_test_arr = tan_test.max(axis=1) >= 0.999

    # --- Assemble results --------------------------------------------------
    results: list[dict] = []
    for i, (smi, mol, mw, logp, hbd, hba, rotb, tpsa, p_active) in enumerate(filtered2):
        results.append({
            "smiles":          smi,
            "mol":             mol,
            "p_active":        p_active,
            "ad_score":        float(ad_scores[i]),
            "mw":              mw,
            "logp":            logp,
            "hbd":             hbd,
            "hba":             hba,
            "rotbonds":        rotb,
            "tpsa":            tpsa,
            "in_training_set": bool(in_training_arr[i]),
            "in_test_set":     bool(in_test_arr[i]),
        })

    n3 = len(results)
    progress_bar.progress(1.0, text=f"Step 4/4 — Done: {n3} final hits.")
    progress_bar.empty()
    status_holder.empty()

    st.session_state["vs_results"] = results
    st.session_state["vs_funnel"] = {"n0": n0, "n1": n1, "n2": n2, "n3": n3}


def _finish_empty(progress_bar, status_holder, n0, n1, n2, n3) -> None:
    progress_bar.empty()
    status_holder.empty()
    st.session_state["vs_results"] = []
    st.session_state["vs_funnel"] = {"n0": n0, "n1": n1, "n2": n2, "n3": n3}


# ---------------------------------------------------------------------------
# Section 4 — Results grid
# ---------------------------------------------------------------------------

def _sort_results(results: list[dict], sort_by: str) -> list[dict]:
    if sort_by == "P(active) ↓":
        return sorted(results, key=lambda r: r["p_active"], reverse=True)
    if sort_by == "P(active) ↑":
        return sorted(results, key=lambda r: r["p_active"])
    if sort_by == "AD score ↓":
        return sorted(results, key=lambda r: r["ad_score"], reverse=True)
    if sort_by == "MW ↓":
        return sorted(results, key=lambda r: r["mw"], reverse=True)
    return results


def _render_results(vs_results: list[dict]) -> None:
    sort_options = ["P(active) ↓", "P(active) ↑", "AD score ↓", "MW ↓"]
    current_sort = st.session_state.get("vs_sort_by", "P(active) ↓")
    current_per  = st.session_state.get("vs_per_page", 12)

    ctrl_cols = st.columns([2, 1, 1, 1], gap="small")
    with ctrl_cols[0]:
        sort_by = st.selectbox(
            "Sort by",
            sort_options,
            index=sort_options.index(current_sort) if current_sort in sort_options else 0,
            key="vs_sort_select",
            label_visibility="collapsed",
        )
        st.session_state["vs_sort_by"] = sort_by

    with ctrl_cols[1]:
        per_page = st.number_input(
            "Results per page",
            min_value=6,
            max_value=48,
            value=current_per,
            step=6,
            key="vs_per_page_input",
        )
        st.session_state["vs_per_page"] = per_page

    sorted_results = _sort_results(vs_results, sort_by)
    total   = len(sorted_results)
    n_pages = max(1, (total + per_page - 1) // per_page)
    page    = max(0, min(st.session_state.get("vs_page", 0), n_pages - 1))

    with ctrl_cols[2]:
        if st.button(
            ":material/chevron_left: Prev",
            key="vs_prev_btn",
            disabled=(page == 0),
        ):
            st.session_state["vs_page"] = page - 1
            st.rerun()

    with ctrl_cols[3]:
        if st.button(
            "Next :material/chevron_right:",
            key="vs_next_btn",
            disabled=(page >= n_pages - 1),
        ):
            st.session_state["vs_page"] = page + 1
            st.rerun()

    st.caption(f"Page {page + 1} of {n_pages} · {total} total hits")

    # Render current page slice only
    start      = page * per_page
    page_slice = sorted_results[start : start + per_page]
    canonical_train = _get_canonical_train()

    per_row = 3
    placeholder_h = _IMG_H + 110 + 70  # card + clipboard + button

    for row_start in range(0, len(page_slice), per_row):
        row  = page_slice[row_start : row_start + per_row]
        cols = st.columns(per_row, gap="small")

        for col_i in range(per_row):
            with cols[col_i]:
                if col_i < len(row):
                    hit  = row[col_i]
                    rank = start + row_start + col_i + 1

                    # Wrap result as DesignCandidate to reuse _build_card_html
                    cand = DesignCandidate(
                        smiles=hit["smiles"],
                        probability=hit["p_active"],
                        delta=hit["p_active"] - 0.5,
                        source="vs_hit",
                        transformation=(
                            f"MW={hit['mw']:.0f}  logP={hit['logp']:.2f}  "
                            f"HBD={hit['hbd']}  HBA={hit['hba']}  "
                            f"TPSA={hit['tpsa']:.0f}"
                        ),
                        rank=rank,
                        ad_score=hit["ad_score"],
                    )
                    st.markdown(
                        _build_card_html(cand, 0.5, canonical_train),
                        unsafe_allow_html=True,
                    )

                    # Test set badge — slot not present in _build_card_html
                    if hit.get("in_test_set"):
                        st.caption("🧪 In test set")

                    smiles_clipboard_widget(hit["smiles"], uid=f"vs_{rank}")

                    use_key = f"vs_use_{rank}_{abs(hash(hit['smiles'])) % 99991}"
                    if st.button("↗ Use in app", key=use_key, width="stretch"):
                        st.session_state["current_smiles"] = hit["smiles"]
                        st.toast(f"Set: {hit['smiles'][:50]}…", icon="✅")
                        st.rerun()
                else:
                    st.markdown(
                        f'<div style="height:{placeholder_h}px;visibility:hidden;"></div>',
                        unsafe_allow_html=True,
                    )


# ---------------------------------------------------------------------------
# Section 5 — Export
# ---------------------------------------------------------------------------

def _render_export(vs_results: list[dict]) -> None:
    rows = [
        {
            "SMILES":           r["smiles"],
            "P_active":         round(r["p_active"],  4),
            "AD_score":         round(r["ad_score"],  4),
            "MW":               round(r["mw"],        2),
            "logP":             round(r["logp"],       3),
            "HBD":              r["hbd"],
            "HBA":              r["hba"],
            "RotBonds":         r["rotbonds"],
            "TPSA":             round(r["tpsa"],       2),
            "in_training_set":  r["in_training_set"],
            "in_test_set":      r["in_test_set"],
        }
        for r in vs_results
    ]
    csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download results as CSV",
        data=csv_bytes,
        file_name="virtual_screening_results.csv",
        mime="text/csv",
        icon=":material/download:",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_virtual_screening() -> None:
    model    = st.session_state.get("rf_model")
    X_train  = st.session_state.get("X_train")
    fp_radius = st.session_state.get("fp_radius", 3)
    fp_nbits  = st.session_state.get("fp_nbits", 2048)

    if model is None:
        st.info(
            "No model loaded. Upload a trained scikit-learn model in the "
            "**Model** section of the sidebar to enable virtual screening."
        )
        return

    st.markdown("## Virtual screening")

    # Section 1 — upload
    _render_upload_section()

    vs_molecules = st.session_state.get("vs_molecules", [])

    # Section 2 — filters
    threshold, filter_states = _render_filters()

    # Section 3 — run button
    if st.button(
        "Run screening",
        type="primary",
        icon=":material/play_arrow:",
        disabled=(len(vs_molecules) == 0),
        key="vs_run_btn",
    ):
        _run_screening(
            vs_molecules, model, X_train,
            fp_radius, fp_nbits, threshold, filter_states,
        )
        st.session_state["vs_page"] = 0

    # Funnel summary + results (shown whenever vs_results is populated)
    vs_results = st.session_state.get("vs_results")
    if vs_results is None:
        return

    funnel = st.session_state.get("vs_funnel", {})
    st.caption(
        f"{funnel.get('n0', '?')} loaded → "
        f"{funnel.get('n1', '?')} passed property filters → "
        f"{funnel.get('n2', '?')} passed activity threshold → "
        f"{funnel.get('n3', '?')} final hits"
    )

    n3 = funnel.get("n3", 0)
    if n3 > 0:
        st.success(f"{n3} molecules passed all filters.")
        _render_results(vs_results)
        st.divider()
        _render_export(vs_results)
    else:
        st.warning("No molecules passed all filters.")
