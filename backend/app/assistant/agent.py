"""PydanticAI agent for grounded SEC filing analysis.

Provides bounded retrieval tools (search_filings, read_chunk, read_chunks,
read_surrounding_chunks) and outputs structured GroundedAnswer with citations.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from sqlalchemy import select

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer, SourcePassage
from app.config import settings
from app.database.models.document_chunk import DocumentChunk
from app.database.models.source_document import SourceDocument
from app.database.session import get_db_session
from app.retrieval.retriever import HybridRetriever

# Load system instructions from instructions.md
_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"
_SYSTEM_PROMPT = _INSTRUCTIONS_PATH.read_text(encoding="utf-8")
INSTRUCTIONS = _SYSTEM_PROMPT


# ─── Bounded Retrieval Tools ──────────────────────────────────────────────────


async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    ticker: str | None = None,
) -> list[dict[str, Any]]:
    """Search SEC filings using hybrid retrieval (pgvector semantic + lexical FTS + RRF).

    Args:
        ctx: Agent runtime context containing dependencies.
        query: Search keywords or question regarding SEC filings.
        ticker: Optional company ticker filter (e.g. 'AAPL', 'AMZN', 'MSFT', 'NVDA').
    """
    retriever = getattr(ctx.deps, "retriever", None) or HybridRetriever()
    passages = await retriever.retrieve(query=query, ticker=ticker)

    # Track newly retrieved passages in deps for grounding validation
    for p in passages:
        if not any(rp.chunk_id == p.chunk_id for rp in ctx.deps.retrieved_passages):
            ctx.deps.retrieved_passages.append(p)

    return [
        {
            "chunk_id": p.chunk_id,
            "document_id": p.document_id,
            "ticker": p.ticker,
            "fiscal_year": p.fiscal_year,
            "filing_type": p.filing_type,
            "section": p.section,
            "page": p.page,
            "chunk_text": p.chunk_text,
        }
        for p in passages
    ]


async def read_chunk(
    ctx: RunContext[DocumentAgentDeps],
    chunk_id: str,
) -> dict[str, Any]:
    """Read full text and metadata for a specific SEC filing chunk by chunk ID.

    Args:
        ctx: Agent runtime context.
        chunk_id: UUID of the chunk to inspect.
    """
    def _fetch():
        with get_db_session() as session:
            try:
                uid = uuid.UUID(chunk_id)
            except ValueError:
                return {"error": f"Invalid chunk UUID format: {chunk_id}"}

            stmt = (
                select(DocumentChunk, SourceDocument)
                .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
                .where(DocumentChunk.id == uid)
            )
            row = session.execute(stmt).first()
            if not row:
                return {"error": f"Chunk not found: {chunk_id}"}
            chunk, doc = row
            return {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "ticker": doc.ticker,
                "company_name": doc.company_name,
                "fiscal_year": doc.fiscal_year,
                "filing_type": doc.filing_type,
                "section": chunk.section,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
            }

    data = await asyncio.to_thread(_fetch)
    if "error" not in data and not any(rp.chunk_id == data["chunk_id"] for rp in ctx.deps.retrieved_passages):
        ctx.deps.retrieved_passages.append(
            SourcePassage(
                chunk_id=data["chunk_id"],
                document_id=data["document_id"],
                chunk_text=data["chunk_text"],
                section=data.get("section"),
                page=data.get("page"),
                ticker=data.get("ticker"),
                fiscal_year=data.get("fiscal_year"),
                filing_type=data.get("filing_type"),
            )
        )
    return data


async def read_chunks(
    ctx: RunContext[DocumentAgentDeps],
    chunk_ids: list[str],
) -> list[dict[str, Any]]:
    """Read full text and metadata for multiple SEC filing chunks by their chunk IDs.

    Args:
        ctx: Agent runtime context.
        chunk_ids: List of chunk UUIDs to fetch.
    """
    results = []
    for cid in chunk_ids:
        chunk_data = await read_chunk(ctx, cid)
        results.append(chunk_data)
    return results


async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps],
    chunk_id: str,
    window: int = 1,
) -> list[dict[str, Any]]:
    """Read neighboring chunks before and after a given chunk in the same filing.

    Useful for reading adjacent paragraphs or tables in context.

    Args:
        ctx: Agent runtime context.
        chunk_id: Anchor chunk UUID.
        window: Number of neighboring chunks to retrieve before and after (default 1).
    """
    def _fetch():
        with get_db_session() as session:
            try:
                uid = uuid.UUID(chunk_id)
            except ValueError:
                return [{"error": f"Invalid chunk UUID format: {chunk_id}"}]
            target = session.get(DocumentChunk, uid)
            if not target:
                return [{"error": f"Anchor chunk not found: {chunk_id}"}]

            stmt = (
                select(DocumentChunk, SourceDocument)
                .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
                .where(
                    DocumentChunk.document_id == target.document_id,
                    DocumentChunk.chunk_index.between(
                        target.chunk_index - window, target.chunk_index + window
                    ),
                )
                .order_by(DocumentChunk.chunk_index.asc())
            )
            rows = session.execute(stmt).all()
            return [
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "ticker": doc.ticker,
                    "company_name": doc.company_name,
                    "fiscal_year": doc.fiscal_year,
                    "filing_type": doc.filing_type,
                    "section": chunk.section,
                    "page": chunk.page,
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text,
                }
                for chunk, doc in rows
            ]

    chunks_data = await asyncio.to_thread(_fetch)
    for data in chunks_data:
        if "error" not in data and not any(rp.chunk_id == data["chunk_id"] for rp in ctx.deps.retrieved_passages):
            ctx.deps.retrieved_passages.append(
                SourcePassage(
                    chunk_id=data["chunk_id"],
                    document_id=data["document_id"],
                    chunk_text=data["chunk_text"],
                    section=data.get("section"),
                    page=data.get("page"),
                    ticker=data.get("ticker"),
                    fiscal_year=data.get("fiscal_year"),
                    filing_type=data.get("filing_type"),
                )
            )
    return chunks_data


# ─── Context Prompt Injection ─────────────────────────────────────────────────


async def add_context(ctx: RunContext[DocumentAgentDeps]) -> str:
    """Inject retrieved passages into the system prompt as grounding context."""
    if not ctx.deps.retrieved_passages:
        return (
            "\n\n## Retrieved Passages\n\n"
            "No passages were retrieved from the corpus yet. "
            "You may use the `search_filings` tool to search for relevant passages."
        )

    lines = ["\n\n## Retrieved Passages\n"]
    for i, p in enumerate(ctx.deps.retrieved_passages, 1):
        header = f"### Passage {i}"
        if p.ticker:
            header += f" — {p.ticker}"
        if p.fiscal_year:
            header += f" {p.fiscal_year}"
        if p.filing_type:
            header += f" {p.filing_type}"
        if p.section:
            header += f", {p.section}"

        lines.append(header)
        lines.append(f"**Chunk ID:** `{p.chunk_id}`")
        lines.append(f"**Document ID:** `{p.document_id}`")
        if p.page:
            lines.append(f"**Page:** {p.page}")
        lines.append(f"\n{p.chunk_text}\n")

    return "\n".join(lines)


# ─── Agent Factory & Singleton ────────────────────────────────────────────────


_document_agent: Agent[DocumentAgentDeps, GroundedAnswer] | None = None


def get_document_agent(
    model: Any = None,
) -> Agent[DocumentAgentDeps, GroundedAnswer]:
    """Factory returning the Document Copilot assistant agent with retrieval tools."""
    global _document_agent
    if _document_agent is None:
        if model is None:
            if settings.openai_api_key:
                from pydantic_ai.models.openai import OpenAIChatModel
                from pydantic_ai.providers.openai import OpenAIProvider

                model = OpenAIChatModel(
                    settings.openai_chat_model,
                    provider=OpenAIProvider(api_key=settings.openai_api_key),
                )
            else:
                model = f"google:{settings.llm_model}"

        _document_agent = Agent(
            model,
            deps_type=DocumentAgentDeps,
            output_type=GroundedAnswer,
            instructions=INSTRUCTIONS,
            tools=[search_filings, read_chunks, read_chunk, read_surrounding_chunks],
            retries=2,
            model_settings={"temperature": settings.agent_temperature},
        )
        _document_agent.system_prompt(add_context)

    return _document_agent


document_agent = get_document_agent()
