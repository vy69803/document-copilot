"""Smoke test script for hybrid retrieval pipeline.

Performs an end-to-end query against the live database and embedding API:
1. Embeds query text with GeminiEmbedder.
2. Runs pgvector dense similarity search and Postgres full-text search concurrently.
3. Merges and ranks results using Reciprocal Rank Fusion (RRF).
4. Prints the retrieved SourcePassage results to stdout.

Usage:
    uv run python scripts/smoke_retrieval.py
    uv run python scripts/smoke_retrieval.py --query "iPhone revenue growth" --ticker AAPL --year 2024
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path and set as current working directory so .env is always found
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app.assistant.outputs import SourcePassage
from app.config import settings
from app.retrieval.retriever import HybridRetriever


async def run_smoke_test(
    query: str,
    ticker: str | None = None,
    fiscal_year: int | None = None,
    filing_type: str | None = None,
    top_k: int | None = None,
    candidate_k: int | None = None,
) -> list[SourcePassage]:
    effective_top_k = top_k if top_k is not None else settings.retrieval_top_k
    effective_candidate_k = candidate_k if candidate_k is not None else settings.retrieval_candidate_k

    print("=" * 80)
    print("RETRIEVAL PIPELINE SMOKE TEST")
    print("=" * 80)
    print(f"Query:        {query}")
    print(f"Ticker:       {ticker or 'All'}")
    print(f"Fiscal Year:  {fiscal_year or 'All'}")
    print(f"Filing Type:  {filing_type or 'All'}")
    print(f"Top K:        {effective_top_k}")
    print(f"Candidate K:  {effective_candidate_k}")
    print("-" * 80)

    retriever = HybridRetriever()

    start_time = time.perf_counter()
    try:
        passages = await retriever.retrieve(
            query=query,
            top_k=effective_top_k,
            candidate_k=effective_candidate_k,
            ticker=ticker,
            fiscal_year=fiscal_year,
            filing_type=filing_type,
        )
    except Exception as exc:
        print(f"\n[ERROR] Retrieval failed: {exc}")
        print("\nTroubleshooting tips:")
        print("  1. Verify backend/.env has valid SUPABASE_URL and DATABASE_URL.")
        print("  2. Verify GEMINI_API_KEY (or OPENAI_API_KEY) is configured.")
        print("  3. Ensure documents and chunks have been ingested into the database.")
        sys.exit(1)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(f"\nCompleted in {elapsed_ms:.1f}ms — Retrieved {len(passages)} passages:\n")

    if not passages:
        print("No matching passages found. (Are documents/chunks loaded in the database?)")
        return []

    for idx, passage in enumerate(passages, start=1):
        print(f"--- [Passage {idx}/{len(passages)}] ---")
        print(f"Chunk ID:     {passage.chunk_id}")
        print(f"Document ID:  {passage.document_id}")
        print(f"Metadata:     {passage.ticker or 'N/A'} | FY{passage.fiscal_year or 'N/A'} | {passage.filing_type or 'N/A'}")
        print(f"Location:     Section: '{passage.section or 'N/A'}' | Page: {passage.page or 'N/A'}")
        
        # Display preview of text (first 300 characters)
        preview = passage.chunk_text.strip().replace("\n", " ")
        if len(preview) > 300:
            preview = preview[:300] + "..."
        print(f"Text Snippet: {preview}\n")

    print("=" * 80)
    print("SMOKE TEST SUCCESSFUL")
    print("=" * 80)
    return passages


def smoke(
    query: str = "What were the primary revenue drivers and financial performance highlights?",
    ticker: str | None = None,
    fiscal_year: int | None = None,
    filing_type: str | None = None,
    top_k: int | None = None,
    candidate_k: int | None = None,
) -> list[SourcePassage]:
    """Synchronous helper for interactive REPL sessions (no await or asyncio.run required)."""
    return asyncio.run(
        run_smoke_test(
            query=query,
            ticker=ticker,
            fiscal_year=fiscal_year,
            filing_type=filing_type,
            top_k=top_k,
            candidate_k=candidate_k,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test for Document Copilot hybrid retrieval.")
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="What were the primary revenue drivers and financial performance highlights?",
        help="Search query text",
    )
    parser.add_argument(
        "--ticker",
        "-t",
        type=str,
        default=None,
        help="Optional company ticker filter (e.g. AAPL, MSFT, NVDA)",
    )
    parser.add_argument(
        "--year",
        "-y",
        type=int,
        default=None,
        help="Optional fiscal year filter (e.g. 2024)",
    )
    parser.add_argument(
        "--filing-type",
        "-f",
        type=str,
        default=None,
        help="Optional filing type filter (e.g. 10-K, 10-Q)",
    )
    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=settings.retrieval_top_k,
        help=f"Number of final fused passages to return (default: {settings.retrieval_top_k})",
    )
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=settings.retrieval_candidate_k,
        help=f"Number of candidates to fetch per search branch before RRF (default: {settings.retrieval_candidate_k})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        run_smoke_test(
            query=args.query,
            ticker=args.ticker,
            fiscal_year=args.year,
            filing_type=args.filing_type,
            top_k=args.top_k,
            candidate_k=args.candidate_k,
        )
    )


if __name__ == "__main__":
    main()

