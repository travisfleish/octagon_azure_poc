#!/usr/bin/env python3
"""
Simple script to index just the extracted text files with vector embeddings.
This bypasses the complex parsed JSON structure to isolate the issue.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from app.services.vector_indexer import VectorIndexer, VectorIndexerError


async def index_text_files():
    """Index just the text files from the extracted container."""
    try:
        indexer = VectorIndexer()
        
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
                
                # Create a simple document with just the text content
                blob_name = text_file.replace('.txt', '')
                
                # Generate embeddings for the text content
                vectors = await indexer._embedding_service.create_document_vectors(
                    blob_name, text_content, None  # No parsed data
                )
                
                # Create a simple document
                document = {
                    "id": blob_name,
                    "blob_name": blob_name,
                    "company": None,
                    "sow_id": None,
                    "format": "txt",
                    "created_at": "2025-09-19T13:00:00Z",
                    
                    # Text content
                    "full_text": text_content,
                    "scope_bullets": [],
                    "deliverables": [],
                    "roles_detected": [],
                    "assumptions": [],
                    
                    # Term information
                    "term_start": None,
                    "term_end": None,
                    "term_months": None,
                    
                    # Units - use null instead of empty arrays for Azure Search
                    "explicit_hours": None,
                    "fte_pct": None,
                    
                    # Vectors
                    "content_vector": vectors["content_vector"],
                    "structured_vector": vectors["structured_vector"],
                    
                    # Metadata
                    "has_llm_parsing": False,
                    "text_length": len(text_content),
                }
                
                # Index the document
                await indexer._vector_service.index_document(document)
                
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


if __name__ == "__main__":
    asyncio.run(index_text_files())
