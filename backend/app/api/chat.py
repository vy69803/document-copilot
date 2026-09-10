"""Chat API endpoints — thread management and streaming."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.chat.orchestrator import run_chat_turn
from app.database import chats

router = APIRouter(prefix="/chat", tags=["chat"])


# ─── Request / Response schemas ───────────────────────────────────────


class CreateThreadRequest(BaseModel):
    title: str = "New Research Chat"


class StreamRequest(BaseModel):
    thread_id: str
    message: str


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class CitationResponse(BaseModel):
    id: str | None = None
    citation_index: int = 1
    ticker: str | None = None
    company_name: str | None = None
    filing_type: str | None = None
    fiscal_year: int | None = None
    section: str | None = None
    page: int | None = None
    excerpt: str = ""
    chunk_id: str | None = None
    document_id: str | None = None


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    citations: list[CitationResponse] = []
    created_at: str


# ─── Thread endpoints ─────────────────────────────────────────────────


@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(user: AuthenticatedUser = Depends(get_current_user)):
    """List all chat threads for the authenticated user."""
    return chats.list_threads(user.id)


@router.post("/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(
    body: CreateThreadRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new chat thread."""
    return chats.create_thread(user.id, body.title)


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def get_thread_messages(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get all messages for a thread. Returns 404 if thread doesn't exist or isn't owned by user."""
    thread = chats.get_thread(thread_id, user.id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return chats.get_thread_messages(thread_id, user.id)


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a chat thread and all its messages. Returns 404 if not found or not owned."""
    deleted = chats.delete_thread(thread_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return None


# ─── Streaming endpoint ──────────────────────────────────────────────


@router.post("/stream")
async def stream_chat(
    body: StreamRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Stream a chat response as AI SDK-compatible SSE events.

    The frontend's useChat() hook sends messages here and receives
    incremental text deltas + a finish event.
    """
    return StreamingResponse(
        run_chat_turn(
            user_id=user.id,
            thread_id=body.thread_id,
            user_message=body.message,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
