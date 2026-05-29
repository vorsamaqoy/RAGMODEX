"""Embedding generation for RAG system."""

from typing import Optional, Union
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingGenerator:
    """Generate embeddings for text using sentence transformers."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: Optional[str] = None):
        """Initialize the embedding generator."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: Union[str, list[str]]) -> np.ndarray:
        """Generate embeddings for text or list of texts."""
        if isinstance(text, str):
            text = [text]

        embeddings = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.embed(text)[0]

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Generate embeddings for a batch of texts."""
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=show_progress,
        )

        return embeddings

    def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        emb1 = self.embed_single(text1)
        emb2 = self.embed_single(text2)
        return float(np.dot(emb1, emb2))

    def find_most_similar(
        self,
        query: str,
        candidates: list[str],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """Find most similar candidates to a query."""
        query_emb = self.embed_single(query)
        candidate_embs = self.embed(candidates)

        # Calculate similarities
        similarities = np.dot(candidate_embs, query_emb)

        # Get top k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        return [(int(idx), float(similarities[idx])) for idx in top_indices]

    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def is_available(self) -> bool:
        """Check if the embedding generator is available."""
        return SENTENCE_TRANSFORMERS_AVAILABLE
