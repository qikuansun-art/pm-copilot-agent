"""Demonstrate generating a response with the configured Qwen client."""

from llm.client import create_llm_client
from llm.config import LLMConfig


def main() -> None:
    """Load LLM configuration, call Qwen, and print safe result fields."""
    config = LLMConfig.from_env()
    client = create_llm_client(config)

    response = client.generate(
        system_prompt="你是一个专业的产品经理助手。",
        user_prompt="请只用一句话回答：CNC 刀具管理最核心解决的是什么问题？",
    )

    print("provider:", config.provider)
    print("model:", config.model)
    print("response:", response)


if __name__ == "__main__":
    main()
