"""FAISS vector store for RAG system."""

from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from .document_processor import DocumentChunk
from .embeddings import EmbeddingGenerator


@dataclass
class SearchResult:
    """A search result from the vector store."""

    chunk: DocumentChunk
    score: float
    rank: int


class VectorStore:
    """FAISS-based vector store for document retrieval."""

    def __init__(
        self,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        index_path: Optional[str] = None,
    ):
        """Initialize the vector store."""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu")

        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.index_path = index_path
        self.index: Optional[faiss.Index] = None
        self.chunks: list[DocumentChunk] = []
        self.metadata: dict = {}

        # Load existing index if path provided
        if index_path:
            self.load(index_path)

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Add document chunks to the vector store."""
        if not chunks:
            return

        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_generator.embed_batch(texts)

        # Initialize or add to index
        if self.index is None:
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine for normalized)

        # Add to index
        self.index.add(embeddings.astype(np.float32))

        # Store chunks
        self.chunks.extend(chunks)

    def _rebuild_index(self) -> None:
        """Rebuild FAISS from the current chunk list."""
        self.index = None
        if not self.chunks:
            return

        texts = [chunk.text for chunk in self.chunks]
        embeddings = self.embedding_generator.embed_batch(texts)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings.astype(np.float32))

    def remove_chunks_by_document(self, document_id: str) -> int:
        """Remove all chunks matching a document id or source."""
        if not document_id:
            return 0

        kept: list[DocumentChunk] = []
        removed = 0
        for chunk in self.chunks:
            metadata = chunk.metadata or {}
            if metadata.get("doc_id") == document_id or chunk.source == document_id:
                removed += 1
            else:
                kept.append(chunk)

        if removed:
            self.chunks = kept
            self._rebuild_index()
        return removed

    def list_documents(self) -> list[dict]:
        """Return aggregate document metadata from stored chunks."""
        documents: dict[str, dict] = {}

        for chunk in self.chunks:
            metadata = chunk.metadata or {}
            doc_id = str(metadata.get("doc_id") or chunk.source)
            doc = documents.setdefault(
                doc_id,
                {
                    "id": doc_id,
                    "name": metadata.get("filename") or Path(chunk.source).name or "document",
                    "source": chunk.source,
                    "type": metadata.get("extension") or Path(chunk.source).suffix.lower().lstrip(".") or "text",
                    "chunk_count": 0,
                    "size_bytes": metadata.get("size_bytes"),
                    "uploaded_at": metadata.get("uploaded_at"),
                    "characters": 0,
                },
            )
            doc["chunk_count"] += 1
            doc["characters"] += len(chunk.text or "")

        return sorted(
            documents.values(),
            key=lambda item: (item.get("uploaded_at") or "", item.get("name") or ""),
            reverse=True,
        )

    def add_texts(
        self,
        texts: list[str],
        source: str = "manual",
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """Add texts directly to the vector store."""
        chunks = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else None
            chunks.append(
                DocumentChunk(
                    text=text,
                    source=source,
                    chunk_index=len(self.chunks) + i,
                    metadata=metadata,
                )
            )
        self.add_chunks(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search for similar chunks."""
        if self.index is None or self.index.ntotal == 0:
            return []

        # Generate query embedding
        query_embedding = self.embedding_generator.embed_single(query)
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)

        # Search
        scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        # Build results
        results = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx >= 0 and score >= min_score:
                results.append(
                    SearchResult(
                        chunk=self.chunks[idx],
                        score=float(score),
                        rank=rank,
                    )
                )

        return results

    def search_with_filter(
        self,
        query: str,
        top_k: int = 5,
        source_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search with optional source filter."""
        # Get more results to filter
        results = self.search(query, top_k * 3)

        # Apply filter
        if source_filter:
            results = [r for r in results if source_filter in r.chunk.source]

        return results[:top_k]

    def save(self, path: str) -> None:
        """Save the vector store to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        if self.index is not None:
            # Save FAISS index
            faiss.write_index(self.index, str(path / "index.faiss"))

        # Save chunks as JSON
        chunks_data = [
            {
                "text": c.text,
                "source": c.source,
                "chunk_index": c.chunk_index,
                "metadata": c.metadata,
            }
            for c in self.chunks
        ]

        with open(path / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2)

        # Save metadata
        self.metadata["num_chunks"] = len(self.chunks)
        self.metadata["embedding_model"] = self.embedding_generator.model_name

        with open(path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def load(self, path: str) -> bool:
        """Load the vector store from disk."""
        path = Path(path)

        if not path.exists():
            return False

        try:
            # Load FAISS index
            index_path = path / "index.faiss"
            if index_path.exists():
                self.index = faiss.read_index(str(index_path))

            # Load chunks
            chunks_path = path / "chunks.json"
            if chunks_path.exists():
                with open(chunks_path, "r", encoding="utf-8") as f:
                    chunks_data = json.load(f)

                self.chunks = [
                    DocumentChunk(
                        text=c["text"],
                        source=c["source"],
                        chunk_index=c["chunk_index"],
                        metadata=c.get("metadata"),
                    )
                    for c in chunks_data
                ]

            # Load metadata
            metadata_path = path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)

            return True

        except Exception as e:
            print(f"Error loading vector store: {e}")
            return False

    def clear(self) -> None:
        """Clear all data from the store."""
        self.index = None
        self.chunks = []
        self.metadata = {}

    @property
    def size(self) -> int:
        """Get number of chunks in the store."""
        return len(self.chunks)

    def is_empty(self) -> bool:
        """Check if the store is empty."""
        return len(self.chunks) == 0
