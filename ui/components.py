"""Shared UI rendering components — used by Visualizer and Prediction pages."""

import streamlit as st
from io import BytesIO
from typing import Optional


# ── Molecule parsing ──────────────────────────────────────────────────────────

def smiles_to_mol(smiles: str):
    """Parse SMILES, falling back to SMARTS for open-valence bitInfo fragments."""
    from rdkit import Chem
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is not None:
        return mol
    return Chem.MolFromSmarts(smiles)


# ── Reliability helpers ───────────────────────────────────────────────────────

def reliability_color(dominance_pct: float) -> str:
    """Color token based on dominance of top substructure (0–100%)."""
    if dominance_pct >= 80:
        return "var(--color-success)"
    elif dominance_pct >= 60:
        return "var(--color-warning-alt)"
    elif dominance_pct >= 40:
        return "var(--color-warning)"
    return "var(--color-danger)"


def reliability_label(dominance_pct: float, n_subs: int) -> str:
    if n_subs <= 1:
        return "Unique"
    suffix = " !" if dominance_pct < 40 else ""
    return f"{n_subs} subs · {dominance_pct:.0f}% dominant{suffix}"


# ── MACCS helpers ─────────────────────────────────────────────────────────────

# Descriptions derived from SMARTS patterns — guaranteed to match the image.
# Covers the most common single-atom and simple patterns found in RDKit's MACCS keys.
_SMARTS_TO_DESC: dict = {
    "?": "Isotope present (no SMARTS pattern defined)",
    # single-atom atoms
    "[#16]": "Sulfur present",
    "[#7]": "Nitrogen present",
    "[#8]": "Oxygen present",
    "[#6]": "Carbon present",
    "[#15]": "Phosphorus present",
    "[#14]": "Silicon present",
    "[#34]": "Selenium present",
    "[#9]": "Fluorine present",
    "[#17]": "Chlorine present",
    "[#35]": "Bromine present",
    "[#53]": "Iodine present",
    "[F,Cl,Br,I]": "Halogen present",
    "[F,Cl,Br,I,S]": "Halogen or sulfur present",
    # aromatic atoms
    "[#7;a]": "Aromatic nitrogen",
    "[n]": "Aromatic nitrogen",
    "[nH]": "Aromatic nitrogen (NH)",
    "[n;H1]": "Aromatic nitrogen (NH)",
    "[#16;a]": "Aromatic sulfur",
    "[s]": "Aromatic sulfur",
    "[#8;a]": "Aromatic oxygen",
    "[o]": "Aromatic oxygen",
    "[a]": "Any aromatic atom",
    "[c]": "Aromatic carbon",
    # ring membership
    "[R]": "Atom in ring",
    "[R2]": "Atom in 2+ rings",
    "[R3]": "Atom in 3+ rings",
    "[r5]": "Atom in 5-membered ring",
    "[r6]": "Atom in 6-membered ring",
    # charge
    "[+]": "Positively charged atom",
    "[-]": "Negatively charged atom",
    "[+1]": "Positively charged atom",
    "[-1]": "Negatively charged atom",
    "[#7+]": "Positively charged nitrogen",
    "[#8-]": "Negatively charged oxygen",
    # hydrogen count
    "[#8H]": "Oxygen with hydrogen (hydroxyl)",
    "[OX2H]": "Hydroxyl group",
    "[OX1H0]": "Carbonyl oxygen",
    "[#7H]": "Nitrogen with hydrogen (amine)",
    "[NH2]": "Primary amine",
    "[NH1]": "Secondary amine",
    "[NH0]": "Tertiary amine",
}


def get_maccs_smarts(key_idx: int) -> Optional[str]:
    """Return the SMARTS pattern for a MACCS key, or None if unavailable."""
    try:
        from rdkit.Chem import MACCSkeys
        val = MACCSkeys.smartsPatts.get(key_idx)
        if val is None:
            return None
        return val[0] if isinstance(val, tuple) else str(val)
    except Exception:
        return None


def _maccs_description(smarts: Optional[str], key_idx: int) -> str:
    """
    Return a description that is guaranteed consistent with the SMARTS pattern.

    Priority:
    1. Exact SMARTS match in _SMARTS_TO_DESC (always correct)
    2. MACCS_DESCRIPTIONS[key_idx] as fallback (may be from a different numbering
       reference — shown as supplementary)
    3. SMARTS itself as last resort
    """
    from descriptors.maccs_descriptions import MACCS_DESCRIPTIONS

    if not smarts or smarts == "?":
        return MACCS_DESCRIPTIONS.get(key_idx, "No description available")

    # Exact match in our SMARTS lookup (guaranteed consistent with image)
    if smarts in _SMARTS_TO_DESC:
        return _SMARTS_TO_DESC[smarts]

    # Fallback: traditional description (may differ from SMARTS for some keys)
    return MACCS_DESCRIPTIONS.get(key_idx, f"SMARTS pattern: {smarts}")


# ── LLM helper ────────────────────────────────────────────────────────────────

def call_llm_once(prompt: str, temperature: float = 0.0, max_tokens: int = 100) -> str:
    """Single-shot LLM call — does NOT add to conversation history."""
    handler = st.session_state.get("chat_handler")
    if handler is None:
        return "LLM not initialized. Configure an API key in the sidebar."
    try:
        messages = [{"role": "user", "content": prompt}]
        response = handler.client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return response.content.strip()
    except Exception as e:
        return f"LLM error: {e}"


# ── MACCS rendering ───────────────────────────────────────────────────────────

def render_maccs_grid(maccs_fp, key_prefix: str = "", smiles: str = ""):
    """Render the 167-cell MACCS key grid with a selectbox for detail inspection."""
    st.markdown("""
    <style>
    .maccs-grid { display: flex; flex-wrap: wrap; gap: 3px; margin: 0.5rem 0; }
    .maccs-key {
        padding: 3px 6px;
        font-size: 0.6rem;
        font-family: 'Space Grotesk', sans-serif;
        border-radius: 4px;
        cursor: default;
        font-weight: 600;
        transition: transform 0.15s;
        white-space: nowrap;
    }
    .maccs-key:hover { transform: scale(1.2); z-index: 10; box-shadow: 0 2px 8px rgba(0,0,0,0.5); }
    .maccs-on  { background-color: var(--color-success); color: var(--color-bg); }
    .maccs-off { background-color: var(--color-border); color: var(--color-text-dim); }
    </style>
    """, unsafe_allow_html=True)

    grid_html = '<div class="maccs-grid">'
    for i in range(167):
        is_on = maccs_fp.GetBit(i)
        cls = "maccs-on" if is_on else "maccs-off"
        grid_html += f'<div class="maccs-key {cls}" title="MACCS Key {i}">{i}</div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    active_maccs = [i for i in range(167) if maccs_fp.GetBit(i)]
    if not active_maccs:
        st.caption("No MACCS keys are active for this molecule.")
        return

    maccs_sel = st.selectbox(
        "Inspect MACCS key:",
        options=active_maccs,
        format_func=lambda x: f"Key {x}",
        key=f"{key_prefix}maccs_sel",
    )
    render_maccs_detail(int(maccs_sel), maccs_fp, key_prefix=key_prefix, smiles=smiles)


def render_maccs_detail(key_idx: int, maccs_fp, key_prefix: str = "", smiles: str = ""):
    """Show MACCS key description, direct structure image, and LLM Explain button."""
    from rdkit import Chem
    from rdkit.Chem import Draw

    is_on = maccs_fp.GetBit(key_idx)
    status = ":material/circle: :green[ON]" if is_on else ":material/circle: :gray[OFF]"

    # Get SMARTS first so description is derived from it (guaranteed consistent)
    smarts = get_maccs_smarts(key_idx)
    description = _maccs_description(smarts, key_idx)

    st.markdown(f"**MACCS Key {key_idx}**: {status}")
    st.markdown(f"**{description}**")
    if smarts and smarts != "?":
        st.caption(f"SMARTS: `{smarts}`")

    # Prefer: actual molecule with highlighted matches (when smiles is given)
    # Fallback: abstract SMARTS pattern image
    rendered = False
    if smiles and smarts and smarts != "?":
        try:
            mol = Chem.MolFromSmiles(smiles)
            pattern = Chem.MolFromSmarts(smarts)
            if mol is not None and pattern is not None:
                matches = mol.GetSubstructMatches(pattern)
                highlight_atoms = list({a for match in matches for a in match})
                img = Draw.MolToImage(mol, size=(300, 250), highlightAtoms=highlight_atoms)
                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                st.image(buf, width=300)
                if matches:
                    st.caption(f"{len(matches)} match{'es' if len(matches) != 1 else ''} highlighted")
                else:
                    st.caption("Pattern not matched in this molecule (bit may be from a composite key)")
                rendered = True
        except Exception:
            pass

    if not rendered:
        if smarts and smarts != "?":
            mol = Chem.MolFromSmarts(smarts)
            if mol is not None:
                try:
                    img = Draw.MolToImage(mol, size=(300, 250))
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    buf.seek(0)
                    st.image(buf, width=300)
                except Exception:
                    st.caption(f"Pattern: `{smarts}` (cannot be visualized)")
            else:
                st.caption(f"Pattern: `{smarts}` (cannot be visualized)")
        else:
            st.caption("No SMARTS pattern defined for this key.")

    if st.button(":material/auto_stories: Explain", key=f"{key_prefix}explain_maccs_{key_idx}"):
        status_word = "present in" if is_on else "absent from"
        prompt = (
            f"Rewrite the following MACCS key description as ONE short sentence "
            f"explaining what it means for the molecule being analyzed. "
            f"State whether the feature is {status_word} the molecule. "
            f"Do NOT add any information beyond what is given. "
            f"Do NOT speculate about implications, activity, or drug design. "
            f"Do NOT mention SMARTS patterns or technical encoding details. "
            f"Just explain what the structural feature is in plain English.\n\n"
            f"MACCS Key {key_idx}: \"{description}\"\n"
            f"Status: {status_word} this molecule\n\n"
            f"Example format: \"MACCS Key 29 indicates that a sulfur-sulfur bond "
            f"(S-S) is present in the molecule.\"\n\n"
            f"Your response (one sentence only):"
        )
        with st.spinner("Explaining…"):
            response = call_llm_once(prompt, temperature=0.0, max_tokens=100)
        st.markdown(
            f"<div style='background:var(--color-card);border:1px solid var(--color-border-subtle);"
            f"border-radius:8px;padding:0.8rem;margin-top:0.5rem;'>"
            f"<div style='color:var(--color-text);font-size:0.85rem;'>{response}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── ECFP rendering ────────────────────────────────────────────────────────────

def render_ecfp_grid(bi: dict, bit_db: dict, shap_vals=None, key_prefix: str = ""):
    """Render ECFP ON-bits as dominance-colored pills with a selectbox for detail."""
    st.markdown(
        "<div style='display:flex;gap:1rem;margin-bottom:0.5rem;font-size:0.75rem;"
        "font-family:var(--font-main);color:var(--color-text-muted);flex-wrap:wrap;'>"
        "<span><svg width='11' height='11' style='vertical-align:middle;margin-right:3px;'>"
        "<circle cx='5.5' cy='5.5' r='5' fill='var(--color-success)'/></svg>Dominant ≥80%</span>"
        "<span><svg width='11' height='11' style='vertical-align:middle;margin-right:3px;'>"
        "<circle cx='5.5' cy='5.5' r='5' fill='var(--color-warning-alt)'/></svg>60–80%</span>"
        "<span><svg width='11' height='11' style='vertical-align:middle;margin-right:3px;'>"
        "<circle cx='5.5' cy='5.5' r='5' fill='var(--color-warning)'/></svg>40–60%</span>"
        "<span><svg width='11' height='11' style='vertical-align:middle;margin-right:3px;'>"
        "<circle cx='5.5' cy='5.5' r='5' fill='var(--color-danger)'/></svg>&lt;40%</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("""
    <style>
    .ecfp-grid { display: flex; flex-wrap: wrap; gap: 3px; margin: 0.5rem 0; }
    .ecfp-bit {
        padding: 3px 7px;
        font-size: 0.6rem;
        font-family: 'Space Grotesk', sans-serif;
        border-radius: 4px;
        cursor: default;
        color: var(--color-bg);
        font-weight: 600;
        transition: transform 0.15s;
        white-space: nowrap;
    }
    .ecfp-bit:hover { transform: scale(1.2); z-index: 10; box-shadow: 0 2px 8px rgba(0,0,0,0.5); }
    </style>
    """, unsafe_allow_html=True)

    on_bits = sorted(bi.keys())
    if shap_vals is not None:
        try:
            on_bits = sorted(on_bits, key=lambda b: abs(float(shap_vals[b])), reverse=True)
        except Exception:
            pass

    grid_html = '<div class="ecfp-grid">'
    for bit in on_bits:
        db_info = bit_db.get(bit)
        n_subs = db_info.get("n_unique_substructures", 1) if db_info else 1
        dominance = db_info.get("dominance", 100.0) if db_info else 100.0
        color = reliability_color(dominance)
        rel_label = reliability_label(dominance, n_subs)
        shap_str = ""
        if shap_vals is not None:
            try:
                sv = float(shap_vals[bit])
                shap_str = f" | SHAP={sv:+.4f} {'→Act' if sv > 0 else '→Ina'}"
            except Exception:
                pass
        grid_html += (
            f'<div class="ecfp-bit" style="background-color:{color};" '
            f'title="Bit {bit} | {rel_label}{shap_str}">{bit}</div>'
        )
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    if not on_bits:
        st.caption("No ECFP bits are active for this molecule.")
        return

    def _bit_label(b):
        info = bit_db.get(b) or {}
        n = info.get("n_unique_substructures", 1)
        dom = info.get("dominance", 100.0)
        return f"Bit {b}  ({reliability_label(dom, n)})"

    ecfp_sel = st.selectbox(
        "Inspect ECFP bit:",
        options=on_bits,
        format_func=_bit_label,
        key=f"{key_prefix}ecfp_sel",
    )
    st.session_state[f"{key_prefix}selected_ecfp_bit"] = int(ecfp_sel)


def render_bit_detail(bit_db: dict, shap_vals=None, key_prefix: str = ""):
    """Render substructure images and statistics for the selected ECFP bit."""
    bit_idx = st.session_state.get(f"{key_prefix}selected_ecfp_bit")
    if bit_idx is None:
        return
    bit_idx = int(bit_idx)

    st.markdown(
        f'<div class="section-header">Bit Detail — ECFP6_{bit_idx}</div>',
        unsafe_allow_html=True,
    )

    info = bit_db.get(bit_idx)
    if info is None:
        st.caption(f"Bit {bit_idx} not found in training database.")
        return

    n_subs = info.get("n_unique_substructures", 0)
    active_ratio = info.get("active_ratio", 0.0)
    dominance = info.get("dominance", 100.0)
    color = reliability_color(dominance)

    shap_str = ""
    if shap_vals is not None:
        try:
            sv = float(shap_vals[bit_idx])
            shap_str = (
                f" &nbsp;·&nbsp; SHAP = {sv:+.6f} "
                f"{'→ Active' if sv > 0 else '→ Inactive'}"
            )
        except Exception:
            pass

    st.markdown(
        f"<div style='background:var(--color-card);border-radius:8px;padding:0.8rem;"
        f"border-left:4px solid {color};margin-bottom:0.5rem;'>"
        f"<div style='font-family:var(--font-main);color:var(--color-text);font-weight:500;'>"
        f"ECFP6_{bit_idx}</div>"
        f"<div style='color:var(--color-text-muted);font-size:0.85rem;margin-top:0.3rem;'>"
        f"{n_subs} substructure{'s' if n_subs != 1 else ''} &nbsp;·&nbsp; "
        f"Reliability: {dominance:.1f}% dominant &nbsp;·&nbsp; "
        f"Active ratio: {active_ratio:.1%}{shap_str}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    subs_dict = info.get("substructures", {})
    if subs_dict:
        from rdkit.Chem import Draw
        items = (
            subs_dict.most_common()
            if hasattr(subs_dict, "most_common")
            else sorted(subs_dict.items(), key=lambda x: x[1], reverse=True)
        )
        total = max(sum(subs_dict.values()), 1)
        mols, legends = [], []
        for sub_smi, count in items:
            mol = smiles_to_mol(str(sub_smi))
            if mol is not None:
                pct = count / total * 100
                mols.append(mol)
                legends.append(f"{count}x ({pct:.1f}%)")
        if mols:
            img = Draw.MolsToGridImage(
                mols,
                molsPerRow=min(5, len(mols)),
                subImgSize=(250, 200),
                legends=legends,
            )
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            st.image(buf, width="stretch")

    if n_subs <= 1:
        st.success(":material/check_circle: Unambiguous — this bit maps to exactly one substructure.")
    elif n_subs <= 3:
        st.info(f":material/info: Low collision — {n_subs} substructures share this bit.")
    else:
        st.warning(
            f":material/warning: High collision — {n_subs} substructures share this bit. "
            "Interpret SHAP values with caution."
        )


# ── Prediction card & AD badge ────────────────────────────────────────────────

def render_prediction_card(prediction: str, p_active: float, p_inactive: float):
    """Render prediction result using native Streamlit metrics."""
    delta_from_threshold = p_active - 0.5
    delta_str = f"{delta_from_threshold:+.4f} vs threshold"
    icon = ":material/check_circle:" if prediction == "Active" else ":material/cancel:"
    pred_label = f":green[{prediction}]" if prediction == "Active" else f":red[{prediction}]"

    with st.container(border=True):
        st.markdown(f"### {icon} {pred_label}")
        col_a, col_b = st.columns(2)
        col_a.metric(
            "P(active)",
            f"{p_active:.4f}",
            delta=delta_str,
            delta_color="normal" if prediction == "Active" else "inverse",
        )
        col_b.metric("P(inactive)", f"{p_inactive:.4f}")
        st.progress(p_active, text=f"{p_active:.1%} probability of activity")


def render_ad_badge(inside_ad: bool, mean_dist: float, threshold: float,
                    rf_std: Optional[float] = None):
    """Render applicability domain status using native Streamlit metrics."""
    icon = ":material/check_circle:" if inside_ad else ":material/warning:"
    label = ":green[INSIDE AD]" if inside_ad else ":orange[OUTSIDE AD]"
    margin = threshold - mean_dist
    margin_str = f"{margin:+.4f} margin"

    with st.container(border=True):
        st.markdown(f"**{icon} {label}**")
        col_a, col_b = st.columns(2)
        col_a.metric(
            "Distance",
            f"{mean_dist:.4f}",
            delta=margin_str,
            delta_color="normal" if inside_ad else "inverse",
        )
        col_b.metric("Threshold", f"{threshold:.4f}")
        if rf_std is not None:
            st.caption(f"RF tree std: {rf_std:.4f}")
