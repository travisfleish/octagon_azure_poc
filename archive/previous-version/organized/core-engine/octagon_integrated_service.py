#!/usr/bin/env python3
"""
Octagon Integrated Service
==========================

This service combines all components to provide a complete SOW processing
and staffing plan recommendation system for Octagon.

Components:
1. Document Intelligence - Extracts text and basic structure from SOWs
2. AI Recommendation Engine - Generates intelligent staffing recommendations
3. Staffing Plan Generator - Creates final normalized staffing plans
4. Quality Assessment - Validates and scores recommendations
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from octagon_staffing_schema import (
    OctagonStaffingPlan, ProjectInfo, StaffingRole, FinancialStructure,
    OctagonDepartment, OctagonRole, OctagonLevel, AllocationType,
    BillabilityType, ExtractedField, StaffingPlanNormalizer
)
from octagon_document_intelligence import OctagonDocumentIntelligenceService
from octagon_staffing_recommendation_engine import OctagonStaffingRecommendationEngine


class OctagonIntegratedService:
    """Integrated service that processes SOWs and generates staffing recommendations"""
    
    def __init__(self):
        self.document_intelligence = OctagonDocumentIntelligenceService()
        self.recommendation_engine = OctagonStaffingRecommendationEngine()
        self.normalizer = StaffingPlanNormalizer()
    
    async def process_sow_and_recommend_staffing(self, 
                                               file_bytes: bytes, 
                                               blob_name: str = "unknown") -> Dict[str, Any]:
        """
        Main method: Process SOW file and generate staffing recommendations
        
        Args:
            file_bytes: Raw file bytes (PDF or DOCX)
            blob_name: Name of the file for reference
            
        Returns:
            Dictionary containing:
            - extracted_data: Raw extraction from document intelligence
            - ai_recommendation: AI-generated staffing plan
            - final_staffing_plan: Synthesized final recommendation
            - quality_metrics: Confidence and completeness scores
        """
        
        print(f"Processing SOW: {blob_name}")
        
        try:
            # Step 1: Extract basic structure from SOW
            print("Step 1: Extracting document structure...")
            extracted_plan = await self.document_intelligence.extract_octagon_staffing_plan(file_bytes, blob_name)
            
            # Step 2: Generate AI recommendations
            print("Step 2: Generating AI recommendations...")
            ai_recommendation = self.recommendation_engine.recommend_staffing_plan(
                extracted_plan.full_text,
                extracted_plan.project_info
            )
            
            # Step 3: Synthesize final recommendation
            print("Step 3: Synthesizing final staffing plan...")
            final_plan = self._synthesize_final_plan(extracted_plan, ai_recommendation)
            
            # Step 4: Quality assessment
            print("Step 4: Assessing quality...")
            quality_metrics = self._assess_quality(extracted_plan, ai_recommendation, final_plan)
            
            return {
                "extracted_data": extracted_plan,
                "ai_recommendation": ai_recommendation,
                "final_staffing_plan": final_plan,
                "quality_metrics": quality_metrics,
                "processing_timestamp": datetime.utcnow(),
                "source_file": blob_name
            }
            
        except Exception as e:
            print(f"Error processing SOW {blob_name}: {e}")
            return {
                "error": str(e),
                "source_file": blob_name,
                "processing_timestamp": datetime.utcnow()
            }
    
    def _synthesize_final_plan(self, 
                             extracted_plan: OctagonStaffingPlan,
                             ai_recommendation: OctagonStaffingPlan) -> OctagonStaffingPlan:
        """Synthesize final staffing plan from extraction and AI recommendation"""
        
        # Combine roles from both sources
        combined_roles = []
        
        # Add roles from AI recommendation (these are more comprehensive)
        for ai_role in ai_recommendation.roles:
            combined_roles.append(ai_role)
        
        # Add any unique roles from extraction that weren't covered by AI
        for extracted_role in extracted_plan.roles:
            # Check if this role is already covered by AI recommendation
            role_covered = any(
                ai_role.role_title.lower() == extracted_role.role_title.lower() 
                for ai_role in ai_recommendation.roles
            )
            
            if not role_covered:
                # Enhance the extracted role with AI insights
                enhanced_role = self._enhance_extracted_role(extracted_role, ai_recommendation)
                combined_roles.append(enhanced_role)
        
        # Calculate department allocation
        department_allocation = {}
        for role in combined_roles:
            if role.octagon_department and role.normalized_fte_percentage:
                if role.octagon_department not in department_allocation:
                    department_allocation[role.octagon_department] = 0
                department_allocation[role.octagon_department] += role.normalized_fte_percentage
        
        # Use AI recommendation's financial structure as it's more comprehensive
        financial_structure = ai_recommendation.financial_structure
        
        return OctagonStaffingPlan(
            project_info=extracted_plan.project_info,
            roles=combined_roles,
            financial_structure=financial_structure,
            total_fte_percentage=sum(role.normalized_fte_percentage or 0 for role in combined_roles),
            service_line_allocation=department_allocation,
            extraction_confidence=(extracted_plan.extraction_confidence + ai_recommendation.extraction_confidence) / 2,
            completeness_score=max(extracted_plan.completeness_score, ai_recommendation.completeness_score),
            source_sow_file=extracted_plan.source_sow_file,
            raw_extraction_data={
                "extracted_plan": extracted_plan.raw_extraction_data,
                "ai_recommendation": ai_recommendation.raw_extraction_data,
                "synthesis_method": "combined_extraction_and_ai"
            }
        )
    
    def _enhance_extracted_role(self, 
                              extracted_role: StaffingRole,
                              ai_recommendation: OctagonStaffingPlan) -> StaffingRole:
        """Enhance extracted role with AI insights"""
        
        # Try to map to Octagon structure if not already mapped
        if not extracted_role.octagon_department:
            octagon_role, octagon_dept, octagon_level = self.normalizer.map_role_to_octagon_structure(extracted_role.role_title)
            
            if octagon_role and octagon_dept and octagon_level:
                extracted_role.octagon_role = octagon_role
                extracted_role.octagon_department = octagon_dept
                extracted_role.octagon_level = octagon_level
        
        # Use AI confidence if higher
        if ai_recommendation.extraction_confidence > extracted_role.confidence_score:
            extracted_role.confidence_score = ai_recommendation.extraction_confidence
        
        # Add AI enhancement to extracted fields
        extracted_role.extracted_fields.append(
            ExtractedField(
                field_name="ai_enhancement",
                raw_text=f"Enhanced with AI insights from recommendation engine",
                structured_value="enhanced",
                confidence_score=ai_recommendation.extraction_confidence,
                source_section="AI Enhancement",
                extraction_method="ai"
            )
        )
        
        return extracted_role
    
    def _assess_quality(self, 
                       extracted_plan: OctagonStaffingPlan,
                       ai_recommendation: OctagonStaffingPlan,
                       final_plan: OctagonStaffingPlan) -> Dict[str, Any]:
        """Assess quality of the final recommendation"""
        
        # Calculate overall confidence
        overall_confidence = (
            extracted_plan.extraction_confidence * 0.3 +
            ai_recommendation.extraction_confidence * 0.7
        )
        
        # Calculate completeness
        completeness_score = (
            extracted_plan.completeness_score * 0.4 +
            ai_recommendation.completeness_score * 0.6
        )
        
        # Role mapping quality
        mapped_roles = sum(1 for role in final_plan.roles if role.octagon_department)
        role_mapping_quality = mapped_roles / len(final_plan.roles) if final_plan.roles else 0
        
        # Department coverage
        departments_covered = len(set(role.octagon_department for role in final_plan.roles if role.octagon_department))
        department_coverage = departments_covered / len(OctagonDepartment)
        
        # Level distribution quality
        level_distribution = {}
        for role in final_plan.roles:
            if role.octagon_level:
                level_key = f"level_{role.octagon_level.value}"
                if level_key not in level_distribution:
                    level_distribution[level_key] = 0
                level_distribution[level_key] += role.normalized_fte_percentage or 0
        
        # Check for reasonable level distribution
        executive_presence = level_distribution.get("level_7", 0) + level_distribution.get("level_8", 0) + level_distribution.get("level_9", 0)
        has_executive_oversight = executive_presence > 0
        
        return {
            "overall_confidence": round(overall_confidence, 3),
            "completeness_score": round(completeness_score, 3),
            "role_mapping_quality": round(role_mapping_quality, 3),
            "department_coverage": round(department_coverage, 3),
            "level_distribution": level_distribution,
            "has_executive_oversight": has_executive_oversight,
            "total_roles": len(final_plan.roles),
            "total_fte": round(final_plan.total_fte_percentage or 0, 1),
            "estimated_budget": final_plan.financial_structure.total_budget if final_plan.financial_structure else None,
            "quality_flags": self._identify_quality_flags(final_plan, overall_confidence, completeness_score)
        }
    
    def _identify_quality_flags(self, 
                              final_plan: OctagonStaffingPlan,
                              confidence: float,
                              completeness: float) -> List[str]:
        """Identify quality issues that need attention"""
        
        flags = []
        
        # Low confidence
        if confidence < 0.7:
            flags.append("Low overall confidence - manual review recommended")
        
        # Low completeness
        if completeness < 0.8:
            flags.append("Low completeness score - may be missing key roles")
        
        # No executive oversight
        executive_levels = [7, 8, 9]
        has_executive = any(
            role.octagon_level and role.octagon_level.value in executive_levels 
            for role in final_plan.roles
        )
        if not has_executive and final_plan.total_fte_percentage and final_plan.total_fte_percentage > 200:
            flags.append("Large project without executive oversight")
        
        # Unmapped roles
        unmapped_roles = [role for role in final_plan.roles if not role.octagon_department]
        if unmapped_roles:
            flags.append(f"{len(unmapped_roles)} roles not mapped to Octagon departments")
        
        # Single department
        departments = set(role.octagon_department for role in final_plan.roles if role.octagon_department)
        if len(departments) == 1:
            flags.append("All roles in single department - may need cross-functional input")
        
        return flags


# ============================================================================
# EXAMPLE USAGE AND TESTING
# ============================================================================

async def test_integrated_service():
    """Test the integrated service with sample SOW data"""
    
    # Sample SOW text as bytes
    sample_sow_text = """
    Project Title: Company 1 Americas 2024-2025 Sponsorship Hospitality Programs
    Client: Company 1
    Contract Number: 1124711 633889
    Effective Date: October 1, 2024
    Duration: 52 weeks
    
    Scope of Work:
    Develop B2B hospitality programming for three (3) Events:
    - Formula 1 – Las Vegas Race (2024)
    - 67th Annual GRAMMY Awards  
    - 2025 API Tournament
    
    Deliverables:
    - High end hospitality programming for up to forty (40) B2B guests/hosts total at Event
    - Compliance documents and necessary approvals decks for guest approvals
    - Program budgets for Hospitality Room, gift premiums, transportation and GRAMMYs assets
    - Third party vendor management including A/V, décor, and gift premiums
    - Guest communications including pre-trip documents, welcome packets and branding elements
    - Program recap and reporting
    
    Project Staffing Plan:
    Account Director - Program Lead Formula 1 – Las Vegas Day to Day Manager
    Account Manager - API Day to Day Manager  
    SAE - GRAMMY's Day to Day Manager
    AE - Program Support
    
    Budget: $3,380 total hours allocated across team
    """
    
    # Create a mock DOCX file by adding the ZIP signature
    file_bytes = b'PK\x03\x04' + sample_sow_text.encode('utf-8')
    
    # Initialize service
    service = OctagonIntegratedService()
    
    # Process SOW
    result = await service.process_sow_and_recommend_staffing(file_bytes, "company_1_sow_test.docx")
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    # Display results
    print("\n" + "="*80)
    print("OCTAGON INTEGRATED SOW PROCESSING RESULTS")
    print("="*80)
    
    final_plan = result["final_staffing_plan"]
    quality_metrics = result["quality_metrics"]
    
    print(f"\nProject: {final_plan.project_info.project_name}")
    print(f"Client: {final_plan.project_info.client_name}")
    print(f"Duration: {final_plan.project_info.duration_weeks} weeks")
    
    print(f"\n=== STAFFING RECOMMENDATION ===")
    print(f"Total Roles: {len(final_plan.roles)}")
    print(f"Total FTE: {final_plan.total_fte_percentage:.1f}%")
    print(f"Estimated Budget: ${final_plan.financial_structure.total_budget:,.0f}" if final_plan.financial_structure else "Budget: Not estimated")
    
    print(f"\n=== ROLE BREAKDOWN ===")
    for role in final_plan.roles:
        dept_name = role.octagon_department.value if role.octagon_department else "Unknown"
        level_name = f"Level {role.octagon_level.value}" if role.octagon_level else "Unknown"
        confidence = role.confidence_score
        print(f"{role.role_title}: {role.normalized_fte_percentage:.1f}% FTE ({dept_name}, {level_name}) [Confidence: {confidence:.2f}]")
    
    print(f"\n=== DEPARTMENT ALLOCATION ===")
    for dept, fte in final_plan.service_line_allocation.items():
        print(f"{dept.value}: {fte:.1f}% FTE")
    
    print(f"\n=== QUALITY METRICS ===")
    print(f"Overall Confidence: {quality_metrics['overall_confidence']:.2f}")
    print(f"Completeness Score: {quality_metrics['completeness_score']:.2f}")
    print(f"Role Mapping Quality: {quality_metrics['role_mapping_quality']:.2f}")
    print(f"Department Coverage: {quality_metrics['department_coverage']:.2f}")
    print(f"Has Executive Oversight: {quality_metrics['has_executive_oversight']}")
    
    if quality_metrics['quality_flags']:
        print(f"\n=== QUALITY FLAGS ===")
        for flag in quality_metrics['quality_flags']:
            print(f"⚠️  {flag}")
    else:
        print(f"\n✅ No quality issues identified")
    
    print(f"\n=== AI ANALYSIS INSIGHTS ===")
    if final_plan.raw_extraction_data and "ai_recommendation" in final_plan.raw_extraction_data:
        ai_data = final_plan.raw_extraction_data["ai_recommendation"]
        if "project_requirements" in ai_data:
            reqs = ai_data["project_requirements"]
            print(f"Project Type: {reqs.get('project_type', 'Unknown')}")
            print(f"Complexity: {reqs.get('complexity', 'Unknown')}")
            print(f"Geographic Scope: {reqs.get('geographic_scope', 'Unknown')}")
            print(f"Events Count: {reqs.get('events_count', 0)}")
            print(f"Deliverables Count: {reqs.get('deliverables_count', 0)}")
    
    return result


if __name__ == "__main__":
    asyncio.run(test_integrated_service())
