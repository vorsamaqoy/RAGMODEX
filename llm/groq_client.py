"""Groq API client for LLM interactions."""

from typing import Optional, Generator
from dataclasses import dataclass
import os

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


@dataclass
class LLMResponse:
    """Container for LLM response."""

    content: str
    model: str
    usage: Optional[dict] = None
    finish_reason: Optional[str] = None


class GroqClient:
    """Client for Groq API."""

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    AVAILABLE_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3-32b",
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the Groq client."""
        if not GROQ_AVAILABLE:
            raise ImportError("Groq package not installed. Run: pip install groq")

        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not provided")

        self.model = model or self.DEFAULT_MODEL
        self.client = Groq(api_key=self.api_key)

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> LLMResponse | Generator:
        """Send a chat completion request."""
        model = model or self.model

        if stream:
            return self._stream_chat(messages, model, temperature, max_tokens)
        else:
            return self._sync_chat(messages, model, temperature, max_tokens)

    def _sync_chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Synchronous chat completion."""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )

    def _stream_chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Generator[str, None, None]:
        """Streaming chat completion."""
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def simple_query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Simple single-turn query."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return response.content

    def stream_query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Streaming single-turn query."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        return self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self.api_key)

    @staticmethod
    def list_models() -> list[str]:
        """List available models."""
        return GroqClient.AVAILABLE_MODELS.copy()
