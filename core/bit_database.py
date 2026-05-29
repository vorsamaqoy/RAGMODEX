"""ECFP bit collision-aware database.

Builds a per-bit knowledge base from a training dataset so that, for each
folded Morgan fingerprint bit, we know WHICH distinct chemical environments
hash to it, how often, and how they correlate with the target label.
"""

from collections import defaultdict, Counter
from typing import Optional
import hashlib

from rdkit import Chem
from rdkit.Chem import AllChem


# ---------------------------------------------------------------------------
# Private helpers (mirror of ECFPInterpreter logic, kept here to avoid
# importing fingerprints/ from core/ which would invert the dependency graph)
# ---------------------------------------------------------------------------

def _extract_env_smiles(mol: Chem.Mol, atom_idx: int, radius: int) -> Optional[str]:
    """Extract canonical SMILES for the atomic environment at atom_idx/radius."""
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
# Public API
# ---------------------------------------------------------------------------

def build_bit_database(
    df,
    smiles_col: str,
    label_col: str,
    radius: int = 3,
    n_bits: int = 2048,
    progress_bar=None,
) -> tuple[dict, int]:
    """Build a per-bit database from a training DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns *smiles_col* and *label_col*.
    smiles_col : str
        Name of the SMILES column.
    label_col : str
        Name of the binary label column (0 or 1).
    radius : int
        Morgan fingerprint radius (default 3 → ECFP6).
    n_bits : int
        Number of fingerprint bits (default 2048).
    progress_bar : streamlit.delta_generator.DeltaGenerator or None
        If provided, call progress_bar.progress(fraction) to report progress.

    Returns
    -------
    (bit_db, n_failed)
        bit_db  – dict mapping bit_index (int) -> entry dict (see below)
        n_failed – number of rows skipped due to invalid SMILES

    Entry dict keys
    ---------------
    substructures     : dict  {env_smiles -> count}  – unique env SMILES per molecule
    active_freq       : int   – molecules with this bit ON and label == 1
    inactive_freq     : int   – molecules with this bit ON and label == 0
    total_activations : int   – total molecules with this bit ON
    n_unique_substructures : int
    dominant_substructure  : str | None
    dominance              : float  – dominant % (0-100)
    is_ambiguous           : bool
    active_ratio           : float  – fraction of ON-molecules that are active
    """
    # Use defaultdict during accumulation; convert to plain dict at the end
    _db: dict[int, dict] = defaultdict(lambda: {
        "substructures": Counter(),
        "radii": defaultdict(set),   # sub_smi -> set of radius values seen
        "active_freq": 0,
        "inactive_freq": 0,
        "total_activations": 0,
    })

    n_rows = len(df)
    n_failed = 0

    for i, (_, row) in enumerate(df.iterrows()):
        if progress_bar is not None:
            progress_bar.progress(i / n_rows)

        smi = str(row[smiles_col]).strip()
        try:
            label = int(row[label_col])
        except (ValueError, TypeError):
            label = 0

        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            n_failed += 1
            continue

        bi: dict = {}
        AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits, bitInfo=bi)

        for bit, envs in bi.items():
            entry = _db[bit]
            entry["total_activations"] += 1
            if label == 1:
                entry["active_freq"] += 1
            else:
                entry["inactive_freq"] += 1

            # Deduplicate by canonical env SMILES within THIS molecule
            # (handles symmetry: same substructure from different symmetric atoms)
            # Track radii per substructure to distinguish genuine collisions later.
            seen_this_mol: dict[str, set] = {}   # env_smi -> set of radii
            for atom_idx, rad in envs:
                env_smi = _extract_env_smiles(mol, atom_idx, rad)
                if env_smi:
                    if env_smi not in seen_this_mol:
                        seen_this_mol[env_smi] = set()
                    seen_this_mol[env_smi].add(rad)
            for env_smi, rads in seen_this_mol.items():
                entry["substructures"][env_smi] += 1
                entry["radii"][env_smi].update(rads)

    if progress_bar is not None:
        progress_bar.progress(1.0)

    # Compute summary statistics
    result: dict[int, dict] = {}
    for bit, info in _db.items():
        subs: Counter = info["substructures"]
        total_sub = sum(subs.values())
        most_common = subs.most_common(1)
        dominant_smi = most_common[0][0] if most_common else None
        dominance = (most_common[0][1] / total_sub * 100) if (most_common and total_sub > 0) else 0.0

        total_mols = info["active_freq"] + info["inactive_freq"]
        active_ratio = info["active_freq"] / total_mols if total_mols > 0 else 0.0

        result[bit] = {
            # Top-N substructures sorted by frequency (most common first)
            "substructures": dict(subs.most_common()),
            # radii: sub_smi -> sorted list of radius values observed for that substructure
            "radii": {smi: sorted(rads) for smi, rads in info["radii"].items()},
            "active_freq": info["active_freq"],
            "inactive_freq": info["inactive_freq"],
            "total_activations": info["total_activations"],
            "n_unique_substructures": len(subs),
            "dominant_substructure": dominant_smi,
            "dominance": dominance,
            "is_ambiguous": len(subs) > 1,
            "active_ratio": active_ratio,
        }

    return result, n_failed


def get_molecule_bit_info(
    smiles: str,
    radius: int = 3,
    n_bits: int = 2048,
) -> Optional[dict[int, list[dict]]]:
    """Compute per-bit atomic environments for a single query molecule.

    Returns
    -------
    dict mapping bit_index -> list of dicts with keys:
        "substructure" : str | None  – env SMILES (or None if extraction failed)
        "atom_idx"     : int
        "radius"       : int
    Returns None if the SMILES is invalid.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    bi: dict = {}
    AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits, bitInfo=bi)

    mol_bits: dict[int, list[dict]] = {}
    for bit, envs in bi.items():
        mol_bits[bit] = []
        for atom_idx, rad in envs:
            env_smi = _extract_env_smiles(mol, atom_idx, rad)
            mol_bits[bit].append({
                "substructure": env_smi,
                "atom_idx": atom_idx,
                "radius": rad,
            })

    return mol_bits


def get_bit_context(bit_idx: int, bit_db: dict) -> str:
    """Return a plain-text training-set summary for a single bit.

    This is the grounded context that gets injected verbatim into the LLM prompt
    for any query about a specific ECFP bit.  The LLM is instructed to answer
    ONLY from this data, not from generic knowledge.

    Parameters
    ----------
    bit_idx : int   – ECFP bit index to look up
    bit_db  : dict  – output of build_bit_database()

    Returns
    -------
    str  – multi-line text block ready for inclusion in an LLM prompt
    """
    if bit_idx not in bit_db:
        return (
            f"ECFP6_{bit_idx}: This bit was NEVER activated in the training set. "
            "No substructure data is available."
        )

    info = bit_db[bit_idx]
    total_sub_counts = sum(info["substructures"].values())

    lines = [
        f"=== ECFP6_{bit_idx} — Training Set Analysis ===",
        f"Total activations: {info['total_activations']} molecules",
        f"Activity correlation: {info['active_freq']} active (label=1), "
        f"{info['inactive_freq']} inactive (label=0)",
        f"Active ratio when bit=1: {info['active_ratio']:.1%}",
        f"Unique substructures mapping to this bit: {info['n_unique_substructures']}",
    ]

    # Ambiguity verdict
    n_sub = info["n_unique_substructures"]
    dom = info["dominance"]
    if n_sub == 1:
        lines.append("Ambiguity: NONE — this bit maps to exactly one substructure")
    elif dom > 80:
        lines.append(
            f"Ambiguity: LOW — dominant substructure covers {dom:.1f}% of activations"
        )
    elif dom > 50:
        lines.append(
            f"Ambiguity: MODERATE — dominant substructure covers {dom:.1f}% of activations; "
            "SHAP value is a partially mixed signal"
        )
    else:
        lines.append(
            f"Ambiguity: HIGH — no dominant substructure (top covers only {dom:.1f}%); "
            f"SHAP value is a MIXED SIGNAL across {n_sub} unrelated environments"
        )

    lines.append("")
    lines.append("Substructure distribution:")
    for sub_smi, count in list(info["substructures"].items())[:10]:
        pct = count / total_sub_counts * 100 if total_sub_counts > 0 else 0.0
        radii = info.get("radii", {}).get(sub_smi, [])
        radii_str = f"radii={radii}" if radii else ""
        lines.append(f"  {sub_smi:<45s}  {count:>4d} ({pct:5.1f}%)  {radii_str}")

    if n_sub > 10:
        lines.append(f"  ... ({n_sub - 10} more substructures not shown)")

    return "\n".join(lines)


def format_bit_context_for_llm(
    bit_index: int,
    shap_value: Optional[float],
    db_entry: Optional[dict],
    mol_bits: Optional[dict[int, list[dict]]],
) -> str:
    """Build a structured text block for LLM consumption.

    Parameters
    ----------
    bit_index  : ECFP bit index
    shap_value : SHAP value (float) or None if unknown
    db_entry   : entry from bit_database for this bit (or None)
    mol_bits   : output of get_molecule_bit_info() for the query molecule (or None)

    Returns
    -------
    Multi-line string suitable for injection into an LLM prompt.
    """
    lines: list[str] = []

    # Header
    if shap_value is not None:
        direction = "pushes toward ACTIVE" if shap_value > 0 else "pushes toward INACTIVE"
        lines.append(f"=== ECFP6 Bit {bit_index} (SHAP = {shap_value:+.4f}, {direction}) ===")
    else:
        lines.append(f"=== ECFP6 Bit {bit_index} ===")

    # ── This molecule ──────────────────────────────────────────────────────
    lines.append("")
    lines.append("[ This molecule ]")
    if mol_bits is not None and bit_index in mol_bits:
        envs = mol_bits[bit_index]
        unique_subs = list({e["substructure"] for e in envs if e["substructure"]})
        if unique_subs:
            lines.append(f"  Activated by {len(envs)} environment(s), "
                         f"{len(unique_subs)} unique substructure(s):")
            for e in envs:
                sub = e["substructure"] or "<extraction failed>"
                lines.append(f"    • \"{sub}\"  (atom {e['atom_idx']}, radius {e['radius']})")
        else:
            lines.append("  Bit is ON but substructure extraction failed for all environments.")
    elif mol_bits is not None:
        lines.append("  Bit is NOT set in this molecule.")
    else:
        lines.append("  (no molecule loaded)")

    # ── Training set ───────────────────────────────────────────────────────
    lines.append("")
    lines.append("[ Training set ]")
    if db_entry is None:
        lines.append("  No training data available for this bit.")
    else:
        total = db_entry["total_activations"]
        n_unique = db_entry["n_unique_substructures"]
        active_pct = db_entry["active_ratio"] * 100
        lines.append(f"  Bit ON in {total} training molecules "
                     f"({active_pct:.0f}% are active / label=1)")
        lines.append(f"  Distinct substructures that hash to this bit: {n_unique}")

        subs_dict: dict = db_entry["substructures"]
        total_counts = sum(subs_dict.values())
        top_n = list(subs_dict.items())[:6]   # show up to 6

        for rank, (smi, count) in enumerate(top_n, 1):
            pct = count / total_counts * 100 if total_counts > 0 else 0.0
            lines.append(f"    {rank}. \"{smi}\"  — {pct:.1f}% of activations "
                         f"({count} molecules)")

        if n_unique > 6:
            lines.append(f"    ... ({n_unique - 6} more substructures not shown)")

        # ── Confidence / collision assessment ─────────────────────────────
        lines.append("")
        dominance = db_entry["dominance"]
        dominant = db_entry["dominant_substructure"]

        # Check if this molecule's substructure matches the dominant one
        mol_sub_set: set[str] = set()
        if mol_bits and bit_index in mol_bits:
            mol_sub_set = {e["substructure"] for e in mol_bits[bit_index]
                           if e["substructure"]}

        dominant_match = dominant in mol_sub_set if dominant else False

        if not db_entry["is_ambiguous"]:
            conf_label = "✅ HIGH"
            conf_note = "Single substructure maps to this bit — no hash collision."
        elif dominance >= 80:
            conf_label = "✅ HIGH"
            match_tag = " (matches current molecule)" if dominant_match else ""
            conf_note = (f"Dominated ({dominance:.0f}%) by \"{dominant}\"{match_tag}.")
        elif dominance >= 50:
            conf_label = "⚠️ MEDIUM"
            conf_note = (
                f"One substructure dominant at {dominance:.0f}% but others present. "
                "SHAP value partly reflects other environments."
            )
        else:
            conf_label = "🔴 LOW"
            conf_note = (
                f"No dominant substructure ({dominance:.0f}% for top). "
                "SHAP value is a MIXED SIGNAL across {n_unique} different environments "
                "due to hash collision. Interpret with caution."
            )

        lines.append(f"  Interpretation confidence: {conf_label}")
        lines.append(f"  {conf_note}")

        # Collision divergence warning: if different envs have very different activity rates
        # (We can't compute per-env activity rate from current data structure,
        #  so we give a general note when is_ambiguous is True)
        if db_entry["is_ambiguous"] and n_unique > 1:
            lines.append(
                f"  ⚠️  NOTE: Because multiple distinct substructures collapse to bit "
                f"{bit_index} via hash folding, the SHAP contribution aggregates "
                "their combined effect. The true per-substructure signal may differ "
                "from the reported SHAP value."
            )

    return "\n".join(lines)
