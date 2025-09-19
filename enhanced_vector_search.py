#!/usr/bin/env python3
"""
Enhanced vector search service that can fetch and display staffing plans from original SOW documents.
"""

import asyncio
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential
from app.config import get_settings
from app.services.embedding_service import EmbeddingService
from process_one_sow import extract_docx_text, extract_pdf_text

class EnhancedVectorSearch:
    """Enhanced vector search service that can fetch staffing plans from original SOWs."""
    
    def __init__(self):
        settings = get_settings()
        self._endpoint = settings.search_endpoint
        self._key = settings.search_key
        self._index_name = "octagon-sows-text-only"
        self._credential = AzureKeyCredential(settings.search_key)
        self._embedding_service = EmbeddingService()
        
        # Azure Storage settings
        self._account_url = "https://octagonstaffingstg5nww.blob.core.windows.net/"
        self._sows_container = "sows"
        
        # Initialize Azure Storage client
        self._credential_storage = DefaultAzureCredential()
        self._blob_service_client = BlobServiceClient(
            account_url=self._account_url,
            credential=self._credential_storage
        )

    async def _get_search_client(self):
        return SearchClient(
            endpoint=self._endpoint,
            index_name=self._index_name,
            credential=self._credential,
        )

    async def search_similar_documents_with_staffing(
        self, 
        query_text: str, 
        top_k: int = 5,
        search_type: str = "vector",
        company_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents and include staffing plan information."""
        search_client = await self._get_search_client()
        
        try:
            # Generate embedding for the query
            query_embeddings = await self._embedding_service.get_embeddings_batch([query_text])
            if not query_embeddings or not query_embeddings[0]:
                return []
            
            # Build filter expression
            filter_expression = None
            if company_filter and company_filter != "All":
                filter_expression = f"company eq '{company_filter}'"
            
            if search_type == "vector":
                # Pure vector search
                results = await search_client.search(
                    search_text="",
                    vector_queries=[
                        {
                            "kind": "vector",
                            "vector": query_embeddings[0],
                            "k_nearest_neighbors": top_k,
                            "fields": "content_vector"
                        }
                    ],
                    filter=filter_expression,
                    select=["id", "blob_name", "company", "sow_id", "full_text"],
                    top=top_k
                )
            elif search_type == "hybrid":
                # Hybrid search (text + vector)
                results = await search_client.search(
                    search_text=query_text,
                    vector_queries=[
                        {
                            "kind": "vector",
                            "vector": query_embeddings[0],
                            "k_nearest_neighbors": top_k,
                            "fields": "content_vector"
                        }
                    ],
                    filter=filter_expression,
                    select=["id", "blob_name", "company", "sow_id", "full_text"],
                    top=top_k
                )
            else:  # text search
                results = await search_client.search(
                    search_text=query_text,
                    filter=filter_expression,
                    select=["id", "blob_name", "company", "sow_id", "full_text"],
                    top=top_k
                )
            
            # Process results and add staffing information
            search_results = []
            rank = 1
            async for result in results:
                result_dict = dict(result)
                # Add ranking and simple score
                result_dict['rank'] = rank
                result_dict['score'] = round(1.0 - (rank * 0.1), 2)
                
                # Fetch and extract staffing plan from original SOW
                # Map .txt blob names to original document names
                original_blob_name = self._map_to_original_blob_name(result_dict['blob_name'])
                staffing_plan = await self._extract_staffing_plan(original_blob_name)
                result_dict['staffing_plan'] = staffing_plan
                
                search_results.append(result_dict)
                rank += 1
            
            return search_results
            
        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def _map_to_original_blob_name(self, txt_blob_name: str) -> str:
        """Map .txt blob name to original document name."""
        # Remove .txt extension and add appropriate extension
        base_name = txt_blob_name.replace('.txt', '')
        
        # Check if it's a .docx file
        if base_name in ['company_1_sow_1', 'company_2_sow_2', 'company_3_sow_1', 'company_4_sow_1']:
            return f"{base_name}.docx"
        else:
            # Assume it's a .pdf file
            return f"{base_name}.pdf"

    async def _extract_staffing_plan(self, blob_name: str) -> Dict[str, Any]:
        """Extract staffing plan information from the original SOW document."""
        try:
            # Download the original SOW document
            blob_client = self._blob_service_client.get_blob_client(
                container=self._sows_container,
                blob=blob_name
            )
            
            # Download blob content
            blob_data = await blob_client.download_blob()
            content = await blob_data.readall()
            
            # Extract text based on file type
            if blob_name.lower().endswith('.docx'):
                text = extract_docx_text(content)
            elif blob_name.lower().endswith('.pdf'):
                text = extract_pdf_text(content)
            else:
                return {"error": "Unsupported file format"}
            
            # Extract staffing plan information
            staffing_info = self._parse_staffing_plan(text)
            return staffing_info
            
        except Exception as e:
            return {"error": f"Failed to extract staffing plan: {str(e)}"}

    def _parse_staffing_plan(self, text: str) -> Dict[str, Any]:
        """Parse staffing plan information from SOW text."""
        staffing_info = {
            "roles": [],
            "hours": [],
            "fte_percentages": [],
            "staffing_table": [],
            "raw_staffing_text": "",
            "structured_staffing": []
        }
        
        # Look for staffing plan sections with more specific patterns
        staffing_patterns = [
            r"(?i)project\s+staffing\s+plan.*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)",
            r"(?i)staffing\s+plan.*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)",
            r"(?i)team\s+structure.*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)",
            r"(?i)personnel\s+allocation.*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)",
            r"(?i)resource\s+allocation.*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)",
            # Look for table patterns
            r"(?i)name\s+role\s+primary\s+role.*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)",
            # Look for specific names that might indicate a staffing table
            r"(?i)(christine\s+franklin|francesca\s+minorini|stephanie\s+riley|genevieve\s+courtney).*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)"
        ]
        
        # Find staffing-related sections
        staffing_sections = []
        for pattern in staffing_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Extract a reasonable amount of text around the match
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 1500)
                section = text[start:end]
                staffing_sections.append(section)
        
        # If no specific patterns found, look for any text containing common staffing keywords
        if not staffing_sections:
            staffing_keywords = [
                r"(?i).*?(staffing|team|personnel|resource|allocation).*?(?=\n\n|\n[A-Z][a-z]+\s+[A-Z]|$)"
            ]
            for pattern in staffing_keywords:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 500)
                    section = text[start:end]
                    if len(section) > 100:  # Only include substantial sections
                        staffing_sections.append(section)
        
        # Combine all staffing sections
        if staffing_sections:
            staffing_info["raw_staffing_text"] = "\n\n".join(staffing_sections)
            
            # Extract structured table data first
            self._extract_structured_staffing_table(staffing_info, text)
            
            # Then extract roles and hours from the text
            self._extract_roles_and_hours(staffing_info, text)
        
        return staffing_info

    def _extract_structured_staffing_table(self, staffing_info: Dict[str, Any], text: str):
        """Extract structured staffing table data like the example table."""
        # First, look for the specific table format we found
        # Pattern: "Project Staffing Plan Name Role Primary Role % Primary Location"
        table_header_pattern = r"(?i)project\s+staffing\s+plan\s+name\s+role\s+primary\s+role\s+%\s+primary\s+location"
        header_match = re.search(table_header_pattern, text, re.IGNORECASE | re.MULTILINE)
        
        if header_match:
            # Extract text after the header
            start_pos = header_match.end()
            # Look for the next section or end of text
            next_section = re.search(r"\n\n[A-Z][a-z]+\s+[A-Z]|Total\s+\$|Fee\s+In\s+consideration", text[start_pos:], re.IGNORECASE)
            if next_section:
                table_text = text[start_pos:start_pos + next_section.start()]
            else:
                table_text = text[start_pos:start_pos + 1000]  # Take next 1000 chars
            
            # Extract staff entries from this table text
            self._extract_staff_from_table_text(staffing_info, table_text)
        
        # Also look for individual staff entries in the full text
        staff_patterns = [
            # Pattern for: Christine Franklin EVP Global Account lead 2% Norwalk, CT
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+([A-Z]{2,4})\s+([^%]+?)\s+(\d+%)\s+([^%]+?)(?=\s|$)",
            # More flexible pattern
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+([A-Z]{1,4})\s+([^%]+?)\s+(\d+%)\s+([^%]+?)(?=\s|$)"
        ]
        
        for pattern in staff_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match.groups()) >= 5:
                    name = match.group(1).strip()
                    role = match.group(2).strip()
                    primary_role = match.group(3).strip()
                    percentage = match.group(4).strip()
                    location = match.group(5).strip()
                    
                    # Clean up the data
                    if name and role and primary_role and percentage and location:
                        # Avoid duplicates
                        if not any(s["name"].lower() == name.lower() for s in staffing_info["structured_staffing"]):
                            staffing_info["structured_staffing"].append({
                                "name": name,
                                "role": role,
                                "primary_role": primary_role,
                                "percentage": percentage,
                                "location": location
                            })

    def _extract_staff_from_table_text(self, staffing_info: Dict[str, Any], table_text: str):
        """Extract staff entries from table text."""
        # Split by lines and look for staff entries
        lines = table_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for patterns like: Christine Franklin EVP Global Account lead 2% Norwalk, CT
            # The table format is: Name Role Primary Role % Primary Location
            staff_match = re.match(r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+([A-Z]{1,4})\s+([^%]+?)\s+(\d+%)\s+([^%]+?)$", line, re.IGNORECASE)
            if staff_match:
                name = staff_match.group(1).strip()
                role = staff_match.group(2).strip()
                primary_role = staff_match.group(3).strip()
                percentage = staff_match.group(4).strip()
                location = staff_match.group(5).strip()
                
                # Clean up the primary role (remove extra spaces)
                primary_role = re.sub(r'\s+', ' ', primary_role).strip()
                
                # Avoid duplicates
                if not any(s["name"].lower() == name.lower() for s in staffing_info["structured_staffing"]):
                    staffing_info["structured_staffing"].append({
                        "name": name,
                        "role": role,
                        "primary_role": primary_role,
                        "percentage": percentage,
                        "location": location
                    })
        
        # Also try to parse the table as a single line (in case it's all on one line)
        # Look for the pattern: Name Role Primary Role % Primary Location followed by staff entries
        single_line_pattern = r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+([A-Z]{1,4})\s+([^%]+?)\s+(\d+%)\s+([^%]+?)(?=\s+[A-Z][a-z]+\s+[A-Z]|$)"
        matches = re.finditer(single_line_pattern, table_text, re.IGNORECASE)
        for match in matches:
            name = match.group(1).strip()
            role = match.group(2).strip()
            primary_role = match.group(3).strip()
            percentage = match.group(4).strip()
            location = match.group(5).strip()
            
            # Clean up the primary role
            primary_role = re.sub(r'\s+', ' ', primary_role).strip()
            
            # Avoid duplicates
            if not any(s["name"].lower() == name.lower() for s in staffing_info["structured_staffing"]):
                staffing_info["structured_staffing"].append({
                    "name": name,
                    "role": role,
                    "primary_role": primary_role,
                    "percentage": percentage,
                    "location": location
                })

    def _extract_roles_and_hours(self, staffing_info: Dict[str, Any], text: str):
        """Extract specific roles and hours from staffing text."""
        # Look for role patterns
        role_patterns = [
            r"(?i)(account\s+director|project\s+manager|senior\s+account\s+executive|account\s+executive|manager|director|lead|coordinator|specialist)",
            r"(?i)([A-Z][a-z]+\s+[A-Z][a-z]+)",  # Title Case patterns
        ]
        
        # Look for hour patterns
        hour_patterns = [
            r"(\d+)\s*hours?",
            r"(\d+)\s*hrs?",
            r"(\d+)\s*hr",
        ]
        
        # Look for FTE patterns
        fte_patterns = [
            r"(\d+(?:\.\d+)?)\s*%?\s*FTE",
            r"(\d+(?:\.\d+)?)\s*%?\s*full\s*time",
        ]
        
        # Extract roles
        for pattern in role_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                role = match.group(1).strip()
                if len(role) > 3 and role not in staffing_info["roles"]:
                    staffing_info["roles"].append(role)
        
        # Extract hours
        for pattern in hour_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                hours = int(match.group(1))
                if hours not in staffing_info["hours"]:
                    staffing_info["hours"].append(hours)
        
        # Extract FTE percentages
        for pattern in fte_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                fte = float(match.group(1))
                if fte not in staffing_info["fte_percentages"]:
                    staffing_info["fte_percentages"].append(fte)
        
        # Try to extract staffing table data
        self._extract_staffing_table(staffing_info, text)

    def _extract_staffing_table(self, staffing_info: Dict[str, Any], text: str):
        """Extract structured staffing table data."""
        # Look for table-like patterns with roles and hours
        table_patterns = [
            r"(?i)([A-Za-z\s]+)\s+(\d+)\s*hours?",
            r"(?i)([A-Za-z\s]+)\s+(\d+)\s*hrs?",
            r"(?i)([A-Za-z\s]+)\s+(\d+(?:\.\d+)?)\s*%?\s*FTE",
        ]
        
        for pattern in table_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                role = match.group(1).strip()
                value = match.group(2)
                
                # Try to determine if it's hours or FTE
                if 'fte' in match.group(0).lower() or '%' in match.group(0):
                    try:
                        fte_value = float(value)
                        staffing_info["staffing_table"].append({
                            "role": role,
                            "fte_percentage": fte_value,
                            "type": "fte"
                        })
                    except ValueError:
                        pass
                else:
                    try:
                        hours_value = int(value)
                        staffing_info["staffing_table"].append({
                            "role": role,
                            "hours": hours_value,
                            "type": "hours"
                        })
                    except ValueError:
                        pass

    async def get_available_companies(self) -> List[str]:
        """Get list of available companies for filtering."""
        search_client = await self._get_search_client()
        
        try:
            # Get all unique companies
            results = await search_client.search(
                search_text="*",
                select=["company"],
                top=1000
            )
            
            companies = set()
            async for result in results:
                if result.get('company'):
                    companies.add(result['company'])
            
            return ["All"] + sorted(list(companies))
            
        except Exception as e:
            print(f"Failed to get companies: {e}")
            return ["All"]

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get basic index statistics."""
        search_client = await self._get_search_client()
        
        try:
            # Count documents
            results = await search_client.search(
                search_text="*",
                select=["id"],
                top=1000
            )
            
            count = 0
            async for result in results:
                count += 1
            
            return {
                "document_count": count,
                "index_name": self._index_name
            }
            
        except Exception as e:
            print(f"Failed to get stats: {e}")
            return {"document_count": 0, "index_name": self._index_name}

    async def index_document(self, doc_data: Dict[str, Any]) -> bool:
        """Index a single document for vector search."""
        try:
            print(f"Starting indexing for {doc_data.get('blob_name', 'unknown')}")
            
            # Get the search client
            search_client = await self._get_search_client()
            print(f"Got search client for index: {self._index_name}")
            
            # Generate embeddings for the document
            print(f"Generating embeddings for text length: {len(doc_data['full_text'])}")
            embeddings = await self._embedding_service.get_embeddings_batch([doc_data['full_text']])
            if not embeddings or not embeddings[0]:
                print(f"Failed to generate embeddings for {doc_data.get('blob_name', 'unknown')}")
                return False
            
            print(f"Generated embeddings with {len(embeddings[0])} dimensions")
            
            # Create the document for indexing
            document = {
                "id": doc_data['blob_name'].replace('.txt', ''),  # Use base name as ID
                "blob_name": doc_data['blob_name'],
                "company": doc_data.get('company', 'Unknown'),
                "sow_id": doc_data.get('sow_id', 'Unknown'),
                "format": "txt",
                "full_text": doc_data['full_text'],
                "content_vector": embeddings[0]
            }
            
            print(f"Uploading document with ID: {document['id']}")
            
            # Upload the document to the search index
            result = await search_client.upload_documents([document])
            print(f"Upload result: {result}")
            print(f"Successfully indexed {doc_data['blob_name']}")
            return True
            
        except Exception as e:
            print(f"Failed to index {doc_data.get('blob_name', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def close(self):
        """Close the blob service client."""
        await self._blob_service_client.close()
        await self._credential_storage.close()

# Helper function for Streamlit
def run_async(coro):
    """Helper function to run async code in Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
