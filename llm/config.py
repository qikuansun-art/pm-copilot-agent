"""Configuration model for the unified LLM client layer."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """Stores provider-neutral configuration for an LLM client."""

    provider: str = "mock"
    model: str = ""
    api_key: str = ""
    base_url: str = ""

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create configuration from environment variables and defaults."""
        load_dotenv()
        return cls(
            provider=os.getenv("LLM_PROVIDER", "mock"),
            model=os.getenv("LLM_MODEL", ""),
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
        )
