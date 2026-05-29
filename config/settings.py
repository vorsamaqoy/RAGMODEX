"""Application settings and configuration."""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class Settings:
    """Application settings container."""

    # Paths
    app_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")
    rag_index_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "rag_index")

    # LLM Settings
    default_llm_provider: str = "groq"
    default_model: str = "llama-3.3-70b-versatile"
    max_tokens: int = 4096
    temperature: float = 0.7

    # RAG Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 5

    # Fingerprint Settings
    default_fp_radius: int = 2
    default_fp_nbits: int = 2048
    default_fp_use_features: bool = False

    # Visualization Settings
    mol_image_size: tuple = (400, 300)
    highlight_color: tuple = (0.8, 0.8, 1.0)

    # Sandbox Settings
    max_execution_time: int = 30  # seconds
    max_memory_mb: int = 512

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        settings = cls()

        # Override with environment variables if present
        if os.getenv("DEFAULT_LLM_PROVIDER"):
            settings.default_llm_provider = os.getenv("DEFAULT_LLM_PROVIDER")
        if os.getenv("DEFAULT_MODEL"):
            settings.default_model = os.getenv("DEFAULT_MODEL")
        if os.getenv("EMBEDDING_MODEL"):
            settings.embedding_model = os.getenv("EMBEDDING_MODEL")
        if os.getenv("CHUNK_SIZE"):
            settings.chunk_size = int(os.getenv("CHUNK_SIZE"))
        if os.getenv("CHUNK_OVERLAP"):
            settings.chunk_overlap = int(os.getenv("CHUNK_OVERLAP"))

        return settings

    def ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.rag_index_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings.from_env()
