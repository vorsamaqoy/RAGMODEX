"""Chat endpoint with SSE streaming."""

from __future__ import annotations

import json
import re
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.state import app_state

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    use_rag: bool = True
    smiles_context: str | None = None


class PipelineChatRequest(ChatRequest):
    smiles: str
    top_n: int = 10


def _get_handler():
    if app_state.chat_handler is None:
        from llm.chat_handler import ChatHandler
        handler = ChatHandler(
            provider=app_state.llm_provider,
            model=app_state.llm_model,
        )
        handler.set_temperature(app_state.temperature)
        app_state.chat_handler = handler
    return app_state.chat_handler


def _friendly_llm_error(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    return (
        "LLM request failed. Check the provider API key, model name, and network "
        f"connectivity. Provider={app_state.llm_provider}, model={app_state.llm_model}. "
        f"Details: {message}"
    )


_RAG_MIN_SCORE = 0.30  # cosine similarity threshold — chunks below this are not injected


def _retrieve_context(message: str) -> str | None:
    if app_state.retriever is None:
        return None
    try:
        result = app_state.retriever.retrieve(message)
        relevant = [sr for sr in result.search_results if sr.score >= _RAG_MIN_SCORE]
        if not relevant:
            return None
        parts = []
        for i, sr in enumerate(relevant, 1):
            parts.append(f"[{i}] (source: {sr.chunk.source})\n{sr.chunk.text}")
        return "\n\n".join(parts)
    except Exception:
        return None


SMILES_BLOCKLIST = {
    "active", "inactive", "smiles", "model", "dataset", "prediction", "probability",
    "describe", "how", "what", "which", "loaded", "training", "test", "molecules",
    "molecule", "fingerprint", "configuration", "radius", "number", "bits", "bbb",
    "cyp", "ecfp", "ecfp6", "maccs", "shap",
}


def _clean_smiles_candidate(value: str | None) -> str:
    return (value or "").strip().strip("`'\" \t\r\n,;:.?!")


def _is_probable_smiles(value: str | None) -> bool:
    token = _clean_smiles_candidate(value)
    if len(token) < 2 or re.search(r"\s", token):
        return False
    if token.lower() in SMILES_BLOCKLIST:
        return False
    if not re.fullmatch(r"[A-Za-z0-9@+\-\[\]\\/#%().=]+", token):
        return False

    has_structure_marker = bool(re.search(r"[\[\]\(\)=#@+\-\\/%.0-9]", token))
    if has_structure_marker:
        return bool(re.search(r"[BCNOFPSIbccnops]", token))

    # Plain alphabetic SMILES such as CCO are valid, but ordinary words like
    # "Describe" or "How" must not enter the prediction path.
    i = 0
    allowed_two = {"Cl", "Br"}
    allowed_one = set("BCNOFPSIbcopsn")
    while i < len(token):
        two = token[i:i + 2]
        if two in allowed_two:
            i += 2
            continue
        if token[i] in allowed_one:
            i += 1
            continue
        return False
    return True


def _extract_smiles(message: str) -> str | None:
    text = message.strip()
    patterns = [
        r"\bfor\s+molecule\s+[\"']?([A-Za-z0-9@+\-\[\]\\/#%().=]{3,})[\"']?\s*[,.;:]?",
        r"\bmolecule\s+[\"']?([A-Za-z0-9@+\-\[\]\\/#%().=]{3,})[\"']?\s*[,.;:]?",
        r"\bsubstructure\s+in\s+[\"']?([A-Za-z0-9@+\-\[\]\\/#%().=]{3,})[\"']?\s+from\b",
        r"\bin\s+[\"']?([A-Za-z0-9@+\-\[\]\\/#%().=]{3,})[\"']?\s+from\b",
        r"\bSMILES\s*[:=]\s*[\"']?([A-Za-z0-9@+\-\[\]\\/#%().=]{3,})[\"']?",
        r"^(?:predict|analyze|analyse|interpret|spiega|predici)\s+[\"']([^\"']{3,})[\"']",
        r"^(?:predict|analyze|analyse|interpret|explain|score|evaluate|spiega|predici)\s+([A-Za-z0-9@+\-\[\]\\/#%().=]{3,})",
        r"[\"']([A-Za-z0-9@+\-\[\]\\/#%().=]{3,})[\"']",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = _clean_smiles_candidate(match.group(1))
            if _is_probable_smiles(candidate):
                return candidate
    return None


def _resolve_smiles_context(smiles_context: str | None, message: str) -> str | None:
    if _is_probable_smiles(smiles_context):
        return _clean_smiles_candidate(smiles_context)
    return _extract_smiles(message)


def _extract_signed_bit_index(message: str) -> int | None:
    match = re.search(
        r"\b(?:ECFP\d*\s*)?bit\s*[_:-]?\s*(-?\d{1,5})\b",
        message,
        flags=re.IGNORECASE,
    )
    if match:
        return int(match.group(1))
    return None


def _unsupported_fact_response(message: str) -> str | None:
    lowered = message.lower()
    unsupported_patterns = [
        ("ic50", "experimental IC50 values are not available in the loaded binary QSAR session unless explicitly present in the indexed retrieval corpus"),
        ("ki value", "Ki values and assay conditions are not available in the loaded session"),
        ("assay temperature", "assay temperatures are not available in the loaded session"),
        ("docking score", "docking was not computed by this RAGMODEX pipeline"),
        ("pdb pose", "PDB pose identifiers are not available in the loaded session"),
        ("pubmed", "PubMed evidence is not available unless it is explicitly present in the indexed retrieval corpus"),
        ("patent", "patent data are not available in the loaded session or retrieval corpus"),
        ("hepatotoxic", "no hepatotoxicity model or endpoint is loaded"),
        ("bbb", "BBB permeability is not modeled in the loaded session"),
        ("cyp", "CYP inhibition is not modeled in the loaded session"),
        ("clinical development", "clinical-development metadata are not available in the loaded session"),
        ("measured aqueous solubility", "measured solubility values are not available in the loaded session"),
        ("crystal structure", "co-crystal structure data are not available in the loaded session"),
        ("allosteric site", "binding-site or allosteric-site data are not available in the loaded session"),
        ("uploaded papers", "the currently indexed corpus does not provide paper-derived IC50 rankings"),
    ]
    for token, reason in unsupported_patterns:
        if token in lowered:
            return (
                f"Unsupported request: {reason}. RAGMODEX can report the loaded QSAR "
                "prediction, SHAP/ECFP interpretation, applicability-domain metrics, "
                "and descriptor values available in the current pipeline, but it should "
                "not invent external experimental or ADMET values."
            )

    if "causally guarantee" in lowered or "causal guarantee" in lowered:
        return (
            "No. A dominant ECFP bit substructure or a positive SHAP contribution does "
            "not causally guarantee GLUT-1 activity. Folded ECFP bits and SHAP values "
            "describe model associations in the loaded training set, not experimental "
            "causal mechanisms; activity still depends on the full molecular context "
            "and requires experimental validation."
        )
    return None


def _descriptor_guard_response(message: str) -> str | None:
    lowered = message.lower()
    if "descriptor" not in lowered and "dragon_" not in lowered:
        return None

    names = re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", message)
    requested = [name for name in names if "_" in name or name.lower().startswith("dragon")]
    if not requested:
        return None

    from descriptors.descriptor_registry import DescriptorRegistry

    invalid = [name for name in requested if not DescriptorRegistry.is_valid_descriptor(name)]
    if invalid:
        return (
            f"Unsupported descriptor: {', '.join(invalid)} is not available in the "
            "RAGMODEX/RDKit descriptor registry. No numeric value or activity "
            "relationship should be inferred for an unsupported descriptor."
        )
    return None


def _maccs_response(message: str) -> str | None:
    match = re.search(r"\bMACCS\s+key\s+(-?\d{1,4})\b", message, flags=re.IGNORECASE)
    if not match:
        return None
    key = int(match.group(1))
    if key == 0:
        return "MACCS key 0 is conventionally unused in the standard 166-key MACCS set and should not be assigned a chemical meaning."
    if key < 1 or key > 166:
        return "Invalid MACCS key: standard MACCS keys are indexed from 1 to 166; no chemical meaning should be assigned to this key."
    return None


def _bit_confidence_text(info: dict) -> str:
    n_unique = int(info.get("n_unique_substructures", 0))
    dominance = float(info.get("dominance", 0.0))
    if n_unique <= 1:
        return "high: one observed substructure in this training set"
    if dominance > 80:
        return "high: one dominant substructure despite hash collisions"
    if dominance > 50:
        return "moderate: one substructure covers more than half of observations"
    return "low: multiple substructures contribute with no dominant mapping"


def _sorted_substructures(info: dict, limit: int = 5) -> list[tuple[str, int]]:
    return sorted(
        ((str(smi), int(count)) for smi, count in dict(info.get("substructures", {})).items()),
        key=lambda item: item[1],
        reverse=True,
    )[:limit]


def _format_substructure_list(info: dict, limit: int = 5) -> str:
    total = max(int(info.get("total_activations", 0)), 1)
    parts = []
    for smi, count in _sorted_substructures(info, limit):
        pct = count / total * 100.0
        parts.append(f"{smi} ({count}, {_fmt_pct(pct)})")
    return "; ".join(parts) if parts else "none"


def _format_bit_database_response(bit_index: int) -> str:
    if bit_index < 0:
        return "Invalid ECFP bit index: negative bit indices are not valid."
    if bit_index >= app_state.fp_nbits:
        return (
            f"Invalid ECFP bit index: valid indices for this session are "
            f"0-{app_state.fp_nbits - 1}; ECFP{2 * app_state.fp_radius}_{bit_index} "
            "should not be assigned a substructure."
        )
    if not app_state.bit_db:
        return "Bit database is not available; load training data before interpreting ECFP bits."

    info = app_state.bit_db.get(bit_index)
    if not info:
        return (
            f"ECFP{2 * app_state.fp_radius}_{bit_index} was not observed in the loaded "
            "training-set bit database; no reliable substructure interpretation is available."
        )

    total = int(info.get("total_activations", 0))
    active = int(info.get("active_freq", 0))
    inactive = int(info.get("inactive_freq", 0))
    n_unique = int(info.get("n_unique_substructures", 0))
    dominance = float(info.get("dominance", 0.0))
    active_ratio = float(info.get("active_ratio", 0.0))
    dominant = info.get("dominant_substructure") or "n/a"
    confidence = _bit_confidence_text(info)
    sub_text = _format_substructure_list(info, 5)
    return (
        f"ECFP{2 * app_state.fp_radius}_{bit_index} was observed {total} times in the "
        f"loaded training set: {active} activations occur in Active molecules and "
        f"{inactive} in Inactive molecules, giving an active ratio of {_fmt_ratio(active_ratio)}. "
        f"The folded bit is associated with {n_unique} unique observed substructures. "
        f"The dominant environment is {dominant}, which accounts for {_fmt_pct(dominance)} "
        f"of activations, so the collision confidence is {confidence}. "
        f"The top observed substructures are {sub_text}."
    )


def _molecule_bit_response(smiles: str, bit_index: int) -> str | None:
    if bit_index < 0 or bit_index >= app_state.fp_nbits:
        return _format_bit_database_response(bit_index)
    try:
        result = _run_prediction_pipeline(smiles, top_n=30)
    except HTTPException as exc:
        return f"Invalid SMILES: {smiles}. {exc.detail}"

    bit = None
    for item in result.get("top_bits", []):
        if int(item.get("bit_index", -1)) == bit_index:
            bit = item
            break
    if bit is None:
        shap_vals = result.get("shap_values_all")
        fp_array = result.get("fp_array")
        bit_on = int(fp_array[bit_index]) if fp_array is not None else 0
        bit = {
            "bit": f"ECFP{2 * app_state.fp_radius}_{bit_index}",
            "bit_index": bit_index,
            "shap_value": float(shap_vals[bit_index]) if shap_vals is not None else 0.0,
            "direction": "-> Active" if shap_vals is not None and float(shap_vals[bit_index]) > 0 else "-> Inactive",
            "bit_on": bit_on,
            "molecule_substructures": [],
        }
        for active in result.get("active_bits", []):
            if int(active.get("bit_index", -1)) == bit_index:
                bit["molecule_substructures"] = active.get("molecule_substructures", [])
                break

    subs = ", ".join(sub["smiles"] for sub in bit.get("molecule_substructures", [])) or "none"
    info = app_state.bit_db.get(bit_index) if app_state.bit_db else None
    training_note = ""
    if info:
        training_note = (
            f" For context, the same folded bit has "
            f"{int(info.get('n_unique_substructures', 0))} observed training-set "
            f"substructures; the dominant one is {info.get('dominant_substructure') or 'n/a'} "
            f"with {_fmt_pct(float(info.get('dominance', 0.0)))} dominance."
        )
    on_text = "ON" if int(bit["bit_on"]) == 1 else "OFF"
    if int(bit["bit_on"]) == 1:
        first = (
            f"Yes. {bit['bit']} is ON in {result['canonical_smiles']}; the molecule-level "
            f"environment that activates it is {subs}."
        )
    else:
        first = (
            f"No. {bit['bit']} is OFF in {result['canonical_smiles']}; no molecule-level "
            "substructure activates this folded bit in the query molecule."
        )
    return (
        f"{first} Its SHAP contribution is {_fmt_shap(float(bit['shap_value']))}, "
        f"so in this prediction it points {_direction_from_shap(float(bit['shap_value']))} "
        f"while the bit state is {on_text}.{training_note}"
    )


def _dataset_context_response(message: str) -> str | None:
    lowered = message.lower()
    if not any(
        token in lowered
        for token in (
            "loaded model", "training set", "test set", "roc-auc", "pr-auc",
            "confusion matrix", "probability threshold", "applicability domain",
            "knn distance", "observed ecfp6 bits", "ambiguous", "descriptor calculator",
            "maccs keys", "regenerate the benchmark", "bit database",
            "llm provider", "retrieval corpus", "chunk size", "redistributed",
        )
    ):
        return None

    if (
        "fingerprint configuration" in lowered
        or "fingerprint type" in lowered
        or (
            "loaded model" in lowered
            and any(token in lowered for token in ("describe", "configuration", "model name", "fingerprint"))
            and not any(token in lowered for token in ("roc-auc", "pr-auc", "auc", "metric", "obtain", "performance"))
        )
    ):
        return (
            f"The loaded predictive model is `{app_state.model_name}`. It uses Morgan/ECFP "
            f"fingerprints with radius {app_state.fp_radius}, which corresponds to ECFP"
            f"{2 * app_state.fp_radius}, folded into {app_state.fp_nbits} bits."
        )

    if "training set and test set" in lowered:
        return (
            f"The loaded dataset contains {len(app_state.training_smiles)} molecules in the "
            f"training set and {len(app_state.test_smiles)} molecules in the test set."
        )

    if "active and inactive" in lowered and "training" in lowered:
        if app_state.training_labels is None:
            return "Training labels are not loaded."
        active = int(app_state.training_labels.sum())
        inactive = int((app_state.training_labels == 0).sum())
        return (
            f"In the training set, {active} molecules are labelled Active and {inactive} "
            "are labelled Inactive."
        )

    if "active and inactive" in lowered and "test" in lowered:
        if app_state.test_labels is None:
            return "Test labels are not loaded."
        active = int(app_state.test_labels.sum())
        inactive = int((app_state.test_labels == 0).sum())
        return (
            f"In the test set, {active} molecules are labelled Active and {inactive} "
            "are labelled Inactive."
        )

    if "roc-auc" in lowered or "pr-auc" in lowered:
        if not app_state.has_test_data():
            return "Test data are not loaded, so ROC-AUC and PR-AUC cannot be computed."
        from sklearn.metrics import average_precision_score, roc_auc_score
        probs = app_state.model.predict_proba(app_state.test_fps)[:, 1]
        roc = roc_auc_score(app_state.test_labels, probs)
        pr = average_precision_score(app_state.test_labels, probs)
        return (
            f"On the loaded test set, the model reaches ROC-AUC {_fmt_ratio(roc)} and "
            f"PR-AUC {_fmt_ratio(pr)}. ROC-AUC summarizes ranking across both classes, while "
            "PR-AUC is especially informative for the Active class when the classes are imbalanced."
        )

    if "confusion matrix" in lowered:
        if not app_state.has_test_data():
            return "Test data are not loaded, so the confusion matrix cannot be computed."
        from sklearn.metrics import confusion_matrix
        probs = app_state.model.predict_proba(app_state.test_fps)[:, 1]
        pred = (probs > 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(app_state.test_labels, pred, labels=[0, 1]).ravel()
        return (
            "Using the default 0.5 probability threshold on the test set, the confusion "
            f"matrix is: {int(tn)} true negatives, {int(fp)} false positives, "
            f"{int(fn)} false negatives, and {int(tp)} true positives."
        )

    if "probability threshold" in lowered:
        return "The default decision threshold is 0.5 on P(active): molecules above this value are classified as Active, and those below it as Inactive."

    if "applicability domain threshold" in lowered or "knn distance" in lowered:
        if not app_state.has_training_data():
            return "Training fingerprints are not loaded, so AD statistics cannot be computed."
        from core.applicability_domain import build_ad_model
        _, threshold, train_mean, train_std = build_ad_model(app_state.training_fps)
        if "mean" in lowered and "standard deviation" in lowered:
            return (
                f"In the training-set applicability-domain model, the mean kNN Jaccard "
                f"distance is {_fmt_distance(train_mean)} and the standard deviation is {_fmt_distance(train_std)}."
            )
        return (
            "The applicability-domain check uses k-nearest neighbours with Jaccard "
            "distance on the ECFP fingerprints. The number of neighbours is "
            f"min(5, n_train), and the current out-of-domain threshold is "
            f"mean + 2 standard deviations of the training distances: {_fmt_distance(threshold)}."
        )

    if "observed ecfp6 bits" in lowered or "unambiguous" in lowered or "ambiguous" in lowered:
        from core.aggregate_stats import build_aggregate_stats
        stats = build_aggregate_stats(app_state.bit_db)
        cs = stats["collision_stats"]
        if "fraction" in lowered or "rate" in lowered:
            return (
                f"{_fmt_pct(cs['ambiguity_rate'])} of the observed folded ECFP6 bits are "
                "ambiguous in the loaded training bit database, meaning that more than "
                "one distinct atom environment mapped to the same bit."
            )
        if "unambiguous" in lowered or "highly ambiguous" in lowered:
            return (
                f"The loaded bit database contains {cs['unambiguous']} unambiguous bits, "
                f"{cs['ambiguous']} ambiguous bits, and {cs['highly_ambiguous']} highly "
                "ambiguous bits with at least five distinct mapped substructures."
            )
        return f"The loaded training-set bit database contains {cs['total_bits']} observed ECFP6 bits."

    if "descriptor calculator" in lowered:
        from core.descriptor_calculator import DescriptorCalculator
        common = [
            "MolWt", "ExactMolWt", "LogP", "MR", "TPSA", "LabuteASA",
            "NumHDonors", "NumHAcceptors", "NumRotatableBonds",
            "NumHeteroatoms", "NumAromaticRings", "RingCount",
            "FractionCSP3", "NumHeavyAtoms",
        ]
        return "Common physicochemical descriptors include: " + ", ".join(common) + f". Total RDKit descriptors available: {len(DescriptorCalculator.ALL_DESCRIPTORS)}."

    if "maccs keys" in lowered and "predictive model" in lowered:
        return "The saved predictive model uses ECFP fingerprints; MACCS keys are used for visualization/exploration, not for numeric prediction in this saved model pipeline."

    if "regenerate the benchmark" in lowered:
        return (
            "To regenerate the benchmark, keep the saved session artifacts together: "
            "`data/session/meta.json`, `model.bin`, `training.npz`, `test.npz`, "
            "`bit_db.pkl`, plus the benchmark question CSV and the ground-truth notebook."
        )

    if "bit database" in lowered:
        return (
            "The bit database is the training-set map used to interpret folded ECFP bits. "
            "For each observed bit it stores activation counts, Active/Inactive frequencies, "
            "active ratio, the mapped atom environments, the dominant substructure, and "
            "collision statistics such as dominance and number of unique substructures."
        )

    if "llm provider" in lowered:
        return "No. Changing the LLM provider affects generated language only; QSAR probabilities, SHAP values, and AD metrics are computed by the saved local model/session pipeline."

    if "retrieval corpus" in lowered:
        from config.settings import settings
        import json
        chunks_path = settings.rag_index_dir / "chunks.json"
        metadata_path = settings.rag_index_dir / "metadata.json"
        chunks = json.loads(chunks_path.read_text(encoding="utf-8")) if chunks_path.exists() else []
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        if "chunk size" in lowered or "chunk overlap" in lowered or "embedding model" in lowered:
            return (
                f"The retrieval corpus is chunked with size {settings.chunk_size} and "
                f"overlap {settings.chunk_overlap}. Embeddings use "
                f"`{metadata.get('embedding_model', settings.embedding_model)}`, and "
                f"retrieval returns the top {settings.top_k_results} chunks by default."
            )
        if "redistributed" in lowered or "update policy" in lowered:
            return "The benchmark corpus should be frozen for reported runs; redistribute only project documentation/generated manifests unless external document redistribution rights are available."
        present = "is present" if chunks_path.exists() else "is not present"
        return (
            f"The current retrieval corpus contains {metadata.get('num_chunks', len(chunks))} "
            f"chunks, and the stored chunks file {present}."
        )

    return None


def _compare_guard_response(message: str) -> str | None:
    lowered = message.lower()
    if "compare" not in lowered:
        return None
    if "with nothing" in lowered or " and nothing" in lowered:
        return "Cannot compare molecules: two valid SMILES strings are required; delta P(active) should not be invented."
    if "not-a-smiles" in lowered:
        return "Cannot compare molecules: not-a-smiles is invalid, so Tanimoto similarity and delta P(active) are undefined."
    return None


SMILES_TOKEN_PATTERN = r"[A-Za-z0-9@+\-\[\]\\/#%().=]+"


def _clean_token(value: str) -> str:
    return value.strip().strip(",:;.?!")


def _parse_two_smiles(message: str) -> tuple[str, str] | None:
    patterns = [
        rf"\bCompare\s+({SMILES_TOKEN_PATTERN})\s+and\s+({SMILES_TOKEN_PATTERN})",
        rf"\bWhich\s+of\s+({SMILES_TOKEN_PATTERN})\s+and\s+({SMILES_TOKEN_PATTERN})",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return _clean_token(match.group(1)), _clean_token(match.group(2))
    return None


def _direction_from_shap(value: float) -> str:
    return "toward Active" if value > 0 else "toward Inactive"


def _fmt_prob(value: float) -> str:
    return f"{float(value):.3f}"


def _fmt_signed_prob(value: float) -> str:
    return f"{float(value):+.3f}"


def _fmt_shap(value: float) -> str:
    return f"{float(value):+.4f}"


def _fmt_ratio(value: float) -> str:
    return f"{float(value):.3f}"


def _fmt_distance(value: float) -> str:
    return f"{float(value):.3f}"


def _fmt_pct(value: float) -> str:
    return f"{float(value):.1f}%"


def _bits_text(bits: list[dict], n: int) -> str:
    parts = []
    for bit in bits[:n]:
        shap = float(bit["shap_value"])
        parts.append(
            f"{bit['bit']} ({_fmt_shap(shap)}, {_direction_from_shap(shap)}, bit {'ON' if int(bit['bit_on']) else 'OFF'})"
        )
    return "; ".join(parts)


def _structured_prediction_report(smiles: str, top_n: int = 3) -> str:
    try:
        result = _run_prediction_pipeline(smiles, top_n=max(top_n, 10))
    except HTTPException as exc:
        return f"Invalid SMILES: {smiles}. No P(active), P(inactive), or SHAP bits should be reported. Details: {exc.detail}"
    p_active = float(result["probability_active"])
    confidence = "high" if p_active >= 0.70 or p_active <= 0.30 else "borderline"
    bits = _bits_text(result.get("top_bits", []), top_n)
    return (
        f"This molecule is classified as {result['prediction']} with {confidence} model support. "
        f"The model assigns P(active) {_fmt_prob(p_active)} and P(inactive) "
        f"{_fmt_prob(result['probability_inactive'])}; the canonical SMILES is "
        f"{result['canonical_smiles']}. The {top_n} strongest ECFP{2 * result['radius']} "
        f"SHAP drivers are {bits}. Positive SHAP values move the score toward Active, "
        "whereas negative values move it toward Inactive."
    )


def _is_prediction_request(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "predict",
            "prediction",
            "predici",
            "classify",
            "classification",
            "score",
            "p(active)",
            "p active",
            "p(inactive)",
            "p inactive",
            "probability",
            "probabilita",
            "probabilità",
            "activity",
            "attivita",
            "attività",
            "shap",
            "explain",
            "spiega",
        )
    )


def _applicability_domain_report(smiles: str) -> str:
    if not app_state.has_training_data():
        return "Training fingerprints are not loaded, so applicability-domain metrics cannot be computed."
    from core.applicability_domain import build_ad_model, check_applicability_domain
    try:
        ad_tuple = build_ad_model(app_state.training_fps)
        result = check_applicability_domain(
            smiles,
            ad_tuple,
            app_state.model,
            app_state.explainer,
            app_state.bit_db,
            app_state.fp_radius,
            app_state.fp_nbits,
        )
    except Exception as exc:
        return f"Applicability-domain calculation failed: {exc}"
    if "error" in result:
        return f"Invalid SMILES: {smiles}. {result['error']}"
    pred = result.get("prediction", {})
    return (
        f"The molecule is {'inside' if result.get('inside_ad') else 'outside'} the applicability domain "
        f"({result.get('ad_confidence')}). Its mean kNN Jaccard distance is "
        f"{_fmt_distance(float(result.get('mean_knn_distance')))} versus the AD threshold "
        f"{_fmt_distance(float(result.get('ad_threshold')))}. Training distance reference: "
        f"mean={_fmt_distance(float(result.get('train_mean_dist')))}, std={_fmt_distance(float(result.get('train_std_dist')))}. "
        f"The loaded QSAR model gives P(active) {_fmt_prob(float(pred.get('probability_active')))}."
    )


def _pair_ad_report(smi1: str, smi2: str) -> str:
    from core.applicability_domain import build_ad_model, check_applicability_domain
    ad_tuple = build_ad_model(app_state.training_fps)
    r1 = check_applicability_domain(smi1, ad_tuple, app_state.model, app_state.explainer, app_state.bit_db, app_state.fp_radius, app_state.fp_nbits)
    r2 = check_applicability_domain(smi2, ad_tuple, app_state.model, app_state.explainer, app_state.bit_db, app_state.fp_radius, app_state.fp_nbits)
    if "error" in r1:
        return f"First molecule is invalid: {r1['error']}"
    if "error" in r2:
        return f"Second molecule is invalid: {r2['error']}"
    closer = "first molecule" if r1["mean_knn_distance"] <= r2["mean_knn_distance"] else "second molecule"
    return (
        f"The {closer} is closer to the training set in the applicability-domain space. "
        f"Its mean kNN Jaccard distance is {_fmt_distance(r1['mean_knn_distance'])} for molecule 1 "
        f"versus {_fmt_distance(r2['mean_knn_distance'])} for molecule 2; the current out-of-domain "
        f"threshold is {_fmt_distance(r1['ad_threshold'])}."
    )


def _comparison_report(message: str) -> str | None:
    pair = _parse_two_smiles(message)
    if not pair:
        return None
    smi1, smi2 = pair
    lowered = message.lower()
    if "structurally closer" in lowered or "closer to the training set" in lowered:
        return _pair_ad_report(smi1, smi2)

    from core.comparison_pipeline import compare_molecules
    result = compare_molecules(
        smi1,
        smi2,
        app_state.model,
        app_state.explainer,
        app_state.bit_db,
        app_state.fp_radius,
        app_state.fp_nbits,
    )
    if "error" in result:
        return result["error"]
    if result.get("identical"):
        return f"The two molecules are identical after canonicalization: {result['canonical_smiles']}."

    p1 = result["mol1"]["probability_active"]
    p2 = result["mol2"]["probability_active"]
    if "more active" in lowered:
        winner = "first molecule" if p1 >= p2 else "second molecule"
        return (
            f"The {winner} is predicted to be more active. Molecule 1 has P(active) "
            f"{_fmt_prob(p1)}, molecule 2 has P(active) {_fmt_prob(p2)}, so the difference "
            f"between molecule 1 and molecule 2 is {_fmt_signed_prob(p1 - p2)}."
        )

    top = "; ".join(
        f"{bit['bit']} ({_fmt_shap(float(bit['shap_diff']))})"
        for bit in result.get("top_differentiating_bits", [])[:3]
    )
    return (
        f"Molecule 1 is assigned P(active) {_fmt_prob(p1)}, while molecule 2 is assigned "
        f"P(active) {_fmt_prob(p2)}. Using the comparison convention molecule 2 minus molecule 1, "
        f"delta P(active) is {_fmt_signed_prob(result['delta_probability'])}. Their ECFP Tanimoto "
        f"similarity is {_fmt_ratio(result['tanimoto'])}, so the pair is not very close in this "
        f"fingerprint space. The three largest SHAP differences are {top}."
    )


def _molecular_structured_response(message: str, smiles: str | None) -> str | None:
    lowered = message.lower()
    comparison = _comparison_report(message)
    if comparison:
        return comparison
    if not smiles:
        return None

    if "applicability domain" in lowered or "inside ad" in lowered:
        return _applicability_domain_report(smiles)

    try:
        result = _run_prediction_pipeline(smiles, top_n=30)
    except HTTPException as exc:
        return f"Invalid SMILES: {smiles}. No prediction, AD, or SHAP values should be reported. Details: {exc.detail}"

    if "expected value" in lowered or "model baseline" in lowered:
        return (
            f"The model baseline expected value is {_fmt_prob(result['expected_value'])}. "
            f"For this molecule the final P(active) is {_fmt_prob(result['probability_active'])}, "
            f"mainly shifted by these SHAP contributors: {_bits_text(result.get('top_bits', []), 3)}."
        )

    if "decision boundary" in lowered:
        margin = abs(float(result["probability_active"]) - 0.5)
        return (
            f"The model assigns P(active) {_fmt_prob(result['probability_active'])}. "
            f"Its distance from the 0.5 decision boundary is {_fmt_prob(margin)}, so this "
            f"prediction is {'close to' if margin < 0.10 else 'not close to'} the boundary."
        )

    if "single strongest negative" in lowered:
        negatives = [bit for bit in result.get("top_bits", []) if float(bit["shap_value"]) < 0]
        bit = negatives[0] if negatives else result["top_bits"][0]
        shap = float(bit["shap_value"])
        return (
            f"The strongest negative SHAP contribution is {bit['bit']}. Its SHAP value is "
            f"{_fmt_shap(shap)}, the bit is {'ON' if int(bit['bit_on']) else 'OFF'} in this molecule, "
            f"and it moves the prediction {_direction_from_shap(shap)}."
        )

    if "single strongest shap" in lowered or "single strongest" in lowered:
        bit = result["top_bits"][0]
        shap = float(bit["shap_value"])
        return (
            f"The single strongest SHAP bit is {bit['bit']}. Its contribution is "
            f"{_fmt_shap(shap)}, the bit is {'ON' if int(bit['bit_on']) else 'OFF'} in this molecule, "
            f"and it moves the prediction {_direction_from_shap(shap)}."
        )

    if "largest positive shap" in lowered:
        bits = [bit for bit in result.get("top_bits", []) if int(bit["bit_on"]) == 1 and float(bit["shap_value"]) > 0][:3]
        return (
            f"The molecule has {result['n_on_bits']} ON ECFP{2 * result['radius']} bits. "
            "The three ON bits with the largest positive SHAP values are "
            + "; ".join(f"{bit['bit']} ({_fmt_shap(float(bit['shap_value']))})" for bit in bits)
            + "."
        )

    if "largest negative shap" in lowered:
        bits = [bit for bit in result.get("top_bits", []) if int(bit["bit_on"]) == 1 and float(bit["shap_value"]) < 0][:3]
        return (
            f"The molecule has {result['n_on_bits']} ON ECFP{2 * result['radius']} bits. "
            "The ON bits with the largest negative SHAP values are "
            + "; ".join(f"{bit['bit']} ({_fmt_shap(float(bit['shap_value']))})" for bit in bits)
            + "."
        )

    if "top 5" in lowered:
        return _structured_prediction_report(smiles, top_n=5)

    if any(token in lowered for token in ("p(active)", "p(inactive)", "predicted class", "top 3 shap", "top shap")):
        return _structured_prediction_report(smiles, top_n=3)

    return None


def _aggregate_bit_response(message: str, smiles: str | None = None) -> str | None:
    lowered = message.lower()
    from core.aggregate_stats import build_aggregate_stats

    if "universal chemical meaning" in lowered:
        bit_index = _extract_signed_bit_index(message)
        example = f" Example from this session: {_format_bit_database_response(bit_index)}" if bit_index is not None else ""
        return (
            "No ECFP6 bit has a universal chemical meaning across studies. "
            "Folded-bit interpretation depends on Morgan radius, fingerprint length, "
            "hash collisions, and the structures present in the training set."
            + example
        )

    if not app_state.bit_db:
        return None

    stats = build_aggregate_stats(app_state.bit_db)
    bit_index = _extract_signed_bit_index(message)

    if bit_index is not None and bit_index in app_state.bit_db and smiles and "distinguish" in lowered:
        try:
            result = _run_prediction_pipeline(smiles, top_n=30)
        except HTTPException as exc:
            return f"Invalid SMILES: {smiles}. {exc.detail}"
        molecule_subs = []
        for item in result.get("active_bits", []):
            if int(item.get("bit_index", -1)) == bit_index:
                molecule_subs = item.get("molecule_substructures", [])
                break
        info = app_state.bit_db[bit_index]
        dominant = info.get("dominant_substructure") or "n/a"
        total = max(int(info.get("total_activations", 0)), 1)
        dominant_count = int(dict(info.get("substructures", {})).get(dominant, 0))
        sub_names = ", ".join(sub.get("smiles", "n/a") for sub in molecule_subs) or "none"
        overlap = "matches" if any(sub.get("smiles") == dominant for sub in molecule_subs) else "does not match"
        return (
            f"In the query molecule, ECFP{2 * app_state.fp_radius}_{bit_index} is activated "
            f"by the molecule-level environment {sub_names}. In the loaded training set, the "
            f"dominant environment for the same folded bit is {dominant}, observed "
            f"{dominant_count}/{total} times ({_fmt_pct(float(info.get('dominance', 0.0)))}). "
            f"Here the molecule-level environment {overlap} the dominant training-set mapping. "
            f"The important caveat is that this folded bit has "
            f"{int(info.get('n_unique_substructures', 0))} observed training-set substructures, "
            "so the bit should be interpreted as a dataset-specific mapping rather than a "
            "universal chemical label."
        )

    if bit_index is not None and bit_index in app_state.bit_db and (
        "reliable chemical interpretation" in lowered
        or "enough training-set evidence" in lowered
        or "enough training set evidence" in lowered
    ):
        info = app_state.bit_db[bit_index]
        total = int(info.get("total_activations", 0))
        n_unique = int(info.get("n_unique_substructures", 0))
        dominance = float(info.get("dominance", 0.0))
        dominant = info.get("dominant_substructure") or "n/a"
        if total < 10:
            verdict = "No: the bit is too rare in the loaded training set to assign a reliable chemical interpretation."
        elif n_unique > 1 and dominance <= 50:
            verdict = "No: the bit has substantial hash-collision ambiguity, so no single chemical environment dominates."
        elif total < 30:
            verdict = "Only cautiously: the bit has limited training-set support."
        else:
            verdict = "Yes, descriptively for this loaded training set, but not as a universal chemical meaning."
        return (
            f"{verdict} For ECFP{2 * app_state.fp_radius}_{bit_index}, the evidence is "
            f"{total} total training-set activations, {n_unique} unique observed "
            f"substructures, and dominant substructure {dominant} with {_fmt_pct(dominance)} "
            f"dominance. Its active ratio is {_fmt_ratio(float(info.get('active_ratio', 0.0)))}."
        )

    if bit_index is not None and bit_index in app_state.bit_db and "unambiguous" in lowered:
        info = app_state.bit_db[bit_index]
        n_unique = int(info.get("n_unique_substructures", 0))
        dominance = float(info.get("dominance", 0.0))
        dominant = info.get("dominant_substructure") or "n/a"
        verdict = (
            "appears unambiguous in this training set"
            if n_unique == 1
            else "does not appear unambiguous in this training set"
        )
        return (
            f"ECFP{2 * app_state.fp_radius}_{bit_index} {verdict}. It has "
            f"{n_unique} unique observed substructure(s), and the dominant substructure is "
            f"{dominant} with {_fmt_pct(dominance)} dominance across "
            f"{info.get('total_activations', 0)} activations. Its active ratio is "
            f"{_fmt_ratio(float(info.get('active_ratio', 0.0)))}."
        )

    if bit_index is not None and bit_index in app_state.bit_db and (
        "low confidence" in lowered
        or "collision confidence" in lowered
        or ("interpretation" in lowered and "confidence" in lowered)
    ):
        info = app_state.bit_db[bit_index]
        total = int(info.get("total_activations", 0))
        n_unique = int(info.get("n_unique_substructures", 0))
        dominance = float(info.get("dominance", 0.0))
        dominant = info.get("dominant_substructure") or "n/a"
        active_ratio = float(info.get("active_ratio", 0.0))
        if n_unique > 1 and dominance <= 50:
            verdict = (
                "Its interpretation should be treated as low confidence because no "
                "single atom environment dominates this folded bit."
            )
        elif n_unique > 1:
            verdict = (
                "A hash collision is present, but the interpretation is not low confidence "
                "from collision alone because one environment is dominant."
            )
        else:
            verdict = (
                "It is not collision-ambiguous in this training set, although reliability "
                "still depends on how many training activations support it."
            )
        dominance_phrase = (
            f"it accounts for {_fmt_pct(dominance)}"
            if dominance > 80
            else f"it accounts for only {_fmt_pct(dominance)}"
        )
        return (
            f"{verdict} ECFP{2 * app_state.fp_radius}_{bit_index} has "
            f"{n_unique} unique observed substructures; the dominant one is {dominant}, "
            f"and {dominance_phrase} of {total} activations. "
            f"The active ratio is {_fmt_ratio(active_ratio)}. In this session, low confidence means "
            "multiple distinct substructures map to the same folded ECFP bit and the "
            "dominant one explains at most about half of the observed activations, so "
            "assigning a single chemical meaning would be misleading."
        )

    if smiles and "active on bit" in lowered and "ambiguous" in lowered:
        try:
            result = _run_prediction_pipeline(smiles, top_n=30)
        except HTTPException as exc:
            return f"Invalid SMILES: {smiles}. {exc.detail}"
        candidates = [
            bit for bit in result.get("active_bits", [])
            if bit.get("training_info")
        ]
        if not candidates:
            return "No active ON bits with training-set collision context were found for this molecule."
        chosen = max(
            candidates,
            key=lambda bit: bit["training_info"].get("n_unique_substructures", 0),
        )
        info = chosen["training_info"]
        return (
            f"Among the active ON bits in this molecule, {chosen['bit']} has the most "
            f"ambiguous training-set collision profile. It maps to "
            f"{info.get('n_unique_substructures')} unique observed substructures; the "
            f"dominant training-set environment is {info.get('dominant_substructure')}, "
            f"but its dominance is only {_fmt_pct(info.get('dominance', 0))}."
        )

    if "highest number of unique substructures" in lowered or "most ambiguous" in lowered:
        row = stats["most_ambiguous_bits"][0] if stats["most_ambiguous_bits"] else None
        if row:
            bit = int(row["bit"])
            info = app_state.bit_db[bit]
            return (
                f"The observed ECFP{2 * app_state.fp_radius} bit with the highest number "
                f"of unique mapped substructures is ECFP{2 * app_state.fp_radius}_{bit}. "
                f"It has {int(info.get('n_unique_substructures', 0))} distinct training-set "
                f"substructures. {_format_bit_database_response(bit)} It is difficult to "
                "interpret uniquely because several chemically different atom environments "
                "share the same folded hash bit."
            )

    if "highest active ratio" in lowered:
        row = stats["top_active_bits"][0] if stats["top_active_bits"] else None
        if row:
            bit = int(row["bit"])
            info = app_state.bit_db[bit]
            return (
                f"Among sufficiently frequent observed bits, ECFP{2 * app_state.fp_radius}_{bit} "
                f"has the highest active ratio: {_fmt_ratio(float(info.get('active_ratio', 0.0)))}. "
                f"Its dominant training-set substructure is {info.get('dominant_substructure') or 'n/a'} "
                f"with {_fmt_pct(float(info.get('dominance', 0.0)))} dominance "
                f"over {info.get('total_activations', 0)} activations. "
                f"The main collision context is: {_format_substructure_list(info, 5)}."
            )

    if "strongest inactive association" in lowered:
        row = stats["top_inactive_bits"][0] if stats["top_inactive_bits"] else None
        if row:
            bit = int(row["bit"])
            info = app_state.bit_db[bit]
            return (
                f"Among sufficiently frequent observed bits, ECFP{2 * app_state.fp_radius}_{bit} "
                f"has the strongest inactive association, with active ratio "
                f"{_fmt_ratio(float(info.get('active_ratio', 0.0)))}. "
                f"Its dominant training-set substructure is {info.get('dominant_substructure') or 'n/a'} "
                f"with {_fmt_pct(float(info.get('dominance', 0.0)))} dominance "
                f"over {info.get('total_activations', 0)} activations. "
                f"The main collision context is: {_format_substructure_list(info, 5)}."
            )

    if smiles and "top shap bit" in lowered and ("clearest" in lowered or "dominant substructure" in lowered):
        try:
            result = _run_prediction_pipeline(smiles, top_n=30)
        except HTTPException as exc:
            return f"Invalid SMILES: {smiles}. {exc.detail}"
        candidates = [
            bit for bit in result.get("top_bits", [])
            if bit.get("training_info")
        ]
        if not candidates:
            return "No top SHAP bits with training-set context were found for this molecule."
        chosen = max(
            candidates,
            key=lambda bit: bit["training_info"].get("dominance", 0),
        )
        return (
            f"Among the top SHAP bits for this molecule, {chosen['bit']} has the clearest "
            f"dominant training-set substructure. The dominant environment is "
            f"{chosen['training_info'].get('dominant_substructure')}, with "
            f"{_fmt_pct(chosen['training_info'].get('dominance', 0))} dominance."
        )

    return None


def _deterministic_response(message: str, smiles_context: str | None = None) -> str | None:
    for handler in (
        _unsupported_fact_response,
        _descriptor_guard_response,
        _maccs_response,
        _compare_guard_response,
    ):
        response = handler(message)
        if response:
            return response

    bit_index = _extract_signed_bit_index(message)
    smiles = _resolve_smiles_context(smiles_context, message)

    aggregate_bit = _aggregate_bit_response(message, smiles)
    if aggregate_bit:
        return aggregate_bit

    if bit_index is not None and smiles:
        return _molecule_bit_response(smiles, bit_index)
    if bit_index is not None:
        return _format_bit_database_response(bit_index)

    molecular = _molecular_structured_response(message, smiles)
    if molecular:
        return molecular

    if smiles and _is_prediction_request(message):
        return _structured_prediction_report(smiles, top_n=3)

    response = _dataset_context_response(message)
    if response:
        return response

    return None


def _dataset_summary() -> str | None:
    if not app_state.has_training_data():
        return None

    n_molecules = len(app_state.training_smiles)
    active = int(app_state.training_labels.sum()) if app_state.training_labels is not None else 0
    inactive = int((app_state.training_labels == 0).sum()) if app_state.training_labels is not None else 0
    lines = [
        "LLM remoto non raggiungibile: rispondo con il fallback locale di RAGMODEX.",
        "",
        "Dataset caricato:",
        f"- Molecole training: {n_molecules}",
        f"- Attive: {active}",
        f"- Inattive: {inactive}",
        f"- Fingerprint: ECFP{2 * app_state.fp_radius}, radius {app_state.fp_radius}, {app_state.fp_nbits} bit",
    ]

    if app_state.bit_db:
        total_bits = len(app_state.bit_db)
        ambiguous = sum(1 for info in app_state.bit_db.values() if info.get("is_ambiguous"))
        highly_ambiguous = sum(
            1 for info in app_state.bit_db.values()
            if info.get("n_unique_substructures", 0) >= 5
        )
        lines.extend([
            "",
            "Bit collision:",
            f"- Bit osservati nel training: {total_bits}",
            f"- Bit con collisioni: {ambiguous}",
            f"- Bit con >=5 sottostrutture: {highly_ambiguous}",
        ])

        top = sorted(
            app_state.bit_db.items(),
            key=lambda item: item[1].get("n_unique_substructures", 0),
            reverse=True,
        )[:5]
        if top:
            lines.append("- Bit piu ambigui:")
            for bit, info in top:
                lines.append(
                    f"  - ECFP{2 * app_state.fp_radius}_{bit}: "
                    f"{info.get('n_unique_substructures', 0)} sottostrutture, "
                    f"dominante {info.get('dominance', 0):.1f}%"
                )
    return "\n".join(lines)


def _bit_summary(bit_index: int) -> str:
    if not app_state.bit_db:
        return "Bit database non disponibile: carica prima il training set."

    info = app_state.bit_db.get(bit_index)
    if not info:
        return f"ECFP{2 * app_state.fp_radius}_{bit_index} non e presente nel bit database del training."

    total = sum(info.get("substructures", {}).values())
    lines = [
        "LLM remoto non raggiungibile: rispondo con il fallback locale di RAGMODEX.",
        "",
        f"ECFP{2 * app_state.fp_radius}_{bit_index}",
        f"- Attivazioni training: {info.get('total_activations', 0)}",
        f"- Active ratio: {info.get('active_ratio', 0) * 100:.1f}%",
        f"- Sottostrutture distinte: {info.get('n_unique_substructures', 0)}",
        f"- Sottostruttura dominante: {info.get('dominant_substructure') or 'n/d'}",
        f"- Dominance: {info.get('dominance', 0):.1f}%",
    ]
    if info.get("is_ambiguous"):
        lines.append("- Interpretazione: bit collision presente; valuta le percentuali delle sottostrutture.")
    else:
        lines.append("- Interpretazione: bit non ambiguo nel training.")

    subs = list(info.get("substructures", {}).items())[:8]
    if subs:
        lines.append("")
        lines.append("Sottostrutture principali:")
        for smiles, count in subs:
            pct = count / total * 100 if total else 0.0
            lines.append(f"- {smiles}: {pct:.1f}% ({count})")
    return "\n".join(lines)


def _prediction_summary(smiles: str) -> str:
    if not app_state.has_model():
        return "Nessun modello caricato: carica un modello in Settings prima di chiedere predizioni."

    from core.model_pipeline import predict_and_interpret

    result = predict_and_interpret(
        smiles=smiles,
        model=app_state.model,
        explainer=app_state.explainer,
        bit_db=app_state.bit_db,
        radius=app_state.fp_radius,
        n_bits=app_state.fp_nbits,
        top_n=8,
    )
    if "error" in result:
        return result["error"]

    lines = [
        "LLM remoto non raggiungibile: rispondo con il fallback locale di RAGMODEX.",
        "",
        f"SMILES canonico: {result['canonical_smiles']}",
        f"Predizione: {result['prediction']}",
        f"P(active): {result['probability_active'] * 100:.2f}%",
        f"P(inactive): {result['probability_inactive'] * 100:.2f}%",
        f"Fingerprint: ECFP{2 * result['radius']}, {result['n_bits']} bit, {result['n_on_bits']} bit ON",
        "",
        "Top bit SHAP:",
    ]
    for bit in result["top_bits"][:8]:
        lines.append(
            f"- {bit['bit']}: {bit['shap_value']:+.5f} {bit['direction']} "
            f"({'ON' if bit['bit_on'] else 'OFF'})"
        )

    active_bits = result.get("active_bits", [])
    collision_bits = [
        bit for bit in active_bits
        if bit.get("training_info") and bit["training_info"].get("is_ambiguous")
    ]
    if collision_bits:
        collision_bits.sort(
            key=lambda bit: bit["training_info"].get("n_unique_substructures", 0),
            reverse=True,
        )
        lines.extend(["", "Bit attivi con collisioni principali:"])
        for bit in collision_bits[:6]:
            info = bit["training_info"]
            lines.append(
                f"- {bit['bit']}: {info.get('n_unique_substructures', 0)} sottostrutture, "
                f"dominante {info.get('dominance', 0):.1f}%"
            )
    return "\n".join(lines)


def _run_prediction_pipeline(smiles: str, top_n: int = 10) -> dict:
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded. Upload a model first.")

    from core.model_pipeline import predict_and_interpret

    result = predict_and_interpret(
        smiles=smiles,
        model=app_state.model,
        explainer=app_state.explainer,
        bit_db=app_state.bit_db,
        radius=app_state.fp_radius,
        n_bits=app_state.fp_nbits,
        top_n=top_n,
    )
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


def _format_pipeline_prompt(message: str, pipeline_context: str, rag_context: str | None) -> str:
    context = pipeline_context
    if rag_context:
        context = f"{pipeline_context}\n\n=== RETRIEVED RAG CONTEXT ===\n{rag_context}"

    from llm.prompt_templates import PromptTemplates
    return PromptTemplates.format_molecule_prediction_prompt(context, message)


def _local_fallback_response(message: str, error: Exception | None = None) -> str:
    bit_match = re.search(r"\b(?:bit|ECFP\d*)[\s_:-]*(\d{1,5})\b", message, flags=re.IGNORECASE)
    if bit_match:
        return _bit_summary(int(bit_match.group(1)))

    smiles = _extract_smiles(message)
    if smiles:
        return _prediction_summary(smiles)

    lowered = message.lower()
    if any(token in lowered for token in ("dataset", "training", "summary", "riassum", "collision", "ambig")):
        summary = _dataset_summary()
        if summary:
            return summary

    detail = _friendly_llm_error(error) if error else "LLM remoto non raggiungibile."
    return (
        f"{detail}\n\n"
        "Posso comunque rispondere localmente a: predizioni SMILES, riassunti del dataset, "
        "statistiche sui bit collision e dettagli di un bit specifico. Esempi: "
        "predict \"O=C(Nc1ccccc1)c1ccncc1\", summarize dataset, bit 809."
    )


async def _stream_response(
    message: str,
    rag_context: str | None,
    smiles: str | None = None,
) -> AsyncGenerator[str, None]:
    deterministic = _deterministic_response(message, smiles)
    if deterministic is not None:
        yield f"data: {json.dumps({'chunk': deterministic})}\n\n"
        yield "data: [DONE]\n\n"
        return

    prompt = message
    system_override = None
    if smiles:
        from core.model_pipeline import format_interpretation_context
        from llm.prompt_templates import PromptTemplates

        result = _run_prediction_pipeline(smiles)
        pipeline_context = format_interpretation_context(result)
        prompt = _format_pipeline_prompt(message, pipeline_context, rag_context)
        system_override = PromptTemplates.MOLECULE_PREDICTION_SYSTEM_PROMPT
    elif rag_context:
        from llm.prompt_templates import PromptTemplates
        prompt = PromptTemplates.format_rag_prompt(rag_context, message)

    # Qwen and similar reasoning models may expose <think> blocks over the stream.
    # Buffer streaming responses so we can remove those blocks before returning.
    buffered_chunks: list[str] = []
    sent_any = False

    def strip_reasoning(text: str) -> str:
        return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

    try:
        handler = _get_handler()
        for chunk in handler.stream_query(prompt, system_override=system_override):
            buffered_chunks.append(chunk)
        content = strip_reasoning("".join(buffered_chunks))
        if content:
            sent_any = True
            yield f"data: {json.dumps({'chunk': content})}\n\n"
    except Exception as e:
        fallback = _prediction_summary(smiles) if smiles else _local_fallback_response(message, e)
        sent_any = True
        yield f"data: {json.dumps({'chunk': fallback})}\n\n"
    finally:
        if not sent_any:
            yield f"data: {json.dumps({'chunk': ''})}\n\n"
        yield "data: [DONE]\n\n"


async def _legacy_stream_response(message: str, rag_context: str | None) -> AsyncGenerator[str, None]:
    prompt = message
    if rag_context:
        from llm.prompt_templates import PromptTemplates
        prompt = PromptTemplates.format_rag_prompt(rag_context, message)

    try:
        handler = _get_handler()
        for chunk in handler.stream_query(prompt):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
    except Exception as e:
        fallback = _local_fallback_response(message, e)
        yield f"data: {json.dumps({'chunk': fallback})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    rag_context = _retrieve_context(req.message) if req.use_rag else None
    smiles = _resolve_smiles_context(req.smiles_context, req.message)

    return StreamingResponse(
        _stream_response(req.message, rag_context, smiles),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/simple")
def chat_simple(req: ChatRequest):
    """Non-streaming chat for short responses."""
    rag_context = _retrieve_context(req.message) if req.use_rag else None
    smiles = _resolve_smiles_context(req.smiles_context, req.message)

    deterministic = _deterministic_response(req.message, smiles)
    if deterministic is not None:
        return {"response": deterministic, "pipeline_injected": bool(smiles)}

    prompt = req.message
    system_override = None
    if smiles:
        from core.model_pipeline import format_interpretation_context
        from llm.prompt_templates import PromptTemplates

        result = _run_prediction_pipeline(smiles)
        pipeline_context = format_interpretation_context(result)
        prompt = _format_pipeline_prompt(req.message, pipeline_context, rag_context)
        system_override = PromptTemplates.MOLECULE_PREDICTION_SYSTEM_PROMPT
    elif rag_context:
        from llm.prompt_templates import PromptTemplates
        prompt = PromptTemplates.format_rag_prompt(rag_context, req.message)

    try:
        handler = _get_handler()
        response = handler.simple_query(prompt, system_override=system_override)
    except Exception as e:
        response = _prediction_summary(smiles) if smiles else _local_fallback_response(req.message, e)

    return {"response": response, "pipeline_injected": bool(smiles)}


@router.post("/with-pipeline")
def chat_with_pipeline(req: PipelineChatRequest):
    """Non-streaming molecular chat with computed pipeline context injected."""
    rag_context = _retrieve_context(req.message) if req.use_rag else None

    from core.model_pipeline import format_interpretation_context
    from llm.prompt_templates import PromptTemplates

    result = _run_prediction_pipeline(req.smiles, req.top_n)
    pipeline_context = format_interpretation_context(result)
    prompt = _format_pipeline_prompt(req.message, pipeline_context, rag_context)

    try:
        handler = _get_handler()
        response = handler.simple_query(
            prompt,
            system_override=PromptTemplates.MOLECULE_PREDICTION_SYSTEM_PROMPT,
        )
    except Exception:
        response = _prediction_summary(req.smiles)

    return {
        "response": response,
        "pipeline_injected": True,
        "smiles": result["canonical_smiles"],
    }
