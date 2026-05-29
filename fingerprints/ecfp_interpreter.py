"""ECFP/Morgan fingerprint interpretation."""

from typing import Optional, Union
from dataclasses import dataclass
from rdkit import Chem
from rdkit.Chem import AllChem, Draw
from rdkit.Chem.Draw import rdMolDraw2D
import io
from PIL import Image

from core.molecule_parser import MoleculeParser
from core.fingerprint_engine import FingerprintEngine
from core.substructure_highlighter import SubstructureHighlighter


@dataclass
class ECFPBitInfo:
    """Information about a single ECFP bit."""

    bit_index: int
    center_atom: int
    radius: int
    atom_symbol: str
    environment_atoms: list[int]
    environment_smiles: Optional[str] = None


@dataclass
class ECFPInterpretation:
    """Container for ECFP interpretation results."""

    bit_index: int
    is_set: bool
    bit_info_list: list[ECFPBitInfo]
    fp_type: str  # "ECFP" or "FCFP"
    radius: int
    n_bits: int


class ECFPInterpreter:
    """Interpret and visualize ECFP/Morgan fingerprints."""

    @staticmethod
    def interpret_bit(
        smiles_or_mol: Union[str, Chem.Mol],
        bit_index: int,
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
    ) -> Optional[ECFPInterpretation]:
        """Interpret a specific bit in a Morgan fingerprint."""
        mol = ECFPInterpreter._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        # Generate fingerprint with bit info
        bit_info_map = {}
        if use_features:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol, radius, nBits=n_bits, useFeatures=True, bitInfo=bit_info_map
            )
        else:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol, radius, nBits=n_bits, bitInfo=bit_info_map
            )

        is_set = fp[bit_index] == 1

        bit_info_list = []
        if bit_index in bit_info_map:
            for center_atom, bit_radius in bit_info_map[bit_index]:
                atom = mol.GetAtomWithIdx(center_atom)
                env_atoms = ECFPInterpreter._get_environment_atoms(
                    mol, center_atom, bit_radius
                )

                # Try to get SMILES for the environment
                env_smiles = ECFPInterpreter._get_environment_smiles(
                    mol, env_atoms
                )

                bit_info_list.append(
                    ECFPBitInfo(
                        bit_index=bit_index,
                        center_atom=center_atom,
                        radius=bit_radius,
                        atom_symbol=atom.GetSymbol(),
                        environment_atoms=env_atoms,
                        environment_smiles=env_smiles,
                    )
                )

        fp_type = "FCFP" if use_features else "ECFP"

        return ECFPInterpretation(
            bit_index=bit_index,
            is_set=is_set,
            bit_info_list=bit_info_list,
            fp_type=fp_type,
            radius=radius,
            n_bits=n_bits,
        )

    @staticmethod
    def get_all_bit_info(
        smiles_or_mol: Union[str, Chem.Mol],
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
    ) -> dict[int, list[ECFPBitInfo]]:
        """Get information about all set bits in a fingerprint."""
        mol = ECFPInterpreter._ensure_mol(smiles_or_mol)
        if mol is None:
            return {}

        bit_info_map = {}
        if use_features:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol, radius, nBits=n_bits, useFeatures=True, bitInfo=bit_info_map
            )
        else:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol, radius, nBits=n_bits, bitInfo=bit_info_map
            )

        results = {}
        for bit_index, info_list in bit_info_map.items():
            bit_info_objs = []
            for center_atom, bit_radius in info_list:
                atom = mol.GetAtomWithIdx(center_atom)
                env_atoms = ECFPInterpreter._get_environment_atoms(
                    mol, center_atom, bit_radius
                )
                env_smiles = ECFPInterpreter._get_environment_smiles(mol, env_atoms)

                bit_info_objs.append(
                    ECFPBitInfo(
                        bit_index=bit_index,
                        center_atom=center_atom,
                        radius=bit_radius,
                        atom_symbol=atom.GetSymbol(),
                        environment_atoms=env_atoms,
                        environment_smiles=env_smiles,
                    )
                )
            results[bit_index] = bit_info_objs

        return results

    @staticmethod
    def get_on_bits_summary(
        smiles_or_mol: Union[str, Chem.Mol],
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
    ) -> list[dict]:
        """Get a summary of all on bits in the fingerprint."""
        all_info = ECFPInterpreter.get_all_bit_info(
            smiles_or_mol, radius, n_bits, use_features
        )

        summary = []
        for bit_index, bit_info_list in sorted(all_info.items()):
            for info in bit_info_list:
                summary.append(
                    {
                        "bit": bit_index,
                        "center_atom": info.center_atom,
                        "atom_symbol": info.atom_symbol,
                        "radius": info.radius,
                        "env_size": len(info.environment_atoms),
                        "env_smiles": info.environment_smiles,
                    }
                )

        return summary

    @staticmethod
    def draw_bit(
        smiles_or_mol: Union[str, Chem.Mol],
        bit_index: int,
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
        size: tuple = (400, 300),
    ) -> Optional[Image.Image]:
        """Draw a molecule with a specific bit highlighted."""
        mol = ECFPInterpreter._ensure_mol(smiles_or_mol)
        if mol is None:
            return None

        bit_info_map = {}
        if use_features:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol, radius, nBits=n_bits, useFeatures=True, bitInfo=bit_info_map
            )
        else:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol, radius, nBits=n_bits, bitInfo=bit_info_map
            )

        if bit_index not in bit_info_map:
            return None

        # Use RDKit's built-in Morgan bit drawing
        try:
            img = Draw.DrawMorganBit(
                mol, bit_index, bit_info_map, molSize=size, useSVG=False
            )
            return img
        except Exception:
            return None

    @staticmethod
    def compare_fingerprints(
        smiles1: str,
        smiles2: str,
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
    ) -> dict:
        """Compare fingerprints of two molecules."""
        mol1 = ECFPInterpreter._ensure_mol(smiles1)
        mol2 = ECFPInterpreter._ensure_mol(smiles2)

        if mol1 is None or mol2 is None:
            return {"error": "Invalid molecule(s)"}

        # Generate fingerprints
        result1 = FingerprintEngine.generate_morgan(
            mol1, radius, n_bits, use_features, include_bit_info=True
        )
        result2 = FingerprintEngine.generate_morgan(
            mol2, radius, n_bits, use_features, include_bit_info=True
        )

        if result1 is None or result2 is None:
            return {"error": "Failed to generate fingerprints"}

        on1 = set(result1.on_bits)
        on2 = set(result2.on_bits)

        # Calculate similarity
        tanimoto = FingerprintEngine.tanimoto_similarity(
            result1.fingerprint, result2.fingerprint
        )

        return {
            "unique_to_mol1": sorted(on1 - on2),
            "unique_to_mol2": sorted(on2 - on1),
            "common_bits": sorted(on1 & on2),
            "tanimoto_similarity": tanimoto,
            "mol1_on_bits": len(on1),
            "mol2_on_bits": len(on2),
        }

    @staticmethod
    def explain_bit(
        smiles_or_mol: Union[str, Chem.Mol],
        bit_index: int,
        radius: int = 2,
        n_bits: int = 2048,
        use_features: bool = False,
    ) -> str:
        """Generate a natural language explanation of a fingerprint bit."""
        interp = ECFPInterpreter.interpret_bit(
            smiles_or_mol, bit_index, radius, n_bits, use_features
        )

        if interp is None:
            return "Could not interpret bit (invalid molecule)."

        if not interp.is_set:
            return f"Bit {bit_index} is not set for this molecule with {interp.fp_type}{2*radius} parameters."

        if not interp.bit_info_list:
            return f"Bit {bit_index} is set but no structural information available."

        lines = [
            f"**{interp.fp_type}{2*radius} Bit {bit_index}**",
            f"This bit is set by {len(interp.bit_info_list)} atomic environment(s):",
            "",
        ]

        for i, info in enumerate(interp.bit_info_list, 1):
            lines.append(f"**Environment {i}:**")
            lines.append(f"- Center atom: {info.atom_symbol} (index {info.center_atom})")
            lines.append(f"- Radius: {info.radius}")
            lines.append(f"- Atoms in environment: {len(info.environment_atoms)}")
            if info.environment_smiles:
                lines.append(f"- Environment SMILES: `{info.environment_smiles}`")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _get_environment_atoms(
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
    def _get_environment_smiles(
        mol: Chem.Mol, atom_indices: list[int]
    ) -> Optional[str]:
        """Get SMILES for a subset of atoms."""
        try:
            # Create a copy of the molecule
            edit_mol = Chem.RWMol(mol)

            # Mark atoms to keep
            atoms_to_keep = set(atom_indices)

            # Remove atoms not in the environment (in reverse order)
            for idx in range(mol.GetNumAtoms() - 1, -1, -1):
                if idx not in atoms_to_keep:
                    edit_mol.RemoveAtom(idx)

            # Get SMILES
            return Chem.MolToSmiles(edit_mol.GetMol())
        except Exception:
            return None

    @staticmethod
    def _ensure_mol(smiles_or_mol: Union[str, Chem.Mol]) -> Optional[Chem.Mol]:
        """Ensure we have an RDKit molecule object."""
        if isinstance(smiles_or_mol, str):
            return MoleculeParser.parse(smiles_or_mol)
        return smiles_or_mol
