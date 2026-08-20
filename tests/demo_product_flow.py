"""Demonstrate structured product-flow generation with deterministic LLM output."""

import json

from agent.flow_generator import ProductFlowGenerator
from models.final_output import FinalProductPlan


class SequenceLLMClient:
    """Return prepared flow decisions and retain generation prompts."""

    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.prompts: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.prompts.append((system_prompt, user_prompt))
        return json.dumps(
            self.responses[len(self.prompts) - 1],
            ensure_ascii=False,
        )


def maintenance_plan() -> FinalProductPlan:
    """Build a repair-work-order plan with an explicit business workflow."""
    return FinalProductPlan(
        title="设备维修工单管理方案",
        summary="建立从报修到确认完成的维修闭环。",
        problems=["设备故障处理过程无法追踪"],
        target_users=["设备操作员", "维修主管", "维修人员"],
        key_scenarios=["操作员发现故障并创建维修工单"],
        requirements=[
            "操作员创建维修工单",
            "维修主管派单",
            "维修人员接单处理",
            "维修人员填写维修结果",
            "操作员确认完成",
        ],
        solution=["通过维修工单串联报修、派单、处理和确认"],
        mvp_scope=["工单创建", "主管派单", "维修处理", "结果确认"],
    )


def information_plan() -> FinalProductPlan:
    """Build a pure information-display plan without business handoffs."""
    return FinalProductPlan(
        title="行业资讯展示页",
        summary="集中展示行业资讯。",
        target_users=["访客"],
        key_scenarios=["访客浏览资讯"],
        requirements=["展示资讯标题、摘要和发布时间"],
        solution=["提供只读资讯列表和详情"],
        mvp_scope=["资讯列表", "资讯详情"],
    )


def main() -> None:
    """Cover one explicit repair flow and one no-flow information plan."""
    repair_flow_response = {
        "has_flow": True,
        "flow": {
            "title": "设备维修工单主流程",
            "description": "从发现故障到操作员确认完成。",
            "nodes": [
                {"id": "n1", "label": "发现设备故障", "node_type": "start"},
                {"id": "n2", "label": "创建维修工单", "node_type": "step"},
                {"id": "n3", "label": "维修主管派单", "node_type": "step"},
                {"id": "n4", "label": "维修人员处理", "node_type": "step"},
                {"id": "n5", "label": "填写维修结果", "node_type": "step"},
                {"id": "n6", "label": "维修是否完成", "node_type": "decision"},
                {"id": "n7", "label": "操作员确认", "node_type": "step"},
                {"id": "n8", "label": "维修工单完成", "node_type": "end"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "label": ""},
                {"source": "n2", "target": "n3", "label": ""},
                {"source": "n3", "target": "n4", "label": ""},
                {"source": "n4", "target": "n5", "label": ""},
                {"source": "n5", "target": "n6", "label": ""},
                {"source": "n6", "target": "n7", "label": "是"},
                {"source": "n6", "target": "n4", "label": "否"},
                {"source": "n7", "target": "n8", "label": ""},
            ],
        },
    }
    client = SequenceLLMClient([repair_flow_response, {"has_flow": False}])
    generator = ProductFlowGenerator.__new__(ProductFlowGenerator)
    generator.llm_client = client

    repair_flow = generator.generate(
        "规划设备维修工单管理，实现报修、派单、维修和确认闭环。",
        maintenance_plan(),
    )
    assert repair_flow is not None
    labels = [node.label for node in repair_flow.nodes]
    assert any("故障" in label for label in labels)
    assert any("工单" in label for label in labels)
    assert any("派单" in label for label in labels)
    assert any("维修" in label and "处理" in label for label in labels)
    assert any("结果" in label for label in labels)
    assert any("确认" in label for label in labels)
    assert any(node.node_type == "decision" for node in repair_flow.nodes)

    no_flow = generator.generate(
        "规划一个只读行业资讯展示页面。",
        information_plan(),
    )
    assert no_flow is None

    _, repair_user_prompt = client.prompts[0]
    prompt_context = json.loads(repair_user_prompt.split("\n", 1)[1])
    assert set(prompt_context["final_output"]) == {
        "problems",
        "target_users",
        "key_scenarios",
        "requirements",
        "solution",
        "mvp_scope",
    }

    print("Case A nodes:", labels)
    print("Case A decision:", next(
        node.label for node in repair_flow.nodes if node.node_type == "decision"
    ))
    print("Case B flow: None")


if __name__ == "__main__":
    main()
