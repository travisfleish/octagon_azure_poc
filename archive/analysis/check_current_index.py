#!/usr/bin/env python3
"""
Check current state of the Azure Search index
"""

import os
import requests
from dotenv import load_dotenv

def check_index():
    load_dotenv()
    search_endpoint = os.getenv('SEARCH_ENDPOINT').rstrip('/')
    search_key = os.getenv('SEARCH_KEY')
    
    url = f'{search_endpoint}/indexes/octagon-sows-parsed/docs/search?api-version=2023-11-01'
    headers = {'Content-Type': 'application/json', 'api-key': search_key}
    payload = {'search': '*', 'select': 'client_name,project_title,staffing_plan', 'top': 20}
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        results = response.json()
        print(f"📊 Current index contains {len(results.get('value', []))} documents:\n")
        
        for i, hit in enumerate(results.get('value', []), 1):
            client = hit.get('client_name', 'Unknown')
            title = hit.get('project_title', 'Unknown') or 'No title'
            staffing = hit.get('staffing_plan', [])
            
            print(f"{i}. {client}")
            print(f"   Project: {title[:60]}...")
            print(f"   Staffing entries: {len(staffing)}")
            
            if staffing and len(staffing) > 0:
                print(f"   Sample staffing:")
                for person in staffing[:2]:  # Show first 2 entries
                    print(f"      • {person[:70]}...")
                if len(staffing) > 2:
                    print(f"      ... and {len(staffing) - 2} more")
            else:
                print(f"   Staffing: No data")
            print()
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    check_index()
