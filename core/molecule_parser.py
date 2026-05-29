"""SMILES parsing and molecular validation."""

from typing import Optional, Union
from dataclasses import dataclass
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors


@dataclass
class MoleculeInfo:
    """Container for basic molecule information."""

    smiles: str
    canonical_smiles: str
    mol: Chem.Mol
    num_atoms: int
    num_heavy_atoms: int
    num_bonds: int
    molecular_formula: str
    molecular_weight: float
    is_valid: bool = True
    error_message: Optional[str] = None


class MoleculeParser:
    """Parse and validate SMILES strings."""

    @staticmethod
    def parse(smiles: str) -> Optional[Chem.Mol]:
        """Parse a SMILES string to an RDKit molecule object."""
        if not smiles or not isinstance(smiles, str):
            return None

        smiles = smiles.strip()
        mol = Chem.MolFromSmiles(smiles)

        return mol

    @staticmethod
    def validate(smiles: str) -> tuple[bool, str]:
        """Validate a SMILES string."""
        if not smiles or not isinstance(smiles, str):
            return False, "Empty or invalid input"

        smiles = smiles.strip()
        if not smiles:
            return False, "Empty SMILES string"

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, f"Invalid SMILES: '{smiles}'"

        return True, "Valid SMILES"

    @staticmethod
    def canonicalize(smiles: str) -> Optional[str]:
        """Convert SMILES to canonical form."""
        mol = MoleculeParser.parse(smiles)
        if mol is None:
            return None
        return Chem.MolToSmiles(mol, canonical=True)

    @staticmethod
    def get_info(smiles: str) -> MoleculeInfo:
        """Get comprehensive information about a molecule."""
        mol = MoleculeParser.parse(smiles)

        if mol is None:
            return MoleculeInfo(
                smiles=smiles,
                canonical_smiles="",
                mol=None,
                num_atoms=0,
                num_heavy_atoms=0,
                num_bonds=0,
                molecular_formula="",
                molecular_weight=0.0,
                is_valid=False,
                error_message=f"Invalid SMILES: '{smiles}'",
            )

        return MoleculeInfo(
            smiles=smiles,
            canonical_smiles=Chem.MolToSmiles(mol, canonical=True),
            mol=mol,
            num_atoms=mol.GetNumAtoms(),
            num_heavy_atoms=mol.GetNumHeavyAtoms(),
            num_bonds=mol.GetNumBonds(),
            molecular_formula=rdMolDescriptors.CalcMolFormula(mol),
            molecular_weight=Descriptors.MolWt(mol),
            is_valid=True,
        )

    @staticmethod
    def smiles_to_mol(smiles: str) -> Optional[Chem.Mol]:
        """Alias for parse method."""
        return MoleculeParser.parse(smiles)

    @staticmethod
    def mol_to_smiles(mol: Chem.Mol, canonical: bool = True) -> Optional[str]:
        """Convert RDKit molecule to SMILES."""
        if mol is None:
            return None
        return Chem.MolToSmiles(mol, canonical=canonical)

    @staticmethod
    def from_smarts(smarts: str) -> Optional[Chem.Mol]:
        """Parse a SMARTS pattern to an RDKit molecule object."""
        if not smarts or not isinstance(smarts, str):
            return None
        return Chem.MolFromSmarts(smarts.strip())

    @staticmethod
    def has_substructure(mol: Union[str, Chem.Mol], pattern: Union[str, Chem.Mol]) -> bool:
        """Check if molecule contains a substructure pattern."""
        # Convert SMILES to mol if needed
        if isinstance(mol, str):
            mol = MoleculeParser.parse(mol)
        if mol is None:
            return False

        # Convert pattern (SMARTS or SMILES) to mol if needed
        if isinstance(pattern, str):
            pattern_mol = Chem.MolFromSmarts(pattern)
            if pattern_mol is None:
                pattern_mol = MoleculeParser.parse(pattern)
        else:
            pattern_mol = pattern

        if pattern_mol is None:
            return False

        return mol.HasSubstructMatch(pattern_mol)

    @staticmethod
    def get_substructure_matches(
        mol: Union[str, Chem.Mol], pattern: Union[str, Chem.Mol]
    ) -> list[tuple[int, ...]]:
        """Get all substructure matches of a pattern in a molecule."""
        if isinstance(mol, str):
            mol = MoleculeParser.parse(mol)
        if mol is None:
            return []

        if isinstance(pattern, str):
            pattern_mol = Chem.MolFromSmarts(pattern)
            if pattern_mol is None:
                pattern_mol = MoleculeParser.parse(pattern)
        else:
            pattern_mol = pattern

        if pattern_mol is None:
            return []

        return mol.GetSubstructMatches(pattern_mol)
