"""Demonstrate advancing AgentState after a user clarification response."""

from agent.runtime import PMCopilotRuntime
from models.state import AgentStage, AgentState, Message, TaskContext


def main() -> None:
    """Run the clarification-response state transition and print its result."""
    state = AgentState(
        task=TaskContext(
            task_id="clarification-response-demo",
            title="CNC 刀具管理规划",
            original_request="帮我规划一个 CNC 刀具管理功能",
        ),
        messages=[
            Message(
                role="user",
                content="帮我规划一个 CNC 刀具管理功能",
            )
        ],
    )

    runtime = PMCopilotRuntime()
    runtime.start_task(state)
    assert state.task.current_stage == AgentStage.WAITING_CLARIFICATION

    result = runtime.handle_clarification_response(
        state,
        "目前完全没有系统化刀具管理，主要想解决工艺和刀具关联以及寿命管理，"
        "主要使用者是工艺人员和设备操作员。",
    )

    print("current_stage:", result.task.current_stage)
    print("known_facts:", result.task.known_facts)
    print("missing_information:", result.task.missing_information)
    print("messages:", result.messages)


if __name__ == "__main__":
    main()
