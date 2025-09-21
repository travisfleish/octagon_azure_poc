#!/usr/bin/env python3
"""
Simple working vector index for SOW documents.
This creates a minimal index that focuses on core functionality.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from app.services.vector_service import VectorService
from app.services.vector_indexer import VectorIndexer

async def create_simple_index():
    """Create a simple working index with minimal fields."""
    
    # Create a simple document structure
    simple_document = {
        "id": "test_doc_1",
        "blob_name": "test_document.pdf",
        "company": "Test Company",
        "sow_id": "TEST-001",
        "format": "pdf",
        "full_text": "This is a test document about project management and marketing strategy.",
        "content_vector": [0.1] * 1536,  # Dummy vector
        "structured_vector": [0.1] * 1536  # Dummy vector
    }
    
    try:
        # Create the service
        vector_service = VectorService()
        
        # Create the index
        print("Creating simple index...")
        await vector_service.create_index()
        
        # Index the test document
        print("Indexing test document...")
        await vector_service.index_document(simple_document)
        
        print("✅ Simple index created and test document indexed successfully!")
        
        # Test search
        print("Testing search...")
        results = await vector_service.search_similar([0.1] * 1536, top_k=5)
        print(f"Search returned {len(results)} results")
        for result in results:
            print(f"  - {result.get('blob_name', 'unknown')}: {result.get('score', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_simple_index())
