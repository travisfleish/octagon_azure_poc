#!/usr/bin/env python3
"""
Historical Staffing Pattern Search Tool
=======================================

This tool helps you find historical staffing patterns for specific companies
to inform staffing decisions for new SOW projects.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

class HistoricalStaffingSearch:
    """Search for historical staffing patterns by company"""
    
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
    
    def search_company_projects(self, company_name):
        """Search for all projects from a specific company"""
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Search for projects from the specific company
        payload = {
            "search": "*",
            "filter": f"client_name eq '{company_name}'",
            "top": 50,
            "select": "client_name,project_title,project_length,scope_summary,staffing_plan,deliverables,file_name"
        }
        
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
    
    def analyze_staffing_patterns(self, results, company_name):
        """Analyze staffing patterns from search results"""
        
        if not results or not results.get('value'):
            print(f"❌ No historical projects found for {company_name}")
            return None
        
        projects = results['value']
        
        print(f"\n📊 HISTORICAL STAFFING ANALYSIS FOR {company_name.upper()}")
        print("=" * 80)
        print(f"Found {len(projects)} historical project(s)")
        
        # Collect staffing data
        all_staffing = []
        role_frequency = defaultdict(int)
        project_types = []
        
        for i, project in enumerate(projects, 1):
            project_title = project.get('project_title', 'Unknown')
            project_length = project.get('project_length', 'Unknown')
            staffing_plan = project.get('staffing_plan', [])
            deliverables = project.get('deliverables', [])
            
            print(f"\n{i}. 📋 {project_title}")
            print(f"   Duration: {project_length}")
            print(f"   Deliverables: {len(deliverables)} items")
            
            if staffing_plan:
                print(f"   👥 Staffing Plan ({len(staffing_plan)} people):")
                for person in staffing_plan:
                    print(f"      • {person}")
                    all_staffing.append(person)
                    
                    # Extract role for frequency analysis
                    if '(' in person and ')' in person:
                        role = person.split('(')[1].split(')')[0].strip()
                        role_frequency[role] += 1
            else:
                print(f"   👥 Staffing Plan: No staffing data available")
            
            # Categorize project type based on deliverables
            project_type = self.categorize_project_type(deliverables, project_title)
            project_types.append(project_type)
        
        # Generate insights
        self.generate_staffing_insights(all_staffing, role_frequency, project_types, company_name)
        
        return {
            'projects': projects,
            'all_staffing': all_staffing,
            'role_frequency': role_frequency,
            'project_types': project_types
        }
    
    def categorize_project_type(self, deliverables, project_title):
        """Categorize project type based on deliverables and title"""
        text_to_analyze = ' '.join(deliverables).lower() + ' ' + project_title.lower()
        
        if any(keyword in text_to_analyze for keyword in ['hospitality', 'event', 'hosting', 'guest']):
            return 'Hospitality/Events'
        elif any(keyword in text_to_analyze for keyword in ['measurement', 'analytics', 'reporting', 'dashboard']):
            return 'Analytics/Measurement'
        elif any(keyword in text_to_analyze for keyword in ['marketing', 'brand', 'campaign', 'activation']):
            return 'Marketing/Activation'
        elif any(keyword in text_to_analyze for keyword in ['partnership', 'platform', 'management', 'support']):
            return 'Partnership Management'
        else:
            return 'General/Other'
    
    def generate_staffing_insights(self, all_staffing, role_frequency, project_types, company_name):
        """Generate insights about staffing patterns"""
        
        print(f"\n🎯 STAFFING INSIGHTS FOR {company_name.upper()}")
        print("=" * 80)
        
        # Project type analysis
        type_counts = defaultdict(int)
        for project_type in project_types:
            type_counts[project_type] += 1
        
        print(f"\n📈 Project Types:")
        for project_type, count in type_counts.items():
            print(f"   • {project_type}: {count} project(s)")
        
        # Role frequency analysis
        if role_frequency:
            print(f"\n👥 Most Common Roles:")
            sorted_roles = sorted(role_frequency.items(), key=lambda x: x[1], reverse=True)
            for role, count in sorted_roles[:10]:  # Top 10 roles
                print(f"   • {role}: {count} occurrence(s)")
        
        # Staffing recommendations
        print(f"\n💡 STAFFING RECOMMENDATIONS FOR NEW {company_name.upper()} PROJECTS:")
        print("-" * 60)
        
        if not all_staffing:
            print("   ⚠️  No historical staffing data available.")
            print("   📋 Consider using general staffing templates or similar client patterns.")
            return
        
        # Analyze common patterns
        total_projects = len(project_types)
        avg_team_size = len(all_staffing) / total_projects if total_projects > 0 else 0
        
        print(f"   📊 Average team size: {avg_team_size:.1f} people per project")
        
        # Role recommendations
        if role_frequency:
            print(f"   🎯 Recommended core roles:")
            for role, count in sorted_roles[:3]:  # Top 3 roles
                percentage = (count / total_projects) * 100
                print(f"      • {role} (used in {percentage:.0f}% of projects)")
        
        # Project type specific recommendations
        if 'Hospitality/Events' in type_counts:
            print(f"   🏨 For hospitality/events projects:")
            print(f"      • Consider event managers and hospitality coordinators")
            print(f"      • Include client services and logistics support")
        
        if 'Analytics/Measurement' in type_counts:
            print(f"   📊 For analytics/measurement projects:")
            print(f"      • Include data analysts and reporting specialists")
            print(f"      • Consider dashboard developers and insights managers")
        
        if 'Marketing/Activation' in type_counts:
            print(f"   📢 For marketing/activation projects:")
            print(f"      • Include brand managers and activation specialists")
            print(f"      • Consider creative directors and campaign managers")
    
    def search_similar_projects(self, company_name, project_type=None):
        """Search for similar projects across all companies for additional insights"""
        
        print(f"\n🔍 SEARCHING FOR SIMILAR PROJECTS ACROSS ALL COMPANIES")
        print("=" * 80)
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Search for similar projects (excluding the target company)
        search_terms = []
        if project_type:
            if project_type == 'Hospitality/Events':
                search_terms = ['hospitality', 'event', 'hosting']
            elif project_type == 'Analytics/Measurement':
                search_terms = ['measurement', 'analytics', 'reporting']
            elif project_type == 'Marketing/Activation':
                search_terms = ['marketing', 'activation', 'brand']
        
        payload = {
            "search": ' '.join(search_terms) if search_terms else "*",
            "filter": f"client_name ne '{company_name}'",  # Not equal to target company
            "top": 20,
            "select": "client_name,project_title,project_length,staffing_plan"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                results = response.json()
                projects = results.get('value', [])
                
                print(f"Found {len(projects)} similar projects from other companies:")
                
                for i, project in enumerate(projects[:5], 1):  # Show top 5
                    client = project.get('client_name', 'Unknown')
                    title = project.get('project_title', 'Unknown')
                    length = project.get('project_length', 'Unknown')
                    staffing = project.get('staffing_plan', [])
                    
                    print(f"\n{i}. {client} - {title}")
                    print(f"   Duration: {length}")
                    print(f"   Team Size: {len(staffing)} people")
                    
                    if staffing:
                        print(f"   Key Roles:")
                        for person in staffing[:3]:  # Show first 3 people
                            print(f"      • {person}")
                
                return projects
            else:
                print(f"❌ Search error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def run_company_analysis(self, company_name):
        """Run complete analysis for a company"""
        
        print(f"🔍 HISTORICAL STAFFING ANALYSIS FOR {company_name.upper()}")
        print("=" * 80)
        
        # Get company's historical projects
        results = self.search_company_projects(company_name)
        
        if not results:
            print(f"❌ Could not retrieve data for {company_name}")
            return
        
        # Analyze staffing patterns
        analysis = self.analyze_staffing_patterns(results, company_name)
        
        if not analysis:
            return
        
        # Determine most common project type for this company
        type_counts = defaultdict(int)
        for project_type in analysis['project_types']:
            type_counts[project_type] += 1
        
        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        
        # Search for similar projects from other companies
        if most_common_type:
            self.search_similar_projects(company_name, most_common_type)
        
        print(f"\n✅ Analysis complete for {company_name}!")
        print(f"📋 Summary: {len(analysis['projects'])} historical projects analyzed")
        print(f"🎯 Most common project type: {most_common_type}")

def main():
    """Main function"""
    search_tool = HistoricalStaffingSearch()
    
    try:
        search_tool.load_environment()
        
        print("🏢 HISTORICAL STAFFING PATTERN SEARCH")
        print("=" * 50)
        print("This tool helps you find historical staffing patterns")
        print("to inform staffing decisions for new SOW projects.")
        print()
        
        # Test with Company 4
        company_name = input("Enter company name (or press Enter for 'Company 4'): ").strip()
        if not company_name:
            company_name = "Company 4"
        
        search_tool.run_company_analysis(company_name)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
