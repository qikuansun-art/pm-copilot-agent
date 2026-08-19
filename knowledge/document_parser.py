"""Text parsing and chunking for supported internal knowledge documents."""

import re
from pathlib import Path


class DocumentParser:
    """Parses UTF-8 text documents into ordered, paragraph-aware chunks."""

    def parse(self, filename: str, content: bytes) -> list[str]:
        """Decode and chunk a supported document without storing it."""
        if Path(filename).suffix.lower() not in {".txt", ".md"}:
            raise ValueError("Unsupported document type")

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Unable to decode document as UTF-8") from error

        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        text = re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", text)
        if not text:
            return []

        return self._chunk_text(text)

    def _chunk_text(self, text: str, max_chars: int = 800) -> list[str]:
        """Split text by paragraphs while keeping chunks within the size limit."""
        if max_chars <= 0:
            raise ValueError("max_chars must be greater than zero")

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n[ \t]*\n", text)
            if paragraph.strip()
        ]
        chunks: list[str] = []
        current_paragraphs: list[str] = []
        current_length = 0

        def flush_current() -> None:
            nonlocal current_paragraphs, current_length
            if current_paragraphs:
                chunks.append("\n\n".join(current_paragraphs))
                current_paragraphs = []
                current_length = 0

        for paragraph in paragraphs:
            if len(paragraph) > max_chars:
                flush_current()
                chunks.extend(
                    paragraph[start : start + max_chars]
                    for start in range(0, len(paragraph), max_chars)
                )
                continue

            separator_length = 2 if current_paragraphs else 0
            if current_length + separator_length + len(paragraph) > max_chars:
                flush_current()

            current_paragraphs.append(paragraph)
            current_length += (2 if current_length else 0) + len(paragraph)

        flush_current()
        return chunks


document_parser = DocumentParser()
