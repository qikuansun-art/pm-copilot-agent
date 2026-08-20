"""Regression coverage for Prototype Planner V2 structures."""

import json

from agent.prototype_planner import PrototypePlanner
from models.final_output import FinalProductPlan
from models.flow import FlowEdge, FlowNode, ProductFlow
from models.prototype import PrototypeSpec


class StubLLMClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.prompts.append((system_prompt, user_prompt))
        return json.dumps(self.response, ensure_ascii=False)


def maintenance_plan() -> FinalProductPlan:
    return FinalProductPlan(
        title="设备维修工单管理",
        summary="形成从报修、派单、维修到确认的闭环。",
        target_users=["设备操作员", "维修主管", "维修人员"],
        key_scenarios=["操作员报修", "主管派单", "维修人员处理", "操作员确认"],
        requirements=["新建工单", "主管派单", "维修处理", "提交维修结果", "确认完成"],
        solution=["按工单状态驱动维修协作"],
        mvp_scope=["工单列表", "新建工单", "派单", "维修处理", "完成确认"],
        future_scope=["AI 诊断"],
    )


def maintenance_flow() -> ProductFlow:
    return ProductFlow(
        title="维修主流程",
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


def v2_response() -> dict:
    return {
        "has_prototype": True,
        "prototype": {
            "title": "维修工单 Prototype V2",
            "description": "按角色表达维修工单 MVP。",
            "default_page": "orders",
            "roles": [
                {"id": "operator", "name": "设备操作员"},
                {"id": "manager", "name": "维修主管"},
                {"id": "technician", "name": "维修人员"},
            ],
            "default_role": "operator",
            "pages": [
                {
                    "id": "orders",
                    "title": "工单列表",
                    "page_type": "list",
                    "tabs": [
                        {"id": "unassigned", "label": "待派单"},
                        {"id": "repairing", "label": "维修中"},
                        {"id": "confirming", "label": "待确认"},
                        {"id": "completed", "label": "已完成"},
                    ],
                    "table": {
                        "search_enabled": True,
                        "columns": [
                            {"id": "order-no", "label": "工单编号", "field": "order_no", "column_type": "text"},
                            {"id": "device", "label": "设备", "field": "device", "column_type": "text"},
                            {"id": "fault", "label": "故障", "field": "fault", "column_type": "text"},
                            {"id": "status", "label": "状态", "field": "status", "column_type": "status"},
                            {"id": "updated-at", "label": "更新时间", "field": "updated_at", "column_type": "date"},
                        ],
                        "filters": [
                            {"id": "status-filter", "label": "状态", "filter_type": "status", "options": ["待派单", "维修中", "待确认", "已完成"]},
                            {"id": "keyword", "label": "搜索", "filter_type": "search"},
                        ],
                        "row_actions": [
                            {"id": "assign", "label": "主管派单", "action_type": "open_drawer", "target": "assign-drawer", "visible_to_roles": ["manager"]},
                            {"id": "repair", "label": "维修处理", "action_type": "navigate", "target": "repair-detail", "visible_to_roles": ["technician"]},
                        ],
                    },
                    "actions": [
                        {"id": "create", "label": "新建工单", "action_type": "navigate", "target": "create-order", "visible_to_roles": ["operator"]}
                    ],
                },
                {"id": "create-order", "title": "新建工单", "page_type": "form", "visible_to_roles": ["operator"]},
                {
                    "id": "repair-detail",
                    "title": "工单详情与处理",
                    "page_type": "detail",
                    "actions": [
                        {"id": "submit-result", "label": "提交维修结果", "action_type": "update_status", "visible_to_roles": ["technician"]},
                        {"id": "confirm-complete", "label": "确认完成", "action_type": "update_status", "visible_to_roles": ["operator"]},
                    ],
                },
            ],
            "panels": [
                {
                    "id": "assign-drawer",
                    "title": "主管派单",
                    "panel_type": "drawer",
                    "fields": [
                        {"id": "assignee", "label": "维修人员", "field_type": "select", "required": True, "options": ["维修人员 A", "维修人员 B"]},
                        {"id": "note", "label": "备注", "field_type": "textarea"},
                    ],
                    "actions": [
                        {"id": "confirm-assign", "label": "确认派单", "action_type": "update_status", "visible_to_roles": ["manager"]}
                    ],
                }
            ],
            "statuses": ["待派单", "维修中", "待确认", "已完成"],
            "status_transitions": [
                {"from_status": "待派单", "action_id": "confirm-assign", "to_status": "维修中"},
                {"from_status": "维修中", "action_id": "submit-result", "to_status": "待确认"},
                {"from_status": "待确认", "action_id": "confirm-complete", "to_status": "已完成"},
            ],
        },
    }


def main() -> None:
    client = StubLLMClient(v2_response())
    planner = PrototypePlanner.__new__(PrototypePlanner)
    planner.llm_client = client
    spec = planner.generate("规划设备维修工单管理。", maintenance_plan(), maintenance_flow())
    assert spec is not None

    assert [role.name for role in spec.roles] == ["设备操作员", "维修主管", "维修人员"]
    orders = next(page for page in spec.pages if page.id == "orders")
    assert orders.table is not None and orders.table.search_enabled
    assert [column.label for column in orders.table.columns] == ["工单编号", "设备", "故障", "状态", "更新时间"]
    assert {item.filter_type for item in orders.table.filters} == {"status", "search"}
    assert [tab.label for tab in orders.tabs] == ["待派单", "维修中", "待确认", "已完成"]

    actions = {
        action.id: action
        for page in spec.pages
        for action in [*page.actions, *(page.table.row_actions if page.table else [])]
    }
    actions.update({action.id: action for panel in spec.panels for action in panel.actions})
    assert actions["assign"].visible_to_roles == ["manager"]
    assert actions["repair"].visible_to_roles == ["technician"]
    assert actions["create"].visible_to_roles == ["operator"]
    assert actions["confirm-complete"].visible_to_roles == ["operator"]

    drawer = next(panel for panel in spec.panels if panel.panel_type == "drawer")
    assert actions["assign"].target == drawer.id
    assert {field.field_type for field in drawer.fields} == {"select", "textarea"}
    assert any("派单" in action.label for action in drawer.actions)

    assert spec.statuses == ["待派单", "维修中", "待确认", "已完成"]
    assert all(transition.action_id in actions for transition in spec.status_transitions)
    assert [(item.from_status, item.to_status) for item in spec.status_transitions] == [
        ("待派单", "维修中"), ("维修中", "待确认"), ("待确认", "已完成")
    ]

    prompt, user_prompt = client.prompts[0]
    assert "Prototype V2" in prompt
    assert "角色" in prompt and "table" in prompt and "status_transitions" in prompt
    assert "Future Scope" in prompt  # prohibition is explicit in instructions
    context = json.loads(user_prompt.split("\n", 1)[1])
    assert "future_scope" not in context["final_output"]

    v1_payload = {
        "title": "V1 原型",
        "description": "旧格式",
        "default_page": "home",
        "pages": [{"id": "home", "title": "首页", "page_type": "dashboard", "fields": [], "actions": []}],
    }
    legacy = PrototypeSpec.model_validate(v1_payload)
    assert legacy.roles == [] and legacy.panels == [] and legacy.statuses == []
    assert legacy.pages[0].table is None and legacy.pages[0].tabs == []

    invalid = v2_response()["prototype"]
    invalid["status_transitions"][0]["action_id"] = "missing-action"
    try:
        PrototypeSpec.model_validate(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown transition action must be rejected")

    print("Roles:", [role.name for role in spec.roles])
    print("Table columns:", [column.label for column in orders.table.columns])
    print("Tabs:", [tab.label for tab in orders.tabs])
    print("Drawer:", drawer.title, [field.label for field in drawer.fields])
    print("Transitions:", [(item.from_status, item.to_status) for item in spec.status_transitions])
    print("V1 compatibility and invalid-reference validation: passed")


if __name__ == "__main__":
    main()
