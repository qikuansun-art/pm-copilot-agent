"""Minimal demonstration of constructing and printing an AgentState."""

from models.state import AgentPlan, AgentState, Decision, Message, PlanStep, TaskContext


def main() -> None:
    """Build and print a CNC tool management task state."""
    task = TaskContext(
        task_id="cnc-tool-management-demo",
        title="CNC 刀具管理规划",
        original_request="帮我规划一个 CNC 刀具管理功能",
        known_facts=[
            "当前没有系统化刀具管理",
            "未来考虑自动换刀",
        ],
        missing_information=[
            "当前刀具有哪些类型",
            "谁是主要使用者",
        ],
    )

    messages = [
        Message(role="user", content="帮我规划一个 CNC 刀具管理功能"),
        Message(
            role="assistant",
            content="我需要先确认当前刀具管理方式和主要使用者。",
        ),
    ]

    plan = AgentPlan(
        goal="输出 CNC 刀具管理 MVP 产品方案",
        steps=[
            PlanStep(id=1, title="理解需求", status="completed"),
            PlanStep(id=2, title="补充上下文", status="running"),
            PlanStep(id=3, title="内部资料检索", status="pending"),
            PlanStep(id=4, title="外部调研", status="pending"),
            PlanStep(id=5, title="产品分析", status="pending"),
            PlanStep(id=6, title="输出方案", status="pending"),
        ],
    )

    decisions = [
        Decision(
            decision="自动换刀暂不进入 MVP",
            reason="当前阶段先建立刀具管理基础能力",
            decided_by="user",
        )
    ]

    state = AgentState(
        task=task,
        messages=messages,
        plan=plan,
        decisions=decisions,
    )

    print("task:")
    print(state.task)
    print("\nmessages:")
    print(state.messages)
    print("\nplan:")
    print(state.plan)
    print("\ndecisions:")
    print(state.decisions)
    print("\ncomplete state:")
    print(state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
