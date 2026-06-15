"""Prediction page — full molecule analysis report."""

import base64
import streamlit as st
import numpy as np
from io import BytesIO
from typing import Optional

from ui.components import (
    smiles_to_mol,
    render_ecfp_grid,
    render_bit_detail,
    render_prediction_card,
    render_ad_badge,
    get_maccs_smarts,
)


# ── SMARTS helper ─────────────────────────────────────────────────────────────

def _smiles_to_smarts(smi: str) -> str:
    """Convert a SMILES string to its SMARTS representation."""
    from rdkit import Chem
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol:
            return Chem.MolToSmarts(mol)
    except Exception:
        pass
    return smi


# ── Shared card-grid renderer ─────────────────────────────────────────────────

def _render_substruct_card_grid(items: list, cols: int = 4):
    """
    Render substructure fragments as individual dark cards in an HTML grid.

    Each item dict must have:
        smiles       – SMILES or SMARTS of the fragment
        label        – primary label (monospace, cyan)
        sublabel     – secondary info (small, muted)
        border_color – left-border accent colour
    """
    from rdkit.Chem import Draw

    if not items:
        return

    grid_css = f"""<style>
    .substruct-grid{{display:grid;
        grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
        gap:0.5rem;margin:0.5rem 0;}}
    .substruct-item{{background:var(--color-card);border:1px solid var(--color-border);
        border-radius:8px;overflow:hidden;}}
    .substruct-item img{{width:100%;display:block;background:#f5f3ee;
        border-radius:8px 8px 0 0;}}
    .substruct-info{{padding:0.28rem 0.42rem;}}
    .substruct-label{{font-family:var(--font-main);
        font-size:0.875rem;font-weight:500;color:var(--color-text);line-height:1.3;}}
    .substruct-sublabel{{font-size:0.75rem;color:var(--color-text-muted);margin-top:0.1rem;line-height:1.3;}}
    .substruct-smarts{{font-size:0.6875rem;color:var(--color-text-dark);font-family:var(--font-main);
        margin-top:0.15rem;cursor:pointer;word-break:break-all;
        white-space:normal;line-height:1.4;}}
    .substruct-smarts:hover{{color:var(--color-accent);}}
    .substruct-smarts:focus{{outline:2px solid var(--color-accent);border-radius:2px;}}
    </style>"""

    cards = []
    for item in items:
        mol = smiles_to_mol(item["smiles"])
        if mol is None:
            continue
        img = Draw.MolToImage(mol, size=(200, 160))
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        border = item.get("border_color", "#283058")
        smarts = item.get("smarts")
        smarts_html = ""
        if smarts:
            safe_smarts = smarts.replace("'", "&#39;").replace('"', "&quot;")
            smarts_html = (
                f'<button class="substruct-smarts" title="Copy SMARTS to clipboard" '
                f'style="background:none;border:none;padding:0;text-align:left;width:100%;" '
                f'onclick="navigator.clipboard.writeText(\'{safe_smarts}\')">'
                f'&#10697; {safe_smarts}</button>'
            )
        cards.append(
            f'<div class="substruct-item" style="border-left:3px solid {border};">'
            f'<img src="data:image/png;base64,{b64}"/>'
            f'<div class="substruct-info">'
            f'<div class="substruct-label">{item["label"]}</div>'
            f'<div class="substruct-sublabel">{item["sublabel"]}</div>'
            f'{smarts_html}'
            f'</div></div>'
        )

    if cards:
        st.markdown(
            grid_css + '<div class="substruct-grid">' + "".join(cards) + "</div>",
            unsafe_allow_html=True,
        )


def _shap_features_to_card_items(features: list, border_color: str) -> list:
    """Convert a list of SHAP feature dicts to card-grid items."""
    items = []
    for f in features:
        if f["bit_on"] == 1 and f["mol_subs"]:
            sub_smi = f["mol_subs"][0]
            source = "ON"
        elif f["bit_on"] == 0 and f.get("db"):
            db = f["db"]
            sub_smi = db.get("dominant_substructure")
            if sub_smi is None:
                subs = db.get("substructures", {})
                if subs:
                    rows = (subs.most_common(1) if hasattr(subs, "most_common")
                            else sorted(subs.items(), key=lambda x: x[1], reverse=True)[:1])
                    sub_smi = rows[0][0] if rows else None
            source = "ABSENT (training)"
        else:
            continue

        if sub_smi is None:
            continue

        smarts = _smiles_to_smarts(sub_smi)
        items.append({
            "smiles": sub_smi,
            "label": f"ECFP6_{f['bit']}  ({source})",
            "sublabel": f"SHAP {f['shap']:+.4f}",
            "border_color": border_color,
            "smarts": smarts,
        })
    return items


def _get_mol_substructure(mol, bit_idx: int, bi: dict) -> Optional[str]:
    """
    Extract the actual substructure activating bit_idx in this specific molecule.
    Uses bitInfo from that molecule — never the training-set dominant substructure.
    Returns None if the bit is not ON in this molecule or extraction fails.

    Tries entries in descending radius order so the most informative (largest)
    environment is returned, falling back to smaller radii only if needed.
    Bare atom symbols (rad == 0) are used only as a last resort.
    """
    from rdkit import Chem
    if mol is None or bit_idx not in bi:
        return None

    # Sort descending by radius: prefer largest environment
    entries = sorted(bi[bit_idx], key=lambda x: x[1], reverse=True)

    atom_fallback = None  # single-atom symbol if nothing better is found
    for atom_idx, rad in entries:
        try:
            if rad == 0:
                # Save as fallback — don't return yet; a higher-rad entry may follow
                if atom_fallback is None:
                    atom_fallback = mol.GetAtomWithIdx(atom_idx).GetSymbol()
                continue
            env = Chem.FindAtomEnvironmentOfRadiusN(mol, rad, atom_idx)
            amap = {}
            submol = Chem.PathToSubmol(mol, env, atomMap=amap)
            if submol.GetNumAtoms() > 0:
                return Chem.MolToSmiles(submol)
        except Exception:
            continue

    return atom_fallback  # None if no entry succeeded at all


# ── Main entry point ──────────────────────────────────────────────────────────

def render_prediction_page():
    st.markdown(":material/analytics: **Prediction — Molecule Analysis**")
    st.caption(
        "Enter a SMILES string to get a prediction, applicability domain "
        "assessment, and full explainability breakdown."
    )

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        smiles_input = st.text_input(
            "SMILES",
            value=st.session_state.get("current_smiles", ""),
            placeholder="O=C(Nc1cnn(Cc2ccccc2)c1)c1ccnc2ccccc12",
            key="pred_smiles",
            label_visibility="collapsed",
        )
    with col_btn:
        analyze = st.button(
            ":material/science: Analyze", key="pred_btn", width="stretch"
        )

    if analyze and smiles_input:
        mol = smiles_to_mol(smiles_input)
        if mol is None:
            st.error("Invalid SMILES string")
            return
        _run_full_analysis(smiles_input, mol)

    elif not analyze:
        results = st.session_state.get("pred_results")
        if results:
            smiles = st.session_state.get("pred_last_smiles", "")
            mol = smiles_to_mol(smiles) if smiles else None
            if mol is not None:
                _display_all_sections(
                    smiles, mol,
                    results["mol_info"],
                    results["lipinski"],
                    results["fp_data"],
                    results["prediction"],
                    results["shap_data"],
                )


# ── Analysis pipeline ─────────────────────────────────────────────────────────

def _run_full_analysis(smiles: str, mol):
    progress = st.progress(0, text="Analyzing molecule…")

    progress.progress(10, text="Computing molecular properties…")
    mol_info = _compute_mol_info(smiles, mol)

    progress.progress(20, text="Checking Lipinski rules…")
    lipinski = _compute_lipinski(mol)

    progress.progress(30, text="Computing fingerprints…")
    fp_data = _compute_fingerprints(mol)

    progress.progress(50, text="Running prediction…")
    prediction = _compute_prediction(mol, fp_data)

    progress.progress(70, text="Computing SHAP explanation…")
    shap_data = _get_shap_data(
        smiles,
        st.session_state.get("rf_model"),
        st.session_state.get("shap_explainer"),
        st.session_state.get("bit_database") or {},
        fp_data,
    )

    progress.progress(100, text="Done!")
    progress.empty()

    st.session_state["pred_last_smiles"] = smiles
    st.session_state["pred_results"] = {
        "mol_info": mol_info,
        "lipinski": lipinski,
        "fp_data": fp_data,
        "prediction": prediction,
        "shap_data": shap_data,
    }

    _display_all_sections(smiles, mol, mol_info, lipinski, fp_data, prediction, shap_data)


# ── Computation functions ─────────────────────────────────────────────────────

def _compute_mol_info(smiles: str, mol) -> dict:
    from rdkit.Chem import Descriptors, rdMolDescriptors
    return {
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "mw": Descriptors.MolWt(mol),
        "n_atoms": mol.GetNumHeavyAtoms(),
        "n_rings": Descriptors.RingCount(mol),
    }


def _compute_lipinski(mol) -> dict:
    from rdkit.Chem import Descriptors
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    rules = [
        {"name": "Molecular Weight", "value": mw, "threshold": 500,
         "unit": "g/mol", "operator": "≤", "pass": mw <= 500},
        {"name": "LogP", "value": logp, "threshold": 5,
         "unit": "", "operator": "≤", "pass": logp <= 5},
        {"name": "H-Bond Donors", "value": hbd, "threshold": 5,
         "unit": "", "operator": "≤", "pass": hbd <= 5},
        {"name": "H-Bond Acceptors", "value": hba, "threshold": 10,
         "unit": "", "operator": "≤", "pass": hba <= 10},
    ]
    return {"rules": rules, "n_passed": sum(1 for r in rules if r["pass"]), "total": 4}


def _compute_fingerprints(mol) -> dict:
    from rdkit.Chem import AllChem, DataStructs
    meta = st.session_state.get("bit_database_meta", {})
    radius = int(meta.get("radius", 3))
    n_bits = int(meta.get("n_bits", 2048))

    maccs = AllChem.GetMACCSKeysFingerprint(mol)
    maccs_on = sum(1 for i in range(167) if maccs.GetBit(i))

    bi = {}
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits, bitInfo=bi)
    fp_arr = np.zeros(n_bits, dtype=np.int32)
    DataStructs.ConvertToNumpyArray(fp, fp_arr)

    return {
        "maccs": maccs,
        "maccs_on": maccs_on,
        "ecfp_bi": bi,
        "ecfp_fp": fp_arr,
        "ecfp_on": len(bi),
        "radius": radius,
        "n_bits": n_bits,
    }


def _compute_prediction(mol, fp_data: dict) -> Optional[dict]:
    model = st.session_state.get("rf_model")
    if model is None:
        return None

    fp_arr = fp_data["ecfp_fp"]
    try:
        prob = model.predict_proba(fp_arr.reshape(1, -1))[0]
    except Exception:
        return None

    p_active = float(prob[1])
    prediction = "Active" if p_active >= 0.5 else "Inactive"

    # Applicability domain
    ad_model = st.session_state.get("ad_model")
    inside_ad = None
    mean_dist = None
    threshold = None
    if ad_model is not None:
        try:
            knn, ad_threshold, _mean, _std = ad_model
            dists, _ = knn.kneighbors(fp_arr.reshape(1, -1))
            mean_dist = float(dists.mean())
            threshold = float(ad_threshold)
            inside_ad = mean_dist <= threshold
        except Exception:
            pass

    # RF tree std
    rf_std = None
    if hasattr(model, "estimators_"):
        try:
            tree_preds = np.array([
                t.predict_proba(fp_arr.reshape(1, -1))[0, 1]
                for t in model.estimators_
            ])
            rf_std = float(tree_preds.std())
        except Exception:
            pass

    # Training-set similarity — Tanimoto vs all training fps stored in kNN model
    max_tanimoto = None
    in_training_set = None
    if ad_model is not None:
        try:
            knn, _thr, _m, _s = ad_model
            train_fps = getattr(knn, "_fit_X", None)
            if train_fps is not None and len(train_fps) > 0:
                fp_bin = fp_arr.astype(np.float32)
                intersection = train_fps.dot(fp_bin)          # (n_train,)
                sum_q = float(fp_bin.sum())
                sum_t = train_fps.sum(axis=1)                 # (n_train,)
                union = sum_q + sum_t - intersection
                tanimoto = np.where(union > 0, intersection / union, 0.0)
                max_tanimoto = float(tanimoto.max())
                # Threshold 0.999 → identical fingerprint (same molecule
                # regardless of SMILES notation); Tanimoto is SMILES-independent.
                in_training_set = max_tanimoto >= 0.999
        except Exception:
            pass

    return {
        "p_active": p_active,
        "p_inactive": float(prob[0]),
        "prediction": prediction,
        "mean_knn_dist": mean_dist,
        "ad_threshold": threshold,
        "inside_ad": inside_ad,
        "rf_std": rf_std,
        "max_tanimoto": max_tanimoto,
        "in_training_set": in_training_set,
    }


def _get_shap_data(smiles: str, model, explainer, bit_db: dict, fp_data: dict) -> Optional[dict]:
    """Compute SHAP, using session_state as a per-SMILES cache."""
    cache_key = f"_pred_shap_{smiles}"
    cached = st.session_state.get(cache_key)
    if cached is not None:
        return cached
    result = _compute_shap(smiles, model, explainer, bit_db, fp_data)
    st.session_state[cache_key] = result
    return result


def _compute_shap(smiles: str, model, explainer, bit_db: dict, fp_data: dict) -> Optional[dict]:
    if model is None or explainer is None:
        return None

    from rdkit import Chem

    fp_arr = fp_data["ecfp_fp"]
    bi = fp_data["ecfp_bi"]
    mol = smiles_to_mol(smiles)

    try:
        sv = explainer.shap_values(fp_arr.reshape(1, -1))
        if isinstance(sv, list):
            shap_vals = sv[1][0]
            exp_val = (
                explainer.expected_value[1]
                if isinstance(explainer.expected_value, (list, np.ndarray))
                else float(explainer.expected_value)
            )
        elif hasattr(sv, "ndim") and sv.ndim == 3:
            shap_vals = sv[0, :, 1]
            exp_val = (
                explainer.expected_value[1]
                if isinstance(explainer.expected_value, (list, np.ndarray))
                else float(explainer.expected_value)
            )
        else:
            shap_vals = sv[0]
            exp_val = float(explainer.expected_value)
    except Exception:
        return None

    top_idx = np.argsort(np.abs(shap_vals))[::-1][:15]
    features = []
    for bit_pos in top_idx:
        bit_pos = int(bit_pos)
        mol_subs = []
        if mol is not None and bit_pos in bi:
            for atom_idx, rad in bi[bit_pos]:
                try:
                    if rad == 0:
                        s = mol.GetAtomWithIdx(atom_idx).GetSymbol()
                    else:
                        env = Chem.FindAtomEnvironmentOfRadiusN(mol, rad, atom_idx)
                        amap = {}
                        submol = Chem.PathToSubmol(mol, env, atomMap=amap)
                        if submol.GetNumAtoms() > 0:
                            s = Chem.MolToSmiles(submol)
                        else:
                            continue
                    mol_subs.append(s)
                except Exception:
                    continue

        features.append({
            "bit": bit_pos,
            "shap": float(shap_vals[bit_pos]),
            "bit_on": int(fp_arr[bit_pos]),
            "mol_subs": mol_subs,
            "db": bit_db.get(bit_pos),
        })

    return {
        "shap_vals": shap_vals,
        "expected_value": float(exp_val),
        "top_features": features,
    }


# ── Display functions ─────────────────────────────────────────────────────────

def _find_new_atoms(current_smiles: str, prev_smiles: str) -> list:
    """Return atom indices in current mol NOT in the MCS with prev mol (yellow highlight)."""
    try:
        from rdkit import Chem as _Chem
        from rdkit.Chem import rdFMCS
        mol_curr = _Chem.MolFromSmiles(current_smiles)
        mol_prev = _Chem.MolFromSmiles(prev_smiles)
        if mol_curr is None or mol_prev is None:
            return []
        mcs = rdFMCS.FindMCS(
            [mol_curr, mol_prev], timeout=2,
            ringMatchesRingOnly=False, completeRingsOnly=False,
        )
        if mcs.numAtoms == 0:
            return list(range(mol_curr.GetNumAtoms()))
        mcs_mol = _Chem.MolFromSmarts(mcs.smartsString)
        if mcs_mol is None:
            return []
        match = mol_curr.GetSubstructMatch(mcs_mol)
        mcs_set = set(match)
        return [i for i in range(mol_curr.GetNumAtoms()) if i not in mcs_set]
    except Exception:
        return []


def _render_structure_with_highlight(smiles: str, mol, mol_info: dict,
                                     prediction: Optional[dict] = None):
    """Molecule image with yellow highlight on atoms added vs previous step."""
    from rdkit import Chem as _Chem
    from rdkit.Chem import AllChem, Draw
    from rdkit.Chem.Draw import rdMolDraw2D

    design_history = st.session_state.get("design_history", [])
    new_atom_idxs: list = []
    if design_history:
        new_atom_idxs = _find_new_atoms(smiles, design_history[-1]["smiles"])

    AllChem.Compute2DCoords(mol)

    rendered = False
    if new_atom_idxs:
        atom_colors = {i: (1.0, 0.85, 0.0, 0.6) for i in new_atom_idxs}
        bond_colors: dict = {}
        for bond in mol.GetBonds():
            a1, a2 = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            if a1 in atom_colors and a2 in atom_colors:
                bond_colors[bond.GetIdx()] = (1.0, 0.85, 0.0, 0.6)
        for DrawerClass, fmt in [
            (rdMolDraw2D.MolDraw2DCairo, "png"),
            (rdMolDraw2D.MolDraw2DSVG,  "svg"),
        ]:
            try:
                drawer = DrawerClass(320, 270)
                drawer.drawOptions().useBWAtomPalette()
                drawer.DrawMolecule(
                    mol,
                    highlightAtoms=new_atom_idxs,
                    highlightAtomColors=atom_colors,
                    highlightBonds=list(bond_colors.keys()),
                    highlightBondColors=bond_colors,
                )
                drawer.FinishDrawing()
                data = drawer.GetDrawingText()
                if fmt == "png":
                    st.image(data, width="stretch")
                else:
                    st.markdown(
                        f'<div style="background:#f5f3ee;border-radius:8px;">{data}</div>',
                        unsafe_allow_html=True,
                    )
                rendered = True
                break
            except Exception:
                continue

    if not rendered:
        img = Draw.MolToImage(mol, size=(320, 270))
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        st.image(buf, width="stretch")

    st.markdown(
        f"<div style='font-size:0.75rem;color:#8890c4;word-break:break-all;"
        f"line-height:1.5;margin-top:0.15rem;font-variant-numeric:tabular-nums;'>{smiles}</div>"
        f"<div style='font-size:0.875rem;color:#eceaf8;margin-top:0.2rem;line-height:1.4;'>"
        f"<b>{mol_info['formula']}</b> · MW {mol_info['mw']:.1f} · "
        f"{mol_info['n_atoms']} atoms · {mol_info['n_rings']} rings</div>",
        unsafe_allow_html=True,
    )

    # ── Compact prediction + AD + training-set badges ─────────────────────────
    if prediction:
        badges = []

        # Prediction badge
        pred_lbl = prediction.get("prediction")
        p_active  = prediction.get("p_active")
        if pred_lbl is not None and p_active is not None:
            p_col = "#50c896" if pred_lbl == "Active" else "#e05070"
            badges.append(
                f'<span style="background:{p_col};color:#fff;font-size:0.75rem;'
                f'font-weight:600;padding:0.1rem 0.45rem;border-radius:4px;'
                f'white-space:nowrap;font-variant-numeric:tabular-nums;">'
                f'{pred_lbl} ({p_active:.2f})</span>'
            )

        # AD badge
        inside_ad = prediction.get("inside_ad")
        if inside_ad is not None:
            ad_col  = "#50c896" if inside_ad else "#d4804a"
            ad_text = "In AD" if inside_ad else "Out AD"
            badges.append(
                f'<span style="background:{ad_col};color:#fff;font-size:0.75rem;'
                f'padding:0.1rem 0.45rem;border-radius:4px;white-space:nowrap;">'
                f'{ad_text}</span>'
            )

        # Training-set badge (Tanimoto-based — SMILES-notation-independent)
        max_t = prediction.get("max_tanimoto")
        in_ts = prediction.get("in_training_set")
        if max_t is not None:
            if in_ts:
                ts_col  = "#e05070"
                ts_text = f"⚠ In training (Tc={max_t:.3f})"
            elif max_t >= 0.85:
                ts_col  = "#d4804a"
                ts_text = f"≈ Training (Tc={max_t:.3f})"
            else:
                ts_col  = "#283058"
                ts_text = f"Novel (Tc={max_t:.3f})"
            badges.append(
                f'<span style="background:{ts_col};color:#eceaf8;font-size:0.75rem;'
                f'padding:0.1rem 0.45rem;border-radius:4px;white-space:nowrap;'
                f'font-variant-numeric:tabular-nums;">'
                f'{ts_text}</span>'
            )

        if badges:
            st.markdown(
                "<div style='display:flex;gap:0.35rem;flex-wrap:wrap;"
                "margin-top:0.3rem;'>" + "".join(badges) + "</div>",
                unsafe_allow_html=True,
            )

    if new_atom_idxs:
        st.caption("🟡 Yellow = atoms added vs previous step")


def _render_prediction_ad_panel(prediction: Optional[dict], lipinski: dict):
    """Right-column analysis box: Lipinski + Prediction + AD in a single container."""
    with st.container(border=True):
        # ── Lipinski bar ──────────────────────────────────────────────────────
        n = lipinski["n_passed"]
        total = lipinski["total"]
        lip_color = "#50c896" if n == total else "#d4804a" if n >= 3 else "#e05070"
        pct = n / total * 100
        verdict = "Drug-like ✓" if n == total else f"Lipinski {n}/{total} rules"
        st.markdown(
            f"<div style='font-size:0.875rem;color:{lip_color};font-weight:600;"
            f"font-family:Space Grotesk,sans-serif;margin-bottom:0.2rem;line-height:1.3;'>{verdict}</div>"
            f"<div style='background:var(--color-bg);border-radius:4px;height:5px;margin-bottom:0.35rem;'>"
            f"<div style='background:{lip_color};width:{pct:.0f}%;height:100%;border-radius:4px;'>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        lip_row = st.columns(2)
        for idx, rule in enumerate(lipinski["rules"]):
            icon = "✅" if rule["pass"] else "❌"
            val_str = (f'{rule["value"]:.1f}' if isinstance(rule["value"], float)
                       else str(rule["value"]))
            with lip_row[idx % 2]:
                st.markdown(
                    f"<div style='font-size:0.75rem;color:#8890c4;margin-bottom:0.05rem;line-height:1.4;'>"
                    f"{icon} {rule['name']}: <b style='color:#eceaf8;'>{val_str}</b>"
                    f" <span style='color:#484c7a;'>({rule['operator']} {rule['threshold']})</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        st.markdown(
            "<hr style='border:none;border-top:1px solid #1c2040;margin:0.4rem 0;'>",
            unsafe_allow_html=True,
        )
        # ── Prediction + AD ───────────────────────────────────────────────────
        if prediction:
            render_prediction_card(
                prediction["prediction"],
                prediction["p_active"],
                prediction["p_inactive"],
            )
            if prediction.get("inside_ad") is not None:
                render_ad_badge(
                    prediction["inside_ad"],
                    prediction["mean_knn_dist"],
                    prediction["ad_threshold"],
                    rf_std=prediction.get("rf_std"),
                )
            else:
                st.caption("No AD model.")
                if prediction.get("rf_std") is not None:
                    st.markdown(
                        f"<div style='font-size:0.875rem;color:#8890c4;line-height:1.4;'>"
                        f"RF std: {prediction['rf_std']:.4f}</div>",
                        unsafe_allow_html=True,
                    )

            # ── Training-set similarity badge ─────────────────────────────────
            max_t = prediction.get("max_tanimoto")
            in_ts = prediction.get("in_training_set")
            if max_t is not None:
                if in_ts:
                    ts_color = "#e05070"
                    ts_icon  = "⚠️"
                    ts_text  = f"Already in training set (Tc={max_t:.3f})"
                    ts_hint  = ("Fingerprint identical to a training compound (Tanimoto≥0.999) — "
                                "the molecule is already present regardless of SMILES notation. "
                                "Prediction may be memorised.")
                elif max_t >= 0.85:
                    ts_color = "#d4804a"
                    ts_icon  = "⚡"
                    ts_text  = f"Very similar to training (Tc={max_t:.3f})"
                    ts_hint  = "High Tanimoto similarity to a training compound — prediction is interpolative."
                else:
                    ts_color = "#50c896"
                    ts_icon  = "✓"
                    ts_text  = f"Novel vs training (Tc={max_t:.3f})"
                    ts_hint  = "Low Tanimoto similarity to training set — genuinely novel chemical space."
                st.markdown(
                    f"<div style='margin-top:0.35rem;font-size:0.875rem;"
                    f"color:{ts_color};font-family:Space Grotesk,sans-serif;'  "
                    f"title='{ts_hint}'>{ts_icon} {ts_text}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No model loaded.")


# ── MACCS highlight color palette (visually distinct on dark backgrounds) ─────

_MACCS_COLORS = [
    (0.91, 0.30, 0.24),  # #e74c3c  red
    (0.20, 0.60, 0.86),  # #3498db  blue
    (0.18, 0.80, 0.44),  # #2ecc71  green
    (0.95, 0.61, 0.07),  # #f39c12  amber
    (0.61, 0.35, 0.71),  # #9b59b6  purple
    (0.10, 0.74, 0.61),  # #1abc9c  teal
    (0.95, 0.37, 0.53),  # #f25f87  pink
    (0.18, 0.63, 0.78),  # #2ea0c7  cyan-blue
]


def _render_maccs_simple(maccs_fp, smiles: str) -> None:
    """Pill grid overview + two-column inspect view without descriptions or LLM."""
    # ── Pill grid ─────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .maccs-grid { display: flex; flex-wrap: wrap; gap: 3px; margin: 0.5rem 0; }
    .maccs-key {
        padding: 3px 6px; font-size: 0.6875rem;   /* --text-xs: 11px */
        font-family: 'Space Grotesk', sans-serif;
        border-radius: 4px; cursor: default; font-weight: 600;
        line-height: 1.2; transition: transform 0.15s; white-space: nowrap;
    }
    .maccs-key:hover { transform: scale(1.2); z-index: 10;
                       box-shadow: 0 2px 8px rgba(0,0,0,0.5); }
    .maccs-on  { background-color: #50c896; color: #090b18; }
    .maccs-off { background-color: #1c2040; color: #484c7a; }
    </style>
    """, unsafe_allow_html=True)

    grid_html = '<div class="maccs-grid">'
    for i in range(167):
        cls = "maccs-on" if maccs_fp.GetBit(i) else "maccs-off"
        grid_html += f'<div class="maccs-key {cls}" title="MACCS Key {i}">{i}</div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    active_keys = [i for i in range(167) if maccs_fp.GetBit(i)]
    if not active_keys:
        st.caption("No MACCS keys active for this molecule.")
        return

    # ── Selectbox + detail view ────────────────────────────────────────────────
    selected = st.selectbox(
        "Inspect MACCS key:",
        options=active_keys,
        format_func=lambda x: f"Key {x}",
        key="pred_maccs_sel",
    )
    _render_maccs_key_detail(int(selected), smiles)


def _render_maccs_key_detail(key_idx: int, smiles: str) -> None:
    """Two-column: left (~70%) = highlighted molecule image, right (~30%) = label + SMARTS."""
    from rdkit import Chem
    from rdkit.Chem import Draw

    smarts = get_maccs_smarts(key_idx)

    col_img, col_info = st.columns([0.7, 0.3])

    with col_img:
        rendered = False

        if smiles and smarts and smarts != "?":
            try:
                mol = Chem.MolFromSmiles(smiles)
                pattern = Chem.MolFromSmarts(smarts)

                if mol is not None and pattern is not None:
                    matches = mol.GetSubstructMatches(pattern)

                    highlight_atoms: list[int] = []
                    highlight_bonds: list[int] = []
                    atom_colors: dict[int, tuple] = {}
                    bond_colors: dict[int, tuple] = {}

                    for match_idx, match in enumerate(matches):
                        color = _MACCS_COLORS[match_idx % len(_MACCS_COLORS)]
                        match_set = set(match)
                        for atom_idx in match:
                            if atom_idx not in atom_colors:
                                highlight_atoms.append(atom_idx)
                                atom_colors[atom_idx] = color
                        for bond in mol.GetBonds():
                            a1, a2 = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
                            if a1 in match_set and a2 in match_set:
                                bidx = bond.GetIdx()
                                if bidx not in bond_colors:
                                    highlight_bonds.append(bidx)
                                    bond_colors[bidx] = color

                    img = Draw.MolToImage(
                        mol, size=(400, 300),
                        highlightAtoms=highlight_atoms or None,
                        highlightAtomColors=atom_colors or None,
                        highlightBonds=highlight_bonds or None,
                        highlightBondColors=bond_colors or None,
                    )
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    buf.seek(0)
                    st.image(buf, width="stretch")

                    if matches:
                        n = len(matches)
                        note = f"{n} occurrence{'s' if n > 1 else ''} highlighted"
                        if n > 1:
                            note += " in distinct colors"
                        st.caption(note)
                    else:
                        st.caption("Pattern not matched in this molecule")

                    rendered = True
            except Exception:
                pass

        if not rendered:
            # Fallback: render the SMARTS pattern itself, no highlights
            try:
                if smarts and smarts != "?":
                    mol_q = Chem.MolFromSmarts(smarts)
                    if mol_q is not None:
                        img = Draw.MolToImage(mol_q, size=(400, 300))
                        buf = BytesIO()
                        img.save(buf, format="PNG")
                        buf.seek(0)
                        st.image(buf, width="stretch")
                    else:
                        st.caption(f"Cannot visualize key {key_idx}")
                else:
                    st.caption(f"No SMARTS pattern defined for key {key_idx}")
            except Exception:
                st.caption(f"Cannot visualize key {key_idx}")

    with col_info:
        st.markdown(f"**Key {key_idx}**")
        if smarts and smarts != "?":
            st.code(smarts, language=None)
        else:
            st.caption("No SMARTS defined")


def _display_all_sections(smiles, mol, mol_info, lipinski, fp_data, prediction, shap_data):
    bit_db = st.session_state.get("bit_database") or {}
    shap_vals = shap_data["shap_vals"] if shap_data else None

    # ── Row 1: Structure image (left) │ Prediction + AD panel (right) ─────────
    col_struct, col_info = st.columns([1.2, 1])
    with col_struct:
        _render_structure_with_highlight(smiles, mol, mol_info, prediction=prediction)
    with col_info:
        _render_prediction_ad_panel(prediction, lipinski)

    st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)

    # ── Advanced Details (collapsed) ──────────────────────────────────────────
    radius = fp_data.get("radius", 3)
    with st.expander("🔬 Advanced Details", expanded=False):
        st.markdown("**Lipinski Rule of Five**")
        _display_lipinski_section(lipinski)
        st.divider()
        st.markdown("**SHAP Explanation**")
        _display_shap_section(shap_data, bit_db)
        st.divider()
        st.markdown("**MACCS Keys**")
        st.caption(f"Keys ON: {fp_data['maccs_on']} / 166")
        _render_maccs_simple(fp_data["maccs"], smiles)
        st.divider()
        st.markdown("**ECFP Fingerprint**")
        st.caption(
            f"Bits ON: {fp_data['ecfp_on']} / {fp_data['n_bits']} "
            f"(ECFP{2 * radius})"
        )
        render_ecfp_grid(fp_data["ecfp_bi"], bit_db, shap_vals, key_prefix="pred_")
        render_bit_detail(bit_db, shap_vals, key_prefix="pred_")

    _render_help_button()


# ── Section renderers (used inside Advanced Details) ──────────────────────────

def _display_lipinski_section(lipinski: dict):
    for rule in lipinski["rules"]:
        icon = "✅" if rule["pass"] else "❌"
        color = "#50c896" if rule["pass"] else "#e05070"
        unit = f' {rule["unit"]}' if rule["unit"] else ""
        val_str = (f'{rule["value"]:.2f}' if isinstance(rule["value"], float)
                   else str(rule["value"]))
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.5rem;"
            f"margin-bottom:0.3rem;font-size:0.875rem;line-height:1.4;'>"
            f"<span>{icon}</span>"
            f"<span style='color:#eceaf8;'>{rule['name']} = </span>"
            f"<span style='color:{color};font-weight:600;"
            f"font-family:'Space Grotesk',sans-serif;'>{val_str}{unit}</span>"
            f"<span style='color:#606490;'>({rule['operator']} {rule['threshold']})</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    n = lipinski["n_passed"]
    total = lipinski["total"]
    pct = n / total * 100
    bar_color = "#50c896" if n == total else "#d4804a" if n >= 3 else "#e05070"
    verdict = "Drug-like" if n == total else f"{n}/{total} rules passed"
    st.markdown(
        f"<div style='margin-top:0.5rem;'>"
        f"<div style='font-family:Space Grotesk,sans-serif;font-size:0.875rem;"
        f"color:{bar_color};font-weight:600;line-height:1.3;'>{verdict}</div>"
        f"<div style='background:#1c2040;border-radius:4px;height:8px;margin-top:0.3rem;'>"
        f"<div style='background:{bar_color};width:{pct:.1f}%;height:100%;border-radius:4px;'>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )


def _display_shap_section(shap_data: Optional[dict], bit_db: dict):
    if shap_data is None:
        st.warning("No model or SHAP explainer available.")
        return

    _display_waterfall(shap_data)
    st.markdown("")
    _display_shap_substructures(shap_data)
    st.markdown("")
    _display_shap_feature_detail(shap_data, bit_db)


def _display_waterfall(shap_data: dict):
    """Custom dark-themed waterfall plot for top SHAP features."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    features = shap_data["top_features"][:10]
    expected = shap_data["expected_value"]

    # Reverse so most important is on top
    labels = [f"ECFP6_{f['bit']}" for f in reversed(features)]
    values = [f["shap"] for f in reversed(features)]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafafa")

    cumulative = expected
    for i, (label, val) in enumerate(zip(labels, values)):
        color = "#23775a" if val > 0 else "#b83245"
        ax.barh(i, val, left=cumulative, color=color, height=0.6,
                edgecolor="#e0e0e0", linewidth=0.5)
        text_color = "#ffffff" if abs(val) > 0.015 else "#1e1c24"
        ax.text(cumulative + val / 2, i, f"{val:+.4f}",
                ha="center", va="center", fontsize=7, color=text_color,
                fontweight="bold", fontfamily="sans-serif")
        cumulative += val

    ax.axvline(expected, color="#a8a8b0", linestyle="--", linewidth=0.8,
               label=f"Base: {expected:.3f}")
    final = expected + sum(values)
    ax.axvline(final, color="#b86020", linestyle="-", linewidth=1.5,
               label=f"Output: {final:.3f}")

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8, color="#1e1c24", fontfamily="sans-serif")
    ax.set_xlabel("SHAP value (contribution to P(active))",
                  color="#65656f", fontsize=9, fontfamily="sans-serif")
    ax.tick_params(axis="x", colors="#65656f", labelsize=8)
    ax.legend(fontsize=8, facecolor="#f4f4f4", edgecolor="#e0e0e0", labelcolor="#1e1c24")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#e0e0e0")
    ax.spines["left"].set_color("#e0e0e0")
    ax.grid(axis="x", alpha=0.4, color="#e0e0e0")
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="PNG", dpi=150, facecolor="#ffffff", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    st.image(buf, width="stretch")


def _display_shap_substructures(shap_data: dict):
    """Show substructure grids grouped by SHAP direction."""
    from rdkit.Chem import Draw

    features = shap_data["top_features"]
    toward_active = [f for f in features if f["shap"] > 0]
    toward_inactive = [f for f in features if f["shap"] < 0]

    if toward_active:
        st.markdown(
            "<div style='color:#50c896;font-family:Space Grotesk,sans-serif;"
            "font-size:0.875rem;font-weight:500;margin-bottom:0.3rem;line-height:1.3;'>"
            "▲ Features pushing toward ACTIVE</div>",
            unsafe_allow_html=True,
        )
        _render_substruct_card_grid(
            _shap_features_to_card_items(toward_active, "#50c896")
        )

    if toward_inactive:
        st.markdown(
            "<div style='color:#e05070;font-family:Space Grotesk,sans-serif;"
            "font-size:0.875rem;font-weight:500;margin-top:0.5rem;margin-bottom:0.3rem;line-height:1.3;'>"
            "▼ Features pushing toward INACTIVE</div>",
            unsafe_allow_html=True,
        )
        _render_substruct_card_grid(
            _shap_features_to_card_items(toward_inactive, "#e05070")
        )


def _build_shap_mol_grid(features: list):
    """Build (mols, legends) for a SHAP substructure grid image."""
    mols, legends = [], []
    for f in features:
        sub_smi = None
        if f["bit_on"] == 1 and f["mol_subs"]:
            sub_smi = f["mol_subs"][0]
        elif f["bit_on"] == 0 and f["db"]:
            # Use dominant substructure from training database
            sub_smi = f["db"].get("dominant_substructure")
            if sub_smi is None:
                subs = f["db"].get("substructures", {})
                if subs:
                    items = (subs.most_common(1) if hasattr(subs, "most_common")
                             else sorted(subs.items(), key=lambda x: x[1], reverse=True)[:1])
                    if items:
                        sub_smi = items[0][0]

        if sub_smi:
            mol = smiles_to_mol(str(sub_smi))
            if mol:
                if f["bit_on"] == 1:
                    on_label = "ON"
                else:
                    on_label = "ABSENT (training)"
                mols.append(mol)
                legends.append(f"ECFP6_{f['bit']} ({on_label})\n{f['shap']:+.4f}")
    return mols, legends


def _display_shap_feature_detail(shap_data: dict, bit_db: dict):
    """Dropdown to inspect individual SHAP features with substructure images."""
    from rdkit.Chem import Draw

    features = shap_data["top_features"]
    options = [f"ECFP6_{f['bit']}  (SHAP={f['shap']:+.4f})" for f in features]

    selected = st.selectbox("Inspect feature:", options, key="pred_shap_sel")
    if not selected:
        return

    idx = options.index(selected)
    f = features[idx]
    bit_idx = f["bit"]

    col_info, col_img = st.columns([1, 1])

    with col_info:
        direction = "→ Active" if f["shap"] > 0 else "→ Inactive"
        on_label = "ON" if f["bit_on"] == 1 else "OFF (absent)"
        st.markdown(
            f"**ECFP6\_{bit_idx}**  \n"
            f"SHAP: `{f['shap']:+.6f}` {direction}  \n"
            f"Bit status: {on_label}"
        )
        if f["bit_on"] == 1 and f["mol_subs"]:
            st.markdown(f"In this molecule: `{f['mol_subs'][0]}`")

        db = f["db"]
        if db:
            active_freq = db.get("active_freq", "?")
            inactive_freq = db.get("inactive_freq", "?")
            st.markdown(
                f"Training: {active_freq} active, {inactive_freq} inactive  \n"
                f"Active ratio: {db.get('active_ratio', 0):.1%}  \n"
                f"Substructures: {db.get('n_unique_substructures', '?')}  \n"
                f"Dominance: {db.get('dominance', 0):.1f}%"
            )

    with col_img:
        db = bit_db.get(bit_idx)
        if db and "substructures" in db:
            st.markdown(
                "<div style='color:#606490;font-size:0.75rem;margin-bottom:0.2rem;'>"
                "Substructures in training data (by frequency):</div>",
                unsafe_allow_html=True,
            )
            subs_dict = db["substructures"]
            items = (
                subs_dict.most_common(5)
                if hasattr(subs_dict, "most_common")
                else sorted(subs_dict.items(), key=lambda x: x[1], reverse=True)[:5]
            )
            total = max(sum(subs_dict.values()), 1)
            _render_substruct_card_grid([
                {
                    "smiles": str(sub_smi),
                    "label": f"{count / total * 100:.1f}%",
                    "sublabel": "from training data",
                    "border_color": "#283058",
                }
                for sub_smi, count in items
            ], cols=3)


# ── Floating help button ──────────────────────────────────────────────────────

def _render_help_button():
    """Render a fixed floating ? button with a SMARTS bond notation guide modal."""
    if "_help_bond_images" not in st.session_state:
        from rdkit import Chem
        from rdkit.Chem import Draw

        bond_specs = [
            ("CC",       "img_b64_single"),
            ("C=C",      "img_b64_double"),
            ("C#N",      "img_b64_triple"),
            ("c1ccccc1", "img_b64_arom"),
            ("C1CCCCC1", "img_b64_ring"),
        ]
        imgs = {}
        for smi, key in bond_specs:
            try:
                mol = Chem.MolFromSmiles(smi)
                if mol:
                    img = Draw.MolToImage(mol, size=(160, 120))
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    imgs[key] = base64.b64encode(buf.getvalue()).decode()
                else:
                    imgs[key] = ""
            except Exception:
                imgs[key] = ""
        st.session_state["_help_bond_images"] = imgs

    imgs = st.session_state["_help_bond_images"]
    img_b64_single = imgs.get("img_b64_single", "")
    img_b64_double = imgs.get("img_b64_double", "")
    img_b64_triple = imgs.get("img_b64_triple", "")
    img_b64_arom   = imgs.get("img_b64_arom", "")
    img_b64_ring   = imgs.get("img_b64_ring", "")

    bond_entries = [
        ("-", "Single bond",  img_b64_single),
        ("=", "Double bond",  img_b64_double),
        ("#", "Triple bond",  img_b64_triple),
        (":", "Aromatic bond", img_b64_arom),
        ("@", "Ring bond",    img_b64_ring),
    ]

    cards_html = ""
    for sym, label, b64 in bond_entries:
        cards_html += f'''
    <div style="background:#141728;border-radius:6px;padding:0.5rem;text-align:center;">
        <img src="data:image/png;base64,{b64}" style="width:100%;border-radius:4px;background:#f5f3ee;"/>
        <div style="color:#50c896;font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:bold;margin-top:0.3rem;">{sym}</div>
        <div style="color:#8890c4;font-size:0.7rem;">{label}</div>
    </div>'''

    any_bond_card = '''
    <div style="background:#141728;border-radius:6px;padding:0.5rem;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:80px;">
        <div style="color:#50c896;font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:bold;">~</div>
        <div style="color:#8890c4;font-size:0.7rem;">Any bond</div>
    </div>'''

    html = f"""
<style>
#_help_fab{{position:fixed;bottom:24px;right:24px;width:46px;height:46px;
    border-radius:50%;background:#e0a85a;color:#090b18;font-size:20px;
    font-weight:bold;border:none;cursor:pointer;z-index:99999;
    box-shadow:0 3px 10px rgba(0,0,0,0.5);font-family:'Space Grotesk',sans-serif;
    display:flex;align-items:center;justify-content:center;}}
#_help_fab:hover{{background:#c89040;}}
#_help_modal{{display:none;position:fixed;bottom:82px;right:24px;width:420px;
    max-height:72vh;overflow-y:auto;background:#0e1128;
    border:1px solid #283058;border-radius:12px;padding:1rem;z-index:99998;
    box-shadow:0 8px 32px rgba(0,0,0,0.6);}}
#_help_modal.open{{display:block;}}
#_help_modal h4{{color:#eceaf8;font-family:'Space Grotesk',sans-serif;
    font-size:1rem;font-weight:600;margin:0 0 0.2rem 0;line-height:1.2;}}
#_help_modal .close-hint{{color:#606490;font-size:0.75rem;margin-bottom:0.8rem;}}
#_help_modal .bond-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:0.4rem;margin-bottom:0.8rem;}}
#_help_modal .section-label{{color:#8890c4;font-size:0.75rem;
    font-family:'Space Grotesk',sans-serif;font-weight:600;letter-spacing:0.06em;
    margin:0.6rem 0 0.3rem 0;border-top:1px solid #1c2040;padding-top:0.5rem;}}
#_help_modal .smarts-list{{font-size:0.75rem;color:#8890c4;line-height:1.8;}}
#_help_modal .smarts-list code{{color:#50c896;background:#141728;
    padding:0.1rem 0.3rem;border-radius:3px;font-size:0.75rem;font-family:'Space Grotesk',sans-serif;}}
#_help_modal .footer-note{{color:#606490;font-size:0.6875rem;
    margin-top:0.8rem;border-top:1px solid #1c2040;padding-top:0.5rem;}}
</style>
<button id="_help_fab" onclick="(function(){{var m=document.getElementById('_help_modal');m.classList.toggle('open');}})()">?</button>
<div id="_help_modal">
  <h4>Bond Notation Guide (SMARTS)</h4>
  <div class="close-hint">Click ? again to close</div>
  <div class="bond-grid">
    {cards_html}
    {any_bond_card}
  </div>
  <div class="section-label">Atom notation</div>
  <div class="smarts-list">
    <code>[#6]</code> any carbon atom<br>
    <code>[#7]</code> any nitrogen atom<br>
    <code>[#8]</code> any oxygen atom<br>
    <code>[!H]</code> non-hydrogen atom<br>
    <code>[r5]</code> atom in a 5-membered ring<br>
    <code>[r6]</code> atom in a 6-membered ring
  </div>
  <div class="footer-note">
    SMARTS strings shown below each substructure image can be copied by clicking them.
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
