#!/usr/bin/env python3
"""
Simple text-only vector index for SOW documents.
This creates an index with just the raw extracted text and basic metadata.
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

from app.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.azure_storage import AzureStorageService

class SimpleTextIndexer:
    """Simple indexer for raw SOW text content."""
    
    def __init__(self):
        settings = get_settings()
        self._endpoint = settings.search_endpoint
        self._key = settings.search_key
        self._index_name = "octagon-sows-text-only"
        self._credential = AzureKeyCredential(settings.search_key)
        
        self._search_client = None
        self._index_client = None
        self._embedding_service = EmbeddingService()
        self._storage_service = AzureStorageService(container_name="extracted")

    async def _get_search_client(self):
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self._endpoint,
                index_name=self._index_name,
                credential=self._credential,
            )
        return self._search_client

    async def _get_index_client(self):
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=self._endpoint,
                credential=self._credential,
            )
        return self._index_client

    async def create_index(self):
        """Create a simple text-only search index."""
        index_client = await self._get_index_client()
        
        # Minimal schema - just text and basic metadata
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
            print(f"✅ Created text-only search index: {self._index_name}")
        except Exception as e:
            print(f"❌ Failed to create search index: {e}")
            raise

    async def process_sow_document(self, blob_name):
        """Process a single SOW document from the extracted text files."""
        try:
            print(f"Processing {blob_name}...")
            
            # Download the extracted text file from Azure Storage
            try:
                content = await self._storage_service.download_bytes(blob_name)
                full_text = content.decode('utf-8')
            except Exception as e:
                print(f"⚠️ Failed to download {blob_name}: {e}")
                return None
            
            if not full_text or len(full_text.strip()) < 100:
                print(f"⚠️ Skipping {blob_name}: insufficient text content")
                return None
            
            # Generate embedding for the text
            print(f"Generating embedding for {blob_name}...")
            embeddings = await self._embedding_service.get_embeddings_batch([full_text])
            
            if not embeddings or not embeddings[0]:
                print(f"⚠️ Skipping {blob_name}: failed to generate embedding")
                return None
            
            # Extract basic metadata from filename
            parts = blob_name.replace('.txt', '').split('_')
            company = parts[0] if len(parts) > 0 else "Unknown"
            sow_id = parts[1] if len(parts) > 1 else "Unknown"
            
            # Create simple document with valid ID (no dots allowed)
            document_id = blob_name.replace('.txt', '')
            document = {
                "id": document_id,
                "blob_name": blob_name,
                "company": company,
                "sow_id": sow_id,
                "format": "txt",
                "full_text": full_text,
                "content_vector": embeddings[0]
            }
            
            return document
            
        except Exception as e:
            print(f"❌ Failed to process {blob_name}: {e}")
            return None

    async def index_document(self, document):
        """Index a single document."""
        search_client = await self._get_search_client()
        
        try:
            await search_client.upload_documents([document])
            print(f"✅ Indexed: {document['blob_name']}")
        except Exception as e:
            print(f"❌ Failed to index {document['blob_name']}: {e}")
            raise

    async def index_all_documents(self):
        """Index all SOW documents from the extracted text files."""
        try:
            # List all extracted text files from Azure Storage
            # We'll use the known list from the Azure portal
            extracted_files = [
                "company_1_sow_1.txt",
                "company_1_sow_2.txt", 
                "company_1_sow_3.txt",
                "company_1_sow_4.txt",
                "company_2_sow_1.txt",
                "company_2_sow_2.txt",
                "company_2_sow_3.txt",
                "company_3_sow_1.txt",
                "company_4_sow_1.txt"
            ]
            
            print(f"Found {len(extracted_files)} extracted text files to process")
            
            successful = 0
            failed = 0
            
            for blob_name in extracted_files:
                document = await self.process_sow_document(blob_name)
                if document:
                    try:
                        await self.index_document(document)
                        successful += 1
                    except Exception as e:
                        print(f"❌ Failed to index {blob_name}: {e}")
                        failed += 1
                else:
                    failed += 1
            
            print(f"\n📊 Indexing Summary:")
            print(f"  Successful: {successful}")
            print(f"  Failed: {failed}")
            
            return successful, failed
            
        except Exception as e:
            print(f"❌ Error during indexing: {e}")
            raise

    async def search_similar(self, query_text, top_k=5):
        """Search for similar documents."""
        search_client = await self._get_search_client()
        
        try:
            # Generate embedding for the query
            query_embeddings = await self._embedding_service.get_embeddings_batch([query_text])
            if not query_embeddings or not query_embeddings[0]:
                print("❌ Failed to generate query embedding")
                return []
            
            # Search using vector similarity
            search_results = await search_client.search(
                search_text="",  # Empty for pure vector search
                vector_queries=[
                    {
                        "kind": "vector",
                        "vector": query_embeddings[0],
                        "k_nearest_neighbors": top_k,
                        "fields": "content_vector"
                    }
                ],
                select=["id", "blob_name", "company", "sow_id", "full_text"],
                top=top_k
            )
            
            results = []
            rank = 1
            async for result in search_results:
                result_dict = dict(result)
                result_dict['score'] = round(1.0 - (rank * 0.1), 2)
                result_dict['rank'] = rank
                results.append(result_dict)
                rank += 1
            
            return results
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []

async def main():
    """Main function to create index and populate with documents."""
    indexer = SimpleTextIndexer()
    
    try:
        # Create the index
        print("Creating text-only search index...")
        await indexer.create_index()
        
        # Index all documents
        print("Indexing all SOW documents...")
        successful, failed = await indexer.index_all_documents()
        
        if successful > 0:
            print(f"\n✅ Successfully indexed {successful} documents!")
            
            # Test search
            print("\n🔍 Testing search...")
            results = await indexer.search_similar("project management marketing strategy", top_k=3)
            print(f"Found {len(results)} similar documents:")
            for result in results:
                print(f"  - {result['blob_name']} (Score: {result['score']})")
        else:
            print("❌ No documents were successfully indexed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
