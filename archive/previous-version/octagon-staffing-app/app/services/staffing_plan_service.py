"""
Staffing Plan Service - Integrates heuristics engine with SOW processing
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime

from .heuristics_engine import HeuristicsEngine, Department, Role
from ..models.sow import ProcessedSOW
from ..models.staffing import StaffingPlan, StaffingRole


class StaffingPlanService:
    """Service that generates staffing plans using heuristics + AI augmentation"""
    
    def __init__(self):
        self.heuristics_engine = HeuristicsEngine()
    
    def generate_staffing_plan_from_sow(self, processed_sow: ProcessedSOW, llm_data: Dict[str, Any]) -> StaffingPlan:
        """
        Generate a staffing plan from processed SOW data and LLM extraction results
        
        Args:
            processed_sow: ProcessedSOW object from document intelligence
            llm_data: Raw LLM extraction data containing roles_detected
            
        Returns:
            StaffingPlan with heuristics-based allocations
        """
        
        # Extract roles from LLM data
        detected_roles = self._extract_roles_from_llm_data(llm_data)
        
        # Debug: Print detected roles
        print(f"DEBUG: Detected roles from LLM: {detected_roles}")
        
        # Generate baseline allocations using heuristics
        baseline_allocations = self.heuristics_engine.generate_baseline_allocations(detected_roles)
        
        # Convert heuristics output to StaffingPlan format
        staffing_plan = self._convert_allocations_to_staffing_plan(
            sow_id=processed_sow.sow_id,
            baseline_allocations=baseline_allocations,
            llm_data=llm_data
        )
        
        return staffing_plan
    
    def _extract_roles_from_llm_data(self, llm_data: Dict[str, Any]) -> List[str]:
        """Extract role titles from LLM extraction data"""
        roles_detected = llm_data.get('roles_detected', [])
        
        if not roles_detected:
            return []
        
        # Extract role titles, handling both string and dict formats
        role_titles = []
        for role_item in roles_detected:
            if isinstance(role_item, dict):
                title = role_item.get('title', '')
                if title:
                    role_titles.append(title)
            elif isinstance(role_item, str):
                role_titles.append(role_item)
        
        return role_titles
    
    def _convert_allocations_to_staffing_plan(
        self, 
        sow_id: str, 
        baseline_allocations: Dict[str, Any],
        llm_data: Dict[str, Any]
    ) -> StaffingPlan:
        """Convert heuristics allocations to StaffingPlan format"""
        
        roles = []
        related_projects = []
        
        # Convert department allocations to StaffingRole objects
        for dept_name, allocation in baseline_allocations.get('departments', {}).items():
            if allocation.get('detected_roles'):
                # Create roles for detected positions
                for role_title in allocation['detected_roles']:
                    fte_percentage = int(allocation['suggested_fte'] * 100)
                    
                    # Get role details from heuristics engine to find level
                    role_details = self.heuristics_engine.org_chart.get_role_by_title(role_title)
                    role_level = role_details.level if role_details else None
                    
                    roles.append(StaffingRole(
                        role=role_title,
                        department=dept_name.replace('_', ' ').title(),
                        level=role_level,
                        quantity=1,  # Default to 1 person per role
                        allocation_percent=fte_percentage,
                        notes=f"AI DRAFT - {dept_name.replace('_', ' ').title()} allocation"
                    ))
        
        # Add special rule roles
        for rule in baseline_allocations.get('special_rules', []):
            fte_percentage = int(rule['fte'] * 100)
            
            # Get role details for special rules
            role_details = self.heuristics_engine.org_chart.get_role_by_title(rule['role'])
            role_level = role_details.level if role_details else None
            role_department = role_details.department.value.replace('_', ' ').title() if role_details else "Special Rules"
            
            roles.append(StaffingRole(
                role=rule['role'],
                department=role_department,
                level=role_level,
                quantity=1,
                allocation_percent=fte_percentage,
                notes=f"AI DRAFT - {rule['rule']} rule"
            ))
        
        # Generate summary
        total_fte = baseline_allocations.get('total_allocated_fte', 0.0)
        summary = self._generate_plan_summary(
            roles=roles,
            total_fte=total_fte,
            llm_data=llm_data,
            baseline_allocations=baseline_allocations
        )
        
        # Calculate confidence based on role mapping success
        detected_roles = self._extract_roles_from_llm_data(llm_data)
        confidence = self._calculate_confidence(detected_roles, roles)
        
        return StaffingPlan(
            sow_id=sow_id,
            summary=summary,
            roles=roles,
            confidence=confidence,
            related_projects=related_projects
        )
    
    def _generate_plan_summary(
        self, 
        roles: List[StaffingRole], 
        total_fte: float,
        llm_data: Dict[str, Any],
        baseline_allocations: Dict[str, Any]
    ) -> str:
        """Generate a summary of the staffing plan"""
        
        # Get project info from LLM data
        company = llm_data.get('company', 'Unknown')
        sow_id = llm_data.get('sow_id', 'Unknown')
        term_months = llm_data.get('term', {}).get('months', 'Unknown')
        
        # Count departments involved
        departments = list(baseline_allocations.get('departments', {}).keys())
        
        summary_parts = [
            f"AI DRAFT Staffing Plan for {company} - {sow_id}",
            f"Project Duration: {term_months} months" if term_months != 'Unknown' else "Duration: TBD",
            f"Departments: {', '.join([d.replace('_', ' ').title() for d in departments])}",
            f"Total Allocation: {total_fte:.1%} FTE",
            f"Roles Identified: {len(roles)} positions",
            "",
            "⚠️ This is an AI-generated draft based on baseline heuristics.",
            "Please review and adjust based on institutional knowledge and project specifics."
        ]
        
        return '\n'.join(summary_parts)
    
    def _calculate_confidence(self, detected_roles: List[str], mapped_roles: List[StaffingRole]) -> float:
        """Calculate confidence score based on role mapping success"""
        
        if not detected_roles:
            return 0.5  # Default confidence if no roles detected
        
        # Simple confidence based on mapping success
        mapped_count = len(mapped_roles)
        total_detected = len(detected_roles)
        
        if total_detected == 0:
            return 0.5
        
        # Base confidence on mapping ratio
        mapping_ratio = min(mapped_count / total_detected, 1.0)
        
        # Adjust confidence based on total roles (more roles = more complex = lower confidence)
        role_complexity_factor = max(0.7, 1.0 - (mapped_count * 0.05))
        
        confidence = mapping_ratio * role_complexity_factor
        
        return round(confidence, 2)
    
    def get_staffing_recommendations(self, processed_sow: ProcessedSOW) -> Dict[str, Any]:
        """
        Get staffing recommendations with both heuristics and AI augmentation
        
        This method provides a more detailed breakdown for the Streamlit interface
        """
        
        # This would integrate with your existing vector search for similar projects
        # For now, return the basic heuristics output
        return {
            "heuristics_applied": True,
            "ai_augmented": False,  # Will be True when integrated with vector search
            "status": "draft",
            "notes": ["Generated using baseline heuristics rules"]
        }


# Example usage function for testing
def test_staffing_plan_integration():
    """Test the integration with sample SOW data"""
    
    # Sample LLM data (what would come from your existing pipeline)
    sample_llm_data = {
        "blob_name": "company_1_sow_1.pdf",
        "company": "Company 1",
        "sow_id": "SOW-001",
        "format": "pdf",
        "term": {
            "start": "2024-01-01",
            "end": "2024-06-30",
            "months": 6,
            "inferred": False
        },
        "roles_detected": [
            {"title": "Account Manager", "canonical": "Account Manager"},
            {"title": "Creative Director", "canonical": "Creative Director"},
            {"title": "Project Manager", "canonical": "Project Manager"},
            {"title": "Strategy Analyst", "canonical": "Strategy Analyst"}
        ],
        "scope_bullets": ["Marketing campaign development", "Brand strategy implementation"],
        "deliverables": ["Creative assets", "Campaign materials"],
        "units": {
            "explicit_hours": [800, 600],
            "fte_pct": [50, 75],
            "fees": [],
            "rate_table": []
        },
        "assumptions": [],
        "provenance": {
            "quotes": [],
            "sections": [],
            "notes": "Generated from SOW text"
        }
    }
    
    # Sample ProcessedSOW
    from ..models.sow import ProcessedSOW
    processed_sow = ProcessedSOW(
        sow_id="SOW-001",
        sections=["Scope", "Deliverables"],
        key_entities=["Company 1", "Marketing Campaign"],
        raw_extraction=sample_llm_data
    )
    
    # Test the service
    service = StaffingPlanService()
    staffing_plan = service.generate_staffing_plan_from_sow(processed_sow, sample_llm_data)
    
    print("Generated Staffing Plan:")
    print(f"Summary: {staffing_plan.summary}")
    print(f"Confidence: {staffing_plan.confidence}")
    print(f"Roles: {len(staffing_plan.roles)}")
    
    for role in staffing_plan.roles:
        print(f"  - {role.role}: {role.allocation_percent}% ({role.notes})")
    
    return staffing_plan


if __name__ == "__main__":
    test_staffing_plan_integration()
