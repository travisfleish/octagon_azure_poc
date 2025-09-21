#!/usr/bin/env python3
"""
Octagon Staffing Plan Generator Schema
=====================================

Purpose: Phase 1 ("Crawl") prototype for normalizing heterogeneous SOW documents
into structured staffing plans for Octagon (sports marketing agency).

Key Requirements:
- Handle mixed SOW formats (PDF, DOCX)
- Normalize FTE % ↔ hours
- Map to Octagon's service lines/departments
- Track billability vs non-billable
- Maintain traceability between raw text and structured fields
- Build extensible foundation for future predictive modeling
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, computed_field


# ============================================================================
# OCTAGON ORGANIZATIONAL STRUCTURE (Based on Official Org Chart)
# ============================================================================

class OctagonDepartment(str, Enum):
    """Octagon's four main departments from the organizational chart"""
    CLIENT_SERVICES = "client_services"
    STRATEGY = "strategy"
    PLANNING_CREATIVE = "planning_creative"
    INTEGRATED_PRODUCTION_EXPERIENCES = "integrated_production_experiences"


class OctagonLevel(int, Enum):
    """Octagon's 9-level seniority system (1=entry, 9=executive)"""
    LEVEL_1 = 1  # Entry level: AE, Trainee, Jr. roles
    LEVEL_2 = 2  # Sr. AE, Planner, Analyst, Producer
    LEVEL_3 = 3  # Manager, Sr. Manager
    LEVEL_4 = 4  # Sr. Account Manager, Senior Manager
    LEVEL_5 = 5  # Director, Account Director, ACD
    LEVEL_6 = 6  # Group Director
    LEVEL_7 = 7  # Vice President
    LEVEL_8 = 8  # Senior Vice President
    LEVEL_9 = 9  # Executive Vice President


class OctagonRole(str, Enum):
    """Specific roles within Octagon's organizational structure"""
    
    # CLIENT SERVICES DEPARTMENT
    EXEC_VICE_PRESIDENT = "exec_vice_president"
    SR_VICE_PRESIDENT = "sr_vice_president"
    VICE_PRESIDENT = "vice_president"
    GROUP_DIRECTOR = "group_director"
    ACCOUNT_DIRECTOR = "account_director"
    SR_ACCOUNT_MANAGER = "sr_account_manager"
    ACCOUNT_MANAGER = "account_manager"
    SR_ACCOUNT_EXECUTIVE = "sr_account_executive"
    ACCOUNT_EXECUTIVE = "account_executive"
    ACCOUNT_TRAINEE = "account_trainee"
    
    # STRATEGY DEPARTMENT
    EXEC_VICE_PRESIDENT_STRATEGY = "exec_vice_president_strategy"
    SR_VP_INNOVATION = "sr_vp_innovation"
    SR_VP_SPONSORSHIP_STRATEGY = "sr_vp_sponsorship_strategy"
    SR_VP_DIGITAL_MEDIA = "sr_vp_digital_media"
    SR_VP_SOCIAL_MEDIA = "sr_vp_social_media"
    VP_SPONSORSHIP_STRATEGY = "vp_sponsorship_strategy"
    VP_INNOVATION = "vp_innovation"
    VP_DIGITAL_MEDIA = "vp_digital_media"
    VP_SOCIAL_MEDIA = "vp_social_media"
    GROUP_DIRECTOR_SPONSORSHIP_STRATEGY = "group_director_sponsorship_strategy"
    GROUP_DIRECTOR_CRM_STRATEGY = "group_director_crm_strategy"
    GROUP_DIRECTOR_INNOVATION = "group_director_innovation"
    GROUP_DIRECTOR_DIGITAL_MEDIA = "group_director_digital_media"
    GROUP_DIRECTOR_SOCIAL_MEDIA = "group_director_social_media"
    DIRECTOR_ANALYTICS_DEVELOPER = "director_analytics_developer"
    DIRECTOR_UX_UI_INNOVATION = "director_ux_ui_innovation"
    DIRECTOR_DIGITAL_MEDIA = "director_digital_media"
    DIRECTOR_SOCIAL_MEDIA = "director_social_media"
    DIRECTOR_PRODUCTS_ANALYTICS = "director_products_analytics"
    DIRECTOR_CRM_STRATEGY = "director_crm_strategy"
    DIRECTOR_SPONSORSHIP_STRATEGY = "director_sponsorship_strategy"
    DIRECTOR_EXPERIENTIAL_STRATEGIST = "director_experiential_strategist"
    SR_FULL_STACK_DEVELOPER = "sr_full_stack_developer"
    SR_MANAGER = "sr_manager"
    MANAGER_SPONSORSHIP_STRATEGY = "manager_sponsorship_strategy"
    MANAGER_RESEARCH = "manager_research"
    MANAGER_CRM_STRATEGY = "manager_crm_strategy"
    MANAGER_DIGITAL_COPYWRITER = "manager_digital_copywriter"
    MANAGER_DIGITAL_MEDIA = "manager_digital_media"
    MANAGER_SOCIAL_MEDIA = "manager_social_media"
    MANAGER_SPONSORSHIP_PLANNER = "manager_sponsorship_planner"
    MANAGER_FULL_STACK_DEVELOPER = "manager_full_stack_developer"
    MANAGER_ACCOUNT_EXECUTIVE_CRM = "manager_account_executive_crm"
    PLANNER_SPONSORSHIP_STRATEGY = "planner_sponsorship_strategy"
    ANALYST_DIGITAL_MEDIA = "analyst_digital_media"
    ANALYST_SOCIAL_MEDIA = "analyst_social_media"
    ANALYTICS_DEVELOPER = "analytics_developer"
    DIGITAL_TRAINEE = "digital_trainee"
    JR_PLANNER = "jr_planner"
    
    # PLANNING & CREATIVE DEPARTMENT
    EXEC_VICE_PRESIDENT_CREATIVE = "exec_vice_president_creative"
    SR_VP_CONCEPT = "sr_vp_concept"
    SR_VP_CREATIVE_SERVICES = "sr_vp_creative_services"
    VP_EXECUTIVE_PRODUCER = "vp_executive_producer"
    VP_CREATIVE_PLANNER = "vp_creative_planner"
    VP_CREATIVE_DIRECTOR = "vp_creative_director"
    GROUP_DIRECTOR_CREATIVE_DIRECTOR = "group_director_creative_director"
    GROUP_DIRECTOR_CREATIVE_PLANNER = "group_director_creative_planner"
    GROUP_DIRECTOR_DESIGN = "group_director_design"
    DIRECTOR_ACD_DESIGN = "director_acd_design"
    DIRECTOR_ASSOCIATE_CREATIVE_DIRECTOR = "director_associate_creative_director"
    DIRECTOR_ACD_3D_DESIGN = "director_acd_3d_design"
    DIRECTOR_SR_CONTENT_EDITOR = "director_sr_content_editor"
    DIRECTOR_SR_PLANNER = "director_sr_planner"
    SR_MANAGER_CREATIVE = "sr_manager_creative"
    MANAGER_CONTENT_PRODUCER = "manager_content_producer"
    MANAGER_CONTENT_EDITOR = "manager_content_editor"
    MANAGER_PROJECT_MANAGER = "manager_project_manager"
    MANAGER_3D_DESIGNER = "manager_3d_designer"
    MANAGER_ART_DIRECTOR = "manager_art_director"
    MANAGER_ART_DIRECTOR_JR = "manager_art_director_jr"
    PRODUCER_STRATEGIST = "producer_strategist"
    SR_PROJECT_COORDINATOR = "sr_project_coordinator"
    JR_DIRECTOR = "jr_director"
    JR_PRODUCER = "jr_producer"
    JR_DEVELOPER = "jr_developer"
    
    # INTEGRATED PRODUCTION/EXPERIENCES DEPARTMENT
    # (Same structure as Client Services but for production/experiences focus)
    EXEC_VICE_PRESIDENT_PROD = "exec_vice_president_prod"
    SR_VICE_PRESIDENT_PROD = "sr_vice_president_prod"
    VICE_PRESIDENT_PROD = "vice_president_prod"
    GROUP_DIRECTOR_PROD = "group_director_prod"
    ACCOUNT_DIRECTOR_PROD = "account_director_prod"
    SR_ACCOUNT_MANAGER_PROD = "sr_account_manager_prod"
    ACCOUNT_MANAGER_PROD = "account_manager_prod"
    SR_ACCOUNT_EXECUTIVE_PROD = "sr_account_executive_prod"
    ACCOUNT_EXECUTIVE_PROD = "account_executive_prod"
    TRAINEE_PROD = "trainee_prod"


# Legacy enum for backward compatibility
class SeniorityLevel(str, Enum):
    """Legacy seniority levels - use OctagonLevel instead"""
    LEVEL_1 = "level_1"  # Entry level
    LEVEL_2 = "level_2"  # Senior AE, Planner, Analyst
    LEVEL_3 = "level_3"  # Manager
    LEVEL_4 = "level_4"  # Senior Manager
    LEVEL_5 = "level_5"  # Director
    LEVEL_6 = "level_6"  # Group Director
    LEVEL_7 = "level_7"  # Vice President
    LEVEL_8 = "level_8"  # Senior Vice President
    LEVEL_9 = "level_9"  # Executive Vice President


# ============================================================================
# STAFFING ALLOCATION MODELS
# ============================================================================

class AllocationType(str, Enum):
    """Types of resource allocation found in SOWs"""
    FTE_PERCENTAGE = "fte_percentage"  # % of full-time equivalent
    HOURS = "hours"  # Specific hour allocations
    RATE_BASED = "rate_based"  # Hourly/daily rates
    RETAINER = "retainer"  # Fixed monthly retainer
    PROJECT_BASED = "project_based"  # Fixed project fee


class BillabilityType(str, Enum):
    """Billability classification for staffing allocations"""
    BILLABLE = "billable"  # Direct client billable time
    NON_BILLABLE = "non_billable"  # Internal, overhead time
    PASS_THROUGH = "pass_through"  # Pass-through costs (vendors, etc.)
    UNKNOWN = "unknown"  # Not specified in SOW


# ============================================================================
# RAW EXTRACTION TRACEABILITY
# ============================================================================

class ExtractedField(BaseModel):
    """Tracks raw extracted text and its structured interpretation"""
    field_name: str
    raw_text: str
    structured_value: Any
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_section: Optional[str] = None  # Which section of SOW this came from
    extraction_method: Literal["regex", "llm", "heuristic", "manual", "ai"] = "llm"
    page_reference: Optional[str] = None


# ============================================================================
# NORMALIZED STAFFING ROLE
# ============================================================================

class StaffingRole(BaseModel):
    """Normalized staffing role for Octagon staffing plans"""
    
    # Core Role Information
    role_title: str
    octagon_department: Optional[OctagonDepartment] = None
    octagon_role: Optional[OctagonRole] = None
    octagon_level: Optional[OctagonLevel] = None
    
    # Legacy fields for backward compatibility
    service_line: Optional[str] = None  # Deprecated - use octagon_department
    seniority_level: Optional[SeniorityLevel] = None  # Deprecated - use octagon_level
    
    # Allocation Information
    allocation_type: AllocationType
    allocation_value: float  # Hours, FTE %, or rate
    billability: BillabilityType = BillabilityType.UNKNOWN
    
    # Duration & Timing
    project_duration_weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Additional Context
    primary_responsibilities: List[str] = Field(default_factory=list)
    special_instructions: Optional[str] = None
    location: Optional[str] = None
    
    # Traceability
    extracted_fields: List[ExtractedField] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    @computed_field
    @property
    def normalized_hours(self) -> Optional[float]:
        """Convert allocation to normalized hours (assuming 40hr/week for FTE)"""
        if self.allocation_type == AllocationType.HOURS:
            return self.allocation_value
        elif self.allocation_type == AllocationType.FTE_PERCENTAGE:
            if self.project_duration_weeks:
                return (self.allocation_value / 100.0) * 40.0 * self.project_duration_weeks
        return None
    
    @computed_field
    @property
    def normalized_fte_percentage(self) -> Optional[float]:
        """Convert allocation to normalized FTE percentage"""
        if self.allocation_type == AllocationType.FTE_PERCENTAGE:
            return self.allocation_value
        elif self.allocation_type == AllocationType.HOURS:
            if self.project_duration_weeks:
                weekly_hours = self.allocation_value / self.project_duration_weeks
                return (weekly_hours / 40.0) * 100.0
        return None


# ============================================================================
# PROJECT INFORMATION
# ============================================================================

class ProjectInfo(BaseModel):
    """Project-level information extracted from SOW"""
    
    # Basic Information
    project_name: str
    client_name: str
    project_id: Optional[str] = None
    
    # Timeline
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_weeks: Optional[int] = None
    
    # Project Characteristics
    project_type: Optional[str] = None  # e.g., "Sponsorship Activation", "Event Management"
    primary_service_lines: List[OctagonDepartment] = Field(default_factory=list)
    complexity_score: float = Field(ge=1.0, le=10.0, default=5.0)
    
    # Contract Information
    contract_number: Optional[str] = None
    effective_date: Optional[datetime] = None
    master_agreement_reference: Optional[str] = None
    
    # Traceability
    extracted_fields: List[ExtractedField] = Field(default_factory=list)


# ============================================================================
# FINANCIAL STRUCTURE
# ============================================================================

class FinancialStructure(BaseModel):
    """Financial structure extracted from SOW"""
    
    # Fee Structure
    primary_fee_type: AllocationType
    total_budget: Optional[float] = None
    currency: str = Field(default="USD")
    
    # Rate Information
    hourly_rates: Dict[str, float] = Field(default_factory=dict)  # Role -> Rate
    daily_rates: Dict[str, float] = Field(default_factory=dict)  # Role -> Rate
    
    # Budget Components
    labor_costs: Optional[float] = None
    pass_through_costs: Optional[float] = None
    overhead_costs: Optional[float] = None
    
    # Payment Terms
    payment_schedule: Optional[str] = None  # "Monthly", "Quarterly", etc.
    invoicing_frequency: Optional[str] = None
    
    # Traceability
    extracted_fields: List[ExtractedField] = Field(default_factory=list)


# ============================================================================
# NORMALIZED STAFFING PLAN
# ============================================================================

class OctagonStaffingPlan(BaseModel):
    """Normalized staffing plan for Octagon projects"""
    
    # Project Information
    project_info: ProjectInfo
    
    # Staffing Details
    roles: List[StaffingRole] = Field(default_factory=list)
    
    # Financial Information
    financial_structure: Optional[FinancialStructure] = None
    
    # Summary Metrics
    total_billable_hours: Optional[float] = None
    total_non_billable_hours: Optional[float] = None
    total_fte_percentage: Optional[float] = None
    
    # Department Breakdown (replacing service line allocation)
    service_line_allocation: Dict[OctagonDepartment, float] = Field(default_factory=dict)
    
    # Quality Metrics
    extraction_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    completeness_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Traceability
    source_sow_file: str
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_extraction_data: Optional[Dict[str, Any]] = None
    
    @computed_field
    @property
    def total_roles(self) -> int:
        """Total number of roles in the staffing plan"""
        return len(self.roles)
    
    @computed_field
    @property
    def departments_involved(self) -> List[OctagonDepartment]:
        """List of departments involved in the project"""
        return list(set(role.octagon_department for role in self.roles if role.octagon_department))
    
    @computed_field
    @property
    def service_lines_involved(self) -> List[OctagonDepartment]:
        """List of departments involved in the project"""
        return list(set(role.octagon_department for role in self.roles if role.octagon_department))


# ============================================================================
# PROCESSING WORKFLOW MODELS
# ============================================================================

class SOWProcessingJob(BaseModel):
    """Represents a SOW processing job for the prototype"""
    
    job_id: str
    source_file: str
    processing_type: Literal["new_staffing", "historical"] = "new_staffing"
    
    # Processing Status
    status: Literal["queued", "processing", "completed", "failed"] = "queued"
    error_message: Optional[str] = None
    
    # Results
    staffing_plan: Optional[OctagonStaffingPlan] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    processing_duration_seconds: Optional[float] = None


# ============================================================================
# NORMALIZATION UTILITIES
# ============================================================================

class StaffingPlanNormalizer:
    """Utilities for normalizing staffing data across different SOW formats"""
    
    # Role mapping from SOW text to Octagon roles and departments
    ROLE_MAPPING = {
        # CLIENT SERVICES DEPARTMENT
        "account director": (OctagonRole.ACCOUNT_DIRECTOR, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_5),
        "account manager": (OctagonRole.ACCOUNT_MANAGER, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_3),
        "sr. account manager": (OctagonRole.SR_ACCOUNT_MANAGER, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_4),
        "sr account manager": (OctagonRole.SR_ACCOUNT_MANAGER, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_4),
        "account executive": (OctagonRole.ACCOUNT_EXECUTIVE, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_1),
        "ae": (OctagonRole.ACCOUNT_EXECUTIVE, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_1),
        "sr. account executive": (OctagonRole.SR_ACCOUNT_EXECUTIVE, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_2),
        "sae": (OctagonRole.SR_ACCOUNT_EXECUTIVE, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_2),
        "account trainee": (OctagonRole.ACCOUNT_TRAINEE, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_1),
        "vice president": (OctagonRole.VICE_PRESIDENT, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_7),
        "vp": (OctagonRole.VICE_PRESIDENT, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_7),
        "group director": (OctagonRole.GROUP_DIRECTOR, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_6),
        
        # STRATEGY DEPARTMENT
        "strategy director": (OctagonRole.DIRECTOR_SPONSORSHIP_STRATEGY, OctagonDepartment.STRATEGY, OctagonLevel.LEVEL_5),
        "strategist": (OctagonRole.PLANNER_SPONSORSHIP_STRATEGY, OctagonDepartment.STRATEGY, OctagonLevel.LEVEL_2),
        "planner": (OctagonRole.PLANNER_SPONSORSHIP_STRATEGY, OctagonDepartment.STRATEGY, OctagonLevel.LEVEL_2),
        "sponsorship strategist": (OctagonRole.DIRECTOR_SPONSORSHIP_STRATEGY, OctagonDepartment.STRATEGY, OctagonLevel.LEVEL_5),
        "analyst": (OctagonRole.ANALYST_DIGITAL_MEDIA, OctagonDepartment.STRATEGY, OctagonLevel.LEVEL_2),
        "data analyst": (OctagonRole.ANALYTICS_DEVELOPER, OctagonDepartment.STRATEGY, OctagonLevel.LEVEL_2),
        
        # PLANNING & CREATIVE DEPARTMENT
        "creative director": (OctagonRole.VP_CREATIVE_DIRECTOR, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_7),
        "art director": (OctagonRole.MANAGER_ART_DIRECTOR, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_3),
        "project manager": (OctagonRole.MANAGER_PROJECT_MANAGER, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_3),
        "producer": (OctagonRole.MANAGER_CONTENT_PRODUCER, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_3),
        "coordinator": (OctagonRole.SR_PROJECT_COORDINATOR, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_2),
        "content producer": (OctagonRole.MANAGER_CONTENT_PRODUCER, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_3),
        
        # INTEGRATED PRODUCTION/EXPERIENCES DEPARTMENT
        "event manager": (OctagonRole.ACCOUNT_MANAGER_PROD, OctagonDepartment.INTEGRATED_PRODUCTION_EXPERIENCES, OctagonLevel.LEVEL_3),
        "hospitality manager": (OctagonRole.ACCOUNT_MANAGER_PROD, OctagonDepartment.INTEGRATED_PRODUCTION_EXPERIENCES, OctagonLevel.LEVEL_3),
        "experience coordinator": (OctagonRole.SR_ACCOUNT_EXECUTIVE_PROD, OctagonDepartment.INTEGRATED_PRODUCTION_EXPERIENCES, OctagonLevel.LEVEL_2),
        
        # Generic mappings for common variations
        "manager": (OctagonRole.MANAGER_PROJECT_MANAGER, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_3),
        "director": (OctagonRole.ACCOUNT_DIRECTOR, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_5),
        "consultant": (OctagonRole.ACCOUNT_MANAGER, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_3),
    }
    
    @classmethod
    def map_role_to_octagon_structure(cls, role_title: str) -> tuple[Optional[OctagonRole], Optional[OctagonDepartment], Optional[OctagonLevel]]:
        """Map a role title to Octagon role, department, and level"""
        role_lower = role_title.lower().strip()
        
        # Try exact match first
        if role_lower in cls.ROLE_MAPPING:
            return cls.ROLE_MAPPING[role_lower]
        
        # Try partial matches
        for pattern, (role, dept, level) in cls.ROLE_MAPPING.items():
            if pattern in role_lower or role_lower in pattern:
                return (role, dept, level)
        
        # Try keyword matching
        if "account" in role_lower and "director" in role_lower:
            return (OctagonRole.ACCOUNT_DIRECTOR, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_5)
        elif "account" in role_lower and "manager" in role_lower:
            return (OctagonRole.ACCOUNT_MANAGER, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_3)
        elif "account" in role_lower and "executive" in role_lower:
            return (OctagonRole.ACCOUNT_EXECUTIVE, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_1)
        elif "creative" in role_lower and "director" in role_lower:
            return (OctagonRole.VP_CREATIVE_DIRECTOR, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_7)
        elif "strategy" in role_lower:
            return (OctagonRole.PLANNER_SPONSORSHIP_STRATEGY, OctagonDepartment.STRATEGY, OctagonLevel.LEVEL_2)
        elif "manager" in role_lower:
            return (OctagonRole.MANAGER_PROJECT_MANAGER, OctagonDepartment.PLANNING_CREATIVE, OctagonLevel.LEVEL_3)
        elif "director" in role_lower:
            return (OctagonRole.ACCOUNT_DIRECTOR, OctagonDepartment.CLIENT_SERVICES, OctagonLevel.LEVEL_5)
        
        return (None, None, None)
    
    @classmethod
    def map_role_to_department(cls, role_title: str) -> Optional[OctagonDepartment]:
        """Map a role title to Octagon department (legacy method)"""
        _, dept, _ = cls.map_role_to_octagon_structure(role_title)
        return dept
    
    @classmethod
    def normalize_allocation(cls, value: float, allocation_type: AllocationType, 
                           project_weeks: Optional[int] = None) -> Dict[str, Optional[float]]:
        """Normalize allocation between hours and FTE percentage"""
        result = {"hours": None, "fte_percentage": None}
        
        if allocation_type == AllocationType.HOURS:
            result["hours"] = value
            if project_weeks:
                weekly_hours = value / project_weeks
                result["fte_percentage"] = (weekly_hours / 40.0) * 100.0
        elif allocation_type == AllocationType.FTE_PERCENTAGE:
            result["fte_percentage"] = value
            if project_weeks:
                result["hours"] = (value / 100.0) * 40.0 * project_weeks
        
        return result


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def create_example_octagon_staffing_plan() -> OctagonStaffingPlan:
    """Create an example Octagon staffing plan based on the SOW analysis"""
    
    # Project info from Company 1 SOW analysis
    project_info = ProjectInfo(
        project_name="Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
        client_name="Company 1",
        project_id="SOW-001-2024",
        duration_weeks=52,  # Full year program
        project_type="Sponsorship Hospitality",
        primary_service_lines=[OctagonDepartment.INTEGRATED_PRODUCTION_EXPERIENCES, OctagonDepartment.CLIENT_SERVICES],
        complexity_score=7.0,
        contract_number="1124711 633889",
        effective_date=datetime(2024, 10, 1)
    )
    
    # Roles based on SOW analysis with Octagon mapping
    roles = [
        StaffingRole(
            role_title="Account Director",
            octagon_department=OctagonDepartment.CLIENT_SERVICES,
            octagon_role=OctagonRole.ACCOUNT_DIRECTOR,
            octagon_level=OctagonLevel.LEVEL_5,
            allocation_type=AllocationType.FTE_PERCENTAGE,
            allocation_value=25.0,  # 25% FTE
            billability=BillabilityType.BILLABLE,
            project_duration_weeks=52,
            primary_responsibilities=["Program Lead", "Formula 1 Las Vegas Manager"],
            location="Formula 1 – Las Vegas",
            confidence_score=0.9,
            extracted_fields=[
                ExtractedField(
                    field_name="role_title",
                    raw_text="Account Director Program Lead Formula 1 – Las Vegas Day to Day Manager 780",
                    structured_value="Account Director",
                    confidence_score=0.9,
                    source_section="Project Staffing Plan",
                    extraction_method="llm"
                )
            ]
        ),
        StaffingRole(
            role_title="Account Manager",
            octagon_department=OctagonDepartment.CLIENT_SERVICES,
            octagon_role=OctagonRole.ACCOUNT_MANAGER,
            octagon_level=OctagonLevel.LEVEL_3,
            allocation_type=AllocationType.FTE_PERCENTAGE,
            allocation_value=30.0,  # 30% FTE
            billability=BillabilityType.BILLABLE,
            project_duration_weeks=52,
            primary_responsibilities=["API Day to Day Manager"],
            confidence_score=0.9
        ),
        StaffingRole(
            role_title="SAE",
            octagon_department=OctagonDepartment.CLIENT_SERVICES,
            octagon_role=OctagonRole.SR_ACCOUNT_EXECUTIVE,
            octagon_level=OctagonLevel.LEVEL_2,
            allocation_type=AllocationType.FTE_PERCENTAGE,
            allocation_value=30.0,  # 30% FTE
            billability=BillabilityType.BILLABLE,
            project_duration_weeks=52,
            primary_responsibilities=["GRAMMY's Day to Day Manager"],
            confidence_score=0.8
        ),
        StaffingRole(
            role_title="AE",
            octagon_department=OctagonDepartment.CLIENT_SERVICES,
            octagon_role=OctagonRole.ACCOUNT_EXECUTIVE,
            octagon_level=OctagonLevel.LEVEL_1,
            allocation_type=AllocationType.FTE_PERCENTAGE,
            allocation_value=15.0,  # 15% FTE
            billability=BillabilityType.BILLABLE,
            project_duration_weeks=52,
            primary_responsibilities=["Program Support"],
            confidence_score=0.8
        )
    ]
    
    # Financial structure
    financial_structure = FinancialStructure(
        primary_fee_type=AllocationType.RETAINER,
        currency="USD",
        total_budget=3380.0,  # Total hours from analysis
        labor_costs=3380.0,
        payment_schedule="Monthly",
        extracted_fields=[
            ExtractedField(
                field_name="total_hours",
                raw_text="TOTAL 3,380 The allocations of time set forth are estimates",
                structured_value=3380.0,
                confidence_score=0.9,
                source_section="Project Staffing Plan",
                extraction_method="regex"
            )
        ]
    )
    
    # Calculate summary metrics
    total_fte = sum(role.normalized_fte_percentage or 0 for role in roles)
    
    # Department allocation (replacing service line allocation)
    department_allocation = {}
    for role in roles:
        if role.octagon_department and role.normalized_fte_percentage:
            if role.octagon_department not in department_allocation:
                department_allocation[role.octagon_department] = 0
            department_allocation[role.octagon_department] += role.normalized_fte_percentage
    
    return OctagonStaffingPlan(
        project_info=project_info,
        roles=roles,
        financial_structure=financial_structure,
        total_fte_percentage=total_fte,
        service_line_allocation=department_allocation,  # Using department allocation as service line allocation
        extraction_confidence=0.85,
        completeness_score=0.9,
        source_sow_file="company_1_sow_1.docx"
    )


if __name__ == "__main__":
    # Test the Octagon-specific schema
    example_plan = create_example_octagon_staffing_plan()
    
    print("Octagon Staffing Plan Example:")
    print(f"Project: {example_plan.project_info.project_name}")
    print(f"Client: {example_plan.project_info.client_name}")
    print(f"Total Roles: {example_plan.total_roles}")
    print(f"Total FTE: {example_plan.total_fte_percentage:.1f}%")
    print(f"Departments: {example_plan.departments_involved}")
    print(f"Service Lines: {example_plan.service_lines_involved}")
    
    print("\nRole Breakdown:")
    for role in example_plan.roles:
        dept_name = role.octagon_department.value if role.octagon_department else "Unknown"
        level_name = f"Level {role.octagon_level.value}" if role.octagon_level else "Unknown"
        print(f"  {role.role_title}: {role.normalized_fte_percentage:.1f}% FTE ({dept_name}, {level_name})")
    
    print(f"\nDepartment Allocation:")
    for dept, fte in example_plan.service_line_allocation.items():
        print(f"  {dept.value}: {fte:.1f}% FTE")
    
    # Test normalizer
    normalizer = StaffingPlanNormalizer()
    print(f"\nNormalizer Test:")
    role, dept, level = normalizer.map_role_to_octagon_structure("Account Manager")
    print(f"Account Manager -> Role: {role.value if role else None}, Dept: {dept.value if dept else None}, Level: {level.value if level else None}")
    
    role, dept, level = normalizer.map_role_to_octagon_structure("Creative Director")
    print(f"Creative Director -> Role: {role.value if role else None}, Dept: {dept.value if dept else None}, Level: {level.value if level else None}")
    
    print(f"25% FTE, 52 weeks -> {normalizer.normalize_allocation(25.0, AllocationType.FTE_PERCENTAGE, 52)}")
