"""Regression coverage for standalone deterministic HTML reports."""

from models.final_output import FinalProductPlan
from models.flow import FlowEdge, FlowNode, ProductFlow
from models.state import AgentStage, AgentState, ReviewFeedback, TaskContext
from report.html_report import generate_html_report


def plan(title: str = "设备维修工单方案") -> FinalProductPlan:
    """Build a representative current final plan."""
    return FinalProductPlan(
        title=title,
        summary="建立设备维修闭环。",
        problems=["故障处理过程不可追踪"],
        target_users=["设备操作员", "维修主管", "维修人员"],
        key_scenarios=["操作员发现故障并创建工单"],
        requirements=["创建工单", "主管派单", "维修结果确认"],
        solution=["使用维修工单串联处理过程"],
        mvp_scope=["报修", "派单", "维修处理"],
        future_scope=["维修知识推荐"],
        risks=["历史维修数据质量不足"],
    )


def flow() -> ProductFlow:
    """Build a small maintenance flow for Mermaid embedding."""
    return ProductFlow(
        title="设备维修主流程",
        description="从发现故障到确认完成。",
        nodes=[
            FlowNode(id="n1", label="发现故障", node_type="start"),
            FlowNode(id="n2", label="创建工单"),
            FlowNode(id="n3", label="维修完成?", node_type="decision"),
            FlowNode(id="n4", label="确认完成", node_type="end"),
        ],
        edges=[
            FlowEdge(source="n1", target="n2"),
            FlowEdge(source="n2", target="n3"),
            FlowEdge(source="n3", target="n4", label="是"),
            FlowEdge(source="n3", target="n2", label="否"),
        ],
    )


def state_with_plan(product_flow: ProductFlow | None) -> AgentState:
    """Build a completed V3 state with revision history."""
    return AgentState(
        task=TaskContext(
            task_id="html-report-demo",
            title="维修方案",
            original_request="规划设备维修工单",
            current_stage=AgentStage.COMPLETED,
            plan_version=3,
        ),
        final_output=plan(),
        product_flow=product_flow,
        review_feedback=[
            ReviewFeedback(
                version=2,
                version_from=1,
                version_to=2,
                feedback="增加维修主管派单",
                revision_summary=["补充主管派单步骤。"],
                revision_type="review_feedback",
            ),
            ReviewFeedback(
                version=3,
                version_from=2,
                version_to=3,
                feedback="增加操作员确认",
                revision_summary=["形成维修确认闭环。"],
                revision_type="added_condition",
            ),
        ],
    )


def main() -> None:
    """Cover flow, no-flow, escaping, and missing-final-plan behavior."""
    # Case A: complete report with Mermaid and revision lineage.
    html = generate_html_report(state_with_plan(flow()))
    for expected in (
        "<!doctype html>",
        "设备维修工单方案",
        "核心问题",
        "目标用户",
        "关键场景",
        "核心需求",
        "解决方案",
        "MVP 范围",
        "业务流程",
        "flowchart TD",
        "Revision History",
        "V1 → V2",
        "V2 → V3",
    ):
        assert expected in html

    # Case B: legacy/no-flow reports omit the complete business-flow section.
    no_flow_html = generate_html_report(state_with_plan(None))
    assert "<!doctype html>" in no_flow_html
    assert "业务流程" not in no_flow_html
    assert 'class="mermaid"' not in no_flow_html

    # Case C: all dynamic HTML text is escaped before insertion.
    unsafe_state = state_with_plan(
        ProductFlow(
            title='<Flow & "Title">',
            nodes=[FlowNode(id="n1", label="<开始>", node_type="start")],
        )
    )
    unsafe_state.final_output = plan('<产品 & "方案" \'测试\'>')
    unsafe_state.final_output.problems = ["<script>alert('x')</script> & 风险"]
    unsafe_state.review_feedback[0].feedback = '<修改 "意见" & 更多>'
    escaped_html = generate_html_report(unsafe_state)
    assert "<script>alert('x')</script>" not in escaped_html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp; 风险" in escaped_html
    assert "&lt;产品 &amp; &quot;方案&quot; &#x27;测试&#x27;&gt;" in escaped_html
    assert "&lt;修改 &quot;意见&quot; &amp; 更多&gt;" in escaped_html
    assert "&lt;Flow &amp; &quot;Title&quot;&gt;" in escaped_html

    # Case D: a report cannot be generated without a current final plan.
    missing = AgentState(
        task=TaskContext(
            task_id="missing-final-plan",
            title="未完成任务",
            original_request="尚未生成方案",
        )
    )
    try:
        generate_html_report(missing)
        raise AssertionError("Expected missing final plan to be rejected")
    except ValueError as error:
        assert str(error) == "Task has no final plan"

    print("Case A: complete report with ProductFlow and revisions")
    print("Case B: report omits Business Flow")
    print("Case C: dynamic text escaped")
    print("Case D: missing final plan rejected")


if __name__ == "__main__":
    main()
