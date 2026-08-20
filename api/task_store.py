"""SQLite persistence for complete PM Copilot task states."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from models.state import AgentState, normalize_agent_state


class TaskStore:
    """Persists each AgentState as JSON in a lightweight SQLite table."""

    def __init__(self, db_path: str | Path = "data/tasks.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        state_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, state: AgentState) -> AgentState:
        """Insert or update one complete task state."""
        now = datetime.now(timezone.utc).isoformat()
        state.task.updated_at = now
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO tasks (task_id, state_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        state_json = excluded.state_json,
                        updated_at = excluded.updated_at
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
        return state

    def get(self, task_id: str) -> AgentState | None:
        """Return one persisted task, or None when it does not exist."""
        connection = self._connect()
        try:
            with connection:
                row = connection.execute(
                    "SELECT state_json FROM tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                state = self._restore_state(connection, row) if row else None
        finally:
            connection.close()
        return state

    def list(self) -> list[AgentState]:
        """Return persisted tasks with the most recently updated first."""
        connection = self._connect()
        try:
            with connection:
                rows = connection.execute(
                    "SELECT state_json FROM tasks ORDER BY updated_at DESC"
                ).fetchall()
                states = [self._restore_state(connection, row) for row in rows]
        finally:
            connection.close()
        return states

    def delete_task(self, task_id: str) -> bool:
        """Permanently delete one task and report whether it existed."""
        connection = self._connect()
        try:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM tasks WHERE task_id = ?",
                    (task_id,),
                )
                deleted = cursor.rowcount > 0
        finally:
            connection.close()
        return deleted

    @staticmethod
    def _restore_state(
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> AgentState:
        """Deserialize, normalize, and permanently migrate one stored state."""
        state = AgentState.model_validate_json(row["state_json"])
        statuses_before = (
            [step.status for step in state.plan.steps]
            if state.plan is not None
            else None
        )
        normalize_agent_state(state)
        statuses_after = (
            [step.status for step in state.plan.steps]
            if state.plan is not None
            else None
        )
        if statuses_after != statuses_before:
            connection.execute(
                "UPDATE tasks SET state_json = ? WHERE task_id = ?",
                (state.model_dump_json(), state.task.task_id),
            )
        return state


task_store = TaskStore()
