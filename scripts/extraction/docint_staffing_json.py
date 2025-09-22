#!/usr/bin/env python3
"""
Extract staffing plan JSON from all PDF SOWs using Azure Document Intelligence (prebuilt-layout).

Outputs one JSON per SOW under outputs/json/docint_staffing/<sow_stem>.json
Each JSON contains an array of employee-centric entries aggregated from detected tables.
"""

from __future__ import annotations

import os
import re
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _canonicalize_header(header_cell: str) -> str:
    h = (header_cell or "").strip().lower()
    h = re.sub(r"\s+", " ", h)
    # Common mappings
    if any(k in h for k in ["name", "personnel", "staff"]):
        return "name"
    if any(k in h for k in ["title", "role", "position"]):
        # Prefer more specific when both appear
        if "primary role" in h:
            return "primary_role"
        return "role"
    # Percentage-like columns
    if "%" in h or "percent" in h or "% time" in h:
        return "percentage"
    # Explicit hours allocation columns
    if h.strip(" #") == "hours" or "# hours" in h:
        return "hours"
    # Avoid mis-mapping Billable Hours Per Annum as allocation hours
    if "billable hours per annum" in h:
        return "bhpa"
    # Generic hours keywords (fallback)
    if "hour" in h:
        return "hours"
    if "location" in h:
        return "location"
    if "level" in h:
        return "level"
    if "workstream" in h or "discipline" in h or "department" in h:
        return "workstream"
    return h  # fallback raw header


def _extract_numeric_percentage(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    # Sometimes FTE like 0.5 FTE
    m = re.search(r"(\d(?:\.\d+)?)\s*fte", text, re.I)
    if m:
        try:
            return float(m.group(1)) * 100.0
        except Exception:
            return None
    return None


def _extract_numeric_hours(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d{1,4}(?:\.\d+)?)\s*(?:hours|hrs|hr)\b", text, re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    # If cell is just a number, assume hours
    m = re.fullmatch(r"\d{1,4}(?:\.\d+)?", text.strip())
    if m:
        try:
            return float(m.group(0))
        except Exception:
            return None
    return None


def _parse_table_to_entries(matrix: List[List[str]], page_number: int, table_index: int) -> List[Dict[str, Any]]:
    if not matrix or not matrix[0]:
        return []
    # Detect the most likely header row among the first few rows
    def _tokens(row: List[str]) -> List[str]:
        return [str(t or "").strip().lower() for t in row]

    def _score(row: List[str]) -> int:
        toks = _tokens(row)
        score = 0
        for t in toks:
            if any(k in t for k in ["name", "personnel", "staff"]):
                score += 3
            if any(k in t for k in ["title", "role", "position"]):
                score += 3
            if "level" in t:
                score += 1
            if "%" in t or "percent" in t or "% time" in t:
                score += 2
            if "# hours" in t or t.strip(" #") == "hours":
                score += 3
        return score

    search_up_to = min(3, len(matrix))
    header_idx = 0
    best_score = _score(matrix[0])
    for i in range(1, search_up_to):
        s = _score(matrix[i])
        if s > best_score:
            best_score = s
            header_idx = i

    headers_raw = matrix[header_idx]
    headers = [_canonicalize_header(h) for h in headers_raw]
    entries: List[Dict[str, Any]] = []

    # Build indices per canonical header
    idx: Dict[str, int] = {}
    for i, h in enumerate(headers):
        # Preserve first occurrence only
        if h not in idx:
            idx[h] = i

    def get(col: str, row: List[str]) -> str:
        j = idx.get(col)
        if j is None or j >= len(row):
            return ""
        return (row[j] or "").strip()

    # Fill in blank headers by inspecting column values just below header
    for c in range(len(headers)):
        if headers[c]:
            continue
        samples = []
        for r in range(header_idx + 1, min(len(matrix), header_idx + 6)):
            if c < len(matrix[r]):
                samples.append((matrix[r][c] or "").strip())
        if any("%" in v for v in samples):
            headers[c] = "percentage"
        elif any(re.fullmatch(r"\d{1,4}(?:[.,]\d+)?", v.replace(",", "")) for v in samples if v):
            headers[c] = "hours"

    # Iterate data rows after the detected header
    for r_idx, row in enumerate(matrix[header_idx + 1 :], start=1):
        if not any((cell or "").strip() for cell in row):
            continue
        # Filter out totals/summary rows if any cell starts with 'total'
        if any(str(cell or "").strip().lower().startswith("total") for cell in row):
            continue
        name = get("name", row) or "N/A"
        role = get("role", row)
        primary_role = get("primary_role", row)
        level = get("level", row)
        location = get("location", row)
        workstream = get("workstream", row)

        pct_text = get("percentage", row)
        hours_text = get("hours", row)
        pct_val = _extract_numeric_percentage(pct_text)
        # Clean hours to avoid misinterpreting thousand separators
        hours_clean = (hours_text or "").replace(",", "").strip()
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", hours_clean):  # e.g., 1.800 -> 1800
            hours_clean = hours_clean.replace(".", "")
        hours_val = _extract_numeric_hours(hours_clean)

        # If percentage cell empty but hours cell has % inside, extract
        if pct_val is None and hours_text:
            pct_val = _extract_numeric_percentage(hours_text)
        # If hours cell empty but percentage cell contains hours, extract
        if hours_val is None and pct_text:
            hours_val = _extract_numeric_hours(pct_text)

        # Assemble column_values for traceability
        column_values = {str(headers_raw[i]).strip(): (row[i] if i < len(row) else "") for i in range(len(headers_raw))}

        entry = {
            "name": name,
            "role": role or primary_role or "",
            "primary_role": primary_role or "",
            "level": level or "",
            "workstream": workstream or "",
            "location": location or "",
            "percentage": pct_val,
            "hours": hours_val,
            "page": page_number,
            "source_table_index": table_index,
            "row_index": r_idx,
            "column_values": column_values,
        }

        # Filter out total/footer rows heuristically
        if re.search(r"^total\b", (name or role or primary_role or "").lower()):
            continue

        entries.append(entry)

    return entries


def main() -> int:
    load_dotenv()

    endpoint = os.getenv("AZURE_DOCINT_ENDPOINT")
    api_key = os.getenv("AZURE_DOCINT_API_KEY")
    if not endpoint or not api_key:
        print("❌ Missing AZURE_DOCINT_ENDPOINT or AZURE_DOCINT_API_KEY in environment")
        return 1

    # Import service
    services_dir = Path(__file__).parent / "streamlit_app" / "services"
    sys.path.append(str(services_dir))
    from document_intelligence_service import AzureDocumentIntelligenceService  # type: ignore

    sows_dir = Path(__file__).parent / "sows"
    if not sows_dir.exists():
        print(f"❌ SOWs directory not found: {sows_dir}")
        return 1

    out_dir = Path(__file__).parent / "outputs" / "json" / "docint_staffing"
    _ensure_dir(out_dir)

    pdf_files = [p for p in sows_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    if not pdf_files:
        print("❌ No PDF files found in sows directory")
        return 1

    client = AzureDocumentIntelligenceService()

    print("🚀 Extracting staffing JSON from PDFs with Azure Document Intelligence")
    print("=" * 70)

    total_entries = 0
    for i, fp in enumerate(sorted(pdf_files), 1):
        print(f"[{i}/{len(pdf_files)}] {fp.name}")
        try:
            analysis = client.analyze_layout(fp)
            tables = analysis.get("tables", [])
            all_entries: List[Dict[str, Any]] = []
            for t_idx, table in enumerate(tables, 1):
                matrix = table.to_matrix()
                if not matrix or len(matrix) < 2:
                    continue
                entries = _parse_table_to_entries(matrix, page_number=table.page_number, table_index=t_idx)
                if entries:
                    all_entries.extend(entries)

            payload = {
                "file": str(fp),
                "pages": analysis.get("pages", 0),
                "tables_detected": len(tables),
                "staffing_entries": all_entries,
            }

            out_path = out_dir / f"{fp.stem}.json"
            with open(out_path, "w") as f:
                json.dump(payload, f, indent=2)
            print(f"  - Entries: {len(all_entries)} | Saved: {out_path}")
            total_entries += len(all_entries)
        except Exception as e:
            print(f"  - Failed: {e}")

    print("\n✅ Completed.")
    print(f"Total staffing entries extracted: {total_entries}")
    print(f"JSON output directory: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


