"""Natural language explanations for molecular descriptors."""

from typing import Optional, Union
from rdkit import Chem

from .descriptor_registry import DescriptorRegistry, DescriptorInfo
from core.descriptor_calculator import DescriptorCalculator
from core.molecule_parser import MoleculeParser


# Detailed explanations for common descriptors
DESCRIPTOR_EXPLANATIONS = {
    "MolWt": """
**Molecular Weight (MolWt)**

The average molecular weight of a molecule, calculated using the average atomic masses of each element. This is the mass you would measure experimentally for a sample of the compound.

**Significance in Drug Discovery:**
- Lipinski's Rule of Five suggests MW < 500 Da for oral bioavailability
- Higher MW molecules tend to have poorer absorption
- Typical drug-like molecules: 150-500 Da

**Calculation:** Sum of (atomic mass × count) for all atoms including hydrogens.
""",

    "ExactMolWt": """
**Exact Molecular Weight (ExactMolWt)**

The molecular weight calculated using the exact mass of the most abundant isotope of each element (monoisotopic mass). This is what you would see in high-resolution mass spectrometry.

**Difference from MolWt:** ExactMolWt uses ¹²C = 12.0000, ¹H = 1.0078, etc., while MolWt uses average atomic masses.
""",

    "MolLogP": """
**Partition Coefficient (MolLogP)**

The Wildman-Crippen LogP value, measuring lipophilicity as log₁₀ of the octanol/water partition coefficient.

**Interpretation:**
- LogP < 0: Hydrophilic (water-loving)
- LogP = 0-3: Intermediate lipophilicity (ideal for oral drugs)
- LogP > 5: Very lipophilic (may have solubility issues)

**Drug Discovery Relevance:**
- Affects membrane permeability, absorption, distribution
- Lipinski's Rule: LogP ≤ 5 for good oral bioavailability
- Higher LogP → better membrane penetration but worse solubility
""",

    "TPSA": """
**Topological Polar Surface Area (TPSA)**

The surface area (Å²) occupied by nitrogen and oxygen atoms, plus attached hydrogens. Calculated using 2D structure (topology), not 3D geometry.

**Interpretation:**
- TPSA < 60 Å²: Good CNS penetration
- TPSA < 140 Å²: Good intestinal absorption
- TPSA > 140 Å²: Poor oral bioavailability

**Applications:**
- Predicting blood-brain barrier penetration
- Estimating oral absorption
- Part of many drug-likeness filters
""",

    "NumHDonors": """
**Number of Hydrogen Bond Donors (NumHDonors)**

Count of NH and OH groups that can donate hydrogen bonds.

**Drug Discovery Rules:**
- Lipinski's Rule: ≤ 5 H-bond donors
- Affects solubility, permeability, and protein binding
- Too many donors → poor membrane permeability
""",

    "NumHAcceptors": """
**Number of Hydrogen Bond Acceptors (NumHAcceptors)**

Count of N and O atoms that can accept hydrogen bonds.

**Drug Discovery Rules:**
- Lipinski's Rule: ≤ 10 H-bond acceptors
- Affects aqueous solubility and protein interactions
- Each acceptor increases hydrophilicity
""",

    "NumRotatableBonds": """
**Number of Rotatable Bonds (NumRotatableBonds)**

Count of bonds that allow free rotation (excluding rings, double bonds, and terminal groups).

**Significance:**
- Affects molecular flexibility and conformational entropy
- More rotatable bonds → entropy penalty upon binding
- Veber's Rule: ≤ 10 for good oral bioavailability
- Affects crystal packing and thus solubility
""",

    "NumHeavyAtoms": """
**Number of Heavy Atoms (NumHeavyAtoms)**

Count of non-hydrogen atoms in the molecule.

**Uses:**
- Simple measure of molecular size
- Normalization factor for other descriptors
- Correlates with molecular weight
""",

    "RingCount": """
**Ring Count (RingCount)**

Total number of rings in the molecule (SSSR - Smallest Set of Smallest Rings).

**Drug Discovery:**
- Rings provide rigidity and defined 3D shape
- Too many rings → poor solubility
- Fused rings reduce flexibility
""",

    "NumAromaticRings": """
**Number of Aromatic Rings (NumAromaticRings)**

Count of aromatic (typically 6-membered, planar, conjugated) rings.

**Properties:**
- Aromatic rings are flat and rigid
- Contribute to LogP (lipophilicity)
- Often involved in π-π stacking interactions with proteins
""",

    "FractionCSP3": """
**Fraction of sp³ Carbons (Fsp³)**

Ratio of sp³ hybridized carbons to total carbons. Measures "saturation" or 3D character.

**Interpretation:**
- Fsp³ = 0: Fully flat/aromatic (e.g., benzene)
- Fsp³ = 1: Fully saturated (e.g., cyclohexane)
- Higher Fsp³ → better solubility, more 3D shape

**Drug Discovery:**
- "Escape from flatland" - higher Fsp³ improves success rates
- Typical drugs: Fsp³ = 0.3-0.6
- Flat molecules more prone to promiscuity
""",

    "BertzCT": """
**Bertz Complexity Index (BertzCT)**

A topological complexity measure based on symmetry and bonding patterns.

**Calculation:** Based on the graph theory of molecular structure, considering atom connectivity and bond orders.

**Use:** Comparing structural complexity across molecule series.
""",

    "BalabanJ": """
**Balaban J Index (BalabanJ)**

A topological index measuring molecular shape/branching. Lower values indicate more spherical molecules, higher values indicate more elongated shapes.

**Properties:**
- Normalized for molecular size
- Useful for QSAR modeling
- Correlates with molecular geometry
""",

    "HallKierAlpha": """
**Hall-Kier Alpha Value**

A descriptor related to molecular shape/volume, calculated from atom hybridization states.

**Interpretation:**
- Positive values: bulky molecules
- Near zero: linear molecules
- Used in Kappa shape index calculations
""",

    "qed": """
**Quantitative Estimate of Drug-Likeness (QED)**

A score from 0 to 1 indicating overall drug-likeness, combining multiple physicochemical properties.

**Calculation:** Weighted combination of MW, LogP, TPSA, HBD, HBA, rotatable bonds, aromatic rings, and alerts.

**Interpretation:**
- QED > 0.67: High drug-likeness
- QED 0.33-0.67: Medium drug-likeness
- QED < 0.33: Low drug-likeness
""",
}


class DescriptorExplainer:
    """Generate natural language explanations for descriptors."""

    def __init__(self):
        """Initialize the explainer."""
        self._calculator = DescriptorCalculator()

    def explain(self, descriptor_name: str) -> str:
        """Get a detailed explanation of a descriptor."""
        # Check if we have a detailed explanation
        if descriptor_name in DESCRIPTOR_EXPLANATIONS:
            return DESCRIPTOR_EXPLANATIONS[descriptor_name].strip()

        # Fall back to metadata
        info = DescriptorRegistry.get_info(descriptor_name)
        if info:
            return self._format_from_metadata(info)

        # Check if it's a valid descriptor at all
        if DescriptorRegistry.is_valid_descriptor(descriptor_name):
            return f"**{descriptor_name}**\n\nA molecular descriptor available in RDKit. Detailed documentation not available in the registry."

        return f"Unknown descriptor: {descriptor_name}"

    def explain_with_value(
        self,
        descriptor_name: str,
        smiles_or_mol: Union[str, Chem.Mol],
    ) -> str:
        """Explain a descriptor and show its value for a specific molecule."""
        explanation = self.explain(descriptor_name)

        # Calculate the value
        value, status = self._calculator.get_descriptor_value(
            smiles_or_mol, descriptor_name
        )

        if value is not None:
            # Get molecule info
            if isinstance(smiles_or_mol, str):
                mol_info = MoleculeParser.get_info(smiles_or_mol)
                mol_desc = f"**{mol_info.canonical_smiles}**"
            else:
                mol_desc = "the provided molecule"

            # Format value
            if isinstance(value, float):
                formatted_value = f"{value:.4f}"
            else:
                formatted_value = str(value)

            # Get unit if available
            info = DescriptorRegistry.get_info(descriptor_name)
            unit = info.unit if info and info.unit else ""
            unit_str = f" {unit}" if unit else ""

            explanation += f"\n\n---\n**Value for {mol_desc}:** {formatted_value}{unit_str}"

            # Add interpretation if possible
            interpretation = self._interpret_value(descriptor_name, value)
            if interpretation:
                explanation += f"\n\n{interpretation}"

        else:
            explanation += f"\n\n---\n*Could not calculate value: {status}*"

        return explanation

    def get_brief_explanation(self, descriptor_name: str) -> str:
        """Get a one-line explanation of a descriptor."""
        info = DescriptorRegistry.get_info(descriptor_name)
        if info:
            return info.description

        # Check if it's in our detailed explanations
        if descriptor_name in DESCRIPTOR_EXPLANATIONS:
            # Extract first meaningful sentence
            text = DESCRIPTOR_EXPLANATIONS[descriptor_name].strip()
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("**") and not line.startswith("-"):
                    return line[:200]

        if DescriptorRegistry.is_valid_descriptor(descriptor_name):
            return f"RDKit molecular descriptor"

        return "Unknown descriptor"

    def compare_descriptors(self, desc1: str, desc2: str) -> str:
        """Compare two descriptors and explain their differences."""
        exp1 = self.explain(desc1)
        exp2 = self.explain(desc2)

        return f"## {desc1}\n\n{exp1}\n\n---\n\n## {desc2}\n\n{exp2}"

    def _format_from_metadata(self, info: DescriptorInfo) -> str:
        """Format a descriptor explanation from metadata."""
        lines = [
            f"**{info.name}**",
            "",
            info.description,
            "",
            f"**Category:** {info.category}",
            f"**Value Type:** {info.value_type}",
            f"**Typical Range:** {info.typical_range[0]} to {info.typical_range[1]}",
        ]

        if info.unit:
            lines.append(f"**Unit:** {info.unit}")

        return "\n".join(lines)

    def _interpret_value(self, descriptor_name: str, value: float) -> Optional[str]:
        """Generate an interpretation of a descriptor value."""
        interpretations = {
            "MolWt": lambda v: self._interpret_molwt(v),
            "MolLogP": lambda v: self._interpret_logp(v),
            "TPSA": lambda v: self._interpret_tpsa(v),
            "NumHDonors": lambda v: self._interpret_hbd(v),
            "NumHAcceptors": lambda v: self._interpret_hba(v),
            "NumRotatableBonds": lambda v: self._interpret_rotbonds(v),
            "FractionCSP3": lambda v: self._interpret_fsp3(v),
            "qed": lambda v: self._interpret_qed(v),
        }

        if descriptor_name in interpretations:
            return interpretations[descriptor_name](value)
        return None

    def _interpret_molwt(self, value: float) -> str:
        if value < 150:
            return "**Interpretation:** Very small molecule (fragment-like)"
        elif value < 500:
            return "**Interpretation:** Within Lipinski's Rule of Five (≤500 Da)"
        elif value < 800:
            return "**Interpretation:** Above Ro5 limit; may have bioavailability challenges"
        else:
            return "**Interpretation:** Large molecule; likely poor oral bioavailability"

    def _interpret_logp(self, value: float) -> str:
        if value < 0:
            return "**Interpretation:** Hydrophilic; good water solubility expected"
        elif value < 3:
            return "**Interpretation:** Good balance of lipophilicity; ideal for oral drugs"
        elif value < 5:
            return "**Interpretation:** Moderately lipophilic; within Ro5"
        else:
            return "**Interpretation:** Highly lipophilic; violates Ro5; solubility concerns"

    def _interpret_tpsa(self, value: float) -> str:
        if value < 60:
            return "**Interpretation:** Low TPSA; good CNS penetration expected"
        elif value < 90:
            return "**Interpretation:** Moderate TPSA; good intestinal absorption"
        elif value < 140:
            return "**Interpretation:** Higher TPSA; may limit absorption"
        else:
            return "**Interpretation:** High TPSA; poor oral bioavailability expected"

    def _interpret_hbd(self, value: float) -> str:
        if value <= 5:
            return "**Interpretation:** Within Lipinski's Rule (≤5 H-bond donors)"
        else:
            return "**Interpretation:** Exceeds Ro5 limit; may reduce permeability"

    def _interpret_hba(self, value: float) -> str:
        if value <= 10:
            return "**Interpretation:** Within Lipinski's Rule (≤10 H-bond acceptors)"
        else:
            return "**Interpretation:** Exceeds Ro5 limit; may affect bioavailability"

    def _interpret_rotbonds(self, value: float) -> str:
        if value <= 10:
            return "**Interpretation:** Within Veber's Rule (≤10 rotatable bonds)"
        else:
            return "**Interpretation:** High flexibility; may reduce bioavailability"

    def _interpret_fsp3(self, value: float) -> str:
        if value < 0.25:
            return "**Interpretation:** Very flat molecule; mostly aromatic/sp² character"
        elif value < 0.5:
            return "**Interpretation:** Moderate 3D character; typical for drug molecules"
        else:
            return "**Interpretation:** High 3D character; good sp³ content"

    def _interpret_qed(self, value: float) -> str:
        if value > 0.67:
            return "**Interpretation:** High drug-likeness score"
        elif value > 0.33:
            return "**Interpretation:** Moderate drug-likeness"
        else:
            return "**Interpretation:** Low drug-likeness; may need optimization"
