"""Database helpers for source_documents and document_chunks.

Provides insert, upsert, and query operations using SQLAlchemy models
and direct database session management.
"""

import uuid
from typing import Any

import structlog
from sqlalchemy import delete, func, select

from app.database.models.document_chunk import DocumentChunk
from app.database.models.source_document import SourceDocument
from app.database.session import get_db_session

logger = structlog.get_logger(__name__)


# ─── Source Document Helpers ──────────────────────────────────────────


def upsert_source_document(document_data: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a single source document by accession_number."""
    with get_db_session() as session:
        stmt = select(SourceDocument).where(
            SourceDocument.accession_number == document_data["accession_number"]
        )
        existing = session.scalar(stmt)

        if existing:
            for key, val in document_data.items():
                if key == "metadata":
                    existing.metadata_ = val
                elif hasattr(existing, key):
                    setattr(existing, key, val)
            session.flush()
            doc_id = str(existing.id)
        else:
            payload = dict(document_data)
            if "metadata" in payload:
                payload["metadata_"] = payload.pop("metadata")
            doc = SourceDocument(**payload)
            session.add(doc)
            session.flush()
            doc_id = str(doc.id)

        return {
            "id": doc_id,
            "ticker": document_data.get("ticker"),
            "fiscal_year": document_data.get("fiscal_year"),
            "accession_number": document_data.get("accession_number"),
        }


def get_source_document(document_id: str | uuid.UUID) -> dict[str, Any] | None:
    """Fetch a single source document by ID."""
    with get_db_session() as session:
        uid = uuid.UUID(str(document_id))
        doc = session.get(SourceDocument, uid)
        if not doc:
            return None
        return {
            "id": str(doc.id),
            "ticker": doc.ticker,
            "company_name": doc.company_name,
            "filing_type": doc.filing_type,
            "fiscal_year": doc.fiscal_year,
            "filing_date": str(doc.filing_date),
            "accession_number": doc.accession_number,
            "source_url": doc.source_url,
            "content_markdown": doc.content_markdown,
            "metadata": doc.metadata_,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }


def list_source_documents(
    ticker: str | None = None,
    fiscal_year: int | None = None,
) -> list[dict[str, Any]]:
    """List source documents with optional ticker and fiscal year filters."""
    with get_db_session() as session:
        stmt = select(SourceDocument)
        if ticker:
            stmt = stmt.where(SourceDocument.ticker == ticker.upper())
        if fiscal_year:
            stmt = stmt.where(SourceDocument.fiscal_year == fiscal_year)

        stmt = stmt.order_by(SourceDocument.fiscal_year.desc(), SourceDocument.ticker.asc())
        docs = session.scalars(stmt).all()

        return [
            {
                "id": str(doc.id),
                "ticker": doc.ticker,
                "company_name": doc.company_name,
                "filing_type": doc.filing_type,
                "fiscal_year": doc.fiscal_year,
                "filing_date": str(doc.filing_date),
                "accession_number": doc.accession_number,
                "source_url": doc.source_url,
                "metadata": doc.metadata_,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in docs
        ]


# ─── Document Chunk Helpers ───────────────────────────────────────────


def bulk_insert_chunks(chunks_data: list[dict[str, Any]]) -> int:
    """Bulk insert document chunks with vector embeddings into the database.

    Returns the count of chunks inserted.
    """
    if not chunks_data:
        return 0

    with get_db_session() as session:
        chunk_objects = []
        for c in chunks_data:
            payload = dict(c)
            if "document_id" in payload and isinstance(payload["document_id"], str):
                payload["document_id"] = uuid.UUID(payload["document_id"])
            if "metadata" in payload:
                payload["metadata_"] = payload.pop("metadata")

            chunk_obj = DocumentChunk(**payload)
            chunk_objects.append(chunk_obj)

        session.add_all(chunk_objects)
        session.flush()
        count = len(chunk_objects)
        logger.info("chunks.bulk_inserted", count=count)
        return count


def delete_chunks_by_document(document_id: str | uuid.UUID) -> int:
    """Delete all chunks belonging to a specific source document."""
    with get_db_session() as session:
        uid = uuid.UUID(str(document_id))
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == uid)
        result = session.execute(stmt)
        deleted = result.rowcount
        logger.info("chunks.deleted_for_doc", document_id=str(document_id), count=deleted)
        return deleted


def get_chunk_count(document_id: str | uuid.UUID | None = None) -> int:
    """Get total count of chunks in the database or for a specific document."""
    with get_db_session() as session:
        stmt = select(func.count(DocumentChunk.id))
        if document_id:
            uid = uuid.UUID(str(document_id))
            stmt = stmt.where(DocumentChunk.document_id == uid)
        return session.scalar(stmt) or 0


def search_chunks_vector(
    query_embedding: list[float],
    limit: int = 5,
    ticker: str | None = None,
) -> list[dict[str, Any]]:
    """Perform cosine distance similarity search against document_chunks embedding."""
    with get_db_session() as session:
        # Cosine distance operator in pgvector is <=>
        distance_col = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")

        stmt = select(
            DocumentChunk,
            distance_col,
            SourceDocument.ticker,
            SourceDocument.company_name,
            SourceDocument.fiscal_year,
            SourceDocument.filing_type,
        ).join(
            SourceDocument, DocumentChunk.document_id == SourceDocument.id
        )

        if ticker:
            stmt = stmt.where(SourceDocument.ticker == ticker.upper())

        stmt = stmt.order_by(distance_col.asc()).limit(limit)
        results = session.execute(stmt).all()

        return [
            {
                "chunk_id": str(row.DocumentChunk.id),
                "document_id": str(row.DocumentChunk.document_id),
                "chunk_index": row.DocumentChunk.chunk_index,
                "section": row.DocumentChunk.section,
                "page": row.DocumentChunk.page,
                "chunk_text": row.DocumentChunk.chunk_text,
                "token_count": row.DocumentChunk.token_count,
                "distance": float(row.distance) if row.distance is not None else None,
                "similarity": 1.0 - float(row.distance) if row.distance is not None else None,
                "ticker": row.ticker,
                "company_name": row.company_name,
                "fiscal_year": row.fiscal_year,
                "filing_type": row.filing_type,
            }
            for row in results
        ]
