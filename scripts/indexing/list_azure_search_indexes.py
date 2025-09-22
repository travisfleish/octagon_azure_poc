#!/usr/bin/env python3
"""
Script to list all existing indexes in Azure Search service.
Uses configuration from .env file.
"""

import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file."""
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

def list_search_indexes(search_endpoint, search_key):
    """List all indexes in the Azure Search service."""
    if not search_endpoint or not search_key:
        print("❌ Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
        return
    
    # Remove trailing slash if present
    search_endpoint = search_endpoint.rstrip('/')
    
    # Azure Search REST API endpoint for listing indexes
    url = f"{search_endpoint}/indexes?api-version=2023-11-01"
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    try:
        print(f"🔍 Connecting to Azure Search service: {search_endpoint}")
        print("📋 Fetching list of indexes...")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            indexes = data.get('value', [])
            
            if not indexes:
                print("📭 No indexes found in the search service")
                return
            
            print(f"\n✅ Found {len(indexes)} index(es):")
            print("=" * 80)
            
            for i, index in enumerate(indexes, 1):
                print(f"\n{i}. Index Name: {index.get('name', 'N/A')}")
                print(f"   Description: {index.get('description', 'No description')}")
                print(f"   Fields: {len(index.get('fields', []))}")
                
                # Show key fields
                fields = index.get('fields', [])
                if fields:
                    print("   Key Fields:")
                    for field in fields[:5]:  # Show first 5 fields
                        field_type = field.get('type', 'unknown')
                        is_key = field.get('key', False)
                        is_searchable = field.get('searchable', False)
                        is_filterable = field.get('filterable', False)
                        
                        key_indicator = " (KEY)" if is_key else ""
                        search_indicator = " [Searchable]" if is_searchable else ""
                        filter_indicator = " [Filterable]" if is_filterable else ""
                        
                        print(f"     - {field.get('name', 'N/A')}: {field_type}{key_indicator}{search_indicator}{filter_indicator}")
                    
                    if len(fields) > 5:
                        print(f"     ... and {len(fields) - 5} more fields")
                
                # Show scoring profiles
                scoring_profiles = index.get('scoringProfiles', [])
                if scoring_profiles:
                    print(f"   Scoring Profiles: {len(scoring_profiles)}")
                    for profile in scoring_profiles:
                        print(f"     - {profile.get('name', 'N/A')}")
                
                # Show CORS options
                cors_options = index.get('corsOptions', {})
                if cors_options:
                    allowed_origins = cors_options.get('allowedOrigins', [])
                    if allowed_origins:
                        print(f"   CORS Origins: {', '.join(allowed_origins)}")
                
                print("-" * 80)
            
            # Summary
            print(f"\n📊 Summary:")
            print(f"   Total indexes: {len(indexes)}")
            
            # Count by type
            field_counts = [len(idx.get('fields', [])) for idx in indexes]
            if field_counts:
                print(f"   Average fields per index: {sum(field_counts) / len(field_counts):.1f}")
                print(f"   Max fields in any index: {max(field_counts)}")
                print(f"   Min fields in any index: {min(field_counts)}")
            
        elif response.status_code == 401:
            print("❌ Authentication failed. Please check your SEARCH_KEY")
        elif response.status_code == 403:
            print("❌ Access forbidden. Please check your permissions")
        elif response.status_code == 404:
            print("❌ Search service not found. Please check your SEARCH_ENDPOINT")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main function."""
    print("🔍 Azure Search Index Lister")
    print("=" * 50)
    
    # Load configuration
    config = load_environment()
    
    # List indexes
    list_search_indexes(config['search_endpoint'], config['search_key'])

if __name__ == "__main__":
    main()
