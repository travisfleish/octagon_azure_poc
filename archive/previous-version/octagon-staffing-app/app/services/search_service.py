from __future__ import annotations

from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

from ..config import get_settings


class SearchServiceError(Exception):
    """Raised when Azure Search operations fail."""


class SearchService:
    """Service to index and retrieve similar projects from Azure AI Search."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.search_endpoint or not settings.search_key:
            raise SearchServiceError("Azure Search configuration missing")
        self._client = SearchClient(
            endpoint=settings.search_endpoint,
            index_name=settings.search_index_name,
            credential=AzureKeyCredential(settings.search_key),
        )

    async def find_similar(self, text: str, top_k: int = 5) -> List[str]:
        try:
            results = self._client.search(search_text=text, top=top_k)
            docs: List[str] = []
            async for r in results:
                docs.append(str(r.get("id", "")))
            return docs
        except Exception as exc:  # noqa: BLE001
            raise SearchServiceError(str(exc)) from exc



