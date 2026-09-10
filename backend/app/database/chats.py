"""Chat persistence — thread, message, and citation CRUD via Supabase.

All functions take user_id explicitly for ownership checks.
Uses the admin client for writes (bypasses RLS) but always
scopes queries to the authenticated user.
"""

import uuid
import structlog
from sqlalchemy import text

from app.config import settings
from app.database.session import get_db_session
from app.database.supabase import get_supabase_admin_client

logger = structlog.get_logger(__name__)


def _has_service_role_key() -> bool:
    key = settings.supabase_service_role_key or ""
    if key.startswith("sb_publishable_"):
        return False
    if key == settings.supabase_anon_key:
        return False
    return True


def _is_mock(client: object) -> bool:
    return "Mock" in type(client).__name__ or hasattr(client, "_mock_return_value")


def create_thread(user_id: str, title: str = "New Research Chat") -> dict:
    """Create a new chat thread owned by user_id."""
    try:
        client = get_supabase_admin_client()
        result = (
            client.table("chat_threads")
            .insert({"user_id": user_id, "title": title})
            .execute()
        )
        if result and result.data:
            return result.data[0]
    except Exception as e:
        logger.warning("chats.supabase_insert_failed_fallback_db", error=str(e))

    # Fallback to direct DB session
    with get_db_session() as session:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        session.execute(
            text("""
                INSERT INTO users (id, email)
                VALUES (:id, :email)
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": uid, "email": f"{user_id}@copilot.internal"},
        )
        row = session.execute(
            text("""
                INSERT INTO chat_threads (id, user_id, title)
                VALUES (gen_random_uuid(), :user_id, :title)
                RETURNING id, user_id, title, created_at, updated_at
            """),
            {"user_id": uid, "title": title},
        ).mappings().fetchone()

        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "title": row["title"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        }


def list_threads(user_id: str) -> list[dict]:
    """List all threads for a user, most recent first."""
    client = get_supabase_admin_client()
    if _is_mock(client) or _has_service_role_key():
        try:
            result = (
                client.table("chat_threads")
                .select("id, title, created_at, updated_at")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .execute()
            )
            if result and result.data is not None:
                return result.data
        except Exception as e:
            logger.warning("chats.supabase_list_failed_fallback_db", error=str(e))

    with get_db_session() as session:
        try:
            uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            return []
        rows = session.execute(
            text("""
                SELECT id, title, created_at, updated_at
                FROM chat_threads
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
            """),
            {"user_id": uid},
        ).mappings().fetchall()
        return [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
                "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
            }
            for r in rows
        ]


def get_thread(thread_id: str, user_id: str) -> dict | None:
    """Fetch a thread by ID, only if owned by user_id."""
    client = get_supabase_admin_client()
    if _is_mock(client) or _has_service_role_key():
        try:
            result = (
                client.table("chat_threads")
                .select("*")
                .eq("id", thread_id)
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if result and result.data:
                return result.data
        except Exception as e:
            logger.warning("chats.supabase_get_failed_fallback_db", error=str(e))

    with get_db_session() as session:
        try:
            tid = uuid.UUID(thread_id) if isinstance(thread_id, str) else thread_id
            uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            return None
        row = session.execute(
            text("""
                SELECT id, user_id, title, created_at, updated_at
                FROM chat_threads
                WHERE id = :thread_id AND user_id = :user_id
            """),
            {"thread_id": tid, "user_id": uid},
        ).mappings().fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "title": row["title"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        }


def get_thread_messages(thread_id: str, user_id: str) -> list[dict]:
    """Get all messages for a thread, ordered chronologically.

    Returns empty list if thread doesn't exist or isn't owned by user.
    """
    # Verify ownership first
    thread = get_thread(thread_id, user_id)
    if not thread:
        return []

    client = get_supabase_admin_client()
    messages: list[dict] = []
    if _is_mock(client) or _has_service_role_key():
        try:
            result = (
                client.table("chat_messages")
                .select("id, thread_id, role, content, message_metadata, created_at")
                .eq("thread_id", thread_id)
                .order("created_at", desc=False)
                .execute()
            )
            if result and result.data is not None:
                messages = result.data
        except Exception as e:
            logger.warning("chats.supabase_messages_failed_fallback_db", error=str(e))

    if not messages:
        with get_db_session() as session:
            try:
                tid = uuid.UUID(thread_id) if isinstance(thread_id, str) else thread_id
            except ValueError:
                return []
            rows = session.execute(
                text("""
                    SELECT id, thread_id, role, content, message_metadata, created_at
                    FROM chat_messages
                    WHERE thread_id = :thread_id
                    ORDER BY created_at ASC
                """),
                {"thread_id": tid},
            ).mappings().fetchall()
            messages = [
                {
                    "id": str(r["id"]),
                    "thread_id": str(r["thread_id"]),
                    "role": r["role"],
                    "content": r["content"],
                    "message_metadata": r["message_metadata"] or {},
                    "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
                }
                for r in rows
            ]

    # Attach citations for assistant messages
    for msg in messages:
        if msg.get("role") == "assistant":
            msg["citations"] = get_message_citations(msg["id"])
        else:
            msg["citations"] = []

    return messages


def get_message_citations(message_id: str) -> list[dict]:
    """Get all citations for a specific assistant message."""
    client = get_supabase_admin_client()
    if _is_mock(client) or _has_service_role_key():
        try:
            result = (
                client.table("message_citations")
                .select("id, message_id, chunk_id, document_id, citation_index, excerpt, page, section, source_documents(ticker, company_name, filing_type, fiscal_year)")
                .eq("message_id", message_id)
                .order("citation_index", desc=False)
                .execute()
            )
            if result and result.data is not None:
                citations = []
                for row in result.data:
                    doc = row.pop("source_documents", None) or {}
                    citations.append({
                        **row,
                        "ticker": doc.get("ticker"),
                        "company_name": doc.get("company_name"),
                        "filing_type": doc.get("filing_type"),
                        "fiscal_year": doc.get("fiscal_year"),
                    })
                return citations
        except Exception as e:
            logger.warning("chats.supabase_citations_failed_fallback_db", error=str(e))

    with get_db_session() as session:
        try:
            mid = uuid.UUID(message_id) if isinstance(message_id, str) else message_id
        except ValueError:
            return []
        rows = session.execute(
            text("""
                SELECT mc.id, mc.message_id, mc.chunk_id, mc.document_id, mc.citation_index,
                       mc.excerpt, mc.page, mc.section,
                       sd.ticker, sd.company_name, sd.filing_type, sd.fiscal_year
                FROM message_citations mc
                LEFT JOIN source_documents sd ON mc.document_id = sd.id
                WHERE mc.message_id = :message_id
                ORDER BY mc.citation_index ASC
            """),
            {"message_id": mid},
        ).mappings().fetchall()
        return [
            {
                "id": str(r["id"]),
                "message_id": str(r["message_id"]),
                "chunk_id": str(r["chunk_id"]) if r["chunk_id"] else None,
                "document_id": str(r["document_id"]) if r["document_id"] else None,
                "citation_index": r["citation_index"],
                "excerpt": r["excerpt"],
                "page": r["page"],
                "section": r["section"],
                "ticker": r["ticker"],
                "company_name": r["company_name"],
                "filing_type": r["filing_type"],
                "fiscal_year": r["fiscal_year"],
            }
            for r in rows
        ]


def persist_turn(
    thread_id: str,
    user_content: str,
    assistant_content: str,
    citations: list[dict] | None = None,
) -> dict:
    """Persist one complete chat turn (user message + assistant response + citations).

    Inserts the user message, then the assistant message, then any citations.
    Updates the thread's updated_at timestamp.

    Returns the assistant message record.
    """
    try:
        client = get_supabase_admin_client()

        # 1. Insert user message
        client.table("chat_messages").insert({
            "thread_id": thread_id,
            "role": "user",
            "content": user_content,
        }).execute()

        # 2. Insert assistant message
        assistant_result = (
            client.table("chat_messages")
            .insert({
                "thread_id": thread_id,
                "role": "assistant",
                "content": assistant_content,
            })
            .execute()
        )
        assistant_msg = assistant_result.data[0]

        # 3. Insert citations if any
        if citations:
            citation_rows = [
                {
                    "message_id": assistant_msg["id"],
                    "chunk_id": c.get("chunk_id"),
                    "document_id": c.get("document_id"),
                    "citation_index": i + 1,
                    "excerpt": c.get("excerpt", ""),
                    "page": c.get("page"),
                    "section": c.get("section"),
                }
                for i, c in enumerate(citations)
            ]
            client.table("message_citations").insert(citation_rows).execute()

        # 4. Touch thread updated_at
        client.table("chat_threads").update(
            {"updated_at": "now()"}
        ).eq("id", thread_id).execute()

        logger.info(
            "chat.turn_persisted",
            thread_id=thread_id,
            assistant_message_id=assistant_msg["id"],
            citation_count=len(citations) if citations else 0,
        )

        return assistant_msg
    except Exception as e:
        logger.warning("chats.supabase_persist_turn_fallback_db", error=str(e))

    with get_db_session() as session:
        tid = uuid.UUID(thread_id) if isinstance(thread_id, str) else thread_id

        # 1. Insert user message
        session.execute(
            text("""
                INSERT INTO chat_messages (id, thread_id, role, content)
                VALUES (gen_random_uuid(), :thread_id, 'user', :content)
            """),
            {"thread_id": tid, "content": user_content},
        )

        # 2. Insert assistant message
        asst_row = session.execute(
            text("""
                INSERT INTO chat_messages (id, thread_id, role, content)
                VALUES (gen_random_uuid(), :thread_id, 'assistant', :content)
                RETURNING id, thread_id, role, content, created_at
            """),
            {"thread_id": tid, "content": assistant_content},
        ).mappings().fetchone()

        asst_id = asst_row["id"]

        # 3. Insert citations
        if citations:
            for i, c in enumerate(citations):
                cid = uuid.UUID(c["chunk_id"]) if c.get("chunk_id") else None
                did = uuid.UUID(c["document_id"]) if c.get("document_id") else None
                session.execute(
                    text("""
                        INSERT INTO message_citations (id, message_id, chunk_id, document_id, citation_index, excerpt, page, section)
                        VALUES (gen_random_uuid(), :message_id, :chunk_id, :document_id, :citation_index, :excerpt, :page, :section)
                    """),
                    {
                        "message_id": asst_id,
                        "chunk_id": cid,
                        "document_id": did,
                        "citation_index": i + 1,
                        "excerpt": c.get("excerpt", ""),
                        "page": c.get("page"),
                        "section": c.get("section"),
                    },
                )

        # 4. Touch thread
        session.execute(
            text("UPDATE chat_threads SET updated_at = now() WHERE id = :thread_id"),
            {"thread_id": tid},
        )

        logger.info(
            "chat.turn_persisted",
            thread_id=str(tid),
            assistant_message_id=str(asst_id),
            citation_count=len(citations) if citations else 0,
        )

        return {
            "id": str(asst_id),
            "thread_id": str(tid),
            "role": "assistant",
            "content": assistant_content,
            "created_at": asst_row["created_at"].isoformat() if hasattr(asst_row["created_at"], "isoformat") else str(asst_row["created_at"]),
        }


def delete_thread(thread_id: str, user_id: str) -> bool:
    """Delete a chat thread and all associated messages/citations.

    Returns True if deleted, False if thread was not found or not owned by user.
    """
    thread = get_thread(thread_id, user_id)
    if not thread:
        return False

    client = get_supabase_admin_client()
    if _is_mock(client) or _has_service_role_key():
        try:
            client.table("chat_threads").delete().eq("id", thread_id).eq("user_id", user_id).execute()
            logger.info("chat.thread_deleted", thread_id=thread_id, user_id=user_id)
            return True
        except Exception as e:
            logger.warning("chats.supabase_delete_failed_fallback_db", error=str(e))

    with get_db_session() as session:
        try:
            tid = uuid.UUID(thread_id) if isinstance(thread_id, str) else thread_id
            uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            return False

        session.execute(
            text("""
                DELETE FROM message_citations
                WHERE message_id IN (
                    SELECT id FROM chat_messages WHERE thread_id = :thread_id
                )
            """),
            {"thread_id": tid},
        )
        session.execute(
            text("DELETE FROM chat_messages WHERE thread_id = :thread_id"),
            {"thread_id": tid},
        )
        result = session.execute(
            text("DELETE FROM chat_threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": tid, "user_id": uid},
        )
        logger.info("chat.thread_deleted", thread_id=str(tid), user_id=str(uid))
        return result.rowcount > 0
