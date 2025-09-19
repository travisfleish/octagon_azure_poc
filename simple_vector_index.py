#!/usr/bin/env python3
"""
Simple vector indexing script that creates a minimal schema and indexes text files.
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
from app.services.embedding_service import EmbeddingService


async def create_simple_index():
    """Create a simple search index with minimal fields."""
    try:
        vector_service = VectorService()
        
        # Create a simple index schema
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SearchField,
            SearchFieldDataType,
            SimpleField,
            SearchableField,
            VectorSearch,
            HnswAlgorithmConfiguration,
            VectorSearchProfile,
            VectorSearchAlgorithmKind,
            VectorSearchAlgorithmMetric,
        )
        
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="blob_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="company", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="sow_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="format", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="full_text", type=SearchFieldDataType.String),
            SearchableField(name="scope_bullets", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchableField(name="deliverables", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchableField(name="roles_detected", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,
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
            name="octagon-sows-simple",
            fields=fields,
            vector_search=vector_search,
        )
        
        # Update the index name in the service
        vector_service._index_name = "octagon-sows-simple"
        
        # Create the index
        index_client = await vector_service._get_index_client()
        await index_client.create_or_update_index(search_index)
        print("✅ Created simple search index: octagon-sows-simple")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create simple index: {e}")
        return False


async def index_text_files_simple():
    """Index text files with the simple schema."""
    try:
        vector_service = VectorService()
        vector_service._index_name = "octagon-sows-simple"
        embedding_service = EmbeddingService()
        
        # Get container clients
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient
        
        cred = DefaultAzureCredential()
        blob_service = BlobServiceClient(
            account_url="https://octagonstaffingstg5nww.blob.core.windows.net/",
            credential=cred
        )
        
        extracted_container = blob_service.get_container_client("extracted")
        
        # List all text files
        text_files = []
        for blob in extracted_container.list_blobs():
            if blob.name.endswith('.txt'):
                text_files.append(blob.name)
        
        print(f"Found {len(text_files)} text files to process")
        
        results = []
        for text_file in text_files:
            try:
                print(f"Processing: {text_file}")
                
                # Download the text content
                blob_client = extracted_container.get_blob_client(text_file)
                text_content = blob_client.download_blob().readall().decode('utf-8')
                
                # Generate embedding
                embedding = await embedding_service.get_embedding(text_content)
                
                # Create a simple document
                blob_name = text_file.replace('.txt', '')
                document = {
                    "id": blob_name,
                    "blob_name": blob_name,
                    "company": None,
                    "sow_id": None,
                    "format": "txt",
                    "full_text": text_content,
                    "scope_bullets": [],
                    "deliverables": [],
                    "roles_detected": [],
                    "content_vector": embedding,
                }
                
                # Index the document
                await vector_service.index_document(document)
                
                results.append({
                    "blob_name": blob_name,
                    "status": "success",
                    "text_length": len(text_content)
                })
                
                print(f"✅ Successfully indexed: {blob_name}")
                
            except Exception as e:
                print(f"❌ Failed to process {text_file}: {e}")
                results.append({
                    "blob_name": text_file,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Print summary
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "failed"]
        
        print(f"\n📊 Processing Summary:")
        print(f"  Total documents: {len(results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        
        if failed:
            print(f"\n❌ Failed documents:")
            for result in failed:
                print(f"  - {result['blob_name']}: {result.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []


async def main():
    print("Creating simple vector index...")
    success = await create_simple_index()
    
    if success:
        print("\nIndexing text files...")
        await index_text_files_simple()
    else:
        print("Failed to create index, skipping indexing")


if __name__ == "__main__":
    asyncio.run(main())
