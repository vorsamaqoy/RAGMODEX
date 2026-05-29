"""Fingerprint generation engine."""

from typing import Optional, Union
from dataclasses import dataclass
from rdkit import Chem
from rdkit.Chem import AllChem, MACCSkeys, rdMolDescriptors
from rdkit import DataStructs
import numpy as np

from .molecule_parser import MoleculeParser


@dataclass
class FingerprintResult:
    """Container for fingerprint computation results."""

    fingerprint: DataStructs.ExplicitBitVect
    on_bits: list[int]
    num_on_bits: int
    num_bits: int
    bit_info: Optional[dict] = None


class FingerprintEngine:
    """Generate and analyze molecular fingerprints."""

    @staticmethod
    def generate_maccs(
        smiles_or_mol: Union[str, Chem.Mol]
    ) -> Optional[FingerprintResult]:
        """Generate MACCS keys fingerprint (166 bits)."""
        mol = FingerprintEngine._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        fp = MACCSkeys.GenMACCSKeys(mol)
        on_bits = list(fp.GetOnBits())

        return FingerprintResult(
            fingerprint=fp,
            on_bits=on_bits,
            num_on_bits=len(on_bits),
            num_bits=167,  # MACCS has 167 bits (0-166)
        )

    @staticmethod
    def generate_morgan(
        smiles_or_mol: Union[str, Chem.Mol],
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
        include_bit_info: bool = False,
    ) -> Optional[FingerprintResult]:
        """Generate Morgan (ECFP/FCFP) fingerprint."""
        mol = FingerprintEngine._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        bit_info = {} if include_bit_info else None

        if use_features:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol,
                radius,
                nBits=n_bits,
                useFeatures=True,
                bitInfo=bit_info,
            )
        else:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol,
                radius,
                nBits=n_bits,
                bitInfo=bit_info,
            )

        on_bits = list(fp.GetOnBits())

        return FingerprintResult(
            fingerprint=fp,
            on_bits=on_bits,
            num_on_bits=len(on_bits),
            num_bits=n_bits,
            bit_info=bit_info,
        )

    @staticmethod
    def generate_rdkit_fp(
        smiles_or_mol: Union[str, Chem.Mol],
        min_path: int = 1,
        max_path: int = 7,
        n_bits: int = 2048,
    ) -> Optional[FingerprintResult]:
        """Generate RDKit topological fingerprint."""
        mol = FingerprintEngine._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        fp = Chem.RDKFingerprint(mol, minPath=min_path, maxPath=max_path, fpSize=n_bits)
        on_bits = list(fp.GetOnBits())

        return FingerprintResult(
            fingerprint=fp,
            on_bits=on_bits,
            num_on_bits=len(on_bits),
            num_bits=n_bits,
        )

    @staticmethod
    def generate_atom_pair(
        smiles_or_mol: Union[str, Chem.Mol],
        n_bits: int = 2048,
    ) -> Optional[FingerprintResult]:
        """Generate atom pair fingerprint."""
        mol = FingerprintEngine._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        fp = rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect(mol, nBits=n_bits)
        on_bits = list(fp.GetOnBits())

        return FingerprintResult(
            fingerprint=fp,
            on_bits=on_bits,
            num_on_bits=len(on_bits),
            num_bits=n_bits,
        )

    @staticmethod
    def generate_topological_torsion(
        smiles_or_mol: Union[str, Chem.Mol],
        n_bits: int = 2048,
    ) -> Optional[FingerprintResult]:
        """Generate topological torsion fingerprint."""
        mol = FingerprintEngine._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        fp = rdMolDescriptors.GetHashedTopologicalTorsionFingerprintAsBitVect(
            mol, nBits=n_bits
        )
        on_bits = list(fp.GetOnBits())

        return FingerprintResult(
            fingerprint=fp,
            on_bits=on_bits,
            num_on_bits=len(on_bits),
            num_bits=n_bits,
        )

    @staticmethod
    def get_morgan_bit_info(
        smiles_or_mol: Union[str, Chem.Mol],
        bit_index: int,
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
    ) -> Optional[list[tuple[int, int]]]:
        """Get information about which atoms contribute to a specific Morgan bit."""
        mol = FingerprintEngine._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

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

        return bit_info.get(bit_index)

    @staticmethod
    def tanimoto_similarity(fp1: DataStructs.ExplicitBitVect, fp2: DataStructs.ExplicitBitVect) -> float:
        """Calculate Tanimoto similarity between two fingerprints."""
        return DataStructs.TanimotoSimilarity(fp1, fp2)

    @staticmethod
    def dice_similarity(fp1: DataStructs.ExplicitBitVect, fp2: DataStructs.ExplicitBitVect) -> float:
        """Calculate Dice similarity between two fingerprints."""
        return DataStructs.DiceSimilarity(fp1, fp2)

    @staticmethod
    def fingerprint_to_array(fp: DataStructs.ExplicitBitVect) -> np.ndarray:
        """Convert fingerprint to numpy array."""
        arr = np.zeros(fp.GetNumBits(), dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fp, arr)
        return arr

    @staticmethod
    def check_maccs_key(
        smiles_or_mol: Union[str, Chem.Mol], key_number: int
    ) -> Optional[bool]:
        """Check if a specific MACCS key is set for a molecule."""
        if key_number < 1 or key_number > 166:
            return None

        result = FingerprintEngine.generate_maccs(smiles_or_mol)
        if result is None:
            return None

        return key_number in result.on_bits

    @staticmethod
    def get_maccs_on_bits(smiles_or_mol: Union[str, Chem.Mol]) -> Optional[list[int]]:
        """Get all MACCS keys that are on for a molecule."""
        result = FingerprintEngine.generate_maccs(smiles_or_mol)
        if result is None:
            return None
        return result.on_bits

    @staticmethod
    def _ensure_mol(smiles_or_mol: Union[str, Chem.Mol]) -> Optional[Chem.Mol]:
        """Ensure we have an RDKit molecule object."""
        if isinstance(smiles_or_mol, str):
            return MoleculeParser.parse(smiles_or_mol)
        return smiles_or_mol
