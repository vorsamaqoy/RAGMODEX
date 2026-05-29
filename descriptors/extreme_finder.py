"""Find molecules with extreme descriptor values."""

from typing import Optional, Union
from dataclasses import dataclass
from rdkit import Chem

from .descriptor_registry import DescriptorRegistry
from core.descriptor_calculator import DescriptorCalculator
from core.molecule_parser import MoleculeParser


@dataclass
class ExtremeExample:
    """Container for extreme value example."""

    smiles: str
    name: str
    value: float
    is_high: bool  # True for high extreme, False for low


# Pre-computed examples of molecules with extreme descriptor values
EXTREME_EXAMPLES = {
    "MolWt": {
        "high": [
            ExtremeExample("CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "Ibuprofen", 206.28, True),
            ExtremeExample("CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F", "Celecoxib", 381.37, True),
        ],
        "low": [
            ExtremeExample("C", "Methane", 16.04, False),
            ExtremeExample("CO", "Methanol", 32.04, False),
            ExtremeExample("CCO", "Ethanol", 46.07, False),
        ],
    },
    "MolLogP": {
        "high": [
            ExtremeExample("CCCCCCCCCCCCCCCC", "Hexadecane", 8.2, True),
            ExtremeExample("c1ccc2c(c1)ccc3ccccc32", "Phenanthrene", 4.46, True),
        ],
        "low": [
            ExtremeExample("OCC(O)C(O)C(O)C(O)CO", "Sorbitol", -2.2, False),
            ExtremeExample("OC(=O)C(O)C(O)C(=O)O", "Tartaric acid", -1.0, False),
        ],
    },
    "TPSA": {
        "high": [
            ExtremeExample("OC(=O)CC(O)(CC(=O)O)C(=O)O", "Citric acid", 132.13, True),
            ExtremeExample("NC(=O)NC(=O)N", "Biuret", 102.64, True),
        ],
        "low": [
            ExtremeExample("CCCCCCCC", "Octane", 0.0, False),
            ExtremeExample("c1ccccc1", "Benzene", 0.0, False),
        ],
    },
    "NumHDonors": {
        "high": [
            ExtremeExample("OCC(O)C(O)C(O)C(O)CO", "Sorbitol", 6, True),
            ExtremeExample("NC(=N)NC(=N)N", "Biguanide", 5, True),
        ],
        "low": [
            ExtremeExample("CCCCCC", "Hexane", 0, False),
            ExtremeExample("c1ccccc1", "Benzene", 0, False),
        ],
    },
    "NumHAcceptors": {
        "high": [
            ExtremeExample("OC(=O)CC(O)(CC(=O)O)C(=O)O", "Citric acid", 7, True),
            ExtremeExample("O=C1NC(=O)NC(=O)N1", "Cyanuric acid", 6, True),
        ],
        "low": [
            ExtremeExample("CCCCCC", "Hexane", 0, False),
            ExtremeExample("c1ccccc1", "Benzene", 0, False),
        ],
    },
    "NumRotatableBonds": {
        "high": [
            ExtremeExample("CCCCCCCCCCCCCCCC", "Hexadecane", 13, True),
            ExtremeExample("CCCCCCCCCCCCC(=O)O", "Myristic acid", 12, True),
        ],
        "low": [
            ExtremeExample("c1ccc2ccccc2c1", "Naphthalene", 0, False),
            ExtremeExample("C1CCC1", "Cyclobutane", 0, False),
        ],
    },
    "FractionCSP3": {
        "high": [
            ExtremeExample("C1CCCCC1", "Cyclohexane", 1.0, True),
            ExtremeExample("CC(C)(C)C", "Neopentane", 1.0, True),
        ],
        "low": [
            ExtremeExample("c1ccccc1", "Benzene", 0.0, False),
            ExtremeExample("c1ccc2ccccc2c1", "Naphthalene", 0.0, False),
        ],
    },
    "RingCount": {
        "high": [
            ExtremeExample("c1ccc2c(c1)cc3ccc4cccc5ccc2c3c45", "Pyrene", 4, True),
            ExtremeExample("C1CCC2C(C1)CCC3CCCCC23", "Perhydronaphthalene", 2, True),
        ],
        "low": [
            ExtremeExample("CCCCCC", "Hexane", 0, False),
            ExtremeExample("CC(C)C", "Isobutane", 0, False),
        ],
    },
    "NumAromaticRings": {
        "high": [
            ExtremeExample("c1ccc2c(c1)cc3ccc4cccc5ccc2c3c45", "Pyrene", 4, True),
            ExtremeExample("c1ccc2c(c1)ccc3ccccc32", "Phenanthrene", 3, True),
        ],
        "low": [
            ExtremeExample("C1CCCCC1", "Cyclohexane", 0, False),
            ExtremeExample("CCCCCC", "Hexane", 0, False),
        ],
    },
}


class ExtremeFinder:
    """Find and display molecules with extreme descriptor values."""

    def __init__(self):
        """Initialize the extreme finder."""
        self._calculator = DescriptorCalculator()

    def get_examples(
        self, descriptor_name: str, extreme_type: str = "both"
    ) -> list[ExtremeExample]:
        """Get example molecules with extreme values for a descriptor."""
        if descriptor_name not in EXTREME_EXAMPLES:
            return []

        examples = EXTREME_EXAMPLES[descriptor_name]

        if extreme_type == "high":
            return examples.get("high", [])
        elif extreme_type == "low":
            return examples.get("low", [])
        else:  # both
            return examples.get("high", []) + examples.get("low", [])

    def find_extremes_in_list(
        self,
        smiles_list: list[str],
        descriptor_name: str,
        top_n: int = 5,
    ) -> dict[str, list[tuple[str, float]]]:
        """Find molecules with highest/lowest values from a list."""
        if not DescriptorRegistry.is_valid_descriptor(descriptor_name):
            return {"error": f"Unknown descriptor: {descriptor_name}"}

        # Calculate descriptor for all molecules
        values = []
        for smiles in smiles_list:
            value = self._calculator.calculate(smiles, descriptor_name)
            if value is not None:
                values.append((smiles, value))

        if not values:
            return {"highest": [], "lowest": []}

        # Sort by value
        sorted_values = sorted(values, key=lambda x: x[1], reverse=True)

        return {
            "highest": sorted_values[:top_n],
            "lowest": sorted_values[-top_n:][::-1],
        }

    def compare_to_extremes(
        self,
        smiles_or_mol: Union[str, Chem.Mol],
        descriptor_name: str,
    ) -> dict:
        """Compare a molecule's descriptor value to known extremes."""
        value = self._calculator.calculate(smiles_or_mol, descriptor_name)
        if value is None:
            return {"error": "Could not calculate descriptor"}

        examples = self.get_examples(descriptor_name)
        if not examples:
            return {
                "value": value,
                "message": "No extreme examples available for comparison",
            }

        high_examples = [e for e in examples if e.is_high]
        low_examples = [e for e in examples if not e.is_high]

        # Find where the value falls
        result = {
            "value": value,
            "descriptor": descriptor_name,
        }

        if high_examples:
            max_example = max(high_examples, key=lambda x: x.value)
            result["highest_known"] = {
                "name": max_example.name,
                "smiles": max_example.smiles,
                "value": max_example.value,
            }
            result["percent_of_max"] = (value / max_example.value) * 100 if max_example.value != 0 else 0

        if low_examples:
            min_example = min(low_examples, key=lambda x: x.value)
            result["lowest_known"] = {
                "name": min_example.name,
                "smiles": min_example.smiles,
                "value": min_example.value,
            }

        return result

    def format_examples(self, descriptor_name: str) -> str:
        """Format extreme examples for display."""
        examples = self.get_examples(descriptor_name)
        if not examples:
            return f"No extreme examples available for {descriptor_name}"

        high_examples = [e for e in examples if e.is_high]
        low_examples = [e for e in examples if not e.is_high]

        lines = [f"## Extreme Examples for {descriptor_name}", ""]

        if high_examples:
            lines.append("### High Values")
            for ex in high_examples:
                lines.append(f"- **{ex.name}** ({ex.smiles}): {ex.value}")
            lines.append("")

        if low_examples:
            lines.append("### Low Values")
            for ex in low_examples:
                lines.append(f"- **{ex.name}** ({ex.smiles}): {ex.value}")

        return "\n".join(lines)

    def suggest_modifications(
        self,
        smiles: str,
        descriptor_name: str,
        direction: str,
    ) -> list[str]:
        """Suggest general modifications to increase/decrease a descriptor."""
        suggestions = {
            "MolWt": {
                "increase": [
                    "Add heavy atoms (halogens like Br, I)",
                    "Add aromatic rings",
                    "Extend carbon chains",
                ],
                "decrease": [
                    "Remove bulky groups",
                    "Replace heavy halogens with lighter ones (I→F)",
                    "Truncate carbon chains",
                ],
            },
            "MolLogP": {
                "increase": [
                    "Add lipophilic groups (alkyl chains, halogens)",
                    "Remove polar groups (OH, NH2)",
                    "Add aromatic rings",
                ],
                "decrease": [
                    "Add polar groups (OH, NH2, COOH)",
                    "Add ionizable groups",
                    "Replace aromatic rings with saturated ones",
                ],
            },
            "TPSA": {
                "increase": [
                    "Add polar groups (OH, NH2, C=O)",
                    "Add heteroatoms (N, O)",
                    "Convert C-C to C-N or C-O",
                ],
                "decrease": [
                    "Remove polar groups",
                    "Replace N/O with C",
                    "Add lipophilic groups",
                ],
            },
            "NumRotatableBonds": {
                "increase": [
                    "Add flexible linkers (-CH2-CH2-)",
                    "Replace rings with open chains",
                    "Add ether linkages (-O-)",
                ],
                "decrease": [
                    "Cyclize flexible chains",
                    "Add rigid scaffolds",
                    "Use double bonds or aromatic systems",
                ],
            },
            "FractionCSP3": {
                "increase": [
                    "Add saturated carbons",
                    "Replace aromatic rings with aliphatic",
                    "Add cycloalkyl groups",
                ],
                "decrease": [
                    "Add aromatic rings",
                    "Add double/triple bonds",
                    "Remove aliphatic carbons",
                ],
            },
        }

        if descriptor_name not in suggestions:
            return [f"No specific suggestions available for {descriptor_name}"]

        direction_suggestions = suggestions[descriptor_name].get(direction, [])
        if not direction_suggestions:
            return [f"No suggestions for {direction}ing {descriptor_name}"]

        return direction_suggestions
