#!/usr/bin/env python3
"""
Test: Validate Azure Document Intelligence parsing to minimal staffing schema.

For each PDF under ./sows, this script:
- Runs prebuilt-layout via Azure Document Intelligence
- Parses detected tables using the same heuristics as the app
- Prints a matrix with the minimal schema (Name, Level, Title, Primary Role, Hours, Hours%)

Env required:
- AZURE_DOCINT_ENDPOINT
- AZURE_DOCINT_API_KEY
Optional:
- AZURE_DOCINT_API_VERSION (defaults to 2023-07-31)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import csv
from dotenv import load_dotenv


def _print_minimal_matrix(file_path: Path, minimal: List[Dict[str, Any]]):
    print("\n" + "=" * 80)
    print(f"File: {file_path.name}")
    print("-" * 80)
    headers = ["Name", "Level", "Title", "Primary Role", "Hours", "Hours %"]
    # Determine column widths
    col_widths = [len(h) for h in headers]
    for row in minimal:
        col_widths[0] = max(col_widths[0], len(str(row.get("name", "") or "")))
        col_widths[1] = max(col_widths[1], len(str(row.get("level", "") or "")))
        col_widths[2] = max(col_widths[2], len(str(row.get("title", "") or "")))
        col_widths[3] = max(col_widths[3], len(str(row.get("primary_role", "") or "")))
        col_widths[4] = max(col_widths[4], len(str(row.get("hours", "") or "")))
        col_widths[5] = max(col_widths[5], len(str(row.get("hours_pct", "") or "")))

    def fmt_row(values: List[str]) -> str:
        return " | ".join(str(v).ljust(w) for v, w in zip(values, col_widths))

    # Print header
    print(fmt_row(headers))
    print("-" * (sum(col_widths) + 3 * (len(headers) - 1)))
    # Print rows
    if not minimal:
        print("(no entries)")
        return
    for row in minimal:
        values = [
            row.get("name", "") or "",
            row.get("level", "") or "",
            row.get("title", "") or "",
            row.get("primary_role", "") or "",
            "" if row.get("hours") is None else ("%s" % row.get("hours")),
            "" if row.get("hours_pct") is None else ("%s" % row.get("hours_pct")),
        ]
        print(fmt_row(values))


def main() -> int:
    load_dotenv()

    endpoint = os.getenv("AZURE_DOCINT_ENDPOINT")
    api_key = os.getenv("AZURE_DOCINT_API_KEY")
    if not endpoint or not api_key:
        print("❌ Missing AZURE_DOCINT_ENDPOINT or AZURE_DOCINT_API_KEY in environment")
        return 1

    # Make services importable
    services_dir = Path(__file__).parent / "streamlit_app" / "services"
    sys.path.append(str(services_dir))
    try:
        from document_intelligence_service import AzureDocumentIntelligenceService  # type: ignore
        from sow_extraction_service import SOWExtractionService  # type: ignore
    except Exception as e:
        print(f"❌ Failed to import services: {e}")
        return 1

    sows_dir = Path(__file__).parent / "sows"
    if not sows_dir.exists():
        print(f"❌ SOWs directory not found: {sows_dir}")
        return 1

    pdf_files = [p for p in sows_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    if not pdf_files:
        print("❌ No PDF files found in sows directory")
        return 1

    di_client = AzureDocumentIntelligenceService()
    parser = SOWExtractionService()

    # Prepare output directory for CSVs
    out_dir = Path(__file__).parent / "outputs" / "csv" / "docint_staffing_minimal"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 Validating Document Intelligence minimal schema extraction on PDFs\n")

    # Prepare combined CSV accumulator
    combined_headers = ["File", "Name", "Level", "Title", "Primary Role", "Hours", "Hours %"]
    combined_rows: List[List[str]] = []
    for i, fp in enumerate(sorted(pdf_files), 1):
        print(f"[{i}/{len(pdf_files)}] Analyzing {fp.name}...")
        try:
            analysis = di_client.analyze_layout(fp)
            tables = analysis.get("tables", [])
            all_entries: List[Dict[str, Any]] = []
            for t_idx, table in enumerate(tables, 1):
                matrix = table.to_matrix()
                if not matrix or len(matrix) < 2:
                    continue
                # Use the same parsing heuristics as the app
                entries = parser._parse_di_table_to_entries(matrix, page_number=table.page_number, table_index=t_idx)  # noqa: SLF001
                if entries:
                    all_entries.extend(entries)
            minimal = parser._to_minimal_staffing(all_entries)  # noqa: SLF001
            _print_minimal_matrix(fp, minimal)

            # Write CSV for review
            csv_path = out_dir / f"{fp.stem}_minimal.csv"
            headers = ["Name", "Level", "Title", "Primary Role", "Hours", "Hours %"]
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in minimal:
                    csv_row = [
                        row.get("name", "") or "",
                        row.get("level", "") or "",
                        row.get("title", "") or "",
                        row.get("primary_role", "") or "",
                        "" if row.get("hours") is None else row.get("hours"),
                        "" if row.get("hours_pct") is None else row.get("hours_pct"),
                    ]
                    writer.writerow(csv_row)
                    combined_rows.append([fp.name] + csv_row)
            print(f"  - CSV saved: {csv_path}")
        
        except Exception as e:
            print(f"  - Failed: {e}")

    # Write combined CSV
    combined_path = out_dir / "_combined_minimal.csv"
    with open(combined_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(combined_headers)
        for r in combined_rows:
            writer.writerow(r)
    print(f"\n📦 Combined CSV saved: {combined_path}")

    print("\n✅ Completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


