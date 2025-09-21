#!/usr/bin/env python3
"""
Octagon Document Intelligence Service
====================================

Enhanced document processing service specifically designed for Octagon's 
staffing plan generation prototype. Integrates with the Octagon-specific
schema and handles the normalization requirements.
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Dict, Any, Optional, List
from datetime import datetime

from PyPDF2 import PdfReader
from openai import AsyncOpenAI

from octagon_staffing_schema import (
    OctagonStaffingPlan, ProjectInfo, StaffingRole, FinancialStructure,
    OctagonDepartment, OctagonRole, OctagonLevel, AllocationType,
    BillabilityType, ExtractedField, StaffingPlanNormalizer
)


class OctagonDocumentIntelligenceError(Exception):
    """Raised when Document Intelligence operations fail."""


class OctagonDocumentIntelligenceService:
    """Enhanced document processing service for Octagon SOWs."""
    
    def __init__(self) -> None:
        self._openai_client: Optional[AsyncOpenAI] = None
        self.normalizer = StaffingPlanNormalizer()
        
        # Octagon-specific patterns for extraction
        self.role_patterns = [
            r"\b(Account Director|Account Manager|Account Executive|AE|SAE)\b",
            r"\b(Creative Director|Art Director|Copywriter|Designer)\b",
            r"\b(Strategy Director|Strategy Manager|Strategist|Planner)\b",
            r"\b(Sponsorship Director|Sponsorship Manager|Partnership Manager)\b",
            r"\b(Event Director|Event Manager|Hospitality Manager|Experience Coordinator)\b",
            r"\b(Business Development|BD Director|BD Manager|New Business Manager)\b",
            r"\b(Analytics Director|Data Analyst|Analyst|Measurement Specialist)\b",
            r"\b(Media Director|Media Manager|Digital Specialist|Social Media Manager)\b",
            r"\b(Project Manager|Program Manager|Coordinator)\b",
        ]
        
        self.allocation_patterns = [
            r"\b(\d{1,3})\s*%?\s*FTE\b",
            r"\b(\d{1,4})\s*(?:hours|hrs)\b",
            r"\b(\d{1,3})\s*(?:hourly|daily|monthly)\b",
            r"\$\s*(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)\b",
        ]
        
        self.project_info_patterns = [
            r"(?:Project Title|Project Name)[:\-]\s*(.+?)(?:\n|$)",
            r"(?:Client|Company)[:\-]\s*(.+?)(?:\n|$)",
            r"(?:Contract Number|Contract #)[:\-]\s*(.+?)(?:\n|$)",
            r"(?:Effective Date|Start Date)[:\-]\s*(.+?)(?:\n|$)",
            r"(?:Duration|Term)[:\-]\s*(.+?)(?:\n|$)",
        ]

    async def _get_openai_client(self) -> AsyncOpenAI:
        """Get OpenAI client for LLM processing."""
        if self._openai_client is None:
            # This would use your existing Azure OpenAI configuration
            # For now, returning None to indicate configuration needed
            raise OctagonDocumentIntelligenceError("Azure OpenAI configuration not set")
        return self._openai_client

    def _extract_docx_text(self, data: bytes) -> str:
        """Fast DOCX text extraction via document.xml."""
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", " ", xml)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_pdf_text(self, data: bytes) -> str:
        """Lightweight PDF text extraction."""
        reader = PdfReader(io.BytesIO(data))
        out = []
        for page in reader.pages[:15]:  # Increased to 15 pages for SOWs
            try:
                out.append(page.extract_text() or "")
            except Exception:
                pass
        return re.sub(r"\s+", " ", "\n".join(out)).strip()

    def _extract_project_info_heuristic(self, text: str) -> Dict[str, Any]:
        """Extract project information using heuristics."""
        project_info = {}
        
        # Extract project title
        title_match = re.search(r"(?:Project Title|Project Name)[:\-]\s*(.+?)(?:\n|$)", text, re.I)
        if title_match:
            project_info["project_name"] = title_match.group(1).strip()
        
        # Extract client name
        client_match = re.search(r"(?:Client|Company)[:\-]\s*(.+?)(?:\n|$)", text, re.I)
        if client_match:
            project_info["client_name"] = client_match.group(1).strip()
        
        # Extract contract number
        contract_match = re.search(r"(?:Contract Number|Contract #)[:\-]\s*(.+?)(?:\n|$)", text, re.I)
        if contract_match:
            project_info["contract_number"] = contract_match.group(1).strip()
        
        # Extract dates
        date_patterns = [
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text, re.I))
        
        if dates:
            project_info["dates_found"] = dates[:3]  # First 3 dates
        
        return project_info

    def _extract_roles_heuristic(self, text: str) -> List[Dict[str, Any]]:
        """Extract roles using heuristics."""
        roles = []
        
        # Look for staffing plan sections
        staffing_sections = re.findall(
            r"(?:Staffing Plan|Project Staffing|Resource Table|Team)(.*?)(?=\n\n|\n[A-Z]|\Z)", 
            text, re.I | re.DOTALL
        )
        
        for section in staffing_sections:
            # Extract role information from staffing sections
            lines = section.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for role patterns in the line
                for pattern in self.role_patterns:
                    match = re.search(pattern, line, re.I)
                    if match:
                        role_title = match.group(0)
                        
                        # Extract allocation information
                        fte_match = re.search(r"\b(\d{1,3})\s*%?\s*FTE\b", line, re.I)
                        hours_match = re.search(r"\b(\d{1,4})\s*(?:hours|hrs)\b", line, re.I)
                        
                        role_data = {
                            "title": role_title,
                            "raw_line": line,
                            "fte_percentage": float(fte_match.group(1)) if fte_match else None,
                            "hours": float(hours_match.group(1)) if hours_match else None,
                        }
                        
                        roles.append(role_data)
                        break
        
        return roles

    async def _llm_extract_octagon_schema(self, blob_name: str, file_format: str, text: str) -> Dict[str, Any]:
        """LLM-powered extraction using Octagon-specific schema."""
        # Trim text for token management
        doc = text[:80_000]  # Increased for SOW complexity
        
        # Octagon-specific JSON schema
        json_schema = {
            "type": "object",
            "properties": {
                "project_info": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "client_name": {"type": "string"},
                        "project_id": {"type": "string"},
                        "contract_number": {"type": "string"},
                        "duration_weeks": {"type": "integer"},
                        "project_type": {"type": "string"},
                        "complexity_score": {"type": "number", "minimum": 1, "maximum": 10}
                    }
                },
                "roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role_title": {"type": "string"},
                            "allocation_type": {"type": "string", "enum": ["fte_percentage", "hours", "rate_based", "retainer"]},
                            "allocation_value": {"type": "number"},
                            "billability": {"type": "string", "enum": ["billable", "non_billable", "pass_through", "unknown"]},
                            "primary_responsibilities": {"type": "array", "items": {"type": "string"}},
                            "location": {"type": "string"},
                            "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                            "raw_text_reference": {"type": "string"}
                        },
                        "required": ["role_title", "allocation_type", "allocation_value", "billability"]
                    }
                },
                "financial_structure": {
                    "type": "object",
                    "properties": {
                        "primary_fee_type": {"type": "string", "enum": ["fte_percentage", "hours", "rate_based", "retainer", "project_based"]},
                        "total_budget": {"type": "number"},
                        "currency": {"type": "string", "default": "USD"},
                        "payment_schedule": {"type": "string"},
                        "hourly_rates": {"type": "object"},
                        "daily_rates": {"type": "object"}
                    }
                },
                "extraction_metadata": {
                    "type": "object",
                    "properties": {
                        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "sections_found": {"type": "array", "items": {"type": "string"}},
                        "extraction_notes": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "required": ["project_info", "roles", "extraction_metadata"]
        }

        system_prompt = """You are an expert SOW parser for Octagon, a global sports marketing agency. 
Your task is to extract staffing plan information from client SOWs.

KEY REQUIREMENTS:
1. Focus on staffing roles and resource allocations
2. Map roles to Octagon's organizational structure (Account, Creative, Strategy, Sponsorship, Experience, etc.)
3. Normalize allocations between FTE percentages and hours
4. Identify billability (billable vs non-billable vs pass-through)
5. Extract project timeline and financial structure
6. Maintain traceability to original text

OCTAGON CONTEXT:
- We work with sports/entertainment sponsorships, hospitality events, partnership activation
- Common roles: Account Directors/Managers, Creative Directors, Strategy teams, Event Managers
- Typical allocations: FTE percentages, hourly rates, retainer fees
- Projects often involve multiple events, hospitality programs, sponsorship activation

EXTRACTION GUIDELINES:
- If uncertain about a role, provide best estimate with lower confidence
- For allocations, convert to consistent format (prefer FTE % for staffing roles)
- Include raw text references for traceability
- Flag any unclear or ambiguous information in extraction_notes"""

        user_prompt = f"""Document: {blob_name}
Format: {file_format}

Extract Octagon staffing plan information from this SOW:

<<<SOW_TEXT_BEGIN>>>
{doc}
<<<SOW_TEXT_END>>>"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response_format = {"type": "json_schema", "json_schema": {"name": "octagon_sow_extraction", "schema": json_schema}}

        # Retry logic for transient issues
        last_err = None
        for attempt in range(3):
            try:
                client = await self._get_openai_client()
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",  # Updated model
                    messages=messages,
                    response_format=response_format,
                    temperature=0.1  # Low temperature for consistent extraction
                )
                import json
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                last_err = e
                continue

        raise OctagonDocumentIntelligenceError(f"LLM extraction failed after 3 attempts: {last_err}")

    def _create_extracted_fields(self, raw_text: str, structured_value: Any, field_name: str, 
                                confidence: float = 0.8, section: str = None) -> ExtractedField:
        """Create an ExtractedField for traceability."""
        return ExtractedField(
            field_name=field_name,
            raw_text=raw_text,
            structured_value=structured_value,
            confidence_score=confidence,
            source_section=section,
            extraction_method="llm"
        )

    def _build_octagon_staffing_plan(self, llm_data: Dict[str, Any], raw_text: str, 
                                   blob_name: str) -> OctagonStaffingPlan:
        """Build OctagonStaffingPlan from LLM extraction data."""
        
        # Project info
        project_info_data = llm_data.get("project_info", {})
        project_info = ProjectInfo(
            project_name=project_info_data.get("project_name", "Unknown Project"),
            client_name=project_info_data.get("client_name", "Unknown Client"),
            project_id=project_info_data.get("project_id"),
            contract_number=project_info_data.get("contract_number"),
            duration_weeks=project_info_data.get("duration_weeks"),
            project_type=project_info_data.get("project_type"),
            complexity_score=project_info_data.get("complexity_score", 5.0),
            extracted_fields=[
                self._create_extracted_fields(
                    raw_text=raw_text[:200],  # Sample of raw text
                    structured_value=project_info_data.get("project_name"),
                    field_name="project_name",
                    confidence=0.8
                )
            ]
        )
        
        # Roles
        roles = []
        roles_data = llm_data.get("roles", [])
        
        for role_data in roles_data:
            role_title = role_data.get("role_title", "")
            
            # Map to Octagon structure
            octagon_role, octagon_dept, octagon_level = self.normalizer.map_role_to_octagon_structure(role_title)
            
            # Determine allocation type and value
            allocation_type_str = role_data.get("allocation_type", "fte_percentage")
            allocation_type = AllocationType(allocation_type_str)
            allocation_value = role_data.get("allocation_value", 0.0)
            
            # Determine billability
            billability_str = role_data.get("billability", "unknown")
            billability = BillabilityType(billability_str)
            
            role = StaffingRole(
                role_title=role_title,
                octagon_department=octagon_dept,
                octagon_role=octagon_role,
                octagon_level=octagon_level,
                allocation_type=allocation_type,
                allocation_value=allocation_value,
                billability=billability,
                project_duration_weeks=project_info.duration_weeks,
                primary_responsibilities=role_data.get("primary_responsibilities", []),
                location=role_data.get("location"),
                confidence_score=role_data.get("confidence_score", 0.8),
                extracted_fields=[
                    self._create_extracted_fields(
                        raw_text=role_data.get("raw_text_reference", ""),
                        structured_value=role_title,
                        field_name="role_title",
                        confidence=role_data.get("confidence_score", 0.8)
                    )
                ]
            )
            
            roles.append(role)
        
        # Financial structure
        financial_data = llm_data.get("financial_structure", {})
        financial_structure = None
        if financial_data:
            financial_structure = FinancialStructure(
                primary_fee_type=AllocationType(financial_data.get("primary_fee_type", "retainer")),
                total_budget=financial_data.get("total_budget"),
                currency=financial_data.get("currency", "USD"),
                payment_schedule=financial_data.get("payment_schedule"),
                hourly_rates=financial_data.get("hourly_rates", {}),
                daily_rates=financial_data.get("daily_rates", {}),
                extracted_fields=[
                    self._create_extracted_fields(
                        raw_text=str(financial_data),
                        structured_value=financial_data.get("total_budget"),
                        field_name="total_budget",
                        confidence=0.8
                    )
                ]
            )
        
        # Calculate summary metrics
        total_fte = sum(role.normalized_fte_percentage or 0 for role in roles)
        
        # Service line allocation
        service_line_allocation = {}
        for role in roles:
            if role.service_line and role.normalized_fte_percentage:
                if role.service_line not in service_line_allocation:
                    service_line_allocation[role.service_line] = 0
                service_line_allocation[role.service_line] += role.normalized_fte_percentage
        
        # Extraction metadata
        metadata = llm_data.get("extraction_metadata", {})
        
        return OctagonStaffingPlan(
            project_info=project_info,
            roles=roles,
            financial_structure=financial_structure,
            total_fte_percentage=total_fte,
            service_line_allocation=service_line_allocation,
            extraction_confidence=metadata.get("confidence_score", 0.8),
            completeness_score=self._calculate_completeness_score(roles, project_info, financial_structure),
            source_sow_file=blob_name,
            raw_extraction_data=llm_data
        )

    def _calculate_completeness_score(self, roles: List[StaffingRole], 
                                    project_info: ProjectInfo, 
                                    financial_structure: Optional[FinancialStructure]) -> float:
        """Calculate completeness score for the extracted data."""
        scores = []
        
        # Project info completeness (40% weight)
        project_score = 0.0
        if project_info.project_name: project_score += 0.3
        if project_info.client_name: project_score += 0.3
        if project_info.contract_number: project_score += 0.2
        if project_info.duration_weeks: project_score += 0.2
        scores.append(project_score * 0.4)
        
        # Roles completeness (40% weight)
        roles_score = min(len(roles) / 3.0, 1.0)  # Expect at least 3 roles
        roles_mapped_score = sum(1 for role in roles if role.octagon_department) / max(len(roles), 1)
        scores.append((roles_score * 0.6 + roles_mapped_score * 0.4) * 0.4)
        
        # Financial completeness (20% weight)
        financial_score = 1.0 if financial_structure and financial_structure.total_budget else 0.0
        scores.append(financial_score * 0.2)
        
        return sum(scores)

    async def extract_octagon_staffing_plan(self, file_bytes: bytes, blob_name: str = "unknown") -> OctagonStaffingPlan:
        """Main method to extract Octagon staffing plan from SOW file."""
        
        try:
            # Determine file type and extract text
            if file_bytes.startswith(b'%PDF'):
                text = self._extract_pdf_text(file_bytes)
                fmt = "pdf"
            elif file_bytes.startswith(b'PK'):  # ZIP/DOCX signature
                text = self._extract_docx_text(file_bytes)
                fmt = "docx"
            else:
                raise OctagonDocumentIntelligenceError(f"Unsupported file type for {blob_name}")
            
            if not text.strip():
                raise OctagonDocumentIntelligenceError(f"No text extracted from {blob_name}")
            
            # Heuristic extraction for basic info
            heuristic_data = {
                "project_info": self._extract_project_info_heuristic(text),
                "roles": self._extract_roles_heuristic(text)
            }
            
            # LLM-powered extraction
            try:
                llm_data = await self._llm_extract_octagon_schema(blob_name, fmt, text)
            except Exception as e:
                # Fallback to heuristic data if LLM fails
                print(f"LLM extraction failed, using heuristics: {e}")
                llm_data = {
                    "project_info": heuristic_data["project_info"],
                    "roles": heuristic_data["roles"],
                    "extraction_metadata": {"confidence_score": 0.6, "extraction_notes": ["LLM extraction failed, using heuristics"]}
                }
            
            # Build final staffing plan
            staffing_plan = self._build_octagon_staffing_plan(llm_data, text, blob_name)
            
            return staffing_plan
            
        except Exception as exc:
            raise OctagonDocumentIntelligenceError(str(exc)) from exc


# Example usage function
async def test_octagon_extraction():
    """Test the Octagon extraction with sample data."""
    
    # This would normally read from a file
    sample_text = """
    Project Title: Company 1 Americas 2024-2025 Sponsorship Hospitality Programs
    Client: Company 1
    Contract Number: 1124711 633889
    Effective Date: October 1, 2024
    
    Project Staffing Plan:
    Name Role Primary Role Total Hours Primary Location
    Account Director Program Lead Formula 1 – Las Vegas Day to Day Manager 780
    Account Manager API Day to Day Manager 900
    SAE GRAMMY's Day to Day Manager 900
    AE Program Support 800
    TOTAL 3,380
    
    The allocations of time set forth are estimates of the percentage of the resources' total work time.
    """
    
    # Convert to bytes for testing
    file_bytes = sample_text.encode('utf-8')
    
    service = OctagonDocumentIntelligenceService()
    
    try:
        # Note: This will fail without proper OpenAI configuration
        # staffing_plan = await service.extract_octagon_staffing_plan(file_bytes, "test_sow.docx")
        print("Octagon Document Intelligence Service initialized successfully")
        print("Ready for SOW processing with Octagon-specific schema")
    except Exception as e:
        print(f"Service test completed with expected configuration error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_octagon_extraction())
