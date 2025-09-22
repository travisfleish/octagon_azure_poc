#!/usr/bin/env python3
"""
Enhanced script to show detailed information about Azure Search indexes.
Shows complete field definitions and index configuration.
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

def get_index_details(search_endpoint, search_key, index_name):
    """Get detailed information about a specific index."""
    if not search_endpoint or not search_key:
        print("❌ Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
        return None
    
    # Remove trailing slash if present
    search_endpoint = search_endpoint.rstrip('/')
    
    # Azure Search REST API endpoint for getting index details
    url = f"{search_endpoint}/indexes/{index_name}?api-version=2023-11-01"
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    try:
        print(f"🔍 Getting details for index: {index_name}")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("❌ Authentication failed. Please check your SEARCH_KEY")
        elif response.status_code == 403:
            print("❌ Access forbidden. Please check your permissions")
        elif response.status_code == 404:
            print(f"❌ Index '{index_name}' not found")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    return None

def display_index_details(index_data):
    """Display detailed information about an index."""
    if not index_data:
        return
    
    print(f"\n📋 Detailed Index Information")
    print("=" * 80)
    print(f"Name: {index_data.get('name', 'N/A')}")
    print(f"Description: {index_data.get('description', 'No description')}")
    
    # Fields
    fields = index_data.get('fields', [])
    print(f"\n📝 Fields ({len(fields)} total):")
    print("-" * 80)
    
    for i, field in enumerate(fields, 1):
        name = field.get('name', 'N/A')
        field_type = field.get('type', 'unknown')
        is_key = field.get('key', False)
        is_searchable = field.get('searchable', False)
        is_filterable = field.get('filterable', False)
        is_sortable = field.get('sortable', False)
        is_facetable = field.get('facetable', False)
        is_retrievable = field.get('retrievable', True)
        is_analyzer = field.get('analyzer', None)
        is_search_analyzer = field.get('searchAnalyzer', None)
        is_index_analyzer = field.get('indexAnalyzer', None)
        
        print(f"{i:2d}. {name}")
        print(f"    Type: {field_type}")
        
        # Attributes
        attributes = []
        if is_key:
            attributes.append("KEY")
        if is_searchable:
            attributes.append("Searchable")
        if is_filterable:
            attributes.append("Filterable")
        if is_sortable:
            attributes.append("Sortable")
        if is_facetable:
            attributes.append("Facetable")
        if not is_retrievable:
            attributes.append("Not Retrievable")
        
        if attributes:
            print(f"    Attributes: {', '.join(attributes)}")
        
        # Analyzers
        analyzers = []
        if is_analyzer:
            analyzers.append(f"Analyzer: {is_analyzer}")
        if is_search_analyzer:
            analyzers.append(f"Search Analyzer: {is_search_analyzer}")
        if is_index_analyzer:
            analyzers.append(f"Index Analyzer: {is_index_analyzer}")
        
        if analyzers:
            print(f"    {' | '.join(analyzers)}")
        
        print()
    
    # Scoring Profiles
    scoring_profiles = index_data.get('scoringProfiles', [])
    if scoring_profiles:
        print(f"🎯 Scoring Profiles ({len(scoring_profiles)}):")
        print("-" * 80)
        for profile in scoring_profiles:
            print(f"- {profile.get('name', 'N/A')}")
            functions = profile.get('functions', [])
            if functions:
                for func in functions:
                    field_name = func.get('fieldName', 'N/A')
                    boost = func.get('boost', 1)
                    boost_mode = func.get('boostMode', 'multiply')
                    print(f"  └─ {field_name}: boost={boost}, mode={boost_mode}")
        print()
    
    # CORS Options
    cors_options = index_data.get('corsOptions', {})
    if cors_options:
        print(f"🌐 CORS Configuration:")
        print("-" * 80)
        allowed_origins = cors_options.get('allowedOrigins', [])
        if allowed_origins:
            print(f"Allowed Origins: {', '.join(allowed_origins)}")
        max_age = cors_options.get('maxAgeInSeconds')
        if max_age:
            print(f"Max Age: {max_age} seconds")
        print()
    
    # Suggesters
    suggesters = index_data.get('suggesters', [])
    if suggesters:
        print(f"💡 Suggesters ({len(suggesters)}):")
        print("-" * 80)
        for suggester in suggesters:
            print(f"- {suggester.get('name', 'N/A')}")
            source_fields = suggester.get('sourceFields', [])
            if source_fields:
                print(f"  Source Fields: {', '.join(source_fields)}")
        print()
    
    # Analyzers (custom)
    analyzers = index_data.get('analyzers', [])
    if analyzers:
        print(f"🔍 Custom Analyzers ({len(analyzers)}):")
        print("-" * 80)
        for analyzer in analyzers:
            print(f"- {analyzer.get('name', 'N/A')}: {analyzer.get('@odata.type', 'N/A')}")
        print()
    
    # Tokenizers
    tokenizers = index_data.get('tokenizers', [])
    if tokenizers:
        print(f"✂️ Custom Tokenizers ({len(tokenizers)}):")
        print("-" * 80)
        for tokenizer in tokenizers:
            print(f"- {tokenizer.get('name', 'N/A')}: {tokenizer.get('@odata.type', 'N/A')}")
        print()
    
    # Token Filters
    token_filters = index_data.get('tokenFilters', [])
    if token_filters:
        print(f"🔧 Custom Token Filters ({len(token_filters)}):")
        print("-" * 80)
        for filter_obj in token_filters:
            print(f"- {filter_obj.get('name', 'N/A')}: {filter_obj.get('@odata.type', 'N/A')}")
        print()

def list_all_indexes(search_endpoint, search_key):
    """List all indexes in the Azure Search service."""
    if not search_endpoint or not search_key:
        print("❌ Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
        return []
    
    # Remove trailing slash if present
    search_endpoint = search_endpoint.rstrip('/')
    
    # Azure Search REST API endpoint for listing indexes
    url = f"{search_endpoint}/indexes?api-version=2023-11-01"
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            indexes = data.get('value', [])
            return [idx.get('name') for idx in indexes if idx.get('name')]
        else:
            print(f"❌ Error listing indexes: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def main():
    """Main function."""
    print("🔍 Azure Search Detailed Index Information")
    print("=" * 60)
    
    # Load configuration
    config = load_environment()
    
    if not config['search_endpoint'] or not config['search_key']:
        print("❌ Missing required configuration")
        return
    
    # List all indexes first
    print("\n📋 Available Indexes:")
    print("-" * 40)
    indexes = list_all_indexes(config['search_endpoint'], config['search_key'])
    
    if not indexes:
        print("No indexes found")
        return
    
    for i, index_name in enumerate(indexes, 1):
        print(f"{i}. {index_name}")
    
    # Get detailed info for each index
    for index_name in indexes:
        index_data = get_index_details(config['search_endpoint'], config['search_key'], index_name)
        display_index_details(index_data)

if __name__ == "__main__":
    main()
