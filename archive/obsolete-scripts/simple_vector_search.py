#!/usr/bin/env python3
"""
Simple vector search service for Streamlit integration.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from app.config import get_settings
from app.services.embedding_service import EmbeddingService

class SimpleVectorSearch:
    """Simple vector search service for the working index."""
    
    def __init__(self):
        settings = get_settings()
        self._endpoint = settings.search_endpoint
        self._key = settings.search_key
        self._index_name = "octagon-sows-text-only"
        self._credential = AzureKeyCredential(settings.search_key)
        self._embedding_service = EmbeddingService()

    async def _get_search_client(self):
        return SearchClient(
            endpoint=self._endpoint,
            index_name=self._index_name,
            credential=self._credential,
        )

    async def search_similar_documents(
        self, 
        query_text: str, 
        top_k: int = 5,
        search_type: str = "vector",
        company_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity."""
        search_client = await self._get_search_client()
        
        try:
            # Generate embedding for the query
            query_embeddings = await self._embedding_service.get_embeddings_batch([query_text])
            if not query_embeddings or not query_embeddings[0]:
                return []
            
            # Build filter expression
            filter_expression = None
            if company_filter and company_filter != "All":
                filter_expression = f"company eq '{company_filter}'"
            
            if search_type == "vector":
                # Pure vector search
                results = await search_client.search(
                    search_text="",
                    vector_queries=[
                        {
                            "kind": "vector",
                            "vector": query_embeddings[0],
                            "k_nearest_neighbors": top_k,
                            "fields": "content_vector"
                        }
                    ],
                    filter=filter_expression,
                    select=["id", "blob_name", "company", "sow_id", "full_text"],
                    top=top_k
                )
            elif search_type == "hybrid":
                # Hybrid search (text + vector)
                results = await search_client.search(
                    search_text=query_text,
                    vector_queries=[
                        {
                            "kind": "vector",
                            "vector": query_embeddings[0],
                            "k_nearest_neighbors": top_k,
                            "fields": "content_vector"
                        }
                    ],
                    filter=filter_expression,
                    select=["id", "blob_name", "company", "sow_id", "full_text"],
                    top=top_k
                )
            else:  # text search
                results = await search_client.search(
                    search_text=query_text,
                    filter=filter_expression,
                    select=["id", "blob_name", "company", "sow_id", "full_text"],
                    top=top_k
                )
            
            # Process results
            search_results = []
            rank = 1
            async for result in results:
                result_dict = dict(result)
                # Add ranking and simple score
                result_dict['rank'] = rank
                result_dict['score'] = round(1.0 - (rank * 0.1), 2)
                search_results.append(result_dict)
                rank += 1
            
            return search_results
            
        except Exception as e:
            print(f"Search failed: {e}")
            return []

    async def get_available_companies(self) -> List[str]:
        """Get list of available companies for filtering."""
        search_client = await self._get_search_client()
        
        try:
            # Get all unique companies
            results = await search_client.search(
                search_text="*",
                select=["company"],
                top=1000
            )
            
            companies = set()
            async for result in results:
                if result.get('company'):
                    companies.add(result['company'])
            
            return ["All"] + sorted(list(companies))
            
        except Exception as e:
            print(f"Failed to get companies: {e}")
            return ["All"]

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get basic index statistics."""
        search_client = await self._get_search_client()
        
        try:
            # Count documents
            results = await search_client.search(
                search_text="*",
                select=["id"],
                top=1000
            )
            
            count = 0
            async for result in results:
                count += 1
            
            return {
                "document_count": count,
                "index_name": self._index_name
            }
            
        except Exception as e:
            print(f"Failed to get stats: {e}")
            return {"document_count": 0, "index_name": self._index_name}

# Helper function for Streamlit
def run_async(coro):
    """Helper function to run async code in Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
