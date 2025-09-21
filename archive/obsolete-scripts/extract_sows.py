import os, io, tempfile, json
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# --- CONFIG ---
STORAGE_ACCOUNT = "octagonstaffingstg5nww"
SRC_CONTAINER   = "sows"
DST_CONTAINER   = "extracted"

DOCINTEL_ENDPOINT = os.environ.get("DOCINTEL_ENDPOINT")  # e.g. https://octagon-staffing-docintel.cognitiveservices.azure.com/
DOCINTEL_KEY      = os.environ.get("DOCINTEL_KEY")

MODEL = "prebuilt-read"  # good OCR + layout text

# --- clients ---
cred = DefaultAzureCredential()
blob_service = BlobServiceClient(f"https://{STORAGE_ACCOUNT}.blob.core.windows.net", credential=cred)
src = blob_service.get_container_client(SRC_CONTAINER)
dst = blob_service.get_container_client(DST_CONTAINER)
try: dst.create_container()
except Exception: pass

di = DocumentIntelligenceClient(DOCINTEL_ENDPOINT, AzureKeyCredential(DOCINTEL_KEY))

def save_blob(name: str, data: bytes, meta: dict, ext: str):
    # copy metadata across and set simple content-types
    ct = "text/plain" if ext == "txt" else "application/json"
    dst.get_blob_client(name).upload_blob(
        data,
        overwrite=True,
        metadata=meta,
        content_settings=ContentSettings(content_type=ct),
    )

for b in src.list_blobs():
    print(f"Processing {b.name}")
    blob = src.get_blob_client(b.name)

    # pull metadata to propagate
    meta = (blob.get_blob_properties().metadata or {}).copy()

    # download to memory (fine for small docs; switch to stream for huge files)
    byts = blob.download_blob().readall()

    # run Document Intelligence
    poller = di.begin_analyze_document(model_id=MODEL, analyze_request=byts, content_type="application/octet-stream")
    result = poller.result()

    # plain text (lines joined)
    lines = []
    for page in result.pages or []:
        for line in page.lines or []:
            lines.append(line.content)
    text = "\n".join(lines).strip()

    # write outputs to extracted/<source>.(txt|json)
    base, _ = os.path.splitext(b.name)
    save_blob(f"{base}.txt", text.encode("utf-8"), meta, "txt")
    save_blob(f"{base}.json", json.dumps(result.as_dict(), ensure_ascii=False).encode("utf-8"), meta, "json")

print("Done: extracted text + JSON saved to 'extracted' container.")
