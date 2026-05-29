"""RAG document management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.state import app_state
from config.settings import settings
from rag.retriever import Retriever

router = APIRouter()


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5


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
        retriever.add_document(text, source=source)
        retriever.save(str(settings.rag_index_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


@router.post("/add-pdf")
async def add_pdf(file: UploadFile = File(...)):
    """Upload and index a PDF file."""
    raw = await file.read()
    pdf_path = settings.data_dir / "uploads" / (file.filename or "document.pdf")
    try:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(raw)
        retriever = _ensure_retriever()
        retriever.add_pdf(str(pdf_path))
        retriever.save(str(settings.rag_index_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "filename": file.filename}


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
        return {"ready": False, "n_docs": 0, "has_saved_index": has_index}
    try:
        n = app_state.retriever.index.ntotal if hasattr(app_state.retriever, "index") else -1
    except Exception:
        n = -1
    return {"ready": True, "n_docs": n}


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
