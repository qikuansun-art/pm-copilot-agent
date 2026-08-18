"""Demonstrate the default unified LLM configuration and mock client."""

from llm.client import create_llm_client
from llm.config import LLMConfig


def main() -> None:
    """Create the default client and print its mock response."""
    config = LLMConfig()
    client = create_llm_client(config)
    response = client.generate(
        system_prompt="You are PM Copilot.",
        user_prompt="Plan a product feature.",
    )

    print("provider:", config.provider)
    print("model:", config.model)
    print("response:", response)


if __name__ == "__main__":
    main()
