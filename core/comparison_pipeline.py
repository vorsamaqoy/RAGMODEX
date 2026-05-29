"""comparison_pipeline.py — Side-by-side molecule comparison via SHAP and fingerprint diff.

No Streamlit dependencies. Pure logic module.
"""

from __future__ import annotations

import numpy as np
from rdkit import Chem
from rdkit.Chem import DataStructs, AllChem

from core.model_pipeline import predict_and_interpret


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _mol_subs_for_bit(result: dict, bit_idx: int) -> list[dict]:
    """Return molecule_substructures for the given bit_index from a result dict.

    Searches result['top_bits'] for an entry whose bit_index matches.
    Returns an empty list if the bit is not in top_bits (it may still be ON in
    the fingerprint but outside the top-N reported).
    """
    for bit_info in result.get("top_bits", []):
        if bit_info["bit_index"] == bit_idx:
            return bit_info.get("molecule_substructures", [])
    return []


def _db_for_bit(result: dict, bit_idx: int) -> dict | None:
    """Return training_info for the given bit_index from a result dict."""
    for bit_info in result.get("top_bits", []):
        if bit_info["bit_index"] == bit_idx:
            return bit_info.get("training_info")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compare_molecules(
    smi1: str,
    smi2: str,
    model,
    explainer,
    bit_db: dict,
    radius: int = 3,
    n_bits: int = 2048,
) -> dict:
    """Compare two molecules: fingerprint diff, SHAP diff, predictions.

    Steps
    -----
    1. Run predict_and_interpret for both molecules (top_n=10).
    2. Use fp_array and shap_values_all from both results.
    3. Compute Tanimoto similarity between the two fingerprint bit-vectors.
    4. Identify bits: only_in_mol1, only_in_mol2, shared.
    5. For each differing bit record shap_mol1, shap_mol2, shap_diff,
       molecule substructures, and training db info.
    6. Sort differentiating bits by abs(shap_diff), keep top 15.

    Returns
    -------
    dict with keys:
        mol1                    – predict_and_interpret result for smi1
        mol2                    – predict_and_interpret result for smi2
        tanimoto                – float Tanimoto similarity
        bits_only_mol1          – int count of bits ON only in mol1
        bits_only_mol2          – int count of bits ON only in mol2
        bits_shared             – int count of bits ON in both
        top_differentiating_bits – list of dicts (see below)
        delta_probability       – float: P(active)_mol2 − P(active)_mol1
    OR {"error": "..."} on failure.

    Each entry in top_differentiating_bits:
        bit         – "ECFP6_N"
        in_mol1     – bool
        in_mol2     – bool
        shap_mol1   – float (0.0 if shap_values_all not available)
        shap_mol2   – float
        shap_diff   – float (shap_mol2 − shap_mol1)
        mol_subs    – list of substructure dicts from whichever molecule has the bit
        db          – training_info dict or None
    """
    # Canonical identity check — must happen before the expensive SHAP pipeline.
    try:
        _can1 = Chem.MolToSmiles(Chem.MolFromSmiles(smi1))
        _can2 = Chem.MolToSmiles(Chem.MolFromSmiles(smi2))
        if _can1 == _can2:
            return {"identical": True, "canonical_smiles": _can1}
    except Exception:
        pass

    mol1_result = predict_and_interpret(smi1, model, explainer, bit_db,
                                        radius=radius, n_bits=n_bits, top_n=10)
    if "error" in mol1_result:
        return {"error": f"Molecule 1 failed: {mol1_result['error']}"}

    mol2_result = predict_and_interpret(smi2, model, explainer, bit_db,
                                        radius=radius, n_bits=n_bits, top_n=10)
    if "error" in mol2_result:
        return {"error": f"Molecule 2 failed: {mol2_result['error']}"}

    # fp_array and shap_values_all may be absent in the current model_pipeline
    # version (will be added). Guard gracefully.
    fp1: np.ndarray | None = mol1_result.get("fp_array")
    fp2: np.ndarray | None = mol2_result.get("fp_array")
    shap1_all: np.ndarray | None = mol1_result.get("shap_values_all")
    shap2_all: np.ndarray | None = mol2_result.get("shap_values_all")

    if fp1 is None or fp2 is None:
        # Recompute fingerprints from canonical SMILES
        def _fp_array(smi: str) -> np.ndarray:
            mol = Chem.MolFromSmiles(smi)
            arr = np.zeros(n_bits, dtype=np.int32)
            if mol is not None:
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
                DataStructs.ConvertToNumpyArray(fp, arr)
            return arr

        fp1 = _fp_array(mol1_result["canonical_smiles"])
        fp2 = _fp_array(mol2_result["canonical_smiles"])

    # Tanimoto similarity (bit-vector definition)
    fp1_bool = fp1.astype(bool)
    fp2_bool = fp2.astype(bool)
    intersection = int(np.logical_and(fp1_bool, fp2_bool).sum())
    union = int(np.logical_or(fp1_bool, fp2_bool).sum())
    tanimoto: float = intersection / union if union > 0 else 1.0

    # Bit set membership
    only_mol1_mask = fp1_bool & ~fp2_bool
    only_mol2_mask = fp2_bool & ~fp1_bool
    shared_mask = fp1_bool & fp2_bool
    bits_only_mol1 = int(only_mol1_mask.sum())
    bits_only_mol2 = int(only_mol2_mask.sum())
    bits_shared = int(shared_mask.sum())

    # Differentiating bits = bits present in one but not both
    diff_indices = np.where(only_mol1_mask | only_mol2_mask)[0]

    # Build per-bit records
    diff_bits: list[dict] = []
    for bit_idx in diff_indices:
        bit_idx_int = int(bit_idx)
        in_mol1 = bool(fp1_bool[bit_idx_int])
        in_mol2 = bool(fp2_bool[bit_idx_int])

        shap_m1 = float(shap1_all[bit_idx_int]) if shap1_all is not None else 0.0
        shap_m2 = float(shap2_all[bit_idx_int]) if shap2_all is not None else 0.0
        shap_diff = shap_m2 - shap_m1

        # Prefer substructures from the molecule that actually has the bit ON
        if in_mol1:
            mol_subs = _mol_subs_for_bit(mol1_result, bit_idx_int)
        else:
            mol_subs = _mol_subs_for_bit(mol2_result, bit_idx_int)

        # db info: prefer whichever result has it in top_bits; fall back to bit_db
        db = _db_for_bit(mol1_result, bit_idx_int) or _db_for_bit(mol2_result, bit_idx_int)
        if db is None:
            db = bit_db.get(bit_idx_int)

        diff_bits.append({
            "bit": f"ECFP6_{bit_idx_int}",
            "in_mol1": in_mol1,
            "in_mol2": in_mol2,
            "shap_mol1": shap_m1,
            "shap_mol2": shap_m2,
            "shap_diff": shap_diff,
            "mol_subs": mol_subs,
            "db": db,
        })

    # Sort by |shap_diff| descending; take top 15
    diff_bits.sort(key=lambda x: abs(x["shap_diff"]), reverse=True)
    top_differentiating_bits = diff_bits[:15]

    delta_probability = (
        mol2_result["probability_active"] - mol1_result["probability_active"]
    )

    return {
        "mol1": mol1_result,
        "mol2": mol2_result,
        "tanimoto": tanimoto,
        "bits_only_mol1": bits_only_mol1,
        "bits_only_mol2": bits_only_mol2,
        "bits_shared": bits_shared,
        "top_differentiating_bits": top_differentiating_bits,
        "delta_probability": delta_probability,
    }


def format_comparison_context(result: dict) -> str:
    """Format comparison result as grounded text for LLM injection.

    Starts with '=== MOLECULE COMPARISON ==='.
    Shows both molecule predictions, delta P(active), Tanimoto similarity,
    and top 10 differentiating bits with substructures, SHAP values and
    training active_ratio.
    """
    if "error" in result:
        return f"PIPELINE ERROR: {result['error']}"

    mol1 = result["mol1"]
    mol2 = result["mol2"]
    delta = result["delta_probability"]

    lines = [
        "=== MOLECULE COMPARISON ===",
        "",
        f"Molecule 1: {mol1['canonical_smiles']}",
        f"  Prediction : {mol1['prediction']}",
        f"  P(active)  : {mol1['probability_active']:.4f}",
        f"  P(inactive): {mol1['probability_inactive']:.4f}",
        f"  Bits ON    : {mol1['n_on_bits']}",
        "",
        f"Molecule 2: {mol2['canonical_smiles']}",
        f"  Prediction : {mol2['prediction']}",
        f"  P(active)  : {mol2['probability_active']:.4f}",
        f"  P(inactive): {mol2['probability_inactive']:.4f}",
        f"  Bits ON    : {mol2['n_on_bits']}",
        "",
        f"Delta P(active) [mol2 - mol1]: {delta:+.4f}",
        f"Tanimoto similarity           : {result['tanimoto']:.4f}",
        f"Bits only in mol1 : {result['bits_only_mol1']}",
        f"Bits only in mol2 : {result['bits_only_mol2']}",
        f"Bits shared       : {result['bits_shared']}",
        "",
        "=== TOP DIFFERENTIATING BITS (by |SHAP diff|) ===",
        "",
    ]

    for i, bit_info in enumerate(result["top_differentiating_bits"][:10], 1):
        present_in = []
        if bit_info["in_mol1"]:
            present_in.append("mol1")
        if bit_info["in_mol2"]:
            present_in.append("mol2")
        present_str = ", ".join(present_in) if present_in else "neither"

        lines.append(f"--- #{i}  {bit_info['bit']}  (present in: {present_str}) ---")
        lines.append(f"  SHAP mol1 : {bit_info['shap_mol1']:+.6f}")
        lines.append(f"  SHAP mol2 : {bit_info['shap_mol2']:+.6f}")
        lines.append(f"  SHAP diff : {bit_info['shap_diff']:+.6f}  (mol2 − mol1)")

        mol_subs = bit_info.get("mol_subs", [])
        if mol_subs:
            lines.append("  Substructure(s):")
            for sub in mol_subs:
                lines.append(
                    f"    → \"{sub['smiles']}\"  "
                    f"(atom {sub['atom_idx']}, radius {sub['radius']})"
                )

        db = bit_info.get("db")
        if db:
            lines.append(
                f"  Training: active_ratio={db['active_ratio']:.1%}, "
                f"activations={db['total_activations']}, "
                f"dominant_sub=\"{db.get('dominant_substructure') or 'n/a'}\""
            )
        else:
            lines.append("  Training: bit not in database")

        lines.append("")

    return "\n".join(lines)
