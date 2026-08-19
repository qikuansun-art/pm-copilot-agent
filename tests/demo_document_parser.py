"""Demonstrate Markdown parsing and paragraph-aware automatic chunking."""

from knowledge.document_parser import document_parser


def main() -> None:
    """Parse a sample document and verify chunk and format handling."""
    long_paragraph = "".join(
        f"第{index}批荒料加工时需要持续记录工序状态、质量结果和责任人员。"
        for index in range(1, 61)
    )
    markdown_text = f"""# 石材荒料加工管理

荒料入库：
记录荒料编号、材质、尺寸、供应商等信息。

加工流程：
量尺、领料、大切、背网、粗磨、刷胶、修边、表面处理、烘干、打蜡。

扫描：
加工完成后扫描板材图片，用于库存管理和后续销售展示。

过程记录：
{long_paragraph}
"""

    chunks = document_parser.parse(
        "stone_block_processing.md",
        markdown_text.encode("utf-8"),
    )

    print("chunk count:", len(chunks))
    for index, chunk in enumerate(chunks):
        print(f"\nchunk index: {index}")
        print("characters:", len(chunk))
        print("content:")
        print(chunk)

    assert chunks
    assert all(chunk for chunk in chunks)
    assert all(len(chunk) <= 800 for chunk in chunks)

    reconstructed = "\n\n".join(chunks)
    core_content = [
        "# 石材荒料加工管理",
        "记录荒料编号、材质、尺寸、供应商等信息。",
        "量尺、领料、大切、背网、粗磨、刷胶、修边、表面处理、烘干、打蜡。",
        "加工完成后扫描板材图片，用于库存管理和后续销售展示。",
        "第60批荒料加工时需要持续记录工序状态、质量结果和责任人员。",
    ]
    assert all(item in reconstructed for item in core_content)

    try:
        document_parser.parse("test.pdf", b"test")
    except ValueError as error:
        assert str(error) == "Unsupported document type"
        print("\nPDF test passed:", error)
    else:
        raise AssertionError("PDF input should be rejected")


if __name__ == "__main__":
    main()
