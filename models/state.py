"""Core state models for the PM Copilot agent workflow."""

from enum import Enum

from pydantic import BaseModel, Field

from models.final_output import FinalProductPlan


class AgentStage(str, Enum):
    """Represents the current lifecycle stage of a PM Copilot task."""

    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    WAITING_CLARIFICATION = "WAITING_CLARIFICATION"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    ANALYZING = "ANALYZING"
    WAITING_REVIEW = "WAITING_REVIEW"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Message(BaseModel):
    """Stores one conversational message exchanged during a task."""

    role: str
    content: str


class TaskContext(BaseModel):
    """Holds the request context and current progress of a PM Copilot task."""

    task_id: str
    title: str
    original_request: str
    current_stage: AgentStage = AgentStage.CREATED
    known_facts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    """Describes one actionable step in the task plan."""

    id: int
    title: str
    status: str = "pending"


class AgentPlan(BaseModel):
    """Defines the task goal and the ordered steps for achieving it."""

    goal: str
    steps: list[PlanStep] = Field(default_factory=list)


class ToolCall(BaseModel):
    """Records a tool invocation and its execution result."""

    tool_name: str
    input: dict = Field(default_factory=dict)
    result: str | None = None
    status: str = "pending"


class Evidence(BaseModel):
    """Captures sourced information used to support product analysis."""

    content: str
    source_type: str
    source: str
    confidence: str = "medium"


class Decision(BaseModel):
    """Records a product decision and the reasoning behind it."""

    decision: str
    reason: str | None = None
    decided_by: str = "user"


class ProductAnalysis(BaseModel):
    """Organizes the structured product analysis produced by PM Copilot."""

    problems: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    solution: list[str] = Field(default_factory=list)
    mvp_scope: list[str] = Field(default_factory=list)
    future_scope: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Aggregates all state generated throughout a PM Copilot task."""

    task: TaskContext
    messages: list[Message] = Field(default_factory=list)
    plan: AgentPlan | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    analysis: ProductAnalysis | None = None
    final_output: FinalProductPlan | None = None
