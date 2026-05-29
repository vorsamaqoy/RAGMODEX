"""design_engine.py — BRICS-based molecular variant generation and evaluation.

Fully self-contained: no Streamlit imports, no external I/O side-effects.
All heavy RDKit and numpy imports are deferred inside functions so the module
can be imported cheaply even when RDKit is slow to initialise.

Public API
----------
generate_variants(mol, n_variants)           → list[Chem.Mol]
predict_batch(model, mols, radius, n_bits)   → np.ndarray
rank_variants(base_prob, pairs, labels)      → list[DesignCandidate]
extract_transformation(base_mol, new_mol)    → str
find_similar_molecules(query_fp, ...)        → list[dict]
run_design_pipeline(smiles, model, ...)      → dict
format_design_context(result, top_n)        → str
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DesignCandidate:
    """A single structural variant with prediction metadata."""

    smiles: str
    probability: float
    delta: float           # probability − base_prob
    source: str            # "brics" | "substitution" | "attachment" | "unknown"
    transformation: str    # human-readable structural diff
    rank: int = 0
    ad_score: float = 1.0  # Tanimoto-based applicability domain score
    parent_smiles: Optional[str] = None   # SMILES of the molecule this was generated from
    iteration: int = 0                    # pipeline iteration at which this was generated


# ---------------------------------------------------------------------------
# Atom-swap rules — (symbol_to_replace, replacement, human_label)
# ---------------------------------------------------------------------------

_ATOM_SWAPS: list[tuple[str, str, str]] = [
    ("Cl", "F",  "Cl→F"),
    ("Cl", "Br", "Cl→Br"),
    ("Cl", "I",  "Cl→I"),
    ("F",  "Cl", "F→Cl"),
    ("Br", "Cl", "Br→Cl"),
    ("Br", "F",  "Br→F"),
    ("O",  "S",  "O→S (thio)"),
    ("S",  "O",  "S→O (oxo)"),
]

# Substituents appended to aromatic C with a free H
# (smiles_fragment, human_label)
_SUBSTITUENTS: list[tuple[str, str]] = [
    ("F",          "add F"),
    ("Cl",         "add Cl"),
    ("C",          "add methyl"),
    ("OC",         "add methoxy"),
    ("N",          "add amino"),
    ("C(F)(F)F",   "add CF3"),
    ("C#N",        "add cyano"),
    ("C(=O)N",     "add amide"),
    ("S(=O)(=O)N", "add sulfonamide"),
    ("C(=O)O",     "add carboxyl"),
]


# ---------------------------------------------------------------------------
# Step 1 — Generate molecular variants
# ---------------------------------------------------------------------------

def generate_variants(mol, n_variants: int = 200) -> list:
    """Generate up to *n_variants* chemically valid structural variants.

    Three complementary strategies are combined:

    1. **BRICS recombination** — decompose the molecule into BRICS fragments,
       then rebuild with RDKit's ``BRICSBuild`` (self-recombination).
    2. **Atom substitution** — systematically replace one atom symbol at a time
       in the SMILES string (halogen swaps, O↔S, etc.).
    3. **Substituent attachment** — bond small fragments to aromatic carbons
       that carry a free hydrogen.

    All results are sanitized with RDKit and deduplicated by canonical SMILES.
    The original molecule is always excluded from the output.

    Parameters
    ----------
    mol : rdkit.Chem.Mol
        Sanitized input molecule.
    n_variants : int
        Hard cap on returned variants.

    Returns
    -------
    list[rdkit.Chem.Mol]
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem, BRICS, RWMol

    seen: set[str] = set()
    results: list = []
    sources: list[str] = []

    original_smi = Chem.MolToSmiles(mol)
    seen.add(original_smi)

    def _try_add(candidate_smi: str, source: str):
        if len(results) >= n_variants or candidate_smi in seen:
            return
        m = Chem.MolFromSmiles(candidate_smi)
        if m is None:
            return
        try:
            Chem.SanitizeMol(m)
        except Exception:
            return
        canon = Chem.MolToSmiles(m)
        if canon not in seen:
            seen.add(canon)
            results.append(m)
            sources.append(source)

    # ── Strategy 1: BRICS recombination ────────────────────────────────────
    try:
        frags_raw = BRICS.BRICSDecompose(mol)
        frags = [Chem.MolFromSmiles(f) for f in frags_raw]
        frags = [f for f in frags if f is not None]
        if frags:
            for new_mol in BRICS.BRICSBuild(frags):
                if len(results) >= n_variants:
                    break
                try:
                    Chem.SanitizeMol(new_mol)
                    _try_add(Chem.MolToSmiles(new_mol), "brics")
                except Exception:
                    continue
    except Exception:
        pass

    # ── Strategy 2: Atom substitutions ─────────────────────────────────────
    smi = original_smi
    for old_sym, new_sym, label in _ATOM_SWAPS:
        if len(results) >= n_variants:
            break
        if old_sym not in smi:
            continue
        # Replace each occurrence independently (up to 5 per type)
        idx = 0
        count = 0
        while count < 5 and len(results) < n_variants:
            pos = smi.find(old_sym, idx)
            if pos == -1:
                break
            candidate = smi[:pos] + new_sym + smi[pos + len(old_sym):]
            _try_add(candidate, "substitution")
            idx = pos + 1
            count += 1

    # ── Strategy 3: Substituent attachment to aromatic C ───────────────────
    try:
        ar_carbons = [
            a.GetIdx()
            for a in mol.GetAtoms()
            if a.GetAtomicNum() == 6
            and a.GetIsAromatic()
            and a.GetTotalNumHs() > 0
        ]
        for sub_smi, sub_label in _SUBSTITUENTS:
            if len(results) >= n_variants:
                break
            sub_mol = Chem.MolFromSmiles(sub_smi)
            if sub_mol is None:
                continue
            n_orig = mol.GetNumAtoms()
            for atom_idx in ar_carbons[:4]:   # at most 4 attachment sites
                if len(results) >= n_variants:
                    break
                try:
                    combined = Chem.CombineMols(mol, sub_mol)
                    rw = Chem.RWMol(combined)
                    rw.AddBond(atom_idx, n_orig, Chem.BondType.SINGLE)
                    Chem.SanitizeMol(rw)
                    _try_add(Chem.MolToSmiles(rw), "attachment")
                except Exception:
                    continue
    except Exception:
        pass

    return results[:n_variants]


# ---------------------------------------------------------------------------
# Step 2 — Batch prediction
# ---------------------------------------------------------------------------

def predict_batch(
    model: Any,
    mols: list,
    radius: int = 3,
    n_bits: int = 2048,
) -> np.ndarray:
    """Return P(active) for every molecule in *mols*.

    Parameters
    ----------
    model : sklearn classifier with ``predict_proba``
    mols : list[Chem.Mol]
    radius, n_bits : Morgan fingerprint parameters (must match training)

    Returns
    -------
    np.ndarray of shape (n_mols,) — float64 P(active).
    Molecules whose fingerprint could not be computed get probability 0.
    """
    from rdkit.Chem import AllChem, DataStructs

    if not mols or model is None:
        return np.zeros(len(mols) if mols else 0, dtype=float)

    fp_rows: list[np.ndarray] = []
    valid: list[bool] = []

    for mol in mols:
        try:
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
            arr = np.zeros(n_bits, dtype=np.int32)
            DataStructs.ConvertToNumpyArray(fp, arr)
            fp_rows.append(arr)
            valid.append(True)
        except Exception:
            fp_rows.append(np.zeros(n_bits, dtype=np.int32))
            valid.append(False)

    X = np.vstack(fp_rows)
    try:
        proba = model.predict_proba(X)[:, 1].astype(float)
    except Exception:
        proba = np.zeros(len(mols), dtype=float)

    # Zero-out molecules whose fingerprint computation failed
    for i, ok in enumerate(valid):
        if not ok:
            proba[i] = 0.0

    return proba


# ---------------------------------------------------------------------------
# Step 3 — Rank variants
# ---------------------------------------------------------------------------

def rank_variants(
    base_prob: float,
    mol_prob_pairs: list[tuple],
    source_labels: Optional[list[str]] = None,
) -> list[DesignCandidate]:
    """Rank (mol, probability) pairs by descending improvement over *base_prob*.

    Parameters
    ----------
    base_prob : float — P(active) of the original molecule
    mol_prob_pairs : list[(Chem.Mol, float)]
    source_labels : optional parallel list of source strings

    Returns
    -------
    list[DesignCandidate] sorted by delta descending.
    """
    from rdkit import Chem

    candidates: list[DesignCandidate] = []
    for i, (mol, prob) in enumerate(mol_prob_pairs):
        try:
            smi = Chem.MolToSmiles(mol)
        except Exception:
            continue
        src = (source_labels[i] if source_labels and i < len(source_labels) else "unknown")
        candidates.append(DesignCandidate(
            smiles=smi,
            probability=float(prob),
            delta=float(prob) - float(base_prob),
            source=src,
            transformation="",   # filled in by run_design_pipeline
        ))

    candidates.sort(key=lambda c: c.delta, reverse=True)
    for rank, c in enumerate(candidates, 1):
        c.rank = rank

    return candidates


# ---------------------------------------------------------------------------
# Step 4 — Extract transformation description
# ---------------------------------------------------------------------------

def extract_transformation(base_mol, new_mol) -> str:
    """Human-readable description of the structural change from *base_mol* to *new_mol*.

    Uses atom-count deltas, ring counts, and per-element census.
    Falls back to Tanimoto if no significant differences are detected.

    Returns a compact comma-joined string, e.g.:
    ``"+1 aromatic ring, +2 Cl, −1 O"``
    """
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors

    if base_mol is None or new_mol is None:
        return "unknown modification"

    try:
        def _count_elem(mol, atomic_num: int) -> int:
            return sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == atomic_num)

        parts: list[str] = []

        # Heavy-atom delta
        da = new_mol.GetNumHeavyAtoms() - base_mol.GetNumHeavyAtoms()
        if da > 4:
            parts.append(f"+{da} atoms")
        elif da < -4:
            parts.append(f"{da} atoms")

        # Aromatic-ring delta
        dar = (rdMolDescriptors.CalcNumAromaticRings(new_mol)
               - rdMolDescriptors.CalcNumAromaticRings(base_mol))
        if dar > 0:
            parts.append(f"+{dar} arom. ring(s)")
        elif dar < 0:
            parts.append(f"{dar} arom. ring(s)")

        # Aliphatic-ring delta (exclude aromatic already counted)
        dr = (rdMolDescriptors.CalcNumRings(new_mol)
              - rdMolDescriptors.CalcNumRings(base_mol)) - dar
        if dr > 0:
            parts.append(f"+{dr} ring(s)")
        elif dr < 0:
            parts.append(f"{dr} ring(s)")

        # Per-element census: F, Cl, Br, I, O, N, S
        ELEMENTS = [(9, "F"), (17, "Cl"), (35, "Br"), (53, "I"),
                    (8, "O"), (7, "N"), (16, "S")]
        for anum, sym in ELEMENTS:
            d = _count_elem(new_mol, anum) - _count_elem(base_mol, anum)
            if d > 0:
                parts.append(f"+{d} {sym}")
            elif d < 0:
                parts.append(f"{d} {sym}")

        if not parts:
            # Tanimoto as last-resort descriptor
            from rdkit.Chem import AllChem, DataStructs
            fp1 = AllChem.GetMorganFingerprintAsBitVect(base_mol, 3, 2048)
            fp2 = AllChem.GetMorganFingerprintAsBitVect(new_mol, 3, 2048)
            tc = DataStructs.TanimotoSimilarity(fp1, fp2)
            parts.append(f"structural change (Tc={tc:.2f})")

        return ", ".join(parts)

    except Exception:
        return "structural modification"


# ---------------------------------------------------------------------------
# Applicability Domain scoring
# ---------------------------------------------------------------------------

def compute_ad_score(query_fp: np.ndarray, dataset_fps: np.ndarray) -> float:
    """Return mean Tanimoto to the 5 nearest training-set neighbours.

    A value near 1 means the molecule is well-represented in the training set;
    a value near 0 means it is very distant from anything the model was trained on.

    Returns 1.0 when *dataset_fps* is None/empty (conservative: assume in domain).
    """
    if dataset_fps is None or len(dataset_fps) == 0:
        return 1.0
    q  = query_fp.astype(np.float32)
    db = dataset_fps.astype(np.float32)
    intersection = db.dot(q)
    union = float(q.sum()) + db.sum(axis=1) - intersection
    tanimoto = np.where(union > 0, intersection / union, 0.0)
    top5 = np.sort(tanimoto)[::-1][:5]
    return float(np.mean(top5))


# ---------------------------------------------------------------------------
# Pharmacophore core detection
# ---------------------------------------------------------------------------

def identify_protected_atoms(mol, explainer: Any, radius: int, n_bits: int) -> set:
    """Identify atom indices that belong to the pharmacophore core.

    The strategy combines two sources:

    1. **SHAP-based** — only the top-25% highest-SHAP positive bits are used.
       Only each bit's *center atom* is protected (not the full radius-N
       environment), keeping the protected set focused.
    2. **Murcko scaffold** — ring systems and the linker atoms are always
       protected regardless of SHAP availability.

    A hard cap of 70 % of total heavy atoms is enforced.  If the combined
    SHAP + Murcko set exceeds this, the function falls back to pure Murcko so
    that at least 30 % of positions remain mutable.

    Parameters
    ----------
    mol       : rdkit.Chem.Mol — sanitized input molecule
    explainer : shap.TreeExplainer or None
    radius    : Morgan fingerprint radius
    n_bits    : folded fingerprint size

    Returns
    -------
    set of int — atom indices to protect.  Empty set if detection fails entirely.
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    n_atoms     = mol.GetNumAtoms()
    max_protect = max(1, int(0.70 * n_atoms))

    murcko_atoms: set = set()
    try:
        from rdkit.Chem.Scaffolds import MurckoScaffold
        core = MurckoScaffold.GetScaffoldForMol(mol)
        if core is not None and core.GetNumAtoms() > 0:
            match = mol.GetSubstructMatch(core)
            if match:
                murcko_atoms = set(match)
    except Exception:
        pass

    shap_atoms: set = set()
    if explainer is not None:
        try:
            fp_folded = _mol_to_fp(mol, radius, n_bits)
            if fp_folded is None:
                raise ValueError("fingerprint failed")

            raw = explainer.shap_values(fp_folded.reshape(1, -1))
            if isinstance(raw, list) and len(raw) >= 2:
                sv = np.array(raw[1]).flatten()
            elif hasattr(raw, "ndim") and raw.ndim == 3:
                sv = raw[0, :, 1]
            else:
                sv = np.array(raw).flatten()

            pos_bits = sorted(
                [(sv[i], i) for i in range(n_bits) if sv[i] > 0 and fp_folded[i] == 1],
                reverse=True,
            )
            n_top = max(1, len(pos_bits) // 4)
            top_bits = {bit for _, bit in pos_bits[:n_top]}

            bi: dict = {}
            AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits, bitInfo=bi)
            for bit in top_bits:
                for atom_idx, _ in bi.get(bit, []):
                    shap_atoms.add(atom_idx)
        except Exception:
            pass

    combined = murcko_atoms | shap_atoms
    if len(combined) > max_protect:
        combined = murcko_atoms

    if combined:
        return combined

    return set()


def core_preserved(child_mol, parent_cores: list) -> bool:
    """Return True if *child_mol* contains at least one parent scaffold as a substructure.

    Parameters
    ----------
    child_mol    : rdkit.Chem.Mol — generated variant to test
    parent_cores : list[rdkit.Chem.Mol] — Murcko scaffolds of beam members

    Returns True when parent_cores is empty (nothing to protect).
    """
    if not parent_cores:
        return True
    try:
        return any(child_mol.HasSubstructMatch(c) for c in parent_cores)
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Diversity helpers for guided generation
# ---------------------------------------------------------------------------

def _tanimoto_fps(fp1: np.ndarray, fp2: np.ndarray) -> float:
    """Tanimoto coefficient between two binary fingerprint arrays."""
    a = fp1.astype(float)
    b = fp2.astype(float)
    intersection = np.dot(a, b)
    union = a.sum() + b.sum() - intersection
    return float(intersection / union) if union > 0 else 0.0


def _ring_heteroatom_variants(
    mol,
    n_variants: int,
    seen: set,
    protected_atoms: Optional[set] = None,
) -> list:
    """Bioisosteres: replace aromatic ring C with N (benzene → pyridine, etc.).

    Atoms in *protected_atoms* are never swapped.
    """
    from rdkit import Chem

    results: list = []
    ring_info = mol.GetRingInfo()
    ring_atom_sets = [set(r) for r in ring_info.AtomRings()]
    _protected = protected_atoms or set()

    for atom in mol.GetAtoms():
        if len(results) >= n_variants:
            break
        if atom.GetAtomicNum() != 6 or not atom.GetIsAromatic():
            continue
        if atom.GetIdx() in _protected:
            continue
        if sum(1 for rs in ring_atom_sets if atom.GetIdx() in rs) > 1:
            continue
        rw = Chem.RWMol(mol)
        try:
            a = rw.GetAtomWithIdx(atom.GetIdx())
            a.SetAtomicNum(7)
            a.SetNoImplicit(True)
            a.SetNumExplicitHs(0)
            Chem.SanitizeMol(rw)
            smi = Chem.MolToSmiles(rw)
            if smi not in seen:
                seen.add(smi)
                results.append(rw.GetMol())
        except Exception:
            pass
    return results


def _remove_terminal_variants(
    mol,
    n_variants: int,
    seen: set,
    protected_atoms: Optional[set] = None,
) -> list:
    """Strip terminal heavy atoms one at a time → smaller analogs.

    Atoms in *protected_atoms* (e.g. SHAP-positive terminal groups like CF3 on
    a key pharmacophore) are skipped.
    """
    from rdkit import Chem

    results: list = []
    _protected = protected_atoms or set()
    terminals = sorted(
        [
            a for a in mol.GetAtoms()
            if a.GetAtomicNum() != 1
            and a.GetDegree() == 1
            and a.GetIdx() not in _protected
        ],
        key=lambda a: a.GetAtomicNum(),
    )
    for atom in terminals:
        if len(results) >= n_variants:
            break
        rw = Chem.RWMol(mol)
        try:
            rw.RemoveAtom(atom.GetIdx())
            Chem.SanitizeMol(rw)
            smi = Chem.MolToSmiles(rw)
            if smi not in seen:
                seen.add(smi)
                results.append(rw.GetMol())
        except Exception:
            pass
    return results


_PERIPHERAL_SUBSTITUENTS: list[tuple[str, str]] = [
    ("F",           "add F"),
    ("Cl",          "add Cl"),
    ("C",           "add Me"),
    ("CC",          "add Et"),
    ("O",           "add OH"),
    ("OC",          "add OMe"),
    ("N",           "add NH2"),
    ("C(F)(F)F",    "add CF3"),
    ("C#N",         "add CN"),
    ("C(=O)N",      "add CONH2"),
    ("S(=O)(=O)N",  "add SO2NH2"),
    ("OC(F)(F)F",   "add OCF3"),
    ("CC(C)C",      "add iBu"),
    ("c1ccncc1",    "add 4-Pyr"),
    ("c1ccccc1",    "add Ph"),
]


def _peripheral_decoration_variants(
    mol,
    protected_atoms: set,
    n_variants: int,
    seen: set,
) -> list:
    """Attach small substituents exclusively to peripheral (non-protected) positions.

    Targets aromatic or sp3 carbons/nitrogens that carry at least one implicit H
    and are NOT in *protected_atoms*.  This explores R-group space without touching
    the pharmacophore core.

    Parameters
    ----------
    mol             : rdkit.Chem.Mol — seed molecule
    protected_atoms : set of atom indices to leave untouched
    n_variants      : maximum variants to return
    seen            : deduplication set (updated in-place)

    Returns
    -------
    list[rdkit.Chem.Mol]
    """
    import random
    from rdkit import Chem

    results: list = []
    _protected = protected_atoms or set()

    peripheral = [
        a.GetIdx() for a in mol.GetAtoms()
        if a.GetIdx() not in _protected
        and a.GetTotalNumHs() > 0
        and a.GetAtomicNum() in (6, 7)
    ]
    if not peripheral:
        return results

    random.shuffle(peripheral)
    subs = list(_PERIPHERAL_SUBSTITUENTS)
    random.shuffle(subs)

    n_orig = mol.GetNumAtoms()
    for atom_idx in peripheral:
        if len(results) >= n_variants:
            break
        for sub_smi, _ in subs:
            if len(results) >= n_variants:
                break
            sub_mol = Chem.MolFromSmiles(sub_smi)
            if sub_mol is None:
                continue
            try:
                combined = Chem.CombineMols(mol, sub_mol)
                rw = Chem.RWMol(combined)
                rw.AddBond(atom_idx, n_orig, Chem.BondType.SINGLE)
                Chem.SanitizeMol(rw)
                smi = Chem.MolToSmiles(rw.GetMol())
                if smi not in seen:
                    seen.add(smi)
                    results.append(rw.GetMol())
            except Exception:
                continue

    return results


def passes_druglikeness(mol, strict: bool = True) -> bool:
    """Test whether *mol* satisfies Lipinski-extended drug-likeness bounds.

    Two tiers are available:

    * **strict** (default) — enforces all five property bounds simultaneously.
    * **relaxed** — only the two most conservative checks (MW and logP).  Used
      as a fallback when the strict filter removes all candidates in an iteration.

    Parameters
    ----------
    mol    : rdkit.Chem.Mol — sanitized molecule
    strict : bool — True for five-property check, False for two-property fallback

    Returns
    -------
    bool — True if the molecule passes the selected tier.
           Returns True on any computation error (conservative: never exclude).
    """
    try:
        from rdkit.Chem import Descriptors
        mw   = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        if strict:
            hba  = Descriptors.NumHAcceptors(mol)
            hbd  = Descriptors.NumHDonors(mol)
            rotb = Descriptors.NumRotatableBonds(mol)
            return (150 <= mw  <= 650
                    and -2.0 <= logp <= 6.0
                    and 0    <= hba  <= 12
                    and 0    <= hbd  <= 7
                    and 0    <= rotb <= 12)
        return mw <= 800 and logp <= 7.0
    except Exception:
        return True


def _shap_guided_variants(
    beam_mols: list,
    explainer: Any,
    bit_db: dict,
    model: Any,
    radius: int,
    n_bits: int,
    n_target: int,
    seen: set,
) -> list:
    """Generate structural variants guided by SHAP bit-importance values.

    For each beam molecule the function identifies:

    * **Pro-activity bits** — positive SHAP, currently OFF.  The dominant
      substructure from the bit database is attached to available aromatic
      carbons.  After attachment the fingerprint is recomputed and only
      molecules where the target bit actually flipped ON are kept.
    * **Anti-activity bits** — negative SHAP, currently ON.  The dominant
      substructure is deleted via ``DeleteSubstructs``.  Only molecules where
      the target bit actually flipped OFF are kept.

    Parameters
    ----------
    beam_mols : list[Chem.Mol] — current beam
    explainer : shap.TreeExplainer — cached in session_state
    bit_db    : dict — output of build_bit_database(), maps bit_idx → entry
    model     : sklearn estimator (not used here but kept for API symmetry)
    radius    : Morgan fingerprint radius
    n_bits    : fingerprint size
    n_target  : maximum variants to return
    seen      : set of canonical SMILES already generated (updated in-place)

    Returns
    -------
    list of (Chem.Mol, "shap_guided") tuples — may be empty if SHAP computation
    fails or bit-to-substructure mapping is sparse.
    """
    from rdkit import Chem

    results: list = []

    fps_list: list = []
    valid_mols: list = []
    for mol in beam_mols:
        fp = _mol_to_fp(mol, radius, n_bits)
        if fp is not None:
            fps_list.append(fp)
            valid_mols.append(mol)

    if not fps_list:
        return results

    X_beam = np.vstack(fps_list)

    try:
        raw_shap = explainer.shap_values(X_beam)
        if isinstance(raw_shap, list) and len(raw_shap) >= 2:
            shap_matrix = np.array(raw_shap[1])
        elif hasattr(raw_shap, "ndim") and raw_shap.ndim == 3:
            shap_matrix = raw_shap[:, :, 1]
        else:
            shap_matrix = np.array(raw_shap)
        if shap_matrix.ndim == 1:
            shap_matrix = shap_matrix[np.newaxis, :]
    except Exception:
        return results

    for mol_idx, (mol, fp) in enumerate(zip(valid_mols, fps_list)):
        if len(results) >= n_target:
            break

        _par_smi = Chem.MolToSmiles(mol)
        mol_shap = shap_matrix[mol_idx]
        fp_bool  = fp.astype(bool)

        pro_indices  = np.where((mol_shap > 0) & (~fp_bool))[0]
        pro_indices  = pro_indices[np.argsort(mol_shap[pro_indices])[::-1]][:10]

        anti_indices = np.where((mol_shap < 0) & fp_bool)[0]
        anti_indices = anti_indices[np.argsort(np.abs(mol_shap[anti_indices]))[::-1]][:5]

        n_orig = mol.GetNumAtoms()
        ar_carbons = [
            a.GetIdx() for a in mol.GetAtoms()
            if a.GetAtomicNum() == 6
            and a.GetIsAromatic()
            and a.GetTotalNumHs() > 0
        ]

        for bit in pro_indices:
            if len(results) >= n_target:
                break
            entry = bit_db.get(int(bit))
            if not entry:
                continue
            sub_smi = entry.get("dominant_substructure")
            if not sub_smi:
                continue
            sub_mol = Chem.MolFromSmiles(sub_smi)
            if sub_mol is None:
                continue
            for atom_idx in ar_carbons[:3]:
                if len(results) >= n_target:
                    break
                try:
                    combined = Chem.CombineMols(mol, sub_mol)
                    rw = Chem.RWMol(combined)
                    rw.AddBond(atom_idx, n_orig, Chem.BondType.SINGLE)
                    Chem.SanitizeMol(rw)
                    new_mol = rw.GetMol()
                    new_fp  = _mol_to_fp(new_mol, radius, n_bits)
                    if new_fp is not None and new_fp[int(bit)] == 1:
                        smi = Chem.MolToSmiles(new_mol)
                        if smi not in seen:
                            seen.add(smi)
                            results.append((new_mol, "shap_guided", _par_smi))
                except Exception:
                    continue

        for bit in anti_indices:
            if len(results) >= n_target:
                break
            entry = bit_db.get(int(bit))
            if not entry:
                continue
            sub_smi = entry.get("dominant_substructure")
            if not sub_smi:
                continue
            try:
                patt = Chem.MolFromSmarts(sub_smi)
                if patt is None:
                    patt = Chem.MolFromSmiles(sub_smi)
                if patt is None:
                    continue
                new_mol = Chem.DeleteSubstructs(mol, patt)
                if new_mol is None or new_mol.GetNumAtoms() == 0:
                    continue
                Chem.SanitizeMol(new_mol)
                new_fp = _mol_to_fp(new_mol, radius, n_bits)
                if new_fp is not None and new_fp[int(bit)] == 0:
                    smi = Chem.MolToSmiles(new_mol)
                    if smi not in seen:
                        seen.add(smi)
                        results.append((new_mol, "shap_guided", _par_smi))
            except Exception:
                continue

    return results


def generate_variants_cross(
    mols: list,
    n_variants: int = 200,
    seen: Optional[set] = None,
    shap_explainer: Any = None,
    bit_db: Optional[dict] = None,
    model: Any = None,
    radius: int = 3,
    n_bits: int = 2048,
    preserve_core: bool = True,
) -> list:
    """Cross-beam variant generation for the guided optimisation loop.

    Pools BRICS fragments from ALL seed molecules and recombines them,
    creating **hybrid molecules** that single-seed generation can never produce.
    After cross-BRICS, fills remaining slots with constrained per-molecule
    transforms (standard substitutions, ring bioisosteres, terminal removal,
    peripheral decoration) and — when a SHAP explainer is provided — SHAP-guided
    modifications.

    When *preserve_core* is True the function:
    (a) computes a protected-atom set for each beam molecule via
        :func:`identify_protected_atoms` and passes it to the per-molecule
        strategies so they never mutate those positions; and
    (b) applies a post-hoc Murcko scaffold check that discards any generated
        molecule whose parent scaffold is no longer present.  If the filter
        would discard everything it falls back to no filtering.

    Parameters
    ----------
    mols           : all current beam molecules
    n_variants     : upper bound on returned variants
    seen           : set of canonical SMILES already generated (updated in-place)
    shap_explainer : shap.TreeExplainer or None — enables SHAP-guided strategy
    bit_db         : dict from build_bit_database() or None
    model          : sklearn estimator or None
    radius         : Morgan fingerprint radius
    n_bits         : fingerprint size
    preserve_core  : if True, apply pharmacophore-aware generation and post-hoc
                     scaffold preservation filter

    Returns
    -------
    list of (Chem.Mol, origin_str) tuples where origin_str is one of
    ``"brics_cross"``, ``"standard"``, ``"bioisostere"``, ``"terminal_removal"``,
    ``"shap_guided"``, ``"peripheral"``.
    """
    import random
    from rdkit import Chem
    from rdkit.Chem import BRICS

    if seen is None:
        seen = set()
    for mol in mols:
        seen.add(Chem.MolToSmiles(mol))

    # ── Pre-compute protected atom sets and parent scaffolds ───────────────
    protected_per_mol: dict = {}
    parent_cores: list = []

    if preserve_core:
        for mol in mols:
            prot = identify_protected_atoms(mol, shap_explainer, radius, n_bits)
            protected_per_mol[id(mol)] = prot

        try:
            from rdkit.Chem.Scaffolds import MurckoScaffold
            for mol in mols:
                c = MurckoScaffold.GetScaffoldForMol(mol)
                if c is not None and c.GetNumAtoms() > 0:
                    parent_cores.append(c)
        except Exception:
            pass

    results: list = []

    # ── A: Cross-BRICS recombination (main diversity source) ───────────────
    all_frags: list = []
    for mol in mols:
        try:
            for f_smi in BRICS.BRICSDecompose(mol):
                f_mol = Chem.MolFromSmiles(f_smi)
                if f_mol:
                    all_frags.append(f_mol)
        except Exception:
            pass

    if all_frags:
        random.shuffle(all_frags)
        target_cross = min(n_variants // 2, 120)
        try:
            for new_mol in BRICS.BRICSBuild(all_frags):
                if len(results) >= target_cross:
                    break
                try:
                    Chem.SanitizeMol(new_mol)
                    smi = Chem.MolToSmiles(new_mol)
                    if smi not in seen:
                        seen.add(smi)
                        results.append((new_mol, "brics_cross", None))
                except Exception:
                    continue
        except Exception:
            pass

    # ── B: Per-molecule standard variants ──────────────────────────────────
    per_mol = max(20, (n_variants - len(results)) // max(len(mols), 1))
    for mol in mols:
        if len(results) >= n_variants:
            break
        _par_smi = Chem.MolToSmiles(mol)
        for v in generate_variants(mol, n_variants=per_mol):
            smi = Chem.MolToSmiles(v)
            if smi not in seen:
                seen.add(smi)
                results.append((v, "standard", _par_smi))
                if len(results) >= n_variants:
                    break

    # ── C: Ring bioisosteres — constrained to peripheral rings ────────────
    per_mol = max(8, (n_variants - len(results)) // max(len(mols), 1))
    for mol in mols:
        if len(results) >= n_variants:
            break
        _par_smi = Chem.MolToSmiles(mol)
        prot = protected_per_mol.get(id(mol), set())
        for v in _ring_heteroatom_variants(mol, per_mol, seen, protected_atoms=prot):
            results.append((v, "bioisostere", _par_smi))

    # ── D: Terminal-group removal — skip SHAP-positive terminals ──────────
    per_mol = max(5, (n_variants - len(results)) // max(len(mols), 1))
    for mol in mols:
        if len(results) >= n_variants:
            break
        _par_smi = Chem.MolToSmiles(mol)
        prot = protected_per_mol.get(id(mol), set())
        for v in _remove_terminal_variants(mol, per_mol, seen, protected_atoms=prot):
            results.append((v, "terminal_removal", _par_smi))

    # ── E: SHAP-guided modifications (25 % budget) ────────────────────────
    if shap_explainer is not None and bit_db and len(results) < n_variants:
        n_shap = max(1, n_variants // 4)
        try:
            shap_pairs = _shap_guided_variants(
                mols, shap_explainer, bit_db, model,
                radius, n_bits, n_shap, seen,
            )
            results.extend(shap_pairs)
        except Exception:
            pass

    # ── F: Peripheral decoration — R-group additions on non-core atoms ─────
    if preserve_core and len(results) < n_variants:
        n_periph = max(1, n_variants // 5)
        per_periph = max(1, n_periph // max(len(mols), 1))
        for mol in mols:
            if len(results) >= n_variants:
                break
            _par_smi = Chem.MolToSmiles(mol)
            prot = protected_per_mol.get(id(mol), set())
            for v in _peripheral_decoration_variants(mol, prot, per_periph, seen):
                results.append((v, "peripheral", _par_smi))

    # ── Post-hoc core-preservation filter ─────────────────────────────────
    if preserve_core and parent_cores:
        filtered = [
            (m, o, p) for m, o, p in results
            if core_preserved(m, parent_cores)
        ]
        if filtered:
            results = filtered
        # else: fallback — never block the pipeline

    return results[:n_variants]


def _diverse_beam_select(
    candidates: list,
    beam_size: int,
    w_prob: float = 0.50,
    w_div: float = 0.25,
    w_ad: float = 0.25,
) -> list:
    """MMR beam selection with continuous applicability-domain integration.

    Replaces the former binary AD filter with a soft AD preference baked into
    the selection score.  The first molecule is chosen by the highest combined
    probability + AD score (no diversity penalty yet); subsequent molecules add
    the diversity term.

    Score = w_prob*(P_v/max_P) + w_div*(1−max_Tanimoto_to_selected) + w_ad*(AD_v/max_AD)

    Parameters
    ----------
    candidates : list of (mol, prob, fp, ad_score) tuples
    beam_size  : number of molecules to select
    w_prob     : weight for normalised P(active)
    w_div      : weight for structural diversity (1 − max Tanimoto to already-selected)
    w_ad       : weight for normalised applicability-domain score
    """
    if len(candidates) <= beam_size:
        return candidates

    max_p  = max(c[1] for c in candidates) or 1.0
    max_ad = max(c[3] for c in candidates) or 1.0

    def _initial_score(c: tuple) -> float:
        return w_prob * (c[1] / max_p) + w_ad * (c[3] / max_ad)

    best_first_idx = max(range(len(candidates)), key=lambda i: _initial_score(candidates[i]))
    selected  = [candidates[best_first_idx]]
    remaining = [c for i, c in enumerate(candidates) if i != best_first_idx]

    while len(selected) < beam_size and remaining:
        best_idx, best_score = 0, -1.0
        for i, (_, p_v, fp_v, ad_v) in enumerate(remaining):
            max_tc = max(_tanimoto_fps(fp_v, s_fp) for _, _, s_fp, _ in selected)
            score  = (w_prob * (p_v  / max_p)
                      + w_div  * (1.0 - max_tc)
                      + w_ad   * (ad_v / max_ad))
            if score > best_score:
                best_score, best_idx = score, i
        selected.append(remaining.pop(best_idx))

    return selected


# ---------------------------------------------------------------------------
# Timeline reconstruction helper
# ---------------------------------------------------------------------------

def _reconstruct_timeline_path(
    all_candidates_raw: list,
    top_candidate: Optional["DesignCandidate"],
    base_smiles: str,
    base_prob: float,
    base_ad: float,
    history: list,
) -> list:
    """Reconstruct the evolutionary path from the input molecule to the top candidate.

    Follows ``parent_smiles`` links backwards from *top_candidate*.  When a link
    is ``None`` (BRICS cross — multi-parent strategy), the function falls back to
    the global-best molecule at the previous iteration recorded in *history*.

    Returns a list of history-style dicts (same format as the pipeline's
    ``history`` output) ordered step 0 → top candidate.  Falls back to returning
    *history* unchanged if reconstruction fails or yields a single-step path.
    """
    if top_candidate is None:
        return history

    # Build SMILES → best DesignCandidate lookup (keep highest prob per SMILES)
    smi_to_cand: dict = {}
    for c in all_candidates_raw:
        if c.smiles not in smi_to_cand or c.probability > smi_to_cand[c.smiles].probability:
            smi_to_cand[c.smiles] = c

    # Iteration index → best_smiles from history (fallback for None parents)
    iter_to_best: dict = {h["iteration"]: h["best_smiles"] for h in history}

    # Walk backwards: top_candidate → … → (close to) input
    chain = [top_candidate]
    visited: set = {top_candidate.smiles}
    current = top_candidate

    for _ in range(100):  # safety cap
        par_smi = current.parent_smiles

        if par_smi is None:
            # BRICS cross variant — no single parent; use history proxy
            prev_iter = current.iteration - 1
            if prev_iter <= 0:
                break
            proxy_smi = iter_to_best.get(prev_iter, base_smiles)
            if proxy_smi == base_smiles or proxy_smi in visited:
                break
            proxy = smi_to_cand.get(proxy_smi)
            if proxy is None or proxy.smiles in visited:
                break
            chain.append(proxy)
            visited.add(proxy.smiles)
            current = proxy

        elif par_smi == base_smiles:
            break  # next node is the input molecule

        else:
            par = smi_to_cand.get(par_smi)
            if par is None or par.smiles in visited:
                break
            chain.append(par)
            visited.add(par.smiles)
            current = par

    chain.reverse()  # now: chain[0] is closest to input, chain[-1] = top_candidate

    # Build timeline dicts, prepend the base (iteration 0)
    timeline: list = [{
        "iteration":   0,
        "n_generated": 0,
        "best_prob":   base_prob,
        "ad_score":    base_ad,
        "best_smiles": base_smiles,
    }]
    seen_iters: set = {0}

    for c in chain:
        if c.iteration in seen_iters:
            continue
        h_ref = history[c.iteration] if 0 < c.iteration < len(history) else {}
        timeline.append({
            "iteration":   c.iteration,
            "n_generated": h_ref.get("n_generated", 0),
            "best_prob":   c.probability,
            "ad_score":    c.ad_score,
            "best_smiles": c.smiles,
        })
        seen_iters.add(c.iteration)

    # Fall back to original history if reconstruction is trivial (≤ 1 step)
    return timeline if len(timeline) > 1 else history


# ---------------------------------------------------------------------------
# Guided (iterative / beam-search) pipeline
# ---------------------------------------------------------------------------

def run_guided_pipeline(
    smiles: str,
    model: Any,
    radius: int = 3,
    n_bits: int = 2048,
    n_variants_per_iter: int = 100,
    n_iterations: int = 5,
    beam_size: int = 3,
    dataset_fps: Optional[np.ndarray] = None,
    train_smiles: Optional[list] = None,
    top_k: int = 9,
    patience: int = 3,
    shap_explainer: Any = None,
    bit_db: Optional[dict] = None,
    w_prob: float = 0.50,
    w_div: float = 0.25,
    w_ad: float = 0.25,
    use_druglikeness: bool = True,
    preserve_core: bool = True,
    progress_callback=None,
) -> dict:
    """Iterative beam-search molecular optimisation guided by predicted activity.

    Each iteration:

    1. Generate variants from the current beam using up to six strategies
       (cross-BRICS, standard substitutions, bioisosteres, terminal removal,
       and — when a SHAP explainer is available — SHAP-guided modifications).
    2. Predict P(active) in batch.
    3. Optionally filter by Lipinski-extended drug-likeness (relaxed fallback
       ensures the pipeline never stalls).
    4. Pre-compute AD scores for the top slice.
    5. Select *beam_size* seeds via MMR with continuous AD integration.
    6. Record one history entry per iteration for the progress plot.

    Parameters
    ----------
    smiles              : input SMILES string
    model               : sklearn classifier with predict_proba
    radius, n_bits      : Morgan fingerprint parameters (must match training)
    n_variants_per_iter : variants generated per iteration
    n_iterations        : maximum number of iterations
    beam_size           : molecules carried forward as seeds each round
    dataset_fps         : training fingerprints for AD scoring (or None)
    top_k               : number of candidates in the returned lists
    patience            : early-stop after this many non-improving iterations
    shap_explainer      : shap.TreeExplainer (enables strategies E and core detection)
    bit_db              : output of build_bit_database() (enables strategy E)
    w_prob              : beam-selection weight for P(active)
    w_div               : beam-selection weight for structural diversity
    w_ad                : beam-selection weight for AD score
    use_druglikeness    : apply Lipinski-extended drug-likeness filter
    preserve_core       : protect pharmacophore core atoms from mutation
    progress_callback   : callable(frac, msg) for UI progress updates

    Returns
    -------
    dict with keys: base_smiles, base_prob, candidates, top_improvers,
    top_total, n_generated, history, guided.
    """
    import random
    import streamlit as _st

    _seed = _st.session_state.get("design_random_seed", None)
    if _seed is not None:
        random.seed(int(_seed))
        np.random.seed(int(_seed))

    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"Invalid SMILES: {smiles!r}"}
    if model is None:
        return {"error": "No model loaded."}

    # Build canonical training-set lookup for hard exclusion from results/beam
    _train_set: set[str] = set()
    if train_smiles:
        for _s in train_smiles:
            try:
                _m = Chem.MolFromSmiles(str(_s).strip())
                if _m is not None:
                    _train_set.add(Chem.MolToSmiles(_m))
            except Exception:
                pass

    canon_smi = Chem.MolToSmiles(mol)
    base_fp   = _mol_to_fp(mol, radius, n_bits)
    if base_fp is None:
        return {"error": "Could not compute fingerprint for the input molecule."}

    base_prob = float(model.predict_proba(base_fp.reshape(1, -1))[0, 1])
    base_ad   = compute_ad_score(base_fp, dataset_fps) if dataset_fps is not None else 1.0

    history: list[dict] = [{
        "iteration":   0,
        "n_generated": 0,
        "best_prob":   base_prob,
        "ad_score":    base_ad,
        "best_smiles": canon_smi,
    }]

    beam:             list[tuple] = [(mol, base_prob, base_fp)]
    seen:             set[str]    = {canon_smi}
    all_candidates:   list[DesignCandidate] = []
    n_total:          int   = 0
    global_best_prob: float = base_prob
    _all_in_train_warning: bool = False
    global_best_smi:  str   = canon_smi
    _no_improve:      int   = 0

    for it in range(n_iterations):
        if progress_callback:
            progress_callback(
                it / n_iterations,
                f"Iteration {it + 1}/{n_iterations} · best P(active) = {global_best_prob:.3f} · {n_total} molecules so far",
            )

        beam_mols      = [m for m, _, _ in beam]
        iter_mol_pairs = generate_variants_cross(
            beam_mols, n_variants_per_iter, seen,
            shap_explainer=shap_explainer,
            bit_db=bit_db,
            model=model,
            radius=radius,
            n_bits=n_bits,
            preserve_core=preserve_core,
        )

        if not iter_mol_pairs:
            break

        iter_mols    = [m for m, _, _p in iter_mol_pairs]
        iter_origins = [o for _, o, _p in iter_mol_pairs]
        # Map each generated SMILES → its parent SMILES for lineage tracking
        parent_by_smi: dict = {
            Chem.MolToSmiles(m): p for m, _, p in iter_mol_pairs
        }

        probs    = predict_batch(model, iter_mols, radius=radius, n_bits=n_bits)
        n_total += len(iter_mols)

        paired  = sorted(
            zip(iter_mols, probs, iter_origins),
            key=lambda x: x[1], reverse=True,
        )
        check_n   = max(beam_size * 8, 40)
        top_check = paired[:check_n]

        # ── Drug-likeness filter ───────────────────────────────────────────
        if use_druglikeness:
            strict_pass = [(m, p, o) for m, p, o in top_check
                           if passes_druglikeness(m, strict=True)]
            if not strict_pass:
                strict_pass = [(m, p, o) for m, p, o in top_check
                               if passes_druglikeness(m, strict=False)]
            top_filtered = strict_pass if strict_pass else list(top_check)
        else:
            top_filtered = list(top_check)

        # ── AD scoring (pre-computed for full filtered pool) ───────────────
        top_with_ad: list = []
        for mol_v, prob_v, origin_v in top_filtered:
            fp_v = _mol_to_fp(mol_v, radius, n_bits)
            if fp_v is None:
                continue
            ad = compute_ad_score(fp_v, dataset_fps) if dataset_fps is not None else 1.0
            top_with_ad.append((mol_v, prob_v, fp_v, ad, origin_v))

        # ── Exclude training-set molecules from beam and results ───────────
        if _train_set and top_with_ad:
            top_novel = [
                t for t in top_with_ad
                if Chem.MolToSmiles(t[0]) not in _train_set
            ]
            if not top_novel:
                # Edge case: every candidate is a training molecule
                _all_in_train_warning = True
                top_novel = top_with_ad[:1]   # fall back to best available
            top_for_beam = top_novel
        else:
            top_for_beam = top_with_ad

        # ── Diversity-aware beam update with continuous AD ─────────────────
        if top_for_beam:
            beam_candidates = [(m, p, fp, ad) for m, p, fp, ad, _ in top_for_beam]
            new_beam_tuples = _diverse_beam_select(beam_candidates, beam_size,
                                                   w_prob, w_div, w_ad)
            beam = [(m, p, fp) for m, p, fp, _ in new_beam_tuples]

        # ── Update global best (from novel candidates only) ───────────────
        _prev_best = global_best_prob
        if top_for_beam and top_for_beam[0][1] > global_best_prob:
            global_best_prob = top_for_beam[0][1]
            global_best_smi  = Chem.MolToSmiles(top_for_beam[0][0])

        if global_best_prob > _prev_best + 1e-4:
            _no_improve = 0
        else:
            _no_improve += 1

        best_mol_obj = Chem.MolFromSmiles(global_best_smi)
        best_fp_obj  = _mol_to_fp(best_mol_obj, radius, n_bits) if best_mol_obj else None
        iter_best_ad = (
            compute_ad_score(best_fp_obj, dataset_fps)
            if (best_fp_obj is not None and dataset_fps is not None)
            else 1.0
        )

        history.append({
            "iteration":   it + 1,
            "n_generated": n_total,
            "best_prob":   global_best_prob,
            "ad_score":    iter_best_ad,
            "best_smiles": global_best_smi,
        })

        if patience > 0 and _no_improve >= patience:
            if progress_callback:
                progress_callback(
                    (it + 1) / n_iterations,
                    f"Early stop at iteration {it + 1}/{n_iterations}: "
                    f"no improvement for {patience} consecutive rounds.",
                )

        # ── Collect candidates with strategy origin (skip training set) ──────
        for mol_v, prob_v, fp_v, ad, origin_v in top_with_ad:
            smi_v = Chem.MolToSmiles(mol_v)
            if smi_v in _train_set:
                continue   # exclude training-set molecules from displayed results
            all_candidates.append(DesignCandidate(
                smiles=smi_v,
                probability=float(prob_v),
                delta=float(prob_v) - base_prob,
                source=origin_v,
                transformation=extract_transformation(mol, mol_v),
                ad_score=ad,
                parent_smiles=parent_by_smi.get(smi_v),
                iteration=it + 1,
            ))

        if patience > 0 and _no_improve >= patience:
            break

    # ── Final ranking ──────────────────────────────────────────────────────
    # Keep raw list for lineage reconstruction (before deduplication)
    _all_candidates_raw = list(all_candidates)

    seen_smi: dict[str, DesignCandidate] = {}
    for c in all_candidates:
        if c.smiles not in seen_smi or c.probability > seen_smi[c.smiles].probability:
            seen_smi[c.smiles] = c
    all_candidates = sorted(seen_smi.values(), key=lambda c: c.probability, reverse=True)
    for i, c in enumerate(all_candidates, 1):
        c.rank = i

    top_improvers = [c for c in all_candidates if c.delta > 0 and c.probability > 0.3 and passes_druglikeness(Chem.MolFromSmiles(c.smiles))][:top_k]
    top_total     = all_candidates[:top_k]

    # ── Reconstruct timeline path to the global top candidate ─────────────
    _top_cand = all_candidates[0] if all_candidates else None
    timeline_path = _reconstruct_timeline_path(
        all_candidates_raw=_all_candidates_raw,
        top_candidate=_top_cand,
        base_smiles=canon_smi,
        base_prob=base_prob,
        base_ad=base_ad,
        history=history,
    )

    return {
        "base_smiles":              canon_smi,
        "base_prob":                base_prob,
        "candidates":               all_candidates,
        "top_improvers":            top_improvers,
        "top_total":                top_total,
        "n_generated":              n_total,
        "history":                  history,
        "timeline_path":            timeline_path,
        "top_candidate_prob":       _top_cand.probability if _top_cand else None,
        "top_candidate_iteration":  _top_cand.iteration   if _top_cand else None,
        "guided":                   True,
        "all_in_train_warning":     _all_in_train_warning,
    }


# ---------------------------------------------------------------------------
# Step 5 — Dataset similarity search
# ---------------------------------------------------------------------------

def find_similar_molecules(
    query_fp: np.ndarray,
    dataset_fps: np.ndarray,
    top_k: int = 5,
    dataset_smiles: Optional[list[str]] = None,
    dataset_labels: Optional[list[int]] = None,
) -> list[dict]:
    """Return the *top_k* most similar molecules in the dataset (Tanimoto).

    Parameters
    ----------
    query_fp : np.ndarray of shape (n_bits,)
    dataset_fps : np.ndarray of shape (n_mols, n_bits)
    top_k : int
    dataset_smiles : optional list[str] — training SMILES
    dataset_labels : optional list[int] — training labels (0/1)

    Returns
    -------
    list[dict] with keys ``index``, ``tanimoto``, and optionally ``smiles``/``label``.
    """
    if dataset_fps is None or len(dataset_fps) == 0:
        return []

    q = query_fp.astype(np.float32)
    db = dataset_fps.astype(np.float32)

    intersection = db.dot(q)
    union = float(q.sum()) + db.sum(axis=1) - intersection
    tanimoto = np.where(union > 0, intersection / union, 0.0)

    top_idx = np.argsort(tanimoto)[::-1][:top_k]
    results = []
    for idx in top_idx:
        entry: dict = {"index": int(idx), "tanimoto": float(tanimoto[idx])}
        if dataset_smiles and int(idx) < len(dataset_smiles):
            entry["smiles"] = dataset_smiles[int(idx)]
        if dataset_labels is not None and int(idx) < len(dataset_labels):
            entry["label"] = int(dataset_labels[int(idx)])
        results.append(entry)
    return results


# ---------------------------------------------------------------------------
# Full pipeline entry point
# ---------------------------------------------------------------------------

def run_design_pipeline(
    smiles: str,
    model: Any,
    radius: int = 3,
    n_bits: int = 2048,
    n_variants: int = 200,
    top_k: int = 10,
    progress_callback=None,
) -> dict:
    """End-to-end design pipeline: variants → predict → rank → describe.

    Parameters
    ----------
    smiles : str — input SMILES
    model  : sklearn-compatible classifier
    radius, n_bits : fingerprint parameters (must match training)
    n_variants : maximum variants to generate
    top_k : number of top candidates to surface

    Returns
    -------
    dict with keys:

    - ``base_smiles``   : str
    - ``base_prob``     : float
    - ``candidates``    : list[DesignCandidate]  — all ranked variants
    - ``top_improvers`` : list[DesignCandidate]  — top_k with delta > 0
    - ``top_total``     : list[DesignCandidate]  — top_k by probability
    - ``n_generated``   : int
    - ``error``         : str (only present if the pipeline failed)
    """
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"Invalid SMILES: {smiles!r}"}
    if model is None:
        return {"error": "No model loaded. Upload a model in the sidebar."}

    canon_smi = Chem.MolToSmiles(mol)

    # Base fingerprint + probability
    base_fp = _mol_to_fp(mol, radius, n_bits)
    if base_fp is None:
        return {"error": "Could not compute Morgan fingerprint for the input molecule."}

    try:
        base_prob = float(model.predict_proba(base_fp.reshape(1, -1))[0, 1])
    except Exception as exc:
        return {"error": f"Model prediction failed: {exc}"}

    def _cb(frac: float, msg: str) -> None:
        if progress_callback:
            progress_callback(frac, msg)

    _cb(0.05, "Generating variants…")
    variants = generate_variants(mol, n_variants=n_variants)
    if not variants:
        _cb(1.0, "Done — no variants generated.")
        return {
            "base_smiles": canon_smi,
            "base_prob": base_prob,
            "candidates": [],
            "top_improvers": [],
            "top_total": [],
            "n_generated": 0,
        }

    _cb(0.5, f"Predicting activity for {len(variants)} variants…")
    probs = predict_batch(model, variants, radius=radius, n_bits=n_bits)

    _cb(0.75, "Ranking candidates…")
    candidates = rank_variants(base_prob, list(zip(variants, probs)))

    _cb(0.90, "Describing structural changes…")
    for c in candidates:
        new_mol = Chem.MolFromSmiles(c.smiles)
        c.transformation = extract_transformation(mol, new_mol)

    top_improvers = [c for c in candidates if c.delta > 0 and c.probability > 0.3 and passes_druglikeness(Chem.MolFromSmiles(c.smiles))][:top_k]
    top_total = candidates[:top_k]

    _cb(1.0, "Done.")
    return {
        "base_smiles": canon_smi,
        "base_prob": base_prob,
        "candidates": candidates,
        "top_improvers": top_improvers,
        "top_total": top_total,
        "n_generated": len(variants),
    }


# ---------------------------------------------------------------------------
# LLM context formatter
# ---------------------------------------------------------------------------

def format_design_context(result: dict, top_n: int = 5) -> str:
    """Format design pipeline results as a grounded LLM context string.

    Starts with ``=== MOLECULAR DESIGN SUGGESTIONS ===`` so the LLM can
    anchor its reasoning to the computed data.
    """
    if "error" in result:
        return f"=== DESIGN ENGINE ERROR ===\n{result['error']}"

    lines = [
        "=== MOLECULAR DESIGN SUGGESTIONS ===",
        "",
        f"Base molecule  : {result['base_smiles']}",
        f"Base P(active) : {result['base_prob']:.4f}",
        f"Variants generated: {result['n_generated']}",
        "",
        f"--- Top {top_n} improvements (ΔP > 0) ---",
        "",
    ]

    improvers = result.get("top_improvers", [])
    if not improvers:
        lines.append("  No variants found with higher predicted activity.")
    else:
        for c in improvers[:top_n]:
            lines.append(
                f"  #{c.rank} SMILES={c.smiles}  "
                f"P={c.probability:.4f}  Δ={c.delta:+.4f}  "
                f"[{c.transformation}]"
            )

    lines += ["", f"--- Top {top_n} overall ---", ""]
    for c in result.get("top_total", [])[:top_n]:
        lines.append(
            f"  #{c.rank} SMILES={c.smiles}  "
            f"P={c.probability:.4f}  Δ={c.delta:+.4f}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mol_to_fp(mol, radius: int, n_bits: int) -> Optional[np.ndarray]:
    """Convert a sanitized Mol to a numpy fingerprint array, or None on failure."""
    try:
        from rdkit.Chem import AllChem, DataStructs
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        arr = np.zeros(n_bits, dtype=np.int32)
        DataStructs.ConvertToNumpyArray(fp, arr)
        return arr
    except Exception:
        return None
