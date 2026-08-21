"""Structured interaction-prototype planning models."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class PrototypeCondition(BaseModel):
    """One structured comparison used to control prototype behavior."""

    field: str
    operator: Literal[
        "equals",
        "not_equals",
        "in",
        "not_in",
        "exists",
        "not_exists",
        "greater_than",
        "less_than",
        "greater_than_or_equal",
        "less_than_or_equal",
    ]
    value: Any | None = None
    value_field: str | None = None

    @model_validator(mode="after")
    def validate_operands(self) -> "PrototypeCondition":
        """Reject ambiguous operands and obvious operator/type mismatches."""
        has_value = "value" in self.model_fields_set
        has_value_field = self.value_field is not None
        if has_value and has_value_field:
            raise ValueError("Prototype conditions cannot use value and value_field together")
        if self.operator in {"exists", "not_exists"}:
            if has_value_field or (has_value and self.value is not None):
                raise ValueError("Prototype existence conditions do not accept an operand")
            return self
        if not has_value and not has_value_field:
            raise ValueError("Prototype conditions require value or value_field")
        if self.operator in {"in", "not_in"}:
            if has_value_field or not isinstance(self.value, list):
                raise ValueError("Prototype in conditions require a list value")
        if (
            self.operator
            in {"greater_than", "less_than", "greater_than_or_equal", "less_than_or_equal"}
            and not has_value_field
            and (isinstance(self.value, bool) or not isinstance(self.value, (int, float)))
        ):
            raise ValueError("Prototype comparison conditions require a numeric value or value_field")
        return self


class PrototypeConditionGroup(BaseModel):
    """Combines one flat list of conditions with AND or OR logic."""

    logic: Literal["and", "or"] = "and"
    conditions: list[PrototypeCondition] = Field(default_factory=list)


class PrototypeAction(BaseModel):
    """One user interaction available from a prototype page."""

    id: str
    label: str
    action_type: Literal[
        "navigate",
        "open_modal",
        "submit_form",
        "update_status",
        "close_modal",
        "filter",
        "search",
        "open_drawer",
        "switch_tab",
        "switch_role",
    ]
    target: str | None = None
    visible_to_roles: list[str] = Field(default_factory=list)
    visible_when: PrototypeConditionGroup | None = None
    enabled_when: PrototypeConditionGroup | None = None


class PrototypeField(BaseModel):
    """One input or displayed data field in a prototype page."""

    id: str
    label: str
    field_type: Literal["text", "textarea", "select", "number", "date"]
    required: bool = False
    options: list[str] = Field(default_factory=list)
    data_source: str | None = None
    option_label_field: str | None = None
    option_value_field: str | None = None
    visible_when: PrototypeConditionGroup | None = None
    required_when: PrototypeConditionGroup | None = None
    enabled_when: PrototypeConditionGroup | None = None


class PrototypeEntityType(BaseModel):
    """A lightweight reference-data shape used only by the prototype."""

    id: str
    name: str
    fields: list[str] = Field(default_factory=list)


class PrototypeEntityRecord(BaseModel):
    """One stable mock record embedded in a PrototypeSpec."""

    id: str
    entity_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class PrototypeRole(BaseModel):
    """A business persona whose prototype view may differ."""

    id: str
    name: str
    description: str = ""


class PrototypeFilter(BaseModel):
    """One filter exposed by a list table."""

    id: str
    label: str
    filter_type: Literal["select", "search", "status"]
    options: list[str] = Field(default_factory=list)


class PrototypeTableColumn(BaseModel):
    """One structured column in a list page table."""

    id: str
    label: str
    field: str
    column_type: Literal["text", "status", "date", "number"]


class PrototypeTable(BaseModel):
    """Structured table behavior for a list page."""

    columns: list[PrototypeTableColumn] = Field(default_factory=list)
    search_enabled: bool = False
    filters: list[PrototypeFilter] = Field(default_factory=list)
    row_actions: list[PrototypeAction] = Field(default_factory=list)


class PrototypeTab(BaseModel):
    """One business-state or content tab within a page."""

    id: str
    label: str


class PrototypeCard(BaseModel):
    """One dashboard metric or summary card."""

    id: str
    label: str
    value: str | int | float
    description: str = ""


class PrototypePanel(BaseModel):
    """A modal or drawer used for focused interactions."""

    id: str
    title: str
    panel_type: Literal["modal", "drawer"]
    fields: list[PrototypeField] = Field(default_factory=list)
    actions: list[PrototypeAction] = Field(default_factory=list)
    visible_when: PrototypeConditionGroup | None = None


class PrototypeStatusTransition(BaseModel):
    """A business-status change triggered by a prototype action."""

    from_status: str
    action_id: str
    to_status: str


class PrototypeLayout(BaseModel):
    """Places the major blocks of one page into a lightweight layout."""

    layout_type: Literal[
        "single_column",
        "two_column",
        "sidebar_detail",
        "dashboard_grid",
    ]
    left_width: int | None = None
    right_width: int | None = None


class PrototypeComponent(BaseModel):
    """References and arranges an existing page-level content block."""

    id: str
    component_type: Literal[
        "cards", "table", "form", "detail", "tabs", "alert", "timeline", "text", "actions"
    ]
    title: str = ""
    description: str = ""
    order: int = 0
    region: Literal["main", "left", "right", "top", "bottom"] = "main"
    visible_to_roles: list[str] = Field(default_factory=list)
    visible_when: PrototypeConditionGroup | None = None


class PrototypeDetailSection(BaseModel):
    """Groups related detail fields without duplicating their business data."""

    id: str
    title: str
    fields: list[str] = Field(default_factory=list)
    order: int = 0


class PrototypeTimelineItem(BaseModel):
    """One display-only event in a page timeline."""

    id: str
    title: str
    description: str
    status: str = ""


class PrototypeAlert(BaseModel):
    """One lightweight page-level business notice."""

    id: str
    message: str
    alert_type: Literal["info", "success", "warning", "error"]


class PrototypePage(BaseModel):
    """One screen represented by the planned interactive prototype."""

    id: str
    title: str
    page_type: Literal["dashboard", "list", "detail", "form"]
    description: str = ""
    fields: list[PrototypeField] = Field(default_factory=list)
    actions: list[PrototypeAction] = Field(default_factory=list)
    visible_to_roles: list[str] = Field(default_factory=list)
    table: PrototypeTable | None = None
    tabs: list[PrototypeTab] = Field(default_factory=list)
    cards: list[PrototypeCard] = Field(default_factory=list)
    layout: PrototypeLayout | None = None
    components: list[PrototypeComponent] = Field(default_factory=list)
    detail_sections: list[PrototypeDetailSection] = Field(default_factory=list)
    timeline_items: list[PrototypeTimelineItem] = Field(default_factory=list)
    alerts: list[PrototypeAlert] = Field(default_factory=list)
    visible_when: PrototypeConditionGroup | None = None


class PrototypeSpec(BaseModel):
    """A validated set of MVP pages and their available interactions."""

    title: str
    description: str
    pages: list[PrototypePage] = Field(default_factory=list)
    default_page: str
    roles: list[PrototypeRole] = Field(default_factory=list)
    default_role: str | None = None
    panels: list[PrototypePanel] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    status_transitions: list[PrototypeStatusTransition] = Field(default_factory=list)
    entity_types: list[PrototypeEntityType] = Field(default_factory=list)
    entity_records: list[PrototypeEntityRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_navigation(self) -> "PrototypeSpec":
        """Validate identities and all cross-references in the prototype."""
        page_ids = [page.id for page in self.pages]
        if len(page_ids) != len(set(page_ids)):
            raise ValueError("Prototype page IDs must be unique")
        known_page_ids = set(page_ids)
        if self.default_page not in known_page_ids:
            raise ValueError("Prototype default_page must reference a page")

        role_ids = [role.id for role in self.roles]
        if len(role_ids) != len(set(role_ids)):
            raise ValueError("Prototype role IDs must be unique")
        known_role_ids = set(role_ids)
        if self.default_role is not None and self.default_role not in known_role_ids:
            raise ValueError("Prototype default_role must reference a role")

        panel_ids = [panel.id for panel in self.panels]
        if len(panel_ids) != len(set(panel_ids)):
            raise ValueError("Prototype panel IDs must be unique")
        known_panels = {panel.id: panel for panel in self.panels}

        entity_type_ids = [entity.id for entity in self.entity_types]
        if len(entity_type_ids) != len(set(entity_type_ids)):
            raise ValueError("Prototype entity type IDs must be unique")
        known_entity_types = {entity.id: entity for entity in self.entity_types}
        entity_record_ids = [record.id for record in self.entity_records]
        if len(entity_record_ids) != len(set(entity_record_ids)):
            raise ValueError("Prototype entity record IDs must be unique")
        for record in self.entity_records:
            if record.entity_type not in known_entity_types:
                raise ValueError("Prototype entity records must reference an entity type")

        all_fields = [
            field for page in self.pages for field in page.fields
        ] + [
            field for panel in self.panels for field in panel.fields
        ]
        for field in all_fields:
            if field.data_source is None:
                continue
            entity_type = known_entity_types.get(field.data_source)
            if entity_type is None:
                raise ValueError("Prototype field data_source must reference an entity type")
            available_fields = {"id", *entity_type.fields}
            if field.option_label_field and field.option_label_field not in available_fields:
                raise ValueError("Prototype option_label_field must reference an entity field")
            if field.option_value_field and field.option_value_field not in available_fields:
                raise ValueError("Prototype option_value_field must reference an entity field")

        page_actions = [action for page in self.pages for action in page.actions]
        row_actions = [
            action
            for page in self.pages
            if page.table is not None
            for action in page.table.row_actions
        ]
        panel_actions = [action for panel in self.panels for action in panel.actions]
        all_actions = page_actions + row_actions + panel_actions
        action_ids = [action.id for action in all_actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("Prototype action IDs must be unique")

        for page in self.pages:
            if not set(page.visible_to_roles) <= known_role_ids:
                raise ValueError("Prototype page roles must reference a role")
            for collection, label in (
                (page.tabs, "tab"),
                (page.cards, "card"),
                (page.table.columns if page.table else [], "table column"),
                (page.table.filters if page.table else [], "filter"),
                (page.components, "component"),
                (page.detail_sections, "detail section"),
                (page.timeline_items, "timeline item"),
                (page.alerts, "alert"),
            ):
                ids = [item.id for item in collection]
                if len(ids) != len(set(ids)):
                    raise ValueError(f"Prototype {label} IDs must be unique per page")
            if len(page.components) > 15:
                raise ValueError("Prototype pages support at most 15 components")
            for component in page.components:
                if not set(component.visible_to_roles) <= known_role_ids:
                    raise ValueError("Prototype component roles must reference a role")

        known_fields = {
            field.id for page in self.pages for field in page.fields
        } | {
            field.id for panel in self.panels for field in panel.fields
        } | {
            column.field
            for page in self.pages
            if page.table is not None
            for column in page.table.columns
        }
        for page in self.pages:
            for section in page.detail_sections:
                if not set(section.fields) <= known_fields:
                    raise ValueError("Prototype detail sections must reference a field")

        condition_groups: list[PrototypeConditionGroup] = []
        for page in self.pages:
            condition_groups.extend(group for group in [page.visible_when] if group)
            for component in page.components:
                condition_groups.extend(group for group in [component.visible_when] if group)
            for field in page.fields:
                condition_groups.extend(
                    group
                    for group in [field.visible_when, field.required_when, field.enabled_when]
                    if group
                )
            for action in page.actions:
                condition_groups.extend(
                    group for group in [action.visible_when, action.enabled_when] if group
                )
            if page.table is not None:
                for action in page.table.row_actions:
                    condition_groups.extend(
                        group for group in [action.visible_when, action.enabled_when] if group
                    )
        for panel in self.panels:
            condition_groups.extend(group for group in [panel.visible_when] if group)
            for field in panel.fields:
                condition_groups.extend(
                    group
                    for group in [field.visible_when, field.required_when, field.enabled_when]
                    if group
                )
            for action in panel.actions:
                condition_groups.extend(
                    group for group in [action.visible_when, action.enabled_when] if group
                )

        for group in condition_groups:
            for condition in group.conditions:
                if condition.field not in {"role", "status"} | known_fields:
                    raise ValueError("Prototype condition fields must reference a field")
                if condition.value_field is not None and condition.value_field not in known_fields:
                    raise ValueError("Prototype condition value_field must reference a field")

        for action in all_actions:
            if not set(action.visible_to_roles) <= known_role_ids:
                raise ValueError("Prototype action roles must reference a role")
            if action.action_type == "navigate" and action.target not in known_page_ids:
                raise ValueError("Prototype navigate targets must reference a page")
            if action.action_type in {"open_modal", "open_drawer"} and self.panels:
                panel = known_panels.get(action.target or "")
                if panel is None:
                    raise ValueError("Prototype panel actions must reference a panel")
                expected_type = "modal" if action.action_type == "open_modal" else "drawer"
                if panel.panel_type != expected_type:
                    raise ValueError("Prototype panel action type must match its panel")

        if len(self.statuses) != len(set(self.statuses)):
            raise ValueError("Prototype statuses must be unique")
        known_statuses = set(self.statuses)
        known_action_ids = set(action_ids)
        for transition in self.status_transitions:
            if transition.from_status not in known_statuses or transition.to_status not in known_statuses:
                raise ValueError("Prototype transitions must reference a status")
            if transition.action_id not in known_action_ids:
                raise ValueError("Prototype transitions must reference an action")
        return self
