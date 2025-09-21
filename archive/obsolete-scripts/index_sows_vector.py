#!/usr/bin/env python3
"""
Batch script to index all SOW documents with vector embeddings.

This script will:
1. Create the Azure AI Search index
2. Process all SOW documents in the source container
3. Generate embeddings for both full text and structured data
4. Index documents in the vector database

Usage:
    python index_sows_vector.py [--create-index] [--blob-name BLOB_NAME]
"""

import asyncio
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from app.services.vector_indexer import VectorIndexer, VectorIndexerError


async def main():
    parser = argparse.ArgumentParser(description="Index SOW documents with vector embeddings")
    parser.add_argument("--create-index", action="store_true", help="Create the search index first")
    parser.add_argument("--blob-name", type=str, help="Process a specific blob by name")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    
    args = parser.parse_args()
    
    try:
        indexer = VectorIndexer()
        
        if args.create_index:
            print("Creating vector search index...")
            await indexer.create_index()
            print("✅ Index created successfully")
            return
        
        if args.stats:
            print("Getting index statistics...")
            stats = await indexer.get_index_statistics()
            print(f"📊 Index Statistics:")
            print(f"  Document count: {stats.get('document_count', 'N/A')}")
            print(f"  Storage size: {stats.get('storage_size', 'N/A')} bytes")
            print(f"  Vector index size: {stats.get('vector_index_size', 'N/A')} bytes")
            return
        
        if args.blob_name:
            print(f"Processing single document: {args.blob_name}")
            result = await indexer.index_single_document(args.blob_name)
            print(f"✅ Result: {result}")
        else:
            print("Processing all SOW documents...")
            results = await indexer.index_all_documents()
            
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
            
            if successful:
                print(f"\n✅ Successfully indexed documents:")
                for result in successful:
                    print(f"  - {result['blob_name']} (text: {result.get('text_length', 0)} chars, parsed: {result.get('has_parsed_data', False)})")
    
    except VectorIndexerError as e:
        print(f"❌ Vector indexing error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
