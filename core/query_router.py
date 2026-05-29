"""Classify user queries into typed categories for the molecular intelligence pipeline."""

from __future__ import annotations
import re
from typing import Optional
from rdkit import Chem

# Tier-1: SMILES between single or double quotes
_QUOTED_PAT = re.compile(r'["\']([^"\']+)["\']')

# Tier-2: unquoted token that looks chemistry-like (≥6 chars)
_SMILES_PAT = re.compile(r'[A-Za-z0-9@+\-\[\]()\\/\#=.%]{6,}')

_ECFP_BIT_PAT = re.compile(
    r'(?:ecfp\d*[_\s]|morgan[_\s](?:bit[_\s])?|(?:^|\s)bit[_\s])(\d+)',
    re.IGNORECASE,
)

_SUBSTRUCTURE_TERMS = re.compile(
    r'chlorine|fluorine|bromine|chloro|fluoro|bromo|methyl|hydroxyl|amino|nitro'
    r'|piperazin|piperidin|morpholin|pyridin|pyrimidin|imidazol'
    r'|pyrazol|phenyl|benzene|aromatic ring|carbonyl|amide'
    r'|sulfonyl|heterocycl|does .* favor|is .* associated'
    r'|effect of|impact of|role of|which group|what group',
    re.IGNORECASE,
)

_AD_TERMS = re.compile(
    r'applicability domain| ad |reliable|trustworthy|trust |'
    r'within domain|outside domain|can i trust|is it reliable',
    re.IGNORECASE,
)

_MOL_EDIT_TERMS = re.compile(
    r'add (?:\w+ )*to |remove the |replace |substitute |'
    r'what if i add|what if i remove|what if i replace|what would happen if',
    re.IGNORECASE,
)

_SUGGESTION_TERMS = re.compile(
    r'suggest|how to improve|how can i improve|optimize|what modifications|'
    r'make it active|increase activity|improve activity|make more active|scaffold hop',
    re.IGNORECASE,
)

_DESIGN_TERMS = re.compile(
    r'design suggestion|generate variant|brics|scaffold variation|'
    r'design mode|run design|design engine|enumerate variant|'
    r'generate analog|generate analogue|generate derivative',
    re.IGNORECASE,
)

_AGGREGATE_TERMS = re.compile(
    r'most frequent|most common|how many bits|top substructures|correlated with|'
    r'exclusive to|collision|ambiguous bit|training set|in training|across all|which bits|'
    r'appears most|most.*active|most.*inactive|in inactive|in active compound',
    re.IGNORECASE,
)


def _iter_smiles_candidates(query: str):
    """Yield SMILES candidate strings from query in priority order.

    Tier 1 — quoted strings (highest confidence): anything between ' or ".
    Tier 2 — unquoted tokens that contain at least one non-letter character
              (real SMILES always have digits, parentheses, =, #, @ etc.).
    Pure alphabetic tokens (English words) are never yielded, so they never
    reach Chem.MolFromSmiles and no "SMILES Parse Error" is emitted.
    """
    # Tier 1: quoted
    for m in _QUOTED_PAT.finditer(query):
        yield m.group(1)
    # Tier 2: unquoted, chemistry-like
    for candidate in _SMILES_PAT.findall(query):
        if not candidate.isalpha():
            yield candidate


def extract_smiles(query: str) -> Optional[str]:
    """Return the first valid SMILES found in query, or None.

    Checks quoted strings first (tier 1), then unquoted tokens (tier 2).
    English words are never tested with RDKit.
    """
    for candidate in _iter_smiles_candidates(query):
        mol = Chem.MolFromSmiles(candidate)
        if mol is not None:
            return candidate
    return None


def detect_two_smiles(query: str) -> Optional[list[str]]:
    """Find up to 2 valid SMILES in query (including identical ones for compare intents).

    Returns a list of exactly 2 valid SMILES (may be the same string), or None.
    Identical-molecule detection happens downstream via canonical SMILES comparison.
    """
    found: list[str] = []
    for candidate in _iter_smiles_candidates(query):
        mol = Chem.MolFromSmiles(candidate)
        if mol is not None:
            found.append(candidate)
            if len(found) >= 2:
                return found
    return None


def classify_query(query: str) -> tuple[str, dict]:
    """Classify a user query into a typed category for the molecular intelligence pipeline.

    Classification is performed in priority order. The first matching rule wins.

    Parameters
    ----------
    query:
        Raw user query string.

    Returns
    -------
    A tuple of (query_type, params_dict) where query_type is one of:
    'comparison', 'bit_query', 'ad_check', 'mol_edit', 'suggestions',
    'substructure_search', 'aggregate_query', 'molecule_query', 'general_query'.
    """
    ql = query.lower()

    # 1. comparison — two distinct valid SMILES present
    two = detect_two_smiles(query)
    if two is not None:
        return "comparison", {"smiles1": two[0], "smiles2": two[1]}

    # 2. bit_query — ECFP bit pattern present, but NOT accompanied by a SHAP value
    bit_match = _ECFP_BIT_PAT.search(query)
    if bit_match:
        has_shap_val = bool(
            re.search(r'shap(?:\s+value)?(?:\s+(?:of|=|:))?\s*[+-]?\d', ql)
        )
        if not has_shap_val:
            return "bit_query", {"bit_idx": int(bit_match.group(1))}

    # 3. ad_check — applicability domain / trust keywords
    if _AD_TERMS.search(query):
        smiles = extract_smiles(query)
        return "ad_check", {"smiles": smiles}

    # 4. mol_edit — editing intent AND a valid SMILES present
    if _MOL_EDIT_TERMS.search(query):
        smiles = extract_smiles(query)
        if smiles is not None:
            return "mol_edit", {"smiles": smiles, "edit": query}

    # 5a. design_query — explicit design/variant-generation intent (checked before suggestions)
    if _DESIGN_TERMS.search(query):
        smiles = extract_smiles(query)
        return "design_query", {"smiles": smiles}

    # 5b. suggestions — optimisation/suggestion intent AND a valid SMILES present
    if _SUGGESTION_TERMS.search(query):
        smiles = extract_smiles(query)
        if smiles is not None:
            return "suggestions", {"smiles": smiles}

    # 6. substructure_search — named substructure or group-effect keywords
    if _SUBSTRUCTURE_TERMS.search(query):
        return "substructure_search", {"query": query}

    # 7. aggregate_query — dataset-level or bit-population questions
    if _AGGREGATE_TERMS.search(query):
        return "aggregate_query", {"query": query}

    # 8. molecule_query — a valid SMILES is present (but no higher priority matched)
    smiles = extract_smiles(query)
    if smiles is not None:
        return "molecule_query", {"smiles": smiles}

    # 9. general_query — fallback
    return "general_query", {}
