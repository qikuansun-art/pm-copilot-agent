"""Demonstrate task binding to validated knowledge groups."""

from unittest.mock import patch

from fastapi import HTTPException

from api.main import CreateTaskRequest, create_task, tasks
from knowledge.document_store import document_store


def main() -> None:
    """Verify valid task binding and rejection of an unknown group ID."""
    group = document_store.create_group("荒料加工")
    created_task_id: str | None = None
    try:
        payload = CreateTaskRequest(
            title="荒料加工管理规划",
            request="帮我规划一个石材荒料加工管理功能",
            knowledge_group_ids=[group.group_id],
        )
        with patch("api.main.PMCopilotRuntime") as runtime_class:
            runtime_class.return_value.start_task.side_effect = lambda state: state
            response = create_task(payload)

        created_task_id = response["task_id"]
        state = tasks[created_task_id]
        print("saved knowledge_group_ids:", state.task.knowledge_group_ids)
        assert state.task.knowledge_group_ids == [group.group_id]
        assert response["knowledge_group_ids"] == [group.group_id]

        invalid_payload = CreateTaskRequest(
            title="无效知识分组任务",
            request="测试不存在的知识分组",
            knowledge_group_ids=["missing-group-id"],
        )
        task_count_before_rejection = len(tasks)
        try:
            create_task(invalid_payload)
        except HTTPException as error:
            print("invalid group rejected:", error.status_code, error.detail)
            assert error.status_code == 422
            assert error.detail == "Unknown knowledge group: missing-group-id"
            assert len(tasks) == task_count_before_rejection
        else:
            raise AssertionError("Unknown knowledge group should be rejected")
    finally:
        if created_task_id is not None:
            tasks.pop(created_task_id, None)
        document_store.delete_group(group.group_id)


if __name__ == "__main__":
    main()
