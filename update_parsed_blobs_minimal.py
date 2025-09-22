#!/usr/bin/env python3
"""
Update parsed blobs in Azure Storage 'parsed' container with minimal staffing schema for PDFs.

Process:
- For each local SOW file in sows/*.pdf, compute minimal staffing via the same logic as main service
- Fetch existing parsed JSON blob (<stem>_parsed.json)
- Merge/insert 'staffing_minimal' array
- Upload back to parsed container
"""

import os
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


async def update_one(file_path: Path, service) -> Dict[str, Any]:
    di = service._extract_staffing_via_document_intelligence(file_path)
    minimal = di.get('minimal', [])
    if not minimal:
        return {"updated": False, "reason": "no_minimal"}

    blob_name = f"{file_path.stem}_parsed.json"
    container = service.containers["parsed"]
    blob_client = service.blob_service_client.get_blob_client(container=container, blob=blob_name)

    try:
        existing = await blob_client.download_blob()
        text = await existing.content_as_text()
        data = json.loads(text)
    except Exception:
        data = {}

    # Replace staffing_plan with DI minimal
    data["staffing_plan"] = minimal
    # Remove any previous staffing_minimal if present
    if "staffing_minimal" in data:
        try:
            del data["staffing_minimal"]
        except Exception:
            pass
    json_data = json.dumps(data, indent=2, ensure_ascii=False)
    await blob_client.upload_blob(json_data.encode("utf-8"), overwrite=True, content_type="application/json")
    return {"updated": True, "blob": blob_name, "count": len(minimal)}


async def main() -> int:
    load_dotenv()
    from streamlit_app.services.sow_extraction_service import SOWExtractionService

    # Init service with Azure Storage
    svc = SOWExtractionService(sows_directory="sows")
    await svc.initialize()
    if not svc.blob_service_client:
        print("❌ Azure Storage not configured. Set AZURE_STORAGE_ACCOUNT_URL and auth.")
        return 1

    sows_dir = Path("sows")
    pdfs = [p for p in sows_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    if not pdfs:
        print("❌ No PDFs found in sows directory")
        return 1

    print("🚀 Updating parsed blobs with staffing_minimal for PDFs")
    print("=" * 60)
    updated = 0
    for i, fp in enumerate(sorted(pdfs), 1):
        try:
            res = await update_one(fp, svc)
            if res.get("updated"):
                updated += 1
                print(f"[{i}/{len(pdfs)}] {fp.name} -> {res.get('blob')} (entries: {res.get('count')})")
            else:
                print(f"[{i}/{len(pdfs)}] {fp.name} -> skipped ({res.get('reason')})")
        except Exception as e:
            print(f"[{i}/{len(pdfs)}] {fp.name} failed: {e}")

    print(f"\n✅ Done. Blobs updated: {updated}/{len(pdfs)}")
    return 0


if __name__ == "__main__":
    asyncio.run(main())


