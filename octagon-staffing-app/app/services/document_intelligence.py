from __future__ import annotations

from typing import Optional

from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from ..config import get_settings


class DocumentIntelligenceError(Exception):
    """Raised when Document Intelligence operations fail."""


class DocumentIntelligenceService:
    """Wrapper for Azure Document Intelligence to parse SOWs."""

    def __init__(self) -> None:
        self._client: Optional[DocumentIntelligenceClient] = None

    async def _get_client(self) -> DocumentIntelligenceClient:
        if self._client is None:
            settings = get_settings()
            if not settings.docintel_endpoint or not settings.docintel_key:
                raise DocumentIntelligenceError("Document Intelligence configuration missing")
            self._client = DocumentIntelligenceClient(settings.docintel_endpoint, AzureKeyCredential(settings.docintel_key))
        return self._client

    async def extract_structure(self, pdf_bytes: bytes) -> dict:
        """Call DI to extract structure from PDF bytes. Returns raw JSON."""

        try:
            client = await self._get_client()
            poller = await client.begin_analyze_document("prebuilt-layout", pdf_bytes)
            result = await poller.result()
            # Placeholder conversion to dict
            return {"pages": len(result.pages) if hasattr(result, "pages") else 0}
        except Exception as exc:  # noqa: BLE001
            raise DocumentIntelligenceError(str(exc)) from exc



