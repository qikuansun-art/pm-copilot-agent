"""Structured interaction-prototype planning models."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


class PrototypeField(BaseModel):
    """One input or displayed data field in a prototype page."""

    id: str
    label: str
    field_type: Literal["text", "textarea", "select", "number", "date"]
    required: bool = False
    options: list[str] = Field(default_factory=list)


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


class PrototypeStatusTransition(BaseModel):
    """A business-status change triggered by a prototype action."""

    from_status: str
    action_id: str
    to_status: str


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
            ):
                ids = [item.id for item in collection]
                if len(ids) != len(set(ids)):
                    raise ValueError(f"Prototype {label} IDs must be unique per page")

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
