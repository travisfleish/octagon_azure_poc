#!/usr/bin/env python3
"""
Populate Vector Index with Embeddings
====================================

This script:
1. Downloads parsed SOW data from Azure Storage
2. Generates vector embeddings using OpenAI
3. Populates the vector-enabled search index
"""

import os
import json
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential
# Using direct REST API instead of OpenAI client


class VectorIndexPopulator:
    """Populates the vector index with embeddings"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.storage_account_url = None
        self.openai_client = None
        self.blob_service_client = None
        self.index_name = "octagon-sows-vector"
        self._load_environment()
    
    def _load_environment(self):
        """Load environment variables"""
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        self.search_endpoint = os.getenv('SEARCH_ENDPOINT')
        self.search_key = os.getenv('SEARCH_KEY')
        self.storage_account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        self.openai_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.openai_deployment = os.getenv('AOAI_DEPLOYMENT')  # Use embeddings deployment
        
        if not all([self.search_endpoint, self.search_key, self.storage_account_url, 
                   self.openai_api_key, self.openai_endpoint, self.openai_deployment]):
            raise ValueError("Missing required environment variables")
        
        # Remove trailing slash if present
        self.search_endpoint = self.search_endpoint.rstrip('/')
    
    async def initialize_clients(self):
        """Initialize Azure Storage client"""
        # Initialize Azure Storage client
        credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(
            account_url=self.storage_account_url, 
            credential=credential
        )
        
        print("✅ Initialized Azure Storage client")
    
    async def get_embedding(self, text: str) -> list:
        """Get vector embedding for text using OpenAI REST API"""
        try:
            import aiohttp
            
            url = f"{self.openai_endpoint}openai/deployments/{self.openai_deployment}/embeddings?api-version=2024-08-01-preview"
            headers = {
                'api-key': self.openai_api_key,
                'Content-Type': 'application/json'
            }
            data = {
                'input': text
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['data'][0]['embedding']
                    else:
                        error_text = await response.text()
                        print(f"❌ Error getting embedding: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"❌ Error getting embedding: {e}")
            return None
    
    async def get_parsed_json_files(self):
        """Get all parsed JSON files from Azure Storage"""
        try:
            container_client = self.blob_service_client.get_container_client("parsed")
            
            json_files = []
            async for blob in container_client.list_blobs():
                if blob.name.endswith('.json'):
                    json_files.append(blob.name)
            
            print(f"📄 Found {len(json_files)} JSON files in parsed container")
            return json_files
            
        except Exception as e:
            print(f"❌ Error accessing Azure Storage: {e}")
            return []
    
    async def download_json_file(self, blob_name):
        """Download and parse a JSON file from Azure Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container="parsed",
                blob=blob_name
            )
            
            blob_data = await blob_client.download_blob()
            content = await blob_data.readall()
            json_data = json.loads(content.decode('utf-8'))
            
            return json_data
            
        except Exception as e:
            print(f"❌ Error downloading {blob_name}: {e}")
            return None
    
    def prepare_document_for_vector_index(self, json_data, content_vector, scope_vector, deliverables_vector):
        """Prepare a JSON document for the vector index"""
        import uuid
        
        # Create a unique ID
        doc_id = str(uuid.uuid4())
        
        # Prepare the document
        document = {
            "id": doc_id,
            "client_name": json_data.get("client_name") or "",
            "project_title": json_data.get("project_title", ""),
            "start_date": json_data.get("start_date") or "",
            "end_date": json_data.get("end_date") or "",
            "project_length": json_data.get("project_length", ""),
            "scope_summary": json_data.get("scope_summary", ""),
            "deliverables": json_data.get("deliverables", []),
            "exclusions": json_data.get("exclusions", []),
            "file_name": json_data.get("file_name", ""),
            "extraction_timestamp": json_data.get("extraction_timestamp", ""),
            "content_vector": content_vector,
            "scope_vector": scope_vector,
            "deliverables_vector": deliverables_vector
        }
        
        # Handle staffing_plan - convert objects to strings
        staffing_plan = json_data.get("staffing_plan", [])
        staffing_plan_strings = []
        for person in staffing_plan:
            if isinstance(person, dict):
                name = person.get("name", "N/A")
                role = person.get("role", "N/A")
                allocation = person.get("allocation", "N/A")
                staffing_plan_strings.append(f"{name} ({role}): {allocation}")
            else:
                staffing_plan_strings.append(str(person))
        
        document["staffing_plan"] = staffing_plan_strings
        
        return document
    
    def upload_documents_to_index(self, documents):
        """Upload documents to the vector index"""
        print(f"📤 Uploading {len(documents)} documents to vector index...")
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/index?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Azure Search accepts up to 1000 documents per batch
        batch_size = 1000
        uploaded_count = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            payload = {
                "value": batch
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    batch_uploaded = len([d for d in result.get('value', []) if d.get('status')])
                    uploaded_count += batch_uploaded
                    print(f"  ✅ Uploaded batch {i//batch_size + 1}: {batch_uploaded}/{len(batch)} documents")
                else:
                    print(f"  ❌ Error uploading batch {i//batch_size + 1}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"  ❌ Error uploading batch {i//batch_size + 1}: {e}")
        
        print(f"📊 Total documents uploaded: {uploaded_count}/{len(documents)}")
        return uploaded_count
    
    async def populate_index(self):
        """Populate the vector index with embeddings"""
        print("🚀 Starting vector index population...")
        
        # Initialize clients
        await self.initialize_clients()
        
        # Get list of JSON files
        json_files = await self.get_parsed_json_files()
        if not json_files:
            print("❌ No JSON files found to process")
            return False
        
        # Process each file
        documents = []
        for i, blob_name in enumerate(json_files, 1):
            print(f"  📄 Processing {i}/{len(json_files)}: {blob_name}")
            
            json_data = await self.download_json_file(blob_name)
            if not json_data:
                print(f"    ❌ Failed to download {blob_name}")
                continue
            
            # Create content for embedding
            content_parts = [
                json_data.get("client_name", ""),
                json_data.get("project_title", ""),
                json_data.get("scope_summary", ""),
                " ".join(json_data.get("deliverables", [])),
                " ".join([str(item) for item in json_data.get("staffing_plan", [])]),
                " ".join(json_data.get("exclusions", []))
            ]
            content_text = " ".join([part for part in content_parts if part])
            
            # Generate embeddings
            print(f"    🔄 Generating embeddings...")
            content_vector = await self.get_embedding(content_text)
            scope_vector = await self.get_embedding(json_data.get("scope_summary", ""))
            deliverables_vector = await self.get_embedding(" ".join(json_data.get("deliverables", [])))
            
            if not all([content_vector, scope_vector, deliverables_vector]):
                print(f"    ❌ Failed to generate embeddings for {blob_name}")
                continue
            
            # Prepare document for index
            document = self.prepare_document_for_vector_index(
                json_data, content_vector, scope_vector, deliverables_vector
            )
            documents.append(document)
            
            print(f"    ✅ Processed: {json_data.get('client_name', 'Unknown')} - {json_data.get('project_title', 'Unknown')}")
        
        if documents:
            # Upload documents to index
            uploaded_count = self.upload_documents_to_index(documents)
            print(f"✅ Successfully populated vector index with {uploaded_count} documents")
            return True
        else:
            print("❌ No documents to upload")
            return False


async def main():
    """Main function"""
    print("🚀 Vector Index Population")
    print("=" * 50)
    
    try:
        populator = VectorIndexPopulator()
        success = await populator.populate_index()
        
        if success:
            print("\n🎉 Vector index population completed successfully!")
            print("📝 Next steps:")
            print("1. Test semantic search with vector embeddings")
            print("2. Update Streamlit app to use vector search")
        else:
            print("\n❌ Vector index population failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
