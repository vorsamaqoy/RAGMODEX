"""Run a head-to-head RAG benchmark against the RAGMODEX API.

Input: a UTF-8 .txt file with one question per line.
Output: JSONL with every response, CSV with a compact table, and a Markdown
report that is easy to inspect manually.

Example:
    python tools/rag_benchmark.py questions.txt --provider groq \
        --models llama-3.3-70b-versatile llama-3.1-8b-instant qwen/qwen3-32b
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request


DEFAULT_API_BASE = "http://127.0.0.1:8000/api"
DEFAULT_MODELS = ["llama-3.3-70b-versatile"]
SMILES_TOKEN = r"[A-Za-z0-9@+\-\[\]\\/#%().=]+"


@dataclass(frozen=True)
class Question:
    index: int
    question_id: str
    text: str


def read_questions(path: Path) -> list[Question]:
    questions: list[Question] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # Optional compact IDs are accepted as "id<TAB>question".
            if "\t" in line:
                maybe_id, text = line.split("\t", 1)
                question_id = maybe_id.strip() or f"q{len(questions) + 1:03d}"
                text = text.strip()
            else:
                question_id = f"q{len(questions) + 1:03d}"
                text = line

            if text:
                questions.append(Question(len(questions) + 1, question_id, text))

    if not questions:
        raise SystemExit(f"No questions found in {path}")
    return questions


class ApiClient:
    def __init__(self, api_base: str, timeout: float):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.api_base}/{path.lstrip('/')}"

    def get_json(self, path: str) -> dict[str, Any]:
        req = request.Request(self._url(path), method="GET")
        return self._request_json(req)

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._url(path),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._request_json(req)

    def post_form(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = parse.urlencode(payload).encode("utf-8")
        req = request.Request(
            self._url(path),
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        return self._request_json(req)

    def _request_json(self, req: request.Request) -> dict[str, Any]:
        try:
            with request.urlopen(req, timeout=self.timeout) as res:
                raw = res.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} for {req.full_url}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach {req.full_url}: {exc}") from exc

        if not raw:
            return {}
        return json.loads(raw)


def configure_model(
    client: ApiClient,
    provider: str,
    model: str,
    temperature: float,
    api_key: str | None,
    local_endpoint: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "temperature": str(temperature),
        "persist_api_key": "false",
        "local_endpoint": local_endpoint,
    }
    if api_key:
        payload["api_key"] = api_key
    return client.post_form("/model/config", payload)


def retrieve_chunks(client: ApiClient, question: str, top_k: int) -> dict[str, Any] | None:
    try:
        return client.post_json("/rag/retrieve", {"query": question, "top_k": top_k})
    except Exception as exc:
        return {"error": str(exc), "chunks": []}


def extract_smiles_from_question(question: str) -> str | None:
    patterns = [
        rf"\bPredict\s+({SMILES_TOKEN})",
        rf"\bFor molecule\s+({SMILES_TOKEN})",
        rf"\bCompare\s+({SMILES_TOKEN})\s+and\s+{SMILES_TOKEN}",
        rf"\bfor\s+({SMILES_TOKEN}):",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if not match:
            continue
        smiles = match.group(1).strip().rstrip(",:;")
        if smiles.endswith("."):
            smiles = smiles[:-1]
        if smiles:
            return smiles
    return None


def ask_chat(
    client: ApiClient,
    question: Question,
    use_rag: bool,
) -> tuple[str, float, str | None, str | None, bool]:
    started = time.perf_counter()
    smiles = extract_smiles_from_question(question.text) if question.question_id.startswith("mol_") else None
    path = "/chat/with-pipeline" if smiles and use_rag else "/chat/simple"
    payload = {"message": question.text, "use_rag": use_rag}
    if smiles and use_rag:
        payload["smiles"] = smiles

    try:
        data = client.post_json(path, payload)
        latency = time.perf_counter() - started
        injected = bool(data.get("pipeline_injected")) if smiles and use_rag else False
        return str(data.get("response", "")), latency, None, smiles, injected
    except Exception as exc:
        latency = time.perf_counter() - started
        return "", latency, str(exc), smiles, False


def safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "timestamp",
        "question_id",
        "question_index",
        "provider",
        "model",
        "condition",
        "use_rag",
        "latency_sec",
        "error",
        "question",
        "answer",
        "retrieved_sources",
        "retrieved_chunk_count",
        "pipeline_smiles",
        "pipeline_injected",
        "manual_category",
        "expected_answer",
        "required_chunks_or_data",
        "pass_fail",
        "annotator_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(path: Path, rows: list[dict[str, Any]], summary: list[dict[str, Any]]) -> None:
    lines = [
        "# RAGMODEX RAG Benchmark",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Summary",
        "",
        "| Provider | Model | Condition | N | Errors | Mean latency (s) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in summary:
        lines.append(
            f"| {item['provider']} | {item['model']} | {item['condition']} | "
            f"{item['n']} | {item['errors']} | {item['mean_latency_sec']:.3f} |"
        )

    lines.extend([
        "",
        "## Annotation Columns",
        "",
        "Use the CSV columns `manual_category`, `expected_answer`, "
        "`required_chunks_or_data`, `pass_fail`, and `annotator_notes` for manual scoring.",
        "",
        "Suggested categories: molecular, conceptual, edge_case, hallucination_probe.",
        "",
        "## Responses",
        "",
    ])

    for row in rows:
        lines.extend([
            f"### {row['question_id']} - {row['model']} - {row['condition']}",
            "",
            f"**Question:** {row['question']}",
            "",
            f"**Latency:** {row['latency_sec']:.3f}s",
            "",
        ])
        if row.get("error"):
            lines.extend(["**Error:**", "", f"```text\n{row['error']}\n```", ""])
        lines.extend(["**Answer:**", "", f"```text\n{row['answer']}\n```", ""])
        chunks = row.get("retrieved_chunks") or []
        if chunks:
            lines.append("**Retrieved chunks:**")
            lines.append("")
            for chunk in chunks:
                text = str(chunk.get("text", "")).replace("\n", " ")
                preview = text[:500] + ("..." if len(text) > 500 else "")
                lines.append(
                    f"- rank {chunk.get('rank')} | score {chunk.get('score'):.4f} | "
                    f"{chunk.get('source')} | chunk {chunk.get('chunk_index')}: {preview}"
                )
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["provider"], row["model"], row["condition"])
        grouped.setdefault(key, []).append(row)

    summary = []
    for (provider, model, condition), items in sorted(grouped.items()):
        latencies = [float(item["latency_sec"]) for item in items]
        summary.append({
            "provider": provider,
            "model": model,
            "condition": condition,
            "n": len(items),
            "errors": sum(1 for item in items if item.get("error")),
            "mean_latency_sec": sum(latencies) / len(latencies) if latencies else 0.0,
        })
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark RAGMODEX chat with and without RAG.")
    parser.add_argument("questions", type=Path, help="UTF-8 .txt file, one question per line.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help=f"Default: {DEFAULT_API_BASE}")
    parser.add_argument("--provider", default="groq", help="LLM provider to configure before running.")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="One or more model names.")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--api-key", default=None, help="Optional provider API key for this run only.")
    parser.add_argument("--local-endpoint", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--conditions",
        choices=["both", "rag-on", "rag-off"],
        default="both",
        help="Run RAG-on, RAG-off, or both. Default: both.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Chunks to save for RAG-on rows.")
    parser.add_argument("--delay", type=float, default=0.0, help="Seconds to wait between calls.")
    parser.add_argument("--timeout", type=float, default=180.0, help="Per-request timeout in seconds.")
    parser.add_argument("--out-dir", type=Path, default=Path("benchmark_outputs"))
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    questions = read_questions(args.questions)
    client = ApiClient(args.api_base, args.timeout)

    run_id = args.run_id or datetime.now().strftime("rag_benchmark_%Y%m%d_%H%M%S")
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.conditions == "both":
        conditions = [("rag-on", True), ("rag-off", False)]
    elif args.conditions == "rag-on":
        conditions = [("rag-on", True)]
    else:
        conditions = [("rag-off", False)]

    try:
        health = client.get_json("/health")
        print(f"Connected to RAGMODEX API: {health}")
    except Exception as exc:
        print(f"ERROR: backend not reachable at {args.api_base}: {exc}", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    total_calls = len(args.models) * len(questions) * len(conditions)
    call_index = 0

    for model in args.models:
        print(f"\nConfiguring {args.provider}/{model} ...")
        try:
            configure_model(
                client=client,
                provider=args.provider,
                model=model,
                temperature=args.temperature,
                api_key=args.api_key,
                local_endpoint=args.local_endpoint,
            )
        except Exception as exc:
            print(f"ERROR: could not configure {args.provider}/{model}: {exc}", file=sys.stderr)
            return 3

        for question in questions:
            retrieval = retrieve_chunks(client, question.text, args.top_k)
            chunks = retrieval.get("chunks", []) if isinstance(retrieval, dict) else []
            sources = sorted({str(chunk.get("source", "")) for chunk in chunks if chunk.get("source")})

            for condition, use_rag in conditions:
                call_index += 1
                print(f"[{call_index}/{total_calls}] {model} {condition} {question.question_id}")
                answer, latency, err, pipeline_smiles, pipeline_injected = ask_chat(client, question, use_rag)
                row = {
                    "run_id": run_id,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "question_id": question.question_id,
                    "question_index": question.index,
                    "provider": args.provider,
                    "model": model,
                    "condition": condition,
                    "use_rag": use_rag,
                    "latency_sec": round(latency, 4),
                    "error": err or "",
                    "question": question.text,
                    "answer": answer,
                    "retrieved_sources": "; ".join(sources) if use_rag else "",
                    "retrieved_chunk_count": len(chunks) if use_rag else 0,
                    "pipeline_smiles": pipeline_smiles or "",
                    "pipeline_injected": "true" if pipeline_injected else "false",
                    "retrieved_chunks": chunks if use_rag else [],
                    "manual_category": "",
                    "expected_answer": "",
                    "required_chunks_or_data": "",
                    "pass_fail": "",
                    "annotator_notes": "",
                }
                rows.append(row)
                if args.delay:
                    time.sleep(args.delay)

    summary = summarize(rows)
    base = out_dir / safe_slug(run_id)
    jsonl_path = base.with_suffix(".jsonl")
    csv_path = base.with_suffix(".csv")
    md_path = base.with_suffix(".md")

    write_jsonl(jsonl_path, rows)
    write_csv(csv_path, rows)
    write_markdown(md_path, rows, summary)

    print("\nDone.")
    print(f"JSONL: {jsonl_path}")
    print(f"CSV:   {csv_path}")
    print(f"MD:    {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
