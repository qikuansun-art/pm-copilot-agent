"""Demonstrate structured MVP interaction-prototype planning."""

import json

from agent.prototype_planner import PrototypePlanner
from models.final_output import FinalProductPlan
from models.flow import FlowEdge, FlowNode, ProductFlow


class SequenceLLMClient:
    """Return prepared prototype specifications and retain prompt context."""

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
    """Build an explicit repair-work-order MVP plan."""
    return FinalProductPlan(
        title="设备维修工单方案",
        summary="建立从报修到确认完成的维修闭环。",
        target_users=["设备操作员", "维修主管", "维修人员"],
        key_scenarios=["操作员发现故障并创建维修工单"],
        requirements=[
            "操作员创建工单",
            "维修主管派单",
            "维修人员维修",
            "填写维修结果",
            "操作员确认完成",
        ],
        solution=["使用工单串联报修、派单、维修和确认"],
        mvp_scope=["工单列表", "创建工单", "维修处理", "完成确认"],
        future_scope=["AI 故障诊断", "备件自动采购"],
    )


def maintenance_flow() -> ProductFlow:
    """Build the primary business flow supplied as optional planner context."""
    return ProductFlow(
        title="维修工单主流程",
        nodes=[
            FlowNode(id="n1", label="创建工单", node_type="start"),
            FlowNode(id="n2", label="主管派单"),
            FlowNode(id="n3", label="维修处理"),
            FlowNode(id="n4", label="确认完成", node_type="end"),
        ],
        edges=[
            FlowEdge(source="n1", target="n2"),
            FlowEdge(source="n2", target="n3"),
            FlowEdge(source="n3", target="n4"),
        ],
    )


def information_plan() -> FinalProductPlan:
    """Build a pure device-parameter display MVP."""
    return FinalProductPlan(
        title="设备参数展示",
        summary="集中展示设备运行参数。",
        target_users=["设备操作员"],
        key_scenarios=["操作员查看设备概况和参数详情"],
        requirements=["展示设备状态", "查看温度、转速和运行时长"],
        solution=["提供设备概览和参数详情"],
        mvp_scope=["设备概览", "参数详情"],
    )


def main() -> None:
    """Cover workflow-oriented and information-display prototypes."""
    maintenance_response = {
        "has_prototype": True,
        "prototype": {
            "title": "维修工单交互原型",
            "description": "覆盖报修、派单、维修和完成确认。",
            "default_page": "work-order-list",
            "pages": [
                {
                    "id": "work-order-list",
                    "title": "工单列表",
                    "page_type": "list",
                    "fields": [
                        {"id": "status", "label": "工单状态", "field_type": "select", "options": ["待派单", "维修中", "待确认", "已完成"]}
                    ],
                    "actions": [
                        {"id": "create-order", "label": "新建工单", "action_type": "navigate", "target": "work-order-create"},
                        {"id": "view-order", "label": "查看详情", "action_type": "navigate", "target": "work-order-detail"},
                    ],
                },
                {
                    "id": "work-order-create",
                    "title": "新建工单",
                    "page_type": "form",
                    "fields": [
                        {"id": "fault", "label": "故障描述", "field_type": "textarea", "required": True}
                    ],
                    "actions": [
                        {"id": "submit-order", "label": "提交工单", "action_type": "submit_form", "target": "work-order-list"}
                    ],
                },
                {
                    "id": "work-order-detail",
                    "title": "工单详情",
                    "page_type": "detail",
                    "fields": [],
                    "actions": [
                        {"id": "assign-order", "label": "主管派单", "action_type": "update_status"},
                        {"id": "start-repair", "label": "维修处理", "action_type": "navigate", "target": "repair-form"},
                        {"id": "confirm-order", "label": "确认完成", "action_type": "update_status"},
                    ],
                },
                {
                    "id": "repair-form",
                    "title": "维修处理",
                    "page_type": "form",
                    "fields": [
                        {"id": "repair-result", "label": "维修结果", "field_type": "textarea", "required": True}
                    ],
                    "actions": [
                        {"id": "submit-repair", "label": "提交维修结果", "action_type": "submit_form", "target": "work-order-detail"}
                    ],
                },
            ],
        },
    }
    information_response = {
        "has_prototype": True,
        "prototype": {
            "title": "设备参数展示原型",
            "description": "查看设备概况和参数。",
            "default_page": "device-dashboard",
            "pages": [
                {
                    "id": "device-dashboard",
                    "title": "设备概览",
                    "page_type": "dashboard",
                    "fields": [],
                    "actions": [
                        {"id": "view-parameters", "label": "查看参数", "action_type": "navigate", "target": "parameter-detail"}
                    ],
                },
                {
                    "id": "parameter-detail",
                    "title": "参数详情",
                    "page_type": "detail",
                    "fields": [
                        {"id": "temperature", "label": "温度", "field_type": "number"},
                        {"id": "speed", "label": "转速", "field_type": "number"},
                    ],
                    "actions": [],
                },
            ],
        },
    }

    client = SequenceLLMClient([maintenance_response, information_response])
    planner = PrototypePlanner.__new__(PrototypePlanner)
    planner.llm_client = client

    maintenance = planner.generate(
        "规划设备维修工单管理。",
        maintenance_plan(),
        maintenance_flow(),
    )
    assert maintenance is not None
    page_titles = [page.title for page in maintenance.pages]
    assert "工单列表" in page_titles
    assert any("新建工单" in title for title in page_titles)
    assert any("工单详情" in title or "维修处理" in title for title in page_titles)
    action_labels = [
        action.label for page in maintenance.pages for action in page.actions
    ]
    assert any("新建" in label for label in action_labels)
    assert any("查看" in label for label in action_labels)
    assert any("提交" in label for label in action_labels)
    assert any("派单" in label or "确认" in label for label in action_labels)

    information = planner.generate(
        "规划纯设备参数展示页面。",
        information_plan(),
    )
    assert information is not None
    assert {page.page_type for page in information.pages} <= {"dashboard", "detail"}

    first_context = json.loads(client.prompts[0][1].split("\n", 1)[1])
    assert "future_scope" not in first_context["final_output"]
    assert first_context["final_output"]["mvp_scope"] == maintenance_plan().mvp_scope
    assert first_context["product_flow"]["title"] == "维修工单主流程"

    print("Case A pages:", page_titles)
    print("Case A actions:", action_labels)
    print("Case B pages:", [page.title for page in information.pages])
    print("MVP-only context: True")


if __name__ == "__main__":
    main()
