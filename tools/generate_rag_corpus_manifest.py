"""Generate a reproducible manifest for the RAGMODEX retrieval corpus.

The manifest is intentionally a source document, not an answer key: it records
the corpus files, hashes, chunking/embedding configuration, index composition,
redistribution policy, and saved-session metadata needed to interpret benchmark
queries about the loaded model and dataset.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAG_INDEX_DIR = ROOT / "data" / "rag_index"
SESSION_DIR = ROOT / "data" / "session"
OUT_DIR = ROOT / "benchmark_inputs"
DEFAULT_SOURCES = [
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "GLUT-1 data" / "README.md",
    OUT_DIR / "rag_session_snapshot.txt",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def source_info(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "characters": len(text),
        "redistributed": True,
        "license_or_status": "Project documentation distributed with RAGMODEX repository.",
    }


def build_payload() -> dict[str, Any]:
    chunks = load_json(RAG_INDEX_DIR / "chunks.json", [])
    index_metadata = load_json(RAG_INDEX_DIR / "metadata.json", {})
    session_metadata = load_json(SESSION_DIR / "meta.json", {})
    source_counts = Counter(str(chunk.get("source", "")) for chunk in chunks)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": (
            "Frozen retrieval-corpus manifest for the RAGMODEX factuality and "
            "hallucination benchmark."
        ),
        "retrieval_configuration": {
            "chunk_size_characters": 500,
            "chunk_overlap_characters": 50,
            "minimum_chunk_size_characters": 100,
            "embedding_model": index_metadata.get("embedding_model", "all-MiniLM-L6-v2"),
            "vector_index": "FAISS IndexFlatIP over normalized embeddings",
            "similarity": "inner product equivalent to cosine similarity for normalized embeddings",
            "default_top_k": 5,
        },
        "indexed_corpus_snapshot": {
            "num_chunks": index_metadata.get("num_chunks", len(chunks)),
            "chunks_by_source": dict(sorted(source_counts.items())),
        },
        "source_documents": [
            source_info(path)
            for path in DEFAULT_SOURCES
            if path.exists()
        ],
        "saved_session_snapshot": {
            "model_name": session_metadata.get("model_name"),
            "fingerprint": {
                "type": "Morgan/ECFP",
                "radius": session_metadata.get("fp_radius"),
                "nbits": session_metadata.get("fp_nbits"),
            },
            "training_molecules": session_metadata.get("n_molecules"),
            "test_molecules": session_metadata.get("n_test"),
            "manual_save": session_metadata.get("manual_save"),
            "saved_at": session_metadata.get("saved_at"),
            "session_files": [
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                    "redistributed": False,
                    "reason": "Model/session artifact; used to regenerate benchmark ground truth but not redistributed as literature corpus.",
                }
                for path in [
                    SESSION_DIR / "meta.json",
                    SESSION_DIR / "model.bin",
                    SESSION_DIR / "training.npz",
                    SESSION_DIR / "test.npz",
                    SESSION_DIR / "bit_db.pkl",
                ]
                if path.exists()
            ],
        },
        "update_policy": (
            "The benchmark corpus is frozen for each reported run. Any change to "
            "source documents, chunking, embedding model, or saved session requires "
            "rebuilding the index, regenerating this manifest, and rerunning the "
            "benchmark with a new run identifier."
        ),
        "redistribution_policy": (
            "Only project documentation and generated manifests are redistributed. "
            "If external copyrighted papers are indexed, RAGMODEX should distribute "
            "only bibliographic identifiers, hashes, and rebuild scripts unless "
            "redistribution rights are available."
        ),
    }


def write_session_snapshot(path: Path) -> None:
    session_metadata = load_json(SESSION_DIR / "meta.json", {})
    lines = [
        "RAGMODEX saved session snapshot",
        "",
        "This source document records the frozen model/session metadata used by the RAG factuality benchmark.",
        "",
        f"model_name: {session_metadata.get('model_name')}",
        "fingerprint_type: Morgan/ECFP",
        f"fingerprint_radius: {session_metadata.get('fp_radius')}",
        f"fingerprint_nbits: {session_metadata.get('fp_nbits')}",
        f"training_molecules: {session_metadata.get('n_molecules')}",
        f"test_molecules: {session_metadata.get('n_test')}",
        f"manual_save: {session_metadata.get('manual_save')}",
        f"saved_at: {session_metadata.get('saved_at')}",
        "",
        "The saved session artifacts are used to regenerate deterministic benchmark ground truth for molecular predictions, SHAP attributions, fingerprint-bit context, and applicability-domain values.",
        "These session artifacts are not treated as redistributed literature-corpus documents.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_text_manifest(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "RAGMODEX retrieval corpus manifest",
        "",
        f"Generated UTC: {payload['generated_at_utc']}",
        "",
        "Retrieval configuration:",
    ]
    for key, value in payload["retrieval_configuration"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "Indexed corpus snapshot:"])
    snapshot = payload["indexed_corpus_snapshot"]
    lines.append(f"- num_chunks: {snapshot['num_chunks']}")
    for source, count in snapshot["chunks_by_source"].items():
        lines.append(f"- chunks from {source}: {count}")

    lines.extend(["", "Source documents:"])
    for doc in payload["source_documents"]:
        lines.append(
            f"- {doc['path']}: sha256={doc['sha256']}; bytes={doc['bytes']}; "
            f"characters={doc['characters']}; redistributed={doc['redistributed']}"
        )

    session = payload["saved_session_snapshot"]
    lines.extend([
        "",
        "Saved RAGMODEX session snapshot:",
        f"- model_name: {session['model_name']}",
        f"- fingerprint: {session['fingerprint']['type']} radius={session['fingerprint']['radius']} nbits={session['fingerprint']['nbits']}",
        f"- training_molecules: {session['training_molecules']}",
        f"- test_molecules: {session['test_molecules']}",
        f"- manual_save: {session['manual_save']}",
        f"- saved_at: {session['saved_at']}",
        "",
        "Session artifact hashes:",
    ])
    for item in session["session_files"]:
        lines.append(f"- {item['path']}: sha256={item['sha256']}; bytes={item['bytes']}; redistributed={item['redistributed']}")

    lines.extend([
        "",
        f"Update policy: {payload['update_policy']}",
        "",
        f"Redistribution policy: {payload['redistribution_policy']}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_session_snapshot(OUT_DIR / "rag_session_snapshot.txt")
    payload = build_payload()
    json_path = OUT_DIR / "rag_corpus_manifest.json"
    text_path = OUT_DIR / "rag_corpus_manifest.txt"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_text_manifest(text_path, payload)
    print(f"Wrote {json_path}")
    print(f"Wrote {text_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
