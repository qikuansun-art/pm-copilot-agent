"""Demonstrate persistence of uploaded documents across store instances."""

from pathlib import Path

from knowledge.document_store import DocumentStore


def main() -> None:
    """Persist, reopen, verify, and delete a sample document."""
    test_db_path = Path("data/test_knowledge.db")
    if test_db_path.exists():
        test_db_path.unlink()

    try:
        first_store = DocumentStore(test_db_path)
        document = first_store.add_document(
            filename="stone_block_processing.md",
            chunks=[
                "荒料入库需要记录编号和尺寸。",
                "荒料加工包括量尺、领料、大切和表面处理。",
                "加工完成后扫描并用于库存和销售展示。",
            ],
        )
        print("document_id:", document.document_id)
        print("chunk_count:", document.chunk_count)
        assert document.chunk_count == 3

        reopened_store = DocumentStore(test_db_path)
        documents = reopened_store.list_documents()
        chunks = reopened_store.get_chunks(document.document_id)
        print("documents after reopening:", documents)
        print("chunks after reopening:", chunks)

        assert len(documents) == 1
        assert documents[0] == document
        assert len(chunks) == 3
        assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]

        deleted = reopened_store.delete_document(document.document_id)
        print("delete_document():", deleted)
        assert deleted is True
        assert reopened_store.get_document(document.document_id) is None
        assert reopened_store.get_chunks(document.document_id) == []
    finally:
        if test_db_path.exists():
            test_db_path.unlink()


if __name__ == "__main__":
    main()
