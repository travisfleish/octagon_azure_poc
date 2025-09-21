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
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
)

from ..config import get_settings


class VectorServiceError(Exception):
    """Raised when vector operations fail."""


class VectorService:
    """Service for vector operations using Azure AI Search."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.search_endpoint or not settings.search_key:
            raise VectorServiceError("Azure Search configuration missing")
        
        self._endpoint = settings.search_endpoint
        self._key = settings.search_key
        self._index_name = "octagon-sows-minimal"  # Use the working minimal index
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
        """Create the vector search index with proper schema."""
        index_client = await self._get_index_client()
        
        # Define the search index schema
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="blob_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="company", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="sow_id", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="format", type=SearchFieldDataType.String, filterable=True),
            
            # Text fields for search
            SearchableField(name="full_text", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
            SearchableField(name="scope_bullets", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchableField(name="deliverables", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchableField(name="roles_detected", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchableField(name="assumptions", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            
            # Structured data fields
            SimpleField(name="term_start", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="term_end", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="term_months", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SimpleField(name="explicit_hours", type=SearchFieldDataType.Collection(SearchFieldDataType.Int32), filterable=True, nullable=True),
            SimpleField(name="fte_pct", type=SearchFieldDataType.Collection(SearchFieldDataType.Int32), filterable=True, nullable=True),
            
            # Vector fields for semantic search
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,  # OpenAI text-embedding-3-small dimensions
                vector_search_profile_name="default-vector-profile"
            ),
            SearchField(
                name="structured_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,
                vector_search_profile_name="default-vector-profile"
            ),
            
            # Metadata for filtering
            SimpleField(name="text_length", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
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

        # Semantic search configuration
        semantic_config = SemanticConfiguration(
            name="default-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="blob_name"),
                prioritized_content_fields=[
                    SemanticField(field_name="full_text"),
                    SemanticField(field_name="scope_bullets"),
                    SemanticField(field_name="deliverables"),
                ],
                prioritized_keywords_fields=[
                    SemanticField(field_name="roles_detected"),
                    SemanticField(field_name="assumptions"),
                ]
            )
        )

        semantic_search = SemanticSearch(configurations=[semantic_config])

        # Create the search index
        search_index = SearchIndex(
            name=self._index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )

        try:
            await index_client.create_or_update_index(search_index)
            print(f"✅ Created/updated search index: {self._index_name}")
        except Exception as e:
            raise VectorServiceError(f"Failed to create search index: {e}") from e

    async def index_document(self, document: Dict[str, Any]) -> None:
        """Index a single document with vector embeddings."""
        search_client = await self._get_search_client()
        
        try:
            await search_client.upload_documents([document])
            print(f"✅ Indexed document: {document.get('blob_name', 'unknown')}")
        except Exception as e:
            raise VectorServiceError(f"Failed to index document: {e}") from e

    async def batch_index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Index multiple documents in batch."""
        search_client = await self._get_search_client()
        
        try:
            # Process in batches of 100 (Azure Search limit)
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                await search_client.upload_documents(batch)
                print(f"✅ Indexed batch {i//batch_size + 1}: {len(batch)} documents")
        except Exception as e:
            raise VectorServiceError(f"Failed to batch index documents: {e}") from e

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
                # Use Azure Search's internal ranking (higher rank = more relevant)
                result_dict['score'] = round(1.0 - (rank * 0.1), 2)  # Simple decreasing score
                result_dict['rank'] = rank
                print(f"✅ Found similar document: {result_dict.get('blob_name', 'unknown')} (rank: {rank})")
                results.append(result_dict)
                rank += 1
            
            return results
        except Exception as e:
            raise VectorServiceError(f"Vector search failed: {e}") from e

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        top_k: int = 5,
        filter_expression: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining text and vector search."""
        search_client = await self._get_search_client()
        
        try:
            search_results = await search_client.search(
                search_text=query_text,
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
                # Use Azure Search's internal ranking (higher rank = more relevant)
                result_dict['score'] = round(1.0 - (rank * 0.1), 2)  # Simple decreasing score
                result_dict['rank'] = rank
                print(f"✅ Found similar document: {result_dict.get('blob_name', 'unknown')} (rank: {rank})")
                results.append(result_dict)
                rank += 1
            
            return results
        except Exception as e:
            raise VectorServiceError(f"Hybrid search failed: {e}") from e

    async def delete_document(self, document_id: str) -> None:
        """Delete a document from the index."""
        search_client = await self._get_search_client()
        
        try:
            await search_client.delete_documents([{"id": document_id}])
            print(f"✅ Deleted document: {document_id}")
        except Exception as e:
            raise VectorServiceError(f"Failed to delete document: {e}") from e

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, min(1.0, similarity))  # Clamp between 0 and 1

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
            raise VectorServiceError(f"Failed to get index stats: {e}") from e
