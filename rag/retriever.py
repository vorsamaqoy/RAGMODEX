"""Context retriever for RAG system."""

from typing import Optional
from dataclasses import dataclass

from .vector_store import VectorStore, SearchResult
from .document_processor import DocumentProcessor, ProcessedDocument
from .embeddings import EmbeddingGenerator


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""

    query: str
    context: str
    sources: list[str]
    num_chunks: int
    search_results: list[SearchResult]


class Retriever:
    """Retrieve relevant context for queries."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        top_k: int = 5,
    ):
        """Initialize the retriever."""
        self.embedding_generator = EmbeddingGenerator(embedding_model)
        self.vector_store = vector_store or VectorStore(self.embedding_generator)
        self.document_processor = DocumentProcessor(chunk_size, chunk_overlap)
        self.top_k = top_k

    def add_document(
        self,
        content: str,
        source: str = "document",
        metadata: Optional[dict] = None,
    ) -> int:
        """Add a document to the retrieval system."""
        processed = self.document_processor.process_text(content, source, metadata)
        self.vector_store.add_chunks(processed.chunks)
        return processed.total_chunks

    def add_pdf(
        self,
        pdf_path: str,
        metadata: Optional[dict] = None,
    ) -> int:
        """Add a PDF document to the retrieval system."""
        processed = self.document_processor.process_pdf(pdf_path, metadata)
        if processed:
            self.vector_store.add_chunks(processed.chunks)
            return processed.total_chunks
        return 0

    def add_file(
        self,
        file_path: str,
        metadata: Optional[dict] = None,
    ) -> int:
        """Add a file to the retrieval system."""
        processed = self.document_processor.process_file(file_path, metadata)
        if processed:
            self.vector_store.add_chunks(processed.chunks)
            return processed.total_chunks
        return 0

    def add_directory(
        self,
        dir_path: str,
        extensions: list[str] = [".txt", ".md", ".pdf"],
        recursive: bool = True,
    ) -> int:
        """Add all matching files in a directory."""
        processed_docs = self.document_processor.process_directory(
            dir_path, extensions, recursive
        )

        total_chunks = 0
        for doc in processed_docs:
            self.vector_store.add_chunks(doc.chunks)
            total_chunks += doc.total_chunks

        return total_chunks

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: float = 0.0,
    ) -> RetrievalResult:
        """Retrieve relevant context for a query."""
        k = top_k or self.top_k

        # Search vector store
        results = self.vector_store.search(query, k, min_score)

        # Build context
        context_parts = []
        sources = set()

        for result in results:
            context_parts.append(result.chunk.text)
            sources.add(result.chunk.source)

        context = "\n\n".join(context_parts)

        return RetrievalResult(
            query=query,
            context=context,
            sources=list(sources),
            num_chunks=len(results),
            search_results=results,
        )

    def retrieve_with_scores(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float, str]]:
        """Retrieve with scores: (text, score, source)."""
        k = top_k or self.top_k
        results = self.vector_store.search(query, k)

        return [
            (r.chunk.text, r.score, r.chunk.source)
            for r in results
        ]

    def format_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        include_sources: bool = True,
    ) -> str:
        """Format retrieved context for LLM consumption."""
        result = self.retrieve(query, top_k)

        if not result.search_results:
            return ""

        formatted = []

        for i, sr in enumerate(result.search_results, 1):
            chunk_text = f"[{i}] {sr.chunk.text}"
            if include_sources:
                chunk_text += f"\n(Source: {sr.chunk.source})"
            formatted.append(chunk_text)

        return "\n\n".join(formatted)

    def save(self, path: str) -> None:
        """Save the retriever's vector store."""
        self.vector_store.save(path)

    def load(self, path: str) -> bool:
        """Load the retriever's vector store."""
        return self.vector_store.load(path)

    def clear(self) -> None:
        """Clear all indexed documents."""
        self.vector_store.clear()

    def list_documents(self) -> list[dict]:
        """List indexed source documents."""
        return self.vector_store.list_documents()

    def remove_document(self, document_id: str) -> int:
        """Remove an indexed source document."""
        return self.vector_store.remove_chunks_by_document(document_id)

    @property
    def num_chunks(self) -> int:
        """Get total number of indexed chunks."""
        return self.vector_store.size

    def is_empty(self) -> bool:
        """Check if the retriever has any indexed content."""
        return self.vector_store.is_empty()


def create_chemistry_retriever(
    index_path: Optional[str] = None,
    pdf_paths: Optional[list[str]] = None,
) -> Retriever:
    """Create a retriever pre-loaded with chemistry documentation."""
    retriever = Retriever()

    # Load existing index if available
    if index_path and retriever.load(index_path):
        return retriever

    # Add PDFs if provided
    if pdf_paths:
        for pdf_path in pdf_paths:
            retriever.add_pdf(pdf_path)

    # Save index if path provided
    if index_path:
        retriever.save(index_path)

    return retriever
