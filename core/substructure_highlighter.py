"""Substructure highlighting utilities."""

from typing import Optional, Union
from dataclasses import dataclass
from rdkit import Chem
from rdkit.Chem import AllChem, Draw

from .molecule_parser import MoleculeParser


@dataclass
class HighlightInfo:
    """Container for substructure highlight information."""

    atom_indices: tuple[int, ...]
    bond_indices: list[int]
    pattern: str
    match_count: int


class SubstructureHighlighter:
    """Highlight substructures in molecules."""

    @staticmethod
    def find_matches(
        smiles_or_mol: Union[str, Chem.Mol],
        pattern: str,
        max_matches: int = 100,
    ) -> list[HighlightInfo]:
        """Find all matches of a SMARTS/SMILES pattern in a molecule."""
        mol = SubstructureHighlighter._ensure_mol(smiles_or_mol)
        if mol is None:
            return []

        # Try as SMARTS first, then as SMILES
        pattern_mol = Chem.MolFromSmarts(pattern)
        if pattern_mol is None:
            pattern_mol = Chem.MolFromSmiles(pattern)
        if pattern_mol is None:
            return []

        matches = mol.GetSubstructMatches(pattern_mol, maxMatches=max_matches)
        if not matches:
            return []

        results = []
        for atom_indices in matches:
            bond_indices = SubstructureHighlighter._get_bond_indices(mol, atom_indices)
            results.append(
                HighlightInfo(
                    atom_indices=atom_indices,
                    bond_indices=bond_indices,
                    pattern=pattern,
                    match_count=len(matches),
                )
            )

        return results

    @staticmethod
    def get_first_match(
        smiles_or_mol: Union[str, Chem.Mol],
        pattern: str,
    ) -> Optional[HighlightInfo]:
        """Get the first match of a pattern in a molecule."""
        matches = SubstructureHighlighter.find_matches(smiles_or_mol, pattern, max_matches=1)
        return matches[0] if matches else None

    @staticmethod
    def get_atoms_for_morgan_bit(
        smiles_or_mol: Union[str, Chem.Mol],
        bit_index: int,
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
    ) -> list[HighlightInfo]:
        """Get atoms that contribute to a specific Morgan fingerprint bit."""
        mol = SubstructureHighlighter._ensure_mol(smiles_or_mol)
        if mol is None:
            return []

        bit_info = {}
        if use_features:
            AllChem.GetMorganFingerprintAsBitVect(
                mol,
                radius,
                nBits=n_bits,
                useFeatures=True,
                bitInfo=bit_info,
            )
        else:
            AllChem.GetMorganFingerprintAsBitVect(
                mol,
                radius,
                nBits=n_bits,
                bitInfo=bit_info,
            )

        if bit_index not in bit_info:
            return []

        results = []
        for center_atom, bit_radius in bit_info[bit_index]:
            env_atoms = SubstructureHighlighter._get_atom_environment(
                mol, center_atom, bit_radius
            )
            bond_indices = SubstructureHighlighter._get_bond_indices(mol, env_atoms)
            results.append(
                HighlightInfo(
                    atom_indices=tuple(env_atoms),
                    bond_indices=bond_indices,
                    pattern=f"Morgan bit {bit_index} (center={center_atom}, radius={bit_radius})",
                    match_count=len(bit_info[bit_index]),
                )
            )

        return results

    @staticmethod
    def get_combined_highlight_atoms(
        smiles_or_mol: Union[str, Chem.Mol],
        pattern: str,
    ) -> tuple[list[int], list[int]]:
        """Get combined atom and bond indices for all matches of a pattern."""
        matches = SubstructureHighlighter.find_matches(smiles_or_mol, pattern)
        if not matches:
            return [], []

        all_atoms = set()
        all_bonds = set()

        for match in matches:
            all_atoms.update(match.atom_indices)
            all_bonds.update(match.bond_indices)

        return sorted(all_atoms), sorted(all_bonds)

    @staticmethod
    def has_pattern(smiles_or_mol: Union[str, Chem.Mol], pattern: str) -> bool:
        """Check if molecule contains a pattern."""
        mol = SubstructureHighlighter._ensure_mol(smiles_or_mol)
        if mol is None:
            return False

        pattern_mol = Chem.MolFromSmarts(pattern)
        if pattern_mol is None:
            pattern_mol = Chem.MolFromSmiles(pattern)
        if pattern_mol is None:
            return False

        return mol.HasSubstructMatch(pattern_mol)

    @staticmethod
    def count_matches(smiles_or_mol: Union[str, Chem.Mol], pattern: str) -> int:
        """Count number of matches of a pattern in a molecule."""
        matches = SubstructureHighlighter.find_matches(smiles_or_mol, pattern)
        return len(matches)

    @staticmethod
    def _get_bond_indices(mol: Chem.Mol, atom_indices: tuple[int, ...]) -> list[int]:
        """Get bond indices connecting the given atoms."""
        atom_set = set(atom_indices)
        bond_indices = []

        for bond in mol.GetBonds():
            begin_idx = bond.GetBeginAtomIdx()
            end_idx = bond.GetEndAtomIdx()
            if begin_idx in atom_set and end_idx in atom_set:
                bond_indices.append(bond.GetIdx())

        return bond_indices

    @staticmethod
    def _get_atom_environment(
        mol: Chem.Mol, center_atom: int, radius: int
    ) -> list[int]:
        """Get all atoms within a given radius of a center atom."""
        if radius == 0:
            return [center_atom]

        env = {center_atom}
        frontier = {center_atom}

        for _ in range(radius):
            new_frontier = set()
            for atom_idx in frontier:
                atom = mol.GetAtomWithIdx(atom_idx)
                for neighbor in atom.GetNeighbors():
                    neighbor_idx = neighbor.GetIdx()
                    if neighbor_idx not in env:
                        new_frontier.add(neighbor_idx)
                        env.add(neighbor_idx)
            frontier = new_frontier

        return sorted(env)

    @staticmethod
    def _ensure_mol(smiles_or_mol: Union[str, Chem.Mol]) -> Optional[Chem.Mol]:
        """Ensure we have an RDKit molecule object."""
        if isinstance(smiles_or_mol, str):
            return MoleculeParser.parse(smiles_or_mol)
        return smiles_or_mol
