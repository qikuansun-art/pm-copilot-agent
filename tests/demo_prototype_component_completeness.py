"""Regression coverage for deterministic page-actions component completion."""

import copy

from agent.prototype_planner import normalize_prototype_payload
from models.prototype import PrototypeSpec
from prototype.html_prototype import generate_interactive_prototype


def base_payload() -> dict:
    return {"has_prototype": True, "prototype": {
        "title": "维修工单", "description": "组件完整性", "default_page": "page-list",
        "roles": [{"id": "operator", "name": "设备操作员"}], "default_role": "operator",
        "statuses": [], "status_transitions": [],
        "panels": [{
            "id": "panel-create", "title": "创建维修工单", "panel_type": "drawer",
            "fields": [{"id": "fault", "label": "故障描述", "field_type": "textarea"}],
            "actions": [{"id": "submit-create", "label": "提交报修", "action_type": "submit_form"}],
        }],
        "pages": [{
            "id": "page-list", "title": "维修工单工作台", "page_type": "list",
            "actions": [{
                "id": "create-order", "label": "创建维修工单", "action_type": "open_drawer",
                "target": "panel-create", "visible_to_roles": ["operator"],
            }],
            "components": [
                {"id": "cards", "component_type": "cards", "region": "top", "order": 1},
                {"id": "table", "component_type": "table", "region": "main", "order": 2},
            ],
            "table": {"columns": [], "filters": [], "row_actions": []},
        }],
    }}


def normalized(payload: dict) -> dict:
    return normalize_prototype_payload(payload)["prototype"]


def main() -> None:
    # A: a missing page-actions renderer is completed deterministically.
    repaired = normalized(base_payload())
    action_components = [x for x in repaired["pages"][0]["components"] if x["component_type"] == "actions"]
    assert len(action_components) == 1
    assert action_components[0] == {
        "id": "page-list-actions", "component_type": "actions", "title": "",
        "description": "", "order": 3, "region": "main", "visible_to_roles": [],
    }

    # B: an existing actions component is preserved without duplication.
    existing = base_payload()
    existing_component = {
        "id": "toolbar", "component_type": "actions", "region": "top", "order": 2,
    }
    existing["prototype"]["pages"][0]["components"].append(existing_component)
    twice = normalized(existing)
    twice = normalized({"has_prototype": True, "prototype": twice})
    assert [x for x in twice["pages"][0]["components"] if x["component_type"] == "actions"] == [existing_component]

    # C: table row actions alone do not create a page actions component.
    row_only = base_payload()
    page = row_only["prototype"]["pages"][0]
    page["actions"] = []
    page["table"]["row_actions"] = [{"id": "view", "label": "查看", "action_type": "update_status"}]
    assert all(x["component_type"] != "actions" for x in normalized(row_only)["pages"][0]["components"])

    # D: panel actions alone do not create a page actions component.
    panel_only = base_payload()
    panel_only["prototype"]["pages"][0]["actions"] = []
    assert all(x["component_type"] != "actions" for x in normalized(panel_only)["pages"][0]["components"])

    # E: the real maintenance shape emits the create-order DOM button.
    maintenance = PrototypeSpec.model_validate(repaired)
    maintenance_html = generate_interactive_prototype(maintenance)
    assert 'data-action="create-order">创建维修工单</button>' in maintenance_html

    # F: multiple warehouse page actions share one generated actions component.
    warehouse = base_payload()
    prototype = warehouse["prototype"]
    prototype["title"] = "仓库管理"
    prototype["panels"] = []
    prototype["pages"][0]["actions"] = [
        {"id": "inbound", "label": "入库", "action_type": "update_status"},
        {"id": "outbound", "label": "出库", "action_type": "update_status"},
    ]
    warehouse_spec = PrototypeSpec.model_validate(normalized(warehouse))
    warehouse_html = generate_interactive_prototype(warehouse_spec)
    assert warehouse_html.count('component_type":"actions"') == 1
    assert 'data-action="inbound">入库</button>' in warehouse_html
    assert 'data-action="outbound">出库</button>' in warehouse_html

    print("Case A: missing page actions component completed")
    print("Case B: existing actions component not duplicated")
    print("Cases C-D: row and panel actions ignored")
    print("Case E: maintenance create-order button rendered")
    print("Case F: warehouse inbound/outbound buttons rendered")


if __name__ == "__main__":
    main()
