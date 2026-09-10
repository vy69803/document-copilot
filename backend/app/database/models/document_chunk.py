import datetime
import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import FetchedValue

from app.config import settings
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.message_citation import MessageCitation
    from app.database.models.source_document import SourceDocument


class DocumentChunk(Base):
    """Retrieval-ready passage chunks with embeddings and full-text search vectors."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector embedding (pgvector)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimensions),
        nullable=True,
    )

    # Postgres full-text search vector (generated always column in DB)
    search_vector: Mapped[Any | None] = mapped_column(
        TSVECTOR,
        server_default=FetchedValue(),
        server_onupdate=FetchedValue(),
        nullable=True,
    )
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped["SourceDocument"] = relationship(
        "SourceDocument",
        back_populates="chunks",
    )
    citations: Mapped[list["MessageCitation"]] = relationship(
        "MessageCitation",
        back_populates="chunk",
    )

    __table_args__ = (
        Index("ix_document_chunks_doc_chunk_idx", "document_id", "chunk_index"),
    )
