"""Hybrid retriever combining pgvector dense search, Postgres full-text search, and RRF."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.assistant.outputs import SourcePassage
from app.config import settings
from app.ingest.embedder import GeminiEmbedder
from app.retrieval.fusion import DEFAULT_RRF_K, reciprocal_rank_fusion
from app.retrieval.keywords import extract_search_keywords
from app.retrieval.queries import get_chunks_by_ids, search_dense, search_lexical

logger = structlog.get_logger(__name__)


class HybridRetriever:
    """Hybrid search pipeline combining semantic vector search and full-text keyword search."""

    def __init__(
        self,
        embedder: GeminiEmbedder | None = None,
        rrf_k: int = DEFAULT_RRF_K,
    ):
        self.embedder = embedder or GeminiEmbedder()
        self.rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        candidate_k: int | None = None,
        ticker: str | None = None,
        fiscal_year: int | None = None,
        filing_type: str | None = None,
        lexical_query: str | None = None,
    ) -> list[SourcePassage]:
        """Execute hybrid search pipeline: embed → parallel search → RRF fuse → SourcePassages."""
        clean_query = query.strip()
        if not clean_query:
            return []

        effective_top_k = top_k if top_k is not None else settings.retrieval_top_k
        effective_candidate_k = candidate_k if candidate_k is not None else settings.retrieval_candidate_k

        # 1. Extract focused 2-3 keyword terms for lexical search (avoiding tsquery conjunction drops)
        effective_lexical_query = (
            lexical_query.strip()
            if lexical_query and lexical_query.strip()
            else extract_search_keywords(clean_query, min_terms=2, max_terms=3)
        )

        logger.info(
            "retrieval.start",
            query=clean_query[:100],
            lexical_query=effective_lexical_query,
            top_k=effective_top_k,
            candidate_k=effective_candidate_k,
            ticker=ticker,
            fiscal_year=fiscal_year,
        )

        # 2. Embed full natural query with Gemini embedder (run in worker thread)
        query_vector = await asyncio.to_thread(self.embedder.embed_text, clean_query)

        # 3. Run dense vector search and lexical FTS concurrently
        dense_task = asyncio.to_thread(
            search_dense,
            query_vector=query_vector,
            limit=effective_candidate_k,
            ticker=ticker,
            fiscal_year=fiscal_year,
            filing_type=filing_type,
        )
        lexical_task = asyncio.to_thread(
            search_lexical,
            query_text=effective_lexical_query or clean_query,
            limit=effective_candidate_k,
            ticker=ticker,
            fiscal_year=fiscal_year,
            filing_type=filing_type,
        )

        dense_results, lexical_results = await asyncio.gather(dense_task, lexical_task)

        # 3. Build candidate lookup map
        candidates_by_id: dict[str, dict[str, Any]] = {}
        for r in dense_results:
            candidates_by_id[r["chunk_id"]] = r
        for r in lexical_results:
            if r["chunk_id"] not in candidates_by_id:
                candidates_by_id[r["chunk_id"]] = r

        # 4. Extract ranked ID lists for RRF
        dense_ids = [r["chunk_id"] for r in dense_results]
        lexical_ids = [r["chunk_id"] for r in lexical_results]

        # 5. Fuse rankings with Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion([dense_ids, lexical_ids], k=self.rrf_k)
        top_fused = fused[:effective_top_k]

        logger.info(
            "retrieval.fused",
            dense_count=len(dense_ids),
            lexical_count=len(lexical_ids),
            fused_total=len(fused),
            selected=len(top_fused),
        )

        # 6. Any missing chunk metadata? Fetch if necessary
        missing_ids = [cid for cid, _ in top_fused if cid not in candidates_by_id]
        if missing_ids:
            fetched = await asyncio.to_thread(get_chunks_by_ids, missing_ids)
            for chunk in fetched:
                candidates_by_id[chunk["chunk_id"]] = chunk

        # 7. Construct SourcePassage models
        passages: list[SourcePassage] = []
        for chunk_id, score in top_fused:
            chunk = candidates_by_id.get(chunk_id)
            if not chunk:
                continue

            passages.append(
                SourcePassage(
                    chunk_id=chunk["chunk_id"],
                    document_id=chunk["document_id"],
                    chunk_text=chunk["chunk_text"],
                    section=chunk.get("section"),
                    page=chunk.get("page"),
                    ticker=chunk.get("ticker"),
                    fiscal_year=chunk.get("fiscal_year"),
                    filing_type=chunk.get("filing_type"),
                )
            )

        return passages
