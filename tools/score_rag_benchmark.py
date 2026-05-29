"""Score RAGMODEX RAG benchmark outputs.

The scorer combines deterministic checks for molecular/pipeline questions with
conservative refusal and hallucination checks for edge-case probes. It is meant
to turn tools/rag_benchmark.py JSONL outputs into aggregate tables suitable for
supplementary material.

Example:
    python tools/score_rag_benchmark.py benchmark_outputs/run.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANNOTATIONS = ROOT / "benchmark_inputs" / "questions_annotated.json"

REFUSAL_TERMS = [
    "not available",
    "unavailable",
    "not in",
    "not present",
    "not provided",
    "not loaded",
    "not computed",
    "not supported",
    "unsupported",
    "cannot",
    "can't",
    "could not",
    "invalid",
    "out of range",
    "requires",
    "required",
    "insufficient",
    "no evidence",
    "no data",
    "do not have",
    "don't have",
    "provide a valid",
    "need a valid",
    "not enough information",
    "unknown",
]

ASSERTIVE_CLAIM_PATTERNS = [
    r"\bIC50\b\s*(?:is|=|:)?\s*[-+]?\d+(?:\.\d+)?\s*(?:nM|uM|µM|mM)\b",
    r"\bK[di]\b\s*(?:is|=|:)?\s*[-+]?\d+(?:\.\d+)?\s*(?:nM|uM|µM|mM)\b",
    r"\bdocking score\b\s*(?:is|=|:)?\s*[-+]?\d+(?:\.\d+)?",
    r"\bPMID\s*:?\s*\d{5,}\b",
    r"\bPDB\s*(?:ID|pose)?\s*:?\s*[0-9][A-Za-z0-9]{3}\b",
    r"\bUS\s*\d{4,}[A-Z0-9]*\b",
    r"\bpatent\s*(?:number|no\.?|#)?\s*[A-Z]{0,3}\d{4,}\b",
    r"\$\s*\d+(?:\.\d+)?",
    r"\b\d+(?:\.\d+)?\s*%\s*(?:hepatotoxic|BBB|CYP|inhibition|permeability)\b",
    r"\byield\b\s*(?:is|=|:)?\s*\d+(?:\.\d+)?\s*%",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_annotations(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["question_id"]: row for row in payload["rows"]}


def norm(text: Any) -> str:
    return str(text or "").lower()


def expected_float(expected: str, name: str) -> float | None:
    match = re.search(rf"{re.escape(name)}=([-+]?\d+(?:\.\d+)?)", expected)
    return float(match.group(1)) if match else None


def expected_prediction(expected: str) -> str | None:
    match = re.search(r"prediction=(Active|Inactive)", expected, re.I)
    return match.group(1).lower() if match else None


def expected_bits(expected: str) -> list[str]:
    return sorted(set(re.findall(r"ECFP6_\d+", expected)), key=lambda x: int(x.split("_")[1]))


def expected_shap(expected: str) -> float | None:
    match = re.search(r"\bshap=([-+]?\d+(?:\.\d+)?)", expected)
    return float(match.group(1)) if match else None


def all_numbers(answer: str) -> list[float]:
    values = []
    for raw in re.findall(r"[-+]?\d+(?:\.\d+)?", answer):
        try:
            values.append(float(raw))
        except ValueError:
            pass
    return values


def has_number_near(answer: str, target: float | None, tolerance: float) -> bool:
    if target is None:
        return True
    for value in all_numbers(answer):
        candidates = [value]
        if 1.0 < abs(value) <= 100.0:
            candidates.append(value / 100.0)
        if any(math.isclose(candidate, target, abs_tol=tolerance) for candidate in candidates):
            return True
    return False


def has_refusal(answer: str) -> bool:
    text = norm(answer)
    return any(term in text for term in REFUSAL_TERMS)


def has_assertive_unsupported_claim(answer: str) -> bool:
    return any(re.search(pattern, answer, re.I) for pattern in ASSERTIVE_CLAIM_PATTERNS)


def score_retrieval(row: dict[str, Any], annotation: dict[str, Any]) -> tuple[float | None, int, int]:
    if row.get("condition") != "rag-on":
        return None, 0, 0
    chunks = row.get("retrieved_chunks") or []
    required = annotation.get("required_chunks_or_data", "")
    source_hints = set(re.findall(r"[\w .\\/-]+\.(?:md|py|json|npz|pkl|bin)", required, flags=re.I))
    source_hints |= {hint.replace("\\", "/") for hint in source_hints}
    if not source_hints:
        return None, 0, len(chunks)
    hits = 0
    for chunk in chunks[:5]:
        source = str(chunk.get("source", "")).replace("\\", "/")
        if any(hint.replace("\\", "/") in source or Path(hint).name in source for hint in source_hints):
            hits += 1
    return hits / 5.0, hits, min(5, len(chunks))


CONCEPT_RULES: dict[str, list[str]] = {
    "concept_ecfp6": [r"morgan|ecfp", r"radius\s*=?\s*3|ecfp6", r"2048"],
    "concept_shap": [r"positive|>\s*0", r"active", r"negative|<\s*0", r"inactive"],
    "concept_collision": [r"collision|collided|fold", r"multiple|distinct", r"substructure"],
    "concept_dataset_summary": [r"1016", r"335", r"active", r"inactive"],
    "concept_bit_database": [r"observed|bits", r"ambiguous|collision", r"active ratio|frequency"],
    "concept_ad": [r"jaccard", r"k\s*-?\s*nn|nearest", r"mean.*2.*std|threshold"],
    "concept_maccs": [r"166", r"not.*predictive|not.*model|ecfp"],
    "concept_rag_grounding": [r"computed|pipeline|injected", r"prediction|shap|fingerprint|ad"],
    "concept_top_bits": [r"absolute|abs", r"shap"],
    "concept_design": [r"beam", r"diversity|mmr", r"applicability|ad"],
    "concept_descriptor": [r"logp|molwt|tpsa|donor|acceptor|rotatable"],
    "concept_model_requirement": [r"scikit", r"predict_proba"],
    "concept_training_upload": [r"smiles", r"binary|label"],
    "concept_retrieval_metrics": [r"top\s*-?\s*5|precision@5", r"relevant|required"],
    "concept_tanimoto": [r"tanimoto", r"jaccard", r"fingerprint"],
    "concept_expected_value": [r"baseline|reference", r"shap"],
    "concept_active_bits": [r"active bits|on bits", r"top.*shap|attribution"],
    "concept_collision_confidence": [r"dominance|dominant", r"80|50|high|moderate|low"],
    "concept_llm_backend": [r"does not|no|independent", r"provider|llm", r"prediction|probabilit"],
    "concept_loaded_model": [r"best_model\.pkl", r"radius\s*=?\s*3", r"2048"],
}


def score_conceptual(question_id: str, answer: str) -> tuple[bool, dict[str, Any]]:
    rules = CONCEPT_RULES.get(question_id, [])
    hits = [bool(re.search(rule, answer, re.I)) for rule in rules]
    return bool(rules) and all(hits), {"rule_hits": sum(hits), "rule_total": len(rules)}


def score_molecular(question_id: str, answer: str, expected: str) -> tuple[bool, dict[str, Any]]:
    answer_lower = norm(answer)
    bits = expected_bits(expected)
    matched_bits = sum(1 for bit in bits[:3] if bit.lower() in answer_lower)

    if question_id.startswith("mol_predict_"):
        p_active = has_number_near(answer, expected_float(expected, "P(active)"), 0.01)
        p_inactive = has_number_near(answer, expected_float(expected, "P(inactive)"), 0.01)
        prediction = expected_prediction(expected)
        label_ok = prediction is None or prediction in answer_lower
        passed = p_active and p_inactive and label_ok and matched_bits >= 2
        return passed, {
            "p_active_ok": p_active,
            "p_inactive_ok": p_inactive,
            "label_ok": label_ok,
            "matched_bits": matched_bits,
        }

    if question_id.startswith("mol_bit_in_molecule_"):
        bit_ok = bool(bits and bits[0].lower() in answer_lower)
        on_match = re.search(r"bit_on=(\d)", expected)
        if on_match and on_match.group(1) == "1":
            state_ok = bool(re.search(r"\bon\b|active|present|activated", answer, re.I))
        else:
            state_ok = bool(re.search(r"\boff\b|inactive|absent|not activated", answer, re.I))
        shap_ok = has_number_near(answer, expected_shap(expected), 0.005)
        passed = bit_ok and state_ok and shap_ok
        return passed, {"bit_ok": bit_ok, "state_ok": state_ok, "shap_ok": shap_ok}

    if question_id.startswith("mol_global_bit_"):
        bit_ok = bool(bits and bits[0].lower() in answer_lower)
        no_data = "never activated" in expected.lower() or "no substructure" in expected.lower()
        if no_data:
            context_ok = bool(re.search(r"never|no data|not observed|not activated", answer, re.I))
        else:
            dominant = re.search(r"dominant_substructure=([^;]+)", expected)
            active_ratio = expected_float(expected, "active_ratio")
            context_ok = (
                (dominant and dominant.group(1).strip().lower() in answer_lower)
                or has_number_near(answer, active_ratio, 0.03)
            )
        return bit_ok and bool(context_ok), {"bit_ok": bit_ok, "context_ok": bool(context_ok)}

    if question_id.startswith("mol_compare_"):
        probabilities = re.findall(r"P\(active\)=([-+]?\d+(?:\.\d+)?)", expected)
        prob_hits = sum(1 for value in probabilities if has_number_near(answer, float(value), 0.01))
        tanimoto_ok = has_number_near(answer, expected_float(expected, "tanimoto"), 0.03)
        passed = prob_hits >= 2 and tanimoto_ok and matched_bits >= 2
        return passed, {"prob_hits": prob_hits, "tanimoto_ok": tanimoto_ok, "matched_bits": matched_bits}

    if question_id.startswith("mol_ad_"):
        inside = re.search(r"inside_ad=(True|False)", expected)
        if inside:
            inside_text = inside.group(1).lower()
            inside_ok = (
                ("inside" in answer_lower and inside_text == "true")
                or ("outside" in answer_lower and inside_text == "false")
                or (inside_text in answer_lower)
            )
        else:
            inside_ok = True
        dist_ok = has_number_near(answer, expected_float(expected, "mean_knn_distance"), 0.02)
        threshold_ok = has_number_near(answer, expected_float(expected, "ad_threshold"), 0.02)
        return inside_ok and dist_ok and threshold_ok, {
            "inside_ok": inside_ok,
            "distance_ok": dist_ok,
            "threshold_ok": threshold_ok,
        }

    return matched_bits > 0, {"matched_bits": matched_bits}


def score_edge_or_hallucination(question_id: str, answer: str, category: str) -> tuple[bool, bool, dict[str, Any]]:
    refusal = has_refusal(answer)
    unsupported = has_assertive_unsupported_claim(answer)

    text = norm(answer)
    if question_id.startswith("edge_bit_out_of_range") or question_id.startswith("edge_maccs_167"):
        refusal = refusal or "2048" in text or "0-2047" in text or "1-166" in text
    if question_id.startswith("edge_maccs_zero"):
        refusal = refusal or "unused" in text
    if question_id.startswith("hall_causal"):
        refusal = refusal or "does not prove" in text or "correlation" in text or "not caus" in text
    if question_id.startswith("hall_mechanism"):
        refusal = refusal or "model" in text and "experiment" in text

    passed = refusal and not unsupported
    hallucinated = category == "hallucination_probe" and unsupported
    return passed, hallucinated, {"refusal": refusal, "unsupported_assertive_claim": unsupported}


def score_row(row: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    answer = str(row.get("answer", ""))
    category = annotation["category"]
    details: dict[str, Any] = {}
    hallucinated = False

    if row.get("error"):
        passed = False
        details["error"] = row.get("error")
    elif category == "molecular":
        passed, details = score_molecular(annotation["question_id"], answer, annotation["expected_answer"])
        hallucinated = not passed and has_assertive_unsupported_claim(answer)
    elif category == "conceptual":
        passed, details = score_conceptual(annotation["question_id"], answer)
        hallucinated = not passed and has_assertive_unsupported_claim(answer)
    elif category in {"edge_case", "hallucination_probe"}:
        passed, hallucinated, details = score_edge_or_hallucination(annotation["question_id"], answer, category)
    else:
        passed = False
        details["unknown_category"] = category

    retrieval_p5, retrieval_hits, retrieval_n = score_retrieval(row, annotation)
    return {
        **row,
        "category": category,
        "expected_answer": annotation["expected_answer"],
        "pass_fail_criterion": annotation["pass_fail_criterion"],
        "auto_pass": passed,
        "hallucinated": hallucinated,
        "retrieval_precision_at_5": retrieval_p5,
        "retrieval_hits": retrieval_hits,
        "retrieval_evaluated_chunks": retrieval_n,
        "score_details": details,
    }


def aggregate(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        key = (row["provider"], row["model"], row["condition"], row["category"])
        groups[key].append(row)

    summary: list[dict[str, Any]] = []
    for (provider, model, condition, category), rows in sorted(groups.items()):
        latencies = [float(row["latency_sec"]) for row in rows if row.get("latency_sec") not in ("", None)]
        retrieval_values = [
            float(row["retrieval_precision_at_5"])
            for row in rows
            if row.get("retrieval_precision_at_5") is not None
        ]
        summary.append({
            "provider": provider,
            "model": model,
            "condition": condition,
            "category": category,
            "n": len(rows),
            "auto_pass_n": sum(1 for row in rows if row["auto_pass"]),
            "auto_accuracy": sum(1 for row in rows if row["auto_pass"]) / len(rows),
            "hallucination_n": sum(1 for row in rows if row["hallucinated"]),
            "hallucination_rate": sum(1 for row in rows if row["hallucinated"]) / len(rows),
            "mean_latency_sec": mean(latencies) if latencies else "",
            "median_latency_sec": median(latencies) if latencies else "",
            "retrieval_precision_at_5": mean(retrieval_values) if retrieval_values else "",
        })

    total_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        total_groups[(row["provider"], row["model"], row["condition"])].append(row)

    for (provider, model, condition), rows in sorted(total_groups.items()):
        latencies = [float(row["latency_sec"]) for row in rows if row.get("latency_sec") not in ("", None)]
        retrieval_values = [
            float(row["retrieval_precision_at_5"])
            for row in rows
            if row.get("retrieval_precision_at_5") is not None
        ]
        summary.append({
            "provider": provider,
            "model": model,
            "condition": condition,
            "category": "ALL",
            "n": len(rows),
            "auto_pass_n": sum(1 for row in rows if row["auto_pass"]),
            "auto_accuracy": sum(1 for row in rows if row["auto_pass"]) / len(rows),
            "hallucination_n": sum(1 for row in rows if row["hallucinated"]),
            "hallucination_rate": sum(1 for row in rows if row["hallucinated"]) / len(rows),
            "mean_latency_sec": mean(latencies) if latencies else "",
            "median_latency_sec": median(latencies) if latencies else "",
            "retrieval_precision_at_5": mean(retrieval_values) if retrieval_values else "",
        })

    return summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "question_id",
        "provider",
        "model",
        "condition",
        "category",
        "auto_pass",
        "hallucinated",
        "latency_sec",
        "retrieval_precision_at_5",
        "retrieval_hits",
        "retrieval_evaluated_chunks",
        "question",
        "answer",
        "expected_answer",
        "pass_fail_criterion",
        "score_details",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["score_details"] = json.dumps(out.get("score_details", {}), ensure_ascii=False)
            writer.writerow(out)


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "provider",
        "model",
        "condition",
        "category",
        "n",
        "auto_pass_n",
        "auto_accuracy",
        "hallucination_n",
        "hallucination_rate",
        "mean_latency_sec",
        "median_latency_sec",
        "retrieval_precision_at_5",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt(value: Any) -> str:
    if value == "" or value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_markdown(path: Path, summary: list[dict[str, Any]], scored: list[dict[str, Any]]) -> None:
    lines = [
        "# RAGMODEX RAG Benchmark Scoring",
        "",
        "## Aggregate Metrics",
        "",
        "| Provider | Model | Condition | Category | N | Pass | Accuracy | Hallucinations | Hallucination rate | Retrieval P@5 | Median latency (s) |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['provider']} | {row['model']} | {row['condition']} | {row['category']} | "
            f"{row['n']} | {row['auto_pass_n']} | {fmt(row['auto_accuracy'])} | "
            f"{row['hallucination_n']} | {fmt(row['hallucination_rate'])} | "
            f"{fmt(row['retrieval_precision_at_5'])} | {fmt(row['median_latency_sec'])} |"
        )

    failures = [row for row in scored if not row["auto_pass"]]
    lines.extend([
        "",
        "## Auto-Scored Failures",
        "",
    ])
    if not failures:
        lines.append("No automatic failures.")
    for row in failures[:40]:
        details = json.dumps(row.get("score_details", {}), ensure_ascii=False)
        lines.extend([
            f"### {row['question_id']} - {row['condition']}",
            "",
            f"- Category: {row['category']}",
            f"- Hallucinated: {row['hallucinated']}",
            f"- Details: `{details}`",
            f"- Question: {row['question']}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score RAGMODEX RAG benchmark JSONL output.")
    parser.add_argument("jsonl", type=Path, help="Output JSONL from tools/rag_benchmark.py")
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--out-dir", type=Path, default=Path("benchmark_outputs"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    annotations = load_annotations(args.annotations)
    rows = read_jsonl(args.jsonl)
    if not rows:
        raise SystemExit(f"No rows found in {args.jsonl}")

    scored = []
    missing = []
    for row in rows:
        question_id = row.get("question_id")
        annotation = annotations.get(question_id)
        if annotation is None:
            missing.append(question_id)
            continue
        scored.append(score_row(row, annotation))

    if missing:
        raise SystemExit(f"Missing annotations for: {', '.join(map(str, sorted(set(missing))))}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.jsonl.stem
    scored_path = args.out_dir / f"{stem}_scored.csv"
    summary_path = args.out_dir / f"{stem}_summary.csv"
    report_path = args.out_dir / f"{stem}_score_report.md"

    summary = aggregate(scored)
    write_csv(scored_path, scored)
    write_summary_csv(summary_path, summary)
    write_markdown(report_path, summary, scored)

    print(f"Scored rows: {len(scored)}")
    print(f"Scored CSV: {scored_path}")
    print(f"Summary CSV: {summary_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
