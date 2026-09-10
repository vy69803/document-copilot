"""Smoke test runner for the assistant agent and hybrid retrieval pipeline.

Supports:
- Single query execution with real-time streaming and rich stage logging.
- Parallel multi-query evaluation (using asyncio.gather) to test benchmarks concurrently.
- Interactive use in Jupyter notebooks or standard terminal REPL.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Ensure UTF-8 output on Windows (skip in Jupyter where stdout lacks reconfigure)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path and set as current working directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from pydantic_ai import UsageLimits

from app.assistant.agent import document_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation
from app.config import settings
from app.grounding.validator import GroundingResult, GroundingValidator
from app.retrieval.retriever import HybridRetriever

# ─── Query Dictionary ────────────────────────────────────────────────────────

QUERIES: dict[str, str] = {
    "amazon": "What were Amazon's key revenue drivers, and how did AWS cloud segment perform in fiscal year 2024?",
    "apple": "What were Apple's primary revenue drivers and how did iPhone and Services perform in fiscal year 2024?",
    "microsoft": "What were the primary drivers of Microsoft's revenue growth, especially in Intelligent Cloud and Azure?",
    "nvidia": "How much did NVIDIA's Data Center revenue grow in fiscal 2024 and what drove that growth?",
    "refusal": "What was the company's total revenue from commercial space tourism flights?",
}


@dataclass
class SmokeResult:
    """Result of running one smoke test query."""

    key: str
    query: str
    passages_count: int
    answer: str
    is_grounded: bool
    citations: list[Citation]
    issues: list[str]
    elapsed_seconds: float
    retrieval_seconds: float
    agent_seconds: float
    error: str | None = None


def _log(stage: str, message: str) -> None:
    """Format and flush a log message with a clean timestamp."""
    now = datetime.now(UTC).strftime("%H:%M:%S")
    print(f"[{now} UTC] [{stage:9s}] {message}", flush=True)


# ─── Single Runner Function ──────────────────────────────────────────────────


async def run_query(
    key: str = "amazon",
    *,
    stream_output: bool = True,
    retriever: HybridRetriever | None = None,
) -> SmokeResult:
    """Run retrieval, agent streaming, and grounding validation for a given query key.

    Args:
        key: Key from QUERIES dictionary, or a custom query string.
        stream_output: Whether to stream text chunks to stdout.
        retriever: Optional shared HybridRetriever instance.
    """
    query = QUERIES.get(key, key)
    total_start = time.perf_counter()

    if stream_output:
        print(f"\n{'='*75}\nQUERY [{key.upper()}]: {query}\n{'='*75}")

    # 1. Retrieve
    _log("RETRIEVE", f"Starting hybrid search (pgvector + FTS + RRF) for: '{query[:60]}...'")
    retriever_instance = retriever or HybridRetriever()

    retrieval_start = time.perf_counter()
    try:
        passages = await retriever_instance.retrieve(query=query)
        retrieval_time = time.perf_counter() - retrieval_start
        _log("RETRIEVE", f"Retrieved {len(passages)} passages in {retrieval_time:.2f}s")

        if stream_output and passages:
            for idx, p in enumerate(passages[:4], start=1):
                loc = f"{p.ticker or 'N/A'} FY{p.fiscal_year or 'N/A'} ({p.section or 'General'}, p.{p.page or 'N/A'})"
                print(f"       [{idx}] {loc} — chunk: {p.chunk_id[:8]}... ({len(p.chunk_text)} chars)")
            if len(passages) > 4:
                print(f"       ... and {len(passages) - 4} more passages")
    except Exception as exc:
        retrieval_time = time.perf_counter() - retrieval_start
        _log("ERROR", f"Retrieval failed: {exc}")
        return SmokeResult(
            key=key,
            query=query,
            passages_count=0,
            answer="",
            is_grounded=False,
            citations=[],
            issues=[str(exc)],
            elapsed_seconds=time.perf_counter() - total_start,
            retrieval_seconds=retrieval_time,
            agent_seconds=0.0,
            error=str(exc),
        )

    # 2. Agent Execution
    _log("AGENT", f"Prompting {settings.llm_model} with {len(passages)} grounding passages...")
    deps = DocumentAgentDeps(
        user_id="smoke-user",
        thread_id="smoke-thread",
        message_history=[],
        retrieved_passages=passages,
    )
    limits = UsageLimits(request_limit=settings.agent_request_limit)
    full_answer = ""
    agent_start = time.perf_counter()

    if stream_output:
        print(f"\nAssistant Response ({settings.llm_model}):\n" + "-" * 75)

    model_citations = []
    try:
        async with document_agent.run_stream(query, deps=deps, usage_limits=limits) as stream:
            if hasattr(stream, "stream_output") and getattr(document_agent, "output_type", None) not in (str, None):
                prev_len = 0
                async for partial in stream.stream_output():
                    curr_answer = getattr(partial, "answer", "")
                    if len(curr_answer) > prev_len:
                        delta = curr_answer[prev_len:]
                        prev_len = len(curr_answer)
                        if stream_output:
                            sys.stdout.write(delta)
                            sys.stdout.flush()
                        full_answer += delta
                final_output = await stream.get_output()
                model_citations = getattr(final_output, "citations", [])
            else:
                async for chunk in stream.stream_text(delta=True):
                    if stream_output:
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    full_answer += chunk

        agent_time = time.perf_counter() - agent_start
        if stream_output:
            print("\n" + "-" * 75)
        _log("AGENT", f"Response generated in {agent_time:.2f}s ({len(full_answer)} chars)")

    except Exception as exc:
        agent_time = time.perf_counter() - agent_start
        _log("ERROR", f"Agent generation failed: {exc}")
        return SmokeResult(
            key=key,
            query=query,
            passages_count=len(passages),
            answer=full_answer,
            is_grounded=False,
            citations=[],
            issues=[str(exc)],
            elapsed_seconds=time.perf_counter() - total_start,
            retrieval_seconds=retrieval_time,
            agent_seconds=agent_time,
            error=str(exc),
        )

    # 3. Grounding & Citation Validation
    _log("GROUNDING", "Validating response citations against retrieved passages...")
    validation_start = time.perf_counter()
    grounding: GroundingResult = GroundingValidator.validate(
        answer_text=full_answer,
        citations=model_citations or None,
        retrieved_passages=deps.retrieved_passages,
    )
    _log(
        "GROUNDING",
        f"Validation complete in {(time.perf_counter() - validation_start)*1000:.1f}ms — "
        f"Grounded: {grounding.is_grounded} | Citations: {len(grounding.citations)} | Issues: {len(grounding.issues)}",
    )

    if stream_output and grounding.citations:
        for i, c in enumerate(grounding.citations, 1):
            print(f"       [{i}] {c.ticker} {c.fiscal_year} ({c.section or 'General'}, p.{c.page or 'N/A'})")

    if grounding.issues:
        for issue in grounding.issues:
            _log("WARNING", f"Grounding issue: {issue}")

    total_time = time.perf_counter() - total_start
    if stream_output:
        print(f"Total turnaround time: {total_time:.2f}s\n")

    return SmokeResult(
        key=key,
        query=query,
        passages_count=len(passages),
        answer=full_answer,
        is_grounded=grounding.is_grounded,
        citations=grounding.citations,
        issues=grounding.issues,
        elapsed_seconds=total_time,
        retrieval_seconds=retrieval_time,
        agent_seconds=agent_time,
    )


# ─── Parallel Runner ─────────────────────────────────────────────────────────


async def run_checks_parallel(
    keys: list[str] | None = None,
    concurrency_limit: int = 5,
) -> list[SmokeResult]:
    """Execute multiple smoke test queries in parallel using asyncio.gather.

    Optimizes evaluation throughput by running concurrent retrieval and LLM API calls.
    """
    target_keys = keys or list(QUERIES.keys())
    print(f"\n{'='*75}\nRUNNING {len(target_keys)} SMOKE CHECKS IN PARALLEL (concurrency={concurrency_limit})\n{'='*75}")

    semaphore = asyncio.Semaphore(concurrency_limit)
    retriever = HybridRetriever()

    async def _bounded_run(k: str) -> SmokeResult:
        async with semaphore:
            _log("PARALLEL", f"Dispatched check: [{k}]")
            result = await run_query(k, stream_output=False, retriever=retriever)
            status = "✓ DONE" if not result.error else "✗ FAILED"
            _log("PARALLEL", f"{status} [{k}] in {result.elapsed_seconds:.2f}s (grounded={result.is_grounded})")
            return result

    start = time.perf_counter()
    results = await asyncio.gather(*[_bounded_run(k) for k in target_keys])
    total_duration = time.perf_counter() - start

    # Print summary comparison table
    print("\n" + "=" * 85)
    print(f"PARALLEL SMOKE CHECKS SUMMARY ({len(results)} queries in {total_duration:.2f}s)")
    print("=" * 85)
    print(f"{'KEY':<12} {'STATUS':<10} {'PASSAGES':<10} {'GROUNDED':<10} {'CITATIONS':<10} {'LATENCY':<10}")
    print("-" * 85)
    for r in results:
        status_str = "ERROR" if r.error else "OK"
        print(
            f"{r.key:<12} {status_str:<10} {r.passages_count:<10} "
            f"{r.is_grounded!s:<10} {len(r.citations):<10} {r.elapsed_seconds:.2f}s"
        )
    print("=" * 85 + "\n")

    return list(results)


# ─── Synchronous Helpers for Jupyter / REPL ──────────────────────────────────


def run(key: str = "amazon") -> str:
    """Synchronous helper for interactive REPL / Jupyter sessions: run('amazon') or run('apple')."""
    result = asyncio.run(run_query(key))
    return result.answer


def run_parallel(keys: list[str] | None = None) -> list[SmokeResult]:
    """Synchronous helper for running all or selected checks in parallel."""
    return asyncio.run(run_checks_parallel(keys))


# ─── CLI Entrypoint ──────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test runner for assistant agent.")
    parser.add_argument(
        "key",
        nargs="?",
        default="amazon",
        help="Query key from QUERIES (amazon, apple, microsoft, nvidia, refusal) or custom text",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Run all queries in parallel and display comparison summary",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.all:
        asyncio.run(run_checks_parallel())
    else:
        asyncio.run(run_query(args.key))

