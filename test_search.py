#!/usr/bin/env python3
"""
Simple test script to verify the parsed SOWs search functionality.
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
    
    search_endpoint = os.getenv('SEARCH_ENDPOINT')
    search_key = os.getenv('SEARCH_KEY')
    
    if not search_endpoint or not search_key:
        raise ValueError("Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
    
    return search_endpoint.rstrip('/'), search_key

def test_search():
    """Test basic search functionality"""
    search_endpoint, search_key = load_environment()
    index_name = "octagon-sows-parsed"
    
    # Test 1: Search for "Company 2"
    print("🔍 Test 1: Searching for 'Company 2'")
    url = f"{search_endpoint}/indexes/{index_name}/docs/search?api-version=2023-11-01"
    headers = {
        'Content-Type': 'application/json',
        'api-key': search_key
    }
    
    payload = {
        "search": "Company 2",
        "searchFields": "client_name",
        "top": 5,
        "count": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            count = data.get('@odata.count', 0)
            docs = data.get('value', [])
            print(f"✅ Found {count} results, showing {len(docs)} documents:")
            for i, doc in enumerate(docs, 1):
                print(f"  {i}. {doc.get('client_name')} - {doc.get('project_title')}")
        else:
            print(f"❌ Search failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*50)
    
    # Test 2: Search for "hospitality" in project titles
    print("🔍 Test 2: Searching for 'hospitality' in project titles")
    payload = {
        "search": "hospitality",
        "searchFields": "project_title",
        "top": 5,
        "count": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            count = data.get('@odata.count', 0)
            docs = data.get('value', [])
            print(f"✅ Found {count} results, showing {len(docs)} documents:")
            for i, doc in enumerate(docs, 1):
                print(f"  {i}. {doc.get('client_name')} - {doc.get('project_title')}")
        else:
            print(f"❌ Search failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*50)
    
    # Test 3: Search for "Project Management" in staffing
    print("🔍 Test 3: Searching for 'Project Management' in staffing")
    payload = {
        "search": "Project Management",
        "searchFields": "staffing_plan",
        "top": 5,
        "count": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            count = data.get('@odata.count', 0)
            docs = data.get('value', [])
            print(f"✅ Found {count} results, showing {len(docs)} documents:")
            for i, doc in enumerate(docs, 1):
                print(f"  {i}. {doc.get('client_name')} - {doc.get('project_title')}")
                # Show staffing info
                staffing = doc.get('staffing_plan', [])
                for staff in staffing[:2]:  # Show first 2 staffing entries
                    if 'Project Management' in staff:
                        print(f"     Staffing: {staff}")
        else:
            print(f"❌ Search failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_search()
