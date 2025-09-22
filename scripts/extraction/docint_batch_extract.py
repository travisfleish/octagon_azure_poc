#!/usr/bin/env python3
"""
Batch extract tables from all SOWs using Azure Document Intelligence (prebuilt-layout).

Outputs:
- CSV files per detected table under outputs/csv/docint_tables/
"""

import os
import sys
import csv
from pathlib import Path
from typing import List
from dotenv import load_dotenv


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _markdown_table_to_rows(md: str) -> List[List[str]]:
    lines = [ln.strip() for ln in md.split("\n") if ln.strip()]
    if len(lines) < 3:
        return []
    header = [h.strip() for h in lines[0].split("|")]
    # Skip separator
    data_lines = lines[2:]
    rows: List[List[str]] = []
    for ln in data_lines:
        cells = [c.strip() for c in ln.split("|")]
        # Normalize length to header
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        elif len(cells) > len(header):
            cells = cells[: len(header)]
        rows.append(cells)
    return [header] + rows


def _write_csv(csv_path: Path, rows: List[List[str]]):
    if not rows:
        return
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(r)


def main() -> int:
    load_dotenv()

    # Validate env for Azure Document Intelligence
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
    except Exception as e:
        print(f"❌ Failed to import AzureDocumentIntelligenceService: {e}")
        return 1

    sows_dir = Path(__file__).parent / "sows"
    if not sows_dir.exists():
        print(f"❌ SOWs directory not found: {sows_dir}")
        return 1

    out_dir = Path(__file__).parent / "outputs" / "csv" / "docint_tables"
    _ensure_dir(out_dir)

    sow_files = [p for p in sows_dir.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}]
    if not sow_files:
        print("❌ No PDF/DOCX files found in sows directory")
        return 1

    print("🚀 Running Azure Document Intelligence (prebuilt-layout) on SOWs")
    print("=" * 60)

    client = AzureDocumentIntelligenceService()
    total_tables = 0

    for i, fp in enumerate(sorted(sow_files), 1):
        print(f"[{i}/{len(sow_files)}] {fp.name}")
        try:
            analysis = client.analyze_layout(fp)
            tables_md = client.extract_tables_markdown(analysis, max_tables=50)
            if not tables_md:
                print("  - No tables detected")
                continue
            table_count = 0
            for t_idx, md in enumerate(tables_md, 1):
                # Drop leading "Table X (pY):" if present
                content = md
                if "\n" in md:
                    content = md.split("\n", 1)[1]
                rows = _markdown_table_to_rows(content)
                if not rows:
                    continue
                csv_path = out_dir / f"{fp.stem}_table_{t_idx}.csv"
                _write_csv(csv_path, rows)
                table_count += 1
            print(f"  - Tables saved: {table_count}")
            total_tables += table_count
        except Exception as e:
            print(f"  - Failed: {e}")

    print("\n✅ Completed.")
    print(f"Total tables exported: {total_tables}")
    print(f"CSV output directory: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


