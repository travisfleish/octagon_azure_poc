from azure.storage.blob import BlobServiceClient
import os

# get connection string
conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if not conn_str:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING not set")

try:
    service = BlobServiceClient.from_connection_string(conn_str)
    # List first 5 containers
    print("Listing containers...")
    for container in service.list_containers():
        print("-", container['name'])
    print("✅ Connection successful")
except Exception as e:
    print("❌ Connection failed:", e)
