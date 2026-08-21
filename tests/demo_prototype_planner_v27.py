"""Prototype V2.7 mock entity planning, validation, rendering, and repair coverage."""

import copy
import json

from agent.prototype_planner import PrototypePlanner
from models.prototype import PrototypeSpec
from prototype.html_prototype import generate_interactive_prototype
from tests.demo_prototype_planner_v26 import maintenance_response, plan, warehouse_response


class SequenceClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return json.dumps(self.responses[len(self.calls) - 1], ensure_ascii=False)


def maintenance_v27() -> dict:
    payload = copy.deepcopy(maintenance_response())
    prototype = payload["prototype"]
    prototype["entity_types"] = [
        {"id": "technician", "name": "维修人员", "fields": ["id", "name", "status"]},
        {"id": "device", "name": "设备", "fields": ["id", "name"]},
        {"id": "spare_part", "name": "备件", "fields": ["id", "name"]},
    ]
    prototype["entity_records"] = [
        {"id": "tech-001", "entity_type": "technician", "data": {"name": "张师傅", "status": "空闲"}},
        {"id": "tech-002", "entity_type": "technician", "data": {"name": "李师傅", "status": "忙碌"}},
        {"id": "tech-003", "entity_type": "technician", "data": {"name": "王师傅", "status": "空闲"}},
        {"id": "DEV-001", "entity_type": "device", "data": {"name": "X450-01"}},
        {"id": "DEV-002", "entity_type": "device", "data": {"name": "X500-5-01"}},
        {"id": "SP-001", "entity_type": "spare_part", "data": {"name": "锯片350"}},
        {"id": "SP-002", "entity_type": "spare_part", "data": {"name": "铣刀10mm"}},
    ]
    prototype["pages"][0]["fields"] = [{
        "id": "device_id", "label": "设备", "field_type": "select",
        "data_source": "device", "option_label_field": "name", "option_value_field": "id",
    }]
    part = prototype["pages"][1]["fields"][1]
    part.update(data_source="spare_part", option_label_field="name", option_value_field="id")
    prototype["panels"] = [{
        "id": "assign-drawer", "title": "主管派单", "panel_type": "drawer",
        "fields": [{
            "id": "technician_id", "label": "选择维修人员", "field_type": "select",
            "required": True, "data_source": "technician",
            "option_label_field": "name", "option_value_field": "id",
        }],
        "actions": [{"id": "confirm-assign", "label": "确认派单", "action_type": "update_status"}],
    }]
    return payload


def warehouse_v27() -> dict:
    payload = copy.deepcopy(warehouse_response())
    prototype = payload["prototype"]
    prototype["entity_types"] = [
        {"id": "warehouse", "name": "仓库", "fields": ["id", "name"]},
        {"id": "material", "name": "物料", "fields": ["id", "name", "stock"]},
    ]
    prototype["entity_records"] = [
        {"id": "WH-001", "entity_type": "warehouse", "data": {"name": "一号仓"}},
        {"id": "WH-002", "entity_type": "warehouse", "data": {"name": "二号仓"}},
        {"id": "MAT-001", "entity_type": "material", "data": {"name": "钢板", "stock": 120}},
        {"id": "MAT-002", "entity_type": "material", "data": {"name": "铝型材", "stock": 80}},
    ]
    prototype["pages"][1]["fields"].insert(0, {
        "id": "warehouse_id", "label": "仓库", "field_type": "select",
        "data_source": "warehouse", "option_label_field": "name", "option_value_field": "id",
    })
    prototype["pages"][1]["fields"].insert(1, {
        "id": "material_id", "label": "物料", "field_type": "select",
        "data_source": "material", "option_label_field": "name", "option_value_field": "id",
    })
    return payload


def main() -> None:
    maintenance_payload = maintenance_v27()
    warehouse_payload = warehouse_v27()
    client = SequenceClient([maintenance_payload, warehouse_payload])
    planner = PrototypePlanner.__new__(PrototypePlanner)
    planner.llm_client = client

    maintenance = planner.generate("维修工单派单原型", plan("维修工单", ["主管选择维修人员派单", "关联设备和备件"]))
    assert maintenance is not None
    fields = {field.id: field for panel in maintenance.panels for field in panel.fields}
    assert fields["technician_id"].data_source == "technician"
    assert len([x for x in maintenance.entity_records if x.entity_type == "technician"]) >= 3
    assert next(x for x in maintenance.pages[0].fields if x.id == "device_id").data_source == "device"
    assert next(x for x in maintenance.pages[1].fields if x.id == "part_id").data_source == "spare_part"
    html = generate_interactive_prototype(maintenance)
    for value in ("张师傅", "李师傅", "王师傅", "X450-01", "X500-5-01", "锯片350", "铣刀10mm"):
        assert value in html
    assert '<option value="tech-001">张师傅</option>' in html

    warehouse = planner.generate("仓库管理原型", plan("仓库管理", ["选择仓库和物料办理出库"]))
    assert warehouse is not None
    assert {x.id for x in warehouse.entity_types} == {"warehouse", "material"}
    assert all(x.entity_type != "technician" for x in warehouse.entity_records)
    assert "维修人员" not in generate_interactive_prototype(warehouse)

    legacy = copy.deepcopy(maintenance_response()["prototype"])
    legacy_spec = PrototypeSpec.model_validate(legacy)
    assert legacy_spec.entity_types == [] and legacy_spec.entity_records == []
    assert all(field.data_source is None for page in legacy_spec.pages for field in page.fields)

    broken = maintenance_v27()
    broken["prototype"]["panels"][0]["fields"][0]["data_source"] = "missing_entity"
    repair_client = SequenceClient([broken, maintenance_v27()])
    repair_planner = PrototypePlanner.__new__(PrototypePlanner)
    repair_planner.llm_client = repair_client
    repaired = repair_planner.generate("维修工单派单原型", plan("维修工单", ["主管选择维修人员派单"]))
    assert repaired is not None and len(repair_client.calls) == 2
    assert "data_source must reference an entity type" in repair_client.calls[1][1]

    prompt = client.calls[0][0]
    assert "Prototype V2.7" in prompt and "entity_types" in prompt and "3～5" in prompt
    print("Case A: maintenance technician/device/spare-part entities passed")
    print("Case B: renderer generated entity-backed select options")
    print("Case C: warehouse domain isolation passed")
    print("Case D: V1-V2.6 defaults remain compatible")
    print("Case E: invalid data_source repaired exactly once")


if __name__ == "__main__":
    main()
