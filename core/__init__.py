"""Core module for molecular operations."""

from .molecule_parser import MoleculeParser
from .descriptor_calculator import DescriptorCalculator
from .fingerprint_engine import FingerprintEngine
from .substructure_highlighter import SubstructureHighlighter
from .bit_database import (
    build_bit_database,
    get_molecule_bit_info,
    get_bit_context,
    format_bit_context_for_llm,
)
from .model_pipeline import (
    load_model,
    create_explainer,
    predict_and_interpret,
    format_interpretation_context,
)
from .aggregate_stats import build_aggregate_stats, select_aggregate_context
from .applicability_domain import (
    build_ad_model,
    check_applicability_domain,
    format_ad_context,
)
from .comparison_pipeline import compare_molecules, format_comparison_context
from .suggestion_pipeline import (
    suggest_modifications,
    format_suggestions_context,
    search_substructure_activity,
    format_substructure_context,
)
from .molecular_editor import apply_edit_rdkit, format_edit_context
from .query_router import classify_query, extract_smiles, detect_two_smiles

__all__ = [
    "MoleculeParser",
    "DescriptorCalculator",
    "FingerprintEngine",
    "SubstructureHighlighter",
    "build_bit_database",
    "get_molecule_bit_info",
    "get_bit_context",
    "format_bit_context_for_llm",
    "load_model",
    "create_explainer",
    "predict_and_interpret",
    "format_interpretation_context",
    "build_aggregate_stats",
    "select_aggregate_context",
    "build_ad_model",
    "check_applicability_domain",
    "format_ad_context",
    "compare_molecules",
    "format_comparison_context",
    "suggest_modifications",
    "format_suggestions_context",
    "search_substructure_activity",
    "format_substructure_context",
    "apply_edit_rdkit",
    "format_edit_context",
    "classify_query",
    "extract_smiles",
    "detect_two_smiles",
]
