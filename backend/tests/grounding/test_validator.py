"""Unit tests for GroundingValidator."""

from app.assistant.outputs import Citation, SourcePassage
from app.grounding.validator import GroundingValidator


def test_validator_with_explicit_valid_citations():
    passages = [
        SourcePassage(
            chunk_id="chunk-100",
            document_id="doc-10",
            chunk_text="In fiscal 2024, iPhone net sales increased 4% compared to fiscal 2023.",
            section="Item 7 MD&A",
            page=32,
            ticker="AAPL",
            fiscal_year=2024,
            filing_type="10-K",
        )
    ]

    citations = [
        Citation(
            chunk_id="chunk-100",
            document_id="doc-10",
            excerpt="iPhone net sales increased 4%",
            section="Item 7 MD&A",
            page=32,
            ticker="AAPL",
            fiscal_year=2024,
        )
    ]

    result = GroundingValidator.validate(
        answer_text="Apple iPhone revenue grew 4% [AAPL 2024 10-K, Item 7].",
        citations=citations,
        retrieved_passages=passages,
    )

    assert result.is_grounded is True
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "chunk-100"
    assert result.citations[0].ticker == "AAPL"
    assert len(result.issues) == 0


def test_validator_extracts_inline_citations_automatically():
    passages = [
        SourcePassage(
            chunk_id="chunk-nvda-1",
            document_id="doc-nvda",
            chunk_text="Compute & Networking revenue increased by 217% to $78.0 billion.",
            section="Item 7 MD&A",
            page=45,
            ticker="NVDA",
            fiscal_year=2024,
            filing_type="10-K",
        )
    ]

    answer = "NVIDIA's Data Center growth was driven by Compute & Networking [NVDA 2024 10-K, Item 7]."

    # Pass citations=None to test automatic extraction from markdown tags
    result = GroundingValidator.validate(
        answer_text=answer,
        citations=None,
        retrieved_passages=passages,
    )

    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "chunk-nvda-1"
    assert result.citations[0].ticker == "NVDA"
    assert result.citations[0].fiscal_year == 2024
    assert result.is_grounded is True


def test_validator_flags_hallucinated_chunk_id():
    passages = [
        SourcePassage(
            chunk_id="real-chunk-1",
            document_id="real-doc-1",
            chunk_text="Legitimate source text.",
            ticker="MSFT",
            fiscal_year=2023,
        )
    ]

    hallucinated_citation = Citation(
        chunk_id="fake-chunk-999",
        document_id="fake-doc-999",
        excerpt="Fabricated claim.",
        ticker="MSFT",
    )

    result = GroundingValidator.validate(
        answer_text="Fabricated claim.",
        citations=[hallucinated_citation],
        retrieved_passages=passages,
    )

    assert result.is_grounded is False
    assert len(result.citations) == 0
    assert len(result.issues) == 1
    assert "fake-chunk-999" in result.issues[0]
