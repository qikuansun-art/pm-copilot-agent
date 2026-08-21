"""Prototype V2.5 layout, component-tree, renderer, and domain checks."""

import json

from agent.prototype_planner import PrototypePlanner
from models.final_output import FinalProductPlan
from models.prototype import PrototypeSpec
from prototype.html_prototype import generate_interactive_prototype


class SequenceClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.prompts: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.prompts.append((system_prompt, user_prompt))
        return json.dumps(self.responses[len(self.prompts) - 1], ensure_ascii=False)


def plan(title: str, scenarios: list[str], requirements: list[str]) -> FinalProductPlan:
    return FinalProductPlan(
        title=title,
        summary=title,
        target_users=["业务操作员", "业务主管"],
        key_scenarios=scenarios,
        requirements=requirements,
        solution=["以核心业务流程组织工作台、列表和详情"],
        mvp_scope=requirements,
    )


def maintenance_response() -> dict:
    return {"has_prototype": True, "prototype": {
        "title": "设备维修工作台", "description": "维修 MVP", "default_page": "orders",
        "roles": [{"id": "operator", "name": "设备操作员"}, {"id": "manager", "name": "维修主管"}],
        "default_role": "operator", "panels": [], "statuses": [], "status_transitions": [],
        "pages": [
            {"id": "orders", "title": "工单列表", "page_type": "list",
             "layout": {"layout_type": "dashboard_grid"},
             "components": [
                 {"id": "order-cards", "component_type": "cards", "region": "top", "order": 1},
                 {"id": "order-tabs", "component_type": "tabs", "region": "main", "order": 2},
                 {"id": "order-table", "component_type": "table", "region": "main", "order": 3}],
             "cards": [{"id": "pending-count", "label": "待处理", "value": 6}],
             "tabs": [{"id": "all", "label": "全部"}],
             "table": {"columns": [
                 {"id": "device", "label": "设备名称", "field": "device_name", "column_type": "text"},
                 {"id": "fault", "label": "故障描述", "field": "fault_description", "column_type": "text"}],
                 "search_enabled": True, "filters": [], "row_actions": []}},
            {"id": "order-detail", "title": "工单详情", "page_type": "detail",
             "layout": {"layout_type": "two_column", "left_width": 2, "right_width": 1},
             "components": [
                 {"id": "detail-main", "component_type": "detail", "region": "left", "order": 1},
                 {"id": "repair-history", "component_type": "timeline", "region": "left", "order": 2},
                 {"id": "detail-actions", "component_type": "actions", "region": "right", "order": 3},
                 {"id": "timeout-alert", "component_type": "alert", "region": "right", "order": 4}],
             "fields": [
                 {"id": "repair_result", "label": "维修结果", "field_type": "textarea"},
                 {"id": "spare_parts", "label": "备件", "field_type": "text"}],
             "detail_sections": [
                 {"id": "device-info", "title": "设备信息", "fields": ["device_name"], "order": 1},
                 {"id": "fault-info", "title": "故障信息", "fields": ["fault_description"], "order": 2},
                 {"id": "repair-info", "title": "维修结果", "fields": ["repair_result", "spare_parts"], "order": 3}],
             "timeline_items": [{"id": "reported", "title": "已报修", "description": "操作员提交工单", "status": "完成"}],
             "alerts": [{"id": "overdue", "message": "工单即将超时", "alert_type": "warning"}],
             "actions": [{"id": "finish", "label": "提交维修结果", "action_type": "update_status"}]}
        ]}}


def warehouse_response() -> dict:
    return {"has_prototype": True, "prototype": {
        "title": "仓库库存管理", "description": "库存 MVP", "default_page": "inventory-overview",
        "roles": [], "panels": [], "statuses": [], "status_transitions": [],
        "pages": [
            {"id": "inventory-overview", "title": "库存总览", "page_type": "dashboard",
             "layout": {"layout_type": "dashboard_grid"},
             "components": [
                 {"id": "inventory-cards", "component_type": "cards", "region": "top", "order": 1},
                 {"id": "stock-alerts", "component_type": "alert", "region": "main", "order": 2}],
             "cards": [{"id": "sku-count", "label": "SKU 数", "value": 128}],
             "alerts": [{"id": "low-stock", "message": "3 个物料库存不足", "alert_type": "warning"}]},
            {"id": "inventory-list", "title": "库存列表", "page_type": "list",
             "layout": {"layout_type": "single_column"},
             "components": [
                 {"id": "inventory-table", "component_type": "table", "order": 1},
                 {"id": "inventory-actions", "component_type": "actions", "region": "bottom", "order": 2}],
             "table": {"columns": [
                 {"id": "sku", "label": "物料编码", "field": "sku", "column_type": "text"},
                 {"id": "quantity", "label": "库存数量", "field": "quantity", "column_type": "number"}],
                 "search_enabled": True, "filters": [], "row_actions": []},
             "actions": [{"id": "stock-in", "label": "入库", "action_type": "submit_form"}, {"id": "stock-out", "label": "出库", "action_type": "submit_form"}]}
        ]}}


def main() -> None:
    client = SequenceClient([maintenance_response(), warehouse_response()])
    planner = PrototypePlanner.__new__(PrototypePlanner)
    planner.llm_client = client

    maintenance = planner.generate("规划设备维修工单", plan("设备维修", ["报修和处理"], ["工单列表", "维修详情"]))
    assert maintenance is not None
    orders = next(page for page in maintenance.pages if page.id == "orders")
    detail = next(page for page in maintenance.pages if page.id == "order-detail")
    assert orders.layout.layout_type in {"single_column", "dashboard_grid"}
    assert [item.component_type for item in orders.components] == ["cards", "tabs", "table"]
    assert detail.layout.layout_type in {"two_column", "sidebar_detail"}
    assert {item.region for item in detail.components} >= {"left", "right"}
    assert detail.detail_sections and detail.timeline_items and detail.alerts
    maintenance_html = generate_interactive_prototype(maintenance)
    assert "layout-two_column" in maintenance_html
    assert "设备信息" in maintenance_html and "prototype-timeline" in maintenance_html
    assert "prototype-alert warning" in maintenance_html

    warehouse = planner.generate("规划仓库库存管理", plan("仓库管理", ["查看库存预警", "入库和出库"], ["库存总览", "库存列表", "库存预警"]))
    assert warehouse is not None
    warehouse_json = warehouse.model_dump_json()
    assert all(term not in warehouse_json for term in ("维修主管", "维修人员", "维修工单"))
    assert {page.title for page in warehouse.pages} == {"库存总览", "库存列表"}
    warehouse_html = generate_interactive_prototype(warehouse)
    assert "库存不足" in warehouse_html and "layout-dashboard_grid" in warehouse_html
    assert "Prototype V2.5" in client.prompts[0][0]

    legacy = PrototypeSpec.model_validate({
        "title": "Legacy", "description": "V1/V2", "default_page": "home",
        "pages": [{"id": "home", "title": "首页", "page_type": "dashboard"}],
    })
    assert legacy.pages[0].layout is None and legacy.pages[0].components == []
    assert "data-page=\"home\"" in generate_interactive_prototype(legacy)

    print("Maintenance:", [(page.title, page.layout.layout_type, [item.component_type for item in page.components]) for page in maintenance.pages])
    print("Warehouse:", [(page.title, page.layout.layout_type, [item.component_type for item in page.components]) for page in warehouse.pages])
    print("Prototype V1/V2 compatibility: passed")


if __name__ == "__main__":
    main()
