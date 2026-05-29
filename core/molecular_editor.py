"""molecular_editor.py — Simple rule-based molecular editing via SMILES substitution
and what-if analysis via SHAP comparison.

No Streamlit dependencies. Pure logic module.
"""

from __future__ import annotations

from typing import Optional

from rdkit import Chem

from core.comparison_pipeline import compare_molecules, format_comparison_context


# ---------------------------------------------------------------------------
# Replacement rule table
# Each entry: (required_keywords, old_fragment, new_fragment)
#   required_keywords – list of lowercase strings ALL of which must appear in
#                       edit_description.lower() for the rule to fire.
#   old_fragment      – plain SMILES substring to find in the input SMILES.
#   new_fragment      – replacement string ("" = deletion).
# Rules are tested in order; the first matching rule that also produces a
# valid molecule is returned.
# ---------------------------------------------------------------------------

_REPLACEMENTS: list[tuple[list[str], str, str]] = [
    # Halogen swaps
    (["replace", "cl", " f"],   "Cl", "F"),
    (["replace", "f", "cl"],    "F",  "Cl"),
    (["replace", "cl", "br"],   "Cl", "Br"),
    (["replace", "br", "cl"],   "Br", "Cl"),
    (["replace", "f", "br"],    "F",  "Br"),
    (["replace", "br", "f"],    "Br", "F"),
    (["replace", "cl", "i"],    "Cl", "I"),
    (["replace", "i", "cl"],    "I",  "Cl"),
    (["replace", "f", "i"],     "F",  "I"),
    (["replace", "i", "f"],     "I",  "F"),
    # Heteroatom swaps
    (["replace", "oh", "nh2"],  "O",  "N"),   # rough hydroxyl→amino
    (["replace", "nh2", "oh"],  "N",  "O"),   # rough amino→hydroxyl
    (["replace", "oh", "sh"],   "O",  "S"),
    (["replace", "sh", "oh"],   "S",  "O"),
    (["replace", "o", "s"],     "O",  "S"),
    (["replace", "s", "o"],     "S",  "O"),
    # Dehalogenation / removal
    (["dehalogenat"],           "Cl", ""),
    (["remove", "chloro"],      "Cl", ""),
    (["remove", "fluoro"],      "F",  ""),
    (["remove", "bromo"],       "Br", ""),
    (["remove", "iodo"],        "I",  ""),
    (["remove", "chlorine"],    "Cl", ""),
    (["remove", "fluorine"],    "F",  ""),
    (["remove", "bromine"],     "Br", ""),
    (["remove", "iodine"],      "I",  ""),
    # Methylation / demethylation
    (["add", "methyl"],         "",   "C"),   # handled specially — append
    (["remove", "methyl"],      "C",  ""),
    # Nitro group removal
    (["remove", "nitro"],       "[N+](=O)[O-]", ""),
    # Hydroxyl removal
    (["remove", "hydroxy"],     "O",  ""),
    (["remove", "hydroxyl"],    "O",  ""),
    # Amino removal
    (["remove", "amino"],       "N",  ""),
    (["remove", "amine"],       "N",  ""),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_edit_rdkit(smiles: str, edit_description: str) -> Optional[str]:
    """Apply a simple molecular edit described in natural language.

    Iterates over _REPLACEMENTS rules.  For each rule:
      - Check that ALL required_keywords appear in edit_lower.
      - Check that old_fragment appears in the SMILES string (when non-empty).
      - Apply str.replace(old_fragment, new_fragment, 1) (one substitution).
      - Validate the resulting SMILES with RDKit; if valid, return canonical SMILES.

    A blank old_fragment ("") in the "add methyl" rule is handled as a special
    case — a "C" is appended to the end of the SMILES before validation.

    Returns
    -------
    Canonical SMILES of the modified molecule, or None if:
      - no rule matched, or
      - the substituted SMILES is chemically invalid (RDKit cannot parse it).
    """
    edit_lower = edit_description.lower()

    for keywords, old_frag, new_frag in _REPLACEMENTS:
        # All keywords must be present
        if not all(kw in edit_lower for kw in keywords):
            continue

        # Special case: "add methyl" has empty old_frag — just append
        if old_frag == "":
            candidate = smiles + new_frag
        else:
            if old_frag not in smiles:
                continue
            candidate = smiles.replace(old_frag, new_frag, 1)

        # Validate with RDKit
        mol = Chem.MolFromSmiles(candidate)
        if mol is not None:
            return Chem.MolToSmiles(mol)

    return None


def format_edit_context(
    original_result: dict,
    modified_result: dict,
    comparison: dict,
) -> str:
    """Format what-if analysis as grounded text for LLM injection.

    Starts with '=== MOLECULAR EDITING (WHAT-IF ANALYSIS) ==='.
    Shows original and modified predictions, delta P(active), Tanimoto
    similarity, and top 5 differentiating bits with substructures.

    Parameters
    ----------
    original_result – predict_and_interpret result for the original molecule
    modified_result – predict_and_interpret result for the modified molecule
    comparison      – compare_molecules result for (original, modified)
    """
    if "error" in comparison:
        return f"PIPELINE ERROR: {comparison['error']}"

    orig_smi = original_result.get("canonical_smiles", "n/a")
    mod_smi = modified_result.get("canonical_smiles", "n/a")
    delta = comparison["delta_probability"]

    lines = [
        "=== MOLECULAR EDITING (WHAT-IF ANALYSIS) ===",
        "",
        "Original molecule:",
        f"  SMILES     : {orig_smi}",
        f"  Prediction : {original_result.get('prediction', 'n/a')}",
        f"  P(active)  : {original_result.get('probability_active', 0.0):.4f}",
        f"  P(inactive): {original_result.get('probability_inactive', 0.0):.4f}",
        "",
        "Modified molecule:",
        f"  SMILES     : {mod_smi}",
        f"  Prediction : {modified_result.get('prediction', 'n/a')}",
        f"  P(active)  : {modified_result.get('probability_active', 0.0):.4f}",
        f"  P(inactive): {modified_result.get('probability_inactive', 0.0):.4f}",
        "",
        f"Delta P(active) [modified - original]: {delta:+.4f}",
        f"Tanimoto similarity                  : {comparison['tanimoto']:.4f}",
        "",
    ]

    # Activity change interpretation
    if abs(delta) < 0.01:
        change_note = "The edit has negligible effect on predicted activity."
    elif delta > 0:
        change_note = (
            f"The edit INCREASES predicted activity by {delta:+.4f} probability units."
        )
    else:
        change_note = (
            f"The edit DECREASES predicted activity by {delta:+.4f} probability units."
        )
    lines.append(change_note)
    lines.append("")

    # Top 5 differentiating bits
    top_bits = comparison.get("top_differentiating_bits", [])[:5]
    if top_bits:
        lines.append("--- Top 5 Differentiating Bits ---")
        lines.append("")
        for i, bit_info in enumerate(top_bits, 1):
            present_in = []
            if bit_info["in_mol1"]:
                present_in.append("original")
            if bit_info["in_mol2"]:
                present_in.append("modified")
            present_str = ", ".join(present_in) if present_in else "neither"

            lines.append(
                f"  {i}. {bit_info['bit']}  (present in: {present_str})"
            )
            lines.append(
                f"     SHAP original: {bit_info['shap_mol1']:+.6f}  |  "
                f"SHAP modified: {bit_info['shap_mol2']:+.6f}  |  "
                f"diff: {bit_info['shap_diff']:+.6f}"
            )

            mol_subs = bit_info.get("mol_subs", [])
            if mol_subs:
                sub_strs = [f"\"{s['smiles']}\"" for s in mol_subs]
                lines.append(f"     Substructure(s): {', '.join(sub_strs)}")

            db = bit_info.get("db")
            if db:
                lines.append(
                    f"     Training: active_ratio={db['active_ratio']:.1%}, "
                    f"activations={db['total_activations']}"
                )
            lines.append("")
    else:
        lines.append("No differentiating bits found (molecules may be identical).")

    return "\n".join(lines)
