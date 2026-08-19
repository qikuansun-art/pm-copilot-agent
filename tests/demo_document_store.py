"""Demonstrate in-memory uploaded-document storage operations."""

from knowledge.document_store import DocumentStore


def main() -> None:
    """Add, inspect, and delete a sample stone-processing document."""
    store = DocumentStore()
    document = store.add_document(
        filename="stone_block_processing.md",
        chunks=[
            "荒料入库后需要记录荒料编号、尺寸和材质。",
            "荒料加工流程包括量尺、领料、大切、背网、粗磨、刷胶等环节。",
            "加工完成后可以扫描成图片，并用于后续库存和销售展示。",
        ],
    )

    print("document_id:", document.document_id)
    print("filename:", document.filename)
    print("chunk_count:", document.chunk_count)
    print("list_documents():", store.list_documents())
    print("get_chunks():", store.get_chunks(document.document_id))

    assert document.chunk_count == 3

    deleted = store.delete_document(document.document_id)
    print("delete_document():", deleted)
    assert deleted is True
    assert store.get_document(document.document_id) is None
    print("get_document() after delete:", store.get_document(document.document_id))


if __name__ == "__main__":
    main()
