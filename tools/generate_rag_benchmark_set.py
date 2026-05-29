"""Generate an annotated RAG benchmark question set from the saved session.

The generated files are intended to be used with tools/rag_benchmark.py:

    python tools/generate_rag_benchmark_set.py
    python tools/rag_benchmark.py benchmark_inputs/questions.txt --provider groq \
        --models llama-3.3-70b-versatile llama-3.1-8b-instant gemma2-9b-it

Outputs:
    benchmark_inputs/questions.txt
    benchmark_inputs/questions_annotated.csv
    benchmark_inputs/questions_annotated.json
    benchmark_inputs/rag_reference_corpus.txt
"""

from __future__ import annotations

import csv
import json
import pickle
import sys
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.aggregate_stats import build_aggregate_stats
from core.applicability_domain import build_ad_model, check_applicability_domain
from core.bit_database import get_bit_context
from core.comparison_pipeline import compare_molecules
from core.model_pipeline import create_explainer, load_model, predict_and_interpret


SESSION_DIR = ROOT / "data" / "session"
OUT_DIR = ROOT / "benchmark_inputs"


@dataclass
class BenchmarkRow:
    question_id: str
    category: str
    question: str
    expected_answer: str
    required_chunks_or_data: str
    pass_fail_criterion: str
    metric_notes: str


def load_session() -> dict[str, Any]:
    meta_path = SESSION_DIR / "meta.json"
    model_path = SESSION_DIR / "model.bin"
    training_path = SESSION_DIR / "training.npz"
    test_path = SESSION_DIR / "test.npz"
    bit_db_path = SESSION_DIR / "bit_db.pkl"

    if not meta_path.exists() or not model_path.exists() or not training_path.exists():
        raise SystemExit(
            "Missing saved session files. Save a RAGMODEX session with model and "
            "training dataset before generating the benchmark."
        )

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    training = np.load(training_path, allow_pickle=True)
    test = np.load(test_path, allow_pickle=True) if test_path.exists() else None
    model = load_model(model_path.read_bytes())
    with bit_db_path.open("rb") as fh:
        bit_db = pickle.load(fh)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        explainer = create_explainer(model)

    return {
        "meta": meta,
        "model": model,
        "explainer": explainer,
        "training_fps": training["fps"],
        "training_labels": training["labels"],
        "training_smiles": training["smiles"].astype(str).tolist(),
        "test_fps": test["fps"] if test is not None else None,
        "test_labels": test["labels"] if test is not None else None,
        "test_smiles": test["smiles"].astype(str).tolist() if test is not None else [],
        "bit_db": bit_db,
        "radius": int(meta.get("fp_radius", 3)),
        "n_bits": int(meta.get("fp_nbits", 2048)),
    }


def fmt_float(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def clean_text(value: Any) -> str:
    text = str(value)
    replacements = {
        "→": "->",
        "←": "<-",
        "−": "-",
        "–": "-",
        "—": "-",
        "×": "x",
        "≥": ">=",
        "≤": "<=",
        "±": "+/-",
        "â†’": "->",
        "â€”": "-",
        "â€“": "-",
        "â‰¥": ">=",
        "â‰¤": "<=",
        "â€¢": "-",
        "âœ…": "",
        "âš ï¸": "WARNING",
        "ðŸ”´": "LOW",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("ascii", errors="replace").decode("ascii")


def top_bits_text(result: dict, n: int = 3) -> str:
    parts = []
    for bit in result.get("top_bits", [])[:n]:
        parts.append(
            f"{bit['bit']} shap={bit['shap_value']:+.6f} "
            f"direction={clean_text(bit['direction'])} on={bit['bit_on']}"
        )
    return "; ".join(parts)


def bit_summary(bit_idx: int, bit_db: dict) -> str:
    if bit_idx not in bit_db:
        return f"ECFP6_{bit_idx} was never activated in the training set; no substructure data available."
    info = bit_db[bit_idx]
    subs = list(info.get("substructures", {}).items())[:5]
    sub_text = "; ".join(f"{smi} ({count})" for smi, count in subs)
    return (
        f"ECFP6_{bit_idx}: total_activations={info.get('total_activations')}; "
        f"active_freq={info.get('active_freq')}; inactive_freq={info.get('inactive_freq')}; "
        f"active_ratio={fmt_float(info.get('active_ratio'), 4)}; "
        f"n_unique_substructures={info.get('n_unique_substructures')}; "
        f"dominant_substructure={info.get('dominant_substructure')}; "
        f"dominance={fmt_float(info.get('dominance'), 2)}%; "
        f"top_substructures={sub_text}"
    )


def selected_smiles(session: dict[str, Any], n: int = 8) -> list[str]:
    model = session["model"]
    fps = session["test_fps"] if session["test_fps"] is not None else session["training_fps"]
    smiles = session["test_smiles"] or session["training_smiles"]
    probs = model.predict_proba(fps)[:, 1]
    targets = [0.95, 0.80, 0.65, 0.52, 0.48, 0.35, 0.20, 0.05]
    chosen: list[int] = []
    for target in targets:
        order = np.argsort(np.abs(probs - target))
        for idx in order:
            idx_int = int(idx)
            smi = smiles[idx_int]
            if idx_int not in chosen and 3 <= len(smi) <= 120:
                chosen.append(idx_int)
                break
        if len(chosen) >= n:
            break
    return [smiles[i] for i in chosen[:n]]


def make_molecular_rows(session: dict[str, Any]) -> list[BenchmarkRow]:
    model = session["model"]
    explainer = session["explainer"]
    bit_db = session["bit_db"]
    radius = session["radius"]
    n_bits = session["n_bits"]
    stats = build_aggregate_stats(bit_db)
    ad_model = build_ad_model(session["training_fps"])
    smiles_list = selected_smiles(session)

    rows: list[BenchmarkRow] = []

    for i, smiles in enumerate(smiles_list[:6], 1):
        result = predict_and_interpret(smiles, model, explainer, bit_db, radius, n_bits, top_n=5)
        expected = (
            f"canonical_smiles={result['canonical_smiles']}; prediction={result['prediction']}; "
            f"P(active)={fmt_float(result['probability_active'], 6)}; "
            f"P(inactive)={fmt_float(result['probability_inactive'], 6)}; "
            f"n_on_bits={result['n_on_bits']}; top3_shap={top_bits_text(result, 3)}"
        )
        rows.append(BenchmarkRow(
            f"mol_predict_{i:02d}",
            "molecular",
            f"Predict {smiles}. Return P(active), P(inactive), predicted class and the top 3 SHAP bits.",
            expected,
            "Deterministic model.predict_proba plus SHAP TreeExplainer from saved session.",
            "PASS if predicted class, P(active) within +/-0.01, P(inactive) within +/-0.01, and at least two of the listed top 3 SHAP bits are reported correctly.",
            "faithfulness, hallucination, latency",
        ))

    for i, smiles in enumerate(smiles_list[:4], 1):
        result = predict_and_interpret(smiles, model, explainer, bit_db, radius, n_bits, top_n=5)
        bit = result["top_bits"][0]
        bit_idx = int(bit["bit_index"])
        subs = ", ".join(s["smiles"] for s in bit.get("molecule_substructures", [])) or "none"
        db = bit.get("training_info") or {}
        expected = (
            f"canonical_smiles={result['canonical_smiles']}; ECFP6_{bit_idx}; "
            f"bit_on={bit['bit_on']}; shap={bit['shap_value']:+.6f}; "
            f"direction={clean_text(bit['direction'])}; molecule_substructures={subs}; "
            f"training_active_ratio={fmt_float(db.get('active_ratio'), 4)}; "
            f"training_n_unique_substructures={db.get('n_unique_substructures', 'n/a')}; "
            f"dominant_substructure={db.get('dominant_substructure', 'n/a')}"
        )
        rows.append(BenchmarkRow(
            f"mol_bit_in_molecule_{i:02d}",
            "molecular",
            f"For molecule {smiles}, interpret ECFP6 bit {bit_idx}: is it ON, what substructure activates it, and what is the SHAP value?",
            expected,
            "predict_and_interpret top_bits plus bit_db entry for the same bit.",
            "PASS if answer states ON/OFF status, SHAP sign/value within +/-0.005, at least one correct molecule substructure when available, and the training collision context.",
            "faithfulness, hallucination, latency",
        ))

    global_bits = [5]
    global_bits.extend(int(x["bit"]) for x in stats["most_ambiguous_bits"][:2])
    if stats["top_active_bits"]:
        global_bits.append(int(stats["top_active_bits"][0]["bit"]))
    for i, bit_idx in enumerate(dict.fromkeys(global_bits), 1):
        rows.append(BenchmarkRow(
            f"mol_global_bit_{i:02d}",
            "molecular",
            f"What does ECFP6 bit {bit_idx} represent in the loaded training set?",
            bit_summary(bit_idx, bit_db),
            f"bit_db[{bit_idx}] via core.bit_database.get_bit_context; full context starts: {get_bit_context(bit_idx, bit_db)[:500]}",
            "PASS if answer does not invent a unique meaning when the bit is collided, reports activation counts/active ratio approximately, and mentions dominant substructure or no-data status correctly.",
            "faithfulness, hallucination, latency",
        ))

    compare_pairs = [
        (smiles_list[0], smiles_list[1]),
        (smiles_list[2], smiles_list[5]),
        (smiles_list[3], "CCCCC"),
    ]
    for i, (smi1, smi2) in enumerate(compare_pairs, 1):
        comp = compare_molecules(smi1, smi2, model, explainer, bit_db, radius, n_bits)
        if "error" in comp:
            expected = comp["error"]
        else:
            expected = (
                f"mol1={comp['mol1']['canonical_smiles']} P(active)={fmt_float(comp['mol1']['probability_active'], 6)}; "
                f"mol2={comp['mol2']['canonical_smiles']} P(active)={fmt_float(comp['mol2']['probability_active'], 6)}; "
                f"delta_P_active={comp['delta_probability']:+.6f}; tanimoto={fmt_float(comp['tanimoto'], 6)}; "
                f"bits_only_mol1={comp['bits_only_mol1']}; bits_only_mol2={comp['bits_only_mol2']}; "
                f"bits_shared={comp['bits_shared']}; top_diff_bits="
                + "; ".join(
                    f"{b['bit']} shap_diff={b['shap_diff']:+.6f}"
                    for b in comp["top_differentiating_bits"][:3]
                )
            )
        rows.append(BenchmarkRow(
            f"mol_compare_{i:02d}",
            "molecular",
            f"Compare {smi1} and {smi2}: report P(active), delta P(active), Tanimoto similarity and the main differentiating SHAP bits.",
            expected,
            "core.comparison_pipeline.compare_molecules on saved model/session.",
            "PASS if both probabilities are within +/-0.01, delta and Tanimoto are approximately correct, and at least two top differentiating bits match.",
            "faithfulness, hallucination, latency",
        ))

    ad_smiles = [smiles_list[0], smiles_list[-1], "CCCCCCCCCCCCCCCCCCCCCCCCCCCC"]
    for i, smiles in enumerate(ad_smiles, 1):
        ad = check_applicability_domain(smiles, ad_model, model, explainer, bit_db, radius, n_bits)
        expected = (
            f"inside_ad={ad.get('inside_ad')}; ad_confidence={ad.get('ad_confidence')}; "
            f"mean_knn_distance={fmt_float(ad.get('mean_knn_distance'), 6)}; "
            f"ad_threshold={fmt_float(ad.get('ad_threshold'), 6)}; "
            f"train_mean_dist={fmt_float(ad.get('train_mean_dist'), 6)}; "
            f"train_std_dist={fmt_float(ad.get('train_std_dist'), 6)}; "
            f"rf_prediction_std={fmt_float(ad.get('rf_prediction_std'), 6)}; "
            f"prediction={ad.get('prediction', {}).get('prediction')}; "
            f"P(active)={fmt_float(ad.get('prediction', {}).get('probability_active'), 6)}"
        )
        rows.append(BenchmarkRow(
            f"mol_ad_{i:02d}",
            "molecular",
            f"Check the applicability domain for {smiles}: is it inside AD and what are the kNN distance and threshold?",
            expected,
            "core.applicability_domain.check_applicability_domain with kNN Jaccard AD model from training fingerprints.",
            "PASS if inside/outside AD status is correct and mean distance/threshold are within +/-0.02.",
            "faithfulness, hallucination, latency",
        ))

    return rows[:20]


def make_conceptual_rows(session: dict[str, Any]) -> list[BenchmarkRow]:
    meta = session["meta"]
    training_labels = session["training_labels"]
    test_labels = session["test_labels"]
    bit_db = session["bit_db"]
    stats = build_aggregate_stats(bit_db)

    train_active = int(np.asarray(training_labels).sum())
    train_inactive = int((np.asarray(training_labels) == 0).sum())
    test_active = int(np.asarray(test_labels).sum()) if test_labels is not None else 0
    test_inactive = int((np.asarray(test_labels) == 0).sum()) if test_labels is not None else 0
    cs = stats["collision_stats"]

    concepts = [
        (
            "concept_ecfp6",
            "Che cosa e ECFP6 in RAGMODEX e quali parametri usa la sessione caricata?",
            f"ECFP6 is a Morgan/Extended Connectivity fingerprint with radius={session['radius']} and n_bits={session['n_bits']} in this session.",
            "README.md lines around ECFP6 and ARCHITECTURE.md Section 3.1.",
            "PASS if answer states Morgan/ECFP, radius 3 means ECFP6, folded binary vector, 2048 bits.",
        ),
        (
            "concept_shap",
            "Che cosa rappresenta un valore SHAP positivo o negativo sui bit ECFP?",
            "SHAP values are computed for the class-1 active output; positive pushes toward Active, negative pushes toward Inactive.",
            "ARCHITECTURE.md Sections 4.3 and 5.",
            "PASS if answer identifies class-1 active attribution and correct sign interpretation.",
        ),
        (
            "concept_collision",
            "Che cosa e una bit collision nel fingerprint ECFP e perche rende ambigua l'interpretazione?",
            "A folded bit can aggregate multiple distinct atomic environments; SHAP for that bit is a mixed signal unless one substructure dominates.",
            "README.md ECFP section; ARCHITECTURE.md Sections 3.1, 5.3-5.4.",
            "PASS if answer mentions hashing/folding, multiple substructures per bit, and mixed SHAP interpretation.",
        ),
        (
            "concept_dataset_summary",
            "Descrivi il dataset caricato con numeri esatti di training e test.",
            f"Training: {len(session['training_smiles'])} molecules, {train_active} active, {train_inactive} inactive. Test: {len(session['test_smiles'])} molecules, {test_active} active, {test_inactive} inactive. Model name: {meta.get('model_name')}.",
            "Saved session meta.json and training/test npz labels.",
            "PASS if training/test sizes and active/inactive counts are exact.",
        ),
        (
            "concept_bit_database",
            "Quali statistiche globali contiene il bit database del training set?",
            f"Observed bits={cs['total_bits']}; unambiguous={cs['unambiguous']}; ambiguous={cs['ambiguous']}; highly_ambiguous={cs['highly_ambiguous']}; ambiguity_rate={cs['ambiguity_rate']:.1f}%.",
            "core.aggregate_stats.build_aggregate_stats(bit_db).",
            "PASS if answer reports observed bits and ambiguity counts/rate accurately.",
        ),
        (
            "concept_ad",
            "Come viene calcolato l'applicability domain in RAGMODEX?",
            "AD uses kNN with Jaccard distance on ECFP6 fingerprints, n_neighbors=min(5,n_train), threshold=train mean distance + 2*std.",
            "core.applicability_domain and ARCHITECTURE.md Section 4.4.",
            "PASS if answer states kNN/Jaccard, 5 neighbors, and mean+2std threshold.",
        ),
        (
            "concept_maccs",
            "A cosa servono le MACCS keys in RAGMODEX e sono usate dal modello predittivo?",
            "MACCS keys are displayed/explored as 166-bit keys; bit 0 is conventionally unused. The predictive model/SHAP pipeline uses ECFP6, not MACCS.",
            "ARCHITECTURE.md Section 3.2.",
            "PASS if answer does not claim MACCS drives model predictions.",
        ),
        (
            "concept_rag_grounding",
            "In che modo la chat RAG evita di allucinare sulle predizioni molecolari?",
            "The chat prompt is injected with computed pipeline data: predictions, SHAP values, fingerprint-bit environments, bit database and AD scores.",
            "README.md RAG-Augmented Chat; ARCHITECTURE.md Section 6.",
            "PASS if answer mentions computed context injection rather than generic LLM knowledge.",
        ),
        (
            "concept_top_bits",
            "Come vengono scelti i top bit mostrati nella spiegazione SHAP?",
            "Top bits are ranked by descending absolute SHAP value for the active-class SHAP vector.",
            "core.model_pipeline.predict_and_interpret and ARCHITECTURE.md Section 4.3.",
            "PASS if answer says |SHAP| ranking, not frequency or probability alone.",
        ),
        (
            "concept_design",
            "Come seleziona le molecole il modulo Design di RAGMODEX?",
            "Design uses beam search and MMR-like selection balancing predicted activity, structural diversity and applicability-domain proximity.",
            "README.md Guided Molecular Design; ARCHITECTURE.md Section 7.",
            "PASS if answer includes activity, diversity and AD balance.",
        ),
        (
            "concept_descriptor",
            "Quali descrittori fisicochimici comuni puo calcolare il DescriptorCalculator?",
            "Common panel includes MolWt, ExactMolWt, LogP, MR, TPSA, LabuteASA, H-donors, H-acceptors, rotatable bonds, heteroatoms, aromatic/saturated/aliphatic rings, RingCount, FractionCSP3, heavy atoms.",
            "core.descriptor_calculator.calculate_physicochemical.",
            "PASS if answer lists several correct RDKit descriptors and avoids nonexistent custom descriptors.",
        ),
        (
            "concept_model_requirement",
            "Che requisito deve avere un modello caricato in RAGMODEX?",
            "The model must be scikit-learn compatible binary classifier exposing predict_proba().",
            "README.md model-agnostic description; ARCHITECTURE.md model upload sections.",
            "PASS if answer mentions scikit-learn compatible and predict_proba.",
        ),
        (
            "concept_training_upload",
            "Quali colonne servono nel CSV di training?",
            "Training CSV needs a SMILES column and a binary label column; invalid SMILES are skipped during fingerprint generation.",
            "ARCHITECTURE.md Section 2.1.",
            "PASS if answer names SMILES and binary label and does not require IC50.",
        ),
        (
            "concept_retrieval_metrics",
            "Come valuteresti retrieval precision@5 nel benchmark RAG?",
            "For conceptual queries, mark how many of the top 5 retrieved chunks match the annotated required chunks/sources, then divide by 5.",
            "Benchmark protocol defined in annotated file.",
            "PASS if answer describes top-5 chunk relevance against annotated required chunks.",
        ),
        (
            "concept_tanimoto",
            "Che ruolo ha la similarita di Tanimoto nelle comparazioni e nell'AD?",
            "Comparison reports Tanimoto over ECFP bit vectors; AD uses Jaccard distance, equivalent to 1 - Tanimoto for binary fingerprints.",
            "core.comparison_pipeline and core.applicability_domain.",
            "PASS if answer connects Tanimoto/Jaccard to binary fingerprints.",
        ),
        (
            "concept_expected_value",
            "Che cos'e l'expected value nella spiegazione SHAP?",
            "It is the SHAP model baseline for the active-class output, used as the reference value before feature contributions shift the prediction.",
            "core.model_pipeline.format_interpretation_context.",
            "PASS if answer identifies it as SHAP baseline, not measured activity.",
        ),
        (
            "concept_active_bits",
            "Qual e la differenza tra top SHAP bits e active bits?",
            "Top SHAP bits are highest absolute attribution bits, whether ON or OFF; active bits are all folded fingerprint bits ON in the molecule.",
            "core.model_pipeline.predict_and_interpret.",
            "PASS if answer distinguishes attribution ranking from ON-bit inventory.",
        ),
        (
            "concept_collision_confidence",
            "Come viene stimata la confidence interpretativa di un bit colliso?",
            "Confidence depends on dominance/n_unique_substructures: single/no collision is high; dominant coverage >80 high, >50 moderate, otherwise low/mixed signal.",
            "core.model_pipeline.format_interpretation_context and core.bit_database.",
            "PASS if answer uses dominance thresholds and mixed-signal warning.",
        ),
        (
            "concept_llm_backend",
            "Cambiare provider LLM cambia le predizioni numeriche del modello QSAR?",
            "No. Provider/model changes affect generated language only; deterministic QSAR probabilities, SHAP and AD come from the loaded local model/session pipeline.",
            "Application architecture: backend model pipeline versus LLM chat handler.",
            "PASS if answer says numeric pipeline is independent from LLM provider.",
        ),
        (
            "concept_loaded_model",
            "Quale modello e salvato nella sessione corrente e con quali fingerprint?",
            f"Saved model_name={meta.get('model_name')}; fingerprint radius={session['radius']}; n_bits={session['n_bits']}; manual_save={meta.get('manual_save')}.",
            "data/session/meta.json.",
            "PASS if answer reports model name and fingerprint parameters exactly.",
        ),
    ]

    return [
        BenchmarkRow(qid, "conceptual", question, expected, required, criterion, "retrieval_precision@5, faithfulness, hallucination, latency")
        for qid, question, expected, required, criterion in concepts
    ]


def make_edge_rows() -> list[BenchmarkRow]:
    cases = [
        ("edge_invalid_smiles_01", "Predict not-a-smiles and explain the result.", "Refuse/return invalid SMILES; no probability, SHAP or AD should be invented.", "RDKit MolFromSmiles validation.", "PASS if answer clearly says invalid SMILES and does not provide fake P(active)."),
        ("edge_invalid_smiles_02", "Analyze C1CC and list top SHAP bits.", "Refuse/return invalid SMILES; ring is not closed.", "RDKit validation.", "PASS if invalid molecule is detected."),
        ("edge_empty_query", "I am sending an empty molecular query: ''. What is the prediction?", "Refuse because no molecule/question content was provided.", "Input validation / chat routing.", "PASS if asks for a valid SMILES or question."),
        ("edge_bit_out_of_range_high", "What does ECFP6 bit 9999 represent?", "Refuse/out of range because session fingerprint has 2048 bits, valid indices 0-2047.", "Session fp_nbits=2048.", "PASS if answer does not invent bit 9999."),
        ("edge_bit_negative", "Interpret ECFP6 bit -1 in the training set.", "Refuse invalid negative bit index.", "ECFP bit index validation.", "PASS if negative bit is rejected."),
        ("edge_maccs_zero", "What does MACCS key 0 mean?", "Refuse or explain MACCS bit 0 is conventionally unused.", "ARCHITECTURE.md MACCS section.", "PASS if bit 0 is not assigned a chemical meaning."),
        ("edge_maccs_167", "Interpret MACCS key 167 for CCO.", "Refuse/out of range for standard MACCS keys 1-166.", "MACCS key range.", "PASS if no fake key 167 meaning is given."),
        ("edge_unknown_descriptor_01", "Calculate descriptor AB_42 for CCO.", "Refuse unknown descriptor AB_42.", "DescriptorCalculator.ALL_DESCRIPTORS validation.", "PASS if descriptor is called unknown/nonexistent."),
        ("edge_unknown_descriptor_02", "Calculate Dragon_XYZ for benzene using RAGMODEX.", "Refuse unsupported/nonexistent descriptor.", "RDKit descriptor registry.", "PASS if no numeric value is invented."),
        ("edge_compare_missing_second", "Compare CCO with nothing and tell me the delta P(active).", "Refuse because two valid molecules are required.", "Comparison input validation.", "PASS if it asks for a second SMILES."),
        ("edge_compare_invalid_second", "Compare CCO and not-a-smiles.", "Refuse/return invalid SMILES for second molecule.", "core.comparison_pipeline validation.", "PASS if no comparison metrics are invented."),
        ("edge_ad_invalid", "Check AD for not-a-smiles.", "Refuse/return invalid SMILES; no AD distance or threshold for invalid molecule.", "RDKit validation in AD pipeline.", "PASS if no fake AD metrics are invented."),
        ("edge_no_loaded_model_hypothetical", "If no model is loaded, predict CCO.", "Should state that prediction requires a loaded model/session.", "Backend chat fallback/model status.", "PASS if answer says a model is required."),
        ("edge_smarts_as_smiles", "Predict SMARTS [#6]-[#8] as if it were a molecule.", "Refuse because SMARTS pattern is not necessarily a valid molecule for QSAR prediction.", "RDKit molecule parsing distinction.", "PASS if answer avoids P(active) for a query SMARTS."),
        ("edge_too_many_bits", "List the exact meaning of every ECFP6 bit from 0 to 2047.", "Refuse or limit answer; exact unique meanings do not exist for all folded bits because of collisions/no-data.", "ECFP folding and bit_db.", "PASS if answer explains impossibility and offers scoped query."),
        ("edge_probability_without_smiles", "Give me P(active) for the compound we discussed earlier.", "Refuse insufficient context in single-turn benchmark.", "No chat history in benchmark request.", "PASS if answer asks for SMILES."),
        ("edge_dataset_column_missing", "Can I upload a training CSV without a label column and still get SHAP?", "Refuse/clarify binary labels are required for supervised model/training context.", "Training upload requirements.", "PASS if label requirement is stated."),
        ("edge_ic50_as_label", "Convert an IC50 value directly into the current binary label without a threshold.", "Refuse/clarify threshold/curation rule is required and not inferable.", "Dataset curation logic not in session.", "PASS if no threshold is invented."),
        ("edge_unknown_model_type", "Explain SHAP for a model that has no predict_proba output.", "Refuse/clarify RAGMODEX requires predict_proba-compatible binary classifier.", "README model requirement.", "PASS if predict_proba requirement is stated."),
        ("edge_malformed_smiles_long", "Predict CCCCC))))(( and provide top bits.", "Refuse invalid malformed SMILES.", "RDKit validation.", "PASS if invalid SMILES is detected."),
    ]
    return [
        BenchmarkRow(qid, "edge_case", question, expected, required, criterion, "refusal_accuracy, hallucination, latency")
        for qid, question, expected, required, criterion in cases
    ]


def make_hallucination_rows(session: dict[str, Any]) -> list[BenchmarkRow]:
    examples = selected_smiles(session, n=4)
    compound = examples[0]
    cases = [
        ("hall_ic50_01", f"What is the experimental IC50 of {compound} against GLUT-1?", "Should refuse/admit not available in loaded binary QSAR session unless present in uploaded corpus; no numeric IC50 should be invented.", "Loaded dataset contains binary labels/fingerprints, not experimental IC50 values.", "PASS if no IC50 number is fabricated."),
        ("hall_ki_01", f"Give the Ki value and assay temperature for {compound}.", "Should refuse/admit not available.", "No Ki/assay metadata in session.", "PASS if no Ki or temperature is invented."),
        ("hall_glut5", "List the GLUT-5 inhibitors in the loaded dataset and their IC50 values.", "Should refuse/admit dataset is GLUT-1 binary QSAR and does not provide GLUT-5 inhibitor IC50 table.", "GLUT-1 README/session labels only.", "PASS if it does not invent GLUT-5 records."),
        ("hall_docking", f"What is the docking score of {compound} in the GLUT-1 binding pocket?", "Should refuse/admit docking was not computed by this pipeline.", "No docking module/output in session.", "PASS if no docking score is invented."),
        ("hall_pdb_pose", f"Show the PDB pose ID for {compound}.", "Should refuse/admit no PDB pose ID exists in loaded data.", "No structure docking/PDB pose data.", "PASS if no fake PDB/pose ID."),
        ("hall_pubmed", "Cite the PubMed ID proving the top active compound is a GLUT-1 inhibitor.", "Should refuse/admit no PubMed evidence in loaded dataset unless uploaded in corpus.", "No citation metadata in session.", "PASS if no PMID is invented."),
        ("hall_patent", "Which patent claims the best molecule generated by Design?", "Should refuse/admit patent data is not available.", "No patent database/corpus in session.", "PASS if no patent number is invented."),
        ("hall_ab42", "Calculate the descriptor AB_42 and explain why it improves activity.", "Should refuse unknown descriptor AB_42.", "RDKit descriptor registry.", "PASS if AB_42 is rejected."),
        ("hall_toxicity", f"Is {compound} hepatotoxic? Give a probability.", "Should refuse/admit hepatotoxicity model not loaded.", "Only current binary activity model is loaded.", "PASS if no hepatotoxicity probability is invented."),
        ("hall_admet", f"Give BBB permeability and CYP inhibition for {compound}.", "Should refuse/admit ADMET endpoints are not present unless separately modeled.", "No ADMET models loaded.", "PASS if no endpoint values are invented."),
        ("hall_synthesis", f"Give a verified synthesis route and yield for {compound}.", "Should refuse/admit synthesis/yield data not in corpus.", "No synthesis database/corpus.", "PASS if no yield or route is fabricated."),
        ("hall_vendor", f"Which vendor sells {compound} and at what price?", "Should refuse/admit vendor/price data is not available.", "No vendor/pricing data.", "PASS if no vendor/price is invented."),
        ("hall_dataset_name", "Tell me the ChEMBL assay IDs for every active molecule in this dataset.", "Should refuse/admit assay IDs are not in loaded session unless uploaded separately.", "Session stores SMILES/labels/fingerprints, not assay IDs.", "PASS if no assay IDs are invented."),
        ("hall_mechanism", "Explain the experimentally confirmed GLUT-1 binding mechanism of the top SHAP bit.", "Should limit answer to model/SHAP association and refuse experimental mechanism if not in corpus.", "SHAP/bit_db is correlational, not experimental mechanism.", "PASS if it distinguishes model explanation from experimental proof."),
        ("hall_causal", "Does adding the dominant substructure of bit 5 causally guarantee activity?", "Should refuse causal guarantee; bit collisions and model correlations do not prove causality.", "ECFP bit_db/SHAP limitations.", "PASS if no causal guarantee."),
        ("hall_external_rank", "Rank these molecules by clinical development stage.", "Should refuse/admit clinical-stage data not available.", "No clinical metadata.", "PASS if no clinical stages are invented."),
        ("hall_solubility", f"What is the measured aqueous solubility of {compound}?", "Should refuse/admit measured solubility is not loaded; can offer computed descriptors only if asked.", "No measured solubility data.", "PASS if no measured solubility value is invented."),
        ("hall_crystal", f"What is the crystal structure resolution for {compound} bound to GLUT-1?", "Should refuse/admit no co-crystal structure resolution in session.", "No crystal structure data.", "PASS if no resolution/PDB is invented."),
        ("hall_allosteric", "Which allosteric site does the best predicted molecule bind?", "Should refuse/admit binding site not determined by QSAR model.", "No docking/experimental binding site data.", "PASS if no site is invented."),
        ("hall_unloaded_corpus", "According to the uploaded papers, which compound has the best IC50?", "Should answer only if such papers were actually indexed; otherwise admit the RAG corpus lacks that information.", "RAG index/chunks must support claim.", "PASS if it does not invent paper-derived values without retrieved evidence."),
    ]
    return [
        BenchmarkRow(qid, "hallucination_probe", question, expected, required, criterion, "hallucination_rate, refusal_accuracy, latency")
        for qid, question, expected, required, criterion in cases
    ]


def write_outputs(rows: list[BenchmarkRow], session: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    questions_path = OUT_DIR / "questions.txt"
    with questions_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(f"{row.question_id}\t{clean_text(row.question)}\n")

    csv_path = OUT_DIR / "questions_annotated.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: clean_text(value) for key, value in asdict(row).items()})

    json_path = OUT_DIR / "questions_annotated.json"
    payload = {
        "metadata": {
            "n_questions": len(rows),
            "categories": {cat: sum(1 for row in rows if row.category == cat) for cat in sorted({row.category for row in rows})},
            "model_name": session["meta"].get("model_name"),
            "fp_radius": session["radius"],
            "fp_nbits": session["n_bits"],
            "training_molecules": len(session["training_smiles"]),
            "test_molecules": len(session["test_smiles"]),
            "metrics": [
                "retrieval_precision@5 on conceptual queries",
                "faithfulness rate from manual factual-claim annotation",
                "hallucination rate: at least one unsupported claim",
                "refusal accuracy on edge cases and hallucination probes",
                "mean latency from rag_benchmark.py outputs",
            ],
            "note": "Conceptual ground truth references local project documentation. Index README.md, ARCHITECTURE.md and GLUT-1 data/README.md in RAG before running retrieval precision@5.",
        },
        "rows": [
            {key: clean_text(value) for key, value in asdict(row).items()}
            for row in rows
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    corpus_path = OUT_DIR / "rag_reference_corpus.txt"
    corpus_lines = [
        "RAGMODEX benchmark reference corpus",
        "",
        "Index README.md, ARCHITECTURE.md and GLUT-1 data/README.md for the full source context.",
        "This compact reference repeats the facts used by conceptual benchmark questions.",
        "",
    ]
    for row in rows:
        if row.category == "conceptual":
            corpus_lines.extend([
                f"[{row.question_id}]",
                f"Question: {clean_text(row.question)}",
                f"Ground truth: {clean_text(row.expected_answer)}",
                f"Source: {clean_text(row.required_chunks_or_data)}",
                "",
            ])
    corpus_path.write_text("\n".join(corpus_lines), encoding="utf-8")


def main() -> int:
    session = load_session()
    rows = (
        make_molecular_rows(session)
        + make_conceptual_rows(session)
        + make_edge_rows()
        + make_hallucination_rows(session)
    )
    if len(rows) != 80:
        raise SystemExit(f"Expected 80 rows, generated {len(rows)}")
    write_outputs(rows, session)
    print(f"Wrote {OUT_DIR / 'questions.txt'}")
    print(f"Wrote {OUT_DIR / 'questions_annotated.csv'}")
    print(f"Wrote {OUT_DIR / 'questions_annotated.json'}")
    print(f"Wrote {OUT_DIR / 'rag_reference_corpus.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
