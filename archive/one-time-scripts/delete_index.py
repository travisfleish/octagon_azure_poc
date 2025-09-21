#!/usr/bin/env python3
"""
Delete Azure Search Index
========================

This script deletes the octagon-sows-parsed index so we can start fresh.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

def delete_index():
    """Delete the octagon-sows-parsed index"""
    
    # Load environment variables
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
    else:
        print("⚠️ .env file not found, using system environment variables")
    
    search_endpoint = os.getenv('SEARCH_ENDPOINT')
    search_key = os.getenv('SEARCH_KEY')
    index_name = "octagon-sows-parsed"
    
    if not search_endpoint or not search_key:
        print("❌ Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
        return False
    
    # Remove trailing slash if present
    search_endpoint = search_endpoint.rstrip('/')
    
    print(f"🗑️  Deleting Azure Search index: {index_name}")
    print(f"🔗 Endpoint: {search_endpoint}")
    
    # Delete the index
    url = f"{search_endpoint}/indexes/{index_name}?api-version=2023-11-01"
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    try:
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 204:
            print(f"✅ Successfully deleted index: {index_name}")
            return True
        elif response.status_code == 404:
            print(f"⚠️  Index {index_name} does not exist")
            return True
        else:
            print(f"❌ Error deleting index: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting index: {e}")
        return False

def verify_deletion():
    """Verify the index has been deleted by listing all indexes"""
    
    search_endpoint = os.getenv('SEARCH_ENDPOINT').rstrip('/')
    search_key = os.getenv('SEARCH_KEY')
    
    url = f"{search_endpoint}/indexes?api-version=2023-11-01"
    headers = {'Content-Type': 'application/json', 'api-key': search_key}
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            indexes = data.get('value', [])
            
            print(f"\n📋 Remaining indexes:")
            if indexes:
                for i, index in enumerate(indexes, 1):
                    print(f"{i}. {index.get('name', 'Unknown')}")
            else:
                print("   No indexes found")
            
            # Check if our index is gone
            index_names = [idx.get('name') for idx in indexes]
            if 'octagon-sows-parsed' not in index_names:
                print(f"\n✅ Confirmed: octagon-sows-parsed index has been deleted")
                return True
            else:
                print(f"\n❌ Warning: octagon-sows-parsed index still exists")
                return False
        else:
            print(f"❌ Error listing indexes: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying deletion: {e}")
        return False

def main():
    """Main function"""
    print("🗑️  AZURE SEARCH INDEX DELETION")
    print("=" * 50)
    
    # Delete the index
    success = delete_index()
    
    if success:
        # Verify deletion
        verify_deletion()
        print(f"\n✅ Index deletion completed!")
        print(f"🎯 You can now recreate the index with proper data")
    else:
        print(f"\n❌ Index deletion failed")

if __name__ == "__main__":
    main()
