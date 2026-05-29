"""API key management and configuration."""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class APIConfig:
    """API configuration and key management."""

    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    def __post_init__(self):
        """Load API keys from environment if not provided."""
        if self.groq_api_key is None:
            self.groq_api_key = os.getenv("GROQ_API_KEY")
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.anthropic_api_key is None:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    @property
    def has_groq(self) -> bool:
        """Check if Groq API key is available."""
        return bool(self.groq_api_key)

    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is available."""
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        """Check if Anthropic API key is available."""
        return bool(self.anthropic_api_key)

    def get_available_providers(self) -> list[str]:
        """Get list of available LLM providers based on configured keys."""
        providers = []
        if self.has_groq:
            providers.append("groq")
        if self.has_openai:
            providers.append("openai")
        if self.has_anthropic:
            providers.append("anthropic")
        return providers

    def validate(self) -> tuple[bool, str]:
        """Validate that at least one API key is configured."""
        if not any([self.has_groq, self.has_openai, self.has_anthropic]):
            return False, "No API keys configured. Please set at least one of: GROQ_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY"
        return True, "API configuration valid"


# Global API config instance
api_config = APIConfig()
