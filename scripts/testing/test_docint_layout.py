#!/usr/bin/env python3
"""
Quick test: Azure Document Intelligence (prebuilt-layout) on a sample SOW PDF/DOCX.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()

    # Make services importable
    sys.path.append(str(Path(__file__).parent / "services"))
    from document_intelligence_service import AzureDocumentIntelligenceService  # type: ignore

    # Confirm env vars
    endpoint = os.getenv("AZURE_DOCINT_ENDPOINT")
    api_key = os.getenv("AZURE_DOCINT_API_KEY")
    api_version = os.getenv("AZURE_DOCINT_API_VERSION", "2023-07-31")
    if not endpoint or not api_key:
        print("❌ Missing AZURE_DOCINT_ENDPOINT or AZURE_DOCINT_API_KEY in environment")
        return 1
    print(f"Endpoint: {endpoint}")
    print(f"API Version: {api_version}")

    # Pick a candidate file
    sows_dir = Path(__file__).parent.parent / "sows"
    if not sows_dir.exists():
        print(f"❌ SOWs directory not found: {sows_dir}")
        return 1
    candidates = [p for p in sows_dir.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}]
    if not candidates:
        print("❌ No PDF/DOCX files found in sows directory")
        return 1
    # Prefer a PDF
    candidates.sort(key=lambda p: (p.suffix.lower() != ".pdf", p.name))
    target = candidates[0]
    print(f"📄 Analyzing: {target.name}")

    # Analyze
    try:
        client = AzureDocumentIntelligenceService()
        analysis = client.analyze_layout(target)
        print(f"✅ Analysis complete | pages={analysis.get('pages', 0)}")
        tables_md = client.extract_tables_markdown(analysis, max_tables=5)
        print(f"📊 Tables extracted: {len(tables_md)}")
        if tables_md:
            print("\nMarkdown preview (first table):\n")
            preview = tables_md[0]
            print(preview if len(preview) < 2000 else preview[:2000] + "\n... [truncated]")
        return 0
    except Exception as e:
        print(f"❌ Document Intelligence analysis failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


