"""Keyword extraction utility for lexical full-text search (Postgres FTS).

Conversational queries (e.g., 'What were Amazon's key revenue drivers, and how did AWS
cloud segment perform in fiscal year 2024?') contain filler words and conversational phrasing.
Postgres `plainto_tsquery` joins all tokens with AND (&), causing conversational queries
to fail or return 0 results if even one word is missing from a document chunk.

This module extracts the 3 to 5 most salient keyword terms (entities, metrics, years,
and domain nouns) for effective lexical search.
"""

from __future__ import annotations

import re

# Standard English stopwords to filter out
STOPWORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "me", "more", "most", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "she", "should", "shouldn't", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "were", "weren't", "what", "when",
    "where", "which", "while", "who", "whom", "why", "with", "won't", "would",
    "wouldn't", "you", "your", "yours", "yourself", "yourselves",
})

# Conversational boilerplate and filler words common in RAG questions
FILLER_WORDS: frozenset[str] = frozenset({
    "tell", "explain", "describe", "detail", "details", "compare", "give", "find",
    "show", "please", "can", "could", "would", "how", "what", "which", "where",
    "key", "primary", "main", "major", "drivers", "driver", "perform", "performance",
    "performed", "company", "companies", "fiscal", "year", "years", "much", "many",
    "total", "overview", "breakdown", "trend", "trends", "commentary", "highlights",
    "regarding", "related", "relate", "faces", "facing", "invest", "investment", "investments",
    "spend", "spending", "spent", "summarize", "summary", "about", "discuss", "discussion",
    "see", "know", "think", "report", "reported", "reports", "say", "says", "said",
})

# Known company name to ticker mappings (chunk headers use tickers like [AAPL FY2024 10-K])
COMPANY_TICKERS: dict[str, str] = {
    "apple": "AAPL",
    "amazon": "AMZN",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "alphabet": "GOOGL",
    "google": "GOOGL",
}

# Core financial metrics that have high ranking value
FINANCIAL_METRICS: frozenset[str] = frozenset({
    "revenue", "revenues", "sales", "income", "profit", "margin", "margins",
    "operating", "capex", "expenses", "expense", "cash", "debt", "guidance",
    "growth", "segment", "segments", "backlog", "commitments", "headcount",
    "earnings", "ebitda", "dividend", "dividends",
})

# Multi-word financial & tech phrases to preserve as compound/quoted tokens
KNOWN_PHRASES: tuple[str, ...] = (
    "research and development",
    "supply chain",
    "net sales",
    "operating income",
    "operating margin",
    "operating expenses",
    "net income",
    "cash flow",
    "free cash flow",
    "balance sheet",
    "capital expenditures",
    "risk factors",
    "component shortages",
    "intelligent cloud",
    "data center",
    "cloud segment",
    "disaggregated revenue",
    "foreign exchange",
    "space tourism",
    "supplier concentration",
)

YEAR_PATTERN = re.compile(r"\b(201\d|202\d|203\d)\b")
WORD_PATTERN = re.compile(r"[A-Za-z0-9\-_]+")


def extract_search_keywords(
    query: str,
    *,
    min_terms: int = 2,
    max_terms: int = 3,
) -> str:
    """Extract 2 to 3 high-salience search terms from a conversational user query.

    Args:
        query: Natural language query string.
        min_terms: Minimum number of terms to return (if available).
        max_terms: Maximum number of terms to return.

    Returns:
        Space-separated string of extracted keywords suitable for Postgres FTS.
    """
    clean_query = query.strip()
    if not clean_query:
        return ""

    matched_phrases: list[str] = []
    working_text = clean_query

    # 1. Extract and protect multi-word domain phrases
    for phrase in KNOWN_PHRASES:
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        match = pattern.search(working_text)
        if match:
            # Wrap in quotes for websearch_to_tsquery phrase matching
            matched_phrases.append(f'"{phrase}"')
            # Remove phrase from working text so its individual words aren't re-added
            working_text = pattern.sub(" ", working_text)

    # 2. Strip possessive suffixes (e.g. Amazon's -> Amazon, Apple's -> Apple)
    working_text = re.sub(r"['’]s\b", "", working_text)

    # 3. Extract words
    raw_tokens = WORD_PATTERN.findall(working_text)
    cleaned_tokens: list[str] = [tok for tok in raw_tokens if len(tok) > 1]

    # 4. Categorize and score candidate terms
    # Higher score = higher priority for keyword inclusion
    candidates: list[tuple[str, int, int]] = []  # (term, score, original_index)

    # Add matched multi-word phrases first (highest priority score 4)
    for idx, phrase in enumerate(matched_phrases):
        candidates.append((phrase, 4, idx))

    curr_idx = len(matched_phrases)
    seen_lower = {p.strip('"').lower() for p in matched_phrases}

    for tok in cleaned_tokens:
        tok_lower = tok.lower()
        if tok_lower in seen_lower:
            continue
        seen_lower.add(tok_lower)

        # Company to ticker mapping (e.g. Apple -> AAPL, Amazon -> AMZN)
        if tok_lower in COMPANY_TICKERS:
            ticker = COMPANY_TICKERS[tok_lower]
            candidates.append((ticker, 4, curr_idx))
            curr_idx += 1
            continue

        # Fiscal year (e.g., 2024) -> score 3
        if YEAR_PATTERN.fullmatch(tok):
            candidates.append((tok, 3, curr_idx))
            curr_idx += 1
            continue

        # Skip pure stopwords
        if tok_lower in STOPWORDS:
            continue

        # Tickers, acronyms, capitalized brand entities, or camelCase (e.g., AWS, AAPL, Azure, NVIDIA, iPhone)
        has_camel_case = bool(re.search(r"[a-z][A-Z]", tok))
        is_entity = (tok.isupper() or tok[0].isupper() or has_camel_case) and tok_lower not in FILLER_WORDS
        if is_entity:
            candidates.append((tok, 3, curr_idx))
            curr_idx += 1
            continue

        # Core financial metrics (revenue, margin, sales, etc.) -> score 2
        if tok_lower in FINANCIAL_METRICS:
            candidates.append((tok, 2, curr_idx))
            curr_idx += 1
            continue

        # Other non-filler nouns/terms -> score 1
        if tok_lower not in FILLER_WORDS:
            candidates.append((tok, 1, curr_idx))
            curr_idx += 1

    # If we didn't get enough candidates, fallback to including non-stop words even if in FILLER_WORDS
    if len(candidates) < min_terms:
        for tok in cleaned_tokens:
            tok_lower = tok.lower()
            if tok_lower not in seen_lower and tok_lower not in STOPWORDS:
                seen_lower.add(tok_lower)
                candidates.append((tok, 0, curr_idx))
                curr_idx += 1

    if not candidates:
        return clean_query

    # Sort by score descending, then by original appearance order
    candidates.sort(key=lambda x: (-x[1], x[2]))

    # Pick top terms up to max_terms, then restore original order for natural reading
    top_candidates = candidates[:max_terms]
    top_candidates.sort(key=lambda x: x[2])

    return " ".join(term for term, _, _ in top_candidates)

