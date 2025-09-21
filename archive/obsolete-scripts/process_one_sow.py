# process_one_sow.py
import io
import json
import re
import zipfile
import csv
from datetime import datetime
from typing import Dict

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from PyPDF2 import PdfReader

# Import the LLM schema extractor (reads .env inside)
from llm_extract import llm_parse_schema

# --------------------
# CONFIG
# --------------------
ACCOUNT_URL = "https://octagonstaffingstg5nww.blob.core.windows.net/"
SRC_CONTAINER = "sows"
EXTRACTED_CONTAINER = "extracted"
PARSED_CONTAINER = "parsed"

# Toggle this to test a single blob first; set to None to process all
TEST_BLOB: str | None = None
# e.g. TEST_BLOB = "company_1_sow_1.docx"

# --------------------
# UTILITIES
# --------------------
def extract_docx_text(data: bytes) -> str:
    """Fast DOCX text pull via document.xml; python-docx also works if you prefer."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", text).strip()

def extract_pdf_text(data: bytes) -> str:
    """Lightweight PDF text; we’ll add Azure Document Intelligence later for tables."""
    reader = PdfReader(io.BytesIO(data))
    out = []
    # Cap initial read to first 10 pages for speed; adjust as needed
    for page in reader.pages[:10]:
        try:
            out.append(page.extract_text() or "")
        except Exception:
            pass
    return re.sub(r"\s+", " ", "\n".join(out)).strip()

def parse_fields_deterministic(text: str) -> Dict:
    """First-pass heuristics kept for auditability alongside LLM output."""
    scope = re.findall(r"(?:Scope of Work|Scope|Services)[:\-]\s*(.+?)(?=(?:Deliverables|Term|Timeline|$))", text, re.I)
    deliverables = re.findall(r"(?:Deliverables?)[:\-]\s*(.+?)(?=(?:Term|Timeline|$))", text, re.I)
    dates = re.findall(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b", text, re.I)
    roles = re.findall(r"\b(Account|Manager|Director|Analyst|Coordinator|Designer|Strategist|Producer|Engineer)\b", text, re.I)
    fte = re.findall(r"\b(\d{1,3})\s*%?\s*FTE\b", text, re.I)
    hours = re.findall(r"\b(\d{1,4})\s*(?:hours|hrs)\b", text, re.I)
    rate_hits = re.findall(r"\b(rate|fee)s?\b.*?\b(hour|daily|monthly)\b", text, re.I)

    return {
        "term": {"start": None, "end": None, "months": None, "inferred": False},
        "scope_bullets": [scope[0]] if scope else [],
        "deliverables": [deliverables[0]] if deliverables else [],
        "units": {
            "explicit_hours": [int(h) for h in hours[:5]] if hours else None,
            "fte_pct": [int(x) for x in fte[:5]] if fte else None,
            "fees": [],
            "rate_table": [{"hit": " ".join(hit)} for hit in rate_hits[:5]]
        },
        "roles_detected": [{"title": r} for r in sorted(set(roles), key=str.lower)],
        "assumptions": [],
        "provenance": {"text_source": "pdf_or_docx", "sample_dates": dates[:3]}
    }

def process_blob(src, extracted, parsed, blob_name: str) -> Dict:
    """Download a blob, extract text, call LLM parser, and write outputs."""
    b = src.get_blob_client(blob_name)
    props = b.get_blob_properties()
    meta = props.metadata or {}
    try:
        tags_resp = b.get_blob_tags()
        tags = tags_resp.get("tags", {}) if isinstance(tags_resp, dict) else {}
    except Exception:
        tags = {}

    data = b.download_blob().readall()
    ctype = (props.content_settings.content_type or "").lower()

    if blob_name.lower().endswith(".docx") or "wordprocessingml" in ctype:
        text = extract_docx_text(data)
        fmt = "docx"
    elif blob_name.lower().endswith(".pdf") or "pdf" in ctype:
        text = extract_pdf_text(data)
        fmt = "pdf"
    else:
        raise ValueError(f"Unsupported type for {blob_name}: {ctype}")

    stem = blob_name.rsplit(".", 1)[0]

    # 1) Raw text artifact
    extracted.upload_blob(f"{stem}.txt", text.encode("utf-8"), overwrite=True, metadata=meta)

    # 2) Deterministic baseline (for audit)
    det = parse_fields_deterministic(text)

    # 3) LLM-powered schema extraction (authoritative for downstream)
    llm = llm_parse_schema(blob_name, fmt, text)

    # Merge company/sow_id preference: LLM → metadata → tags
    company = llm.get("company") or meta.get("company") or tags.get("company")
    sow_id  = llm.get("sow_id")  or meta.get("sow_id")  or tags.get("sow_id")

    record = {
        "blob_name": blob_name,
        "format": fmt,
        "metadata": meta,
        "tags": tags,
        "company": company,
        "sow_id": sow_id,
        "deterministic": det,
        "llm": llm
    }

    parsed.upload_blob(
        f"{stem}.json",
        json.dumps(record, indent=2).encode("utf-8"),
        overwrite=True,
        metadata=meta
    )

    # Small manifest row back to caller
    return {
        "blob_name": blob_name,
        "format": fmt,
        "company": company,
        "sow_id": sow_id,
        "text_chars": len(text),
        "roles_detected_det": ",".join(sorted({r["title"] for r in det.get("roles_detected", [])})) if det.get("roles_detected") else "",
        "has_llm": bool(llm),
    }

def main():
    cred = DefaultAzureCredential()   # uses your 'az login' locally
    svc = BlobServiceClient(account_url=ACCOUNT_URL, credential=cred)
    src = svc.get_container_client(SRC_CONTAINER)
    extracted = svc.get_container_client(EXTRACTED_CONTAINER)
    parsed = svc.get_container_client(PARSED_CONTAINER)

    results = []

    if TEST_BLOB:  # single-file smoke test
        print("Processing (single):", TEST_BLOB)
        row = process_blob(src, extracted, parsed, TEST_BLOB)
        results.append(row)
    else:          # process all SOWs in container
        for blob in src.list_blobs():
            name = blob.name
            if not name.lower().endswith((".pdf", ".docx")):
                continue
            print("Processing:", name)
            try:
                row = process_blob(src, extracted, parsed, name)
                results.append(row)
            except Exception as e:
                print("  ⚠️ Skipped due to error:", e)

    # Write a local manifest and upload to parsed/
    manifest_name = f"manifest_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
    with open(manifest_name, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "blob_name","format","company","sow_id","text_chars","roles_detected_det","has_llm"
        ])
        writer.writeheader()
        writer.writerows(results)

    parsed.upload_blob(f"manifest/{manifest_name}", open(manifest_name, "rb"), overwrite=True)
    print(f"✅ Uploaded parsed/manifest/{manifest_name} with {len(results)} rows")

if __name__ == "__main__":
    main()
