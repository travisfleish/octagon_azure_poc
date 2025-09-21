#!/usr/bin/env python3
"""
Create Comprehensive SOW Spreadsheet
===================================

This script pulls all parsed SOW data from Azure Storage and creates
a detailed spreadsheet with all the extracted information.
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

class SOWSpreadsheetCreator:
    """Creates comprehensive spreadsheets from parsed SOW data"""
    
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
        """Format staffing plan for display in spreadsheet"""
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
    
    def create_main_spreadsheet(self, all_sow_data):
        """Create the main SOW overview spreadsheet"""
        
        print("📊 Creating main SOW overview spreadsheet...")
        
        # Prepare data for main spreadsheet
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
        
        # Create DataFrame and save to Excel
        df_main = pd.DataFrame(main_rows)
        
        # Sort by client name, then project title
        df_main = df_main.sort_values(['Client Name', 'Project Title'])
        
        return df_main
    
    def create_staffing_detail_spreadsheet(self, all_sow_data):
        """Create detailed staffing breakdown spreadsheet"""
        
        print("👥 Creating detailed staffing breakdown spreadsheet...")
        
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
    
    def create_deliverables_spreadsheet(self, all_sow_data):
        """Create deliverables breakdown spreadsheet"""
        
        print("📋 Creating deliverables breakdown spreadsheet...")
        
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
    
    def create_summary_spreadsheet(self, all_sow_data):
        """Create summary statistics spreadsheet"""
        
        print("📈 Creating summary statistics spreadsheet...")
        
        # Client summary
        client_summary = {}
        project_types = {}
        total_staffing = 0
        total_deliverables = 0
        
        for sow_data in all_sow_data:
            if not sow_data:
                continue
            
            client = sow_data.get("client_name", "Unknown")
            project_title = sow_data.get("project_title", "")
            staffing_count = len(sow_data.get("staffing_plan", []))
            deliverables_count = len(sow_data.get("deliverables", []))
            
            # Client summary
            if client not in client_summary:
                client_summary[client] = {
                    "Projects": 0,
                    "Total Staffing": 0,
                    "Total Deliverables": 0
                }
            
            client_summary[client]["Projects"] += 1
            client_summary[client]["Total Staffing"] += staffing_count
            client_summary[client]["Total Deliverables"] += deliverables_count
            
            total_staffing += staffing_count
            total_deliverables += deliverables_count
            
            # Project type analysis (simple keyword-based)
            title_lower = project_title.lower()
            if any(keyword in title_lower for keyword in ['hospitality', 'event', 'hosting']):
                project_type = "Hospitality/Events"
            elif any(keyword in title_lower for keyword in ['measurement', 'analytics', 'reporting']):
                project_type = "Analytics/Measurement"
            elif any(keyword in title_lower for keyword in ['marketing', 'brand', 'campaign']):
                project_type = "Marketing/Activation"
            elif any(keyword in title_lower for keyword in ['partnership', 'platform', 'support']):
                project_type = "Partnership Management"
            else:
                project_type = "Other"
            
            project_types[project_type] = project_types.get(project_type, 0) + 1
        
        # Create summary data
        summary_data = []
        
        # Overall summary
        summary_data.append({
            "Metric": "Total SOWs",
            "Value": len(all_sow_data),
            "Category": "Overall"
        })
        summary_data.append({
            "Metric": "Total Staffing Entries",
            "Value": total_staffing,
            "Category": "Overall"
        })
        summary_data.append({
            "Metric": "Total Deliverables",
            "Value": total_deliverables,
            "Category": "Overall"
        })
        summary_data.append({
            "Metric": "Average Staffing per SOW",
            "Value": round(total_staffing / len(all_sow_data), 1) if all_sow_data else 0,
            "Category": "Overall"
        })
        
        # Client breakdown
        for client, stats in client_summary.items():
            summary_data.append({
                "Metric": f"{client} - Projects",
                "Value": stats["Projects"],
                "Category": "By Client"
            })
            summary_data.append({
                "Metric": f"{client} - Staffing",
                "Value": stats["Total Staffing"],
                "Category": "By Client"
            })
        
        # Project type breakdown
        for project_type, count in project_types.items():
            summary_data.append({
                "Metric": f"{project_type} Projects",
                "Value": count,
                "Category": "By Type"
            })
        
        df_summary = pd.DataFrame(summary_data)
        return df_summary
    
    async def create_all_spreadsheets(self):
        """Create all spreadsheets from parsed SOW data"""
        
        print("🚀 SOW SPREADSHEET CREATOR")
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
        
        print(f"\n📊 Creating spreadsheets from {len(all_sow_data)} SOW documents...")
        
        # Create all spreadsheets
        df_main = self.create_main_spreadsheet(all_sow_data)
        df_staffing = self.create_staffing_detail_spreadsheet(all_sow_data)
        df_deliverables = self.create_deliverables_spreadsheet(all_sow_data)
        df_summary = self.create_summary_spreadsheet(all_sow_data)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_sow_analysis_{timestamp}.xlsx"
        
        # Save to Excel with multiple sheets
        print(f"\n💾 Saving to Excel file: {filename}")
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_main.to_excel(writer, sheet_name='SOW Overview', index=False)
            df_staffing.to_excel(writer, sheet_name='Staffing Details', index=False)
            df_deliverables.to_excel(writer, sheet_name='Deliverables', index=False)
            df_summary.to_excel(writer, sheet_name='Summary Statistics', index=False)
        
        print(f"✅ Successfully created comprehensive spreadsheet: {filename}")
        print(f"\n📋 Spreadsheet contains {len(df_main)} SOWs with:")
        print(f"   • {len(df_staffing)} staffing entries")
        print(f"   • {len(df_deliverables)} deliverables")
        print(f"   • {len(df_summary)} summary statistics")
        
        return True

async def main():
    """Main function"""
    creator = SOWSpreadsheetCreator()
    await creator.create_all_spreadsheets()

if __name__ == "__main__":
    asyncio.run(main())
