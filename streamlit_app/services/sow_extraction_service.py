#!/usr/bin/env python3
"""
SOW Extraction Service
=====================

Core service for extracting structured data from SOW documents using Azure OpenAI.
Refactored from sow_data_extractor.py to be reusable across different applications.
"""

import os
import json
import asyncio
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass

from openai import AsyncOpenAI
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential
try:
    # Optional: Azure Document Intelligence service for PDF table extraction
    from .document_intelligence_service import AzureDocumentIntelligenceService
    _DOCINT_AVAILABLE = True
except Exception:
    _DOCINT_AVAILABLE = False


@dataclass
class ExtractionResult:
    """Result of SOW extraction process"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    file_name: Optional[str] = None
    processing_time: Optional[float] = None


@dataclass
class ExtractionProgress:
    """Progress tracking for extraction process"""
    stage: str
    message: str
    percentage: int
    details: Optional[Dict[str, Any]] = None


class SOWExtractionService:
    """Core service for extracting structured data from SOW documents using Azure OpenAI"""
    
    def __init__(self, sows_directory: str = "sows"):
        self.sows_directory = Path(sows_directory)
        self.openai_client = None
        self.blob_service_client = None
        self.containers = {
            "sows": "sows",           # Raw original files
            "extracted": "extracted", # Extracted text files
            "parsed": "parsed"        # Structured JSON data
        }
        self.progress_callback: Optional[Callable[[ExtractionProgress], None]] = None
    
    def set_progress_callback(self, callback: Callable[[ExtractionProgress], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback
    
    def _update_progress(self, stage: str, message: str, percentage: int, details: Optional[Dict[str, Any]] = None):
        """Update progress if callback is set"""
        if self.progress_callback:
            progress = ExtractionProgress(stage=stage, message=message, percentage=percentage, details=details)
            self.progress_callback(progress)
    
    async def initialize(self):
        """Initialize Azure OpenAI client and Azure Storage client"""
        self._update_progress("initialization", "Initializing Azure services...", 0)
        
        # Note: SSL certificates should now work properly after upgrading certifi
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/openai/deployments/{os.getenv('AZURE_OPENAI_DEPLOYMENT')}",
            default_query={"api-version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")}
        )
        
        # Initialize Azure Storage client
        account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        if account_url:
            import certifi
            
            # Set environment variables to use certifi's certificate bundle
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
            os.environ['SSL_CERT_FILE'] = certifi.where()
            
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
            self._update_progress("initialization", f"Connected to Azure Storage: {account_url}", 20)
        else:
            self._update_progress("initialization", "Azure Storage not configured - upload will be skipped", 20)
        
        self._update_progress("initialization", "Azure services initialized successfully", 100)
    
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
    
    def normalize_staffing_allocation(self, allocation_text: str) -> str:
        """
        Normalize staffing allocation to percentage format based on 1800-hour annual basis.
        
        Examples:
        - "45 hours (2.50%)" -> "2.5%"
        - "9 hours (1%)" -> "1.0%"
        - "67 hours" -> "3.7%" (67/1800*100)
        - "525 hrs (25% + Onboarding)" -> "25.0%"
        - "5% – 60 hrs" -> "5.0%"
        - "100%" -> "100.0%"
        """
        if not allocation_text or not allocation_text.strip():
            return "0.0%"
        
        import re
        
        allocation_text = allocation_text.strip()
        
        # First, try to extract percentage if it exists
        percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*%', allocation_text, re.IGNORECASE)
        
        if percentage_match:
            # If percentage is found, use it
            percentage = float(percentage_match.group(1))
            return f"{percentage:.1f}%"
        
        # If no percentage found, try to extract hours
        hours_match = re.search(r'(\d+(?:\.\d+)?)\s*h(?:ours?|rs?)?', allocation_text, re.IGNORECASE)
        
        if hours_match:
            # Convert hours to percentage based on 1800-hour annual basis
            hours = float(hours_match.group(1))
            percentage = (hours / 1800) * 100
            return f"{percentage:.1f}%"
        
        # If neither percentage nor hours found, return original text
        return allocation_text
    
    def normalize_staffing_plan(self, staffing_plan: list) -> list:
        """
        Normalize all staffing plan entries to use percentage-based allocations.
        
        Args:
            staffing_plan: List of staffing entries with name, role, allocation
            
        Returns:
            List of normalized staffing entries with percentage allocations
        """
        if not staffing_plan:
            return []
        
        normalized_plan = []
        
        for entry in staffing_plan:
            if not isinstance(entry, dict):
                continue
                
            # Create normalized entry
            normalized_entry = {
                'name': entry.get('name', 'N/A'),
                'role': entry.get('role', 'N/A'),
                'allocation': self.normalize_staffing_allocation(entry.get('allocation', ''))
            }
            
            normalized_plan.append(normalized_entry)
        
        return normalized_plan

    def _canonicalize_header(self, header_cell: str) -> str:
        h = (header_cell or '').strip().lower()
        import re as _re
        h = _re.sub(r"\s+", " ", h)
        if any(k in h for k in ["name", "personnel", "staff"]):
            return "name"
        if any(k in h for k in ["title", "role", "position"]):
            if "primary role" in h:
                return "primary_role"
            return "role"
        if "%" in h or "percent" in h or "% time" in h:
            return "percentage"
        if h.strip(" #") == "hours" or "# hours" in h:
            return "hours"
        if "billable hours per annum" in h:
            return "bhpa"
        if "hour" in h:
            return "hours"
        if "location" in h:
            return "location"
        if "level" in h:
            return "level"
        if any(k in h for k in ["workstream", "discipline", "department"]):
            return "workstream"
        return h

    def _extract_numeric_percentage(self, text: str) -> float:
        if not text:
            return None
        import re as _re
        m = _re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
        m = _re.search(r"(\d(?:\.\d+)?)\s*fte", text, _re.I)
        if m:
            try:
                return float(m.group(1)) * 100.0
            except Exception:
                return None
        return None

    def _extract_numeric_hours(self, text: str) -> float:
        if not text:
            return None
        import re as _re
        m = _re.search(r"(\d{1,4}(?:\.\d+)?)\s*(?:hours|hrs|hr)\b", text, _re.I)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
        m = _re.fullmatch(r"\d{1,4}(?:\.\d+)?", text.strip())
        if m:
            try:
                return float(m.group(0))
            except Exception:
                return None
        return None

    def _parse_di_table_to_entries(self, matrix: list, page_number: int, table_index: int) -> list:
        if not matrix or not matrix[0]:
            return []
        import re as _re
        # Pick best header row among first 3
        def _score(row: list) -> int:
            toks = [str(t or '').strip().lower() for t in row]
            score = 0
            for t in toks:
                if any(k in t for k in ["name", "personnel", "staff"]): score += 3
                if any(k in t for k in ["title", "role", "position"]): score += 3
                if "level" in t: score += 1
                if "%" in t or "percent" in t or "% time" in t: score += 2
                if "# hours" in t or t.strip(" #") == "hours": score += 3
            return score
        search_up_to = min(3, len(matrix))
        header_idx = 0
        best_score = _score(matrix[0])
        for i in range(1, search_up_to):
            s = _score(matrix[i])
            if s > best_score:
                best_score = s
                header_idx = i
        headers_raw = matrix[header_idx]
        headers = [self._canonicalize_header(h) for h in headers_raw]
        # Build index
        idx = {}
        for i, h in enumerate(headers):
            if h not in idx:
                idx[h] = i
        # Fill blank headers based on sample data
        for c in range(len(headers)):
            if headers[c]:
                continue
            samples = []
            for r in range(header_idx + 1, min(len(matrix), header_idx + 6)):
                if c < len(matrix[r]):
                    samples.append((matrix[r][c] or '').strip())
            if any('%' in v for v in samples):
                headers[c] = 'percentage'
            elif any(_re.fullmatch(r"\d{1,4}(?:[.,]\d+)?", v.replace(',', '')) for v in samples if v):
                headers[c] = 'hours'
        def get(col: str, row: list) -> str:
            j = idx.get(col)
            if j is None or j >= len(row):
                return ''
            return (row[j] or '').strip()
        entries = []
        for r_idx, row in enumerate(matrix[header_idx + 1 :], start=1):
            if not any((cell or '').strip() for cell in row):
                continue
            # Filter totals
            if any(str(cell or '').strip().lower().startswith('total') for cell in row):
                continue
            name = get('name', row) or 'N/A'
            role = get('role', row)
            primary_role = get('primary_role', row)
            level = get('level', row)
            location = get('location', row)
            workstream = get('workstream', row)
            pct_text = get('percentage', row)
            hours_text = get('hours', row)
            pct_val = self._extract_numeric_percentage(pct_text)
            hours_clean = (hours_text or '').replace(',', '').strip()
            if _re.fullmatch(r"\d{1,3}(?:\.\d{3})+", hours_clean):
                hours_clean = hours_clean.replace('.', '')
            hours_val = self._extract_numeric_hours(hours_clean)
            if pct_val is None and hours_text:
                pct_val = self._extract_numeric_percentage(hours_text)
            if hours_val is None and pct_text:
                hours_val = self._extract_numeric_hours(pct_text)
            column_values = {str(headers_raw[i]).strip(): (row[i] if i < len(row) else '') for i in range(len(headers_raw))}
            entries.append({
                'name': name,
                'role': role or primary_role or '',
                'primary_role': primary_role or '',
                'level': level or '',
                'workstream': workstream or '',
                'location': location or '',
                'percentage': pct_val,
                'hours': hours_val,
                'page': page_number,
                'source_table_index': table_index,
                'row_index': r_idx,
                'column_values': column_values,
            })
        return entries

    def _to_minimal_staffing(self, di_entries: list) -> list:
        """Convert DI entries to minimal schema: name, level, title, primary_role, hours, hours_pct."""
        minimal = []
        FTE_YEARLY_HOURS = 1800.0
        for e in di_entries:
            name = (e.get('name') or '').strip()
            if name.upper() in {'N/A', 'NA', ''}:
                name = None
            level = (e.get('level') or '').strip() or None
            role = (e.get('role') or '').strip() or None
            primary_role = (e.get('primary_role') or '').strip() or None
            title = role or primary_role or level
            if not title:
                continue
            hours = e.get('hours')
            pct = e.get('percentage')
            try:
                hours_val = float(hours) if hours is not None else None
            except Exception:
                hours_val = None
            try:
                pct_val = float(pct) if pct is not None else None
            except Exception:
                pct_val = None
            if pct_val is not None:
                pct_val = max(0.0, min(100.0, pct_val))
                hours_val = (pct_val / 100.0) * FTE_YEARLY_HOURS
            elif hours_val is not None:
                pct_val = (hours_val / FTE_YEARLY_HOURS) * 100.0
            def _round(v):
                if v is None:
                    return None
                try:
                    return round(float(v), 1)
                except Exception:
                    return None
            minimal.append({
                'name': name,
                'level': level,
                'title': title,
                'primary_role': primary_role,
                'hours': _round(hours_val),
                'hours_pct': _round(pct_val),
            })
        return minimal

    def _extract_staffing_via_document_intelligence(self, file_path: Path) -> Dict[str, Any]:
        """Use Azure Document Intelligence for PDFs to extract staffing entries and minimal schema."""
        if not _DOCINT_AVAILABLE or file_path.suffix.lower() != '.pdf':
            return {"entries": [], "minimal": []}
        try:
            di = AzureDocumentIntelligenceService()
            analysis = di.analyze_layout(file_path)
            tables = analysis.get('tables', [])
            all_entries = []
            for idx, table in enumerate(tables, 1):
                matrix = table.to_matrix()
                if not matrix or len(matrix) < 2:
                    continue
                entries = self._parse_di_table_to_entries(matrix, page_number=table.page_number, table_index=idx)
                if entries:
                    all_entries.extend(entries)
            minimal = self._to_minimal_staffing(all_entries)
            return {"entries": all_entries, "minimal": minimal}
        except Exception:
            return {"entries": [], "minimal": []}
    
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
            raise Exception(f"Error extracting text from {file_path}: {e}")
    
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
                self._update_progress("text_extraction", "Low text extraction, trying pdfplumber...", 30)
                text = self._extract_pdf_with_pdfplumber(data)
            
            # If still low text, try OCR
            if len(text.strip()) < 500:
                self._update_progress("text_extraction", "Still low text, trying OCR...", 40)
                text = self._extract_pdf_with_ocr(data)
            
            return text
        except Exception as e:
            raise Exception(f"PDF extraction error: {e}")
    
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
            raise Exception(f"PDFplumber extraction error: {e}")
    
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
                    self._update_progress("text_extraction", f"OCR error on page {i+1}: {e}", 50)
                    continue
            
            return text
        except Exception as e:
            raise Exception(f"OCR extraction error: {e}")
    
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
            raise Exception(f"DOCX extraction error: {e}")
    
    async def extract_sow_data(self, file_name: str, text: str) -> Dict[str, Any]:
        """Extract structured data from SOW text using GPT-5-mini"""
        
        self._update_progress("llm_extraction", "Extracting staffing plan with targeted approach...", 60)
        
        # First, try targeted staffing extraction (best-effort; don't fail pipeline on connection issues)
        try:
            staffing_plan = await self.extract_staffing_plan_targeted(text)
        except Exception as e:
            self._update_progress("llm_extraction", f"Targeted staffing skipped: {e}", 65)
            staffing_plan = []
        
        self._update_progress("llm_extraction", "Extracting structured data with GPT-5-mini...", 70)
        
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
            
            # Normalize staffing plan allocations to percentages
            if result.get("staffing_plan"):
                result["staffing_plan"] = self.normalize_staffing_plan(result["staffing_plan"])
            
            # Calculate project length if not provided explicitly
            if not result.get("project_length") and result.get("start_date") and result.get("end_date"):
                calculated_length = self.calculate_project_length(result["start_date"], result["end_date"])
                if calculated_length:
                    result["project_length"] = f"{result.get('project_length', '')} (calculated: {calculated_length})".strip()
            
            result["extraction_timestamp"] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            raise Exception(f"Error extracting data from {file_name}: {e}")
    
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
- name: the person's name or role title (use "N/A" if name not provided)
- role: the job title, discipline, or department
- allocation: hours, percentage, FTE, or time allocation

Return ONLY a JSON array. If no staffing information is found, return an empty array: []

Examples of what to extract:
- "David Hargis, SVP, 45 hours, 2.50%" → {{"name": "David Hargis", "role": "SVP", "allocation": "45 hours (2.50%)"}}
- "Vice President Client Services 67" → {{"name": "N/A", "role": "Vice President, Client Services", "allocation": "67 hours"}}
- Table rows with Name/Role/Hours columns → extract each row as a separate entry"""
                
                response = await self.openai_client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {'role': 'system', 'content': 'You are a data extraction expert. Extract staffing information and return only valid JSON.'},
                        {'role': 'user', 'content': prompt}
                    ]
                )
                
                result = response.choices[0].message.content.strip()
                import json
                staffing_plan = json.loads(result)
                
                # Normalize the extracted staffing plan
                return self.normalize_staffing_plan(staffing_plan)
            
            return []
            
        except Exception as e:
            raise Exception(f"Error in targeted staffing extraction: {e}")
    
    async def upload_raw_file_to_storage(self, file_path: Path, file_name: str) -> bool:
        """Upload raw file to Azure Storage sows container"""
        try:
            if not self.blob_service_client:
                self._update_progress("upload", "Azure Storage client not initialized - skipping raw file upload", 75)
                return False
            
            # Read file data
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Upload to sows container with timeout
            blob_client = self.blob_service_client.get_blob_client(
                container=self.containers["sows"],
                blob=file_name
            )
            
            # Use asyncio.wait_for to add timeout
            self._update_progress("upload", f"Uploading {file_name} ({len(file_data)} bytes) to sows container...", 75)
            await asyncio.wait_for(
                blob_client.upload_blob(
                    file_data,
                    overwrite=True,
                    content_type="application/pdf" if file_name.lower().endswith('.pdf') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ),
                timeout=120.0  # 2 minute timeout
            )
            
            self._update_progress("upload", f"Uploaded raw file to sows container: {file_name}", 76)
            return True
            
        except asyncio.TimeoutError:
            raise Exception(f"Timeout uploading raw file to Azure Storage: {file_name}")
        except Exception as e:
            raise Exception(f"Error uploading raw file to Azure Storage: {e}")
    
    async def upload_extracted_text_to_storage(self, file_name: str, text: str) -> bool:
        """Upload extracted text to Azure Storage extracted container"""
        try:
            if not self.blob_service_client:
                self._update_progress("upload", "Azure Storage client not initialized - skipping text upload", 77)
                return False
            
            # Create text blob name
            text_blob_name = f"{file_name.replace('.pdf', '').replace('.docx', '')}.txt"
            
            # Upload to extracted container
            blob_client = self.blob_service_client.get_blob_client(
                container=self.containers["extracted"],
                blob=text_blob_name
            )
            
            self._update_progress("upload", f"Uploading extracted text ({len(text)} chars) to extracted container...", 77)
            await asyncio.wait_for(
                blob_client.upload_blob(
                    text.encode('utf-8'),
                    overwrite=True,
                    content_type="text/plain"
                ),
                timeout=60.0  # 1 minute timeout
            )
            
            self._update_progress("upload", f"Uploaded extracted text to extracted container: {text_blob_name}", 78)
            return True
            
        except asyncio.TimeoutError:
            raise Exception(f"Timeout uploading extracted text to Azure Storage: {file_name}")
        except Exception as e:
            raise Exception(f"Error uploading extracted text to Azure Storage: {e}")
    
    async def upload_json_to_storage(self, file_name: str, data: dict) -> bool:
        """Upload extracted JSON data to Azure Storage parsed container"""
        try:
            if not self.blob_service_client:
                self._update_progress("upload", "Azure Storage client not initialized - skipping upload", 80)
                return False
            
            # Create JSON blob name
            json_blob_name = f"{file_name.replace('.pdf', '').replace('.docx', '')}_parsed.json"
            
            # Convert data to JSON string
            json_data = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Upload to parsed container
            blob_client = self.blob_service_client.get_blob_client(
                container=self.containers["parsed"],
                blob=json_blob_name
            )
            
            self._update_progress("upload", f"Uploading structured JSON ({len(json_data)} chars) to parsed container...", 79)
            await asyncio.wait_for(
                blob_client.upload_blob(
                    json_data.encode('utf-8'),
                    overwrite=True,
                    content_type="application/json"
                ),
                timeout=60.0  # 1 minute timeout
            )
            
            self._update_progress("upload", f"Uploaded JSON to Azure Storage: {json_blob_name}", 90)
            return True
            
        except asyncio.TimeoutError:
            raise Exception(f"Timeout uploading JSON to Azure Storage: {file_name}")
        except Exception as e:
            raise Exception(f"Error uploading JSON to Azure Storage: {e}")
    
    def get_sow_files(self) -> List[Path]:
        """Get list of SOW files from local directory"""
        try:
            if not self.sows_directory.exists():
                raise Exception(f"SOWs directory not found: {self.sows_directory}")
            
            files = []
            for file_path in self.sows_directory.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.docx']:
                    files.append(file_path)
            return files
        except Exception as e:
            raise Exception(f"Error listing files: {e}")
    
    async def process_single_sow(self, file_path: Path, skip_uploads: bool = False) -> ExtractionResult:
        """Process a single SOW document and extract data"""
        start_time = datetime.now()
        
        try:
            # Always (re)initialize in the CURRENT event loop to avoid closed-loop issues with async clients
            await self.initialize()
            
            self._update_progress("file_processing", f"Processing {file_path.name}...", 10)
            
            # Extract text
            self._update_progress("text_extraction", "Extracting text from document...", 20)
            text = self.extract_text_from_file(file_path)
            if not text:
                raise Exception(f"Failed to extract text from {file_path.name}")
            
            self._update_progress("text_extraction", f"Extracted {len(text)} characters", 30)
            
            # Extract structured data
            self._update_progress("llm_extraction", "Extracting structured data with GPT-5-mini...", 50)
            data = await self.extract_sow_data(file_path.name, text)

            # If PDF, replace staffing_plan with Document Intelligence minimal
            if file_path.suffix.lower() == '.pdf':
                di_result = self._extract_staffing_via_document_intelligence(file_path)
                if di_result.get('minimal'):
                    data['staffing_plan'] = di_result['minimal']
            
            # Uploads (optional)
            if not skip_uploads:
                self._update_progress("upload", "Uploading files to Azure Storage...", 70)
                # 1. Upload raw file to sows container
                await self.upload_raw_file_to_storage(file_path, file_path.name)
                # 2. Upload extracted text to extracted container
                await self.upload_extracted_text_to_storage(file_path.name, text)
                # 3. Upload structured JSON to parsed container
                await self.upload_json_to_storage(file_path.name, data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self._update_progress("complete", f"Completed: {data.get('client_name', 'Unknown')} - {data.get('project_title', 'Unknown')}", 100)
            
            return ExtractionResult(
                success=True,
                data=data,
                file_name=file_path.name,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return ExtractionResult(
                success=False,
                error=str(e),
                file_name=file_path.name,
                processing_time=processing_time
            )
    
    async def process_all_sows(self) -> List[ExtractionResult]:
        """Process all SOW documents and extract data"""
        self._update_progress("file_discovery", "Getting list of SOW documents...", 0)
        
        file_paths = self.get_sow_files()
        self._update_progress("file_discovery", f"Found {len(file_paths)} SOW documents", 5)
        
        results = []
        
        for i, file_path in enumerate(file_paths, 1):
            self._update_progress("batch_processing", f"Processing {i}/{len(file_paths)}: {file_path.name}", int((i-1) / len(file_paths) * 100))
            
            result = await self.process_single_sow(file_path)
            results.append(result)
        
        return results
    
    def save_to_spreadsheet(self, results: List[ExtractionResult], filename: str = None) -> str:
        """Save results to Excel spreadsheet"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sow_extraction_results_{timestamp}.xlsx"
        
        # Prepare data for DataFrame
        rows = []
        for result in results:
            if not result.success or not result.data:
                continue
                
            # Format staffing plan as readable text
            staffing_plan_text = ""
            staffing_plan = result.data.get("staffing_plan", [])
            if staffing_plan:
                staffing_items = []
                for person in staffing_plan:
                    name = person.get("name", "N/A")
                    role = person.get("role", "N/A")
                    allocation = person.get("allocation", "N/A")
                    staffing_items.append(f"{name} ({role}): {allocation}")
                staffing_plan_text = " | ".join(staffing_items)
            
            row = {
                "File Name": result.data.get("file_name", ""),
                "Client Name": result.data.get("client_name", ""),
                "Project Title": result.data.get("project_title", ""),
                "Start Date": result.data.get("start_date", ""),
                "End Date": result.data.get("end_date", ""),
                "Project Length": result.data.get("project_length", ""),
                "Scope Summary": result.data.get("scope_summary", ""),
                "Deliverables": " | ".join(result.data.get("deliverables", [])),
                "Exclusions": " | ".join(result.data.get("exclusions", [])),
                "Staffing Plan": staffing_plan_text,
                "Extraction Timestamp": result.data.get("extraction_timestamp", ""),
                "Processing Time": result.processing_time
            }
            rows.append(row)
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(rows)
        df.to_excel(filename, index=False, sheet_name="SOW Extraction Results")
        
        return filename
