"""Prototype V2.6 structured condition planning and validation coverage."""

import copy
import json

from pydantic import ValidationError

from agent.prototype_planner import PrototypePlanner
from models.final_output import FinalProductPlan
from models.prototype import PrototypeCondition, PrototypeSpec
from tests.demo_prototype_planner_v25 import warehouse_response as v25_warehouse_response


class SequenceClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return json.dumps(self.responses[len(self.calls) - 1], ensure_ascii=False)


def plan(title: str, requirements: list[str]) -> FinalProductPlan:
    return FinalProductPlan(
        title=title,
        summary=title,
        target_users=["业务操作员", "业务主管"],
        key_scenarios=requirements,
        requirements=requirements,
        solution=requirements,
        mvp_scope=requirements,
    )


def condition(field: str, operator: str, *, value=None, value_field=None) -> dict:
    item = {"field": field, "operator": operator}
    if value is not None:
        item["value"] = value
    if value_field is not None:
        item["value_field"] = value_field
    return {"logic": "and", "conditions": [item]}


def maintenance_response() -> dict:
    return {"has_prototype": True, "prototype": {
        "title": "维修工单", "description": "条件交互", "default_page": "orders",
        "roles": [
            {"id": "operator", "name": "设备操作员"},
            {"id": "manager", "name": "维修主管"},
            {"id": "technician", "name": "维修人员"}],
        "default_role": "operator", "panels": [],
        "statuses": ["待派单", "维修中", "待确认", "已完成"], "status_transitions": [],
        "pages": [
            {"id": "orders", "title": "工单列表", "page_type": "list",
             "table": {"columns": [{"id": "status", "label": "状态", "field": "status", "column_type": "status"}],
                       "filters": [], "row_actions": [
                           {"id": "assign", "label": "主管派单", "action_type": "update_status", "visible_to_roles": ["manager"], "visible_when": condition("status", "equals", value="待派单")},
                           {"id": "repair", "label": "填写维修结果", "action_type": "navigate", "target": "repair-form", "visible_to_roles": ["technician"], "visible_when": condition("status", "equals", value="维修中")},
                           {"id": "confirm", "label": "确认完成", "action_type": "update_status", "visible_to_roles": ["operator"], "visible_when": condition("status", "equals", value="待确认")}]}},
            {"id": "repair-form", "title": "维修结果", "page_type": "form",
             "fields": [
                 {"id": "replace_part", "label": "是否更换备件", "field_type": "select", "options": ["是", "否"]},
                 {"id": "part_id", "label": "备件", "field_type": "select", "visible_when": condition("replace_part", "equals", value="是"), "required_when": condition("replace_part", "equals", value="是")},
                 {"id": "quantity", "label": "数量", "field_type": "number", "visible_when": condition("replace_part", "equals", value="是"), "required_when": condition("replace_part", "equals", value="是")}],
             "actions": [{"id": "submit-repair", "label": "提交维修结果", "action_type": "update_status", "visible_to_roles": ["technician"], "visible_when": condition("status", "equals", value="维修中")}]}
        ]}}


def warehouse_response() -> dict:
    return {"has_prototype": True, "prototype": {
        "title": "库存管理", "description": "条件交互", "default_page": "overview",
        "roles": [], "panels": [], "statuses": [], "status_transitions": [],
        "pages": [
            {"id": "overview", "title": "库存总览", "page_type": "dashboard",
             "components": [{"id": "low-alert", "component_type": "alert", "visible_when": condition("inventory_status", "equals", value="low")}],
             "alerts": [{"id": "low-stock", "message": "库存低于安全库存", "alert_type": "warning"}],
             "table": {"columns": [{"id": "inventory-status", "label": "库存状态", "field": "inventory_status", "column_type": "status"}], "filters": [], "row_actions": []}},
            {"id": "outbound", "title": "出库", "page_type": "form",
             "fields": [
                 {"id": "requested_quantity", "label": "出库数量", "field_type": "number"},
                 {"id": "available_quantity", "label": "当前库存", "field_type": "number"}],
             "actions": [{"id": "submit-outbound", "label": "提交出库", "action_type": "submit_form", "enabled_when": condition("requested_quantity", "less_than_or_equal", value_field="available_quantity")}]}
        ]}}


def main() -> None:
    client = SequenceClient([maintenance_response(), warehouse_response()])
    planner = PrototypePlanner.__new__(PrototypePlanner)
    planner.llm_client = client

    maintenance = planner.generate("规划维修工单条件交互", plan("维修工单", ["按角色和状态处理工单", "更换备件时填写备件和数量"]))
    assert maintenance is not None
    actions = {action.id: action for page in maintenance.pages for action in [*page.actions, *(page.table.row_actions if page.table else [])]}
    assert actions["assign"].visible_to_roles == ["manager"]
    assert actions["assign"].visible_when.conditions[0].value == "待派单"
    assert actions["repair"].visible_when.conditions[0].value == "维修中"
    assert actions["confirm"].visible_when.conditions[0].value == "待确认"
    repair_page = next(page for page in maintenance.pages if page.id == "repair-form")
    fields = {field.id: field for field in repair_page.fields}
    assert fields["part_id"].visible_when.conditions[0].field == "replace_part"
    assert fields["quantity"].required_when.conditions[0].value == "是"

    warehouse = planner.generate("规划库存条件交互", plan("库存管理", ["低库存时预警", "出库量不能超过库存量"]))
    assert warehouse is not None
    alert = warehouse.pages[0].components[0]
    outbound = warehouse.pages[1].actions[0]
    assert alert.visible_when.conditions[0].field == "inventory_status"
    cross_field = outbound.enabled_when.conditions[0]
    assert cross_field.operator == "less_than_or_equal"
    assert cross_field.value_field == "available_quantity"

    # Invalid field references remain strict.
    invalid = maintenance_response()["prototype"]
    invalid["pages"][1]["fields"][1]["visible_when"] = condition("abc_not_exists", "equals", value="是")
    try:
        PrototypeSpec.model_validate(invalid)
    except ValidationError as error:
        assert "condition fields must reference a field" in str(error)
    else:
        raise AssertionError("Unknown condition fields must fail")

    # Operator/value contracts reject obvious mistakes.
    try:
        PrototypeCondition.model_validate({"field": "status", "operator": "in", "value": "abc"})
    except ValidationError:
        pass
    else:
        raise AssertionError("in requires a list value")
    try:
        PrototypeCondition.model_validate({"field": "quantity", "operator": "equals", "value": 1, "value_field": "available_quantity"})
    except ValidationError:
        pass
    else:
        raise AssertionError("value and value_field are mutually exclusive")

    # A V2.5 payload has no rules and remains valid.
    legacy_v25 = PrototypeSpec.model_validate(copy.deepcopy(v25_warehouse_response()["prototype"]))
    assert legacy_v25.pages[0].visible_when is None
    assert all(action.visible_when is None for page in legacy_v25.pages for action in page.actions)

    prompt = client.calls[0][0]
    assert "Prototype V2.6" in prompt and "value_field" in prompt
    assert "不要为了增加复杂度" in prompt
    print("Maintenance conditions:", {key: item.visible_when.model_dump() for key, item in actions.items() if item.visible_when})
    print("Warehouse alert:", alert.visible_when.model_dump())
    print("Warehouse outbound:", outbound.enabled_when.model_dump())
    print("Invalid condition cases and V2.5 compatibility: passed")


if __name__ == "__main__":
    main()
