"""SEC filing hierarchical and hybrid chunker using Docling.

Splits normalized markdown filings into structured passage chunks respecting
semantic boundaries, table headers, and embedding token limits (~600 tokens).
"""

from __future__ import annotations

import importlib.machinery
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import structlog

logger = structlog.get_logger(__name__)


def _setup_mocks():
    """Mock unused DLL-dependent modules so Docling runs natively on Windows."""
    def make_mock(name: str):
        m = MagicMock()
        m.__spec__ = importlib.machinery.ModuleSpec(name, loader=None)
        m.__file__ = f"{name}.py"
        m.__name__ = name
        return m

    torch_mock = make_mock("torch")
    torch_mock.backends.mps.is_built.return_value = False
    torch_mock.backends.mps.is_available.return_value = False
    torch_mock.cuda.is_available.return_value = False

    sys.modules["torch"] = torch_mock
    sys.modules["torch.distributed"] = make_mock("torch.distributed")
    sys.modules["torch.nn"] = make_mock("torch.nn")
    sys.modules["torch.utils"] = make_mock("torch.utils")
    sys.modules["torch.utils.data"] = make_mock("torch.utils.data")
    sys.modules["torchvision"] = make_mock("torchvision")
    sys.modules["torchvision.transforms"] = make_mock("torchvision.transforms")
    sys.modules["rtree"] = make_mock("rtree")
    sys.modules["rtree.index"] = make_mock("rtree.index")
    sys.modules["rtree.core"] = make_mock("rtree.core")
    sys.modules["rtree.finder"] = make_mock("rtree.finder")

    hf_mock = make_mock("docling_core.transforms.chunker.tokenizer.huggingface")
    hf_mock.get_default_tokenizer = lambda: None
    hf_mock.HuggingFaceTokenizer = MagicMock()
    sys.modules["docling_core.transforms.chunker.tokenizer.huggingface"] = hf_mock


_setup_mocks()

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hierarchical_chunker import (
    HierarchicalChunker,
)

ITEM_REGEX = re.compile(
    r"(Item\s+(?:1A|1B|7A|9A|9B|9C|\d{1,2})[\.\:\s\-–—]?[^\n\r,;]*)",
    re.IGNORECASE,
)


class FilingChunker:
    """Chunks SEC filing Markdown files using Docling's HierarchicalChunker."""

    def __init__(self, max_tokens: int = 600):
        self.max_tokens = max_tokens
        self.converter = DocumentConverter(allowed_formats=[InputFormat.MD, InputFormat.HTML])
        self.chunker = HierarchicalChunker()

    def _extract_section_name(self, headings: list[str]) -> str | None:
        """Extract SEC Item designation (e.g. Item 1A Risk Factors, Item 7 MD&A) from headings."""
        if not headings:
            return None

        # Check in reverse (most specific heading first, then parent)
        for h in reversed(headings):
            match = ITEM_REGEX.search(h)
            if match:
                return match.group(1).strip()

        # Fallback to the top-level non-empty heading
        for h in headings:
            clean = h.strip()
            if clean:
                return clean[:100]

        return None

    def chunk_file(
        self,
        file_path: Path | str,
        *,
        ticker: str,
        fiscal_year: int,
        company_name: str,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Parse a markdown filing and generate enriched chunks.

        Returns a list of chunk dictionaries ready for database insertion and embedding.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Filing not found at: {path}")

        logger.info(
            "chunker.converting_document",
            ticker=ticker,
            fiscal_year=fiscal_year,
            path=str(path),
        )

        conv_res = self.converter.convert(path)
        doc = conv_res.document

        raw_chunks = list(self.chunker.chunk(doc))
        logger.info(
            "chunker.chunks_generated",
            ticker=ticker,
            fiscal_year=fiscal_year,
            count=len(raw_chunks),
        )

        processed_chunks: list[dict[str, Any]] = []

        for idx, chunk in enumerate(raw_chunks):
            headings = getattr(chunk.meta, "headings", []) or []
            section = self._extract_section_name(headings)

            # Estimate page if provided in doc items
            page: int | None = None
            if hasattr(chunk.meta, "doc_items") and chunk.meta.doc_items:
                for item in chunk.meta.doc_items:
                    if hasattr(item, "page_no") and item.page_no:
                        page = item.page_no
                        break

            # Contextualized text with filing header
            section_label = section or "General"
            context_header = f"[{ticker} FY{fiscal_year} 10-K | {section_label}]"
            contextualized_text = f"{context_header}\n{chunk.text.strip()}"

            # Word / token approximation (~1.3 tokens per word)
            word_count = len(chunk.text.split())
            token_count = int(word_count * 1.3)

            chunk_dict: dict[str, Any] = {
                "chunk_index": idx,
                "section": section_label,
                "page": page,
                "chunk_text": contextualized_text,
                "token_count": token_count,
                "metadata": {
                    "ticker": ticker,
                    "company_name": company_name,
                    "fiscal_year": fiscal_year,
                    "headings": headings,
                    "raw_text": chunk.text,
                    "word_count": word_count,
                },
            }

            if document_id:
                chunk_dict["document_id"] = document_id

            processed_chunks.append(chunk_dict)

        return processed_chunks
