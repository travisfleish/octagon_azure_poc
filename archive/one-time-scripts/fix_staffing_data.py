#!/usr/bin/env python3
"""
Fix Staffing Data in Azure Search Index
=======================================

This script removes the incorrectly added staffing-only documents
and properly merges the detailed staffing data into existing SOW documents.
"""

import os
import requests
from dotenv import load_dotenv

class StaffingDataFixer:
    """Fix the staffing data in the Azure Search index"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.index_name = "octagon-sows-parsed"
        
        # Detailed staffing data from ChatGPT extraction
        self.detailed_staffing_data = {
            "company_4_sow_1": [
                "VP, Client Services – 525 hrs (25% + Onboarding)",
                "Director, Client Services – 450 hrs (25%)",
                "VP, Experiences – 420 hrs (20% + Onboarding)",
                "Sr. Director, Experiences – 1,350 hrs (75% + Onboarding)",
                "Experiential Manager – 1,800 hrs (100%)",
                "Experiential Manager – 1,800 hrs (100%)",
                "Sr. Event Executive – 1,800 hrs (100%)",
                "Sr. Event Executive – 1,650 hrs (100% × 11 months)",
                "Event Executive – 1,650 hrs (100% × 11 months)",
                "Director, Experiences Production – 900 hrs (50%)",
                "Sr. Event Executive, Experiences Production – 900 hrs (50%)"
            ],
            "company_2_sow_1": [
                "EVP (US) – 5% – 60 hrs",
                "SVP (US) – 50% – 920 hrs",
                "VP (US) – 20% – 180 hrs",
                "VP (US) – 100% – 1,800 hrs",
                "SME (US) – 100% – 1,800 hrs",
                "AD (US) – 100% – 1,800 hrs",
                "AM (US) – 100% – 1,800 hrs",
                "SAM (US) – 30% – 540 hrs",
                "AE (UK) – 13% – 220 hrs"
            ],
            "company_2_sow_3": [
                "Derek Aframe (EVP, US) – 5% – 83 hrs",
                "Hannah Woodfin (SVP, US) – 10% – 190 hrs",
                "Sarah Binkenstein Hubner (AD, US) – 100% – 1,800 hrs",
                "Max Boeinelmann (Toolkit Lead, AD, US) – 100% – 1,800 hrs",
                "Caitlin Blankenship (AD, US) – 100% – 1,800 hrs",
                "AM Finance – 100% – 1,800 hrs",
                "Svetlana Hanau (VP) – 25% – 450 hrs",
                "Ted Murphy (VP) – 25% – 450 hrs",
                "Marina T (AM, Hospitality) – 100% – 1,800 hrs",
                "SAM BG Project (Feb–Jul, FRA) – 75% – 690 hrs"
            ],
            "company_1_sow_3": [
                "David Hargis (SVP, US) – 2.5% – 45 hrs",
                "Cynthia Sotero (VP, US) – 2.5% – 45 hrs",
                "Chelsea Pham (Account Manager, US) – 2.0% – 36 hrs"
            ],
            "company_1_sow_4": [
                "Rob McGuire (SVP) – 540 hrs",
                "Thomas Carter (Director) – 540 hrs",
                "Nicole Carter (Sr. Manager) – 540 hrs",
                "Carol Patrick (Director) – 540 hrs",
                "Leslie Knott (Experiential Director) – 540 hrs",
                "Thomas Carter (Experiential Manager) – 540 hrs"
            ],
            "company_1_sow_1": [
                "Account Director – 780 hrs (Formula 1 – Las Vegas, Day-to-Day Lead)",
                "Account Manager – 900 hrs (API Day-to-Day Manager)",
                "Sr. Account Executive (SAE) – 900 hrs (GRAMMY's Day-to-Day Manager)",
                "Account Executive (AE) – 800 hrs (Program Support)"
            ]
        }
    
    def load_environment(self):
        """Load environment variables"""
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
        
        self.search_endpoint = self.search_endpoint.rstrip('/')
    
    def get_all_documents(self):
        """Get all documents from the index"""
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        headers = {'Content-Type': 'application/json', 'api-key': self.search_key}
        
        payload = {
            "search": "*",
            "top": 100,
            "select": "id,file_name,client_name,project_title,staffing_plan"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                results = response.json()
                return results.get('value', [])
            else:
                print(f"❌ Error getting documents: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting documents: {e}")
            return []
    
    def delete_document(self, document_id):
        """Delete a document from the index"""
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/index?api-version=2023-11-01"
        headers = {'Content-Type': 'application/json', 'api-key': self.search_key}
        
        payload = {
            "value": [
                {
                    "@odata.operation": "delete",
                    "id": document_id
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                success_count = len([d for d in result.get('value', []) if d.get('status')])
                return success_count > 0
            else:
                print(f"❌ Error deleting document {document_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting document {document_id}: {e}")
            return False
    
    def update_document_staffing(self, document_id, new_staffing_plan):
        """Update a document's staffing plan"""
        
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/index?api-version=2023-11-01"
        headers = {'Content-Type': 'application/json', 'api-key': self.search_key}
        
        payload = {
            "value": [
                {
                    "@odata.operation": "merge",
                    "id": document_id,
                    "staffing_plan": new_staffing_plan
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                success_count = len([d for d in result.get('value', []) if d.get('status')])
                return success_count > 0
            else:
                print(f"❌ Error updating document {document_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating document {document_id}: {e}")
            return False
    
    def fix_staffing_data(self):
        """Fix the staffing data by removing incorrect entries and updating existing ones"""
        
        print("🔍 Getting all documents from index...")
        documents = self.get_all_documents()
        
        if not documents:
            print("❌ No documents found in index")
            return False
        
        print(f"📄 Found {len(documents)} documents")
        
        # Identify documents to delete (those with null client_name and only staffing_plan)
        documents_to_delete = []
        documents_to_update = []
        
        for doc in documents:
            doc_id = doc.get('id', '')
            client_name = doc.get('client_name')
            project_title = doc.get('project_title')
            file_name = doc.get('file_name')
            staffing_plan = doc.get('staffing_plan', [])
            
            # Check if this is a staffing-only document (null client_name but has staffing data)
            if client_name is None and project_title is None and file_name is None and staffing_plan:
                documents_to_delete.append(doc_id)
                print(f"🗑️  Marked for deletion: {doc_id} (staffing-only document)")
            elif file_name:
                # This is a real SOW document - check if it needs staffing update
                documents_to_update.append(doc)
        
        # Delete the incorrect staffing-only documents
        deleted_count = 0
        if documents_to_delete:
            print(f"\n🗑️  Deleting {len(documents_to_delete)} incorrect documents...")
            for doc_id in documents_to_delete:
                if self.delete_document(doc_id):
                    deleted_count += 1
                    print(f"   ✅ Deleted {doc_id}")
                else:
                    print(f"   ❌ Failed to delete {doc_id}")
        
        # Update existing SOW documents with detailed staffing data
        updated_count = 0
        print(f"\n🔄 Updating existing SOW documents with detailed staffing data...")
        
        for doc in documents_to_update:
            file_name = doc.get('file_name', '')
            doc_id = doc.get('id', '')
            
            # Find matching detailed staffing data
            matching_key = None
            for key in self.detailed_staffing_data.keys():
                if key in file_name.lower().replace('.pdf', '').replace('.docx', '').replace('_', '_'):
                    matching_key = key
                    break
            
            if matching_key:
                new_staffing = self.detailed_staffing_data[matching_key]
                current_staffing = doc.get('staffing_plan', [])
                
                print(f"📋 Updating {file_name}")
                print(f"   Current staffing: {len(current_staffing)} entries")
                print(f"   New staffing: {len(new_staffing)} entries")
                
                if self.update_document_staffing(doc_id, new_staffing):
                    updated_count += 1
                    print(f"   ✅ Successfully updated")
                else:
                    print(f"   ❌ Failed to update")
            else:
                print(f"⚠️  No detailed staffing data found for {file_name}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Documents deleted: {deleted_count}")
        print(f"   Documents updated: {updated_count}")
        print(f"   Total SOW documents: {len(documents_to_update)}")
        
        return True
    
    def run(self):
        """Main execution method"""
        
        print("🔧 FIXING STAFFING DATA IN AZURE SEARCH INDEX")
        print("=" * 60)
        
        self.load_environment()
        success = self.fix_staffing_data()
        
        if success:
            print(f"\n✅ Staffing data fix completed!")
            print(f"🎯 The index now has proper SOW documents with detailed staffing data")
        else:
            print(f"\n❌ Staffing data fix failed")
        
        return success

if __name__ == "__main__":
    from pathlib import Path
    fixer = StaffingDataFixer()
    fixer.run()
