"""Regression coverage for legacy plan-status migration on SQLite reads."""

import sqlite3
from pathlib import Path

from api.task_store import TaskStore
from models.state import AgentPlan, AgentStage, AgentState, PlanStep, TaskContext


def legacy_state(task_id: str, stage: AgentStage, statuses: list[str]) -> AgentState:
    """Build a state shaped like records written before status normalization."""
    return AgentState(
        task=TaskContext(
            task_id=task_id,
            title=f"Legacy {stage.value}",
            original_request="测试旧任务迁移",
            current_stage=stage,
        ),
        plan=AgentPlan(
            goal="验证旧状态迁移",
            steps=[
                PlanStep(id=index, title=f"动态步骤 {index}", status=status)
                for index, status in enumerate(statuses, start=1)
            ],
        ),
    )


def insert_legacy_state(db_path: Path, state: AgentState) -> None:
    """Bypass TaskStore.save to simulate JSON produced by an old release."""
    connection = sqlite3.connect(db_path)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO tasks (task_id, state_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    state.task.task_id,
                    state.model_dump_json(),
                    state.task.created_at,
                    state.task.updated_at,
                ),
            )
    finally:
        connection.close()


def read_raw_state(db_path: Path, task_id: str) -> AgentState:
    """Read persisted JSON directly, without invoking migration again."""
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "SELECT state_json FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return AgentState.model_validate_json(row[0])


def main() -> None:
    """Verify get and list normalize legacy states and write them back."""
    db_path = Path("data/test_legacy_migration.db")
    if db_path.exists():
        db_path.unlink()

    try:
        TaskStore(db_path)
        completed = legacy_state(
            "legacy-completed",
            AgentStage.COMPLETED,
            ["completed", "completed", "running", "pending", "running"],
        )
        waiting_review = legacy_state(
            "legacy-waiting-review",
            AgentStage.WAITING_REVIEW,
            ["completed", "completed", "running", "pending", "pending"],
        )
        insert_legacy_state(db_path, completed)
        insert_legacy_state(db_path, waiting_review)

        restored_completed = TaskStore(db_path).get(completed.task.task_id)
        assert restored_completed is not None
        assert restored_completed.task.current_stage == AgentStage.COMPLETED
        assert [step.status for step in restored_completed.plan.steps] == [
            "completed", "completed", "completed", "completed", "completed"
        ]
        persisted_completed = read_raw_state(db_path, completed.task.task_id)
        assert all(step.status == "completed" for step in persisted_completed.plan.steps)

        restored_by_list = {
            state.task.task_id: state for state in TaskStore(db_path).list()
        }
        assert [
            step.status
            for step in restored_by_list[waiting_review.task.task_id].plan.steps
        ] == ["completed", "completed", "completed", "completed", "running"]
        persisted_waiting_review = read_raw_state(db_path, waiting_review.task.task_id)
        assert [step.status for step in persisted_waiting_review.plan.steps] == [
            "completed", "completed", "completed", "completed", "running"
        ]

        print("COMPLETED migrated:", [
            step.status for step in persisted_completed.plan.steps
        ])
        print("WAITING_REVIEW migrated:", [
            step.status for step in persisted_waiting_review.plan.steps
        ])
    finally:
        if db_path.exists():
            db_path.unlink()


if __name__ == "__main__":
    main()
