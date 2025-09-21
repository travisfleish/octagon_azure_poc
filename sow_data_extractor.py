#!/usr/bin/env python3
"""
SOW Data Extractor
==================

Extracts standardized data from SOW documents using Azure OpenAI GPT-5-mini
and compiles results into a spreadsheet.

Parameters extracted:
- Client Name
- Project Title  
- Start Date
- End Date
- Project Length
- Scope Summary
- Deliverables
- Exclusions
- Staffing Plan
"""

import os
import json
import asyncio
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from pathlib import Path

from openai import AsyncOpenAI
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential


class SOWDataExtractor:
    """Extracts structured data from SOW documents using Azure OpenAI"""
    
    def __init__(self, sows_directory: str = "sows"):
        self.sows_directory = Path(sows_directory)
        self.openai_client = None
        self.blob_service_client = None
        self.container_name = "parsed"
    
    def calculate_project_length(self, start_date_str: str, end_date_str: str) -> str:
        """Calculate project length from start and end dates"""
        if not start_date_str or not end_date_str:
            return None
        
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            delta = end_date - start_date
            days = delta.days
            
            if days >= 365:
                months = round(days / 30.44)
                return f"{months} months"
            elif days >= 30:
                weeks = round(days / 7)
                return f"{weeks} weeks"
            else:
                return f"{days} days"
        except ValueError:
            return None
        
    async def initialize(self):
        """Initialize Azure OpenAI client and Azure Storage client"""
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
            print("⚠️  AZURE_STORAGE_ACCOUNT_URL not found - Azure Storage upload will be skipped")
        
    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from a local file using PyPDF2 or zipfile"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Determine file type and extract text
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
        """Extract text from PDF using multiple methods"""
        try:
            import PyPDF2
            import io
            
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            text = ""
            for page in reader.pages[:10]:  # Limit to first 10 pages
                text += page.extract_text() + "\n"
            
            # If we got very little text, try pdfplumber
            if len(text.strip()) < 500:
                print("  🔄 Low text extraction, trying pdfplumber...")
                text = self._extract_pdf_with_pdfplumber(data)
            
            # If still low text, try OCR
            if len(text.strip()) < 500:
                print("  🔄 Still low text, trying OCR...")
                text = self._extract_pdf_with_ocr(data)
            
            return text
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return ""
    
    def _extract_pdf_with_pdfplumber(self, data: bytes) -> str:
        """Extract text using pdfplumber"""
        try:
            import pdfplumber
            import io
            
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                text = ""
                for page in pdf.pages[:10]:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Also try to extract tables and convert to text
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            for row in table:
                                if row:
                                    row_text = " | ".join([str(cell) for cell in row if cell])
                                    if row_text.strip():
                                        text += row_text + "\n"
                return text
        except Exception as e:
            print(f"PDFplumber extraction error: {e}")
            return ""
    
    def _extract_pdf_with_ocr(self, data: bytes) -> str:
        """Extract text using OCR"""
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            import io
            
            # Convert PDF pages to images
            images = convert_from_bytes(data, first_page=1, last_page=10)
            
            text = ""
            for i, image in enumerate(images):
                try:
                    # Use OCR to extract text from image
                    page_text = pytesseract.image_to_string(image)
                    if page_text.strip():
                        text += f"--- PAGE {i+1} ---\n{page_text}\n"
                except Exception as e:
                    print(f"  OCR error on page {i+1}: {e}")
                    continue
            
            return text
        except Exception as e:
            print(f"OCR extraction error: {e}")
            return ""
    
    def _extract_docx_text(self, data: bytes) -> str:
        """Extract text from DOCX using zipfile"""
        try:
            import zipfile
            import io
            import re
            
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            
            # Remove XML tags and clean up text
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception as e:
            print(f"DOCX extraction error: {e}")
            return ""
    
    async def extract_sow_data(self, file_name: str, text: str) -> Dict[str, Any]:
        """Extract structured data from SOW text using GPT-5-mini"""
        
        # First, try targeted staffing extraction
        print("  👥 Extracting staffing plan with targeted approach...")
        staffing_plan = await self.extract_staffing_plan_targeted(text)
        
        # JSON schema for structured output
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
        - For project_length, look for explicit duration mentions first (e.g., "12 months", "6 weeks"). If not found but dates are available, calculate the duration
        - For exclusions, look for sections titled "Exclusions", "Not Included", "Out of Scope", or similar language
        
        CRITICAL - For staffing_plan extraction:
        - Look for explicit "Staffing Plan", "Staff Plan", or similar sections first
        - ALSO look for staffing data in sections titled "Fees", "Resources", "Personnel", "Team", or any table containing:
          * Personnel/Staff names (even if redacted as [BLACKED OUT])
          * Job levels/roles (EVP, VP, Director, Manager, etc.)
          * Time allocations (% Time, FTE, hours, days, months)
          * Locations (US, UK, etc.)
        - Extract structured tables that show:
          * Personnel names (use "N/A" if redacted/blacked out)
          * Roles/titles/levels 
          * Allocations (hours, percentages, FTE, days, months)
        - Look for patterns in tables with columns like:
          * "Name" + "Title/Role" + "Hours/%/FTE"
          * "Personnel" + "Level" + "% Time" + "hours"
          * "Staff" + "Position" + "Allocation"
        - Include ANY structured data that shows who is working on the project and how much time they're allocated
        - Be thorough - staffing information may be in fee tables, resource tables, or other sections
        
        EXAMPLES of what to extract:
        - "David Hargis, SVP, 45 hours, 2.50%" -> name: "David Hargis", role: "SVP", allocation: "45 hours (2.50%)"
        - "[BLACKED OUT], EVP, 1%, 9 hours" -> name: "N/A", role: "EVP", allocation: "9 hours (1%)"
        - Table with columns "Personnel", "Level", "% Time", "hours" -> extract each row as staffing plan entry
        - "Vice President Client Services 67 Sr. Project Manager Client Services 265" -> 
          [{"name": "Vice President", "role": "Client Services", "allocation": "67 hours"}, {"name": "Sr. Project Manager", "role": "Client Services", "allocation": "265 hours"}]
        - "Title Discipline Hours Vice President Client Services 67 Sr. Vice President Strategy 194" -> extract each role as separate entry
        
        - Be precise and accurate - do not infer or assume information
        - Return null for fields that cannot be determined from the text
        - If absolutely no staffing information is found, return an empty array"""
        
        user_prompt = f"""Extract the following information from this SOW document:

        Document: {file_name}
        
        <<<SOW_TEXT_BEGIN>>>
        {text[:15000]}  # Limit text to avoid token limits
        <<<SOW_TEXT_END>>>
        
        IMPORTANT: Do NOT extract staffing_plan information - that will be handled separately.
        Focus on extracting client_name, project_title, scope_summary, deliverables, and exclusions.
        
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
            
            # Add the pre-extracted staffing plan
            result["staffing_plan"] = staffing_plan
            
            # Calculate project length if not provided explicitly
            if not result.get("project_length") and result.get("start_date") and result.get("end_date"):
                calculated_length = self.calculate_project_length(result["start_date"], result["end_date"])
                if calculated_length:
                    result["project_length"] = f"{result.get('project_length', '')} (calculated: {calculated_length})".strip()
            
            result["extraction_timestamp"] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            print(f"Error extracting data from {file_name}: {e}")
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
    
    async def extract_staffing_plan_targeted(self, text: str) -> list:
        """Extract staffing plan using targeted approach for better accuracy"""
        try:
            # Look for multiple staffing plan patterns
            staffing_sections = []
            
            # Pattern 1: "Title Discipline Hours" (company_3_sow_1.docx)
            if 'Title Discipline Hours' in text:
                start_idx = text.find('Title Discipline Hours')
                if start_idx != -1:
                    if 'Jr. Analyst TV/Broadcast Exposure 291.5' in text:
                        end_idx = text.find('Jr. Analyst TV/Broadcast Exposure 291.5') + len('Jr. Analyst TV/Broadcast Exposure 291.5')
                        section = text[start_idx:end_idx]
                    else:
                        section = text[start_idx:start_idx + 10000]
                    staffing_sections.append(section)
            
            # Pattern 2: Look for other staffing-related sections
            staffing_keywords = ['staffing', 'staff plan', 'personnel', 'team', 'resources', 'fees']
            
            # Split text into lines and look for staffing sections
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in staffing_keywords):
                    # Extract context around this line
                    start = max(0, i-3)
                    end = min(len(lines), i+15)
                    section = '\n'.join(lines[start:end])
                    staffing_sections.append(section)
            
            # If we found staffing sections, use them
            if staffing_sections:
                # Prioritize the "Title Discipline Hours" pattern if it exists
                title_discipline_sections = [s for s in staffing_sections if 'Title Discipline Hours' in s]
                if title_discipline_sections:
                    combined_sections = title_discipline_sections[0]
                else:
                    # Use the longest section (most likely to contain complete data)
                    combined_sections = max(staffing_sections, key=len)
                
                # Use targeted prompt for staffing extraction
                prompt = f"""Extract staffing information from this text. Look for any structured staffing data including:

Text: {combined_sections[:5000]}

Look for staffing information in these formats:
1. Continuous text: "Vice President Client Services 67 Sr. Project Manager Client Services 265"
2. Tables with columns: Name | Role | Hours | Allocation
3. Lists with personnel: "John Smith, Director, 50% allocation"
4. Any structured data showing team members, roles, and time allocations

Extract ALL staffing entries found. Each entry should have:
- name: the person's name or role title
- role: the job title, discipline, or department
- allocation: hours, percentage, FTE, or time allocation

Return ONLY a JSON array. If no staffing information is found, return an empty array: []

Examples of what to extract:
- "David Hargis, SVP, 45 hours, 2.50%" → {{"name": "David Hargis", "role": "SVP", "allocation": "45 hours (2.50%)"}}
- "Vice President Client Services 67" → {{"name": "Vice President", "role": "Client Services", "allocation": "67 hours"}}
- Table rows with Name/Role/Hours columns → extract each row as a separate entry"""
                
                response = await self.openai_client.chat.completions.create(
                    model=os.getenv('AZURE_OPENAI_DEPLOYMENT'),
                    messages=[
                        {'role': 'system', 'content': 'You are a data extraction expert. Extract staffing information and return only valid JSON.'},
                        {'role': 'user', 'content': prompt}
                    ]
                )
                
                result = response.choices[0].message.content.strip()
                import json
                return json.loads(result)
            
            return []
            
        except Exception as e:
            print(f"Error in targeted staffing extraction: {e}")
            return []
    
    async def upload_json_to_storage(self, file_name: str, data: dict) -> bool:
        """Upload extracted JSON data to Azure Storage parsed container"""
        try:
            if not self.blob_service_client:
                print("  ⚠️  Azure Storage client not initialized - skipping upload")
                return False
            
            # Create JSON blob name
            json_blob_name = f"{file_name.replace('.pdf', '').replace('.docx', '')}_parsed.json"
            
            # Convert data to JSON string
            json_data = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Upload to Azure Storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=json_blob_name
            )
            
            await blob_client.upload_blob(
                json_data.encode('utf-8'),
                overwrite=True,
                content_type="application/json"
            )
            
            print(f"  📤 Uploaded JSON to Azure Storage: {json_blob_name}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error uploading to Azure Storage: {e}")
            return False
    
    def get_sow_files(self) -> List[Path]:
        """Get list of SOW files from local directory"""
        try:
            if not self.sows_directory.exists():
                print(f"SOWs directory not found: {self.sows_directory}")
                return []
            
            files = []
            for file_path in self.sows_directory.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.docx']:
                    files.append(file_path)
            return files
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    async def process_all_sows(self) -> List[Dict[str, Any]]:
        """Process all SOW documents and extract data"""
        print("🔄 Getting list of SOW documents...")
        file_paths = self.get_sow_files()
        print(f"📄 Found {len(file_paths)} SOW documents")
        
        results = []
        
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n📋 Processing {i}/{len(file_paths)}: {file_path.name}")
            
            # Extract text
            print("  🔍 Extracting text...")
            text = self.extract_text_from_file(file_path)
            if not text:
                print(f"  ❌ Failed to extract text from {file_path.name}")
                continue
            
            print(f"  📝 Extracted {len(text)} characters")
            
            # Extract structured data
            print("  🤖 Extracting structured data with GPT-5-mini...")
            data = await self.extract_sow_data(file_path.name, text)
            
            # Upload JSON data to Azure Storage
            print("  📤 Uploading JSON to Azure Storage...")
            await self.upload_json_to_storage(file_path.name, data)
            
            results.append(data)
            
            print(f"  ✅ Completed: {data.get('client_name', 'Unknown')} - {data.get('project_title', 'Unknown')}")
        
        return results
    
    def save_to_spreadsheet(self, results: List[Dict[str, Any]], filename: str = None):
        """Save results to Excel spreadsheet"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sow_extraction_results_{timestamp}.xlsx"
        
        # Prepare data for DataFrame
        rows = []
        for result in results:
            # Format staffing plan as readable text
            staffing_plan_text = ""
            staffing_plan = result.get("staffing_plan", [])
            if staffing_plan:
                staffing_items = []
                for person in staffing_plan:
                    name = person.get("name", "N/A")
                    role = person.get("role", "N/A")
                    allocation = person.get("allocation", "N/A")
                    staffing_items.append(f"{name} ({role}): {allocation}")
                staffing_plan_text = " | ".join(staffing_items)
            
            row = {
                "File Name": result.get("file_name", ""),
                "Client Name": result.get("client_name", ""),
                "Project Title": result.get("project_title", ""),
                "Start Date": result.get("start_date", ""),
                "End Date": result.get("end_date", ""),
                "Project Length": result.get("project_length", ""),
                "Scope Summary": result.get("scope_summary", ""),
                "Deliverables": " | ".join(result.get("deliverables", [])),
                "Exclusions": " | ".join(result.get("exclusions", [])),
                "Staffing Plan": staffing_plan_text,
                "Extraction Timestamp": result.get("extraction_timestamp", "")
            }
            rows.append(row)
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(rows)
        df.to_excel(filename, index=False, sheet_name="SOW Extraction Results")
        
        print(f"\n📊 Results saved to: {filename}")
        print(f"📈 Processed {len(results)} SOW documents")
        
        return filename


async def main():
    """Main execution function"""
    print("🚀 SOW Data Extractor Starting...")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # Initialize extractor
    extractor = SOWDataExtractor()
    await extractor.initialize()
    
    # Process all SOWs
    results = await extractor.process_all_sows()
    
    if results:
        # Save to spreadsheet
        filename = extractor.save_to_spreadsheet(results)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 EXTRACTION SUMMARY")
        print("=" * 50)
        
        for result in results:
            print(f"\n📄 {result.get('file_name', 'Unknown')}")
            print(f"   Client: {result.get('client_name', 'Unknown')}")
            print(f"   Project: {result.get('project_title', 'Unknown')}")
            print(f"   Length: {result.get('project_length', 'Unknown')}")
            print(f"   Deliverables: {len(result.get('deliverables', []))} items")
            print(f"   Exclusions: {len(result.get('exclusions', []))} items")
            print(f"   Staffing Plan: {len(result.get('staffing_plan', []))} people")
        
        print(f"\n✅ Extraction complete! Results saved to: {filename}")
    else:
        print("❌ No results to save")


if __name__ == "__main__":
    asyncio.run(main())
