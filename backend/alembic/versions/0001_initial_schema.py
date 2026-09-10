"""Initial database schema with pgvector, full-text search, and RLS

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-05

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op
from app.config import settings

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Users table (mapped to Supabase auth)
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    # 3. Source documents table (full SEC filing Markdown & metadata)
    op.create_table(
        "source_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("filing_type", sa.String(length=20), server_default="10-K", nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("accession_number", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_documents")),
        sa.UniqueConstraint("accession_number", name=op.f("uq_source_documents_accession_number")),
    )
    op.create_index(op.f("ix_source_documents_ticker"), "source_documents", ["ticker"], unique=False)
    op.create_index(op.f("ix_source_documents_fiscal_year"), "source_documents", ["fiscal_year"], unique=False)
    op.create_index("ix_source_documents_ticker_year", "source_documents", ["ticker", "fiscal_year"], unique=False)

    # 4. Document chunks table (embeddings + full-text search)
    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=100), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(settings.embedding_dimensions), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', coalesce(chunk_text, ''))", persisted=True),
            nullable=True,
        ),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["source_documents.id"],
            name=op.f("fk_document_chunks_document_id_source_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
    )
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_section"), "document_chunks", ["section"], unique=False)
    op.create_index("ix_document_chunks_doc_chunk_idx", "document_chunks", ["document_id", "chunk_index"], unique=False)

    # Explicit HNSW and GIN indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_search_vector_gin "
        "ON document_chunks USING gin (search_vector);"
    )

    # 5. Chat threads table
    op.create_table(
        "chat_threads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), server_default="New Research Chat", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_threads_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_threads")),
    )
    op.create_index(op.f("ix_chat_threads_user_id"), "chat_threads", ["user_id"], unique=False)

    # 6. Chat messages table
    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "message_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["chat_threads.id"],
            name=op.f("fk_chat_messages_thread_id_chat_threads"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index(op.f("ix_chat_messages_thread_id"), "chat_messages", ["thread_id"], unique=False)

    # 7. Message citations table
    op.create_table(
        "message_citations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("citation_index", sa.Integer(), server_default="1", nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            name=op.f("fk_message_citations_chunk_id_document_chunks"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["source_documents.id"],
            name=op.f("fk_message_citations_document_id_source_documents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name=op.f("fk_message_citations_message_id_chat_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_citations")),
    )
    op.create_index(op.f("ix_message_citations_chunk_id"), "message_citations", ["chunk_id"], unique=False)
    op.create_index(op.f("ix_message_citations_document_id"), "message_citations", ["document_id"], unique=False)
    op.create_index(op.f("ix_message_citations_message_id"), "message_citations", ["message_id"], unique=False)

    # 8. Row Level Security (RLS) enablement and policies
    for table_name in [
        "users",
        "source_documents",
        "document_chunks",
        "chat_threads",
        "chat_messages",
        "message_citations",
    ]:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")

    # Source documents & chunks: read-only access for authenticated users
    op.execute(
        "CREATE POLICY \"Allow authenticated read on source_documents\" "
        "ON source_documents FOR SELECT "
        "TO authenticated "
        "USING (true);"
    )
    op.execute(
        "CREATE POLICY \"Allow authenticated read on document_chunks\" "
        "ON document_chunks FOR SELECT "
        "TO authenticated "
        "USING (true);"
    )

    # User profile policy: users can only view and update their own record
    op.execute(
        "CREATE POLICY \"Users can view their own profile\" "
        "ON users FOR SELECT "
        "TO authenticated "
        "USING (auth.uid() = id);"
    )
    op.execute(
        "CREATE POLICY \"Users can update their own profile\" "
        "ON users FOR UPDATE "
        "TO authenticated "
        "USING (auth.uid() = id);"
    )

    # Chat threads policy: isolate threads per user
    op.execute(
        "CREATE POLICY \"Users can manage their own threads\" "
        "ON chat_threads FOR ALL "
        "TO authenticated "
        "USING (auth.uid() = user_id) "
        "WITH CHECK (auth.uid() = user_id);"
    )

    # Chat messages policy: isolate messages via thread ownership
    op.execute(
        "CREATE POLICY \"Users can manage messages in their own threads\" "
        "ON chat_messages FOR ALL "
        "TO authenticated "
        "USING (EXISTS (SELECT 1 FROM chat_threads WHERE chat_threads.id = chat_messages.thread_id AND chat_threads.user_id = auth.uid())) "
        "WITH CHECK (EXISTS (SELECT 1 FROM chat_threads WHERE chat_threads.id = chat_messages.thread_id AND chat_threads.user_id = auth.uid()));"
    )

    # Message citations policy: isolate citations via message & thread ownership
    op.execute(
        "CREATE POLICY \"Users can view citations in their own threads\" "
        "ON message_citations FOR SELECT "
        "TO authenticated "
        "USING (EXISTS ("
        "  SELECT 1 FROM chat_messages "
        "  JOIN chat_threads ON chat_threads.id = chat_messages.thread_id "
        "  WHERE chat_messages.id = message_citations.message_id AND chat_threads.user_id = auth.uid()"
        "));"
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("message_citations")
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")
    op.drop_table("document_chunks")
    op.drop_table("source_documents")
    op.drop_table("users")

    # Optionally drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector;")
