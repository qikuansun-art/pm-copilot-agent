"""Demonstrate mock requirement understanding with filled and empty requests."""

from agent.requirement_understanding import RequirementUnderstandingService
from models.understanding import RequirementUnderstandingResult


def print_result(result: RequirementUnderstandingResult) -> None:
    """Print the fields relevant to requirement understanding."""
    print("known_facts:", result.known_facts)
    print("missing_information:", result.missing_information)
    print("need_clarification:", result.need_clarification)
    print("questions:")
    for question in result.questions:
        print(f"- question: {question.question}")
        print(f"  reason: {question.reason}")


def main() -> None:
    """Run the two requested mock-understanding scenarios."""
    service = RequirementUnderstandingService()

    print("场景1：非空需求")
    print_result(service.understand("帮我规划一个 CNC 刀具管理功能"))

    print("\n场景2：空字符串")
    print_result(service.understand(""))


if __name__ == "__main__":
    main()
