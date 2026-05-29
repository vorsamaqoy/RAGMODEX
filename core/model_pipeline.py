"""Full molecule prediction + SHAP interpretation pipeline.

Pipeline (triggered per query molecule):
  SMILES → fingerprint → model.predict_proba → SHAP values
         → bitInfo (this molecule) → cross-reference with bit_db
         → structured context for the LLM
"""

from __future__ import annotations

import io
import pickle
from typing import Optional, Any

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs


# ---------------------------------------------------------------------------
# Internal helper (mirrors _extract_env_smiles in bit_database.py)
# Kept local to avoid importing private symbols across modules.
# ---------------------------------------------------------------------------

def _env_smiles(mol: Chem.Mol, atom_idx: int, radius: int) -> Optional[str]:
    """Return canonical SMILES for the atomic environment at atom_idx/radius."""
    try:
        if radius == 0:
            return mol.GetAtomWithIdx(atom_idx).GetSymbol()
        env = Chem.FindAtomEnvironmentOfRadiusN(mol, radius, atom_idx)
        if not env:
            return None
        amap: dict = {}
        submol = Chem.PathToSubmol(mol, env, atomMap=amap)
        if submol.GetNumAtoms() == 0:
            return None
        return Chem.MolToSmiles(submol)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(model_bytes: bytes) -> Any:
    """Load a scikit-learn model from raw bytes (pickle or joblib).

    Raises ValueError if neither loader succeeds.
    InconsistentVersionWarning (model saved with different sklearn version)
    is suppressed — the model still loads and usually works fine.
    """
    import warnings
    from sklearn.exceptions import InconsistentVersionWarning
    # Try pickle first (most common)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InconsistentVersionWarning)
            return pickle.loads(model_bytes)
    except Exception:
        pass
    # Fallback: joblib
    try:
        import joblib
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InconsistentVersionWarning)
            return joblib.load(io.BytesIO(model_bytes))
    except Exception as e:
        raise ValueError(f"Could not load model (tried pickle and joblib): {e}") from e


def create_explainer(model: Any):
    """Create a SHAP TreeExplainer for a tree-based model.

    This is slow (~1 s) and should be called once and cached in session state.
    """
    import shap
    return shap.TreeExplainer(model)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def predict_and_interpret(
    smiles: str,
    model: Any,
    explainer: Any,
    bit_db: dict,
    radius: int = 3,
    n_bits: int = 2048,
    top_n: int = 10,
) -> dict:
    """Full pipeline: SMILES → fingerprint → prediction → SHAP → structured context.

    Parameters
    ----------
    smiles    : query SMILES string
    model     : fitted sklearn estimator with predict_proba()
    explainer : shap.TreeExplainer (pre-built, cached)
    bit_db    : output of build_bit_database() — may be empty dict if no data loaded
    radius    : Morgan radius (must match training; ECFP6 = 3)
    n_bits    : fingerprint length (must match training)
    top_n     : number of highest-|SHAP| bits to report

    Returns
    -------
    dict with keys:
        smiles, canonical_smiles, prediction, probability_active,
        probability_inactive, expected_value, top_bits, n_on_bits,
        radius, n_bits
    OR {"error": "..."} on failure.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"Invalid SMILES: {smiles!r}"}

    # 1. Fingerprint
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    fp_array = np.zeros(n_bits, dtype=np.int32)
    DataStructs.ConvertToNumpyArray(fp, fp_array)

    # 2. Prediction
    try:
        prob = model.predict_proba(fp_array.reshape(1, -1))[0]
    except Exception as exc:
        return {"error": f"model.predict_proba failed: {exc}"}

    pred_class = "Active" if prob[1] > 0.5 else "Inactive"

    # 3. SHAP values
    try:
        shap_raw = explainer.shap_values(fp_array.reshape(1, -1))
        # Handle various SHAP output shapes:
        # - list of arrays (one per class) → take class-1 slice
        # - 3-D array (samples, features, classes) → take [0, :, 1]
        # - 2-D array (samples, features) → take [0, :]
        if isinstance(shap_raw, list):
            shap_vals: np.ndarray = np.asarray(shap_raw[1])[0]
        elif np.asarray(shap_raw).ndim == 3:
            shap_vals = np.asarray(shap_raw)[0, :, 1]
        else:
            shap_vals = np.asarray(shap_raw)[0]
    except Exception as exc:
        return {"error": f"SHAP computation failed: {exc}"}

    # 4. bitInfo for THIS molecule (exact atom environments)
    bi: dict = {}
    AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits, bitInfo=bi)

    bit_prefix = f"ECFP{2 * radius}"

    # 5. Top-N bits by absolute SHAP value
    top_idx = np.argsort(np.abs(shap_vals))[::-1][:top_n]

    # 6. Per-bit interpretation
    bit_interpretations: list[dict] = []
    for rank, bit_pos in enumerate(top_idx, 1):
        bit_pos = int(bit_pos)
        shap_val = float(shap_vals[bit_pos])
        bit_on = int(fp_array[bit_pos])
        direction = "-> Active" if shap_val > 0 else "-> Inactive"

        # Molecule-level: which substructure(s) activate this bit IN THIS MOLECULE
        # Deduplicate by canonical SMILES (handles symmetry without over-counting)
        mol_subs: list[dict] = []
        seen: set[str] = set()
        if bit_pos in bi:
            for atom_idx, rad in bi[bit_pos]:
                sub_smi = _env_smiles(mol, atom_idx, rad)
                if sub_smi and sub_smi not in seen:
                    mol_subs.append({
                        "smiles": sub_smi,
                        "atom_idx": atom_idx,
                        "radius": rad,
                    })
                    seen.add(sub_smi)

        bit_interpretations.append({
            "rank": rank,
            "bit": f"{bit_prefix}_{bit_pos}",
            "bit_index": bit_pos,
            "shap_value": shap_val,
            "abs_shap": abs(shap_val),
            "direction": direction,
            "bit_on": bit_on,
            "molecule_substructures": mol_subs,
            "training_info": bit_db.get(bit_pos),   # None if bit_db empty/missing
        })

    # 7. All active folded bits, used by the UI collision map.
    # Keep this separate from SHAP ranking so users can inspect every ON bit.
    active_bits: list[dict] = []
    for bit_pos in map(int, fp.GetOnBits()):
        mol_subs: list[dict] = []
        seen: set[str] = set()
        for atom_idx, rad in bi.get(bit_pos, []):
            sub_smi = _env_smiles(mol, atom_idx, rad)
            key = f"{sub_smi}|{atom_idx}|{rad}"
            if sub_smi and key not in seen:
                mol_subs.append({
                    "smiles": sub_smi,
                    "atom_idx": atom_idx,
                    "radius": rad,
                })
                seen.add(key)
        active_bits.append({
            "bit": f"{bit_prefix}_{bit_pos}",
            "bit_index": bit_pos,
            "molecule_substructures": mol_subs,
            "training_info": bit_db.get(bit_pos),
        })

    # Expected value (model baseline)
    ev = explainer.expected_value
    if isinstance(ev, (list, np.ndarray)):
        expected_value = float(np.asarray(ev)[1])
    else:
        expected_value = float(ev)

    return {
        "smiles": smiles,
        "canonical_smiles": Chem.MolToSmiles(mol),
        "prediction": pred_class,
        "probability_active": float(prob[1]),
        "probability_inactive": float(prob[0]),
        "expected_value": expected_value,
        "top_bits": bit_interpretations,
        "active_bits": active_bits,
        "n_on_bits": int(fp_array.sum()),
        "radius": radius,
        "n_bits": n_bits,
        # Full arrays — required by comparison_pipeline and aggregate stats
        "fp_array": fp_array.copy(),              # int32 ndarray, shape (n_bits,)
        "shap_values_all": shap_vals.copy(),      # float64 ndarray, shape (n_bits,)
    }


# ---------------------------------------------------------------------------
# Context formatter for LLM
# ---------------------------------------------------------------------------

def format_interpretation_context(result: dict) -> str:
    """Convert predict_and_interpret() output into grounded text for the LLM.

    The returned string is injected verbatim into the LLM prompt.
    It contains ONLY actual computed data — no hallucinated content.
    """
    if "error" in result:
        return f"PIPELINE ERROR: {result['error']}"

    lines = [
        "=== MOLECULE PREDICTION ===",
        f"SMILES: {result['smiles']}",
        f"Canonical SMILES: {result['canonical_smiles']}",
        f"Prediction: {result['prediction']}",
        f"P(active)   = {result['probability_active']:.4f}",
        f"P(inactive) = {result['probability_inactive']:.4f}",
        f"Model baseline (expected value) = {result['expected_value']:.4f}",
        f"Fingerprint: ECFP{2 * result['radius']}, {result['n_bits']} bits, "
        f"{result['n_on_bits']} bits ON in this molecule",
        "",
        f"=== TOP {len(result['top_bits'])} MOST INFLUENTIAL BITS (by |SHAP|) ===",
        "",
    ]

    for bit_info in result["top_bits"]:
        lines.append(f"--- #{bit_info['rank']}  {bit_info['bit']} ---")
        lines.append(
            f"SHAP value: {bit_info['shap_value']:+.6f}  ({bit_info['direction']})"
        )
        lines.append(f"Bit is {'ON (=1)' if bit_info['bit_on'] else 'OFF (=0)'} in this molecule")

        # Molecule-level substructures
        if bit_info["molecule_substructures"]:
            lines.append("Substructure(s) activating this bit in THIS molecule:")
            for sub in bit_info["molecule_substructures"]:
                lines.append(
                    f"  -> \"{sub['smiles']}\"  "
                    f"(center atom {sub['atom_idx']}, radius {sub['radius']})"
                )
        elif bit_info["bit_on"] == 0:
            lines.append(
                "Bit is OFF in this molecule - the ABSENCE of the corresponding "
                "substructure contributes to the prediction shift."
            )

        # Training-set context from bit_db
        db = bit_info["training_info"]
        if db:
            total_counts = sum(db["substructures"].values())
            if db["dominance"] > 80:
                confidence = "HIGH"
            elif db["dominance"] > 50:
                confidence = "MODERATE"
            else:
                confidence = "LOW (hash collision — mixed signal)"

            lines.append("Training set context:")
            lines.append(
                f"  Activated in: {db['active_freq']} active + "
                f"{db['inactive_freq']} inactive molecules"
            )
            lines.append(f"  Active ratio when bit=1: {db['active_ratio']:.1%}")
            lines.append(f"  Unique substructures mapped to this bit: {db['n_unique_substructures']}")
            lines.append(
                f"  Interpretation confidence: {confidence} "
                f"(dominant substructure covers {db['dominance']:.1f}%)"
            )
            if db["dominant_substructure"]:
                lines.append(f"  Dominant substructure: \"{db['dominant_substructure']}\"")
            lines.append("  Top substructures in training (by frequency):")
            for sub_smi, count in list(db["substructures"].items())[:5]:
                pct = count / total_counts * 100 if total_counts > 0 else 0.0
                lines.append(f"    {sub_smi:<40s}  {pct:5.1f}%")
        else:
            lines.append("Training set context: bit not in database (no data)")

        lines.append("")

    return "\n".join(lines)
