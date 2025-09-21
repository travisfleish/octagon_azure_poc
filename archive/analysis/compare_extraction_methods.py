#!/usr/bin/env python3
"""
SOW Extraction Methods Comparison
================================

This script runs both LLM and taxonomy-based extraction methods separately
and generates comparison charts to assess the results.
"""

import os
import json
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
# import seaborn as sns  # Optional for enhanced styling
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI
import re

from sow_extraction_taxonomy import SOWExtractionTaxonomy, get_field_keywords, get_compiled_patterns_for_field

class SOWExtractionComparator:
    """Compare LLM vs Taxonomy extraction methods"""
    
    def __init__(self):
        self.openai_client = None
        self.blob_service_client = None
        self.container_name = "parsed"
        self.taxonomy = SOWExtractionTaxonomy()
        self.results = []
        
    async def initialize(self):
        """Initialize Azure services"""
        # Load environment variables
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment from {env_path}")
        else:
            print("⚠️ .env file not found, using system environment variables")
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/openai/deployments/{os.getenv('AZURE_OPENAI_DEPLOYMENT')}",
            default_query={"api-version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")}
        )
        
        # Initialize Azure Storage client
        account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        if account_url:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
            print(f"🔗 Connected to Azure Storage: {account_url}")
        else:
            print("⚠️ AZURE_STORAGE_ACCOUNT_URL not found - Azure Storage upload will be skipped")
        
        return True
    
    async def get_parsed_sow_files(self):
        """Get all parsed SOW JSON files from Azure Storage"""
        if not self.blob_service_client:
            print("❌ Azure Storage client not initialized")
            return []
        
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            json_files = []
            async for blob in container_client.list_blobs():
                if blob.name.endswith('.json'):
                    json_files.append(blob_name)
            
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
    
    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from a local file"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            if file_path.suffix.lower() == '.pdf':
                return self._extract_pdf_text(file_data)
            elif file_path.suffix.lower() == '.docx':
                return self._extract_docx_text(file_data)
            else:
                return ""
                
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_pdf_text(self, data: bytes) -> str:
        """Extract text from PDF"""
        try:
            import PyPDF2
            import io
            
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            text = ""
            for page in reader.pages[:10]:  # Limit to first 10 pages
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return ""
    
    def _extract_docx_text(self, data: bytes) -> str:
        """Extract text from DOCX"""
        try:
            import zipfile
            import io
            import re
            
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception as e:
            print(f"DOCX extraction error: {e}")
            return ""
    
    async def llm_extract(self, file_name: str, text: str) -> dict:
        """Extract data using LLM approach"""
        
        json_schema = {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Name of the client company"},
                "project_title": {"type": "string", "description": "Title of the project"},
                "start_date": {"type": "string", "description": "Project start date (YYYY-MM-DD format)"},
                "end_date": {"type": "string", "description": "Project end date (YYYY-MM-DD format)"},
                "project_length": {"type": "string", "description": "Project duration in months, weeks, or other time units"},
                "scope_summary": {"type": "string", "description": "Brief summary of project scope"},
                "deliverables": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "List of project deliverables"
                },
                "exclusions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of explicitly mentioned exclusions or items not included"
                },
                "staffing_plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Employee or role name"},
                            "role": {"type": "string", "description": "Job title or role"},
                            "allocation": {"type": "string", "description": "FTE percentage, hours, or time allocation"}
                        },
                        "required": ["name", "role", "allocation"]
                    },
                    "description": "Project staffing plan with employee details"
                }
            },
            "required": ["client_name", "project_title", "scope_summary", "deliverables", "exclusions", "staffing_plan"]
        }
        
        system_prompt = """You are an expert SOW analyst. Extract the requested information from the SOW document.
        
        Guidelines:
        - Extract only information that is explicitly stated in the document
        - If dates are not provided, leave start_date and end_date as null
        - For project_length, look for explicit duration mentions first
        - For exclusions, look for sections titled "Exclusions", "Not Included", "Out of Scope", or similar language
        - Be precise and accurate - do not infer or assume information
        - Return null for fields that cannot be determined from the text"""
        
        user_prompt = f"""Extract the following information from this SOW document:

        Document: {file_name}
        
        <<<SOW_TEXT_BEGIN>>>
        {text[:15000]}  # Limit text to avoid token limits
        <<<SOW_TEXT_END>>>
        
        Please extract the structured data according to the schema."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-5-mini",
                messages=messages,
                response_format={"type": "json_schema", "json_schema": {"name": "sow_extraction", "schema": json_schema}}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["file_name"] = file_name
            result["extraction_timestamp"] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            print(f"Error in LLM extraction from {file_name}: {e}")
            return {
                "file_name": file_name,
                "client_name": "Error",
                "project_title": "Error",
                "start_date": None,
                "end_date": None,
                "project_length": None,
                "scope_summary": f"Extraction failed: {str(e)}",
                "deliverables": [],
                "exclusions": [],
                "staffing_plan": [],
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
    
    def taxonomy_extract(self, file_name: str, text: str) -> dict:
        """Extract data using taxonomy approach"""
        
        result = {
            "file_name": file_name,
            "client_name": self._extract_client_name(text),
            "project_title": self._extract_project_title(text),
            "start_date": self._extract_start_date(text),
            "end_date": self._extract_end_date(text),
            "project_length": self._extract_project_length(text),
            "scope_summary": self._extract_scope_summary(text),
            "deliverables": self._extract_deliverables(text),
            "exclusions": self._extract_exclusions(text),
            "staffing_plan": self._extract_staffing_plan(text),
            "extraction_timestamp": datetime.utcnow().isoformat()
        }
        
        return result
    
    def _extract_client_name(self, text: str) -> str:
        """Extract client name using taxonomy"""
        keywords = get_field_keywords("client_name")
        
        # Look for contract indicators
        for indicator in keywords["contract_indicators"]:
            pattern = rf"{indicator}\s+([^,]+?)(?:\s+and\s+|\s+vs\.?\s+|\s+versus\s+|\s+\(|\s*$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                client = match.group(1).strip()
                # Filter out obvious non-clients
                if not any(exclude in client.lower() for exclude in keywords["exclusion_patterns"]):
                    return client
        
        # Look for label indicators
        for indicator in keywords["label_indicators"]:
            pattern = rf"{indicator}\s*:?\s*([^\n\r]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                client = match.group(1).strip()
                if not any(exclude in client.lower() for exclude in keywords["exclusion_patterns"]):
                    return client
        
        return "Not found"
    
    def _extract_project_title(self, text: str) -> str:
        """Extract project title using taxonomy"""
        keywords = get_field_keywords("project_title")
        
        for indicator in keywords["title_indicators"]:
            pattern = rf"{indicator}\s*:?\s*([^\n\r]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if not any(exclude in title.lower() for exclude in keywords["exclusion_patterns"]):
                    return title
        
        return "Not found"
    
    def _extract_start_date(self, text: str) -> str:
        """Extract start date using taxonomy"""
        keywords = get_field_keywords("start_date")
        patterns = get_compiled_patterns_for_field("start_date")
        
        # Look for context patterns first
        for pattern in keywords["context_patterns"]:
            context_match = re.search(rf"{pattern}\s*([^\n\r]+)", text, re.IGNORECASE)
            if context_match:
                date_text = context_match.group(1).strip()
                # Try to extract date from the context
                for date_pattern in patterns:
                    date_match = date_pattern.search(date_text)
                    if date_match:
                        return date_match.group(0)
        
        # Look for primary indicators
        for indicator in keywords["primary_indicators"]:
            pattern = rf"{indicator}\s*:?\s*([^\n\r]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_text = match.group(1).strip()
                for date_pattern in patterns:
                    date_match = date_pattern.search(date_text)
                    if date_match:
                        return date_match.group(0)
        
        return "Not found"
    
    def _extract_end_date(self, text: str) -> str:
        """Extract end date using taxonomy"""
        keywords = get_field_keywords("end_date")
        patterns = get_compiled_patterns_for_field("end_date")
        
        # Look for context patterns first
        for pattern in keywords["context_patterns"]:
            context_match = re.search(rf"{pattern}\s*([^\n\r]+)", text, re.IGNORECASE)
            if context_match:
                date_text = context_match.group(1).strip()
                for date_pattern in patterns:
                    date_match = date_pattern.search(date_text)
                    if date_match:
                        return date_match.group(0)
        
        # Look for primary indicators
        for indicator in keywords["primary_indicators"]:
            pattern = rf"{indicator}\s*:?\s*([^\n\r]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_text = match.group(1).strip()
                for date_pattern in patterns:
                    date_match = date_pattern.search(date_text)
                    if date_match:
                        return date_match.group(0)
        
        return "Not found"
    
    def _extract_project_length(self, text: str) -> str:
        """Extract project length using taxonomy"""
        keywords = get_field_keywords("project_length")
        patterns = get_compiled_patterns_for_field("project_length")
        
        for indicator in keywords["duration_indicators"]:
            pattern = rf"{indicator}\s*:?\s*([^\n\r]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration_text = match.group(1).strip()
                for duration_pattern in patterns:
                    duration_match = duration_pattern.search(duration_text)
                    if duration_match:
                        return duration_match.group(0)
        
        return "Not found"
    
    def _extract_scope_summary(self, text: str) -> str:
        """Extract scope summary using taxonomy"""
        keywords = get_field_keywords("scope_summary")
        
        for header in keywords["section_headers"]:
            pattern = rf"{header}[:\s]*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*\n|\n[A-Z][A-Z\s]+:|\n\d+\.|\Z)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                if len(summary) > 50:  # Ensure it's substantial
                    return summary[:500] + "..." if len(summary) > 500 else summary
        
        return "Not found"
    
    def _extract_deliverables(self, text: str) -> list:
        """Extract deliverables using taxonomy"""
        keywords = get_field_keywords("deliverables")
        deliverables = []
        
        for header in keywords["section_headers"]:
            # Find the deliverables section
            pattern = rf"{header}[:\s]*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*\n|\n[A-Z][A-Z\s]+:|\Z)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1)
                
                # Extract list items
                for indicator in keywords["list_indicators"]:
                    pattern = rf"{re.escape(indicator)}\s*([^\n\r]+)"
                    matches = re.findall(pattern, section_text)
                    for item in matches:
                        item = item.strip()
                        if len(item) > 10:  # Ensure it's substantial
                            deliverables.append(item)
        
        return deliverables if deliverables else []
    
    def _extract_exclusions(self, text: str) -> list:
        """Extract exclusions using taxonomy"""
        keywords = get_field_keywords("exclusions")
        exclusions = []
        
        for header in keywords["section_headers"]:
            pattern = rf"{header}[:\s]*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*\n|\n[A-Z][A-Z\s]+:|\Z)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1)
                
                for indicator in keywords["list_indicators"]:
                    pattern = rf"{re.escape(indicator)}\s*([^\n\r]+)"
                    matches = re.findall(pattern, section_text)
                    for item in matches:
                        item = item.strip()
                        if len(item) > 10:
                            exclusions.append(item)
        
        return exclusions if exclusions else []
    
    def _extract_staffing_plan(self, text: str) -> list:
        """Extract staffing plan using taxonomy"""
        keywords = get_field_keywords("staffing_plan")
        staffing = []
        
        for header in keywords["section_headers"]:
            pattern = rf"{header}[:\s]*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*\n|\n[A-Z][A-Z\s]+:|\Z)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1)
                
                # Look for table patterns
                lines = section_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if any(indicator in line.lower() for indicator in keywords["table_indicators"]):
                        # This looks like a staffing entry
                        staffing.append(line)
        
        return staffing if staffing else []
    
    def compare_extractions(self, llm_result: dict, taxonomy_result: dict) -> dict:
        """Compare LLM and taxonomy extraction results"""
        
        comparison = {
            "file_name": llm_result["file_name"],
            "fields": {}
        }
        
        fields_to_compare = [
            "client_name", "project_title", "start_date", "end_date", 
            "project_length", "scope_summary", "deliverables", "exclusions", "staffing_plan"
        ]
        
        for field in fields_to_compare:
            llm_value = llm_result.get(field, "")
            taxonomy_value = taxonomy_result.get(field, "")
            
            # Handle different data types
            if isinstance(llm_value, list):
                llm_value = len(llm_value)
            if isinstance(taxonomy_value, list):
                taxonomy_value = len(taxonomy_value)
            
            # Determine match status
            if llm_value == taxonomy_value:
                status = "Match"
            elif llm_value and not taxonomy_value:
                status = "LLM Only"
            elif taxonomy_value and not llm_value:
                status = "Taxonomy Only"
            else:
                status = "Different"
            
            comparison["fields"][field] = {
                "llm_value": llm_value,
                "taxonomy_value": taxonomy_value,
                "status": status
            }
        
        return comparison
    
    def create_comparison_charts(self, results: list):
        """Create comparison charts"""
        
        # Prepare data for charts
        field_stats = {}
        file_stats = {}
        
        for result in results:
            file_name = result["file_name"]
            file_stats[file_name] = {"total_fields": 0, "matches": 0, "llm_only": 0, "taxonomy_only": 0, "different": 0}
            
            for field, data in result["fields"].items():
                if field not in field_stats:
                    field_stats[field] = {"matches": 0, "llm_only": 0, "taxonomy_only": 0, "different": 0}
                
                file_stats[file_name]["total_fields"] += 1
                status_key = data["status"].lower().replace(" ", "_")
                if status_key in file_stats[file_name]:
                    file_stats[file_name][status_key] += 1
                if status_key in field_stats[field]:
                    field_stats[field][status_key] += 1
        
        # Create charts
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('SOW Extraction Methods Comparison', fontsize=16, fontweight='bold')
        
        # Chart 1: Field-level comparison
        field_df = pd.DataFrame(field_stats).T
        field_df.plot(kind='bar', ax=axes[0,0], stacked=True, color=['green', 'blue', 'orange', 'red'])
        axes[0,0].set_title('Field-Level Comparison')
        axes[0,0].set_xlabel('Fields')
        axes[0,0].set_ylabel('Count')
        axes[0,0].legend(['Match', 'LLM Only', 'Taxonomy Only', 'Different'])
        axes[0,0].tick_params(axis='x', rotation=45)
        
        # Chart 2: File-level comparison
        file_df = pd.DataFrame(file_stats).T
        file_df[['matches', 'llm_only', 'taxonomy_only', 'different']].plot(kind='bar', ax=axes[0,1], stacked=True, color=['green', 'blue', 'orange', 'red'])
        axes[0,1].set_title('File-Level Comparison')
        axes[0,1].set_xlabel('Files')
        axes[0,1].set_ylabel('Count')
        axes[0,1].legend(['Match', 'LLM Only', 'Taxonomy Only', 'Different'])
        axes[0,1].tick_params(axis='x', rotation=45)
        
        # Chart 3: Match rate by field
        match_rates = {}
        for field, stats in field_stats.items():
            total = sum(stats.values())
            match_rates[field] = (stats['matches'] / total * 100) if total > 0 else 0
        
        axes[1,0].bar(match_rates.keys(), match_rates.values(), color='skyblue')
        axes[1,0].set_title('Match Rate by Field (%)')
        axes[1,0].set_xlabel('Fields')
        axes[1,0].set_ylabel('Match Rate (%)')
        axes[1,0].tick_params(axis='x', rotation=45)
        
        # Chart 4: Overall statistics
        total_matches = sum(stats['matches'] for stats in field_stats.values())
        total_llm_only = sum(stats['llm_only'] for stats in field_stats.values())
        total_taxonomy_only = sum(stats['taxonomy_only'] for stats in field_stats.values())
        total_different = sum(stats['different'] for stats in field_stats.values())
        
        overall_stats = [total_matches, total_llm_only, total_taxonomy_only, total_different]
        labels = ['Match', 'LLM Only', 'Taxonomy Only', 'Different']
        colors = ['green', 'blue', 'orange', 'red']
        
        axes[1,1].pie(overall_stats, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        axes[1,1].set_title('Overall Distribution')
        
        plt.tight_layout()
        
        # Save the chart
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_filename = f"extraction_comparison_{timestamp}.png"
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
        print(f"📊 Comparison chart saved: {chart_filename}")
        
        return chart_filename
    
    def create_detailed_comparison_csv(self, results: list):
        """Create detailed comparison CSV"""
        
        detailed_rows = []
        
        for result in results:
            file_name = result["file_name"]
            
            for field, data in result["fields"].items():
                row = {
                    "File Name": file_name,
                    "Field": field,
                    "LLM Value": str(data["llm_value"]),
                    "Taxonomy Value": str(data["taxonomy_value"]),
                    "Status": data["status"],
                    "LLM Has Value": bool(data["llm_value"]),
                    "Taxonomy Has Value": bool(data["taxonomy_value"])
                }
                detailed_rows.append(row)
        
        df = pd.DataFrame(detailed_rows)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"detailed_comparison_{timestamp}.csv"
        df.to_csv(csv_filename, index=False)
        
        print(f"📋 Detailed comparison CSV saved: {csv_filename}")
        return csv_filename
    
    async def run_comparison(self):
        """Run the complete comparison analysis"""
        
        print("🔍 SOW EXTRACTION METHODS COMPARISON")
        print("=" * 60)
        
        # Initialize services
        if not await self.initialize():
            return False
        
        # Get SOW files from local directory
        sows_directory = Path("sows")
        if not sows_directory.exists():
            print(f"❌ SOWs directory not found: {sows_directory}")
            return False
        
        sow_files = []
        for file_path in sows_directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.docx']:
                sow_files.append(file_path)
        
        print(f"📄 Found {len(sow_files)} SOW files to process")
        
        # Process each file
        for i, file_path in enumerate(sow_files, 1):
            print(f"\n📋 Processing {i}/{len(sow_files)}: {file_path.name}")
            
            # Extract text
            print("  🔍 Extracting text...")
            text = self.extract_text_from_file(file_path)
            if not text:
                print(f"  ❌ Failed to extract text from {file_path.name}")
                continue
            
            print(f"  📝 Extracted {len(text)} characters")
            
            # Run LLM extraction
            print("  🤖 Running LLM extraction...")
            llm_result = await self.llm_extract(file_path.name, text)
            
            # Run taxonomy extraction
            print("  🔧 Running taxonomy extraction...")
            taxonomy_result = self.taxonomy_extract(file_path.name, text)
            
            # Compare results
            print("  📊 Comparing results...")
            comparison = self.compare_extractions(llm_result, taxonomy_result)
            self.results.append(comparison)
            
            print(f"  ✅ Completed: {file_path.name}")
        
        if not self.results:
            print("❌ No results to analyze")
            return False
        
        # Create comparison charts
        print(f"\n📊 Creating comparison charts...")
        chart_filename = self.create_comparison_charts(self.results)
        
        # Create detailed comparison CSV
        print(f"📋 Creating detailed comparison CSV...")
        csv_filename = self.create_detailed_comparison_csv(self.results)
        
        # Print summary
        print(f"\n📈 COMPARISON SUMMARY")
        print("=" * 60)
        
        field_stats = {}
        for result in self.results:
            for field, data in result["fields"].items():
                if field not in field_stats:
                    field_stats[field] = {"matches": 0, "llm_only": 0, "taxonomy_only": 0, "different": 0}
                status_key = data["status"].lower().replace(" ", "_")
                if status_key in field_stats[field]:
                    field_stats[field][status_key] += 1
        
        for field, stats in field_stats.items():
            total = sum(stats.values())
            match_rate = (stats['matches'] / total * 100) if total > 0 else 0
            print(f"  {field}: {match_rate:.1f}% match rate ({stats['matches']}/{total})")
        
        print(f"\n✅ Comparison analysis complete!")
        print(f"   📊 Chart: {chart_filename}")
        print(f"   📋 CSV: {csv_filename}")
        
        return True

async def main():
    """Main function"""
    comparator = SOWExtractionComparator()
    await comparator.run_comparison()

if __name__ == "__main__":
    asyncio.run(main())
