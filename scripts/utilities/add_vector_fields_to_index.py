#!/usr/bin/env python3
"""
Add Vector Fields to Parsed SOWs Index
=====================================

This script adds vector fields to the existing octagon-sows-parsed index
to enable semantic search capabilities.
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


def get_current_index_definition(search_endpoint, search_key):
    """Get the current index definition"""
    url = f"{search_endpoint}/indexes/octagon-sows-parsed?api-version=2023-11-01"
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error getting index definition: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting index definition: {e}")
        return None


def create_updated_index_definition(current_definition):
    """Create updated index definition with vector fields"""
    if not current_definition:
        return None
    
    # Add vector fields to the existing fields
    new_fields = [
        {
            "name": "content_vector",
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
        }
    ]
    
    # Add vector search configuration
    vector_search = {
        "algorithms": [
            {
                "name": "default-algorithm",
                "kind": "hnsw",
                "parameters": {
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
    }
    
    # Add semantic configuration
    semantic_config = {
        "configurations": [
            {
                "name": "default",
                "prioritizedFields": {
                    "titleField": {
                        "fieldName": "project_title"
                    },
                    "prioritizedContentFields": [
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
    
    # Create updated definition
    updated_definition = current_definition.copy()
    updated_definition["fields"].extend(new_fields)
    updated_definition["vectorSearch"] = vector_search
    updated_definition["semantic"] = semantic_config
    
    return updated_definition


def update_index_definition(search_endpoint, search_key, updated_definition):
    """Update the index definition"""
    url = f"{search_endpoint}/indexes/octagon-sows-parsed?api-version=2023-11-01"
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    try:
        response = requests.put(url, headers=headers, json=updated_definition)
        if response.status_code == 200:
            print("✅ Successfully updated index definition")
            return True
        else:
            print(f"❌ Error updating index: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating index: {e}")
        return False


def main():
    """Main function"""
    print("🔧 Adding Vector Fields to Parsed SOWs Index")
    print("=" * 60)
    
    # Load configuration
    config = load_environment()
    
    if not config['search_endpoint'] or not config['search_key']:
        print("❌ Missing required configuration")
        return
    
    search_endpoint = config['search_endpoint'].rstrip('/')
    search_key = config['search_key']
    
    # Get current index definition
    print("📋 Getting current index definition...")
    current_definition = get_current_index_definition(search_endpoint, search_key)
    
    if not current_definition:
        print("❌ Could not retrieve current index definition")
        return
    
    print(f"✅ Found {len(current_definition['fields'])} existing fields")
    
    # Create updated definition
    print("🔧 Creating updated index definition...")
    updated_definition = create_updated_index_definition(current_definition)
    
    if not updated_definition:
        print("❌ Could not create updated definition")
        return
    
    print(f"✅ Added {len(updated_definition['fields']) - len(current_definition['fields'])} new fields")
    print("✅ Added vector search configuration")
    print("✅ Added semantic configuration")
    
    # Update the index
    print("🚀 Updating index definition...")
    if update_index_definition(search_endpoint, search_key, updated_definition):
        print("🎉 Index successfully updated with vector and semantic capabilities!")
        print("\n📝 Next steps:")
        print("1. The index now supports vector search and semantic ranking")
        print("2. You'll need to re-index documents to populate vector fields")
        print("3. Use the semantic search service for enhanced search capabilities")
    else:
        print("❌ Failed to update index")


if __name__ == "__main__":
    main()
