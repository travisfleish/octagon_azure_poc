#!/usr/bin/env python3
"""
Quick Staffing Lookup Tool
==========================

A simple tool to quickly look up historical staffing patterns for any company.
Perfect for when you need immediate staffing guidance for a new SOW.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

class QuickStaffingLookup:
    """Quick lookup for historical staffing patterns"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.index_name = "octagon-sows-parsed"
        
    def load_environment(self):
        """Load environment variables"""
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        self.search_endpoint = os.getenv('SEARCH_ENDPOINT').rstrip('/')
        self.search_key = os.getenv('SEARCH_KEY')
    
    def get_company_staffing(self, company_name):
        """Get quick staffing summary for a company"""
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        headers = {'Content-Type': 'application/json', 'api-key': self.search_key}
        
        payload = {
            "search": "*",
            "filter": f"client_name eq '{company_name}'",
            "select": "client_name,project_title,staffing_plan,project_length",
            "top": 10
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                results = response.json()
                projects = results.get('value', [])
                
                if not projects:
                    return None
                
                print(f"\n🏢 {company_name.upper()} - HISTORICAL STAFFING")
                print("=" * 60)
                
                total_team_size = 0
                projects_with_staffing = 0
                
                for i, project in enumerate(projects, 1):
                    title = project.get('project_title', 'Unknown')
                    length = project.get('project_length', 'Unknown')
                    staffing = project.get('staffing_plan', [])
                    
                    print(f"\n{i}. {title}")
                    print(f"   Duration: {length}")
                    
                    if staffing:
                        print(f"   Team Size: {len(staffing)} people")
                        total_team_size += len(staffing)
                        projects_with_staffing += 1
                        
                        # Show key roles
                        for person in staffing[:3]:  # First 3 people
                            print(f"      • {person}")
                        
                        if len(staffing) > 3:
                            print(f"      ... and {len(staffing) - 3} more")
                    else:
                        print(f"   Team Size: No staffing data")
                
                # Summary
                if projects_with_staffing > 0:
                    avg_team_size = total_team_size / projects_with_staffing
                    print(f"\n📊 SUMMARY:")
                    print(f"   • {projects_with_staffing} project(s) with staffing data")
                    print(f"   • Average team size: {avg_team_size:.1f} people")
                    print(f"   • Total projects: {len(projects)}")
                
                return projects
                
            else:
                print(f"❌ Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def list_all_companies(self):
        """List all available companies"""
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        headers = {'Content-Type': 'application/json', 'api-key': self.search_key}
        
        payload = {
            "search": "*",
            "select": "client_name",
            "top": 50
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                results = response.json()
                clients = set()
                
                for hit in results.get('value', []):
                    client = hit.get('client_name', '').strip()
                    if client:
                        clients.add(client)
                
                print("\n🏢 AVAILABLE COMPANIES:")
                print("-" * 30)
                for i, client in enumerate(sorted(clients), 1):
                    print(f"{i}. {client}")
                
                return sorted(clients)
                
            else:
                print(f"❌ Error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return []

def main():
    """Main function"""
    lookup = QuickStaffingLookup()
    
    try:
        lookup.load_environment()
        
        print("⚡ QUICK STAFFING LOOKUP")
        print("=" * 40)
        print("Quickly find historical staffing patterns for any company")
        
        while True:
            print("\nOptions:")
            print("1. Look up company staffing")
            print("2. List all companies")
            print("3. Exit")
            
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == "1":
                company = input("Enter company name: ").strip()
                if company:
                    lookup.get_company_staffing(company)
                else:
                    print("❌ Please enter a company name")
            
            elif choice == "2":
                lookup.list_all_companies()
            
            elif choice == "3":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
