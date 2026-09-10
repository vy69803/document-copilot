# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "sqlalchemy",
#     "psycopg[binary]",
#     "pydantic",
#     "pydantic-settings",
#     "structlog",
# ]
# ///
"""Load converted Markdown SEC filings into Supabase source_documents table."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database.documents import upsert_source_document

DATA_DIR = REPO_ROOT / "data"
MARKDOWN_DIR = DATA_DIR / "markdown"
MANIFEST_PATH = MARKDOWN_DIR / "manifest.json"

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}


def load_source_documents():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Markdown manifest not found at {MANIFEST_PATH}")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    filings = manifest.get("filings", [])
    total = len(filings)
    print(f"Starting ingestion of {total} filings into Supabase source_documents table...\n")

    inserted_count = 0

    for idx, filing in enumerate(filings, start=1):
        ticker = filing["ticker"]
        company_name = COMPANY_NAMES.get(ticker, f"{ticker} Inc.")
        accession_number = filing["accession_number"]
        filing_date = filing["filing_date"]
        fiscal_year = int(filing.get("year", filing_date[:4]))
        filing_type = filing.get("form", "10-K")
        source_url = filing.get("source_url")

        local_path_str = filing.get("local_path", "")
        normalized_path = Path(local_path_str.replace("\\", "/"))
        md_file_path = MARKDOWN_DIR / normalized_path

        if not md_file_path.exists():
            print(f"[{idx:02d}/{total:02d}] WARNING: Markdown file not found: {md_file_path}. Skipping.")
            continue

        content_markdown = md_file_path.read_text(encoding="utf-8")

        metadata = {
            "cik": filing.get("cik"),
            "report_date": filing.get("report_date"),
            "primary_document": filing.get("primary_document"),
            "markdown_bytes": len(content_markdown.encode("utf-8")),
            "local_path": local_path_str,
        }

        doc_payload = {
            "ticker": ticker,
            "company_name": company_name,
            "filing_type": filing_type,
            "fiscal_year": fiscal_year,
            "filing_date": filing_date,
            "accession_number": accession_number,
            "source_url": source_url,
            "content_markdown": content_markdown,
            "metadata": metadata,
        }

        size_kb = len(content_markdown.encode("utf-8")) / 1024
        print(f"[{idx:02d}/{total:02d}] Upserting {ticker} ({fiscal_year}) [{accession_number}] ({size_kb:.1f} KB)...")
        try:
            res = upsert_source_document(doc_payload)
            print(f"       ✓ Upserted successfully (id: {res.get('id')})")
            inserted_count += 1
        except Exception as e:
            print(f"       ✗ Failed to upsert: {e}")

    print(f"\n========================================================")
    print(f"Source documents ingestion complete: {inserted_count}/{total} documents in database.")
    print(f"========================================================")


if __name__ == "__main__":
    load_source_documents()
