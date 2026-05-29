"""MACCS key interpretation and visualization."""

from typing import Optional, Union
from dataclasses import dataclass
from rdkit import Chem
from rdkit.Chem import MACCSkeys

from .maccs_keys import MACCSKeys, MACCSKeyDefinition
from core.molecule_parser import MoleculeParser
from core.substructure_highlighter import SubstructureHighlighter, HighlightInfo


@dataclass
class MACCSInterpretation:
    """Container for MACCS key interpretation results."""

    key_number: int
    definition: MACCSKeyDefinition
    smarts: str
    description: str
    category: str
    is_present: Optional[bool] = None
    matches: Optional[list[HighlightInfo]] = None
    explanation: Optional[str] = None


class MACCSInterpreter:
    """Interpret and visualize MACCS keys."""

    @staticmethod
    def _get_rdkit_smarts(key_number: int) -> Optional[str]:
        """Return the SMARTS pattern RDKit actually uses internally for this MACCS key.

        RDKit's MACCSkeys.smartsPatts maps bit → (smarts, count_threshold).
        Using these patterns for visualization guarantees that bit detection
        (via GenMACCSKeys) and substructure matching are always consistent.
        """
        try:
            entry = MACCSkeys.smartsPatts.get(key_number)
            if entry:
                smarts = entry[0]
                if smarts and smarts != "?":
                    return smarts
        except AttributeError:
            pass
        return None

    @staticmethod
    def interpret_key(key_number: int) -> Optional[MACCSInterpretation]:
        """Get interpretation for a specific MACCS key."""
        if not MACCSKeys.is_valid_key(key_number):
            return None

        definition = MACCSKeys.get_key(key_number)
        explanation = MACCSInterpreter._generate_explanation(definition)

        # Prefer RDKit's own SMARTS (guaranteed consistent with fingerprint computation)
        rdkit_smarts = MACCSInterpreter._get_rdkit_smarts(key_number)
        display_smarts = rdkit_smarts if rdkit_smarts else definition.smarts

        return MACCSInterpretation(
            key_number=key_number,
            definition=definition,
            smarts=display_smarts,
            description=definition.description,
            category=definition.category,
            explanation=explanation,
        )

    @staticmethod
    def check_key_in_molecule(
        key_number: int, smiles_or_mol: Union[str, Chem.Mol]
    ) -> Optional[MACCSInterpretation]:
        """Check if a specific MACCS key is present in a molecule."""
        interp = MACCSInterpreter.interpret_key(key_number)
        if interp is None:
            return None

        mol = MACCSInterpreter._ensure_mol(smiles_or_mol)
        if mol is None:
            return interp

        # Generate MACCS fingerprint and check bit
        fp = MACCSkeys.GenMACCSKeys(mol)
        interp.is_present = fp[key_number] == 1

        # Use RDKit's own SMARTS for matching — same pattern used to set the bit
        if interp.is_present and interp.smarts not in ["?", ""]:
            matches = SubstructureHighlighter.find_matches(mol, interp.smarts)
            interp.matches = matches

        return interp

    @staticmethod
    def get_active_keys(
        smiles_or_mol: Union[str, Chem.Mol]
    ) -> list[MACCSInterpretation]:
        """Get all active MACCS keys for a molecule."""
        mol = MACCSInterpreter._ensure_mol(smiles_or_mol)
        if mol is None:
            return []

        fp = MACCSkeys.GenMACCSKeys(mol)
        on_bits = list(fp.GetOnBits())

        results = []
        for bit in on_bits:
            if bit == 0:  # Skip bit 0 (not used)
                continue
            interp = MACCSInterpreter.interpret_key(bit)
            if interp:
                interp.is_present = True
                # Find matches
                if interp.smarts not in ["?", ""]:
                    matches = SubstructureHighlighter.find_matches(mol, interp.smarts)
                    interp.matches = matches
                results.append(interp)

        return results

    @staticmethod
    def get_inactive_keys(
        smiles_or_mol: Union[str, Chem.Mol]
    ) -> list[MACCSInterpretation]:
        """Get all inactive MACCS keys for a molecule."""
        mol = MACCSInterpreter._ensure_mol(smiles_or_mol)
        if mol is None:
            return []

        fp = MACCSkeys.GenMACCSKeys(mol)
        on_bits = set(fp.GetOnBits())

        results = []
        for key_number in range(1, 167):
            if key_number not in on_bits:
                interp = MACCSInterpreter.interpret_key(key_number)
                if interp:
                    interp.is_present = False
                    results.append(interp)

        return results

    @staticmethod
    def compare_molecules(
        smiles1: str, smiles2: str
    ) -> dict[str, list[MACCSInterpretation]]:
        """Compare MACCS keys between two molecules."""
        mol1 = MACCSInterpreter._ensure_mol(smiles1)
        mol2 = MACCSInterpreter._ensure_mol(smiles2)

        if mol1 is None or mol2 is None:
            return {"error": "Invalid molecule(s)"}

        fp1 = MACCSkeys.GenMACCSKeys(mol1)
        fp2 = MACCSkeys.GenMACCSKeys(mol2)

        on1 = set(fp1.GetOnBits())
        on2 = set(fp2.GetOnBits())

        # Keys unique to molecule 1
        unique_to_1 = []
        for bit in on1 - on2:
            if bit > 0:
                interp = MACCSInterpreter.interpret_key(bit)
                if interp:
                    interp.is_present = True
                    unique_to_1.append(interp)

        # Keys unique to molecule 2
        unique_to_2 = []
        for bit in on2 - on1:
            if bit > 0:
                interp = MACCSInterpreter.interpret_key(bit)
                if interp:
                    interp.is_present = True
                    unique_to_2.append(interp)

        # Keys common to both
        common = []
        for bit in on1 & on2:
            if bit > 0:
                interp = MACCSInterpreter.interpret_key(bit)
                if interp:
                    interp.is_present = True
                    common.append(interp)

        return {
            "unique_to_molecule1": unique_to_1,
            "unique_to_molecule2": unique_to_2,
            "common": common,
        }

    @staticmethod
    def get_keys_by_category(
        smiles_or_mol: Union[str, Chem.Mol], category: str
    ) -> list[MACCSInterpretation]:
        """Get active MACCS keys in a specific category for a molecule."""
        active_keys = MACCSInterpreter.get_active_keys(smiles_or_mol)
        return [k for k in active_keys if k.category == category]

    @staticmethod
    def _generate_explanation(definition: MACCSKeyDefinition) -> str:
        """Generate a natural language explanation for a MACCS key."""
        key = definition.key_number
        desc = definition.description
        smarts = definition.smarts
        cat = definition.category

        if smarts == "?":
            return f"MACCS key {key}: {desc}. This key is not implemented in standard fingerprints."

        explanations = {
            "element": f"MACCS key {key} detects the presence of {desc}. "
            f"The SMARTS pattern '{smarts}' matches atoms of this element type.",
            "functional": f"MACCS key {key} identifies the {desc} functional group or substructure. "
            f"The SMARTS pattern '{smarts}' matches this structural feature.",
            "ring": f"MACCS key {key} detects {desc}. "
            f"The SMARTS pattern '{smarts}' identifies this ring system.",
            "aromatic": f"MACCS key {key} identifies {desc}. "
            f"The SMARTS pattern '{smarts}' matches aromatic systems.",
            "topology": f"MACCS key {key} captures the topological feature: {desc}. "
            f"The SMARTS pattern '{smarts}' identifies this structural arrangement.",
            "special": f"MACCS key {key}: {desc}. This is a special key that may have unique behavior.",
        }

        return explanations.get(
            cat,
            f"MACCS key {key}: {desc}. SMARTS pattern: '{smarts}'.",
        )

    @staticmethod
    def format_interpretation(interp: MACCSInterpretation) -> str:
        """Format an interpretation for display."""
        lines = [
            f"**MACCS Key {interp.key_number}**",
            f"- Description: {interp.description}",
            f"- SMARTS: `{interp.smarts}`",
            f"- Category: {interp.category}",
        ]

        if interp.is_present is not None:
            status = "Present" if interp.is_present else "Absent"
            lines.append(f"- Status: {status}")

        if interp.matches:
            lines.append(f"- Matches found: {len(interp.matches)}")

        if interp.explanation:
            lines.append(f"\n{interp.explanation}")

        return "\n".join(lines)

    @staticmethod
    def _ensure_mol(smiles_or_mol: Union[str, Chem.Mol]) -> Optional[Chem.Mol]:
        """Ensure we have an RDKit molecule object."""
        if isinstance(smiles_or_mol, str):
            return MoleculeParser.parse(smiles_or_mol)
        return smiles_or_mol
