"""Demonstrate task-specific research planning for two distinct domains."""

from agent.research_planner import ResearchPlanner
from models.research import ResearchPlan
from models.state import AgentPlan, AgentState, PlanStep, TaskContext


def build_state(
    task_id: str,
    title: str,
    original_request: str,
    known_facts: list[str],
) -> AgentState:
    """Build a representative planned state for the research planner."""
    return AgentState(
        task=TaskContext(
            task_id=task_id,
            title=title,
            original_request=original_request,
            known_facts=known_facts,
        ),
        plan=AgentPlan(
            goal=f"完成{title}的产品规划",
            steps=[
                PlanStep(id=1, title="理解需求", status="completed"),
                PlanStep(id=2, title="需求澄清", status="completed"),
                PlanStep(id=3, title="资料调研", status="pending"),
                PlanStep(id=4, title="产品分析", status="pending"),
                PlanStep(id=5, title="最终方案", status="pending"),
            ],
        ),
    )


def print_research_plan(task_name: str, research_plan: ResearchPlan) -> None:
    """Print the requested research plan fields."""
    print(f"\n{task_name}")
    print("internal_query:", research_plan.internal_query)
    print("external_query:", research_plan.external_query)
    print("research_focus:", research_plan.research_focus)


def main() -> None:
    """Generate research plans for CNC tooling and stone-block processing."""
    planner = ResearchPlanner()

    cnc_state = build_state(
        task_id="research-cnc-demo",
        title="CNC 刀具管理功能",
        original_request="帮我规划一个 CNC 刀具管理功能",
        known_facts=["需要工艺与刀具关联", "需要刀具寿命管理"],
    )
    cnc_plan = planner.create_research_plan(cnc_state)
    print_research_plan("任务 A：CNC 刀具管理", cnc_plan)

    stone_state = build_state(
        task_id="research-stone-demo",
        title="石材荒料加工管理功能",
        original_request="帮我规划一个石材荒料加工管理功能",
        known_facts=[
            "当前没有系统化管理",
            "希望梳理荒料从入库到加工出库的流程",
            "后续考虑扫描并用于销售展示",
        ],
    )
    stone_plan = planner.create_research_plan(stone_state)
    print_research_plan("任务 B：石材荒料加工管理", stone_plan)

    stone_queries = f"{stone_plan.internal_query} {stone_plan.external_query}"
    forbidden_terms = ("刀具", "自动换刀", "刀具寿命")
    unexpected_terms = [term for term in forbidden_terms if term in stone_queries]
    assert not unexpected_terms, f"荒料任务查询包含无关词：{unexpected_terms}"


if __name__ == "__main__":
    main()
