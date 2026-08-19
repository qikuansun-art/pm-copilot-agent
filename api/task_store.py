"""SQLite persistence for complete PM Copilot task states."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from models.state import AgentState


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
            row = connection.execute(
                "SELECT state_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        finally:
            connection.close()
        return AgentState.model_validate_json(row["state_json"]) if row else None

    def list(self) -> list[AgentState]:
        """Return persisted tasks with the most recently updated first."""
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT state_json FROM tasks ORDER BY updated_at DESC"
            ).fetchall()
        finally:
            connection.close()
        return [AgentState.model_validate_json(row["state_json"]) for row in rows]


task_store = TaskStore()
