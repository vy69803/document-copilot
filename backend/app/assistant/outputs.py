"""Structured output models for the Document Copilot assistant agent.

These define the typed contract between the LLM and the rest of the system.
The agent must return a GroundedAnswer — anything else is a bug.
"""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single citation linking an answer claim to a source passage."""

    chunk_id: str = Field(description="UUID of the document_chunk this citation refers to")
    document_id: str = Field(description="UUID of the source_document")
    excerpt: str = Field(description="The exact passage text supporting the claim")
    section: str | None = Field(default=None, description="SEC filing section (e.g. 'Item 7 MD&A')")
    page: int | None = Field(default=None, description="Page number in the original filing")
    ticker: str | None = Field(default=None, description="Company ticker symbol")
    fiscal_year: int | None = Field(default=None, description="Fiscal year of the filing")
    filing_type: str | None = Field(default=None, description="Filing type (e.g. '10-K')")


class SourcePassage(BaseModel):
    """A retrieved chunk provided to the agent as context."""

    chunk_id: str
    document_id: str
    chunk_text: str
    section: str | None = None
    page: int | None = None
    ticker: str | None = None
    fiscal_year: int | None = None
    filing_type: str | None = None


class GroundedAnswer(BaseModel):
    """The agent's complete response: answer text + citations.

    Every factual claim in `answer` must have a corresponding Citation.
    If the corpus doesn't support an answer, `answer` should say so explicitly
    and `citations` should be empty.
    """

    answer: str = Field(description="The assistant's response text with inline citation markers")
    citations: list[Citation] = Field(default_factory=list, description="Citations grounding the answer")
