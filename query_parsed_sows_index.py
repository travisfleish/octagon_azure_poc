#!/usr/bin/env python3
"""
Script to query the parsed SOWs Azure Search index.
This script provides various search capabilities for the structured SOW data.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

class ParsedSOWsQueryManager:
    """Manages queries against the parsed SOWs Azure Search index"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
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
        
        if not self.search_endpoint or not self.search_key:
            raise ValueError("Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
        
        # Remove trailing slash if present
        self.search_endpoint = self.search_endpoint.rstrip('/')
    
    def search(self, query, search_fields=None, filter_expression=None, top=10, skip=0):
        """Perform a search query against the index"""
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Build search payload
        payload = {
            "search": query,
            "top": top,
            "skip": skip,
            "count": True,
            "queryType": "simple",
            "searchMode": "all"
        }
        
        if search_fields:
            payload["searchFields"] = search_fields if isinstance(search_fields, str) else ",".join(search_fields)
        
        if filter_expression:
            payload["filter"] = filter_expression
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Search error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return None
    
    def search_by_client(self, client_name):
        """Search for SOWs by client name"""
        print(f"🔍 Searching for SOWs from client: {client_name}")
        results = self.search(
            query=client_name,
            search_fields=["client_name"],
            top=20
        )
        return results
    
    def search_by_project_title(self, project_title):
        """Search for SOWs by project title"""
        print(f"🔍 Searching for SOWs with project title containing: {project_title}")
        results = self.search(
            query=project_title,
            search_fields=["project_title"],
            top=20
        )
        return results
    
    def search_by_staffing_role(self, role):
        """Search for SOWs by staffing role"""
        print(f"🔍 Searching for SOWs with staffing role: {role}")
        results = self.search(
            query=role,
            search_fields=["staffing_plan"],
            top=20
        )
        return results
    
    def search_by_deliverables(self, deliverable):
        """Search for SOWs by deliverable"""
        print(f"🔍 Searching for SOWs with deliverable: {deliverable}")
        results = self.search(
            query=deliverable,
            search_fields=["deliverables"],
            top=20
        )
        return results
    
    def search_by_date_range(self, start_date=None, end_date=None):
        """Search for SOWs by date range"""
        filter_parts = []
        if start_date:
            filter_parts.append(f"start_date ge '{start_date}'")
        if end_date:
            filter_parts.append(f"end_date le '{end_date}'")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        print(f"🔍 Searching for SOWs in date range: {start_date} to {end_date}")
        results = self.search(
            query="*",
            filter_expression=filter_expression,
            top=20
        )
        return results
    
    def search_by_project_length(self, project_length):
        """Search for SOWs by project length"""
        print(f"🔍 Searching for SOWs with project length: {project_length}")
        results = self.search(
            query=project_length,
            search_fields=["project_length"],
            top=20
        )
        return results
    
    def get_all_documents(self, top=50):
        """Get all documents from the index"""
        print("🔍 Retrieving all documents from index")
        results = self.search(
            query="*",
            top=top
        )
        return results
    
    def display_results(self, results, show_details=True):
        """Display search results in a formatted way"""
        if not results:
            print("❌ No results to display")
            return
        
        count = results.get('@odata.count', 0)
        documents = results.get('value', [])
        
        print(f"\n📊 Found {count} total results, showing {len(documents)} documents:")
        print("=" * 80)
        
        for i, doc in enumerate(documents, 1):
            print(f"\n{i}. {doc.get('client_name', 'Unknown Client')}")
            print(f"   Project: {doc.get('project_title', 'No title')}")
            print(f"   Duration: {doc.get('project_length', 'Unknown')}")
            print(f"   Dates: {doc.get('start_date', 'N/A')} to {doc.get('end_date', 'N/A')}")
            print(f"   File: {doc.get('file_name', 'Unknown')}")
            
            if show_details:
                # Show scope summary (truncated)
                scope = doc.get('scope_summary', '')
                if scope:
                    scope_preview = scope[:200] + "..." if len(scope) > 200 else scope
                    print(f"   Scope: {scope_preview}")
                
                # Show deliverables (first 3)
                deliverables = doc.get('deliverables', [])
                if deliverables:
                    deliverables_preview = deliverables[:3]
                    print(f"   Deliverables: {', '.join(deliverables_preview)}")
                    if len(deliverables) > 3:
                        print(f"   ... and {len(deliverables) - 3} more")
                
                # Show staffing plan (first 3)
                staffing = doc.get('staffing_plan', [])
                if staffing:
                    staffing_preview = staffing[:3]
                    print(f"   Staffing: {', '.join(staffing_preview)}")
                    if len(staffing) > 3:
                        print(f"   ... and {len(staffing) - 3} more")
            
            print("-" * 80)
    
    def interactive_search(self):
        """Interactive search interface"""
        print("🔍 Interactive SOW Search")
        print("=" * 50)
        
        while True:
            print("\nSearch Options:")
            print("1. Search by client name")
            print("2. Search by project title")
            print("3. Search by staffing role")
            print("4. Search by deliverable")
            print("5. Search by date range")
            print("6. Search by project length")
            print("7. Get all documents")
            print("8. Custom search")
            print("9. Exit")
            
            choice = input("\nEnter your choice (1-9): ").strip()
            
            if choice == "1":
                client = input("Enter client name: ").strip()
                if client:
                    results = self.search_by_client(client)
                    self.display_results(results)
            
            elif choice == "2":
                title = input("Enter project title keywords: ").strip()
                if title:
                    results = self.search_by_project_title(title)
                    self.display_results(results)
            
            elif choice == "3":
                role = input("Enter staffing role: ").strip()
                if role:
                    results = self.search_by_staffing_role(role)
                    self.display_results(results)
            
            elif choice == "4":
                deliverable = input("Enter deliverable keywords: ").strip()
                if deliverable:
                    results = self.search_by_deliverables(deliverable)
                    self.display_results(results)
            
            elif choice == "5":
                start_date = input("Enter start date (YYYY-MM-DD) or press Enter to skip: ").strip()
                end_date = input("Enter end date (YYYY-MM-DD) or press Enter to skip: ").strip()
                results = self.search_by_date_range(start_date or None, end_date or None)
                self.display_results(results)
            
            elif choice == "6":
                length = input("Enter project length: ").strip()
                if length:
                    results = self.search_by_project_length(length)
                    self.display_results(results)
            
            elif choice == "7":
                results = self.get_all_documents()
                self.display_results(results)
            
            elif choice == "8":
                query = input("Enter search query: ").strip()
                if query:
                    results = self.search(query)
                    self.display_results(results)
            
            elif choice == "9":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please try again.")

def main():
    """Main function"""
    try:
        manager = ParsedSOWsQueryManager()
        manager.load_environment()
        manager.interactive_search()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()