"""Conversation management and chat handling."""

from typing import Optional, Generator, Union
from dataclasses import dataclass, field
from datetime import datetime

from .client_factory import LLMClientFactory
from .prompt_templates import PromptTemplates
from .groq_client import LLMResponse


def _strip_reasoning_tags(text: str) -> str:
    """Remove reasoning tags exposed by some models (for example Qwen)."""
    import re

    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


@dataclass
class Message:
    """A single chat message."""

    role: str  # "system", "user", or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Conversation:
    """Container for a conversation history."""

    messages: list[Message] = field(default_factory=list)
    system_prompt: str = PromptTemplates.SYSTEM_PROMPT

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(role=role, content=content))

    def get_messages_for_api(self) -> list[dict]:
        """Get messages in API format."""
        api_messages = [{"role": "system", "content": self.system_prompt}]
        for msg in self.messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        return api_messages

    def clear(self) -> None:
        """Clear the conversation history."""
        self.messages = []

    def get_last_n_messages(self, n: int) -> list[Message]:
        """Get the last n messages."""
        return self.messages[-n:] if len(self.messages) >= n else self.messages


class ChatHandler:
    """Handle chat interactions with LLM."""

    def __init__(
        self,
        provider: str = "groq",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """Initialize the chat handler."""
        self.provider = provider
        self.client = LLMClientFactory.create(provider, api_key, model)
        self.conversation = Conversation(
            system_prompt=system_prompt or PromptTemplates.SYSTEM_PROMPT
        )
        self.temperature = 0.3
        self.max_tokens = 700

    def chat(
        self,
        message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Union[str, Generator[str, None, None]]:
        """Send a message and get a response."""
        # Add user message to conversation
        self.conversation.add_message("user", message)

        # Get API-formatted messages
        messages = self.conversation.get_messages_for_api()

        # Get response
        response = self.client.chat(
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            stream=stream,
        )

        if stream:
            return self._handle_stream(response)
        else:
            # Add assistant response to conversation
            content = _strip_reasoning_tags(response.content)
            self.conversation.add_message("assistant", content)
            return content

    def _handle_stream(
        self, stream: Generator[str, None, None]
    ) -> Generator[str, None, None]:
        """Handle streaming response and save to conversation."""
        full_response = []

        for chunk in stream:
            full_response.append(chunk)
            yield chunk

        # Save complete response to conversation
        self.conversation.add_message("assistant", "".join(full_response))

    def query_with_context(
        self,
        message: str,
        context: str,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a message with additional context (for RAG)."""
        # Format message with context
        formatted_message = PromptTemplates.format_rag_prompt(context, message)

        # Add to conversation
        self.conversation.add_message("user", formatted_message)

        # Get response
        response = self.client.chat(
            messages=self.conversation.get_messages_for_api(),
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )

        # Add to conversation
        content = _strip_reasoning_tags(response.content)
        self.conversation.add_message("assistant", content)
        return content

    def explain_maccs_key(
        self,
        key_number: int,
        smarts: str,
        description: str,
        category: str,
    ) -> str:
        """Get LLM explanation for a MACCS key."""
        prompt = PromptTemplates.format_maccs_prompt(
            key_number, smarts, description, category
        )
        return self.simple_query(prompt)

    def explain_ecfp_bit(
        self,
        smiles: str,
        bit_index: int,
        bit_info: str,
        fp_type: str = "ECFP",
        radius: int = 2,
        n_bits: int = 2048,
    ) -> str:
        """Get LLM explanation for an ECFP bit."""
        prompt = PromptTemplates.format_ecfp_prompt(
            smiles, bit_index, bit_info, fp_type, radius, n_bits
        )
        return self.simple_query(prompt)

    def explain_descriptor(
        self,
        descriptor_name: str,
        smiles: Optional[str] = None,
        value: Optional[float] = None,
    ) -> str:
        """Get LLM explanation for a descriptor."""
        if smiles and value is not None:
            prompt = PromptTemplates.format_descriptor_with_value_prompt(
                descriptor_name, smiles, value
            )
        else:
            prompt = PromptTemplates.format_descriptor_prompt(descriptor_name)
        return self.simple_query(prompt)

    def analyze_molecule(
        self,
        smiles: str,
        canonical_smiles: str,
        formula: str,
        mol_weight: float,
    ) -> str:
        """Get comprehensive molecular analysis."""
        prompt = PromptTemplates.format_analysis_prompt(
            smiles, canonical_smiles, formula, mol_weight
        )
        return self.simple_query(prompt)

    def generate_code(self, task_description: str, smiles: str) -> str:
        """Code generation is disabled — RAGMODEX handles all computation internally."""
        return "Code generation is not available in this interface."

    def simple_query(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        system_override: Optional[str] = None,
    ) -> str:
        """Simple one-off query without conversation history.

        Parameters
        ----------
        system_override:
            If provided, replaces the default system prompt for this call only.
            Use this for grounded responses that must not hallucinate.
        """
        system = system_override if system_override is not None else self.conversation.system_prompt
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        response = self.client.chat(
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )

        return _strip_reasoning_tags(response.content)

    def stream_query(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        system_override: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Streaming one-off query."""
        system = system_override if system_override is not None else self.conversation.system_prompt
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        return self.client.chat(
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation.clear()

    def get_history(self) -> list[Message]:
        """Get conversation history."""
        return self.conversation.messages

    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt."""
        self.conversation.system_prompt = prompt

    def set_temperature(self, temperature: float) -> None:
        """Set the temperature for responses."""
        self.temperature = max(0.0, min(2.0, temperature))

    def set_max_tokens(self, max_tokens: int) -> None:
        """Set the maximum tokens for responses."""
        self.max_tokens = max(100, min(8192, max_tokens))
