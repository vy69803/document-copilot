"""Grounding and citation validator for assistant responses.

Verifies that all citations and inline references correspond to actual retrieved
source passages and that cited excerpts are grounded in the chunk text.
"""

from __future__ import annotations

import re
from typing import NamedTuple

import structlog

from app.assistant.outputs import Citation, SourcePassage

logger = structlog.get_logger(__name__)

# Matches inline SEC citations such as:
# [AAPL 2024 10-K, Item 7]
# [MSFT 2023 10-K, Item 1A]
# [AMZN 2022 10-K, Financial Statements]
# [NVDA 2025 10-K, p. 45]
INLINE_CITATION_PATTERN = re.compile(
    r"\[([A-Z]{1,5})\s+(\d{4})\s+([0-9A-Z\-]+)(?:,\s*([^\]]+))?\]",
    re.IGNORECASE,
)


class GroundingResult(NamedTuple):
    """Result of validating answer citations against retrieved passages."""

    is_grounded: bool
    citations: list[Citation]
    issues: list[str]


class GroundingValidator:
    """Validates citations against retrieved passages and extracts inline citation tags."""

    @staticmethod
    def extract_inline_citations(
        text: str,
        retrieved_passages: list[SourcePassage],
    ) -> list[Citation]:
        """Extract inline citation markers from text and match them to retrieved passages."""
        if not text or not retrieved_passages:
            return []

        extracted: list[Citation] = []
        seen_chunks: set[str] = set()

        matches = INLINE_CITATION_PATTERN.finditer(text)
        for match in matches:
            ticker = match.group(1).upper()
            year_str = match.group(2)
            fiscal_year = int(year_str) if year_str else None
            filing_type = match.group(3).upper() if match.group(3) else "10-K"
            section_or_page = match.group(4).strip() if match.group(4) else None

            # Find matching passage from retrieved passages
            matched_passage = None
            for p in retrieved_passages:
                ticker_match = not p.ticker or p.ticker.upper() == ticker
                year_match = not p.fiscal_year or p.fiscal_year == fiscal_year
                if ticker_match and year_match:
                    if section_or_page and p.section and section_or_page.lower() in p.section.lower():
                        matched_passage = p
                        break
                    elif not matched_passage:
                        matched_passage = p

            if matched_passage and matched_passage.chunk_id not in seen_chunks:
                seen_chunks.add(matched_passage.chunk_id)
                extracted.append(
                    Citation(
                        chunk_id=matched_passage.chunk_id,
                        document_id=matched_passage.document_id,
                        excerpt=matched_passage.chunk_text[:300],
                        section=matched_passage.section,
                        page=matched_passage.page,
                        ticker=matched_passage.ticker,
                        fiscal_year=matched_passage.fiscal_year,
                        filing_type=matched_passage.filing_type or filing_type,
                    )
                )

        return extracted

    @classmethod
    def validate(
        cls,
        answer_text: str,
        citations: list[Citation] | None,
        retrieved_passages: list[SourcePassage],
    ) -> GroundingResult:
        """Validate that all provided citations are grounded in retrieved passages.

        If `citations` is empty, attempts to infer citations from inline tags in `answer_text`.
        """
        issues: list[str] = []
        valid_citations: list[Citation] = []
        passages_by_id = {p.chunk_id: p for p in retrieved_passages}

        candidate_citations = citations or []

        # If no structured citations were provided, extract from markdown text
        if not candidate_citations:
            candidate_citations = cls.extract_inline_citations(answer_text, retrieved_passages)

        for cit in candidate_citations:
            passage = passages_by_id.get(cit.chunk_id)
            if not passage:
                issue = f"Citation references unknown chunk_id: {cit.chunk_id}"
                issues.append(issue)
                logger.warning("grounding.unknown_chunk", chunk_id=cit.chunk_id)
                continue

            # Check excerpt validity if provided
            if cit.excerpt and len(cit.excerpt.strip()) > 10:
                clean_excerpt = cit.excerpt.strip().lower()
                clean_passage = passage.chunk_text.lower()
                # Check for direct substring or high token overlap
                if clean_excerpt not in clean_passage:
                    excerpt_words = set(clean_excerpt.split())
                    passage_words = set(clean_passage.split())
                    overlap = len(excerpt_words & passage_words) / max(1, len(excerpt_words))
                    if overlap < 0.4:
                        issues.append(
                            f"Citation excerpt has low overlap ({overlap:.1%}) with chunk {cit.chunk_id}"
                        )
                        logger.warning(
                            "grounding.low_excerpt_overlap",
                            chunk_id=cit.chunk_id,
                            overlap=overlap,
                        )

            # Ensure document metadata is enriched from verified passage
            enriched_citation = Citation(
                chunk_id=passage.chunk_id,
                document_id=passage.document_id,
                excerpt=cit.excerpt or passage.chunk_text[:300],
                section=cit.section or passage.section,
                page=cit.page or passage.page,
                ticker=cit.ticker or passage.ticker,
                fiscal_year=cit.fiscal_year or passage.fiscal_year,
                filing_type=cit.filing_type or passage.filing_type,
            )
            valid_citations.append(enriched_citation)

        is_grounded = len(issues) == 0 and (len(valid_citations) > 0 or not retrieved_passages)

        return GroundingResult(
            is_grounded=is_grounded,
            citations=valid_citations,
            issues=issues,
        )
