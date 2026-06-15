"""RAG document management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.state import app_state
from config.settings import settings
from rag.retriever import Retriever

router = APIRouter()


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5


def _rag_payload(retriever: Retriever | None = None, has_saved_index: bool | None = None) -> dict:
    docs = retriever.list_documents() if retriever is not None else []
    n_chunks = retriever.num_chunks if retriever is not None else 0
    saved = has_saved_index
    if saved is None:
        saved = settings.rag_index_dir.exists() and any(settings.rag_index_dir.iterdir())
    return {
        "ready": retriever is not None and n_chunks > 0,
        "n_docs": n_chunks,
        "n_chunks": n_chunks,
        "n_documents": len(docs),
        "documents": docs,
        "has_saved_index": bool(saved),
    }


def _ensure_retriever() -> Retriever:
    if app_state.retriever is None:
        retriever = Retriever(
            embedding_model=settings.embedding_model,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            top_k=settings.top_k_results,
        )
        if settings.rag_index_dir.exists() and any(settings.rag_index_dir.iterdir()):
            retriever.load(str(settings.rag_index_dir))
        app_state.retriever = retriever
    return app_state.retriever


@router.post("/add-text")
async def add_text(body: dict):
    """Add raw text to the RAG index."""
    text = body.get("text", "")
    source = str(body.get("source") or "document")
    if not text.strip():
        raise HTTPException(status_code=422, detail="Empty text.")
    try:
        retriever = _ensure_retriever()
        doc_id = f"text-{uuid4().hex}"
        metadata = {
            "doc_id": doc_id,
            "filename": source,
            "extension": "text",
            "size_bytes": len(text.encode("utf-8")),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        chunks = retriever.add_document(text, source=source, metadata=metadata)
        retriever.save(str(settings.rag_index_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "document": retriever.list_documents()[0], "chunks": chunks}


@router.post("/add-pdf")
async def add_pdf(file: UploadFile = File(...)):
    """Upload and index a PDF, TXT, or Markdown file."""
    raw = await file.read()
    original_name = Path(file.filename or "document").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".pdf", ".txt", ".md", ".rst"}:
        raise HTTPException(status_code=422, detail="Supported formats: PDF, TXT, MD, RST.")
    doc_id = f"doc-{uuid4().hex}"
    upload_name = f"{doc_id}{suffix}"
    file_path = settings.data_dir / "uploads" / upload_name
    metadata = {
        "doc_id": doc_id,
        "filename": original_name,
        "extension": suffix.lstrip(".") or "text",
        "size_bytes": len(raw),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "stored_path": str(file_path),
    }
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(raw)
        retriever = _ensure_retriever()
        chunks = retriever.add_file(str(file_path), metadata=metadata)
        if not chunks:
            raise HTTPException(status_code=422, detail="No readable text found in this document.")
        retriever.save(str(settings.rag_index_dir))
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    doc = next((item for item in retriever.list_documents() if item["id"] == doc_id), None)
    return {"ok": True, "filename": original_name, "document": doc, "chunks": chunks}


@router.delete("/documents/{document_id}")
def remove_document(document_id: str):
    """Remove one uploaded source from the RAG index."""
    try:
        retriever = _ensure_retriever()
        docs = retriever.list_documents()
        doc = next((item for item in docs if item["id"] == document_id), None)
        stored_paths = {
            (chunk.metadata or {}).get("stored_path")
            for chunk in retriever.vector_store.chunks
            if (chunk.metadata or {}).get("doc_id") == document_id
        }
        removed = retriever.remove_document(document_id)
        if removed == 0:
            raise HTTPException(status_code=404, detail="Document not found.")
        retriever.save(str(settings.rag_index_dir))
        if doc:
            for stored_path in stored_paths:
                if stored_path:
                    Path(stored_path).unlink(missing_ok=True)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "removed_chunks": removed}


@router.delete("/clear")
def clear_rag():
    """Clear the RAG index."""
    try:
        if app_state.retriever is not None:
            app_state.retriever.clear()
        import shutil
        shutil.rmtree(settings.rag_index_dir, ignore_errors=True)
        settings.rag_index_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


@router.get("/status")
def rag_status():
    if app_state.retriever is None:
        has_index = settings.rag_index_dir.exists() and any(settings.rag_index_dir.iterdir())
        if not has_index:
            return _rag_payload(None, has_saved_index=False)
        try:
            retriever = _ensure_retriever()
            return _rag_payload(retriever, has_saved_index=True)
        except Exception:
            return _rag_payload(None, has_saved_index=True)
    return _rag_payload(app_state.retriever)


@router.post("/retrieve")
def retrieve_rag(body: RetrievalRequest):
    """Return the top retrieved chunks for benchmark annotation."""
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query is required.")

    try:
        retriever = _ensure_retriever()
        result = retriever.retrieve(query, top_k=max(1, min(body.top_k, 20)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "query": result.query,
        "context": result.context,
        "sources": result.sources,
        "num_chunks": result.num_chunks,
        "chunks": [
            {
                "rank": sr.rank + 1,
                "score": sr.score,
                "source": sr.chunk.source,
                "chunk_index": sr.chunk.chunk_index,
                "metadata": sr.chunk.metadata,
                "text": sr.chunk.text,
            }
            for sr in result.search_results
        ],
    }
