"""Document processing for RAG system."""

from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import re

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


@dataclass
class DocumentChunk:
    """A chunk of processed document."""

    text: str
    source: str
    chunk_index: int
    metadata: Optional[dict] = None


@dataclass
class ProcessedDocument:
    """A processed document with chunks."""

    source: str
    chunks: list[DocumentChunk]
    total_chunks: int
    total_characters: int


class DocumentProcessor:
    """Process documents for RAG indexing."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ):
        """Initialize the document processor."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def process_text(
        self,
        text: str,
        source: str = "text",
        metadata: Optional[dict] = None,
    ) -> ProcessedDocument:
        """Process raw text into chunks."""
        # Clean text
        text = self._clean_text(text)

        # Split into chunks
        chunks = self._chunk_text(text, source, metadata)

        return ProcessedDocument(
            source=source,
            chunks=chunks,
            total_chunks=len(chunks),
            total_characters=len(text),
        )

    def process_pdf(
        self,
        pdf_path: str,
        metadata: Optional[dict] = None,
    ) -> Optional[ProcessedDocument]:
        """Process a PDF file into chunks."""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")

        path = Path(pdf_path)
        if not path.exists():
            return None

        try:
            reader = PdfReader(str(path))
            text_parts = []

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text}")

            full_text = "\n\n".join(text_parts)
            return self.process_text(full_text, source=str(path), metadata=metadata)

        except Exception as e:
            print(f"Error processing PDF: {e}")
            return None

    def process_file(
        self,
        file_path: str,
        metadata: Optional[dict] = None,
    ) -> Optional[ProcessedDocument]:
        """Process a file based on its extension."""
        path = Path(file_path)

        if not path.exists():
            return None

        if path.suffix.lower() == ".pdf":
            return self.process_pdf(file_path, metadata)
        elif path.suffix.lower() in [".txt", ".md", ".rst"]:
            text = path.read_text(encoding="utf-8")
            return self.process_text(text, source=str(path), metadata=metadata)
        else:
            # Try to read as text
            try:
                text = path.read_text(encoding="utf-8")
                return self.process_text(text, source=str(path), metadata=metadata)
            except Exception:
                return None

    def process_directory(
        self,
        dir_path: str,
        extensions: list[str] = [".txt", ".md", ".pdf"],
        recursive: bool = True,
    ) -> list[ProcessedDocument]:
        """Process all matching files in a directory."""
        path = Path(dir_path)

        if not path.exists() or not path.is_dir():
            return []

        results = []
        pattern = "**/*" if recursive else "*"

        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                doc = self.process_file(str(file_path))
                if doc:
                    results.append(doc)

        return results

    def _chunk_text(
        self,
        text: str,
        source: str,
        metadata: Optional[dict] = None,
    ) -> list[DocumentChunk]:
        """Split text into overlapping chunks."""
        chunks = []

        # Split into sentences first
        sentences = self._split_into_sentences(text)

        current_chunk = []
        current_length = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(
                        DocumentChunk(
                            text=chunk_text,
                            source=source,
                            chunk_index=chunk_index,
                            metadata=metadata,
                        )
                    )
                    chunk_index += 1

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk, self.chunk_overlap
                )
                current_chunk = overlap_sentences
                current_length = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_length += sentence_length

        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        source=source,
                        chunk_index=chunk_index,
                        metadata=metadata,
                    )
                )

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_overlap_sentences(
        self, sentences: list[str], target_overlap: int
    ) -> list[str]:
        """Get sentences for overlap from the end of a chunk."""
        overlap_sentences = []
        overlap_length = 0

        for sentence in reversed(sentences):
            if overlap_length >= target_overlap:
                break
            overlap_sentences.insert(0, sentence)
            overlap_length += len(sentence)

        return overlap_sentences

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters that might cause issues
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        return text.strip()
