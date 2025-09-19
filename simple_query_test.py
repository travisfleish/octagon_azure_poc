#!/usr/bin/env python3
"""
Simple query test for the vector search index.
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

async def test_vector_search():
    """Test the vector search index."""
    
    # Setup
    settings = get_settings()
    search_client = SearchClient(
        endpoint=settings.search_endpoint,
        index_name="octagon-sows-text-only",
        credential=AzureKeyCredential(settings.search_key),
    )
    embedding_service = EmbeddingService()
    
    print("🔍 Testing Vector Search Index")
    print("=" * 50)
    
    # Test 1: Basic text search
    print("\n1. Basic Text Search for 'project management':")
    try:
        results = await search_client.search(
            search_text="project management",
            select=["id", "blob_name", "company", "sow_id"],
            top=5
        )
        
        count = 0
        async for result in results:
            count += 1
            print(f"   {count}. {result['blob_name']} ({result['company']})")
        print(f"   Total: {count} results")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Vector search
    print("\n2. Vector Search for 'hospitality events':")
    try:
        # Generate embedding
        query_embeddings = await embedding_service.get_embeddings_batch(["hospitality events"])
        
        results = await search_client.search(
            search_text="",
            vector_queries=[
                {
                    "kind": "vector",
                    "vector": query_embeddings[0],
                    "k_nearest_neighbors": 3,
                    "fields": "content_vector"
                }
            ],
            select=["id", "blob_name", "company", "sow_id", "full_text"],
            top=3
        )
        
        count = 0
        async for result in results:
            count += 1
            text_preview = result.get('full_text', '')[:150] + "..."
            print(f"   {count}. {result['blob_name']} ({result['company']})")
            print(f"      Preview: {text_preview}")
        print(f"   Total: {count} results")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Hybrid search
    print("\n3. Hybrid Search for 'retainer work':")
    try:
        # Generate embedding
        query_embeddings = await embedding_service.get_embeddings_batch(["retainer work"])
        
        results = await search_client.search(
            search_text="retainer work",
            vector_queries=[
                {
                    "kind": "vector",
                    "vector": query_embeddings[0],
                    "k_nearest_neighbors": 3,
                    "fields": "content_vector"
                }
            ],
            select=["id", "blob_name", "company", "sow_id"],
            top=3
        )
        
        count = 0
        async for result in results:
            count += 1
            print(f"   {count}. {result['blob_name']} ({result['company']})")
        print(f"   Total: {count} results")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Filtered search
    print("\n4. Filtered Search (Company 2 only):")
    try:
        results = await search_client.search(
            search_text="olympics",
            filter="company eq 'company_2'",
            select=["id", "blob_name", "company", "sow_id"],
            top=5
        )
        
        count = 0
        async for result in results:
            count += 1
            print(f"   {count}. {result['blob_name']} ({result['company']})")
        print(f"   Total: {count} results")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: List all documents
    print("\n5. All Documents in Index:")
    try:
        results = await search_client.search(
            search_text="*",
            select=["id", "blob_name", "company", "sow_id"],
            top=10
        )
        
        count = 0
        async for result in results:
            count += 1
            print(f"   {count}. {result['blob_name']} ({result['company']})")
        print(f"   Total: {count} documents indexed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")

if __name__ == "__main__":
    asyncio.run(test_vector_search())
