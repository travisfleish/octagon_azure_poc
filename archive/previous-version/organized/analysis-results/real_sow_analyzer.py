#!/usr/bin/env python3
"""
Real SOW Analyzer - Uses Azure OpenAI to analyze actual SOW files
================================================================

This script demonstrates how AI can extract homogeneous data from heterogeneous SOW documents.
It processes all 9 sample SOW files using real Azure OpenAI LLM calls.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Azure OpenAI imports
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field

# Local imports
import sys
sys.path.append('octagon-staffing-app')
from app.config import get_settings
from app.services.document_intelligence import DocumentIntelligenceService


class SOWAnalysisResult(BaseModel):
    """Structured result from SOW analysis"""
    file_name: str
    company: str
    project_title: str
    duration_weeks: int
    departments_involved: List[str]
    deliverables: List[str]
    roles_mentioned: List[str]
    budget_info: Dict[str, Any]
    scope_description: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    extraction_timestamp: datetime = Field(default_factory=datetime.now)


class RealSOWAnalyzer:
    """Real SOW analyzer using Azure OpenAI"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncAzureOpenAI(
            api_key=self.settings.aoai_key,
            azure_endpoint=self.settings.aoai_endpoint,
            api_version=self.settings.aoai_api_version,
        )
        self.document_service = DocumentIntelligenceService()
        
        # Define the extraction schema for the LLM
        self.extraction_schema = {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "The client company name"
                },
                "project_title": {
                    "type": "string", 
                    "description": "The project or campaign title"
                },
                "duration_weeks": {
                    "type": "integer",
                    "description": "Project duration in weeks"
                },
                "departments_involved": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Octagon departments involved - MUST ONLY be from these 4: 'client_services', 'strategy', 'planning_creative', 'integrated_production_experiences'"
                },
                "deliverables": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific deliverables or outputs"
                },
                "roles_mentioned": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "Staffing roles mentioned in the SOW"
                },
                "budget_info": {
                    "type": "object",
                    "properties": {
                        "total_budget": {"type": "number"},
                        "budget_currency": {"type": "string"},
                        "budget_breakdown": {"type": "array", "items": {"type": "string"}}
                    },
                    "description": "Budget and financial information"
                },
                "scope_description": {
                    "type": "string",
                    "description": "Brief description of the project scope"
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Confidence in the extraction accuracy"
                }
            },
            "required": ["company", "project_title", "duration_weeks", "departments_involved", "deliverables", "roles_mentioned", "scope_description"]
        }
    
    async def analyze_sow_file(self, file_path: Path) -> SOWAnalysisResult:
        """Analyze a single SOW file using real Azure OpenAI"""
        
        print(f"📄 Analyzing: {file_path.name}")
        
        try:
            # Read file bytes
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Extract structure using the document service
            extraction_result = await self.document_service.extract_structure(file_bytes, file_path.name)
            
            # Get the extracted text from the result
            text = extraction_result.get('full_text', '')
            
            print(f"✅ Extracted {len(text)} characters from {file_path.name}")
            
            # Create the LLM prompt
            prompt = self._create_extraction_prompt(text)
            
            # Call Azure OpenAI with structured output
            response = await self.client.chat.completions.create(
                model=self.settings.aoai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at analyzing Statement of Work (SOW) documents for Octagon, a global sports marketing agency. 

Extract the following information from the SOW text:
- Company/client name
- Project title
- Duration in weeks
- Octagon departments involved (MUST ONLY use these 4 exact values: 'client_services', 'strategy', 'planning_creative', 'integrated_production_experiences')
- Specific deliverables
- Staffing roles mentioned
- Budget information if available
- Project scope description

CRITICAL: For departments_involved, you must map all department references to ONLY these 4 Octagon departments:
- 'client_services' (for account management, client relationship, account services)
- 'strategy' (for strategic planning, insights, research, analytics)
- 'planning_creative' (for creative development, brand work, campaign planning, creative strategy)
- 'integrated_production_experiences' (for events, hospitality, activations, production, experiences)

Be precise and extract only information that is explicitly stated or clearly implied in the document."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"}
                # Note: This model doesn't support custom temperature, uses default
            )
            
            # Parse the JSON response
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Create the result object
            result = SOWAnalysisResult(
                file_name=file_path.name,
                company=extracted_data.get("company", "Unknown"),
                project_title=extracted_data.get("project_title", "Unknown"),
                duration_weeks=extracted_data.get("duration_weeks", 0),
                departments_involved=extracted_data.get("departments_involved", []),
                deliverables=extracted_data.get("deliverables", []),
                roles_mentioned=extracted_data.get("roles_mentioned", []),
                budget_info=extracted_data.get("budget_info", {}),
                scope_description=extracted_data.get("scope_description", ""),
                confidence_score=extracted_data.get("confidence_score", 0.8)
            )
            
            print(f"🎯 Successfully analyzed {file_path.name}")
            return result
            
        except Exception as e:
            print(f"❌ Error analyzing {file_path.name}: {e}")
            # Return a minimal result for failed files
            return SOWAnalysisResult(
                file_name=file_path.name,
                company="ERROR",
                project_title="Analysis Failed",
                duration_weeks=0,
                departments_involved=[],
                deliverables=[],
                roles_mentioned=[],
                budget_info={},
                scope_description=f"Error during analysis: {str(e)}",
                confidence_score=0.0
            )
    
    def _create_extraction_prompt(self, text: str) -> str:
        """Create the extraction prompt for the LLM"""
        
        # Truncate text if too long (keep first 8000 characters to stay within token limits)
        truncated_text = text[:8000] if len(text) > 8000 else text
        
        prompt = f"""
Analyze this SOW document and extract the required information in JSON format.

SOW Document Text:
{truncated_text}

Please extract the following information and return it as a JSON object:
- company: The client company name
- project_title: The project or campaign title  
- duration_weeks: Project duration in weeks (if not specified, estimate based on context)
- departments_involved: List of Octagon departments involved (MUST ONLY use these 4: 'client_services', 'strategy', 'planning_creative', 'integrated_production_experiences')
- deliverables: List of specific deliverables or outputs
- roles_mentioned: List of staffing roles mentioned in the SOW
- budget_info: Object with total_budget, budget_currency, and budget_breakdown if available
- scope_description: Brief description of the project scope
- confidence_score: Your confidence in the extraction accuracy (0.0 to 1.0)

Return only valid JSON with no additional text.
"""
        return prompt
    
    async def analyze_all_sows(self, sows_directory: str) -> List[SOWAnalysisResult]:
        """Analyze all SOW files in the directory"""
        
        sows_path = Path(sows_directory)
        if not sows_path.exists():
            raise ValueError(f"SOWs directory not found: {sows_directory}")
        
        # Get all SOW files
        sow_files = []
        for ext in ['.pdf', '.docx']:
            sow_files.extend(sows_path.glob(f"*{ext}"))
        
        print(f"🔍 Found {len(sow_files)} SOW files to analyze")
        
        # Analyze all files concurrently
        tasks = [self.analyze_sow_file(file_path) for file_path in sow_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, SOWAnalysisResult):
                valid_results.append(result)
            else:
                print(f"⚠️ Exception during analysis: {result}")
        
        return valid_results
    
    def generate_comparison_report(self, results: List[SOWAnalysisResult]) -> Dict[str, Any]:
        """Generate a comparison report showing homogeneous extraction from heterogeneous inputs"""
        
        report = {
            "analysis_summary": {
                "total_sows_analyzed": len(results),
                "successful_extractions": len([r for r in results if r.confidence_score > 0.5]),
                "average_confidence": sum(r.confidence_score for r in results) / len(results) if results else 0,
                "analysis_timestamp": datetime.now().isoformat()
            },
            "companies": {},
            "departments": {},
            "deliverables": {},
            "roles": {},
            "duration_analysis": {},
            "detailed_results": []
        }
        
        # Aggregate data by company
        for result in results:
            company = result.company
            if company not in report["companies"]:
                report["companies"][company] = {
                    "sow_count": 0,
                    "projects": [],
                    "total_duration_weeks": 0
                }
            
            report["companies"][company]["sow_count"] += 1
            report["companies"][company]["projects"].append(result.project_title)
            report["companies"][company]["total_duration_weeks"] += result.duration_weeks
        
        # Aggregate departments
        for result in results:
            for dept in result.departments_involved:
                report["departments"][dept] = report["departments"].get(dept, 0) + 1
        
        # Aggregate deliverables
        for result in results:
            for deliverable in result.deliverables:
                report["deliverables"][deliverable] = report["deliverables"].get(deliverable, 0) + 1
        
        # Aggregate roles
        for result in results:
            for role in result.roles_mentioned:
                report["roles"][role] = report["roles"].get(role, 0) + 1
        
        # Duration analysis
        durations = [r.duration_weeks for r in results if r.duration_weeks > 0]
        if durations:
            report["duration_analysis"] = {
                "min_weeks": min(durations),
                "max_weeks": max(durations),
                "avg_weeks": sum(durations) / len(durations),
                "median_weeks": sorted(durations)[len(durations) // 2]
            }
        
        # Add detailed results
        for result in results:
            report["detailed_results"].append(result.dict())
        
        return report


async def main():
    """Main function to run the real SOW analysis"""
    
    print("🤖 Real SOW Analyzer - Azure OpenAI Integration")
    print("=" * 60)
    
    # Check if Azure OpenAI is configured
    settings = get_settings()
    if not settings.aoai_endpoint or not settings.aoai_key:
        print("❌ Azure OpenAI not configured. Please set AOAI_ENDPOINT and AOAI_KEY environment variables.")
        return
    
    print(f"✅ Azure OpenAI configured: {settings.aoai_endpoint}")
    print(f"✅ Using deployment: {settings.aoai_deployment}")
    
    # Initialize analyzer
    analyzer = RealSOWAnalyzer()
    
    # Analyze all SOW files
    sows_directory = "/Users/travisfleisher/Cursor Project/Octagon/azure_setup/sows"
    
    print(f"\n🔍 Analyzing all SOW files in: {sows_directory}")
    
    try:
        results = await analyzer.analyze_all_sows(sows_directory)
        
        print(f"\n✅ Successfully analyzed {len(results)} SOW files")
        
        # Generate comparison report
        report = analyzer.generate_comparison_report(results)
        
        # Save results
        output_file = "real_sow_analysis_results.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📊 Analysis Results:")
        print(f"   Companies: {len(report['companies'])}")
        print(f"   Departments: {len(report['departments'])}")
        print(f"   Unique Deliverables: {len(report['deliverables'])}")
        print(f"   Unique Roles: {len(report['roles'])}")
        print(f"   Average Confidence: {report['analysis_summary']['average_confidence']:.2f}")
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Print sample results
        print(f"\n📋 Sample Extractions:")
        for result in results[:3]:  # Show first 3 results
            print(f"\n   File: {result.file_name}")
            print(f"   Company: {result.company}")
            print(f"   Project: {result.project_title}")
            print(f"   Duration: {result.duration_weeks} weeks")
            print(f"   Departments: {', '.join(result.departments_involved)}")
            print(f"   Confidence: {result.confidence_score:.2f}")
        
        if len(results) > 3:
            print(f"   ... and {len(results) - 3} more results")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
