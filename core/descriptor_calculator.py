"""RDKit descriptor calculation engine."""

from typing import Optional, Union, Any
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors, Lipinski, Crippen, MolSurf
from rdkit.Chem import GraphDescriptors, Fragments
from rdkit.ML.Descriptors import MoleculeDescriptors

from .molecule_parser import MoleculeParser


class DescriptorCalculator:
    """Calculate RDKit molecular descriptors."""

    # All available descriptors from Descriptors module
    ALL_DESCRIPTORS = [desc[0] for desc in Descriptors.descList]

    def __init__(self):
        """Initialize the descriptor calculator."""
        self._calc = MoleculeDescriptors.MolecularDescriptorCalculator(
            self.ALL_DESCRIPTORS
        )

    def calculate(
        self, smiles_or_mol: Union[str, Chem.Mol], descriptor_name: str
    ) -> Optional[float]:
        """Calculate a single descriptor for a molecule."""
        mol = self._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        # Try to get the descriptor function
        if hasattr(Descriptors, descriptor_name):
            func = getattr(Descriptors, descriptor_name)
            try:
                return func(mol)
            except Exception:
                return None
        return None

    def calculate_all(
        self, smiles_or_mol: Union[str, Chem.Mol]
    ) -> Optional[dict[str, float]]:
        """Calculate all descriptors for a molecule."""
        mol = self._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        try:
            values = self._calc.CalcDescriptors(mol)
            return dict(zip(self.ALL_DESCRIPTORS, values))
        except Exception:
            return None

    def calculate_selected(
        self, smiles_or_mol: Union[str, Chem.Mol], descriptor_names: list[str]
    ) -> Optional[dict[str, float]]:
        """Calculate selected descriptors for a molecule."""
        mol = self._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        results = {}
        for name in descriptor_names:
            value = self.calculate(mol, name)
            if value is not None:
                results[name] = value
        return results

    def calculate_physicochemical(
        self, smiles_or_mol: Union[str, Chem.Mol]
    ) -> Optional[dict[str, float]]:
        """Calculate common physicochemical properties."""
        mol = self._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        return {
            "MolWt": Descriptors.MolWt(mol),
            "ExactMolWt": Descriptors.ExactMolWt(mol),
            "HeavyAtomMolWt": Descriptors.HeavyAtomMolWt(mol),
            "LogP": Crippen.MolLogP(mol),
            "MR": Crippen.MolMR(mol),
            "TPSA": rdMolDescriptors.CalcTPSA(mol),
            "LabuteASA": rdMolDescriptors.CalcLabuteASA(mol),
            "NumHDonors": Lipinski.NumHDonors(mol),
            "NumHAcceptors": Lipinski.NumHAcceptors(mol),
            "NumRotatableBonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
            "NumHeteroatoms": Lipinski.NumHeteroatoms(mol),
            "NumAromaticRings": rdMolDescriptors.CalcNumAromaticRings(mol),
            "NumSaturatedRings": rdMolDescriptors.CalcNumSaturatedRings(mol),
            "NumAliphaticRings": rdMolDescriptors.CalcNumAliphaticRings(mol),
            "RingCount": rdMolDescriptors.CalcNumRings(mol),
            "FractionCSP3": rdMolDescriptors.CalcFractionCSP3(mol),
            "NumHeavyAtoms": mol.GetNumHeavyAtoms(),
        }

    def calculate_lipinski(
        self, smiles_or_mol: Union[str, Chem.Mol]
    ) -> Optional[dict[str, Any]]:
        """Calculate Lipinski's Rule of Five descriptors."""
        mol = self._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        mw = Descriptors.MolWt(mol)
        logp = Crippen.MolLogP(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)

        violations = sum(
            [
                mw > 500,
                logp > 5,
                hbd > 5,
                hba > 10,
            ]
        )

        return {
            "MolWt": mw,
            "LogP": logp,
            "NumHDonors": hbd,
            "NumHAcceptors": hba,
            "Violations": violations,
            "PassesRo5": violations == 0,
        }

    def calculate_topological(
        self, smiles_or_mol: Union[str, Chem.Mol]
    ) -> Optional[dict[str, float]]:
        """Calculate topological descriptors."""
        mol = self._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        return {
            "BalabanJ": GraphDescriptors.BalabanJ(mol),
            "BertzCT": GraphDescriptors.BertzCT(mol),
            "Chi0": GraphDescriptors.Chi0(mol),
            "Chi0n": GraphDescriptors.Chi0n(mol),
            "Chi0v": GraphDescriptors.Chi0v(mol),
            "Chi1": GraphDescriptors.Chi1(mol),
            "Chi1n": GraphDescriptors.Chi1n(mol),
            "Chi1v": GraphDescriptors.Chi1v(mol),
            "HallKierAlpha": GraphDescriptors.HallKierAlpha(mol),
            "Kappa1": GraphDescriptors.Kappa1(mol),
            "Kappa2": GraphDescriptors.Kappa2(mol),
            "Kappa3": GraphDescriptors.Kappa3(mol),
        }

    def get_descriptor_value(
        self, smiles_or_mol: Union[str, Chem.Mol], descriptor_name: str
    ) -> tuple[Optional[float], str]:
        """Get descriptor value with error handling."""
        mol = self._ensure_mol(smiles_or_mol)
        if mol is None:
            return None, "Invalid molecule"

        if descriptor_name not in self.ALL_DESCRIPTORS:
            return None, f"Unknown descriptor: {descriptor_name}"

        try:
            value = self.calculate(mol, descriptor_name)
            if value is None:
                return None, "Failed to calculate descriptor"
            return value, "Success"
        except Exception as e:
            return None, f"Error: {str(e)}"

    @staticmethod
    def list_all_descriptors() -> list[str]:
        """List all available descriptor names."""
        return [desc[0] for desc in Descriptors.descList]

    @staticmethod
    def get_descriptor_info(descriptor_name: str) -> Optional[tuple[str, str]]:
        """Get descriptor name and function from descList."""
        for name, func in Descriptors.descList:
            if name == descriptor_name:
                doc = func.__doc__ or "No documentation available"
                return name, doc
        return None

    def _ensure_mol(self, smiles_or_mol: Union[str, Chem.Mol]) -> Optional[Chem.Mol]:
        """Ensure we have an RDKit molecule object."""
        if isinstance(smiles_or_mol, str):
            return MoleculeParser.parse(smiles_or_mol)
        return smiles_or_mol
