"""LLM client factory for multiple providers."""

from typing import Optional, Union, Generator
from dataclasses import dataclass
import json
import os
from urllib import request as urlrequest

from .groq_client import GroqClient, LLMResponse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Try importing optional providers
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ProviderInfo:
    """Information about an LLM provider."""

    name: str
    available: bool
    default_model: str
    models: list[str]


class OpenAIClient:
    """Client for OpenAI API."""

    DEFAULT_MODEL = "gpt-4o-mini"
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the OpenAI client."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        self.model = model or self.DEFAULT_MODEL
        self.client = OpenAI(api_key=self.api_key)

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

    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self.api_key)


class AnthropicClient:
    """Client for Anthropic API."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    AVAILABLE_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")

        self.model = model or self.DEFAULT_MODEL
        self.client = Anthropic(api_key=self.api_key)

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

        # Extract system message if present
        system_prompt = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered_messages.append(msg)

        if stream:
            return self._stream_chat(
                filtered_messages, system_prompt, model, temperature, max_tokens
            )

        response = self.client.messages.create(
            model=model,
            messages=filtered_messages,
            system=system_prompt or "",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )

    def _stream_chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Generator[str, None, None]:
        """Streaming chat completion."""
        with self.client.messages.stream(
            model=model,
            messages=messages,
            system=system_prompt or "",
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            for text in stream.text_stream:
                yield text

    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self.api_key)


class LocalOllamaClient:
    """Client for local Ollama-compatible chat models."""

    DEFAULT_MODEL = "qwen3:4b"
    DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
    AVAILABLE_MODELS = [
        "qwen3:0.6b",
        "qwen3:1.7b",
        "qwen3:4b",
        "qwen3:8b",
        "llama3.2:3b",
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.model = model or self.DEFAULT_MODEL
        self.endpoint = os.getenv("LOCAL_LLM_ENDPOINT", self.DEFAULT_ENDPOINT).rstrip("/")

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> LLMResponse | Generator:
        model = model or self.model
        if stream:
            return self._stream_chat(messages, model, temperature, max_tokens)
        return self._sync_chat(messages, model, temperature, max_tokens)

    def _payload(self, messages: list[dict], model: str, temperature: float, max_tokens: int, stream: bool) -> bytes:
        return json.dumps({
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }).encode("utf-8")

    def _sync_chat(self, messages: list[dict], model: str, temperature: float, max_tokens: int) -> LLMResponse:
        req = urlrequest.Request(
            f"{self.endpoint}/api/chat",
            data=self._payload(messages, model, temperature, max_tokens, False),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=120) as res:
            data = json.loads(res.read().decode("utf-8"))
        content = data.get("message", {}).get("content", "")
        return LLMResponse(content=content, model=data.get("model", model), usage=None, finish_reason=data.get("done_reason"))

    def _stream_chat(self, messages: list[dict], model: str, temperature: float, max_tokens: int) -> Generator[str, None, None]:
        req = urlrequest.Request(
            f"{self.endpoint}/api/chat",
            data=self._payload(messages, model, temperature, max_tokens, True),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=120) as res:
            for raw in res:
                if not raw:
                    continue
                data = json.loads(raw.decode("utf-8"))
                chunk = data.get("message", {}).get("content")
                if chunk:
                    yield chunk

    def is_available(self) -> bool:
        return True

    @classmethod
    def list_models(cls, endpoint: Optional[str] = None) -> list[str]:
        base = (endpoint or os.getenv("LOCAL_LLM_ENDPOINT") or cls.DEFAULT_ENDPOINT).rstrip("/")
        try:
            with urlrequest.urlopen(f"{base}/api/tags", timeout=2) as res:
                data = json.loads(res.read().decode("utf-8"))
            names = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return names or cls.AVAILABLE_MODELS.copy()
        except Exception:
            return cls.AVAILABLE_MODELS.copy()


class LLMClientFactory:
    """Factory for creating LLM clients."""

    PROVIDERS = {
        "groq": {
            "class": GroqClient,
            "available": True,  # Always available as it's the default
            "default_model": GroqClient.DEFAULT_MODEL,
            "models": GroqClient.AVAILABLE_MODELS,
        },
        "openai": {
            "class": OpenAIClient if OPENAI_AVAILABLE else None,
            "available": OPENAI_AVAILABLE,
            "default_model": OpenAIClient.DEFAULT_MODEL if OPENAI_AVAILABLE else "",
            "models": OpenAIClient.AVAILABLE_MODELS if OPENAI_AVAILABLE else [],
        },
        "anthropic": {
            "class": AnthropicClient if ANTHROPIC_AVAILABLE else None,
            "available": ANTHROPIC_AVAILABLE,
            "default_model": AnthropicClient.DEFAULT_MODEL if ANTHROPIC_AVAILABLE else "",
            "models": AnthropicClient.AVAILABLE_MODELS if ANTHROPIC_AVAILABLE else [],
        },
        "local": {
            "class": LocalOllamaClient,
            "available": True,
            "default_model": LocalOllamaClient.DEFAULT_MODEL,
            "models": LocalOllamaClient.AVAILABLE_MODELS,
        },
    }

    @classmethod
    def create(
        cls,
        provider: str = "groq",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Union[GroqClient, OpenAIClient, AnthropicClient, LocalOllamaClient]:
        """Create an LLM client for the specified provider."""
        provider = provider.lower()

        if provider not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(cls.PROVIDERS.keys())}")

        provider_info = cls.PROVIDERS[provider]

        if not provider_info["available"]:
            raise ImportError(f"Provider '{provider}' is not available. Please install the required package.")

        client_class = provider_info["class"]
        return client_class(api_key=api_key, model=model)

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available providers (with API keys configured)."""
        available = []

        for name, info in cls.PROVIDERS.items():
            if info["available"]:
                # Check if API key is configured
                env_key = f"{name.upper()}_API_KEY"
                if name == "local" or os.getenv(env_key):
                    available.append(name)

        return available

    @classmethod
    def get_provider_info(cls, provider: str) -> Optional[ProviderInfo]:
        """Get information about a provider."""
        if provider not in cls.PROVIDERS:
            return None

        info = cls.PROVIDERS[provider]
        return ProviderInfo(
            name=provider,
            available=info["available"],
            default_model=info["default_model"],
            models=info["models"],
        )

    @classmethod
    def list_all_providers(cls) -> list[ProviderInfo]:
        """List all providers with their info."""
        return [
            ProviderInfo(
                name=name,
                available=info["available"],
                default_model=info["default_model"],
                models=info["models"],
            )
            for name, info in cls.PROVIDERS.items()
        ]
