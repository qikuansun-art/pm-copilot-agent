"""Prototype HTML V2.6 condition runtime and JavaScript syntax coverage."""

import copy
import re
import subprocess
import tempfile
from pathlib import Path

from models.prototype import PrototypeSpec
from prototype.html_prototype import generate_interactive_prototype
from tests.demo_prototype_planner_v25 import warehouse_response as v25_warehouse_response
from tests.demo_prototype_planner_v26 import maintenance_response, warehouse_response


def node_check(script: str) -> None:
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
            handle.write(script)
            path = Path(handle.name)
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def main() -> None:
    maintenance_payload = maintenance_response()["prototype"]
    maintenance_payload["pages"][1]["visible_when"] = {
        "logic": "or",
        "conditions": [
            {"field": "status", "operator": "equals", "value": "维修中"},
            {"field": "role", "operator": "equals", "value": "technician"},
        ],
    }
    maintenance_payload["panels"] = [{
        "id": "repair-note", "title": "维修备注", "panel_type": "drawer",
        "visible_when": {"logic": "and", "conditions": [{"field": "status", "operator": "equals", "value": "维修中"}]},
        "fields": [{"id": "panel_note", "label": "备注", "field_type": "textarea"}],
        "actions": [],
    }]
    maintenance_payload["pages"][0]["actions"] = [{
        "id": "open-note", "label": "维修备注", "action_type": "open_drawer", "target": "repair-note",
    }]
    maintenance = PrototypeSpec.model_validate(maintenance_payload)
    html = generate_interactive_prototype(maintenance)

    # A: role/status evaluator and unified refresh runtime are emitted.
    assert "function getConditionContext" in html
    assert "function evaluateCondition(condition,context)" in html
    assert "function evaluateConditionGroup(group,context" in html
    assert "function refreshConditionalUI()" in html
    assert "context.role=currentRole" in html
    assert "record?.__status??record?.status" in html

    # B-C: fields carry stable IDs and runtime visibility/required rules.
    assert 'data-field-id="replace_part"' in html
    assert 'data-field-id="part_id"' in html
    assert "field.visible_when" in html
    assert "field.required||evaluateConditionGroup(field.required_when,context)" in html
    assert "wrapper.hidden=!visible" in html

    # D-E: enabled_when remains visible but disabled and value_field reads context.
    warehouse = PrototypeSpec.model_validate(warehouse_response()["prototype"])
    warehouse_html = generate_interactive_prototype(warehouse)
    assert "action.enabled_when" in warehouse_html
    assert "button.disabled=visible&&!evaluateConditionGroup" in warehouse_html
    assert "context[condition.value_field]" in warehouse_html
    assert "Number.isFinite" in warehouse_html

    # F: Page, Panel, and Component conditions are serialized and consumed.
    assert '"visible_when":{"logic":"or"' in html
    assert "panel.visible_when" in html
    assert 'data-component-id="low-alert"' in warehouse_html
    assert "component.visible_when" in warehouse_html
    assert "page.visible_when" in html

    # G: a condition-free V2.5 spec still renders normally.
    legacy = PrototypeSpec.model_validate(copy.deepcopy(v25_warehouse_response()["prototype"]))
    legacy_html = generate_interactive_prototype(legacy)
    assert 'data-page="inventory-overview"' in legacy_html
    assert "function refreshConditionalUI()" in legacy_html

    # H: no executable expression mechanism is introduced.
    for output in (html, warehouse_html, legacy_html):
        assert "eval(" not in output
        assert "new Function" not in output
        script = re.search(r"<script>([\s\S]*?)</script>", output)
        assert script is not None
        node_check(script.group(1))

    print("Cases A-F: Condition runtime emitted for actions, fields, pages, panels, and components")
    print("Case G: V2.5 condition-free HTML compatibility passed")
    print("Case H: no eval/new Function; node --check passed for all generated scripts")


if __name__ == "__main__":
    main()
