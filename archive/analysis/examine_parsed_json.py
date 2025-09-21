#!/usr/bin/env python3
"""
Script to examine the structure of parsed JSON files in Azure Storage
and design an appropriate Azure Search index schema.
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential

async def examine_parsed_json_files():
    """Examine the structure of parsed JSON files in Azure Storage"""
    
    # Load environment variables
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
    else:
        print("⚠️ .env file not found, using system environment variables")
    
    # Get Azure Storage configuration
    account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
    container_name = "parsed"
    
    if not account_url:
        print("❌ AZURE_STORAGE_ACCOUNT_URL not found in environment variables")
        return
    
    try:
        # Initialize Azure Storage client
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        print(f"🔗 Connected to Azure Storage: {account_url}")
        
        # List all JSON files in the parsed container
        container_client = blob_service_client.get_container_client(container_name)
        print(f"📂 Examining container: {container_name}")
        
        blob_list = []
        async for blob in container_client.list_blobs():
            if blob.name.endswith('.json'):
                blob_list.append(blob.name)
        
        print(f"📄 Found {len(blob_list)} JSON files")
        
        if not blob_list:
            print("❌ No JSON files found in the parsed container")
            return
        
        # Examine the first few files to understand structure
        sample_files = blob_list[:3]  # Examine first 3 files
        all_structures = {}
        
        for blob_name in sample_files:
            print(f"\n🔍 Examining: {blob_name}")
            
            try:
                blob_client = blob_service_client.get_blob_client(
                    container=container_name,
                    blob=blob_name
                )
                
                # Download and parse JSON
                blob_data = await blob_client.download_blob()
                content = await blob_data.readall()
                json_data = json.loads(content.decode('utf-8'))
                
                # Analyze structure
                structure = analyze_json_structure(json_data, blob_name)
                all_structures[blob_name] = structure
                
                print(f"  ✅ Successfully analyzed {blob_name}")
                
            except Exception as e:
                print(f"  ❌ Error analyzing {blob_name}: {e}")
        
        # Generate summary and index schema recommendation
        print("\n" + "="*80)
        print("📊 STRUCTURE ANALYSIS SUMMARY")
        print("="*80)
        
        generate_schema_recommendation(all_structures)
        
    except Exception as e:
        print(f"❌ Error connecting to Azure Storage: {e}")

def analyze_json_structure(data, filename):
    """Analyze the structure of a JSON object"""
    structure = {
        'filename': filename,
        'top_level_keys': list(data.keys()) if isinstance(data, dict) else [],
        'field_types': {},
        'array_fields': {},
        'nested_objects': {}
    }
    
    if isinstance(data, dict):
        for key, value in data.items():
            structure['field_types'][key] = type(value).__name__
            
            if isinstance(value, list):
                structure['array_fields'][key] = {
                    'length': len(value),
                    'item_type': type(value[0]).__name__ if value else 'empty'
                }
                
                # If it's a list of objects, analyze the first item
                if value and isinstance(value[0], dict):
                    structure['array_fields'][key]['item_structure'] = list(value[0].keys())
                    
            elif isinstance(value, dict):
                structure['nested_objects'][key] = list(value.keys())
    
    return structure

def generate_schema_recommendation(structures):
    """Generate Azure Search index schema recommendation based on analyzed structures"""
    
    print("\n🔍 FIELD ANALYSIS:")
    print("-" * 50)
    
    # Collect all unique fields across all files
    all_fields = set()
    field_type_counts = {}
    array_fields = set()
    
    for filename, structure in structures.items():
        print(f"\n📄 {filename}:")
        print(f"  Top-level keys: {structure['top_level_keys']}")
        
        for field, field_type in structure['field_types'].items():
            all_fields.add(field)
            
            if field not in field_type_counts:
                field_type_counts[field] = {}
            field_type_counts[field][field_type] = field_type_counts[field].get(field_type, 0) + 1
            
            if field in structure['array_fields']:
                array_fields.add(field)
                print(f"    {field}: {field_type} (array, {structure['array_fields'][field]['length']} items)")
            else:
                print(f"    {field}: {field_type}")
    
    print(f"\n📋 ALL UNIQUE FIELDS FOUND:")
    print("-" * 50)
    for field in sorted(all_fields):
        type_counts = field_type_counts[field]
        primary_type = max(type_counts, key=type_counts.get)
        print(f"  {field}: {primary_type} ({type_counts})")
        if field in array_fields:
            print(f"    └─ Array field")
    
    print(f"\n🏗️  RECOMMENDED AZURE SEARCH INDEX SCHEMA:")
    print("=" * 80)
    
    # Generate Azure Search index definition
    index_definition = {
        "name": "octagon-sows-parsed",
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
            }
        ]
    }
    
    # Add fields based on analysis
    for field in sorted(all_fields):
        primary_type = max(field_type_counts[field], key=field_type_counts[field].get)
        
        # Map JSON types to Azure Search types
        azure_type = map_json_type_to_azure_search(primary_type, field in array_fields)
        
        field_def = {
            "name": field,
            "type": azure_type,
            "searchable": should_be_searchable(field, primary_type),
            "filterable": should_be_filterable(field, primary_type),
            "sortable": should_be_sortable(field, primary_type),
            "facetable": should_be_facetable(field, primary_type),
            "retrievable": True
        }
        
        # Add analyzer for text fields
        if azure_type == "Edm.String" and should_be_searchable(field, primary_type):
            field_def["analyzer"] = "en.microsoft"
        
        index_definition["fields"].append(field_def)
    
    # Add vector field for semantic search
    index_definition["fields"].append({
        "name": "content_vector",
        "type": "Collection(Edm.Single)",
        "searchable": True,
        "retrievable": False,
        "dimensions": 1536  # OpenAI embedding dimension
    })
    
    print(json.dumps(index_definition, indent=2))

def map_json_type_to_azure_search(json_type, is_array):
    """Map JSON type to Azure Search type"""
    if is_array:
        return "Collection(Edm.String)"  # Most arrays will be strings
    
    type_mapping = {
        'str': 'Edm.String',
        'string': 'Edm.String',
        'int': 'Edm.Int32',
        'integer': 'Edm.Int32',
        'float': 'Edm.Double',
        'double': 'Edm.Double',
        'bool': 'Edm.Boolean',
        'boolean': 'Edm.Boolean',
        'datetime': 'Edm.DateTimeOffset',
        'date': 'Edm.DateTimeOffset',
        'list': 'Collection(Edm.String)',
        'dict': 'Edm.String'  # Store as JSON string
    }
    
    return type_mapping.get(json_type.lower(), 'Edm.String')

def should_be_searchable(field_name, field_type):
    """Determine if a field should be searchable"""
    searchable_fields = ['client_name', 'project_title', 'scope_summary', 'deliverables', 'exclusions']
    return field_name in searchable_fields or field_type == 'str'

def should_be_filterable(field_name, field_type):
    """Determine if a field should be filterable"""
    filterable_fields = ['client_name', 'start_date', 'end_date', 'project_length', 'file_name']
    return field_name in filterable_fields or field_type in ['str', 'int', 'float', 'bool']

def should_be_sortable(field_name, field_type):
    """Determine if a field should be sortable"""
    sortable_fields = ['client_name', 'start_date', 'end_date', 'project_length', 'file_name']
    return field_name in sortable_fields or field_type in ['str', 'int', 'float', 'bool']

def should_be_facetable(field_name, field_type):
    """Determine if a field should be facetable"""
    facetable_fields = ['client_name', 'project_length']
    return field_name in facetable_fields and field_type == 'str'

async def main():
    """Main function"""
    print("🔍 Parsed JSON Structure Analyzer")
    print("=" * 50)
    
    await examine_parsed_json_files()

if __name__ == "__main__":
    asyncio.run(main())
