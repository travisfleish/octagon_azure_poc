#!/usr/bin/env python3
"""
Query script to test the vector search index.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from app.config import get_settings
from app.services.embedding_service import EmbeddingService

class VectorIndexQuerier:
    """Query the vector search index."""
    
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

    async def test_basic_search(self):
        """Test basic text search."""
        print("🔍 Testing basic text search...")
        search_client = await self._get_search_client()
        
        try:
            # Basic text search
            results = search_client.search(
                search_text="project management",
                select=["id", "blob_name", "company", "sow_id"],
                top=5
            )
            
            count = 0
            print(f"Results for 'project management':")
            async for result in results:
                count += 1
                print(f"  {count}. {result['blob_name']} ({result['company']})")
            print(f"Total: {count} results")
                
        except Exception as e:
            print(f"❌ Basic search failed: {e}")

    async def test_vector_search(self, query_text):
        """Test vector similarity search."""
        print(f"🔍 Testing vector search for: '{query_text}'")
        search_client = await self._get_search_client()
        
        try:
            # Generate embedding for the query
            query_embeddings = await self._embedding_service.get_embeddings_batch([query_text])
            if not query_embeddings or not query_embeddings[0]:
                print("❌ Failed to generate query embedding")
                return
            
            # Vector search
            results = search_client.search(
                search_text="",  # Empty for pure vector search
                vector_queries=[
                    {
                        "kind": "vector",
                        "vector": query_embeddings[0],
                        "k_nearest_neighbors": 5,
                        "fields": "content_vector"
                    }
                ],
                select=["id", "blob_name", "company", "sow_id", "full_text"],
                top=5
            )
            
            print(f"Similar documents for '{query_text}':")
            rank = 1
            async for result in results:
                # Show first 200 characters of the text
                text_preview = result.get('full_text', '')[:200] + "..." if len(result.get('full_text', '')) > 200 else result.get('full_text', '')
                print(f"  {rank}. {result['blob_name']} ({result['company']})")
                print(f"     Preview: {text_preview}")
                print()
                rank += 1
                
        except Exception as e:
            print(f"❌ Vector search failed: {e}")

    async def test_hybrid_search(self, query_text):
        """Test hybrid search (text + vector)."""
        print(f"🔍 Testing hybrid search for: '{query_text}'")
        search_client = await self._get_search_client()
        
        try:
            # Generate embedding for the query
            query_embeddings = await self._embedding_service.get_embeddings_batch([query_text])
            if not query_embeddings or not query_embeddings[0]:
                print("❌ Failed to generate query embedding")
                return
            
            # Hybrid search (text + vector)
            results = search_client.search(
                search_text=query_text,  # Text search
                vector_queries=[
                    {
                        "kind": "vector",
                        "vector": query_embeddings[0],
                        "k_nearest_neighbors": 5,
                        "fields": "content_vector"
                    }
                ],
                select=["id", "blob_name", "company", "sow_id", "full_text"],
                top=5
            )
            
            print(f"Hybrid search results for '{query_text}':")
            rank = 1
            async for result in results:
                text_preview = result.get('full_text', '')[:200] + "..." if len(result.get('full_text', '')) > 200 else result.get('full_text', '')
                print(f"  {rank}. {result['blob_name']} ({result['company']})")
                print(f"     Preview: {text_preview}")
                print()
                rank += 1
                
        except Exception as e:
            print(f"❌ Hybrid search failed: {e}")

    async def test_filtered_search(self):
        """Test search with filters."""
        print("🔍 Testing filtered search (Company 2 only)...")
        search_client = await self._get_search_client()
        
        try:
            # Search with company filter
            results = search_client.search(
                search_text="retainer work",
                filter="company eq 'company_2'",
                select=["id", "blob_name", "company", "sow_id"],
                top=10
            )
            
            print(f"Company 2 documents containing 'retainer work':")
            count = 0
            async for result in results:
                count += 1
                print(f"  {count}. {result['blob_name']} ({result['company']})")
            print(f"Total: {count} results")
                
        except Exception as e:
            print(f"❌ Filtered search failed: {e}")

    async def get_index_stats(self):
        """Get index statistics."""
        print("📊 Getting index statistics...")
        search_client = await self._get_search_client()
        
        try:
            # Count documents by doing a simple search
            results = search_client.search(search_text="*", select=["id"], top=1000)
            count = 0
            async for result in results:
                count += 1
            print(f"  Document count: {count}")
            print(f"  Index name: {self._index_name}")
        except Exception as e:
            print(f"❌ Failed to get stats: {e}")

async def main():
    """Run all tests."""
    querier = VectorIndexQuerier()
    
    print("=" * 60)
    print("🔍 VECTOR SEARCH INDEX TESTING")
    print("=" * 60)
    
    # Get index stats
    await querier.get_index_stats()
    print()
    
    # Test basic search
    await querier.test_basic_search()
    print()
    
    # Test vector searches with different queries
    test_queries = [
        "project management marketing strategy",
        "hospitality events retainer",
        "olympics platform",
        "measurement analytics",
        "partnerships platforms"
    ]
    
    for query in test_queries:
        await querier.test_vector_search(query)
        print()
    
    # Test hybrid search
    await querier.test_hybrid_search("retainer work hospitality")
    print()
    
    # Test filtered search
    await querier.test_filtered_search()
    
    print("=" * 60)
    print("✅ Testing complete!")

if __name__ == "__main__":
    asyncio.run(main())
