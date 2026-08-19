"""SQLite-backed storage for uploaded document records and text chunks."""

import sqlite3
from pathlib import Path
from uuid import uuid4

from models.knowledge import DocumentRecord, KnowledgeChunk, KnowledgeGroup


class DocumentStore:
    """Persists uploaded-document metadata and chunks in a local SQLite file."""

    def __init__(self, db_path: str | Path = "data/knowledge.db") -> None:
        """Initialize the database path and create the required tables."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        """Open a configured connection to the document database."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        """Create document and chunk tables when they do not yet exist."""
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS groups (
                        group_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        chunk_count INTEGER NOT NULL,
                        group_id TEXT NULL
                    )
                    """
                )
                document_columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(documents)"
                    ).fetchall()
                }
                if "group_id" not in document_columns:
                    connection.execute(
                        "ALTER TABLE documents ADD COLUMN group_id TEXT NULL"
                    )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chunks (
                        chunk_id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        content TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        source_type TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chunks_document_id
                    ON chunks (document_id, chunk_index)
                    """
                )
        finally:
            connection.close()

    def create_group(self, name: str) -> KnowledgeGroup:
        """Create and persist a named knowledge group."""
        group = KnowledgeGroup(group_id=str(uuid4()), name=name)
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO groups (group_id, name) VALUES (?, ?)",
                    (group.group_id, group.name),
                )
        finally:
            connection.close()
        return group

    def list_groups(self) -> list[KnowledgeGroup]:
        """Return all groups with their current document counts."""
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT g.group_id, g.name, COUNT(d.document_id) AS document_count
                FROM groups AS g
                LEFT JOIN documents AS d ON d.group_id = g.group_id
                GROUP BY g.group_id, g.name, g.rowid
                ORDER BY g.rowid
                """
            ).fetchall()
        finally:
            connection.close()
        return [KnowledgeGroup.model_validate(dict(row)) for row in rows]

    def get_group(self, group_id: str) -> KnowledgeGroup | None:
        """Return a group and its document count, or None if absent."""
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT g.group_id, g.name, COUNT(d.document_id) AS document_count
                FROM groups AS g
                LEFT JOIN documents AS d ON d.group_id = g.group_id
                WHERE g.group_id = ?
                GROUP BY g.group_id, g.name
                """,
                (group_id,),
            ).fetchone()
        finally:
            connection.close()
        return KnowledgeGroup.model_validate(dict(row)) if row is not None else None

    def delete_group(self, group_id: str) -> bool:
        """Delete a group after moving its documents to the ungrouped state."""
        connection = self._connect()
        try:
            with connection:
                existing = connection.execute(
                    "SELECT 1 FROM groups WHERE group_id = ?",
                    (group_id,),
                ).fetchone()
                if existing is None:
                    return False
                connection.execute(
                    "UPDATE documents SET group_id = NULL WHERE group_id = ?",
                    (group_id,),
                )
                connection.execute(
                    "DELETE FROM groups WHERE group_id = ?",
                    (group_id,),
                )
        finally:
            connection.close()
        return True

    def move_document(self, document_id: str, group_id: str | None) -> bool:
        """Move a document into a group or into the ungrouped state."""
        connection = self._connect()
        try:
            with connection:
                document_exists = connection.execute(
                    "SELECT 1 FROM documents WHERE document_id = ?",
                    (document_id,),
                ).fetchone()
                if document_exists is None:
                    return False
                if group_id is not None:
                    group_exists = connection.execute(
                        "SELECT 1 FROM groups WHERE group_id = ?",
                        (group_id,),
                    ).fetchone()
                    if group_exists is None:
                        return False
                connection.execute(
                    "UPDATE documents SET group_id = ? WHERE document_id = ?",
                    (group_id, document_id),
                )
        finally:
            connection.close()
        return True

    def add_document(
        self,
        filename: str,
        chunks: list[str],
        group_id: str | None = None,
    ) -> DocumentRecord:
        """Persist a new document and all supplied chunks in one transaction."""
        document = DocumentRecord(
            document_id=str(uuid4()),
            filename=filename,
            chunk_count=len(chunks),
            group_id=group_id,
        )
        knowledge_chunks = [
            KnowledgeChunk(
                chunk_id=str(uuid4()),
                document_id=document.document_id,
                filename=filename,
                content=content,
                chunk_index=chunk_index,
            )
            for chunk_index, content in enumerate(chunks)
        ]

        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO documents (
                        document_id, filename, source_type, status,
                        chunk_count, group_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.document_id,
                        document.filename,
                        document.source_type,
                        document.status,
                        document.chunk_count,
                        document.group_id,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO chunks (
                        chunk_id, document_id, filename, content,
                        chunk_index, source_type
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            chunk.chunk_id,
                            chunk.document_id,
                            chunk.filename,
                            chunk.content,
                            chunk.chunk_index,
                            chunk.source_type,
                        )
                        for chunk in knowledge_chunks
                    ],
                )
        finally:
            connection.close()

        return document

    def get_document(self, document_id: str) -> DocumentRecord | None:
        """Load a document by ID, or return None when it does not exist."""
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT document_id, filename, source_type, status,
                       chunk_count, group_id
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        finally:
            connection.close()

        return DocumentRecord.model_validate(dict(row)) if row is not None else None

    def list_documents(self) -> list[DocumentRecord]:
        """Load all stored document records in insertion order."""
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT document_id, filename, source_type, status,
                       chunk_count, group_id
                FROM documents
                ORDER BY rowid
                """
            ).fetchall()
        finally:
            connection.close()

        return [DocumentRecord.model_validate(dict(row)) for row in rows]

    def get_chunks(self, document_id: str) -> list[KnowledgeChunk]:
        """Load a document's chunks ordered by their zero-based chunk index."""
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT chunk_id, document_id, filename, content,
                       chunk_index, source_type
                FROM chunks
                WHERE document_id = ?
                ORDER BY chunk_index
                """,
                (document_id,),
            ).fetchall()
        finally:
            connection.close()

        return [KnowledgeChunk.model_validate(dict(row)) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks, returning whether it existed."""
        connection = self._connect()
        try:
            with connection:
                existing = connection.execute(
                    "SELECT 1 FROM documents WHERE document_id = ?",
                    (document_id,),
                ).fetchone()
                if existing is None:
                    return False

                connection.execute(
                    "DELETE FROM chunks WHERE document_id = ?",
                    (document_id,),
                )
                connection.execute(
                    "DELETE FROM documents WHERE document_id = ?",
                    (document_id,),
                )
        finally:
            connection.close()

        return True


document_store = DocumentStore()
