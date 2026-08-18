"""Demonstrate requirement understanding with the configured real LLM."""

from agent.requirement_understanding import RequirementUnderstandingService


def main() -> None:
    """Analyze the CNC request and print the structured result."""
    service = RequirementUnderstandingService()
    result = service.understand("帮我规划一个 CNC 刀具管理功能")

    print("known_facts:", result.known_facts)
    print("missing_information:", result.missing_information)
    print("need_clarification:", result.need_clarification)
    print("questions:")
    for item in result.questions:
        print("- question:", item.question)
        print("  reason:", item.reason)


if __name__ == "__main__":
    main()
