"""suggestion_pipeline.py — SHAP-based structural modification suggestions
and substructure activity search against the training bit database.

No Streamlit dependencies. Pure logic module.
"""

from __future__ import annotations

import re
from typing import Optional

from rdkit import Chem

from core.model_pipeline import predict_and_interpret


# ---------------------------------------------------------------------------
# Name-to-SMARTS fragment mapping
# ---------------------------------------------------------------------------

_NAME_TO_FRAGMENTS: dict[str, list[str]] = {
    "chlorine":    ["Cl"],
    "chloro":      ["Cl"],
    "fluorine":    ["F"],
    "fluoro":      ["F"],
    "bromine":     ["Br"],
    "bromo":       ["Br"],
    "iodine":      ["I"],
    "iodo":        ["I"],
    "methyl":      ["C"],
    "ethyl":       ["CC"],
    "hydroxyl":    ["[OH]"],
    "hydroxy":     ["[OH]"],
    "amino":       ["[NH2]"],
    "amine":       ["N"],
    "nitro":       ["[N+](=O)[O-]"],
    "methoxy":     ["OC"],
    "ethoxy":      ["OCC"],
    "trifluoro":   ["C(F)(F)F"],
    "trifluoromethyl": ["C(F)(F)F"],
    "piperazine":  ["N1CCNCC1"],
    "piperidine":  ["C1CCNCC1"],
    "morpholine":  ["C1COCCN1"],
    "pyrrolidine": ["C1CCNC1"],
    "pyridine":    ["c1ccncc1"],
    "pyrimidine":  ["c1ccncn1"],
    "pyrazine":    ["c1cnccn1"],
    "triazine":    ["c1ncncn1"],
    "imidazole":   ["c1cnc[nH]1"],
    "pyrazole":    ["c1cc[nH]n1"],
    "oxazole":     ["c1cnco1"],
    "thiazole":    ["c1cncs1"],
    "furan":       ["c1ccco1"],
    "thiophene":   ["c1cccs1"],
    "phenyl":      ["c1ccccc1"],
    "benzene":     ["c1ccccc1"],
    "aromatic":    ["c1ccccc1", "c1ccncc1"],
    "carbonyl":    ["C=O"],
    "ketone":      ["CC(=O)C"],
    "aldehyde":    ["CC=O"],
    "amide":       ["C(=O)N"],
    "sulfonyl":    ["S(=O)(=O)"],
    "sulfone":     ["S(=O)(=O)"],
    "sulfonamide": ["S(=O)(=O)N"],
    "carboxyl":    ["C(=O)O"],
    "carboxylic":  ["C(=O)O"],
    "ester":       ["C(=O)OC"],
    "ether":       ["COC"],
    "epoxide":     ["C1OC1"],
    "lactam":      ["C1(=O)NCC1"],
    "lactone":     ["C1(=O)OCC1"],
    "urea":        ["NC(=O)N"],
    "thiourea":    ["NC(=S)N"],
    "guanidine":   ["NC(=N)N"],
    "hydrazine":   ["NN"],
    "hydroxamic":  ["C(=O)NO"],
    "phosphate":   ["P(=O)(O)O"],
    "indole":      ["c1ccc2[nH]ccc2c1"],
    "benzimidazole": ["c1ccc2[nH]cnc2c1"],
    "benzothiazole": ["c1ccc2scnc2c1"],
    "quinoline":   ["c1ccc2ncccc2c1"],
    "isoquinoline": ["c1ccc2cnccc2c1"],
    "naphthalene": ["c1ccc2ccccc2c1"],
    "purine":      ["c1ncnc2[nH]cnc12"],
    "pyrrole":     ["c1cc[nH]c1"],
    "cyclopropyl": ["C1CC1"],
    "cyclobutyl":  ["C1CCC1"],
    "cyclopentyl": ["C1CCCC1"],
    "cyclohexyl":  ["C1CCCCC1"],
}


# ---------------------------------------------------------------------------
# A. Validation helpers
# ---------------------------------------------------------------------------

def validate_add_suggestion(
    mol: "Chem.Mol",
    target_bit: int,
    fragment_smiles: str,
    radius: int = 3,
    n_bits: int = 2048,
) -> Optional[str]:
    """Try attaching fragment_smiles to mol at various single-bond positions.

    Returns the canonical SMILES of the first valid modified molecule
    where target_bit is ON, or None if no attachment works.
    """
    from rdkit.Chem import AllChem, RWMol

    frag_mol = Chem.MolFromSmiles(fragment_smiles)
    if frag_mol is None:
        return None

    base_atoms = [a.GetIdx() for a in mol.GetAtoms() if a.GetTotalNumHs() > 0]
    frag_atoms = [a.GetIdx() for a in frag_mol.GetAtoms() if a.GetTotalNumHs() > 0]

    if not base_atoms or not frag_atoms:
        return None

    n_base = mol.GetNumAtoms()
    for base_idx in base_atoms[:10]:
        for frag_idx in frag_atoms[:4]:
            try:
                combined = RWMol(Chem.CombineMols(mol, frag_mol))
                combined.AddBond(base_idx, n_base + frag_idx, Chem.BondType.SINGLE)
                try:
                    Chem.SanitizeMol(combined)
                except Exception:
                    continue
                smi = Chem.MolToSmiles(combined.GetMol())
                check_mol = Chem.MolFromSmiles(smi)
                if check_mol is None:
                    continue
                fp = AllChem.GetMorganFingerprintAsBitVect(check_mol, radius, nBits=n_bits)
                if fp.GetBit(target_bit):
                    return smi
            except Exception:
                continue
    return None


def validate_remove_suggestion(
    mol: "Chem.Mol",
    target_bit: int,
    substructure_smiles: str,
    radius: int = 3,
    n_bits: int = 2048,
) -> Optional[str]:
    """Try removing substructure_smiles from mol.

    Returns the canonical SMILES of the modified molecule where
    target_bit is OFF, or None if removal doesn't deactivate the bit.
    """
    from rdkit.Chem import AllChem

    sub_mol = Chem.MolFromSmiles(substructure_smiles)
    if sub_mol is None:
        return None
    try:
        query = Chem.MolFromSmarts(Chem.MolToSmarts(sub_mol))
    except Exception:
        return None
    if query is None or not mol.HasSubstructMatch(query):
        return None

    try:
        result = AllChem.DeleteSubstructs(mol, query)
        if result is not None and result.GetNumAtoms() > 0:
            frags = Chem.GetMolFrags(result, asMols=True)
            if len(frags) > 1:
                result = max(frags, key=lambda m: m.GetNumAtoms())
            smi = Chem.MolToSmiles(result)
            check_mol = Chem.MolFromSmiles(smi)
            if check_mol is not None and check_mol.GetNumAtoms() > 0:
                fp = AllChem.GetMorganFingerprintAsBitVect(check_mol, radius, nBits=n_bits)
                if not fp.GetBit(target_bit):
                    return smi
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# A1. Post-validation metrics
# ---------------------------------------------------------------------------

def _compute_mod_metrics(
    modified_smiles: str,
    model,
    ad_model,
    radius: int,
    n_bits: int,
    current_p: float,
) -> "tuple[Optional[float], Optional[bool]]":
    """Compute (delta_p_active, inside_ad) for a validated modified molecule.

    Runs model.predict_proba on the modified fingerprint and checks AD model.
    Returns (None, None) on any failure.
    """
    import numpy as np
    from rdkit.Chem import AllChem, DataStructs

    try:
        mod_mol = Chem.MolFromSmiles(modified_smiles)
        if mod_mol is None:
            return None, None
        fp = AllChem.GetMorganFingerprintAsBitVect(mod_mol, radius, nBits=n_bits)
        fp_arr = np.zeros(n_bits, dtype=np.int32)
        DataStructs.ConvertToNumpyArray(fp, fp_arr)
        prob = model.predict_proba(fp_arr.reshape(1, -1))[0]
        p_new = float(prob[1])
        delta_p = p_new - current_p

        inside_ad: Optional[bool] = None
        if ad_model is not None:
            try:
                knn, threshold, _m, _s = ad_model
                dists, _ = knn.kneighbors(fp_arr.reshape(1, -1))
                inside_ad = float(dists.mean()) <= float(threshold)
            except Exception:
                pass

        return delta_p, inside_ad
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# A. Structural modification suggestions
# ---------------------------------------------------------------------------

def suggest_modifications(
    smiles: str,
    model,
    explainer,
    bit_db: dict,
    aggregate_stats: dict,
    radius: int = 3,
    n_bits: int = 2048,
    ad_model=None,
) -> dict:
    """SHAP-based suggestions to improve molecular activity.

    Algorithm
    ---------
    1. Run predict_and_interpret with top_n=20.
    2. For each bit in top_bits classify:
       - bit ON  and shap < -0.001  → type="remove"  (substructure hurts activity)
       - bit OFF and shap < -0.001  → type="add"     (dominant sub from db would help if present)
       - bit ON  and shap >  0.001  → type="keep"    (favorable, retain in derivatives)
    3. Scan aggregate_stats["active_exclusive_bits"] for bits not in this molecule
       but found in >90% of actives → type="consider".
    4. Priority order: remove(0) > add(1) > keep(2) > consider(3), then by |shap|.
    5. Return top 15 suggestions.

    Returns
    -------
    dict:
        molecule    – predict_and_interpret result
        suggestions – list of suggestion dicts

    Each suggestion:
        type        – "remove" | "add" | "keep" | "consider"
        bit         – "ECFP6_N"
        shap        – float SHAP value (0.0 for "consider" without SHAP context)
        substructure – str or None (dominant substructure for the bit)
        reason      – human-readable explanation
    """
    result = predict_and_interpret(smiles, model, explainer, bit_db,
                                   radius=radius, n_bits=n_bits, top_n=20)
    if "error" in result:
        return {"molecule": result, "suggestions": []}

    current_p: float = float(result.get("probability_active", 0.5))

    # Collect suggestions from top_bits
    suggestions: list[dict] = []
    _seen_bits: set[int] = set()

    for bit_info in result["top_bits"]:
        bit_idx: int = bit_info["bit_index"]
        bit_name: str = bit_info["bit"]
        shap_val: float = bit_info["shap_value"]
        bit_on: int = bit_info["bit_on"]
        _seen_bits.add(bit_idx)

        db: dict | None = bit_info.get("training_info")

        # Determine the representative substructure label
        sub_label: str | None = None
        mol_subs = bit_info.get("molecule_substructures", [])
        if mol_subs:
            sub_label = mol_subs[0].get("smiles")
        if sub_label is None and db:
            sub_label = db.get("dominant_substructure")

        active_ratio_str = (
            f"{db['active_ratio']:.1%}" if db else "unknown"
        )

        if bit_on == 1 and shap_val < -0.001:
            # This substructure is present and hurts activity
            reason = (
                f"Bit ON with negative SHAP ({shap_val:+.4f}): substructure "
                f"\"{sub_label or 'unknown'}\" is associated with inactivity "
                f"(training active ratio: {active_ratio_str}). "
                "Removing or replacing this fragment may improve activity."
            )
            suggestions.append({
                "type": "remove",
                "bit": bit_name,
                "shap": shap_val,
                "substructure": sub_label,
                "reason": reason,
            })

        elif bit_on == 0 and shap_val < -0.001:
            # Bit is absent; its absence is penalising — adding the dominant sub could help
            add_sub: str | None = db.get("dominant_substructure") if db else None
            reason = (
                f"Bit OFF with negative SHAP ({shap_val:+.4f}): the absence of "
                f"\"{add_sub or 'unknown'}\" contributes to inactivity. "
                f"Training active ratio when bit=1: {active_ratio_str}. "
                "Introducing this fragment may improve activity."
            )
            suggestions.append({
                "type": "add",
                "bit": bit_name,
                "shap": shap_val,
                "substructure": add_sub,
                "reason": reason,
            })

        elif bit_on == 1 and shap_val > 0.001:
            # Favorable substructure; advise keeping it in derivatives
            reason = (
                f"Bit ON with positive SHAP ({shap_val:+.4f}): substructure "
                f"\"{sub_label or 'unknown'}\" contributes to activity "
                f"(training active ratio: {active_ratio_str}). "
                "Retain this fragment in derivative designs."
            )
            suggestions.append({
                "type": "keep",
                "bit": bit_name,
                "shap": shap_val,
                "substructure": sub_label,
                "reason": reason,
            })

    # Collect "consider" suggestions from active_exclusive_bits not in molecule
    for excl_entry in aggregate_stats.get("active_exclusive_bits", []):
        bit_idx = excl_entry["bit"]
        if bit_idx in _seen_bits:
            continue  # already covered above
        # Only suggest if active_ratio > 0.90 (definition of exclusive)
        if excl_entry.get("active_ratio", 0.0) <= 0.90:
            continue
        dom_sub = excl_entry.get("dominant_sub")
        reason = (
            f"This bit is found in {excl_entry['active_ratio']:.1%} of active "
            f"training molecules (n={excl_entry['n_activations']} activations) "
            f"but is NOT present in the query molecule. "
            f"Dominant substructure: \"{dom_sub or 'unknown'}\". "
            "Consider incorporating this fragment."
        )
        suggestions.append({
            "type": "consider",
            "bit": f"ECFP6_{bit_idx}",
            "shap": 0.0,
            "substructure": dom_sub,
            "reason": reason,
        })

    # ── Validate and cap add / remove candidates (max 2 each) ────────────────
    mol_obj = Chem.MolFromSmiles(smiles)

    validated_remove: list[dict] = []
    validated_add: list[dict] = []

    remove_candidates = sorted(
        [s for s in suggestions if s["type"] == "remove"],
        key=lambda s: abs(s["shap"]), reverse=True,
    )
    add_candidates = sorted(
        [s for s in suggestions if s["type"] == "add"],
        key=lambda s: abs(s["shap"]), reverse=True,
    )

    if mol_obj is not None:
        for s in remove_candidates:
            if len(validated_remove) >= 2:
                break
            if not s.get("substructure"):
                continue
            bit_idx = int(s["bit"].split("_")[-1])
            mod_smi = validate_remove_suggestion(mol_obj, bit_idx, s["substructure"],
                                                  radius=radius, n_bits=n_bits)
            if mod_smi is not None:
                s["validated"] = True
                s["modified_smiles"] = mod_smi
                delta_p, inside_ad = _compute_mod_metrics(
                    mod_smi, model, ad_model, radius, n_bits, current_p
                )
                s["delta_p_active"] = delta_p
                s["modified_inside_ad"] = inside_ad
                validated_remove.append(s)

        for s in add_candidates:
            if len(validated_add) >= 2:
                break
            if not s.get("substructure"):
                continue
            bit_idx = int(s["bit"].split("_")[-1])
            mod_smi = validate_add_suggestion(mol_obj, bit_idx, s["substructure"],
                                               radius=radius, n_bits=n_bits)
            if mod_smi is not None:
                s["validated"] = True
                s["modified_smiles"] = mod_smi
                delta_p, inside_ad = _compute_mod_metrics(
                    mod_smi, model, ad_model, radius, n_bits, current_p
                )
                s["delta_p_active"] = delta_p
                s["modified_inside_ad"] = inside_ad
                validated_add.append(s)

    keep_suggestions = [s for s in suggestions if s["type"] in ("keep", "consider")]
    keep_suggestions.sort(key=lambda s: -abs(s["shap"]))

    final_suggestions = validated_remove + validated_add + keep_suggestions[:2]

    return {
        "molecule": result,
        "suggestions": final_suggestions,
    }


def format_suggestions_context(result: dict) -> str:
    """Format suggestions as grounded text for LLM injection.

    Starts with '=== STRUCTURAL MODIFICATION SUGGESTIONS ==='.
    """
    molecule = result.get("molecule", {})
    suggestions = result.get("suggestions", [])

    if "error" in molecule:
        return f"PIPELINE ERROR: {molecule['error']}"

    _type_icons = {
        "remove":   "[REMOVE]",
        "add":      "[ADD]",
        "keep":     "[KEEP]",
        "consider": "[CONSIDER]",
    }

    lines = [
        "=== VALIDATED STRUCTURAL MODIFICATION SUGGESTIONS ===",
        "",
        f"Molecule   : {molecule.get('canonical_smiles', 'n/a')}",
        f"Prediction : {molecule.get('prediction', 'n/a')}",
        f"P(active)  : {molecule.get('probability_active', 0.0):.4f}",
        f"P(inactive): {molecule.get('probability_inactive', 0.0):.4f}",
        "",
        f"Total suggestions: {len(suggestions)}",
        "Note: add/remove suggestions have been computationally validated — "
        "the modified_smiles field shows a molecule where the bit change was confirmed.",
        "",
    ]

    if not suggestions:
        lines.append("No actionable suggestions generated.")
        return "\n".join(lines)

    for i, sug in enumerate(suggestions, 1):
        icon = _type_icons.get(sug["type"], f"[{sug['type'].upper()}]")
        shap_str = f"  SHAP: {sug['shap']:+.4f}" if sug["shap"] != 0.0 else ""
        lines.append(
            f"{i}. {icon}  {sug['bit']}"
            + (f"  |  Substructure: \"{sug['substructure']}\"" if sug["substructure"] else "")
            + shap_str
        )
        lines.append(f"   {sug['reason']}")
        if sug.get("modified_smiles"):
            lines.append(f"   Validated SMILES: {sug['modified_smiles']}")
        if sug.get("delta_p_active") is not None:
            lines.append(f"   ΔP(active): {sug['delta_p_active']:+.4f}")
        if sug.get("modified_inside_ad") is not None:
            ad_str = "Inside AD ✓" if sug["modified_inside_ad"] else "Outside AD ⚠"
            lines.append(f"   AD status: {ad_str}")
        lines.append("")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# B. Substructure activity search
# ---------------------------------------------------------------------------

def search_substructure_activity(query: str, bit_db: dict) -> dict:
    """Search the bit database for substructures matching the natural-language query.

    Strategy (applied in order)
    ---------------------------
    1. Match query words against _NAME_TO_FRAGMENTS keys → collect SMARTS fragments.
    2. If no names matched, extract token-like strings from query and try as SMARTS.
    3. Substring string matching: compare each fragment against all sub_smi in bit_db.
    4. SMARTS substructure matching via RDKit (wrapped in try/except for invalid SMARTS).
    5. Deduplicate by bit index.
    6. Sort by active_ratio descending.

    Returns
    -------
    dict:
        query               – original query string
        fragments_searched  – list of SMARTS strings that were tried
        matched_names       – list of fragment names recognised
        n_matching_bits     – int total bits matched
        avg_active_ratio    – float average active_ratio across matched bits
        total_in_actives    – int sum of active_freq across matched bits
        total_in_inactives  – int sum of inactive_freq across matched bits
        matches             – list of match dicts sorted by active_ratio desc

    Each match dict:
        bit         – int
        substructure – str (the matching sub_smi from the db)
        count       – int activation count for this substructure within the bit
        active_ratio – float (from bit_db)
        active_freq  – int
        inactive_freq – int
        total        – int total_activations for this bit
    """
    query_lower = query.lower()

    # Step 1: name matching
    matched_names: list[str] = []
    fragments: list[str] = []
    for name, frags in _NAME_TO_FRAGMENTS.items():
        if name in query_lower:
            matched_names.append(name)
            fragments.extend(frags)

    # Deduplicate fragment list while preserving order
    seen_frags: set[str] = set()
    unique_fragments: list[str] = []
    for f in fragments:
        if f not in seen_frags:
            unique_fragments.append(f)
            seen_frags.add(f)

    # Step 2: if no names matched, extract tokens and use as candidate SMARTS
    if not unique_fragments:
        tokens = re.findall(r"[A-Za-z0-9@#+\-\[\]()=/#\\%]+", query)
        for tok in tokens:
            if len(tok) >= 2 and tok not in seen_frags:
                unique_fragments.append(tok)
                seen_frags.add(tok)

    fragments_searched = unique_fragments

    # Classify fragments into two tiers:
    #   Tier 1 — single-atom fragments (e.g. "Cl", "F", "N"): use direct GetSymbol()
    #            check to avoid SMARTS engine false positives on simple element symbols.
    #   Tier 2 — multi-atom fragments (e.g. "c1ccccc1"): use SMARTS HasSubstructMatch.
    atom_symbols: list[str] = []     # capitalised element symbols, e.g. ["Cl", "F"]
    smarts_mols: list[tuple[str, Chem.Mol]] = []  # (frag_str, qmol) for multi-atom frags

    for frag in fragments_searched:
        # Try parsing as SMILES to detect single-atom fragments reliably
        try:
            test_mol = Chem.MolFromSmiles(frag)
            if test_mol is not None and test_mol.GetNumAtoms() == 1:
                atom_symbols.append(test_mol.GetAtomWithIdx(0).GetSymbol())
                continue
        except Exception:
            pass
        # Multi-atom or non-SMILES token: compile as SMARTS
        try:
            qmol = Chem.MolFromSmarts(frag)
            if qmol is not None:
                smarts_mols.append((frag, qmol))
        except Exception:
            pass

    # Step 3 + 4: search through bit_db
    # For each substructure in each bit, check if THAT specific substructure contains
    # the queried fragment. Never report a bit with a non-matching substructure.
    matched_bits: dict[int, tuple[dict, str, int]] = {}  # bit_idx → (info, matching_sub, count)

    for bit_idx, info in bit_db.items():
        substructures: dict[str, int] = info.get("substructures", {})
        best_match_sub: str | None = None
        best_match_count: int = 0

        for sub_smi, sub_count in substructures.items():
            # Parse this substructure
            try:
                sub_mol = Chem.MolFromSmiles(sub_smi)
            except Exception:
                sub_mol = None

            if sub_mol is None:
                continue

            # Does THIS substructure contain the queried fragment?
            sub_matched = False

            # Tier 1: direct atom symbol check — reliable for Cl, F, Br, N, O, etc.
            if not sub_matched and atom_symbols:
                mol_symbols = {a.GetSymbol() for a in sub_mol.GetAtoms()}
                if any(sym in mol_symbols for sym in atom_symbols):
                    sub_matched = True

            # Tier 2: SMARTS substructure match for multi-atom fragments
            if not sub_matched and smarts_mols:
                for _frag_smi, qmol in smarts_mols:
                    try:
                        if sub_mol.HasSubstructMatch(qmol):
                            sub_matched = True
                            break
                    except Exception:
                        pass

            # Tier 3: string containment fallback when no matchers are available
            if not sub_matched and not atom_symbols and not smarts_mols:
                for frag in fragments_searched:
                    if frag in sub_smi:
                        sub_matched = True
                        break

            # Track the highest-count substructure that actually matches
            if sub_matched and (best_match_sub is None or sub_count > best_match_count):
                best_match_sub = sub_smi
                best_match_count = sub_count

        if best_match_sub is not None:
            matched_bits[int(bit_idx)] = (info, best_match_sub, best_match_count)

    # Sort by active_ratio descending
    sorted_matches = sorted(
        matched_bits.items(),
        key=lambda kv: kv[1][0].get("active_ratio", 0.0),
        reverse=True,
    )

    # Build output match list
    matches: list[dict] = []
    total_in_actives = 0
    total_in_inactives = 0
    active_ratio_sum = 0.0

    for bit_idx, (info, matching_sub, matching_count) in sorted_matches:
        active_freq = info.get("active_freq", 0)
        inactive_freq = info.get("inactive_freq", 0)
        active_ratio = float(info.get("active_ratio", 0.0))
        total_activations = info.get("total_activations", 0)

        total_in_actives += active_freq
        total_in_inactives += inactive_freq
        active_ratio_sum += active_ratio

        matches.append({
            "bit": bit_idx,
            "substructure": matching_sub,   # the sub_smi that actually matched the query
            "count": matching_count,
            "active_ratio": active_ratio,
            "active_freq": active_freq,
            "inactive_freq": inactive_freq,
            "total": total_activations,
        })

    n_matching_bits = len(matches)
    avg_active_ratio = (active_ratio_sum / n_matching_bits) if n_matching_bits > 0 else 0.0

    return {
        "query": query,
        "fragments_searched": fragments_searched,
        "matched_names": matched_names,
        "n_matching_bits": n_matching_bits,
        "avg_active_ratio": avg_active_ratio,
        "total_in_actives": total_in_actives,
        "total_in_inactives": total_in_inactives,
        "matches": matches,
    }


def format_substructure_context(result: dict) -> str:
    """Format substructure search result as grounded text for LLM injection.

    Starts with '=== SUBSTRUCTURE ACTIVITY ANALYSIS ==='.
    Shows avg active ratio, top 15 matches, and an overall verdict.
    """
    lines = [
        "=== SUBSTRUCTURE ACTIVITY ANALYSIS ===",
        "",
        f"Query              : \"{result['query']}\"",
        f"Fragments searched : {result['fragments_searched']}",
        f"Names recognised   : {result['matched_names']}",
        f"Matching bits found: {result['n_matching_bits']}",
    ]

    if result["n_matching_bits"] == 0:
        lines.append("")
        lines.append("No matching substructures found in the training bit database.")
        return "\n".join(lines)

    lines += [
        f"Avg active ratio   : {result['avg_active_ratio']:.1%}",
        f"Total in actives   : {result['total_in_actives']}",
        f"Total in inactives : {result['total_in_inactives']}",
        "",
        "--- Top 15 Matching Bits (sorted by active_ratio) ---",
        "",
    ]

    for i, match in enumerate(result["matches"][:15], 1):
        sub_str = f"\"{match['substructure']}\"" if match["substructure"] else "n/a"
        lines.append(
            f"  {i:>2}. Bit {match['bit']:>4}  sub={sub_str:<35s}  "
            f"active_ratio={match['active_ratio']:.1%}  "
            f"active={match['active_freq']}  inactive={match['inactive_freq']}  "
            f"total={match['total']}"
        )

    # Overall verdict
    avg = result["avg_active_ratio"]
    lines.append("")
    if avg >= 0.75:
        verdict = (
            "VERDICT: This substructure/fragment type is STRONGLY associated with "
            f"active compounds (avg active ratio {avg:.1%} across matching bits)."
        )
    elif avg >= 0.55:
        verdict = (
            "VERDICT: This substructure/fragment type is MODERATELY associated with "
            f"active compounds (avg active ratio {avg:.1%} across matching bits)."
        )
    elif avg <= 0.25:
        verdict = (
            "VERDICT: This substructure/fragment type is STRONGLY associated with "
            f"INACTIVE compounds (avg active ratio {avg:.1%} across matching bits)."
        )
    elif avg <= 0.45:
        verdict = (
            "VERDICT: This substructure/fragment type is MODERATELY associated with "
            f"INACTIVE compounds (avg active ratio {avg:.1%} across matching bits)."
        )
    else:
        verdict = (
            "VERDICT: Mixed signal — this substructure/fragment type shows no clear "
            f"association with either active or inactive compounds "
            f"(avg active ratio {avg:.1%})."
        )
    lines.append(verdict)

    return "\n".join(lines)
