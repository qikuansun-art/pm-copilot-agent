"""Demonstrate product analysis with the configured real LLM."""

from agent.product_analyzer import ProductAnalyzer
from models.state import AgentState, Decision, Evidence, TaskContext


def main() -> None:
    """Analyze the CNC task using its facts, decision, and evidence."""
    internal_evidence = [
        "当前刀具主要包括锯片和铣刀",
        "公司希望建立工艺库与刀具库的对应关系",
        "刀具寿命第一阶段按加工时长统计",
        "当前设备暂无自动换刀",
        "后续需要支持换刀和断刀流程",
    ]
    external_evidence = [
        "CNC 刀具管理通常需要维护刀具身份、规格、状态和适用工艺",
        "刀具寿命可通过累计加工时间进行管理和预警",
    ]

    state = AgentState(
        task=TaskContext(
            task_id="real-product-analysis-demo",
            title="CNC 刀具管理规划",
            original_request="帮我规划一个 CNC 刀具管理功能",
            known_facts=[
                "当前没有系统化刀具管理",
                "主要目标是建立工艺与刀具关联",
                "需要管理刀具寿命",
                "主要使用者是工艺人员和设备操作员",
            ],
        ),
        decisions=[
            Decision(
                decision="自动换刀暂不进入 MVP",
                reason="当前阶段先建立刀具管理基础能力",
                decided_by="user",
            )
        ],
        evidence=[
            *[
                Evidence(
                    content=content,
                    source_type="knowledge",
                    source="knowledge/cnc_context.md",
                    confidence="high",
                )
                for content in internal_evidence
            ],
            *[
                Evidence(
                    content=content,
                    source_type="web",
                    source="https://example.com/cnc-tool-management",
                    confidence="medium",
                )
                for content in external_evidence
            ],
        ],
    )

    analyzer = ProductAnalyzer()
    analysis = analyzer.analyze(state)

    print("problems:", analysis.problems)
    print("users:", analysis.users)
    print("scenarios:", analysis.scenarios)
    print("requirements:", analysis.requirements)
    print("solution:", analysis.solution)
    print("mvp_scope:", analysis.mvp_scope)
    print("future_scope:", analysis.future_scope)
    print("risks:", analysis.risks)


if __name__ == "__main__":
    main()
