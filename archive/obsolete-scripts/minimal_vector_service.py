#!/usr/bin/env python3
"""
Minimal vector service with only essential fields for semantic search.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndex,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
)

from octagon_staffing_app.app.config import get_settings


class MinimalVectorServiceError(Exception):
    """Raised when vector operations fail."""


class MinimalVectorService:
    """Minimal service for vector operations using Azure AI Search."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.search_endpoint or not settings.search_key:
            raise MinimalVectorServiceError("Azure Search configuration missing")
        
        self._endpoint = settings.search_endpoint
        self._key = settings.search_key
        self._index_name = "octagon-sows-minimal-working"
        self._credential = AzureKeyCredential(settings.search_key)
        
        # Initialize clients
        self._search_client: Optional[SearchClient] = None
        self._index_client: Optional[SearchIndexClient] = None

    async def _get_search_client(self) -> SearchClient:
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self._endpoint,
                index_name=self._index_name,
                credential=self._credential,
            )
        return self._search_client

    async def _get_index_client(self) -> SearchIndexClient:
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=self._endpoint,
                credential=self._credential,
            )
        return self._index_client

    async def create_index(self) -> None:
        """Create a minimal vector search index."""
        index_client = await self._get_index_client()
        
        # Minimal schema with only essential fields
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="blob_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="company", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="sow_id", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="format", type=SearchFieldDataType.String, filterable=True),
            
            # Main text content for search
            SearchableField(name="full_text", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
            
            # Vector field for semantic search
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,  # OpenAI text-embedding-3-small dimensions
                vector_search_profile_name="default-vector-profile"
            ),
        ]

        # Vector search configuration
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="default-algorithm",
                    kind=VectorSearchAlgorithmKind.HNSW,
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": VectorSearchAlgorithmMetric.COSINE
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="default-algorithm"
                )
            ]
        )

        # Create the search index
        search_index = SearchIndex(
            name=self._index_name,
            fields=fields,
            vector_search=vector_search,
        )

        try:
            await index_client.create_or_update_index(search_index)
            print(f"✅ Created minimal search index: {self._index_name}")
        except Exception as e:
            raise MinimalVectorServiceError(f"Failed to create search index: {e}") from e

    async def index_document(self, document: Dict[str, Any]) -> None:
        """Index a single document."""
        search_client = await self._get_search_client()
        
        try:
            await search_client.upload_documents([document])
            print(f"✅ Indexed document: {document.get('blob_name', 'unknown')}")
        except Exception as e:
            raise MinimalVectorServiceError(f"Failed to index document: {e}") from e

    async def search_similar(
        self, 
        query_vector: List[float], 
        top_k: int = 5,
        filter_expression: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity."""
        search_client = await self._get_search_client()
        
        try:
            # Vector search query
            search_results = await search_client.search(
                search_text="",  # Empty for pure vector search
                vector_queries=[
                    {
                        "kind": "vector",
                        "vector": query_vector,
                        "k_nearest_neighbors": top_k,
                        "fields": "content_vector"
                    }
                ],
                filter=filter_expression,
                select=["id", "blob_name", "company", "sow_id", "full_text"],
                top=top_k
            )
            
            results = []
            rank = 1
            async for result in search_results:
                result_dict = dict(result)
                # Simple ranking score
                result_dict['score'] = round(1.0 - (rank * 0.1), 2)
                result_dict['rank'] = rank
                print(f"✅ Found similar document: {result_dict.get('blob_name', 'unknown')} (rank: {rank})")
                results.append(result_dict)
                rank += 1
            
            return results
        except Exception as e:
            raise MinimalVectorServiceError(f"Vector search failed: {e}") from e

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the search index."""
        search_client = await self._get_search_client()
        
        try:
            stats = await search_client.get_search_statistics()
            return {
                "document_count": stats.document_count,
                "storage_size": stats.storage_size,
                "vector_index_size": stats.vector_index_size
            }
        except Exception as e:
            raise MinimalVectorServiceError(f"Failed to get index stats: {e}") from e
