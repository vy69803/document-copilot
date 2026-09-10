"""Database query helpers for semantic (pgvector) and lexical (Postgres FTS) search."""

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select

from app.config import settings
from app.database.models.document_chunk import DocumentChunk
from app.database.models.source_document import SourceDocument
from app.database.session import get_db_session

logger = structlog.get_logger(__name__)


def search_dense(
    query_vector: list[float],
    limit: int | None = None,
    ticker: str | None = None,
    fiscal_year: int | None = None,
    filing_type: str | None = None,
) -> list[dict[str, Any]]:
    """Perform cosine distance similarity search against document_chunks embedding with pgvector.

    Returns candidate chunks ordered by cosine distance ascending.
    """
    effective_limit = limit if limit is not None else settings.retrieval_candidate_k

    with get_db_session() as session:
        distance_col = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

        stmt = (
            select(
                DocumentChunk,
                distance_col,
                SourceDocument.ticker,
                SourceDocument.company_name,
                SourceDocument.fiscal_year,
                SourceDocument.filing_type,
            )
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .where(DocumentChunk.embedding.is_not(None))
        )

        if ticker:
            stmt = stmt.where(SourceDocument.ticker == ticker.upper())
        if fiscal_year:
            stmt = stmt.where(SourceDocument.fiscal_year == fiscal_year)
        if filing_type:
            stmt = stmt.where(SourceDocument.filing_type == filing_type.upper())

        stmt = stmt.order_by(distance_col.asc()).limit(effective_limit)
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


def search_lexical(
    query_text: str,
    limit: int | None = None,
    fts_config: str | None = None,
    ticker: str | None = None,
    fiscal_year: int | None = None,
    filing_type: str | None = None,
) -> list[dict[str, Any]]:
    """Perform full-text search against document_chunks search_vector using Postgres FTS.

    Uses `websearch_to_tsquery(fts_config, query)` and ranks candidates using `ts_rank_cd`.
    """
    clean_query = query_text.strip()
    if not clean_query:
        return []

    effective_limit = limit if limit is not None else settings.retrieval_candidate_k
    effective_config = fts_config or settings.retrieval_fts_config

    with get_db_session() as session:
        ts_query = func.websearch_to_tsquery(effective_config, clean_query)
        rank_col = func.ts_rank_cd(DocumentChunk.search_vector, ts_query).label("rank")

        stmt = (
            select(
                DocumentChunk,
                rank_col,
                SourceDocument.ticker,
                SourceDocument.company_name,
                SourceDocument.fiscal_year,
                SourceDocument.filing_type,
            )
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .where(DocumentChunk.search_vector.op("@@")(ts_query))
        )

        if ticker:
            stmt = stmt.where(SourceDocument.ticker == ticker.upper())
        if fiscal_year:
            stmt = stmt.where(SourceDocument.fiscal_year == fiscal_year)
        if filing_type:
            stmt = stmt.where(SourceDocument.filing_type == filing_type.upper())

        stmt = stmt.order_by(rank_col.desc()).limit(effective_limit)
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
                "lexical_rank": float(row.rank) if row.rank is not None else 0.0,
                "ticker": row.ticker,
                "company_name": row.company_name,
                "fiscal_year": row.fiscal_year,
                "filing_type": row.filing_type,
            }
            for row in results
        ]


def get_chunks_by_ids(chunk_ids: list[str | uuid.UUID]) -> list[dict[str, Any]]:
    """Fetch chunk details and parent document metadata for a batch of chunk IDs."""
    if not chunk_ids:
        return []

    uids = [uuid.UUID(str(cid)) for cid in chunk_ids]

    with get_db_session() as session:
        stmt = (
            select(
                DocumentChunk,
                SourceDocument.ticker,
                SourceDocument.company_name,
                SourceDocument.fiscal_year,
                SourceDocument.filing_type,
            )
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .where(DocumentChunk.id.in_(uids))
        )

        results = session.execute(stmt).all()
        chunks_map = {
            str(row.DocumentChunk.id): {
                "chunk_id": str(row.DocumentChunk.id),
                "document_id": str(row.DocumentChunk.document_id),
                "chunk_index": row.DocumentChunk.chunk_index,
                "section": row.DocumentChunk.section,
                "page": row.DocumentChunk.page,
                "chunk_text": row.DocumentChunk.chunk_text,
                "token_count": row.DocumentChunk.token_count,
                "ticker": row.ticker,
                "company_name": row.company_name,
                "fiscal_year": row.fiscal_year,
                "filing_type": row.filing_type,
            }
            for row in results
        }

        # Preserve the ordering of the input chunk_ids
        return [chunks_map[str(cid)] for cid in chunk_ids if str(cid) in chunks_map]


def get_surrounding_chunks(
    document_id: str | uuid.UUID,
    chunk_index: int,
    window: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch adjacent chunks for contextual expansion (e.g. chunk_index - 1, chunk_index + 1)."""
    effective_window = window if window is not None else settings.retrieval_neighbor_radius
    doc_uid = uuid.UUID(str(document_id))
    min_idx = max(0, chunk_index - effective_window)
    max_idx = chunk_index + effective_window

    with get_db_session() as session:
        stmt = (
            select(
                DocumentChunk,
                SourceDocument.ticker,
                SourceDocument.company_name,
                SourceDocument.fiscal_year,
                SourceDocument.filing_type,
            )
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .where(
                DocumentChunk.document_id == doc_uid,
                DocumentChunk.chunk_index >= min_idx,
                DocumentChunk.chunk_index <= max_idx,
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )

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
                "ticker": row.ticker,
                "company_name": row.company_name,
                "fiscal_year": row.fiscal_year,
                "filing_type": row.filing_type,
            }
            for row in results
        ]
