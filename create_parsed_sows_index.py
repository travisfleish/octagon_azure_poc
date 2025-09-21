#!/usr/bin/env python3
"""
Script to create and populate a new Azure Search index for parsed SOW JSON data.
This script reads parsed JSON files from the Azure Storage 'parsed' container
and creates a searchable index with structured SOW data.
"""

import os
import json
import asyncio
import uuid
from pathlib import Path
from dotenv import load_dotenv
import requests
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential

class ParsedSOWsIndexManager:
    """Manages the creation and population of Azure Search index for parsed SOW data"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.storage_account_url = None
        self.index_name = "octagon-sows-parsed"
        
    def load_environment(self):
        """Load environment variables from .env file"""
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment from {env_path}")
        else:
            print("⚠️ .env file not found, using system environment variables")
        
        self.search_endpoint = os.getenv('SEARCH_ENDPOINT')
        self.search_key = os.getenv('SEARCH_KEY')
        self.storage_account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        
        if not self.search_endpoint or not self.search_key:
            raise ValueError("Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
        
        # Remove trailing slash if present
        self.search_endpoint = self.search_endpoint.rstrip('/')
    
    def get_index_definition(self):
        """Get the Azure Search index definition for parsed SOW data"""
        return {
            "name": self.index_name,
            "fields": [
                {
                    "name": "id",
                    "type": "Edm.String",
                    "key": True,
                    "searchable": False,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "client_name",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": True,
                    "facetable": True,
                    "retrievable": True,
                    "analyzer": "en.microsoft"
                },
                {
                    "name": "project_title",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True,
                    "analyzer": "en.microsoft"
                },
                {
                    "name": "start_date",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "end_date",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "project_length",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": True,
                    "facetable": True,
                    "retrievable": True,
                    "analyzer": "en.microsoft"
                },
                {
                    "name": "scope_summary",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True,
                    "analyzer": "en.microsoft"
                },
                {
                    "name": "deliverables",
                    "type": "Collection(Edm.String)",
                    "searchable": True,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "exclusions",
                    "type": "Collection(Edm.String)",
                    "searchable": True,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "staffing_plan",
                    "type": "Collection(Edm.String)",
                    "searchable": True,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "file_name",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True,
                    "analyzer": "en.microsoft"
                },
                {
                    "name": "extraction_timestamp",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True
                },
            ]
        }
    
    def create_index(self):
        """Create the Azure Search index"""
        print(f"🏗️  Creating Azure Search index: {self.index_name}")
        
        index_definition = self.get_index_definition()
        url = f"{self.search_endpoint}/indexes?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        try:
            response = requests.post(url, headers=headers, json=index_definition)
            
            if response.status_code == 201:
                print(f"✅ Successfully created index: {self.index_name}")
                return True
            elif response.status_code == 409:
                print(f"⚠️  Index {self.index_name} already exists")
                return True
            else:
                print(f"❌ Error creating index: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating index: {e}")
            return False
    
    def delete_index(self):
        """Delete the Azure Search index if it exists"""
        print(f"🗑️  Deleting existing index: {self.index_name}")
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        try:
            response = requests.delete(url, headers=headers)
            
            if response.status_code == 204:
                print(f"✅ Successfully deleted index: {self.index_name}")
                return True
            elif response.status_code == 404:
                print(f"⚠️  Index {self.index_name} does not exist")
                return True
            else:
                print(f"❌ Error deleting index: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting index: {e}")
            return False
    
    async def get_parsed_json_files(self):
        """Get all parsed JSON files from Azure Storage"""
        if not self.storage_account_url:
            print("❌ AZURE_STORAGE_ACCOUNT_URL not found - cannot access parsed files")
            return []
        
        try:
            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(account_url=self.storage_account_url, credential=credential)
            
            container_client = blob_service_client.get_container_client("parsed")
            
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
            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(account_url=self.storage_account_url, credential=credential)
            
            blob_client = blob_service_client.get_blob_client(
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
    
    def prepare_document_for_index(self, json_data):
        """Prepare a JSON document for indexing in Azure Search"""
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
            "extraction_timestamp": json_data.get("extraction_timestamp", "")
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
    
    def upload_documents(self, documents):
        """Upload documents to Azure Search index"""
        print(f"📤 Uploading {len(documents)} documents to index...")
        
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
        """Populate the index with data from parsed JSON files"""
        print("📥 Populating index with parsed JSON data...")
        
        # Get list of JSON files
        json_files = await self.get_parsed_json_files()
        if not json_files:
            print("❌ No JSON files found to process")
            return False
        
        # Download and process each file
        documents = []
        for i, blob_name in enumerate(json_files, 1):
            print(f"  📄 Processing {i}/{len(json_files)}: {blob_name}")
            
            json_data = await self.download_json_file(blob_name)
            if json_data:
                document = self.prepare_document_for_index(json_data)
                documents.append(document)
                print(f"    ✅ Processed: {json_data.get('client_name', 'Unknown')} - {json_data.get('project_title', 'Unknown')}")
            else:
                print(f"    ❌ Failed to process {blob_name}")
        
        if documents:
            # Upload documents to index
            uploaded_count = self.upload_documents(documents)
            print(f"✅ Successfully populated index with {uploaded_count} documents")
            return True
        else:
            print("❌ No documents to upload")
            return False
    
    async def run(self, recreate_index=False):
        """Main execution method"""
        print("🚀 Parsed SOWs Index Manager")
        print("=" * 50)
        
        # Load environment
        self.load_environment()
        
        # Delete existing index if requested
        if recreate_index:
            self.delete_index()
        
        # Create index
        if not self.create_index():
            print("❌ Failed to create index")
            return False
        
        # Populate index
        if not await self.populate_index():
            print("❌ Failed to populate index")
            return False
        
        print("\n✅ Index creation and population completed successfully!")
        return True

async def main():
    """Main function"""
    manager = ParsedSOWsIndexManager()
    
    # Ask user if they want to recreate the index
    print("Options:")
    print("1. Create new index (will fail if index already exists)")
    print("2. Recreate index (delete existing and create new)")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "2":
        await manager.run(recreate_index=True)
    else:
        await manager.run(recreate_index=False)

if __name__ == "__main__":
    asyncio.run(main())
