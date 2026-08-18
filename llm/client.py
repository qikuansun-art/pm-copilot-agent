"""Provider-neutral LLM client interfaces and the initial mock client."""

from abc import ABC, abstractmethod

from openai import OpenAI

from llm.config import LLMConfig


class LLMClient(ABC):
    """Defines the common text-generation interface for LLM providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a text response from system and user prompts."""


class MockLLMClient(LLMClient):
    """Returns deterministic output without calling a real model API."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the fixed mock response."""
        return "Mock LLM response"


class QwenLLMClient(LLMClient):
    """Uses Qwen through its OpenAI-compatible Chat Completions API."""

    def __init__(self, config: LLMConfig) -> None:
        """Validate Qwen configuration and initialize the OpenAI client."""
        if not config.api_key:
            raise ValueError("Qwen API key is required")
        if not config.base_url:
            raise ValueError("Qwen base URL is required")
        if not config.model:
            raise ValueError("Qwen model is required")

        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using Qwen Chat Completions."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content


def create_llm_client(config: LLMConfig) -> LLMClient:
    """Create an LLM client for the configured provider."""
    if config.provider == "mock":
        return MockLLMClient()
    if config.provider == "qwen":
        return QwenLLMClient(config)
    raise ValueError("Unsupported LLM provider")
