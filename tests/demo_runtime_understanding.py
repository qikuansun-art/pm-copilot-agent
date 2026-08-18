"""Demonstrate the first AgentState transition through the runtime."""

from agent.runtime import PMCopilotRuntime
from models.state import AgentState, Message, TaskContext


def main() -> None:
    """Run and print the CNC requirement-understanding state transition."""
    state = AgentState(
        task=TaskContext(
            task_id="runtime-demo",
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

    result = PMCopilotRuntime().start_task(state)

    print(result.task.current_stage)
    print(result.task.known_facts)
    print(result.task.missing_information)
    print(result.messages)


if __name__ == "__main__":
    main()
