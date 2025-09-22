#!/usr/bin/env python3
"""
Normalize DI staffing JSONs to a minimal schema across all processed PDFs.

Input directory:
- outputs/json/docint_staffing/*.json (produced by docint_staffing_json.py)

Output directory:
- outputs/json/docint_staffing_minimal/<stem>_minimal.json

Minimal record fields:
- name (string|null)
- level (string|null)
- title (string)  # required; use role or fallback to primary_role
- primary_role (string|null)
- hours (number|null)
- hours_pct (number|null)  # 0–100 based on 1800 hours/year
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


FTE_YEARLY_HOURS = 1800.0


def _to_null_if_na(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip()
    if not v or v.upper() in {"N/A", "NA"}:
        return None
    return v


def _round_or_none(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except Exception:
        return None


def _normalize_entry(e: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = _to_null_if_na(e.get("name"))  # allow null
    level = _to_null_if_na(e.get("level"))
    role = _to_null_if_na(e.get("role"))
    primary_role = _to_null_if_na(e.get("primary_role"))

    # Title selection: role preferred, fallback to primary_role, then level
    title = role or primary_role or level
    if not title:
        # No usable title -> skip entry per minimal dataset usefulness
        return None

    hours = e.get("hours")
    pct = e.get("percentage")
    try:
        hours_val = float(hours) if hours is not None else None
    except Exception:
        hours_val = None
    try:
        pct_val = float(pct) if pct is not None else None
    except Exception:
        pct_val = None

    # Normalize hours/pct: trust pct if both present
    if pct_val is not None:
        if pct_val < 0:
            pct_val = 0.0
        if pct_val > 100:
            pct_val = 100.0
        hours_val = (pct_val / 100.0) * FTE_YEARLY_HOURS
    elif hours_val is not None:
        pct_val = (hours_val / FTE_YEARLY_HOURS) * 100.0

    return {
        "name": name,
        "level": level,
        "title": title,
        "primary_role": primary_role,
        "hours": _round_or_none(hours_val),
        "hours_pct": _round_or_none(pct_val),
    }


def normalize_file(src_path: Path, dst_path: Path) -> int:
    data = json.loads(src_path.read_text())
    entries = data.get("staffing_entries", []) or []
    out: List[Dict[str, Any]] = []
    for e in entries:
        ne = _normalize_entry(e)
        if ne is not None:
            out.append(ne)

    payload = {
        "file": data.get("file"),
        "entries": out,
    }
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(json.dumps(payload, indent=2))
    return len(out)


def main() -> int:
    src_dir = Path("outputs/json/docint_staffing")
    dst_dir = Path("outputs/json/docint_staffing_minimal")
    if not src_dir.exists():
        print(f"❌ Source directory not found: {src_dir}")
        return 1

    files = sorted([p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() == ".json"])
    if not files:
        print("❌ No source JSON files found to normalize")
        return 1

    print("🚀 Normalizing DI staffing JSONs to minimal schema")
    print("=" * 60)
    total = 0
    for i, src in enumerate(files, 1):
        dst = dst_dir / f"{src.stem}_minimal.json"
        try:
            count = normalize_file(src, dst)
            total += count
            print(f"[{i}/{len(files)}] {src.name} -> {dst.name} | entries: {count}")
        except Exception as e:
            print(f"[{i}/{len(files)}] {src.name} failed: {e}")

    # Optional combined output
    combined = []
    for dst in sorted([p for p in dst_dir.iterdir() if p.is_file() and p.suffix.lower() == ".json"]):
        try:
            combined.append(json.loads(dst.read_text()))
        except Exception:
            pass
    (dst_dir / "_combined.json").write_text(json.dumps(combined, indent=2))

    print(f"\n✅ Done. Total normalized entries: {total}")
    print(f"Output directory: {dst_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


