# set_tags_only.py
import re
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

ACCOUNT_NAME = "octagonstaffingstg5nww"
CONTAINER = "sows"
NAME_RE = re.compile(r"company_(\d+).*?sow_(\d+)\.(\w+)$", re.IGNORECASE)

def parse(name: str):
    m = NAME_RE.search(name)
    if not m:
        ext = name.split(".")[-1].lower() if "." in name else "bin"
        return "Unknown","Unknown",ext
    return f"Company_{m.group(1)}", m.group(2), m.group(3).lower()

def main():
    cred = DefaultAzureCredential()
    svc = BlobServiceClient(f"https://{ACCOUNT_NAME}.blob.core.windows.net", credential=cred)
    cc = svc.get_container_client(CONTAINER)

    for item in cc.list_blobs():
        name = item.name
        company, sow_id, ext = parse(name)
        print(f"Tagging {name} → company={company} sow_id={sow_id} format={ext}")
        blob = cc.get_blob_client(name)
        set_tags = getattr(blob, "set_tags", None) or getattr(blob, "set_blob_tags", None)
        set_tags({"company": company, "sow_id": sow_id, "format": ext})

if __name__ == "__main__":
    main()
