"""SSE streaming helpers for AI SDK-compatible events.

Emits events in the format expected by the Vercel AI SDK's useChat() hook
on the frontend. Each event is a Server-Sent Event (SSE) line.
"""

import json
from collections.abc import AsyncIterator


def _sse_event(event: str, data: dict | str) -> str:
    """Format a single SSE event line."""
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


def text_delta_event(text: str) -> str:
    """AI SDK text-stream event for incremental text."""
    # AI SDK data stream protocol: type 0 = text delta
    return f"0:{json.dumps(text)}\n"


def finish_event(
    finish_reason: str = "stop",
    usage: dict | None = None,
) -> str:
    """AI SDK finish event marking end of generation."""
    data = {
        "finishReason": finish_reason,
        "usage": usage or {"promptTokens": 0, "completionTokens": 0},
    }
    # AI SDK data stream protocol: type e = finish
    return f"e:{json.dumps(data)}\n"


def error_event(message: str) -> str:
    """AI SDK error event."""
    # AI SDK data stream protocol: type 3 = error
    return f"3:{json.dumps(message)}\n"


def data_event(data: list[dict]) -> str:
    """AI SDK data event for structured metadata (e.g. citations)."""
    # AI SDK data stream protocol: type 2 = data
    return f"2:{json.dumps(data)}\n"


def status_event(stage: str, message: str) -> str:
    """AI SDK data event emitting pipeline progress updates (e.g. searching, analyzing, validating)."""
    # AI SDK data stream protocol: type 2 = data
    return f"2:{json.dumps([{'type': 'status', 'stage': stage, 'message': message}])}\n"


async def stream_text_deltas(
    text_stream: AsyncIterator[str],
) -> AsyncIterator[str]:
    """Wrap an async text stream into AI SDK-compatible SSE events.

    Yields text delta events followed by a finish event.
    """
    async for chunk in text_stream:
        if chunk:
            yield text_delta_event(chunk)

    yield finish_event()
