# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "docling",
# ]
# ///
"""Convert downloaded SEC 10-K HTML filings to Markdown using Docling.

Maintains the exact folder structure (by fiscal year) and generates
an updated manifest in data/markdown/manifest.json.
"""

from __future__ import annotations

import argparse
import importlib.machinery
import json
import sys
import time
import types
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

# Ensure UTF-8 stdout for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def _setup_mocks():
    """Mock unused DLL-dependent modules so Docling HTML converter runs natively on Windows."""
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
    sys.modules["torch.nn"] = make_mock("torch.nn")
    sys.modules["torch.utils"] = make_mock("torch.utils")
    sys.modules["torch.utils.data"] = make_mock("torch.utils.data")
    sys.modules["torchvision"] = make_mock("torchvision")
    sys.modules["torchvision.transforms"] = make_mock("torchvision.transforms")
    sys.modules["rtree"] = make_mock("rtree")
    sys.modules["rtree.index"] = make_mock("rtree.index")
    sys.modules["rtree.core"] = make_mock("rtree.core")


_setup_mocks()

from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.document_converter import DocumentConverter  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = DATA_DIR / "downloads"
MARKDOWN_DIR = DATA_DIR / "markdown"


def convert_all_filings(force: bool = False) -> dict:
    manifest_path = DOWNLOADS_DIR / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Downloads manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        downloads_manifest = json.load(f)

    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    print("Initializing Docling DocumentConverter (HTML pipeline)...")
    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])

    markdown_manifest = {
        "source": downloads_manifest.get("source", "SEC EDGAR"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "form": downloads_manifest.get("form", "10-K"),
        "converter": "docling",
        "converted_count": 0,
        "filings": [],
    }

    filings = downloads_manifest.get("filings", [])
    total_filings = len(filings)
    print(f"Found {total_filings} filings to process in {DOWNLOADS_DIR}\n")

    start_total_time = time.time()

    for idx, filing in enumerate(filings, start=1):
        local_path_str = filing.get("local_path", "")
        normalized_local_path = Path(local_path_str.replace("\\", "/"))
        source_file = DOWNLOADS_DIR / normalized_local_path

        if not source_file.exists():
            print(f"[{idx:02d}/{total_filings:02d}] WARNING: File not found: {source_file}. Skipping.")
            continue

        year = normalized_local_path.parent.name or filing.get("filing_date", "")[:4]
        ticker = filing.get("ticker", "UNKNOWN")
        stem = source_file.stem
        target_year_dir = MARKDOWN_DIR / year
        target_year_dir.mkdir(parents=True, exist_ok=True)

        target_md_file = target_year_dir / f"{stem}.md"
        relative_md_path = f"{year}/{stem}.md"

        if target_md_file.exists() and not force:
            print(f"[{idx:02d}/{total_filings:02d}] Skipped (already exists): {ticker} {year} -> {relative_md_path}")
            markdown_manifest["filings"].append({
                **filing,
                "local_path": relative_md_path,
                "converted_at": datetime.now(UTC).isoformat(),
                "markdown_bytes": target_md_file.stat().st_size,
            })
            markdown_manifest["converted_count"] += 1
            continue

        print(f"[{idx:02d}/{total_filings:02d}] Converting {ticker} ({year}) [{source_file.name}]...")
        t0 = time.time()

        try:
            conv_result = converter.convert(source_file)
            md_content = conv_result.document.export_to_markdown()

            target_md_file.write_text(md_content, encoding="utf-8")
            elapsed = time.time() - t0
            size_kb = len(md_content.encode("utf-8")) / 1024

            print(
                f"       ✓ Converted in {elapsed:.1f}s | Output size: {size_kb:.1f} KB -> {relative_md_path}"
            )

            markdown_manifest["filings"].append({
                **filing,
                "local_path": relative_md_path,
                "converted_at": datetime.now(UTC).isoformat(),
                "markdown_bytes": len(md_content.encode("utf-8")),
            })
            markdown_manifest["converted_count"] += 1

        except Exception as err:
            print(f"       ✗ ERROR converting {source_file.name}: {err}")

    # Write target manifest
    output_manifest_path = MARKDOWN_DIR / "manifest.json"
    output_manifest_path.write_text(
        json.dumps(markdown_manifest, indent=2) + "\n", encoding="utf-8"
    )

    total_elapsed = time.time() - start_total_time
    print(f"\n========================================================")
    print(f"Conversion complete!")
    print(f"Processed: {markdown_manifest['converted_count']}/{total_filings} filings")
    print(f"Total elapsed time: {total_elapsed / 60:.2f} minutes")
    print(f"Manifest written to: {output_manifest_path}")
    print(f"========================================================")

    return markdown_manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert SEC HTML filings to Markdown using Docling")
    parser.add_argument("--force", action="store_true", help="Force re-conversion of existing markdown files")
    args = parser.parse_args()

    convert_all_filings(force=args.force)
