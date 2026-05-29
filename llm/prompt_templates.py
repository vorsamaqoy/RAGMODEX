"""Prompt templates for LLM interactions."""

from typing import Optional


class PromptTemplates:
    """System prompts and templates for LLM interactions."""

    SYSTEM_PROMPT = """You are a molecular AI assistant embedded in RAGMODEX, a cheminformatics application.
You help researchers interpret molecular descriptors, fingerprints, SHAP values, and bioactivity predictions.

Rules — follow strictly:
- Always respond in English, regardless of the input language.
- Maximum 180 words. No exceptions unless the user explicitly asks for more detail.
- NEVER generate Python, RDKit, or any code. The app handles all computation internally.
- NEVER suggest the user run code or scripts. Never mention RDKit, sklearn, or SHAP library names.
- SMARTS patterns may appear inline in backticks when chemically relevant.
- No filler phrases: no "Let's break down", "In summary", "It's worth noting that", "Great question".
- Be direct and technically precise. No meta-commentary.
- TPSA is 2D-only: never mention 3D embedding or conformer generation."""

    MACCS_EXPLANATION_TEMPLATE = """Explain MACCS key {key_number}.

SMARTS: {smarts}
Description: {description}
Category: {category}

In ≤ 120 words: what chemical feature it detects, which functional groups match, and its relevance in drug-likeness or bioactivity. No code."""

    ECFP_EXPLANATION_TEMPLATE = """Explain ECFP6 bit {bit_index} for this molecule.

SMILES: {smiles}
Type: {fp_type} (radius={radius}, nbits={n_bits})

{bit_info}

In ≤ 100 words: what atomic environment sets this bit and its chemical significance. No code."""

    MOLECULE_PREDICTION_SYSTEM_PROMPT = """You are a molecular bioactivity interpreter inside RAGMODEX.

Hard rules:
1. Use ONLY the provided SHAP and prediction data — never hallucinate.
2. ECFP6 = diameter 6 = radius 3. Never say "radius 6".
3. Structure: 2–3 sentence summary of the prediction, then comment on the TOP 3 bits by |SHAP| only. For each bit: one sentence naming the substructure, one sentence on why the SHAP sign pushes toward active or inactive. End with: "Further bits are visible in the side panel."
3a. If the user asks to "report" prediction results, include the exact canonical SMILES, predicted class, P(active), P(inactive), and the exact top-3 ECFP6 bit IDs with their SHAP values from the provided data.
4. SHAP sign rules — never invert:
   · bit ON,  SHAP > 0 → substructure promotes activity
   · bit ON,  SHAP < 0 → substructure suppresses activity
   · bit OFF, SHAP > 0 → absence of this feature mildly hurts activity
   · bit OFF, SHAP < 0 → absence is consistent with inactivity
5. Hash collision (ambiguous bit) → one phrase only: "mixed signal — multiple substructures share this bit."
6. NEVER generate code. NEVER mention library names.
7. Always respond in English. Do not expose hidden reasoning or <think> text.
8. Maximum 180 words."""

    MOLECULE_PREDICTION_TEMPLATE = """--- PREDICTION DATA ---
{context}

--- USER QUERY ---
{user_query}

Follow the system rules. Preserve exact numeric values and ECFP6 bit IDs from the prediction data. Never replace ECFP6 bit IDs with invented SMARTS patterns. Maximum 180 words."""

    ECFP_BIT_GROUNDED_SYSTEM_PROMPT = """You are a fingerprint interpretation assistant inside RAGMODEX.

Rules:
1. ECFP6 = diameter 6 = radius 3. Never say "radius 6".
2. Use ONLY the provided bit database data — no prior knowledge.
3. Maximum 120 words.
4. If the bit maps to multiple substructures, flag it as a mixed signal and name only the dominant one.
5. NEVER generate code. Always respond in English."""

    ECFP_BIT_QUERY_TEMPLATE = """--- BIT DATABASE DATA ---
{bit_context}

--- USER QUERY ---
{user_query}

Answer using only the data above. Maximum 120 words. No code."""

    ECFP_BIT_SHAP_COLLISION_TEMPLATE = """Interpret this ECFP6 bit SHAP value.

{collision_context}
Training set size: {n_molecules} molecules.

In ≤ 150 words:
1. What SHAP = {shap_value:+.4f} means (direction + magnitude).
2. The most likely substructure driving it, from the training data above.
3. If the bit is ambiguous: one sentence flagging it as a mixed signal.
No code. Always respond in English."""

    DESCRIPTOR_EXPLANATION_TEMPLATE = """Explain the molecular descriptor "{descriptor_name}" in ≤ 120 words.

Cover: what it measures, typical range, relevance to drug discovery. No code.
IMPORTANT: TPSA is calculated from 2D topology only — never mention 3D embedding, conformer generation, or EmbedMolecule."""

    DESCRIPTOR_WITH_VALUE_TEMPLATE = """Interpret descriptor "{descriptor_name}" for this molecule.

SMILES: {smiles}
Value: {value}

In ≤ 100 words: what the value means, whether it is high/low/typical, and any practical implication. No code.
IMPORTANT: TPSA is calculated from 2D topology only — never mention 3D embedding, conformer generation, or EmbedMolecule."""

    MOLECULAR_ANALYSIS_TEMPLATE = """Summarize the key structural features of this molecule in ≤ 150 words.

SMILES: {smiles}
Formula: {formula}  MW: {mol_weight:.2f} Da

Focus on notable functional groups and structural motifs. No code."""

    RAG_CONTEXT_TEMPLATE = """Use the context below to answer the question. If not relevant, answer from chemistry knowledge.

Context:
{context}

Question: {question}

Maximum 150 words. No code."""

    @staticmethod
    def format_maccs_prompt(key_number: int, smarts: str, description: str, category: str) -> str:
        return PromptTemplates.MACCS_EXPLANATION_TEMPLATE.format(
            key_number=key_number,
            smarts=smarts,
            description=description,
            category=category,
        )

    @staticmethod
    def format_ecfp_prompt(
        smiles: str,
        bit_index: int,
        bit_info: str,
        fp_type: str = "ECFP",
        radius: int = 2,
        n_bits: int = 2048,
    ) -> str:
        return PromptTemplates.ECFP_EXPLANATION_TEMPLATE.format(
            smiles=smiles,
            bit_index=bit_index,
            bit_info=bit_info,
            fp_type=fp_type,
            radius=radius,
            n_bits=n_bits,
        )

    @staticmethod
    def format_descriptor_prompt(descriptor_name: str) -> str:
        return PromptTemplates.DESCRIPTOR_EXPLANATION_TEMPLATE.format(
            descriptor_name=descriptor_name
        )

    @staticmethod
    def format_descriptor_with_value_prompt(
        descriptor_name: str, smiles: str, value: float
    ) -> str:
        return PromptTemplates.DESCRIPTOR_WITH_VALUE_TEMPLATE.format(
            descriptor_name=descriptor_name,
            smiles=smiles,
            value=value,
        )

    @staticmethod
    def format_analysis_prompt(
        smiles: str,
        canonical_smiles: str,
        formula: str,
        mol_weight: float,
    ) -> str:
        return PromptTemplates.MOLECULAR_ANALYSIS_TEMPLATE.format(
            smiles=smiles,
            formula=formula,
            mol_weight=mol_weight,
        )

    @staticmethod
    def format_rag_prompt(context: str, question: str) -> str:
        return PromptTemplates.RAG_CONTEXT_TEMPLATE.format(
            context=context,
            question=question,
        )

    @staticmethod
    def format_molecule_prediction_prompt(context: str, user_query: str) -> str:
        return PromptTemplates.MOLECULE_PREDICTION_TEMPLATE.format(
            context=context,
            user_query=user_query,
        )

    @staticmethod
    def format_ecfp_bit_query_prompt(bit_context: str, user_query: str) -> str:
        return PromptTemplates.ECFP_BIT_QUERY_TEMPLATE.format(
            bit_context=bit_context,
            user_query=user_query,
        )

    @staticmethod
    def format_ecfp_bit_shap_prompt(
        bit_index: int,
        shap_value: float,
        n_molecules: int,
        collision_context: str,
    ) -> str:
        return PromptTemplates.ECFP_BIT_SHAP_COLLISION_TEMPLATE.format(
            bit_index=bit_index,
            shap_value=shap_value,
            n_molecules=n_molecules,
            collision_context=collision_context,
        )
