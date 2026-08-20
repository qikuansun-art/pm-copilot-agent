"""Validate dynamic internal-query structure and retrieval effectiveness."""

import re

from agent.research_planner import ResearchPlanner
from models.research import ResearchPlan
from models.state import AgentPlan, AgentState, PlanStep, TaskContext
from tools.knowledge_search import KnowledgeSearchTool


def build_state(task_id: str, title: str, original_request: str) -> AgentState:
    """Build a representative planned state for the research planner."""
    return AgentState(
        task=TaskContext(
            task_id=task_id,
            title=title,
            original_request=original_request,
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


def query_tokens(plan: ResearchPlan) -> list[str]:
    """Validate and return space-delimited atomic internal-query tokens."""
    tokens = plan.internal_query.split()
    assert 3 <= len(tokens) <= 6
    assert plan.internal_query == " ".join(tokens)
    assert all(not re.search(r"[，。！？；：,!?;:]", token) for token in tokens)
    assert all(len(token) <= 8 for token in tokens)
    return tokens


def main() -> None:
    """Cover a cross-domain request and a maintenance-work-order request."""
    planner = ResearchPlanner()

    cross_domain_state = build_state(
        "research-cross-domain-demo",
        "荒料加工与刀具使用管理",
        "帮我规划石材荒料加工中的刀具使用管理，既要管理荒料从入库到大切的加工流程，"
        "也要管理刀具与工艺关联和刀具寿命。",
    )
    cross_domain_plan = planner.create_research_plan(cross_domain_state)
    cross_domain_tokens = query_tokens(cross_domain_plan)
    assert any(
        any(term in token for term in ("石材", "荒料", "入库", "大切"))
        for token in cross_domain_tokens
    )
    assert any(
        any(term in token for term in ("刀具", "寿命", "工艺"))
        for token in cross_domain_tokens
    )
    assert "石材荒料加工流程" not in cross_domain_tokens

    results = KnowledgeSearchTool().search(
        cross_domain_plan.internal_query,
        knowledge_group_ids=[],
    )
    uploaded_sources = {
        item.source for item in results if item.source_type == "uploaded_document"
    }
    assert "stone_block_processing.md" in uploaded_sources
    assert "tool_management.md" in uploaded_sources

    maintenance_state = build_state(
        "research-maintenance-demo",
        "设备维修工单管理",
        "规划设备维修工单，由维修主管派单，并对处理超时进行提醒。",
    )
    maintenance_plan = planner.create_research_plan(maintenance_state)
    maintenance_tokens = query_tokens(maintenance_plan)
    assert "设备维修工单管理流程" not in maintenance_tokens
    assert any("工单" in token for token in maintenance_tokens)
    assert any("派单" in token or "维修主管" in token for token in maintenance_tokens)

    print("Case A internal_query:", cross_domain_plan.internal_query)
    print("Case A uploaded documents:", sorted(uploaded_sources))
    print("Case B internal_query:", maintenance_plan.internal_query)


if __name__ == "__main__":
    main()
