"""Global application state shared across all request handlers."""

from __future__ import annotations
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class AppState:
    # ML model
    model: Optional[Any] = None
    model_bytes: Optional[bytes] = None
    explainer: Optional[Any] = None
    bit_db: dict = field(default_factory=dict)

    # Training data (for AD scoring, evaluation, visualizer)
    training_fps: Optional[Any] = None       # np.ndarray shape (n, n_bits)
    training_smiles: list[str] = field(default_factory=list)
    training_labels: Optional[Any] = None    # np.ndarray shape (n,)
    training_probs: Optional[Any] = None     # np.ndarray shape (n,) – cached predict_proba
    model_name: str = ""

    # Test data (optional, for held-out evaluation)
    test_fps: Optional[Any] = None           # np.ndarray shape (m, n_bits)
    test_smiles: list[str] = field(default_factory=list)
    test_labels: Optional[Any] = None        # np.ndarray shape (m,)
    test_probs: Optional[Any] = None         # np.ndarray shape (m,) – cached predict_proba

    # Fingerprint config (must match training)
    fp_radius: int = 3
    fp_nbits: int = 2048

    # RAG
    retriever: Optional[Any] = None

    # LLM
    chat_handler: Optional[Any] = None
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_local_endpoint: str = "http://127.0.0.1:11434"
    temperature: float = 0.3

    def has_model(self) -> bool:
        return self.model is not None and self.explainer is not None

    def has_training_data(self) -> bool:
        return self.training_fps is not None and len(self.training_smiles) > 0

    def has_test_data(self) -> bool:
        return self.test_fps is not None and len(self.test_smiles) > 0


app_state = AppState()
