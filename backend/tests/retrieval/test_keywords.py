"""Unit tests for keyword extraction utility (app.retrieval.keywords)."""

from app.retrieval.keywords import extract_search_keywords


def test_empty_query():
    assert extract_search_keywords("") == ""
    assert extract_search_keywords("   ") == ""


def test_conversational_question_filters_fillers():
    query = "What were the primary revenue drivers and financial performance highlights for Apple in 2024?"
    keywords = extract_search_keywords(query)
    
    # Fillers like 'what', 'were', 'the', 'primary', 'drivers', 'highlights' must be excluded
    assert "what" not in keywords.lower()
    assert "primary" not in keywords.lower()
    assert "drivers" not in keywords.lower()
    assert "highlights" not in keywords.lower()

    # Core high-signal terms must be present
    assert "AAPL" in keywords
    assert "2024" in keywords
    assert "revenue" in keywords.lower()


def test_company_to_ticker_mapping():
    # Apple -> AAPL, Amazon -> AMZN, Microsoft -> MSFT, Nvidia -> NVDA
    assert "AAPL" in extract_search_keywords("Apple total net sales")
    assert "AMZN" in extract_search_keywords("Amazon AWS cloud revenue")
    assert "MSFT" in extract_search_keywords("Microsoft intelligent cloud")
    assert "NVDA" in extract_search_keywords("Nvidia data center chips")


def test_known_phrase_protection_and_quoting():
    query = "What are the major risk factors regarding supply chain disruptions and component shortages?"
    keywords = extract_search_keywords(query)

    # Multi-word phrases should be preserved in quotes for websearch phrase matching
    assert '"supply chain"' in keywords
    assert '"risk factors"' in keywords or '"component shortages"' in keywords
    # Filler word 'regarding' must be excluded
    assert "regarding" not in keywords.lower()


def test_research_and_development_phrase():
    query = "How much did Apple spend on research and development expenses during fiscal year 2024?"
    keywords = extract_search_keywords(query)

    assert '"research and development"' in keywords
    assert "AAPL" in keywords
    assert "2024" in keywords
    assert "spend" not in keywords.lower()


def test_max_terms_limit():
    query = "Apple Amazon Microsoft Nvidia Google total revenue net income operating margin cash flow 2024"
    keywords = extract_search_keywords(query, max_terms=4)
    terms = keywords.split()
    # Should not exceed maximum specified terms (allowing for multi-word quotes)
    assert len(terms) <= 8


def test_pure_stopword_fallback():
    # If all tokens are conversational or stopwords, should gracefully fallback rather than error
    result = extract_search_keywords("could you please tell me about this")
    assert isinstance(result, str)
    assert len(result) > 0
