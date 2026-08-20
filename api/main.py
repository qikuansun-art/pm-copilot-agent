"""Minimal FastAPI application for PM Copilot Agent."""

from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.runtime import PMCopilotRuntime
from api.task_store import task_store
from knowledge.document_parser import document_parser
from knowledge.document_store import document_store
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
tasks: dict[str, AgentState] = {
    state.task.task_id: state for state in task_store.list()
}


def get_task_state(task_id: str) -> AgentState | None:
    """Return a task from memory, falling back to persistent storage."""
    state = tasks.get(task_id)
    if state is None:
        state = task_store.get(task_id)
        if state is not None:
            tasks[task_id] = state
    return state


def save_task_state(state: AgentState) -> AgentState:
    """Synchronize an updated task to memory and SQLite."""
    task_store.save(state)
    tasks[state.task.task_id] = state
    return state


class CreateTaskRequest(BaseModel):
    """Request body for creating and starting a PM Copilot task."""

    title: str
    request: str
    knowledge_group_ids: list[str] = Field(default_factory=list)


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


class RevisionRequest(BaseModel):
    """Request body containing a new condition for a completed plan."""

    feedback: str


class CreateKnowledgeGroupRequest(BaseModel):
    """Request body for creating a named knowledge group."""

    name: str


class MoveDocumentRequest(BaseModel):
    """Request body for moving a document into or out of a group."""

    group_id: str | None = None


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


@app.post("/knowledge/documents")
async def upload_knowledge_document(
    file: UploadFile = File(...),
    group_id: str | None = Form(None),
) -> dict[str, object]:
    """Parse and store an uploaded UTF-8 text or Markdown document."""
    if group_id is not None and document_store.get_group(group_id) is None:
        raise HTTPException(status_code=404, detail="Knowledge group not found")

    content = await file.read()
    try:
        chunks = document_parser.parse(file.filename or "", content)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Document contains no usable text",
        )

    document = document_store.add_document(
        filename=file.filename or "",
        chunks=chunks,
        group_id=group_id,
    )
    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "group_id": document.group_id,
    }


@app.post("/knowledge/groups")
def create_knowledge_group(payload: CreateKnowledgeGroupRequest) -> object:
    """Create a named knowledge group."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be empty")
    return document_store.create_group(name)


@app.get("/knowledge/groups")
def list_knowledge_groups() -> list[object]:
    """Return all knowledge groups with document counts."""
    return document_store.list_groups()


@app.delete("/knowledge/groups/{group_id}")
def delete_knowledge_group(group_id: str) -> dict[str, bool]:
    """Delete a group while preserving its documents as ungrouped."""
    if not document_store.delete_group(group_id):
        raise HTTPException(status_code=404, detail="Knowledge group not found")
    return {"deleted": True}


@app.get("/knowledge/documents")
def list_knowledge_documents() -> list[object]:
    """Return all documents currently held in the in-memory store."""
    return document_store.list_documents()


@app.get("/knowledge/documents/{document_id}/chunks")
def get_knowledge_document_chunks(document_id: str) -> dict[str, object]:
    """Return all chunks for an existing uploaded document."""
    if document_store.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "chunks": document_store.get_chunks(document_id),
    }


@app.delete("/knowledge/documents/{document_id}")
def delete_knowledge_document(document_id: str) -> dict[str, bool]:
    """Delete an uploaded document and all of its chunks."""
    if not document_store.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


@app.put("/knowledge/documents/{document_id}/group")
def move_knowledge_document(
    document_id: str,
    payload: MoveDocumentRequest,
) -> object:
    """Move an uploaded document into a group or remove its grouping."""
    if document_store.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if (
        payload.group_id is not None
        and document_store.get_group(payload.group_id) is None
    ):
        raise HTTPException(status_code=404, detail="Knowledge group not found")
    document_store.move_document(document_id, payload.group_id)
    return document_store.get_document(document_id)


@app.post("/tasks")
def create_task(payload: CreateTaskRequest) -> dict[str, object]:
    """Create a task and run its initial requirement-understanding stage."""
    if not payload.request.strip():
        raise HTTPException(status_code=422, detail="request must not be empty")

    for group_id in payload.knowledge_group_ids:
        if document_store.get_group(group_id) is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown knowledge group: {group_id}",
            )

    task_id = str(uuid4())
    state = AgentState(
        task=TaskContext(
            task_id=task_id,
            title=payload.title,
            original_request=payload.request,
            knowledge_group_ids=payload.knowledge_group_ids,
        )
    )
    state = PMCopilotRuntime().start_task(state)
    save_task_state(state)

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
        "knowledge_group_ids": state.task.knowledge_group_ids,
        "plan_version": state.task.plan_version,
    }


@app.get("/tasks")
def list_tasks() -> list[dict[str, object]]:
    """Return persisted task summaries ordered by recent activity."""
    return [
        {
            "task_id": state.task.task_id,
            "title": state.task.title,
            "original_request": state.task.original_request,
            "current_stage": state.task.current_stage.value,
            "created_at": state.task.created_at,
            "updated_at": state.task.updated_at,
            "plan_version": state.task.plan_version,
        }
        for state in task_store.list()
    ]


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    """Return the complete persisted state for one task."""
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return state.model_dump(mode="json")


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str) -> dict[str, object]:
    """Permanently delete one persisted task and its memory cache entry."""
    if not task_store.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    tasks.pop(task_id, None)
    return {"deleted": True, "task_id": task_id}


@app.post("/tasks/{task_id}/clarification")
def submit_clarification(
    task_id: str,
    payload: ClarificationRequest,
) -> dict[str, object]:
    """Record a user's clarification answer for an existing task."""
    state = get_task_state(task_id)
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

    save_task_state(state)
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "known_facts": state.task.known_facts,
        "missing_information": state.task.missing_information,
    }


@app.post("/tasks/{task_id}/plan")
def create_task_plan(task_id: str) -> dict[str, object]:
    """Create a product task plan for an existing task."""
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        state = PMCopilotRuntime().create_plan(state)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    save_task_state(state)
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "plan": state.plan.model_dump() if state.plan is not None else None,
    }


@app.post("/tasks/{task_id}/research/plan")
def create_task_research_plan(task_id: str) -> dict[str, object]:
    """Create research queries for an existing task without running searches."""
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        research_plan = PMCopilotRuntime().create_research_plan(state)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "research_plan": research_plan.model_dump(),
    }


@app.post("/tasks/{task_id}/research/internal")
def run_internal_research(
    task_id: str,
    payload: ResearchRequest,
) -> dict[str, object]:
    """Run internal knowledge research for an existing task."""
    state = get_task_state(task_id)
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

    save_task_state(state)
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
    state = get_task_state(task_id)
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

    save_task_state(state)
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "tool_calls": [item.model_dump() for item in state.tool_calls],
        "evidence": [item.model_dump() for item in state.evidence],
    }


@app.post("/tasks/{task_id}/analysis")
def run_product_analysis(task_id: str) -> dict[str, object]:
    """Run product analysis for an existing task."""
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        state = PMCopilotRuntime().run_product_analysis(state)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    save_task_state(state)
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "analysis": (
            state.analysis.model_dump() if state.analysis is not None else None
        ),
        "final_output": (
            state.final_output.model_dump()
            if state.final_output is not None
            else None
        ),
        "plan_version": state.task.plan_version,
    }


@app.post("/tasks/{task_id}/review")
def review_task(
    task_id: str,
    payload: ReviewRequest,
) -> dict[str, object]:
    """Apply human review and finalize an existing task."""
    state = get_task_state(task_id)
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

    save_task_state(state)
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "final_output": (
            state.final_output.model_dump()
            if state.final_output is not None
            else None
        ),
        "plan_version": state.task.plan_version,
        "review_feedback": [
            item.model_dump() for item in state.review_feedback
        ],
    }


@app.post("/tasks/{task_id}/revision")
def revise_completed_task(
    task_id: str,
    payload: RevisionRequest,
) -> dict[str, object]:
    """Create a new review-ready version of a completed task."""
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not payload.feedback.strip():
        raise HTTPException(status_code=422, detail="feedback must not be empty")

    try:
        state = PMCopilotRuntime().revise_completed_task(
            state,
            payload.feedback.strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    save_task_state(state)
    return {
        "task_id": task_id,
        "current_stage": state.task.current_stage.value,
        "final_output": state.final_output.model_dump() if state.final_output else None,
        "plan_version": state.task.plan_version,
        "review_feedback": [item.model_dump() for item in state.review_feedback],
    }
