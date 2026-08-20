"""Regression coverage for persistent task deletion and knowledge isolation."""

from pathlib import Path

from api.task_store import TaskStore
from knowledge.document_store import DocumentStore
from models.state import AgentState, TaskContext


def make_task(task_id: str, group_ids: list[str] | None = None) -> AgentState:
    """Build a minimal persisted task."""
    return AgentState(
        task=TaskContext(
            task_id=task_id,
            title=f"Task {task_id}",
            original_request="测试历史方案删除",
            knowledge_group_ids=group_ids or [],
        )
    )


def main() -> None:
    """Cover existing, missing, restarted, and knowledge-linked deletion."""
    task_db_path = Path("data/test_task_deletion.db")
    knowledge_db_path = Path("data/test_task_deletion_knowledge.db")
    for path in (task_db_path, knowledge_db_path):
        if path.exists():
            path.unlink()

    try:
        store = TaskStore(task_db_path)

        # Case A: an existing task is deleted and cannot be loaded.
        case_a = make_task("delete-existing")
        store.save(case_a)
        assert store.delete_task(case_a.task.task_id) is True
        assert store.get(case_a.task.task_id) is None

        # Case B: deleting an unknown task reports False.
        assert store.delete_task("missing-task") is False

        # Case C: deletion remains effective after recreating TaskStore.
        case_c = make_task("delete-before-restart")
        store.save(case_c)
        assert store.delete_task(case_c.task.task_id) is True
        restarted_store = TaskStore(task_db_path)
        assert restarted_store.get(case_c.task.task_id) is None
        assert all(
            state.task.task_id != case_c.task.task_id
            for state in restarted_store.list()
        )

        # Case D: task references never cascade into the knowledge database.
        knowledge_store = DocumentStore(knowledge_db_path)
        group = knowledge_store.create_group("保留的知识分组")
        document = knowledge_store.add_document(
            "retained.md",
            ["删除任务后仍需保留的知识内容。"],
            group_id=group.group_id,
        )
        case_d = make_task("delete-with-knowledge", [group.group_id])
        restarted_store.save(case_d)
        assert restarted_store.delete_task(case_d.task.task_id) is True
        assert knowledge_store.get_group(group.group_id) is not None
        assert knowledge_store.get_document(document.document_id) is not None
        assert len(knowledge_store.get_chunks(document.document_id)) == 1

        print("Case A: deleted=True and get=None")
        print("Case B: deleted=False")
        print("Case C: absent after TaskStore restart")
        print("Case D: knowledge group, document, and chunk retained")
    finally:
        for path in (task_db_path, knowledge_db_path):
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    main()
