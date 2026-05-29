"""Molecule image rendering and fingerprint endpoints."""

from __future__ import annotations

import base64
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from rdkit import Chem
from rdkit.Chem import Draw, AllChem

from backend.state import app_state

router = APIRouter()


def _mol_for_render(smiles: str) -> Chem.Mol | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is not None:
        return mol

    # ECFP environments cut out of aromatic systems are often valid query
    # patterns rather than standalone molecules. Render those as SMARTS so the
    # UI can still show the substructure instead of dropping the image.
    mol = Chem.MolFromSmarts(smiles)
    if mol is not None:
        return mol

    mol = Chem.MolFromSmiles(smiles, sanitize=False)
    if mol is not None:
        try:
            mol.UpdatePropertyCache(strict=False)
        except Exception:
            pass
    return mol


@router.get("/image")
def molecule_image(
    smiles: str = Query(...),
    width: int = Query(300),
    height: int = Query(200),
):
    """Render a SMILES as PNG and return it."""
    mol = _mol_for_render(smiles)
    if mol is None:
        raise HTTPException(status_code=422, detail=f"Invalid molecule pattern: {smiles!r}")

    img = Draw.MolToImage(mol, size=(width, height))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


def _morgan_environment(mol: Chem.Mol, atom_idx: int, radius: int) -> tuple[list[int], list[int]]:
    if atom_idx < 0 or atom_idx >= mol.GetNumAtoms():
        raise HTTPException(status_code=422, detail=f"Invalid atom index: {atom_idx}")
    if radius < 0:
        raise HTTPException(status_code=422, detail=f"Invalid Morgan radius: {radius}")

    if radius == 0:
        return [atom_idx], []

    bond_ids = list(Chem.FindAtomEnvironmentOfRadiusN(mol, radius, atom_idx))
    atom_ids = {atom_idx}
    for bond_id in bond_ids:
        bond = mol.GetBondWithIdx(bond_id)
        atom_ids.add(bond.GetBeginAtomIdx())
        atom_ids.add(bond.GetEndAtomIdx())

    return sorted(atom_ids), bond_ids


@router.get("/highlight")
def molecule_highlight(
    smiles: str = Query(...),
    atom_idx: int = Query(...),
    radius: int = Query(...),
    direction: str = Query("active"),
    width: int = Query(420),
    height: int = Query(300),
):
    """Render a full molecule with one Morgan atom environment highlighted."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise HTTPException(status_code=422, detail=f"Invalid SMILES: {smiles!r}")

    atom_ids, bond_ids = _morgan_environment(mol, atom_idx, radius)
    lowered = direction.lower()
    color = (0.10, 0.62, 0.34) if "active" in lowered and "inactive" not in lowered else (0.82, 0.20, 0.16)

    img = Draw.MolToImage(
        mol,
        size=(width, height),
        highlightAtoms=atom_ids,
        highlightBonds=bond_ids,
        highlightColor=color,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


class FingerprintRequest(BaseModel):
    smiles: str
    radius: int | None = None
    nbits: int | None = None


@router.post("/fingerprint")
def fingerprint(req: FingerprintRequest):
    """Return Morgan fingerprint bit vector for a SMILES."""
    mol = Chem.MolFromSmiles(req.smiles)
    if mol is None:
        raise HTTPException(status_code=422, detail=f"Invalid SMILES: {req.smiles!r}")

    radius = req.radius or app_state.fp_radius
    nbits = req.nbits or app_state.fp_nbits

    bi: dict = {}
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=nbits, bitInfo=bi)
    on_bits = list(fp.GetOnBits())

    return {
        "smiles": req.smiles,
        "canonical_smiles": Chem.MolToSmiles(mol),
        "radius": radius,
        "nbits": nbits,
        "n_on_bits": len(on_bits),
        "on_bits": on_bits,
        "bit_info": {str(k): v for k, v in bi.items()},
    }


@router.get("/validate")
def validate_smiles(smiles: str = Query(...)):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"valid": False, "canonical": None}
    return {"valid": True, "canonical": Chem.MolToSmiles(mol)}


@router.get("/diff")
def molecule_diff(
    smiles_a: str = Query(...),
    smiles_b: str = Query(...),
):
    """MCS-based structural diff: returns added/removed fragments between two molecules."""
    try:
        from rdkit.Chem import rdFMCS

        mol_a = Chem.MolFromSmiles(smiles_a)
        mol_b = Chem.MolFromSmiles(smiles_b)
        if mol_a is None or mol_b is None:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        mcs = rdFMCS.FindMCS(
            [mol_a, mol_b], timeout=3,
            atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareOrder,
        )
        if mcs.canceled or mcs.numAtoms == 0:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        min_atoms = min(mol_a.GetNumAtoms(), mol_b.GetNumAtoms())
        if mcs.numAtoms / max(min_atoms, 1) < 0.40:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        mcs_mol = Chem.MolFromSmarts(mcs.smartsString)
        if mcs_mol is None:
            return {"added_frags": [], "removed_frags": [], "scaffold_change": True}

        def _formula_label(mol: Chem.Mol, atom_ids: list[int]) -> str:
            counts: dict[str, int] = {}
            for atom_id in atom_ids:
                symbol = mol.GetAtomWithIdx(atom_id).GetSymbol()
                counts[symbol] = counts.get(symbol, 0) + 1
            order = ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I"]
            symbols = [s for s in order if s in counts] + sorted(s for s in counts if s not in order)
            return "".join(f"{s}{counts[s] if counts[s] > 1 else ''}" for s in symbols)

        def _non_mcs_components(mol: Chem.Mol) -> list[list[int]]:
            match = mol.GetSubstructMatch(mcs_mol)
            if not match:
                return []
            non_mcs_set = {i for i in range(mol.GetNumAtoms()) if i not in set(match)}
            if not non_mcs_set:
                return []
            seen: set[int] = set()
            components: list[list[int]] = []
            for atom_id in sorted(non_mcs_set):
                if atom_id in seen:
                    continue
                stack = [atom_id]
                comp: list[int] = []
                seen.add(atom_id)
                while stack:
                    current = stack.pop()
                    comp.append(current)
                    atom = mol.GetAtomWithIdx(current)
                    for nbr in atom.GetNeighbors():
                        nbr_id = nbr.GetIdx()
                        if nbr_id in non_mcs_set and nbr_id not in seen:
                            seen.add(nbr_id)
                            stack.append(nbr_id)
                components.append(sorted(comp))
            return components[:3]

        def non_mcs_frags(mol: Chem.Mol) -> tuple[list[str], list[str]]:
            match = mol.GetSubstructMatch(mcs_mol)
            if not match:
                return [], []
            non_mcs = [i for i in range(mol.GetNumAtoms()) if i not in set(match)]
            if not non_mcs:
                return [], []
            try:
                components = _non_mcs_components(mol)
                labels = [_formula_label(mol, comp) for comp in components]
                frag_smi = Chem.MolFragmentToSmiles(mol, atomsToUse=non_mcs)
                if not frag_smi:
                    return [], labels
                out = []
                for p in frag_smi.split("."):
                    p = p.strip()
                    m = Chem.MolFromSmiles(p)
                    if m and m.GetNumAtoms() >= 1:
                        out.append(Chem.MolToSmiles(m))
                return out[:3], labels[:3]
            except Exception:
                return [], []

        added_frags, added_labels = non_mcs_frags(mol_b)
        removed_frags, removed_labels = non_mcs_frags(mol_a)
        return {
            "added_frags":   added_frags,
            "removed_frags": removed_frags,
            "added_frag_labels": added_labels,
            "removed_frag_labels": removed_labels,
            "fragment_render_warning": (
                "Fragment images are RDKit renderings of isolated fragments. "
                "RDKit may add implicit hydrogens to satisfy valence, so a chlorine substituent can render as HCl "
                "and an oxygen substituent can render as water-like species. Atom-delta labels omit those implicit hydrogens."
            ),
            "scaffold_change": False,
        }
    except Exception:
        return {"added_frags": [], "removed_frags": [], "scaffold_change": True}
