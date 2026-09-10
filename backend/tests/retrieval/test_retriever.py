"""Unit tests for HybridRetriever with mocked database queries."""

from unittest.mock import MagicMock, patch

import pytest

from app.assistant.outputs import SourcePassage
from app.retrieval.retriever import HybridRetriever


@pytest.mark.asyncio
async def test_hybrid_retriever_empty_query():
    retriever = HybridRetriever(embedder=MagicMock())
    result = await retriever.retrieve("   ")
    assert result == []


@pytest.mark.asyncio
async def test_hybrid_retriever_pipeline():
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 768

    dense_candidates = [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "chunk_text": "Apple generated revenue from iPhone and Services in 2024.",
            "section": "Item 7 MD&A",
            "page": 24,
            "ticker": "AAPL",
            "fiscal_year": 2024,
            "filing_type": "10-K",
        },
        {
            "chunk_id": "chunk-2",
            "document_id": "doc-1",
            "chunk_text": "Mac and iPad revenue trends in fiscal 2024.",
            "section": "Item 7 MD&A",
            "page": 25,
            "ticker": "AAPL",
            "fiscal_year": 2024,
            "filing_type": "10-K",
        },
    ]

    lexical_candidates = [
        {
            "chunk_id": "chunk-2",
            "document_id": "doc-1",
            "chunk_text": "Mac and iPad revenue trends in fiscal 2024.",
            "section": "Item 7 MD&A",
            "page": 25,
            "ticker": "AAPL",
            "fiscal_year": 2024,
            "filing_type": "10-K",
        },
        {
            "chunk_id": "chunk-3",
            "document_id": "doc-2",
            "chunk_text": "Microsoft Azure cloud revenue commentary.",
            "section": "Item 7",
            "page": 30,
            "ticker": "MSFT",
            "fiscal_year": 2024,
            "filing_type": "10-K",
        },
    ]

    with (
        patch("app.retrieval.retriever.search_dense", return_value=dense_candidates) as mock_dense,
        patch("app.retrieval.retriever.search_lexical", return_value=lexical_candidates) as mock_lexical,
    ):
        retriever = HybridRetriever(embedder=mock_embedder)
        results = await retriever.retrieve(
            query="Apple iPhone revenue 2024",
            top_k=2,
            ticker="AAPL",
            fiscal_year=2024,
        )

        assert len(results) == 2
        assert all(isinstance(p, SourcePassage) for p in results)

        # chunk-2 appears in both dense (#2) and lexical (#1), so it should rank first after RRF
        assert results[0].chunk_id == "chunk-2"
        assert results[0].ticker == "AAPL"
        assert results[0].fiscal_year == 2024

        # chunk-1 is in dense (#1) only, so ranks next
        assert results[1].chunk_id == "chunk-1"

        mock_dense.assert_called_once()
        mock_lexical.assert_called_once()
