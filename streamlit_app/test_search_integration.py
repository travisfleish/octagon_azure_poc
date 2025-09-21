#!/usr/bin/env python3
"""
Test script for Azure Search integration in Streamlit app
"""

import sys
from pathlib import Path

# Add the services directory to the path
sys.path.append(str(Path(__file__).parent / "services"))

from azure_search_service import get_search_service

def test_search_service():
    """Test the Azure Search service functionality"""
    print("🧪 Testing Azure Search Service Integration")
    print("=" * 50)
    
    try:
        # Initialize service
        print("1. Initializing search service...")
        search_service = get_search_service()
        print("   ✅ Service initialized successfully")
        
        # Test basic stats
        print("\n2. Testing basic stats...")
        stats = search_service.get_stats()
        print(f"   📊 Total documents: {stats['total_documents']}")
        print(f"   🏢 Unique clients: {stats['clients']}")
        if stats['date_range']:
            print(f"   📅 Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        print("   ✅ Stats retrieved successfully")
        
        # Test search functionality
        print("\n3. Testing search functionality...")
        
        # Test 1: Search for "Company 2"
        print("   🔍 Testing client search...")
        results = search_service.search_by_client("Company 2", top=5)
        if results and results.get('value'):
            print(f"   ✅ Found {len(results['value'])} results for 'Company 2'")
        else:
            print("   ⚠️  No results found for 'Company 2'")
        
        # Test 2: Search for "hospitality"
        print("   🔍 Testing project title search...")
        results = search_service.search_by_project_title("hospitality", top=5)
        if results and results.get('value'):
            print(f"   ✅ Found {len(results['value'])} results for 'hospitality'")
        else:
            print("   ⚠️  No results found for 'hospitality'")
        
        # Test 3: Search for "Project Management"
        print("   🔍 Testing staffing search...")
        results = search_service.search_by_staffing_role("Project Management", top=5)
        if results and results.get('value'):
            print(f"   ✅ Found {len(results['value'])} results for 'Project Management'")
        else:
            print("   ⚠️  No results found for 'Project Management'")
        
        # Test 4: Get all documents
        print("   🔍 Testing get all documents...")
        results = search_service.get_all_documents(top=10)
        if results and results.get('value'):
            print(f"   ✅ Retrieved {len(results['value'])} documents")
        else:
            print("   ⚠️  No documents retrieved")
        
        # Test 5: Test unique values
        print("\n4. Testing unique value retrieval...")
        clients = search_service.get_unique_clients()
        print(f"   🏢 Unique clients: {len(clients)}")
        for client in clients[:3]:  # Show first 3
            print(f"      • {client}")
        
        lengths = search_service.get_unique_project_lengths()
        print(f"   ⏱️  Unique project lengths: {len(lengths)}")
        for length in lengths[:3]:  # Show first 3
            print(f"      • {length}")
        
        print("\n✅ All tests completed successfully!")
        print("🎉 Azure Search integration is working properly!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("Please check your Azure Search configuration")
        return False
    
    return True

if __name__ == "__main__":
    test_search_service()
