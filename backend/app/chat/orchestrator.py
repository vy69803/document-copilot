"""Chat turn orchestrator — coordinates retrieval, agent, persistence, and streaming.

This is the single entry point for processing one user message.
The flow is:

    1. Verify thread ownership & load history
    2. Retrieve relevant passages via HybridRetriever (pgvector + Postgres FTS + RRF)
    3. Run the PydanticAI agent with streaming
    4. Collect full response and validate grounding & citations
    5. Emit structured citation events to client
    6. Persist turn (user message + assistant message + citations)
"""

import asyncio
from collections.abc import AsyncIterator

import structlog
from pydantic_ai import UsageLimits

from app.assistant.agent import document_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import SourcePassage
from app.chat.streaming import (
    data_event,
    error_event,
    finish_event,
    status_event,
    text_delta_event,
)
from app.config import settings
from app.database import chats
from app.grounding.validator import GroundingValidator
from app.retrieval.retriever import HybridRetriever

logger = structlog.get_logger(__name__)

# Module-level retriever instance
retriever = HybridRetriever()


async def run_chat_turn(
    *,
    user_id: str,
    thread_id: str,
    user_message: str,
) -> AsyncIterator[str]:
    """Execute one chat turn and yield AI SDK-compatible SSE events.

    This is an async generator — the caller wraps it in a StreamingResponse.
    """
    # 1. Verify thread ownership (fail fast before performing retrieval)
    thread = await asyncio.to_thread(chats.get_thread, thread_id, user_id)
    if not thread:
        yield error_event("Thread not found or access denied")
        return

    # Notify frontend: searching stage
    yield status_event("searching", "Searching SEC filings (pgvector + FTS)...")

    # 2 & 3. Load message history and retrieve relevant passages concurrently
    async def _safe_retrieve() -> list[SourcePassage]:
        try:
            return await retriever.retrieve(query=user_message)
        except Exception as e:
            logger.error("chat.retrieval_error", error=str(e), thread_id=thread_id)
            return []

    history, retrieved_passages = await asyncio.gather(
        asyncio.to_thread(chats.get_thread_messages, thread_id, user_id),
        _safe_retrieve(),
    )

    history_dicts = [
        {"role": m["role"], "content": m["content"]}
        for m in history
    ]

    # 4. Build agent dependencies
    deps = DocumentAgentDeps(
        user_id=user_id,
        thread_id=thread_id,
        message_history=history_dicts,
        retrieved_passages=retrieved_passages,
    )

    # Notify frontend: analyzing / generating stage
    passage_count = len(retrieved_passages)
    if passage_count > 0:
        yield status_event("analyzing", f"Analyzing {passage_count} retrieved SEC passages...")
    else:
        yield status_event("analyzing", "No direct filing passages found. Reviewing corpus boundaries...")

    # 5. Build the message list for the agent (history + new user message)
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        TextPart,
        UserPromptPart,
    )

    messages = []
    for m in history_dicts:
        if m["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=m["content"])]))
        elif m["role"] == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=m["content"])]))

    # 6. Run agent with streaming
    full_response = ""
    model_citations = []
    try:
        usage_limits = UsageLimits(request_limit=settings.agent_request_limit)
        async with document_agent.run_stream(
            user_message,
            deps=deps,
            message_history=messages,
            usage_limits=usage_limits,
        ) as stream:
            if hasattr(stream, "stream_output") and getattr(document_agent, "output_type", None) not in (str, None):
                prev_len = 0
                async for partial in stream.stream_output():
                    curr_answer = getattr(partial, "answer", "")
                    if len(curr_answer) > prev_len:
                        delta = curr_answer[prev_len:]
                        prev_len = len(curr_answer)
                        full_response += delta
                        yield text_delta_event(delta)
                final_output = await stream.get_output()
                model_citations = getattr(final_output, "citations", [])
            else:
                async for chunk in stream.stream_text(delta=True):
                    if chunk:
                        full_response += chunk
                        yield text_delta_event(chunk)

    except Exception as e:
        logger.error("chat.agent_error", error=str(e), thread_id=thread_id)
        yield error_event(f"An error occurred while generating the response: {e}")
        return

    # 7. Validate grounding and extract structured citations
    yield status_event("validating", "Validating citations and grounding against filings...")
    grounding_result = GroundingValidator.validate(
        answer_text=full_response,
        citations=model_citations or None,
        retrieved_passages=deps.retrieved_passages,
    )

    citations_payload = [c.model_dump() for c in grounding_result.citations]

    # Emit data event with citations for frontend SourceDrawer & Badges
    if citations_payload:
        yield data_event(citations_payload)

    yield status_event("complete", "Answer verified and complete")
    yield finish_event()

    # 8. Persist the turn after successful generation (offloaded to thread)
    try:
        await asyncio.to_thread(
            chats.persist_turn,
            thread_id=thread_id,
            user_content=user_message,
            assistant_content=full_response,
            citations=citations_payload if citations_payload else None,
        )
    except Exception as e:
        logger.error("chat.persist_error", error=str(e), thread_id=thread_id)
        # Don't fail the response — the user already saw the streamed answer
