"""Index local text/markdown files into the RAGMODEX RAG corpus.

Start the FastAPI backend first, then run for the benchmark corpus:

    python tools/index_rag_corpus.py benchmark_inputs/rag_reference_corpus.txt

Or index the broader project documentation:

    python tools/index_rag_corpus.py README.md ARCHITECTURE.md "GLUT-1 data/README.md"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import error, request


DEFAULT_API_BASE = "http://127.0.0.1:8000/api"


def post_json(api_base: str, path: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{api_base.rstrip('/')}/{path.lstrip('/')}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    return json.loads(raw or "{}")


def get_json(api_base: str, path: str, timeout: float) -> dict:
    req = request.Request(f"{api_base.rstrip('/')}/{path.lstrip('/')}", method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    return json.loads(raw or "{}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index text files into RAGMODEX RAG.")
    parser.add_argument("files", nargs="+", type=Path, help="Text/Markdown files to index.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for file_path in args.files:
        if not file_path.exists():
            print(f"Missing file: {file_path}", file=sys.stderr)
            return 2
        text = file_path.read_text(encoding="utf-8-sig")
        source = file_path.as_posix()
        print(f"Indexing {source} ({len(text)} chars)")
        post_json(args.api_base, "/rag/add-text", {"text": text, "source": source}, args.timeout)

    status = get_json(args.api_base, "/rag/status", args.timeout)
    print(f"RAG status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
