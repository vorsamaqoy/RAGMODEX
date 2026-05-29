"""Registry of all RDKit molecular descriptors with metadata."""

from typing import Optional
from dataclasses import dataclass
from rdkit.Chem import Descriptors


@dataclass
class DescriptorInfo:
    """Information about a molecular descriptor."""

    name: str
    category: str
    description: str
    value_type: str  # "continuous", "integer", "count"
    typical_range: tuple[float, float]
    unit: Optional[str] = None


# Comprehensive descriptor metadata
DESCRIPTOR_METADATA: dict[str, DescriptorInfo] = {
    # Molecular Weight Descriptors
    "MolWt": DescriptorInfo(
        "MolWt", "physicochemical", "Average molecular weight", "continuous",
        (0, 1000), "Da"
    ),
    "ExactMolWt": DescriptorInfo(
        "ExactMolWt", "physicochemical", "Exact molecular weight (most abundant isotope)", "continuous",
        (0, 1000), "Da"
    ),
    "HeavyAtomMolWt": DescriptorInfo(
        "HeavyAtomMolWt", "physicochemical", "Molecular weight of heavy atoms only", "continuous",
        (0, 1000), "Da"
    ),

    # Lipophilicity
    "MolLogP": DescriptorInfo(
        "MolLogP", "lipophilicity", "Wildman-Crippen LogP (octanol-water partition)", "continuous",
        (-5, 10), None
    ),
    "MolMR": DescriptorInfo(
        "MolMR", "lipophilicity", "Wildman-Crippen molar refractivity", "continuous",
        (0, 200), None
    ),

    # Surface Area
    "TPSA": DescriptorInfo(
        "TPSA", "surface_area", "Topological polar surface area", "continuous",
        (0, 300), "Å²"
    ),
    "LabuteASA": DescriptorInfo(
        "LabuteASA", "surface_area", "Labute approximate surface area", "continuous",
        (0, 500), "Å²"
    ),

    # Hydrogen Bonding
    "NumHDonors": DescriptorInfo(
        "NumHDonors", "hbond", "Number of hydrogen bond donors", "count",
        (0, 20), None
    ),
    "NumHAcceptors": DescriptorInfo(
        "NumHAcceptors", "hbond", "Number of hydrogen bond acceptors", "count",
        (0, 20), None
    ),

    # Atom Counts
    "NumHeavyAtoms": DescriptorInfo(
        "NumHeavyAtoms", "counts", "Number of heavy (non-hydrogen) atoms", "count",
        (0, 100), None
    ),
    "NumHeteroatoms": DescriptorInfo(
        "NumHeteroatoms", "counts", "Number of heteroatoms", "count",
        (0, 50), None
    ),
    "NumRotatableBonds": DescriptorInfo(
        "NumRotatableBonds", "counts", "Number of rotatable bonds", "count",
        (0, 30), None
    ),
    "NumRadicalElectrons": DescriptorInfo(
        "NumRadicalElectrons", "counts", "Number of radical electrons", "count",
        (0, 10), None
    ),
    "NumValenceElectrons": DescriptorInfo(
        "NumValenceElectrons", "counts", "Number of valence electrons", "count",
        (0, 500), None
    ),

    # Ring Descriptors
    "RingCount": DescriptorInfo(
        "RingCount", "rings", "Number of rings", "count",
        (0, 20), None
    ),
    "NumAromaticRings": DescriptorInfo(
        "NumAromaticRings", "rings", "Number of aromatic rings", "count",
        (0, 10), None
    ),
    "NumSaturatedRings": DescriptorInfo(
        "NumSaturatedRings", "rings", "Number of saturated rings", "count",
        (0, 10), None
    ),
    "NumAliphaticRings": DescriptorInfo(
        "NumAliphaticRings", "rings", "Number of aliphatic rings", "count",
        (0, 10), None
    ),
    "NumAromaticCarbocycles": DescriptorInfo(
        "NumAromaticCarbocycles", "rings", "Number of aromatic carbocycles", "count",
        (0, 10), None
    ),
    "NumAromaticHeterocycles": DescriptorInfo(
        "NumAromaticHeterocycles", "rings", "Number of aromatic heterocycles", "count",
        (0, 10), None
    ),
    "NumSaturatedCarbocycles": DescriptorInfo(
        "NumSaturatedCarbocycles", "rings", "Number of saturated carbocycles", "count",
        (0, 10), None
    ),
    "NumSaturatedHeterocycles": DescriptorInfo(
        "NumSaturatedHeterocycles", "rings", "Number of saturated heterocycles", "count",
        (0, 10), None
    ),
    "NumAliphaticCarbocycles": DescriptorInfo(
        "NumAliphaticCarbocycles", "rings", "Number of aliphatic carbocycles", "count",
        (0, 10), None
    ),
    "NumAliphaticHeterocycles": DescriptorInfo(
        "NumAliphaticHeterocycles", "rings", "Number of aliphatic heterocycles", "count",
        (0, 10), None
    ),

    # Complexity
    "FractionCSP3": DescriptorInfo(
        "FractionCSP3", "complexity", "Fraction of sp3 hybridized carbons", "continuous",
        (0, 1), None
    ),
    "BertzCT": DescriptorInfo(
        "BertzCT", "complexity", "Bertz complexity index", "continuous",
        (0, 5000), None
    ),

    # Topological Indices
    "BalabanJ": DescriptorInfo(
        "BalabanJ", "topological", "Balaban J index", "continuous",
        (0, 10), None
    ),
    "Chi0": DescriptorInfo(
        "Chi0", "topological", "Chi0 connectivity index (zeroth order)", "continuous",
        (0, 100), None
    ),
    "Chi0n": DescriptorInfo(
        "Chi0n", "topological", "Chi0n connectivity index", "continuous",
        (0, 100), None
    ),
    "Chi0v": DescriptorInfo(
        "Chi0v", "topological", "Chi0v valence connectivity index", "continuous",
        (0, 100), None
    ),
    "Chi1": DescriptorInfo(
        "Chi1", "topological", "Chi1 connectivity index (first order)", "continuous",
        (0, 50), None
    ),
    "Chi1n": DescriptorInfo(
        "Chi1n", "topological", "Chi1n connectivity index", "continuous",
        (0, 50), None
    ),
    "Chi1v": DescriptorInfo(
        "Chi1v", "topological", "Chi1v valence connectivity index", "continuous",
        (0, 50), None
    ),
    "Chi2n": DescriptorInfo(
        "Chi2n", "topological", "Chi2n connectivity index", "continuous",
        (0, 50), None
    ),
    "Chi2v": DescriptorInfo(
        "Chi2v", "topological", "Chi2v valence connectivity index", "continuous",
        (0, 50), None
    ),
    "Chi3n": DescriptorInfo(
        "Chi3n", "topological", "Chi3n connectivity index", "continuous",
        (0, 50), None
    ),
    "Chi3v": DescriptorInfo(
        "Chi3v", "topological", "Chi3v valence connectivity index", "continuous",
        (0, 50), None
    ),
    "Chi4n": DescriptorInfo(
        "Chi4n", "topological", "Chi4n connectivity index", "continuous",
        (0, 50), None
    ),
    "Chi4v": DescriptorInfo(
        "Chi4v", "topological", "Chi4v valence connectivity index", "continuous",
        (0, 50), None
    ),
    "HallKierAlpha": DescriptorInfo(
        "HallKierAlpha", "topological", "Hall-Kier alpha value", "continuous",
        (-5, 5), None
    ),
    "Kappa1": DescriptorInfo(
        "Kappa1", "topological", "Kappa1 shape index", "continuous",
        (0, 50), None
    ),
    "Kappa2": DescriptorInfo(
        "Kappa2", "topological", "Kappa2 shape index", "continuous",
        (0, 50), None
    ),
    "Kappa3": DescriptorInfo(
        "Kappa3", "topological", "Kappa3 shape index", "continuous",
        (0, 50), None
    ),

    # EState Indices
    "MaxEStateIndex": DescriptorInfo(
        "MaxEStateIndex", "estate", "Maximum EState index", "continuous",
        (-5, 20), None
    ),
    "MinEStateIndex": DescriptorInfo(
        "MinEStateIndex", "estate", "Minimum EState index", "continuous",
        (-5, 20), None
    ),
    "MaxAbsEStateIndex": DescriptorInfo(
        "MaxAbsEStateIndex", "estate", "Maximum absolute EState index", "continuous",
        (0, 20), None
    ),
    "MinAbsEStateIndex": DescriptorInfo(
        "MinAbsEStateIndex", "estate", "Minimum absolute EState index", "continuous",
        (0, 20), None
    ),

    # Partial Charge Descriptors
    "MaxPartialCharge": DescriptorInfo(
        "MaxPartialCharge", "charge", "Maximum Gasteiger partial charge", "continuous",
        (-1, 1), None
    ),
    "MinPartialCharge": DescriptorInfo(
        "MinPartialCharge", "charge", "Minimum Gasteiger partial charge", "continuous",
        (-1, 1), None
    ),
    "MaxAbsPartialCharge": DescriptorInfo(
        "MaxAbsPartialCharge", "charge", "Maximum absolute Gasteiger partial charge", "continuous",
        (0, 1), None
    ),
    "MinAbsPartialCharge": DescriptorInfo(
        "MinAbsPartialCharge", "charge", "Minimum absolute Gasteiger partial charge", "continuous",
        (0, 1), None
    ),

    # Molecular Orbital Energies
    "PEOE_VSA1": DescriptorInfo(
        "PEOE_VSA1", "moe", "MOE-type partial charge VSA descriptor 1", "continuous",
        (0, 500), "Å²"
    ),
    "PEOE_VSA2": DescriptorInfo(
        "PEOE_VSA2", "moe", "MOE-type partial charge VSA descriptor 2", "continuous",
        (0, 500), "Å²"
    ),
    "PEOE_VSA3": DescriptorInfo(
        "PEOE_VSA3", "moe", "MOE-type partial charge VSA descriptor 3", "continuous",
        (0, 500), "Å²"
    ),

    # SMR VSA Descriptors
    "SMR_VSA1": DescriptorInfo(
        "SMR_VSA1", "moe", "MOE-type molar refractivity VSA descriptor 1", "continuous",
        (0, 500), "Å²"
    ),
    "SMR_VSA2": DescriptorInfo(
        "SMR_VSA2", "moe", "MOE-type molar refractivity VSA descriptor 2", "continuous",
        (0, 500), "Å²"
    ),
    "SMR_VSA3": DescriptorInfo(
        "SMR_VSA3", "moe", "MOE-type molar refractivity VSA descriptor 3", "continuous",
        (0, 500), "Å²"
    ),

    # SLogP VSA Descriptors
    "SlogP_VSA1": DescriptorInfo(
        "SlogP_VSA1", "moe", "MOE-type LogP VSA descriptor 1", "continuous",
        (0, 500), "Å²"
    ),
    "SlogP_VSA2": DescriptorInfo(
        "SlogP_VSA2", "moe", "MOE-type LogP VSA descriptor 2", "continuous",
        (0, 500), "Å²"
    ),
    "SlogP_VSA3": DescriptorInfo(
        "SlogP_VSA3", "moe", "MOE-type LogP VSA descriptor 3", "continuous",
        (0, 500), "Å²"
    ),

    # QED (drug-likeness)
    "qed": DescriptorInfo(
        "qed", "druglikeness", "Quantitative estimate of drug-likeness", "continuous",
        (0, 1), None
    ),

    # Wildman-Crippen LogP contributions
    "VSA_EState1": DescriptorInfo(
        "VSA_EState1", "estate", "VSA EState descriptor 1", "continuous",
        (0, 100), "Å²"
    ),
}


class DescriptorRegistry:
    """Registry of all available RDKit descriptors."""

    # Get all descriptors from RDKit
    ALL_DESCRIPTORS = [desc[0] for desc in Descriptors.descList]

    @staticmethod
    def get_info(descriptor_name: str) -> Optional[DescriptorInfo]:
        """Get metadata for a descriptor."""
        return DESCRIPTOR_METADATA.get(descriptor_name)

    @staticmethod
    def get_all_names() -> list[str]:
        """Get names of all available descriptors."""
        return DescriptorRegistry.ALL_DESCRIPTORS.copy()

    # DEAD CODE — flagged for removal
    # @staticmethod
    # def get_all_with_metadata() -> dict[str, Optional[DescriptorInfo]]:
    #     """Get all descriptor names with their metadata (if available)."""
    #     return {
    #         name: DESCRIPTOR_METADATA.get(name)
    #         for name in DescriptorRegistry.ALL_DESCRIPTORS
    #     }

    # DEAD CODE — flagged for removal
    # @staticmethod
    # def get_by_category(category: str) -> list[str]:
    #     """Get all descriptors in a specific category."""
    #     return [
    #         name
    #         for name, info in DESCRIPTOR_METADATA.items()
    #         if info.category == category
    #     ]

    # DEAD CODE — flagged for removal
    # @staticmethod
    # def get_categories() -> list[str]:
    #     """Get all unique descriptor categories."""
    #     return list(set(info.category for info in DESCRIPTOR_METADATA.values()))

    @staticmethod
    def search(query: str) -> list[str]:
        """Search descriptors by name or description."""
        query = query.lower()
        results = []

        for name, info in DESCRIPTOR_METADATA.items():
            if query in name.lower() or query in info.description.lower():
                results.append(name)

        # Also search in descriptor names without metadata
        for name in DescriptorRegistry.ALL_DESCRIPTORS:
            if name not in results and query in name.lower():
                results.append(name)

        return results

    @staticmethod
    def is_valid_descriptor(name: str) -> bool:
        """Check if a descriptor name is valid."""
        return name in DescriptorRegistry.ALL_DESCRIPTORS

    @staticmethod
    def get_count() -> int:
        """Get total number of available descriptors."""
        return len(DescriptorRegistry.ALL_DESCRIPTORS)

    @staticmethod
    def get_common_descriptors() -> list[str]:
        """Get list of commonly used descriptors."""
        return [
            "MolWt",
            "MolLogP",
            "TPSA",
            "NumHDonors",
            "NumHAcceptors",
            "NumRotatableBonds",
            "NumHeavyAtoms",
            "NumAromaticRings",
            "FractionCSP3",
            "RingCount",
        ]

    @staticmethod
    def get_lipinski_descriptors() -> list[str]:
        """Get descriptors related to Lipinski's Rule of Five."""
        return ["MolWt", "MolLogP", "NumHDonors", "NumHAcceptors"]

    @staticmethod
    def get_admet_descriptors() -> list[str]:
        """Get descriptors commonly used in ADMET prediction."""
        return [
            "MolWt",
            "MolLogP",
            "TPSA",
            "NumHDonors",
            "NumHAcceptors",
            "NumRotatableBonds",
            "NumHeavyAtoms",
            "NumHeteroatoms",
            "RingCount",
            "FractionCSP3",
        ]
