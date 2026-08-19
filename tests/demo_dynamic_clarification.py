"""Demonstrate dynamic clarification counts and the four-question hard cap."""

import json

from agent.requirement_understanding import RequirementUnderstandingService
from agent.runtime import PMCopilotRuntime
from models.state import AgentStage, AgentState, TaskContext


class StubLLMClient:
    """Return one configured understanding response and capture its prompt."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.system_prompt = ""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        return json.dumps(self.payload, ensure_ascii=False)


def service_with(payload: dict) -> RequirementUnderstandingService:
    """Construct the service without environment-dependent LLM setup."""
    service = RequirementUnderstandingService.__new__(RequirementUnderstandingService)
    service.llm_client = StubLLMClient(payload)
    return service


def question(index: int) -> dict[str, str]:
    return {
        "question": f"关键问题 {index}？",
        "reason": f"答案会影响方案维度 {index}。",
    }


def main() -> None:
    """Cover ambiguous, detailed, over-limit, and zero-question requests."""
    ambiguous_service = service_with(
        {
            "known_facts": ["用户希望规划刀具管理系统"],
            "missing_information": ["业务现状", "核心目标", "目标用户"],
            "need_clarification": True,
            "questions": [question(1), question(2), question(3)],
        }
    )
    ambiguous = ambiguous_service.understand("帮我规划一个刀具管理系统")
    assert 0 < len(ambiguous.questions) <= 4
    assert "0～4" in ambiguous_service.llm_client.system_prompt

    detailed = service_with(
        {
            "known_facts": [
                "主要用户是工艺人员和设备操作员",
                "第一期解决工艺刀具关联和按加工时长统计寿命",
                "暂不考虑自动换刀",
            ],
            "missing_information": [],
            "need_clarification": False,
            "questions": [],
        }
    ).understand(
        "帮我规划刀具管理系统，主要给工艺人员和设备操作员使用，"
        "第一期解决工艺和刀具关联、刀具寿命按加工时长统计，"
        "暂时不考虑自动换刀。"
    )
    assert detailed.need_clarification is False
    assert detailed.questions == []

    capped = service_with(
        {
            "known_facts": [],
            "missing_information": ["多个关键条件"],
            "need_clarification": True,
            "questions": [question(index) for index in range(1, 7)],
        }
    ).understand("帮我规划一个刀具管理系统")
    assert len(capped.questions) == 4
    assert [item.question for item in capped.questions] == [
        "关键问题 1？",
        "关键问题 2？",
        "关键问题 3？",
        "关键问题 4？",
    ]

    zero_service = service_with(
        {
            "known_facts": ["需求信息充分"],
            "missing_information": [],
            "need_clarification": True,
            "questions": [],
        }
    )
    runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    runtime.requirement_understanding = zero_service
    state = runtime.start_task(
        AgentState(
            task=TaskContext(
                task_id="zero-clarification-demo",
                title="明确需求",
                original_request="信息充分的产品需求",
            )
        )
    )
    assert state.task.current_stage == AgentStage.PLANNING
    assert state.messages == []

    print("case A questions:", len(ambiguous.questions))
    print("case B questions:", len(detailed.questions))
    print("case C questions after cap:", len(capped.questions))
    print("case D stage:", state.task.current_stage.value)


if __name__ == "__main__":
    main()
