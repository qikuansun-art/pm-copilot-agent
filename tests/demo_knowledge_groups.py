"""Demonstrate SQLite knowledge groups, document moves, and migration."""

import sqlite3
from pathlib import Path

from knowledge.document_store import DocumentStore


def remove_database(path: Path) -> None:
    """Remove an isolated test database when it exists."""
    if path.exists():
        path.unlink()


def test_group_operations(db_path: Path) -> None:
    """Verify group counts, moves, and independent deletion behavior."""
    store = DocumentStore(db_path)
    tooling_group = store.create_group("刀具管理")
    stone_group = store.create_group("荒料加工")

    tooling_document = store.add_document(
        "tool_management.md",
        ["刀具寿命需要按加工时长统计。"],
        group_id=tooling_group.group_id,
    )
    stone_document = store.add_document(
        "stone_block_processing.md",
        [
            "荒料入库需要记录编号和尺寸。",
            "荒料加工包括量尺、领料和大切。",
        ],
        group_id=stone_group.group_id,
    )

    initial_counts = {
        group.name: group.document_count for group in store.list_groups()
    }
    print("initial group counts:", initial_counts)
    assert initial_counts == {"刀具管理": 1, "荒料加工": 1}

    assert store.move_document(tooling_document.document_id, stone_group.group_id)
    moved_counts = {
        group.name: group.document_count for group in store.list_groups()
    }
    print("counts after move:", moved_counts)
    assert moved_counts == {"刀具管理": 0, "荒料加工": 2}
    assert store.get_document(tooling_document.document_id).group_id == stone_group.group_id

    assert store.delete_document(stone_document.document_id)
    assert store.get_document(stone_document.document_id) is None
    assert store.get_chunks(stone_document.document_id) == []
    print("document and chunks deleted: True")

    assert store.delete_group(stone_group.group_id)
    retained_document = store.get_document(tooling_document.document_id)
    assert retained_document is not None
    assert retained_document.group_id is None
    assert len(store.get_chunks(tooling_document.document_id)) == 1
    print("group deleted; document retained ungrouped:", retained_document)


def test_legacy_migration(db_path: Path) -> None:
    """Verify automatic addition of group_id to an existing documents table."""
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                source_type TEXT NOT NULL,
                status TEXT NOT NULL,
                chunk_count INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO documents (
                document_id, filename, source_type, status, chunk_count
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("legacy-document", "legacy.md", "uploaded", "ready", 0),
        )
        connection.commit()
    finally:
        connection.close()

    migrated_store = DocumentStore(db_path)
    migrated_document = migrated_store.get_document("legacy-document")
    assert migrated_document is not None
    assert migrated_document.group_id is None

    connection = sqlite3.connect(db_path)
    try:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(documents)")
        }
    finally:
        connection.close()
    assert "group_id" in columns
    print("legacy migration added group_id: True")


def main() -> None:
    """Run isolated group-management and migration demonstrations."""
    group_db_path = Path("data/test_knowledge_groups.db")
    legacy_db_path = Path("data/test_knowledge_legacy.db")
    remove_database(group_db_path)
    remove_database(legacy_db_path)
    try:
        test_group_operations(group_db_path)
        test_legacy_migration(legacy_db_path)
    finally:
        remove_database(group_db_path)
        remove_database(legacy_db_path)


if __name__ == "__main__":
    main()
