import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.document_chunk import DocumentChunk
    from app.database.models.message_citation import MessageCitation


class SourceDocument(Base):
    """Stores full normalized SEC filing metadata and Markdown content."""

    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    filing_type: Mapped[str] = mapped_column(String(20), nullable=False, default="10-K")
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filing_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    accession_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)

    # Mapped as "metadata" in DB, using metadata_ to avoid collision with Base.metadata
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
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )
    citations: Mapped[list["MessageCitation"]] = relationship(
        "MessageCitation",
        back_populates="document",
    )

    __table_args__ = (
        Index("ix_source_documents_ticker_year", "ticker", "fiscal_year"),
    )
