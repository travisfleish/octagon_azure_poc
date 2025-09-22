#!/usr/bin/env python3
"""
Create SOW Data CSV Files
========================

This script pulls all parsed SOW data from Azure Storage and creates
CSV files with all the extracted information.
"""

import os
import json
import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential

class SOWCSVCreator:
    """Creates CSV files from parsed SOW data"""
    
    def __init__(self):
        self.blob_service_client = None
        self.container_name = "parsed"
        
    async def initialize(self):
        """Initialize Azure Storage client"""
        # Load environment variables
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment from {env_path}")
        else:
            print("⚠️ .env file not found, using system environment variables")
        
        account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        if not account_url:
            print("❌ AZURE_STORAGE_ACCOUNT_URL not found in environment variables")
            return False
        
        try:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
            print(f"🔗 Connected to Azure Storage: {account_url}")
            return True
        except Exception as e:
            print(f"❌ Error connecting to Azure Storage: {e}")
            return False
    
    async def get_all_parsed_sows(self):
        """Get all parsed SOW JSON files from Azure Storage"""
        if not self.blob_service_client:
            print("❌ Azure Storage client not initialized")
            return []
        
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            json_files = []
            async for blob in container_client.list_blobs():
                if blob.name.endswith('.json'):
                    json_files.append(blob.name)
            
            print(f"📄 Found {len(json_files)} JSON files in parsed container")
            return json_files
            
        except Exception as e:
            print(f"❌ Error listing JSON files: {e}")
            return []
    
    async def download_json_file(self, blob_name):
        """Download and parse a JSON file from Azure Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_data = await blob_client.download_blob()
            content = await blob_data.readall()
            json_data = json.loads(content.decode('utf-8'))
            
            return json_data
            
        except Exception as e:
            print(f"❌ Error downloading {blob_name}: {e}")
            return None
    
    def format_staffing_plan(self, staffing_plan):
        """Format staffing plan for display in CSV"""
        if not staffing_plan:
            return "No staffing data"
        
        formatted_entries = []
        for person in staffing_plan:
            if isinstance(person, dict):
                name = person.get("name", "N/A")
                role = person.get("role", "N/A")
                allocation = person.get("allocation", "N/A")
                formatted_entries.append(f"{name} ({role}): {allocation}")
            else:
                formatted_entries.append(str(person))
        
        return " | ".join(formatted_entries)
    
    def create_main_csv(self, all_sow_data):
        """Create the main SOW overview CSV"""
        
        print("📊 Creating main SOW overview CSV...")
        
        # Prepare data for main CSV
        main_rows = []
        
        for sow_data in all_sow_data:
            if not sow_data:
                continue
            
            # Format staffing plan
            staffing_plan = sow_data.get("staffing_plan", [])
            staffing_text = self.format_staffing_plan(staffing_plan)
            
            # Format deliverables
            deliverables = sow_data.get("deliverables", [])
            deliverables_text = " | ".join(deliverables) if deliverables else "No deliverables listed"
            
            # Format exclusions
            exclusions = sow_data.get("exclusions", [])
            exclusions_text = " | ".join(exclusions) if exclusions else "No exclusions listed"
            
            row = {
                "File Name": sow_data.get("file_name", "Unknown"),
                "Client Name": sow_data.get("client_name", "Unknown"),
                "Project Title": sow_data.get("project_title", "Unknown"),
                "Start Date": sow_data.get("start_date", "Not specified"),
                "End Date": sow_data.get("end_date", "Not specified"),
                "Project Length": sow_data.get("project_length", "Not specified"),
                "Scope Summary": sow_data.get("scope_summary", "No summary available"),
                "Deliverables": deliverables_text,
                "Exclusions": exclusions_text,
                "Staffing Plan": staffing_text,
                "Staffing Count": len(staffing_plan),
                "Deliverables Count": len(deliverables),
                "Exclusions Count": len(exclusions),
                "Extraction Timestamp": sow_data.get("extraction_timestamp", "Unknown")
            }
            main_rows.append(row)
        
        # Create DataFrame and save to CSV
        df_main = pd.DataFrame(main_rows)
        
        # Sort by client name, then project title
        df_main = df_main.sort_values(['Client Name', 'Project Title'])
        
        return df_main
    
    def create_staffing_csv(self, all_sow_data):
        """Create detailed staffing breakdown CSV"""
        
        print("👥 Creating detailed staffing breakdown CSV...")
        
        staffing_rows = []
        
        for sow_data in all_sow_data:
            if not sow_data:
                continue
            
            client_name = sow_data.get("client_name", "Unknown")
            project_title = sow_data.get("project_title", "Unknown")
            file_name = sow_data.get("file_name", "Unknown")
            staffing_plan = sow_data.get("staffing_plan", [])
            
            if not staffing_plan:
                # Add a row indicating no staffing data
                staffing_rows.append({
                    "Client Name": client_name,
                    "Project Title": project_title,
                    "File Name": file_name,
                    "Person Name": "No staffing data available",
                    "Role": "",
                    "Allocation": "",
                    "Hours": "",
                    "Percentage": ""
                })
                continue
            
            for person in staffing_plan:
                if isinstance(person, dict):
                    name = person.get("name", "N/A")
                    role = person.get("role", "N/A")
                    allocation = person.get("allocation", "N/A")
                    
                    # Try to extract hours and percentage from allocation string
                    hours = ""
                    percentage = ""
                    if allocation and allocation != "N/A":
                        # Look for patterns like "100% – 1,800 hrs" or "45 hrs (2.50%)"
                        import re
                        hours_match = re.search(r'(\d+(?:,\d+)?)\s*hrs?', allocation)
                        percent_match = re.search(r'(\d+(?:\.\d+)?)%', allocation)
                        
                        if hours_match:
                            hours = hours_match.group(1)
                        if percent_match:
                            percentage = percent_match.group(1) + "%"
                    
                    staffing_rows.append({
                        "Client Name": client_name,
                        "Project Title": project_title,
                        "File Name": file_name,
                        "Person Name": name,
                        "Role": role,
                        "Allocation": allocation,
                        "Hours": hours,
                        "Percentage": percentage
                    })
                else:
                    # Handle string format
                    staffing_rows.append({
                        "Client Name": client_name,
                        "Project Title": project_title,
                        "File Name": file_name,
                        "Person Name": "See allocation",
                        "Role": "",
                        "Allocation": str(person),
                        "Hours": "",
                        "Percentage": ""
                    })
        
        df_staffing = pd.DataFrame(staffing_rows)
        return df_staffing
    
    def create_deliverables_csv(self, all_sow_data):
        """Create deliverables breakdown CSV"""
        
        print("📋 Creating deliverables breakdown CSV...")
        
        deliverables_rows = []
        
        for sow_data in all_sow_data:
            if not sow_data:
                continue
            
            client_name = sow_data.get("client_name", "Unknown")
            project_title = sow_data.get("project_title", "Unknown")
            file_name = sow_data.get("file_name", "Unknown")
            deliverables = sow_data.get("deliverables", [])
            
            if not deliverables:
                deliverables_rows.append({
                    "Client Name": client_name,
                    "Project Title": project_title,
                    "File Name": file_name,
                    "Deliverable": "No deliverables listed",
                    "Deliverable Number": ""
                })
                continue
            
            for i, deliverable in enumerate(deliverables, 1):
                deliverables_rows.append({
                    "Client Name": client_name,
                    "Project Title": project_title,
                    "File Name": file_name,
                    "Deliverable": deliverable,
                    "Deliverable Number": f"{i}"
                })
        
        df_deliverables = pd.DataFrame(deliverables_rows)
        return df_deliverables
    
    async def create_all_csvs(self):
        """Create all CSV files from parsed SOW data"""
        
        print("🚀 SOW CSV CREATOR")
        print("=" * 50)
        
        # Initialize Azure Storage
        if not await self.initialize():
            return False
        
        # Get all parsed SOW files
        json_files = await self.get_all_parsed_sows()
        if not json_files:
            print("❌ No JSON files found to process")
            return False
        
        # Download and process all SOW data
        print(f"\n📥 Processing {len(json_files)} SOW files...")
        all_sow_data = []
        
        for i, blob_name in enumerate(json_files, 1):
            print(f"  📄 Processing {i}/{len(json_files)}: {blob_name}")
            
            sow_data = await self.download_json_file(blob_name)
            if sow_data:
                all_sow_data.append(sow_data)
                print(f"    ✅ Processed: {sow_data.get('client_name', 'Unknown')} - {sow_data.get('project_title', 'Unknown')}")
            else:
                print(f"    ❌ Failed to process {blob_name}")
        
        if not all_sow_data:
            print("❌ No SOW data processed successfully")
            return False
        
        print(f"\n📊 Creating CSV files from {len(all_sow_data)} SOW documents...")
        
        # Create all CSVs
        df_main = self.create_main_csv(all_sow_data)
        df_staffing = self.create_staffing_csv(all_sow_data)
        df_deliverables = self.create_deliverables_csv(all_sow_data)
        
        # Generate filenames with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to CSV files
        print(f"\n💾 Saving CSV files...")
        
        main_filename = f"sow_overview_{timestamp}.csv"
        staffing_filename = f"sow_staffing_details_{timestamp}.csv"
        deliverables_filename = f"sow_deliverables_{timestamp}.csv"
        
        df_main.to_csv(main_filename, index=False)
        df_staffing.to_csv(staffing_filename, index=False)
        df_deliverables.to_csv(deliverables_filename, index=False)
        
        print(f"✅ Successfully created CSV files:")
        print(f"   📊 {main_filename} - Main SOW overview ({len(df_main)} rows)")
        print(f"   👥 {staffing_filename} - Staffing details ({len(df_staffing)} rows)")
        print(f"   📋 {deliverables_filename} - Deliverables ({len(df_deliverables)} rows)")
        
        # Print summary
        print(f"\n📈 SUMMARY:")
        print(f"   • Total SOWs: {len(all_sow_data)}")
        print(f"   • Total staffing entries: {len(df_staffing)}")
        print(f"   • Total deliverables: {len(df_deliverables)}")
        
        # Client breakdown
        clients = df_main['Client Name'].value_counts()
        print(f"\n🏢 By Client:")
        for client, count in clients.items():
            print(f"   • {client}: {count} project(s)")
        
        return True

async def main():
    """Main function"""
    creator = SOWCSVCreator()
    await creator.create_all_csvs()

if __name__ == "__main__":
    asyncio.run(main())
