#!/usr/bin/env python3
"""
Test: LLM safety-net header mapping on mock column names.

For each mock header set, prints a side-by-side of:
- Original header
- Heuristic mapping (from SOWExtractionService._canonicalize_header)
- LLM mapping (canonical key)

Requires Azure OpenAI env vars used elsewhere in the project:
  AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List
from dotenv import load_dotenv


def _print_mapping_table(title: str, headers_raw: List[str], heuristics: List[str], llm_mapped: List[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("-" * 80)
    col_names = ["Original", "Heuristic", "LLM"]
    # Compute widths
    widths = [len(c) for c in col_names]
    for a, b, c in zip(headers_raw, heuristics, llm_mapped):
        widths[0] = max(widths[0], len(str(a)))
        widths[1] = max(widths[1], len(str(b)))
        widths[2] = max(widths[2], len(str(c)))
    def fmt_row(vals: List[str]) -> str:
        return " | ".join(str(v).ljust(w) for v, w in zip(vals, widths))
    print(fmt_row(col_names))
    print("-" * (sum(widths) + 3 * (len(col_names) - 1)))
    for a, b, c in zip(headers_raw, heuristics, llm_mapped):
        print(fmt_row([a, b, c]))


def _heuristic_map(headers_raw: List[str]) -> List[str]:
    # Import canonicalizer from service to keep behavior aligned
    import sys
    services_dir = Path(__file__).parent / "streamlit_app" / "services"
    sys.path.append(str(services_dir))
    from sow_extraction_service import SOWExtractionService  # type: ignore

    svc = SOWExtractionService()
    return [svc._canonicalize_header(h) for h in headers_raw]  # noqa: SLF001


def _llm_map(headers_raw: List[str]) -> List[str]:
    from openai import OpenAI

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    if not api_key or not endpoint or not deployment:
        raise RuntimeError("Missing Azure OpenAI env vars (key/endpoint/deployment)")

    client = OpenAI(
        api_key=api_key,
        base_url=f"{endpoint}/openai/deployments/{deployment}",
        default_query={"api-version": api_version},
    )

    schema = {
        "type": "object",
        "properties": {
            "mapped": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "name",
                        "role",
                        "primary_role",
                        "level",
                        "location",
                        "workstream",
                        "percentage",
                        "hours",
                        "ignore",
                    ],
                },
            }
        },
        "required": ["mapped"],
    }

    sys_prompt = (
        "Map each header to a canonical key for staffing tables. "
        "Valid keys: name, role, primary_role, level, location, workstream, percentage, hours, ignore. "
        "Use percentage for % time/FTE columns; hours for time allocations in hours."
    )
    user_prompt = "Headers: " + json.dumps([str(h or "").strip() for h in headers_raw])

    resp = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_schema", "json_schema": {"name": "map_headers", "schema": schema}},
    )
    payload = json.loads(resp.choices[0].message.content)
    mapped = payload.get("mapped")
    if isinstance(mapped, list) and len(mapped) == len(headers_raw):
        return mapped
    raise RuntimeError("LLM returned unexpected payload")


def main() -> int:
    load_dotenv()

    test_sets = [
        (
            "Baseline variants",
            ["Personnel", "Title", "% Time", "# Hours"],
        ),
        (
            "Unseen synonyms",
            ["Team Member", "Position", "Capacity", "Billable Hours"],
        ),
        (
            "FTE and locale mix",
            ["Resource", "Role / Discipline", "FTE", "Stunden"],  # Stunden=hours (DE)
        ),
        (
            "Sparse headers",
            ["Name", "Allocation", "Notes"],  # ambiguous allocation
        ),
    ]

    for title, headers_raw in test_sets:
        try:
            heur = _heuristic_map(headers_raw)
            llm = _llm_map(headers_raw)
            _print_mapping_table(title, headers_raw, heur, llm)
        except Exception as e:
            print(f"\n[{title}] Failed: {e}")

    print("\n✅ Completed header mapping tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


