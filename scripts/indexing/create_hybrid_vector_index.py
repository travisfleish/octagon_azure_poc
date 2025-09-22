#!/usr/bin/env python3
"""
Create Hybrid Vector Index
==========================

This script creates a new Azure Search index that combines:
- Full text extractions (raw content)
- Parsed JSON data (structured fields)
- Multiple vector embeddings for comprehensive search
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
    else:
        print("⚠️ .env file not found, using system environment variables")
    
    return {
        'search_endpoint': os.getenv('SEARCH_ENDPOINT'),
        'search_key': os.getenv('SEARCH_KEY')
    }


def create_hybrid_index_definition():
    """Create the hybrid vector index definition"""
    return {
        "name": "octagon-sows-hybrid",
        "fields": [
            # Standard identifier fields
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
            
            # Parsed data fields
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
            
            # Full text content
            {
                "name": "raw_content",
                "type": "Edm.String",
                "searchable": True,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True,
                "analyzer": "en.microsoft"
            },
            
            # Vector fields for semantic search
            {
                "name": "full_text_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": 1536,
                "vectorSearchProfile": "default-vector-profile"
            },
            {
                "name": "parsed_content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": 1536,
                "vectorSearchProfile": "default-vector-profile"
            },
            {
                "name": "scope_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": 1536,
                "vectorSearchProfile": "default-vector-profile"
            },
            {
                "name": "deliverables_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": 1536,
                "vectorSearchProfile": "default-vector-profile"
            }
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "default-algorithm",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                }
            ],
            "profiles": [
                {
                    "name": "default-vector-profile",
                    "algorithm": "default-algorithm"
                }
            ]
        },
        "semantic": {
            "configurations": [
                {
                    "name": "default",
                    "prioritizedFields": {
                        "titleField": {
                            "fieldName": "project_title"
                        },
                        "prioritizedContentFields": [
                            {
                                "fieldName": "raw_content"
                            },
                            {
                                "fieldName": "scope_summary"
                            },
                            {
                                "fieldName": "deliverables"
                            }
                        ],
                        "prioritizedKeywordsFields": [
                            {
                                "fieldName": "client_name"
                            }
                        ]
                    }
                }
            ]
        }
    }


def create_index(search_endpoint, search_key, index_definition):
    """Create the Azure Search index"""
    url = f"{search_endpoint}/indexes?api-version=2023-11-01"
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    try:
        response = requests.post(url, headers=headers, json=index_definition)
        
        if response.status_code == 201:
            print(f"✅ Successfully created hybrid index: {index_definition['name']}")
            return True
        elif response.status_code == 409:
            print(f"⚠️  Index {index_definition['name']} already exists")
            return True
        else:
            print(f"❌ Error creating index: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False


def main():
    """Main function"""
    print("🚀 Creating Hybrid Vector Index")
    print("=" * 60)
    
    # Load configuration
    config = load_environment()
    
    if not config['search_endpoint'] or not config['search_key']:
        print("❌ Missing required configuration")
        return
    
    search_endpoint = config['search_endpoint'].rstrip('/')
    search_key = config['search_key']
    
    # Create index definition
    print("📋 Creating hybrid index definition...")
    index_definition = create_hybrid_index_definition()
    
    print(f"✅ Index definition created with {len(index_definition['fields'])} fields")
    print("✅ Vector search configuration added")
    print("✅ Semantic ranking configuration added")
    print("✅ Hybrid data structure (full text + parsed)")
    
    # Create the index
    print("🏗️  Creating index...")
    if create_index(search_endpoint, search_key, index_definition):
        print("🎉 Hybrid vector index created successfully!")
        print("\n📝 Next steps:")
        print("1. Populate the hybrid index with both full text and parsed data")
        print("2. Test hybrid search capabilities")
        print("3. Update Streamlit app to use hybrid search")
    else:
        print("❌ Failed to create index")


if __name__ == "__main__":
    main()
