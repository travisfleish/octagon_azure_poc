#!/usr/bin/env python3
"""
Populate Hybrid Vector Index
============================

This script populates the hybrid index with both:
- Full text extractions from the 'extracted' container
- Parsed JSON data from the 'parsed' container
- Multiple vector embeddings for comprehensive search
"""

import os
import json
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential


class HybridIndexPopulator:
    """Populates the hybrid vector index with both full text and parsed data"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.storage_account_url = None
        self.openai_api_key = None
        self.openai_endpoint = None
        self.openai_deployment = None
        self.blob_service_client = None
        self.index_name = "octagon-sows-hybrid"
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
        self.openai_deployment = os.getenv('AOAI_DEPLOYMENT')
        
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
    
    async def get_file_pairs(self):
        """Get matching pairs of parsed JSON and extracted text files"""
        try:
            parsed_container = self.blob_service_client.get_container_client("parsed")
            extracted_container = self.blob_service_client.get_container_client("extracted")
            
            # Get all parsed JSON files
            parsed_files = []
            async for blob in parsed_container.list_blobs():
                if blob.name.endswith('.json'):
                    parsed_files.append(blob.name)
            
            # Get all extracted text files
            extracted_files = []
            async for blob in extracted_container.list_blobs():
                if blob.name.endswith('.txt'):
                    extracted_files.append(blob.name)
            
            # Match files by base name
            file_pairs = []
            for parsed_file in parsed_files:
                base_name = parsed_file.replace('_parsed.json', '')
                matching_txt = f"{base_name}.txt"
                
                if matching_txt in extracted_files:
                    file_pairs.append({
                        'parsed_file': parsed_file,
                        'extracted_file': matching_txt,
                        'base_name': base_name
                    })
                else:
                    print(f"⚠️  No matching text file for {parsed_file}")
            
            print(f"📄 Found {len(file_pairs)} matching file pairs")
            return file_pairs
            
        except Exception as e:
            print(f"❌ Error accessing Azure Storage: {e}")
            return []
    
    async def download_file(self, container_name, blob_name):
        """Download a file from Azure Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            blob_data = await blob_client.download_blob()
            content = await blob_data.readall()
            
            if container_name == "parsed":
                return json.loads(content.decode('utf-8'))
            else:  # extracted
                return content.decode('utf-8')
                
        except Exception as e:
            print(f"❌ Error downloading {container_name}/{blob_name}: {e}")
            return None
    
    def prepare_document_for_hybrid_index(self, json_data, raw_content, embeddings):
        """Prepare a document for the hybrid index"""
        # Use deterministic ID so re-populations overwrite instead of duplicating
        file_name = json_data.get("file_name", "")
        doc_id = file_name or json_data.get("project_title", "") or json_data.get("client_name", "")
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())
        
        # Prepare the document
        document = {
            "id": doc_id,
            "file_name": json_data.get("file_name", ""),
            "extraction_timestamp": json_data.get("extraction_timestamp", ""),
            "client_name": json_data.get("client_name", ""),
            "project_title": json_data.get("project_title", ""),
            "start_date": json_data.get("start_date", ""),
            "end_date": json_data.get("end_date", ""),
            "project_length": json_data.get("project_length", ""),
            "scope_summary": json_data.get("scope_summary", ""),
            "deliverables": json_data.get("deliverables", []),
            "exclusions": json_data.get("exclusions", []),
            "raw_content": raw_content,
            "full_text_vector": embeddings['full_text'],
            "parsed_content_vector": embeddings['parsed_content'],
            "scope_vector": embeddings['scope'],
            "deliverables_vector": embeddings['deliverables']
        }
        
        # Handle staffing_plan - convert objects (minimal schema) to strings suitable for indexing
        staffing_plan = json_data.get("staffing_plan", [])
        staffing_plan_strings = []
        for person in staffing_plan:
            if isinstance(person, dict):
                # Support both old and new schemas
                name = person.get("name") or "N/A"
                title = person.get("title") or person.get("role") or ""
                hrs_pct = person.get("hours_pct")
                hrs = person.get("hours")
                # Fallback to legacy 'allocation'
                allocation = None
                if hrs_pct is not None:
                    allocation = f"{hrs_pct:.1f}%"
                elif hrs is not None:
                    allocation = f"{hrs:.1f} hours"
                else:
                    allocation = person.get("allocation") or ""
                staffing_plan_strings.append(
                    " — ".join([p for p in [str(name), str(title), allocation] if p])
                )
            else:
                staffing_plan_strings.append(str(person))

        document["staffing_plan"] = staffing_plan_strings
        
        return document
    
    def upload_documents_to_index(self, documents):
        """Upload documents to the hybrid index"""
        print(f"📤 Uploading {len(documents)} documents to hybrid index...")
        
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
            
            # Use mergeOrUpload to upsert and avoid duplicates
            payload = {"value": [{"@search.action": "mergeOrUpload", **doc} for doc in batch]}
            
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
        """Populate the hybrid index with both full text and parsed data"""
        print("🚀 Starting hybrid index population...")
        
        # Initialize clients
        await self.initialize_clients()
        
        # Get matching file pairs
        file_pairs = await self.get_file_pairs()
        if not file_pairs:
            print("❌ No matching file pairs found to process")
            return False
        
        # Process each file pair
        documents = []
        for i, pair in enumerate(file_pairs, 1):
            print(f"  📄 Processing {i}/{len(file_pairs)}: {pair['base_name']}")
            
            # Download both files
            json_data = await self.download_file("parsed", pair['parsed_file'])
            raw_content = await self.download_file("extracted", pair['extracted_file'])
            
            if not json_data or not raw_content:
                print(f"    ❌ Failed to download files for {pair['base_name']}")
                continue
            
            # Create content for different embeddings
            # Flatten staffing strings here (mirror logic from prepare_document_for_hybrid_index)
            staffing_plan = json_data.get("staffing_plan", [])
            staffing_plan_strings = []
            for person in staffing_plan:
                if isinstance(person, dict):
                    name = person.get("name") or "N/A"
                    title = person.get("title") or person.get("role") or ""
                    hrs_pct = person.get("hours_pct")
                    hrs = person.get("hours")
                    if hrs_pct is not None:
                        allocation = f"{hrs_pct:.1f}%"
                    elif hrs is not None:
                        allocation = f"{hrs:.1f} hours"
                    else:
                        allocation = person.get("allocation") or ""
                    staffing_plan_strings.append(" — ".join([p for p in [str(name), str(title), allocation] if p]))
                else:
                    staffing_plan_strings.append(str(person))

            parsed_content_parts = [
                json_data.get("client_name", ""),
                json_data.get("project_title", ""),
                json_data.get("scope_summary", ""),
                " ".join(json_data.get("deliverables", [])),
                # Use flattened staffing strings for better embedding
                " ".join(staffing_plan_strings),
                " ".join(json_data.get("exclusions", []))
            ]
            parsed_content_text = " ".join([part for part in parsed_content_parts if part])
            
            # Generate embeddings
            print(f"    🔄 Generating embeddings...")
            embeddings = {}
            
            # Full text embedding
            embeddings['full_text'] = await self.get_embedding(raw_content)
            
            # Parsed content embedding
            embeddings['parsed_content'] = await self.get_embedding(parsed_content_text)
            
            # Scope embedding
            embeddings['scope'] = await self.get_embedding(json_data.get("scope_summary", ""))
            
            # Deliverables embedding
            embeddings['deliverables'] = await self.get_embedding(" ".join(json_data.get("deliverables", [])))
            
            if not all(embeddings.values()):
                print(f"    ❌ Failed to generate embeddings for {pair['base_name']}")
                continue
            
            # Prepare document for index
            document = self.prepare_document_for_hybrid_index(json_data, raw_content, embeddings)
            documents.append(document)
            
            print(f"    ✅ Processed: {json_data.get('client_name', 'Unknown')} - {json_data.get('project_title', 'Unknown')}")
        
        if documents:
            # Upload documents to index
            uploaded_count = self.upload_documents_to_index(documents)
            print(f"✅ Successfully populated hybrid index with {uploaded_count} documents")
            return True
        else:
            print("❌ No documents to upload")
            return False


async def main():
    """Main function"""
    print("🚀 Hybrid Index Population")
    print("=" * 50)
    
    try:
        populator = HybridIndexPopulator()
        success = await populator.populate_index()
        
        if success:
            print("\n🎉 Hybrid index population completed successfully!")
            print("📝 Next steps:")
            print("1. Test hybrid search with both full text and parsed data")
            print("2. Update Streamlit app to use hybrid search")
            print("3. Compare results with previous search methods")
        else:
            print("\n❌ Hybrid index population failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
