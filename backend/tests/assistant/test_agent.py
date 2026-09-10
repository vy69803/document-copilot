"""Tests for Document Copilot assistant agent, tools, and factory."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel

from app.assistant.agent import (
    get_document_agent,
    read_chunk,
    read_chunks,
    read_surrounding_chunks,
    search_filings,
)
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage


def test_get_document_agent():
    """Verify get_document_agent returns an Agent instance configured with GroundedAnswer and tools."""
    agent = get_document_agent()
    assert agent is not None
    assert agent.output_type == GroundedAnswer

    # Check tools are registered on the agent
    tool_names = list(agent._function_toolset.tools.keys())
    assert "search_filings" in tool_names
    assert "read_chunk" in tool_names
    assert "read_chunks" in tool_names
    assert "read_surrounding_chunks" in tool_names


@pytest.mark.asyncio
async def test_search_filings_tool():
    """Test search_filings tool delegates to retriever and tracks retrieved passages in deps."""
    mock_passage = SourcePassage(
        chunk_id="chunk-123",
        document_id="doc-456",
        chunk_text="Apple services revenue grew to 96B in fiscal 2024.",
        section="Item 7",
        page=35,
        ticker="AAPL",
        fiscal_year=2024,
        filing_type="10-K",
    )

    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[mock_passage])

    deps = DocumentAgentDeps(
        user_id="user-1",
        thread_id="thread-1",
        retriever=mock_retriever,
        retrieved_passages=[],
    )

    ctx = RunContext(deps=deps, model=TestModel(), usage=MagicMock(), prompt="test")

    results = await search_filings(ctx, query="Apple services revenue", ticker="AAPL")

    assert len(results) == 1
    assert results[0]["chunk_id"] == "chunk-123"
    assert results[0]["ticker"] == "AAPL"
    mock_retriever.retrieve.assert_awaited_once_with(query="Apple services revenue", ticker="AAPL")

    # Verify newly retrieved passage was tracked into ctx.deps.retrieved_passages
    assert len(deps.retrieved_passages) == 1
    assert deps.retrieved_passages[0].chunk_id == "chunk-123"


@pytest.mark.asyncio
async def test_read_chunk_invalid_uuid():
    """Test read_chunk returns error dictionary for invalid UUID string."""
    deps = DocumentAgentDeps(
        user_id="user-1",
        thread_id="thread-1",
        retrieved_passages=[],
    )
    ctx = RunContext(deps=deps, model=TestModel(), usage=MagicMock(), prompt="test")
    res = await read_chunk(ctx, "not-a-valid-uuid")
    assert "error" in res
    assert "Invalid chunk UUID format" in res["error"]


@pytest.mark.asyncio
async def test_read_chunks_batch():
    """Test read_chunks calls read_chunk for multiple IDs."""
    deps = DocumentAgentDeps(
        user_id="user-1",
        thread_id="thread-1",
        retrieved_passages=[],
    )
    ctx = RunContext(deps=deps, model=TestModel(), usage=MagicMock(), prompt="test")
    results = await read_chunks(ctx, ["invalid-1", "invalid-2"])
    assert len(results) == 2
    assert all("error" in r for r in results)


@pytest.mark.asyncio
async def test_read_surrounding_chunks_invalid_uuid():
    """Test read_surrounding_chunks handles invalid UUID input."""
    deps = DocumentAgentDeps(
        user_id="user-1",
        thread_id="thread-1",
        retrieved_passages=[],
    )
    ctx = RunContext(deps=deps, model=TestModel(), usage=MagicMock(), prompt="test")
    res = await read_surrounding_chunks(ctx, "invalid-uuid")
    assert len(res) == 1
    assert "error" in res[0]


@pytest.mark.asyncio
async def test_agent_run_with_test_model():
    """Test running an Agent with TestModel producing typed GroundedAnswer."""
    expected_answer = "Apple total revenue was $391B in FY 2024."
    test_model = TestModel(
        custom_output_args={
            "answer": expected_answer,
            "citations": [
                {
                    "chunk_id": "chunk-123",
                    "document_id": "doc-456",
                    "excerpt": "Total net sales were $391,035 million in 2024",
                    "ticker": "AAPL",
                    "fiscal_year": 2024,
                    "filing_type": "10-K",
                    "section": "Item 7",
                    "page": 32,
                }
            ],
        }
    )

    from pydantic_ai import Agent

    agent = Agent(
        test_model,
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
    )

    deps = DocumentAgentDeps(
        user_id="test-user",
        thread_id="test-thread",
    )

    result = await agent.run("What was Apple's revenue in 2024?", deps=deps)

    assert isinstance(result.output, GroundedAnswer)
    assert result.output.answer == expected_answer
    assert len(result.output.citations) == 1
    citation = result.output.citations[0]
    assert isinstance(citation, Citation)
    assert citation.ticker == "AAPL"
    assert citation.fiscal_year == 2024
