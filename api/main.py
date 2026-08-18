"""Minimal FastAPI application for PM Copilot Agent."""

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.runtime import PMCopilotRuntime
from models.state import AgentState, TaskContext


app = FastAPI(title="PM Copilot Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
tasks: dict[str, AgentState] = {}


class CreateTaskRequest(BaseModel):
    """Request body for creating and starting a PM Copilot task."""

    title: str
    request: str


class ClarificationRequest(BaseModel):
    """Request body containing a user's clarification answer."""

    answer: str


class ResearchRequest(BaseModel):
    """Request body containing a research query."""

    query: str


class ReviewRequest(BaseModel):
    """Request body containing a human review decision and feedback."""

    approved: bool
    feedback: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    """Return basic service information."""
    return {
        "name": "PM Copilot Agent",
        "status": "ok",
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "healthy"}


@app.post("/tasks")
def create_task(payload: CreateTaskRequest) -> dict[str, object]:
    """Create a task and run its initial requirement-understanding stage."""
    if not payload.request.strip():
        raise HTTPException(status_code=422, detail="request must not be empty")

    task_id = str(uuid4())
    state = AgentState(
        task=TaskContext(
            task_id=task_id,
            title=payload.title,
            original_request=payload.request,
        )
    )
    state = PMCopilotRuntime().start_task(state)
    tasks[task_id] = state

    questions: list[dict[str, str]] = []
    for message in state.messages:
        if message.role != "assistant":
            continue
        question, separator, reason = message.content.partition("\n原因：")
        questions.append(
            {
                "question": question,
                "reason": reason if separator else "",
            }
        )

    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "known_facts": state.task.known_facts,
        "missing_information": state.task.missing_information,
        "questions": questions,
    }


@app.post("/tasks/{task_id}/clarification")
def submit_clarification(
    task_id: str,
    payload: ClarificationRequest,
) -> dict[str, object]:
    """Record a user's clarification answer for an existing task."""
    state = tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not payload.answer.strip():
        raise HTTPException(status_code=422, detail="answer must not be empty")

    try:
        state = PMCopilotRuntime().handle_clarification_response(
            state,
            payload.answer,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    tasks[task_id] = state
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "known_facts": state.task.known_facts,
        "missing_information": state.task.missing_information,
    }


@app.post("/tasks/{task_id}/plan")
def create_task_plan(task_id: str) -> dict[str, object]:
    """Create a product task plan for an existing task."""
    state = tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        state = PMCopilotRuntime().create_plan(state)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    tasks[task_id] = state
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "plan": state.plan.model_dump() if state.plan is not None else None,
    }


@app.post("/tasks/{task_id}/research/internal")
def run_internal_research(
    task_id: str,
    payload: ResearchRequest,
) -> dict[str, object]:
    """Run internal knowledge research for an existing task."""
    state = tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    try:
        state = PMCopilotRuntime().run_internal_research(
            state,
            payload.query,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    tasks[task_id] = state
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "tool_calls": [item.model_dump() for item in state.tool_calls],
        "evidence": [item.model_dump() for item in state.evidence],
    }


@app.post("/tasks/{task_id}/research/external")
def run_external_research(
    task_id: str,
    payload: ResearchRequest,
) -> dict[str, object]:
    """Run external industry research for an existing task."""
    state = tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    try:
        state = PMCopilotRuntime().run_external_research(
            state,
            payload.query,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    tasks[task_id] = state
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "tool_calls": [item.model_dump() for item in state.tool_calls],
        "evidence": [item.model_dump() for item in state.evidence],
    }


@app.post("/tasks/{task_id}/analysis")
def run_product_analysis(task_id: str) -> dict[str, object]:
    """Run product analysis for an existing task."""
    state = tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        state = PMCopilotRuntime().run_product_analysis(state)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    tasks[task_id] = state
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "analysis": (
            state.analysis.model_dump() if state.analysis is not None else None
        ),
    }


@app.post("/tasks/{task_id}/review")
def review_task(
    task_id: str,
    payload: ReviewRequest,
) -> dict[str, object]:
    """Apply human review and finalize an existing task."""
    state = tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not payload.approved and not payload.feedback:
        raise HTTPException(
            status_code=422,
            detail="feedback is required when review is not approved",
        )

    try:
        state = PMCopilotRuntime().handle_review(
            state,
            approved=payload.approved,
            feedback=payload.feedback,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    tasks[task_id] = state
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "final_output": (
            state.final_output.model_dump()
            if state.final_output is not None
            else None
        ),
    }
