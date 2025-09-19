from __future__ import annotations

from datetime import datetime
from typing import Optional

from azure.storage.blob.aio import BlobServiceClient
from fastapi import UploadFile

from ..config import get_settings
from ..utils.azure_auth import get_default_credential


class AzureStorageError(Exception):
    """Raised when Azure Storage operations fail."""


class AzureStorageService:
    """Service for operations against Azure Blob Storage."""

    def __init__(self, container_name: str = "sows") -> None:
        self._container_name = container_name
        self._client: Optional[BlobServiceClient] = None

    async def _get_client(self) -> BlobServiceClient:
        if self._client is None:
            settings = get_settings()
            credential = await get_default_credential()
            self._client = BlobServiceClient(account_url=settings.storage_blob_endpoint, credential=credential)
        return self._client

    async def upload_file(self, file: UploadFile, blob_name: str) -> str:
        """Upload a file to the container and return the blob URL."""

        try:
            client = await self._get_client()
            container = client.get_container_client(self._container_name)
            await container.upload_blob(name=blob_name, data=await file.read(), overwrite=True, content_type=file.content_type)
            return f"{client.url}/{self._container_name}/{blob_name}"
        except Exception as exc:  # noqa: BLE001
            raise AzureStorageError(str(exc)) from exc

    async def download_bytes(self, blob_name: str) -> bytes:
        try:
            client = await self._get_client()
            container = client.get_container_client(self._container_name)
            downloader = await container.download_blob(blob=blob_name)
            return await downloader.readall()
        except Exception as exc:  # noqa: BLE001
            raise AzureStorageError(str(exc)) from exc



