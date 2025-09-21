#!/usr/bin/env python3
"""
Octagon Staffing Plan Recommendation Engine
==========================================

This engine takes an SOW and uses AI + heuristics to generate intelligent
staffing plan recommendations based on Octagon's organizational structure.

Key Components:
1. SOW Analyzer - Extracts project requirements and complexity
2. Heuristics Engine - Applies Octagon-specific allocation rules
3. AI Recommendation Engine - Uses LLM to suggest role allocations
4. Recommendation Synthesizer - Combines AI + heuristics for final plan
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from octagon_staffing_schema import (
    OctagonStaffingPlan, ProjectInfo, StaffingRole, FinancialStructure,
    OctagonDepartment, OctagonRole, OctagonLevel, AllocationType,
    BillabilityType, ExtractedField, StaffingPlanNormalizer
)


# ============================================================================
# PROJECT COMPLEXITY ANALYSIS
# ============================================================================

class ProjectComplexity(str, Enum):
    """Project complexity levels for staffing recommendations"""
    SIMPLE = "simple"  # Single event, clear scope, < 3 months
    MODERATE = "moderate"  # Multiple events, some complexity, 3-12 months
    COMPLEX = "complex"  # Multi-year, multiple properties, complex deliverables
    ENTERPRISE = "enterprise"  # Global programs, multiple stakeholders, 12+ months


class ProjectType(str, Enum):
    """Types of projects for staffing recommendations"""
    SPONSORSHIP_ACTIVATION = "sponsorship_activation"
    EVENT_MANAGEMENT = "event_management"
    HOSPITALITY_PROGRAM = "hospitality_program"
    CREATIVE_CAMPAIGN = "creative_campaign"
    STRATEGIC_PLANNING = "strategic_planning"
    PARTNERSHIP_MANAGEMENT = "partnership_management"
    MEASUREMENT_ANALYTICS = "measurement_analytics"
    CONTENT_PRODUCTION = "content_production"


@dataclass
class ProjectRequirements:
    """Extracted project requirements from SOW analysis"""
    project_type: ProjectType
    complexity: ProjectComplexity
    duration_weeks: int
    budget_range: str  # "low", "medium", "high", "enterprise"
    client_size: str  # "startup", "mid-market", "enterprise"
    geographic_scope: str  # "local", "regional", "national", "global"
    deliverables_count: int
    events_count: int
    stakeholders_count: int
    special_requirements: List[str]


# ============================================================================
# STAFFING ALLOCATION RULES (HEURISTICS)
# ============================================================================

class StaffingHeuristics:
    """Heuristics-based staffing allocation rules for Octagon"""
    
    # OCTAGON BUSINESS RULES
    OCTAGON_RULES = {
        "creative_director_preallocation": 5.0,  # Creative Director always pre-allocated at 5%
        "executive_oversight_allocation": 5.0,   # L7/L8 leaders allocated for oversight at 5%
        "sponsorship_max_client_fte": 25.0,     # Sponsorship always ≤ 25% FTE per client
        "sponsorship_max_person_fte": 50.0,     # Sponsorship always ≤ 50% FTE per person
        "client_services_min_fte": 75.0,        # Client Services 75–100% FTE
        "client_services_max_fte": 100.0,
        "experiences_hospitality_fte": 100.0,   # Experiences/Hospitality usually near 100% FTE per client
        "creative_min_fte": 5.0,                # Creative usually 5–25% FTE across multiple clients
        "creative_max_fte": 25.0,
        "minimum_pod_size": 4,                  # Minimum pod size of four employees
    }
    
    # Base staffing patterns by project type and complexity
    STAFFING_PATTERNS = {
        ProjectType.SPONSORSHIP_ACTIVATION: {
            ProjectComplexity.SIMPLE: {
                "client_services": 0.4,  # 40% FTE
                "strategy": 0.2,         # 20% FTE
                "planning_creative": 0.2, # 20% FTE
                "integrated_production_experiences": 0.2  # 20% FTE
            },
            ProjectComplexity.MODERATE: {
                "client_services": 0.35,
                "strategy": 0.25,
                "planning_creative": 0.25,
                "integrated_production_experiences": 0.15
            },
            ProjectComplexity.COMPLEX: {
                "client_services": 0.3,
                "strategy": 0.3,
                "planning_creative": 0.25,
                "integrated_production_experiences": 0.15
            },
            ProjectComplexity.ENTERPRISE: {
                "client_services": 0.25,
                "strategy": 0.35,
                "planning_creative": 0.25,
                "integrated_production_experiences": 0.15
            }
        },
        ProjectType.EVENT_MANAGEMENT: {
            ProjectComplexity.SIMPLE: {
                "client_services": 0.3,
                "strategy": 0.1,
                "planning_creative": 0.2,
                "integrated_production_experiences": 0.4
            },
            ProjectComplexity.MODERATE: {
                "client_services": 0.25,
                "strategy": 0.15,
                "planning_creative": 0.25,
                "integrated_production_experiences": 0.35
            },
            ProjectComplexity.COMPLEX: {
                "client_services": 0.2,
                "strategy": 0.2,
                "planning_creative": 0.3,
                "integrated_production_experiences": 0.3
            },
            ProjectComplexity.ENTERPRISE: {
                "client_services": 0.2,
                "strategy": 0.25,
                "planning_creative": 0.3,
                "integrated_production_experiences": 0.25
            }
        },
        ProjectType.HOSPITALITY_PROGRAM: {
            ProjectComplexity.SIMPLE: {
                "client_services": 0.4,
                "strategy": 0.1,
                "planning_creative": 0.1,
                "integrated_production_experiences": 0.4
            },
            ProjectComplexity.MODERATE: {
                "client_services": 0.35,
                "strategy": 0.15,
                "planning_creative": 0.15,
                "integrated_production_experiences": 0.35
            },
            ProjectComplexity.COMPLEX: {
                "client_services": 0.3,
                "strategy": 0.2,
                "planning_creative": 0.2,
                "integrated_production_experiences": 0.3
            },
            ProjectComplexity.ENTERPRISE: {
                "client_services": 0.25,
                "strategy": 0.25,
                "planning_creative": 0.25,
                "integrated_production_experiences": 0.25
            }
        },
        ProjectType.CREATIVE_CAMPAIGN: {
            ProjectComplexity.SIMPLE: {
                "client_services": 0.3,
                "strategy": 0.2,
                "planning_creative": 0.4,
                "integrated_production_experiences": 0.1
            },
            ProjectComplexity.MODERATE: {
                "client_services": 0.25,
                "strategy": 0.25,
                "planning_creative": 0.4,
                "integrated_production_experiences": 0.1
            },
            ProjectComplexity.COMPLEX: {
                "client_services": 0.2,
                "strategy": 0.3,
                "planning_creative": 0.4,
                "integrated_production_experiences": 0.1
            },
            ProjectComplexity.ENTERPRISE: {
                "client_services": 0.2,
                "strategy": 0.35,
                "planning_creative": 0.35,
                "integrated_production_experiences": 0.1
            }
        }
    }
    
    # Role level patterns by project complexity
    ROLE_LEVEL_PATTERNS = {
        ProjectComplexity.SIMPLE: {
            "level_9": 0.0,  # No EVP needed
            "level_8": 0.0,  # No SVP needed
            "level_7": 0.1,  # 10% VP level
            "level_6": 0.2,  # 20% Group Director
            "level_5": 0.3,  # 30% Director
            "level_4": 0.2,  # 20% Senior Manager
            "level_3": 0.2,  # 20% Manager
            "level_2": 0.0,  # No SAE/AE
            "level_1": 0.0   # No entry level
        },
        ProjectComplexity.MODERATE: {
            "level_9": 0.0,
            "level_8": 0.05,
            "level_7": 0.15,
            "level_6": 0.25,
            "level_5": 0.3,
            "level_4": 0.15,
            "level_3": 0.1,
            "level_2": 0.0,
            "level_1": 0.0
        },
        ProjectComplexity.COMPLEX: {
            "level_9": 0.05,
            "level_8": 0.1,
            "level_7": 0.2,
            "level_6": 0.25,
            "level_5": 0.25,
            "level_4": 0.1,
            "level_3": 0.05,
            "level_2": 0.0,
            "level_1": 0.0
        },
        ProjectComplexity.ENTERPRISE: {
            "level_9": 0.1,
            "level_8": 0.15,
            "level_7": 0.25,
            "level_6": 0.25,
            "level_5": 0.2,
            "level_4": 0.05,
            "level_3": 0.0,
            "level_2": 0.0,
            "level_1": 0.0
        }
    }
    
    @classmethod
    def get_department_allocation(cls, project_type: ProjectType, complexity: ProjectComplexity) -> Dict[str, float]:
        """Get recommended department allocation for project type and complexity"""
        if project_type in cls.STAFFING_PATTERNS and complexity in cls.STAFFING_PATTERNS[project_type]:
            return cls.STAFFING_PATTERNS[project_type][complexity]
        
        # Default to sponsorship activation pattern
        return cls.STAFFING_PATTERNS[ProjectType.SPONSORSHIP_ACTIVATION][complexity]
    
    @classmethod
    def get_level_distribution(cls, complexity: ProjectComplexity) -> Dict[str, float]:
        """Get recommended level distribution for project complexity"""
        return cls.ROLE_LEVEL_PATTERNS.get(complexity, cls.ROLE_LEVEL_PATTERNS[ProjectComplexity.MODERATE])
    
    @classmethod
    def apply_octagon_business_rules(cls, 
                                   roles: List[StaffingRole], 
                                   project_type: ProjectType,
                                   complexity: ProjectComplexity) -> List[StaffingRole]:
        """Apply Octagon-specific business rules to staffing roles"""
        
        # Create a copy of roles to modify
        adjusted_roles = []
        
        # Rule 1: Creative Director always pre-allocated at 5%
        creative_director_role = cls._ensure_creative_director_allocation(roles, adjusted_roles)
        
        # Rule 2: L7/L8 leaders allocated for oversight at 5%
        executive_oversight_role = cls._ensure_executive_oversight(roles, adjusted_roles, complexity)
        
        # Rule 3: Sponsorship always ≤ 25% FTE per client (≤ 50% per person)
        cls._apply_sponsorship_limits(roles, adjusted_roles, project_type)
        
        # Rule 4: Client Services 75–100% FTE
        cls._apply_client_services_fte_rules(roles, adjusted_roles)
        
        # Rule 5: Experiences/Hospitality usually near 100% FTE per client
        cls._apply_experiences_hospitality_rules(roles, adjusted_roles, project_type)
        
        # Rule 6: Creative usually 5–25% FTE across multiple clients
        cls._apply_creative_fte_rules(roles, adjusted_roles)
        
        # Rule 7: Minimum pod size of four employees (applied after other rules)
        cls._ensure_minimum_pod_size(adjusted_roles, complexity)
        
        # Final check: Ensure Client Services doesn't exceed 100% FTE
        cls._final_client_services_check(adjusted_roles)
        
        # Add any remaining roles that weren't processed
        for role in roles:
            if role not in adjusted_roles:
                adjusted_roles.append(role)
        
        return adjusted_roles
    
    @classmethod
    def _ensure_creative_director_allocation(cls, 
                                           original_roles: List[StaffingRole], 
                                           adjusted_roles: List[StaffingRole]) -> Optional[StaffingRole]:
        """Ensure Creative Director is allocated at 5%"""
        
        # Check if Creative Director already exists
        existing_creative_director = None
        for role in original_roles:
            if (role.octagon_role == OctagonRole.VP_CREATIVE_DIRECTOR or 
                "creative director" in role.role_title.lower()):
                existing_creative_director = role
                break
        
        if existing_creative_director:
            # Adjust allocation to 5% if not already
            if existing_creative_director.normalized_fte_percentage != cls.OCTAGON_RULES["creative_director_preallocation"]:
                existing_creative_director.allocation_value = cls.OCTAGON_RULES["creative_director_preallocation"]
                existing_creative_director.allocation_type = AllocationType.FTE_PERCENTAGE
            adjusted_roles.append(existing_creative_director)
            return existing_creative_director
        else:
            # Create new Creative Director role
            creative_director = StaffingRole(
                role_title="Creative Director",
                octagon_department=OctagonDepartment.PLANNING_CREATIVE,
                octagon_role=OctagonRole.VP_CREATIVE_DIRECTOR,
                octagon_level=OctagonLevel.LEVEL_6,
                allocation_type=AllocationType.FTE_PERCENTAGE,
                allocation_value=cls.OCTAGON_RULES["creative_director_preallocation"],
                billability=BillabilityType.BILLABLE,
                primary_responsibilities=["Creative oversight and direction"],
                confidence_score=1.0,  # High confidence for business rule
                extracted_fields=[
                    ExtractedField(
                        field_name="octagon_business_rule",
                        raw_text="Creative Director always pre-allocated at 5% per Octagon business rule",
                        structured_value=cls.OCTAGON_RULES["creative_director_preallocation"],
                        confidence_score=1.0,
                        source_section="Octagon Business Rules",
                        extraction_method="heuristic"
                    )
                ]
            )
            adjusted_roles.append(creative_director)
            return creative_director
    
    @classmethod
    def _ensure_executive_oversight(cls, 
                                  original_roles: List[StaffingRole], 
                                  adjusted_roles: List[StaffingRole],
                                  complexity: ProjectComplexity) -> Optional[StaffingRole]:
        """Ensure L7/L8 leaders allocated for oversight at 5%"""
        
        # Only add executive oversight for Complex or Enterprise projects
        if complexity not in [ProjectComplexity.COMPLEX, ProjectComplexity.ENTERPRISE]:
            return None
        
        # Check if executive oversight already exists
        existing_executive = None
        for role in original_roles:
            if (role.octagon_level and 
                role.octagon_level.value in [7, 8] and
                (role.octagon_role == OctagonRole.VICE_PRESIDENT or 
                 role.octagon_role == OctagonRole.SENIOR_VICE_PRESIDENT)):
                existing_executive = role
                break
        
        if existing_executive:
            # Adjust allocation to 5% if not already
            if existing_executive.normalized_fte_percentage != cls.OCTAGON_RULES["executive_oversight_allocation"]:
                existing_executive.allocation_value = cls.OCTAGON_RULES["executive_oversight_allocation"]
                existing_executive.allocation_type = AllocationType.FTE_PERCENTAGE
            adjusted_roles.append(existing_executive)
            return existing_executive
        else:
            # Create new executive oversight role
            executive_role = StaffingRole(
                role_title="Vice President - Executive Oversight",
                octagon_department=OctagonDepartment.CLIENT_SERVICES,
                octagon_role=OctagonRole.VICE_PRESIDENT,
                octagon_level=OctagonLevel.LEVEL_7,
                allocation_type=AllocationType.FTE_PERCENTAGE,
                allocation_value=cls.OCTAGON_RULES["executive_oversight_allocation"],
                billability=BillabilityType.BILLABLE,
                primary_responsibilities=["Executive oversight and strategic guidance"],
                confidence_score=1.0,  # High confidence for business rule
                extracted_fields=[
                    ExtractedField(
                        field_name="octagon_business_rule",
                        raw_text="L7/L8 leaders allocated for oversight at 5% per Octagon business rule",
                        structured_value=cls.OCTAGON_RULES["executive_oversight_allocation"],
                        confidence_score=1.0,
                        source_section="Octagon Business Rules",
                        extraction_method="heuristic"
                    )
                ]
            )
            adjusted_roles.append(executive_role)
            return executive_role
    
    @classmethod
    def _apply_sponsorship_limits(cls, 
                                original_roles: List[StaffingRole], 
                                adjusted_roles: List[StaffingRole],
                                project_type: ProjectType):
        """Apply sponsorship FTE limits: ≤ 25% FTE per client (≤ 50% per person)"""
        
        if project_type != ProjectType.SPONSORSHIP_ACTIVATION:
            return
        
        # Calculate total sponsorship FTE per client
        total_sponsorship_fte = 0
        sponsorship_roles = []
        
        for role in original_roles:
            if (role.octagon_department == OctagonDepartment.STRATEGY and
                ("sponsorship" in role.role_title.lower() or 
                 role.octagon_role == OctagonRole.DIRECTOR_SPONSORSHIP_STRATEGY or
                 role.octagon_role == OctagonRole.MANAGER_SPONSORSHIP_STRATEGY)):
                sponsorship_roles.append(role)
                total_sponsorship_fte += role.normalized_fte_percentage or 0
        
        # Apply 25% client limit
        if total_sponsorship_fte > cls.OCTAGON_RULES["sponsorship_max_client_fte"]:
            # Scale down all sponsorship roles proportionally
            scale_factor = cls.OCTAGON_RULES["sponsorship_max_client_fte"] / total_sponsorship_fte
            for role in sponsorship_roles:
                if role.normalized_fte_percentage:
                    new_allocation = role.normalized_fte_percentage * scale_factor
                    role.allocation_value = new_allocation
                    role.allocation_type = AllocationType.FTE_PERCENTAGE
                    role.extracted_fields.append(
                        ExtractedField(
                            field_name="sponsorship_limit_applied",
                            raw_text=f"Adjusted from {role.normalized_fte_percentage:.1f}% to {new_allocation:.1f}% due to 25% client limit",
                            structured_value=new_allocation,
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    )
        
        # Apply 50% person limit (check individual roles)
        for role in sponsorship_roles:
            if (role.normalized_fte_percentage and 
                role.normalized_fte_percentage > cls.OCTAGON_RULES["sponsorship_max_person_fte"]):
                role.allocation_value = cls.OCTAGON_RULES["sponsorship_max_person_fte"]
                role.allocation_type = AllocationType.FTE_PERCENTAGE
                role.extracted_fields.append(
                    ExtractedField(
                        field_name="sponsorship_person_limit_applied",
                        raw_text=f"Adjusted to {cls.OCTAGON_RULES['sponsorship_max_person_fte']}% due to 50% person limit",
                        structured_value=cls.OCTAGON_RULES["sponsorship_max_person_fte"],
                        confidence_score=1.0,
                        source_section="Octagon Business Rules",
                        extraction_method="heuristic"
                    )
                )
    
    @classmethod
    def _apply_client_services_fte_rules(cls, 
                                       original_roles: List[StaffingRole], 
                                       adjusted_roles: List[StaffingRole]):
        """Apply Client Services 75–100% FTE rules"""
        
        client_services_roles = []
        total_client_services_fte = 0
        
        for role in original_roles:
            if role.octagon_department == OctagonDepartment.CLIENT_SERVICES:
                client_services_roles.append(role)
                total_client_services_fte += role.normalized_fte_percentage or 0
        
        # Ensure minimum 75% FTE for Client Services
        if total_client_services_fte < cls.OCTAGON_RULES["client_services_min_fte"]:
            # Scale up to minimum
            scale_factor = cls.OCTAGON_RULES["client_services_min_fte"] / total_client_services_fte if total_client_services_fte > 0 else 1.0
            for role in client_services_roles:
                if role.normalized_fte_percentage:
                    new_allocation = min(role.normalized_fte_percentage * scale_factor, 
                                       cls.OCTAGON_RULES["client_services_max_fte"])
                    role.allocation_value = new_allocation
                    role.allocation_type = AllocationType.FTE_PERCENTAGE
                    role.extracted_fields.append(
                        ExtractedField(
                            field_name="client_services_minimum_applied",
                            raw_text=f"Adjusted to {new_allocation:.1f}% to meet 75% minimum FTE requirement",
                            structured_value=new_allocation,
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    )
        
        # Ensure maximum 100% FTE for Client Services
        elif total_client_services_fte > cls.OCTAGON_RULES["client_services_max_fte"]:
            # Scale down to maximum
            scale_factor = cls.OCTAGON_RULES["client_services_max_fte"] / total_client_services_fte
            for role in client_services_roles:
                if role.normalized_fte_percentage:
                    new_allocation = role.normalized_fte_percentage * scale_factor
                    role.allocation_value = new_allocation
                    role.allocation_type = AllocationType.FTE_PERCENTAGE
                    role.extracted_fields.append(
                        ExtractedField(
                            field_name="client_services_maximum_applied",
                            raw_text=f"Adjusted to {new_allocation:.1f}% to meet 100% maximum FTE requirement",
                            structured_value=new_allocation,
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    )
    
    @classmethod
    def _apply_experiences_hospitality_rules(cls, 
                                           original_roles: List[StaffingRole], 
                                           adjusted_roles: List[StaffingRole],
                                           project_type: ProjectType):
        """Apply Experiences/Hospitality usually near 100% FTE per client"""
        
        if project_type not in [ProjectType.EVENT_MANAGEMENT, ProjectType.HOSPITALITY_PROGRAM]:
            return
        
        experiences_roles = []
        total_experiences_fte = 0
        
        for role in original_roles:
            if role.octagon_department == OctagonDepartment.INTEGRATED_PRODUCTION_EXPERIENCES:
                experiences_roles.append(role)
                total_experiences_fte += role.normalized_fte_percentage or 0
        
        # Ensure near 100% FTE for Experiences/Hospitality
        if total_experiences_fte < cls.OCTAGON_RULES["experiences_hospitality_fte"] * 0.8:  # 80% of 100%
            # Scale up to near 100%
            target_fte = cls.OCTAGON_RULES["experiences_hospitality_fte"]
            scale_factor = target_fte / total_experiences_fte if total_experiences_fte > 0 else 1.0
            for role in experiences_roles:
                if role.normalized_fte_percentage:
                    new_allocation = role.normalized_fte_percentage * scale_factor
                    role.allocation_value = new_allocation
                    role.allocation_type = AllocationType.FTE_PERCENTAGE
                    role.extracted_fields.append(
                        ExtractedField(
                            field_name="experiences_hospitality_target_applied",
                            raw_text=f"Adjusted to {new_allocation:.1f}% to meet ~100% FTE target for experiences/hospitality",
                            structured_value=new_allocation,
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    )
    
    @classmethod
    def _apply_creative_fte_rules(cls, 
                                original_roles: List[StaffingRole], 
                                adjusted_roles: List[StaffingRole]):
        """Apply Creative usually 5–25% FTE across multiple clients"""
        
        creative_roles = []
        total_creative_fte = 0
        
        for role in original_roles:
            if role.octagon_department == OctagonDepartment.PLANNING_CREATIVE:
                creative_roles.append(role)
                total_creative_fte += role.normalized_fte_percentage or 0
        
        # Apply 5-25% FTE range for Creative
        if total_creative_fte < cls.OCTAGON_RULES["creative_min_fte"]:
            # Scale up to minimum
            scale_factor = cls.OCTAGON_RULES["creative_min_fte"] / total_creative_fte if total_creative_fte > 0 else 1.0
            for role in creative_roles:
                if role.normalized_fte_percentage:
                    new_allocation = min(role.normalized_fte_percentage * scale_factor, 
                                       cls.OCTAGON_RULES["creative_max_fte"])
                    role.allocation_value = new_allocation
                    role.allocation_type = AllocationType.FTE_PERCENTAGE
                    role.extracted_fields.append(
                        ExtractedField(
                            field_name="creative_minimum_applied",
                            raw_text=f"Adjusted to {new_allocation:.1f}% to meet 5% minimum FTE requirement",
                            structured_value=new_allocation,
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    )
        
        elif total_creative_fte > cls.OCTAGON_RULES["creative_max_fte"]:
            # Scale down to maximum
            scale_factor = cls.OCTAGON_RULES["creative_max_fte"] / total_creative_fte
            for role in creative_roles:
                if role.normalized_fte_percentage:
                    new_allocation = role.normalized_fte_percentage * scale_factor
                    role.allocation_value = new_allocation
                    role.allocation_type = AllocationType.FTE_PERCENTAGE
                    role.extracted_fields.append(
                        ExtractedField(
                            field_name="creative_maximum_applied",
                            raw_text=f"Adjusted to {new_allocation:.1f}% to meet 25% maximum FTE requirement",
                            structured_value=new_allocation,
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    )
    
    @classmethod
    def _ensure_minimum_pod_size(cls, 
                               adjusted_roles: List[StaffingRole], 
                               complexity: ProjectComplexity):
        """Ensure minimum pod size of four employees"""
        
        current_pod_size = len(adjusted_roles)
        minimum_size = cls.OCTAGON_RULES["minimum_pod_size"]
        
        if current_pod_size < minimum_size:
            # Add additional roles to meet minimum pod size
            roles_to_add = minimum_size - current_pod_size
            
            # Add Account Manager if not present
            has_account_manager = any(
                role.octagon_role == OctagonRole.ACCOUNT_MANAGER 
                for role in adjusted_roles
            )
            
            if not has_account_manager and roles_to_add > 0:
                account_manager = StaffingRole(
                    role_title="Account Manager",
                    octagon_department=OctagonDepartment.CLIENT_SERVICES,
                    octagon_role=OctagonRole.ACCOUNT_MANAGER,
                    octagon_level=OctagonLevel.LEVEL_3,
                    allocation_type=AllocationType.FTE_PERCENTAGE,
                    allocation_value=25.0,  # Default allocation
                    billability=BillabilityType.BILLABLE,
                    primary_responsibilities=["Account management and client coordination"],
                    confidence_score=0.8,
                    extracted_fields=[
                        ExtractedField(
                            field_name="minimum_pod_size_rule",
                            raw_text="Added to meet minimum pod size of 4 employees",
                            structured_value="Account Manager",
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    ]
                )
                adjusted_roles.append(account_manager)
                roles_to_add -= 1
            
            # Add Senior Account Executive if not present and still need more
            has_sae = any(
                role.octagon_role == OctagonRole.SR_ACCOUNT_EXECUTIVE 
                for role in adjusted_roles
            )
            
            if not has_sae and roles_to_add > 0:
                sae = StaffingRole(
                    role_title="Senior Account Executive",
                    octagon_department=OctagonDepartment.CLIENT_SERVICES,
                    octagon_role=OctagonRole.SR_ACCOUNT_EXECUTIVE,
                    octagon_level=OctagonLevel.LEVEL_2,
                    allocation_type=AllocationType.FTE_PERCENTAGE,
                    allocation_value=20.0,  # Default allocation
                    billability=BillabilityType.BILLABLE,
                    primary_responsibilities=["Account coordination and project support"],
                    confidence_score=0.8,
                    extracted_fields=[
                        ExtractedField(
                            field_name="minimum_pod_size_rule",
                            raw_text="Added to meet minimum pod size of 4 employees",
                            structured_value="Senior Account Executive",
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    ]
                )
                adjusted_roles.append(sae)
                roles_to_add -= 1
            
            # Add Account Executive if still need more
            if roles_to_add > 0:
                ae = StaffingRole(
                    role_title="Account Executive",
                    octagon_department=OctagonDepartment.CLIENT_SERVICES,
                    octagon_role=OctagonRole.ACCOUNT_EXECUTIVE,
                    octagon_level=OctagonLevel.LEVEL_1,
                    allocation_type=AllocationType.FTE_PERCENTAGE,
                    allocation_value=15.0,  # Default allocation
                    billability=BillabilityType.BILLABLE,
                    primary_responsibilities=["Project coordination and administrative support"],
                    confidence_score=0.8,
                    extracted_fields=[
                        ExtractedField(
                            field_name="minimum_pod_size_rule",
                            raw_text="Added to meet minimum pod size of 4 employees",
                            structured_value="Account Executive",
                            confidence_score=1.0,
                            source_section="Octagon Business Rules",
                            extraction_method="heuristic"
                        )
                    ]
                )
                adjusted_roles.append(ae)
    
    @classmethod
    def _final_client_services_check(cls, adjusted_roles: List[StaffingRole]):
        """Final check to ensure Client Services doesn't exceed 100% FTE"""
        
        client_services_roles = []
        total_client_services_fte = 0
        
        for role in adjusted_roles:
            if role.octagon_department == OctagonDepartment.CLIENT_SERVICES:
                client_services_roles.append(role)
                total_client_services_fte += role.normalized_fte_percentage or 0
        
        # If Client Services exceeds 100%, scale down proportionally
        if total_client_services_fte > cls.OCTAGON_RULES["client_services_max_fte"]:
            scale_factor = cls.OCTAGON_RULES["client_services_max_fte"] / total_client_services_fte
            for role in client_services_roles:
                if role.normalized_fte_percentage:
                    new_allocation = role.normalized_fte_percentage * scale_factor
                    role.allocation_value = new_allocation
                    role.allocation_type = AllocationType.FTE_PERCENTAGE
                    role.extracted_fields.append(
                        ExtractedField(
                            field_name="final_client_services_adjustment",
                            raw_text=f"Final adjustment to {new_allocation:.1f}% to meet 100% maximum FTE requirement",
                            structured_value=new_allocation,
                            confidence_score=1.0,
                            source_section="Octagon Business Rules - Final Check",
                            extraction_method="heuristic"
                        )
                    )


# ============================================================================
# SOW ANALYZER
# ============================================================================

class SOWAnalyzer:
    """Analyzes SOW content to extract project requirements"""
    
    def __init__(self):
        self.normalizer = StaffingPlanNormalizer()
    
    def analyze_sow_content(self, sow_text: str, project_info: ProjectInfo) -> ProjectRequirements:
        """Analyze SOW text to extract project requirements"""
        
        # Determine project type
        project_type = self._determine_project_type(sow_text)
        
        # Determine complexity
        complexity = self._determine_complexity(sow_text, project_info)
        
        # Extract other requirements
        duration_weeks = project_info.duration_weeks or self._extract_duration(sow_text)
        budget_range = self._extract_budget_range(sow_text)
        client_size = self._determine_client_size(sow_text, project_info)
        geographic_scope = self._determine_geographic_scope(sow_text)
        deliverables_count = self._count_deliverables(sow_text)
        events_count = self._count_events(sow_text)
        stakeholders_count = self._count_stakeholders(sow_text)
        special_requirements = self._extract_special_requirements(sow_text)
        
        return ProjectRequirements(
            project_type=project_type,
            complexity=complexity,
            duration_weeks=duration_weeks or 26,  # Default to 6 months
            budget_range=budget_range,
            client_size=client_size,
            geographic_scope=geographic_scope,
            deliverables_count=deliverables_count,
            events_count=events_count,
            stakeholders_count=stakeholders_count,
            special_requirements=special_requirements
        )
    
    def _determine_project_type(self, text: str) -> ProjectType:
        """Determine project type from SOW content"""
        text_lower = text.lower()
        
        # Sponsorship activation keywords
        if any(keyword in text_lower for keyword in ['sponsorship', 'activation', 'rights', 'partnership']):
            return ProjectType.SPONSORSHIP_ACTIVATION
        
        # Event management keywords
        if any(keyword in text_lower for keyword in ['event', 'hospitality', 'guest', 'venue', 'ticketing']):
            return ProjectType.EVENT_MANAGEMENT
        
        # Hospitality program keywords
        if any(keyword in text_lower for keyword in ['hospitality', 'guest management', 'catering', 'transportation']):
            return ProjectType.HOSPITALITY_PROGRAM
        
        # Creative campaign keywords
        if any(keyword in text_lower for keyword in ['creative', 'campaign', 'design', 'content', 'brand']):
            return ProjectType.CREATIVE_CAMPAIGN
        
        # Strategic planning keywords
        if any(keyword in text_lower for keyword in ['strategy', 'planning', 'research', 'analysis', 'recommendation']):
            return ProjectType.STRATEGIC_PLANNING
        
        # Measurement analytics keywords
        if any(keyword in text_lower for keyword in ['measurement', 'analytics', 'roi', 'metrics', 'reporting']):
            return ProjectType.MEASUREMENT_ANALYTICS
        
        # Content production keywords
        if any(keyword in text_lower for keyword in ['production', 'video', 'photography', 'content creation']):
            return ProjectType.CONTENT_PRODUCTION
        
        # Default to sponsorship activation
        return ProjectType.SPONSORSHIP_ACTIVATION
    
    def _determine_complexity(self, text: str, project_info: ProjectInfo) -> ProjectComplexity:
        """Determine project complexity from SOW content"""
        complexity_score = 0
        
        # Duration factor
        duration_weeks = project_info.duration_weeks or 26
        if duration_weeks >= 52:
            complexity_score += 3
        elif duration_weeks >= 26:
            complexity_score += 2
        else:
            complexity_score += 1
        
        # Budget factor (based on text indicators)
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ['million', 'multi-million', 'enterprise']):
            complexity_score += 3
        elif any(keyword in text_lower for keyword in ['hundred thousand', 'significant budget']):
            complexity_score += 2
        else:
            complexity_score += 1
        
        # Geographic scope factor
        if any(keyword in text_lower for keyword in ['global', 'international', 'worldwide']):
            complexity_score += 3
        elif any(keyword in text_lower for keyword in ['national', 'multi-market']):
            complexity_score += 2
        else:
            complexity_score += 1
        
        # Stakeholder complexity
        if any(keyword in text_lower for keyword in ['multiple stakeholders', 'cross-functional', 'executive']):
            complexity_score += 2
        
        # Event complexity
        event_count = self._count_events(text)
        if event_count >= 5:
            complexity_score += 3
        elif event_count >= 3:
            complexity_score += 2
        elif event_count >= 1:
            complexity_score += 1
        
        # Map score to complexity
        if complexity_score >= 12:
            return ProjectComplexity.ENTERPRISE
        elif complexity_score >= 9:
            return ProjectComplexity.COMPLEX
        elif complexity_score >= 6:
            return ProjectComplexity.MODERATE
        else:
            return ProjectComplexity.SIMPLE
    
    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract project duration in weeks"""
        # Look for duration patterns
        duration_patterns = [
            r'(\d+)\s*(?:weeks?|months?)',
            r'(?:duration|term|period)[:\s]*(\d+)\s*(?:weeks?|months?)',
            r'(\d+)\s*(?:week|month)\s*(?:project|program|engagement)',
        ]
        
        for pattern in duration_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                duration = int(matches[0])
                # Convert months to weeks if needed
                if 'month' in pattern.lower():
                    duration *= 4
                return duration
        
        return None
    
    def _extract_budget_range(self, text: str) -> str:
        """Extract budget range from text"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['million', 'multi-million', 'enterprise']):
            return "enterprise"
        elif any(keyword in text_lower for keyword in ['hundred thousand', 'significant', 'substantial']):
            return "high"
        elif any(keyword in text_lower for keyword in ['thousand', 'moderate', 'standard']):
            return "medium"
        else:
            return "low"
    
    def _determine_client_size(self, text: str, project_info: ProjectInfo) -> str:
        """Determine client size from SOW content"""
        client_name = project_info.client_name or ""
        text_lower = text.lower()
        
        # Enterprise indicators
        if any(keyword in text_lower for keyword in ['fortune 500', 'global', 'international', 'enterprise']):
            return "enterprise"
        
        # Known enterprise clients (you can expand this list)
        enterprise_clients = ['company 1', 'company 2', 'company 3', 'company 4']
        if any(client in client_name.lower() for client in enterprise_clients):
            return "enterprise"
        
        # Mid-market indicators
        if any(keyword in text_lower for keyword in ['regional', 'multi-market', 'established']):
            return "mid-market"
        
        return "startup"
    
    def _determine_geographic_scope(self, text: str) -> str:
        """Determine geographic scope from text"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['global', 'international', 'worldwide', 'multi-country']):
            return "global"
        elif any(keyword in text_lower for keyword in ['national', 'country-wide', 'multi-market']):
            return "national"
        elif any(keyword in text_lower for keyword in ['regional', 'multi-city', 'state-wide']):
            return "regional"
        else:
            return "local"
    
    def _count_deliverables(self, text: str) -> int:
        """Count number of deliverables mentioned"""
        deliverable_patterns = [
            r'deliverable[s]?[:\-]',
            r'provide[s]?[:\-]',
            r'develop[s]?[:\-]',
            r'create[s]?[:\-]',
            r'produce[s]?[:\-]',
        ]
        
        count = 0
        for pattern in deliverable_patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        
        return max(count, 1)  # At least 1 deliverable
    
    def _count_events(self, text: str) -> int:
        """Count number of events mentioned"""
        event_patterns = [
            r'event[s]?[:\-]',
            r'activation[s]?[:\-]',
            r'program[s]?[:\-]',
            r'campaign[s]?[:\-]',
        ]
        
        count = 0
        for pattern in event_patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        
        return count
    
    def _count_stakeholders(self, text: str) -> int:
        """Count number of stakeholders mentioned"""
        stakeholder_patterns = [
            r'stakeholder[s]?',
            r'client[s]?',
            r'partner[s]?',
            r'team[s]?',
            r'department[s]?',
        ]
        
        count = 0
        for pattern in stakeholder_patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        
        return max(count, 1)  # At least 1 stakeholder
    
    def _extract_special_requirements(self, text: str) -> List[str]:
        """Extract special requirements from text"""
        special_keywords = [
            'compliance', 'regulatory', 'legal', 'security', 'confidential',
            'international', 'multi-language', 'accessibility', 'sustainability',
            'diversity', 'inclusion', 'crisis management', 'risk management'
        ]
        
        requirements = []
        text_lower = text.lower()
        
        for keyword in special_keywords:
            if keyword in text_lower:
                requirements.append(keyword.replace('_', ' ').title())
        
        return requirements


# ============================================================================
# AI RECOMMENDATION ENGINE
# ============================================================================

class AIStaffingRecommendationEngine:
    """AI-powered staffing recommendation engine"""
    
    def __init__(self):
        self.normalizer = StaffingPlanNormalizer()
    
    def generate_ai_recommendations(self, 
                                  project_requirements: ProjectRequirements,
                                  project_info: ProjectInfo,
                                  sow_text: str) -> Dict[str, Any]:
        """Generate AI-powered staffing recommendations"""
        
        # This would integrate with your Azure OpenAI service
        # For now, we'll create a structured prompt and return mock recommendations
        
        recommendations = {
            "ai_analysis": {
                "project_assessment": self._assess_project_ai(project_requirements, sow_text),
                "role_recommendations": self._generate_role_recommendations_ai(project_requirements),
                "allocation_suggestions": self._generate_allocation_suggestions_ai(project_requirements),
                "risk_factors": self._identify_risk_factors_ai(project_requirements, sow_text),
                "success_factors": self._identify_success_factors_ai(project_requirements)
            },
            "confidence_scores": {
                "overall_confidence": 0.85,
                "role_mapping_confidence": 0.90,
                "allocation_confidence": 0.80,
                "complexity_assessment_confidence": 0.85
            }
        }
        
        return recommendations
    
    def _assess_project_ai(self, requirements: ProjectRequirements, sow_text: str) -> Dict[str, Any]:
        """AI assessment of project requirements"""
        return {
            "complexity_justification": f"Project classified as {requirements.complexity.value} based on {requirements.duration_weeks}-week duration, {requirements.budget_range} budget, and {requirements.geographic_scope} scope",
            "key_challenges": self._identify_key_challenges(requirements),
            "resource_requirements": self._assess_resource_requirements(requirements),
            "timeline_considerations": self._assess_timeline_considerations(requirements)
        }
    
    def _generate_role_recommendations_ai(self, requirements: ProjectRequirements) -> List[Dict[str, Any]]:
        """Generate AI-powered role recommendations"""
        recommendations = []
        
        # Base role recommendations by project type
        if requirements.project_type == ProjectType.SPONSORSHIP_ACTIVATION:
            recommendations.extend([
                {
                    "role": "Account Director",
                    "department": "CLIENT_SERVICES",
                    "level": 5,
                    "rationale": "Lead client relationship and program oversight",
                    "allocation_min": 25.0,
                    "allocation_max": 40.0
                },
                {
                    "role": "Strategy Director",
                    "department": "STRATEGY", 
                    "level": 5,
                    "rationale": "Strategic planning and sponsorship activation",
                    "allocation_min": 20.0,
                    "allocation_max": 35.0
                }
            ])
        elif requirements.project_type == ProjectType.EVENT_MANAGEMENT:
            recommendations.extend([
                {
                    "role": "Account Manager",
                    "department": "CLIENT_SERVICES",
                    "level": 3,
                    "rationale": "Day-to-day client management",
                    "allocation_min": 30.0,
                    "allocation_max": 50.0
                },
                {
                    "role": "Event Manager",
                    "department": "INTEGRATED_PRODUCTION_EXPERIENCES",
                    "level": 3,
                    "rationale": "Event execution and logistics",
                    "allocation_min": 40.0,
                    "allocation_max": 60.0
                }
            ])
        
        # Adjust based on complexity
        if requirements.complexity == ProjectComplexity.COMPLEX:
            # Add more senior roles
            recommendations.append({
                "role": "Vice President",
                "department": "CLIENT_SERVICES",
                "level": 7,
                "rationale": "Executive oversight for complex project",
                "allocation_min": 10.0,
                "allocation_max": 20.0
            })
        
        return recommendations
    
    def _generate_allocation_suggestions_ai(self, requirements: ProjectRequirements) -> Dict[str, Any]:
        """Generate AI-powered allocation suggestions"""
        return {
            "total_fte_recommended": self._calculate_total_fte(requirements),
            "department_allocations": self._suggest_department_allocations(requirements),
            "level_distribution": self._suggest_level_distribution(requirements),
            "timeline_phases": self._suggest_timeline_phases(requirements)
        }
    
    def _identify_risk_factors_ai(self, requirements: ProjectRequirements, sow_text: str) -> List[str]:
        """Identify potential risk factors"""
        risks = []
        
        if requirements.complexity in [ProjectComplexity.COMPLEX, ProjectComplexity.ENTERPRISE]:
            risks.append("High complexity requires experienced team")
        
        if requirements.duration_weeks > 52:
            risks.append("Long duration may require team continuity planning")
        
        if requirements.geographic_scope == "global":
            risks.append("Global scope requires time zone coordination")
        
        if requirements.events_count > 5:
            risks.append("Multiple events require strong project management")
        
        return risks
    
    def _identify_success_factors_ai(self, requirements: ProjectRequirements) -> List[str]:
        """Identify success factors"""
        factors = []
        
        factors.append(f"Clear {requirements.project_type.value.replace('_', ' ')} focus")
        factors.append(f"Appropriate team size for {requirements.complexity.value} complexity")
        
        if requirements.special_requirements:
            factors.append(f"Specialized expertise for: {', '.join(requirements.special_requirements)}")
        
        return factors
    
    def _identify_key_challenges(self, requirements: ProjectRequirements) -> List[str]:
        """Identify key project challenges"""
        challenges = []
        
        if requirements.events_count > 3:
            challenges.append("Coordinating multiple events")
        
        if requirements.geographic_scope in ["national", "global"]:
            challenges.append("Multi-location coordination")
        
        if requirements.deliverables_count > 10:
            challenges.append("Managing multiple deliverables")
        
        return challenges
    
    def _assess_resource_requirements(self, requirements: ProjectRequirements) -> Dict[str, str]:
        """Assess resource requirements"""
        return {
            "team_size": "Small" if requirements.complexity == ProjectComplexity.SIMPLE else "Medium" if requirements.complexity == ProjectComplexity.MODERATE else "Large",
            "expertise_level": "Senior" if requirements.complexity in [ProjectComplexity.COMPLEX, ProjectComplexity.ENTERPRISE] else "Mid-level",
            "coordination_needs": "High" if requirements.events_count > 3 else "Medium" if requirements.events_count > 1 else "Low"
        }
    
    def _assess_timeline_considerations(self, requirements: ProjectRequirements) -> List[str]:
        """Assess timeline considerations"""
        considerations = []
        
        if requirements.duration_weeks < 13:
            considerations.append("Short timeline requires immediate mobilization")
        elif requirements.duration_weeks > 52:
            considerations.append("Long timeline allows for phased approach")
        
        if requirements.events_count > 1:
            considerations.append("Multiple events require staggered execution")
        
        return considerations
    
    def _calculate_total_fte(self, requirements: ProjectRequirements) -> float:
        """Calculate total FTE recommendation"""
        base_ftes = {
            ProjectComplexity.SIMPLE: 1.0,
            ProjectComplexity.MODERATE: 2.0,
            ProjectComplexity.COMPLEX: 4.0,
            ProjectComplexity.ENTERPRISE: 6.0
        }
        
        base_fte = base_ftes.get(requirements.complexity, 2.0)
        
        # Adjust for project type
        type_multipliers = {
            ProjectType.EVENT_MANAGEMENT: 1.5,
            ProjectType.HOSPITALITY_PROGRAM: 1.3,
            ProjectType.CREATIVE_CAMPAIGN: 1.2,
            ProjectType.SPONSORSHIP_ACTIVATION: 1.0,
            ProjectType.STRATEGIC_PLANNING: 0.8,
            ProjectType.MEASUREMENT_ANALYTICS: 0.7,
            ProjectType.CONTENT_PRODUCTION: 1.1,
            ProjectType.PARTNERSHIP_MANAGEMENT: 1.0
        }
        
        multiplier = type_multipliers.get(requirements.project_type, 1.0)
        
        # Adjust for events count
        if requirements.events_count > 3:
            multiplier *= 1.2
        
        return round(base_fte * multiplier, 1)
    
    def _suggest_department_allocations(self, requirements: ProjectRequirements) -> Dict[str, float]:
        """Suggest department allocations"""
        return StaffingHeuristics.get_department_allocation(requirements.project_type, requirements.complexity)
    
    def _suggest_level_distribution(self, requirements: ProjectRequirements) -> Dict[str, float]:
        """Suggest level distribution"""
        return StaffingHeuristics.get_level_distribution(requirements.complexity)
    
    def _suggest_timeline_phases(self, requirements: ProjectRequirements) -> List[Dict[str, Any]]:
        """Suggest timeline phases"""
        phases = []
        
        if requirements.duration_weeks >= 26:
            phases = [
                {"phase": "Planning", "duration_weeks": 4, "fte_percentage": 0.3},
                {"phase": "Execution", "duration_weeks": requirements.duration_weeks - 8, "fte_percentage": 1.0},
                {"phase": "Wrap-up", "duration_weeks": 4, "fte_percentage": 0.3}
            ]
        else:
            phases = [
                {"phase": "Planning", "duration_weeks": 2, "fte_percentage": 0.5},
                {"phase": "Execution", "duration_weeks": requirements.duration_weeks - 4, "fte_percentage": 1.0},
                {"phase": "Wrap-up", "duration_weeks": 2, "fte_percentage": 0.5}
            ]
        
        return phases


# ============================================================================
# RECOMMENDATION SYNTHESIZER
# ============================================================================

class StaffingRecommendationSynthesizer:
    """Synthesizes AI recommendations with heuristics to create final staffing plan"""
    
    def __init__(self):
        self.sow_analyzer = SOWAnalyzer()
        self.ai_engine = AIStaffingRecommendationEngine()
        self.normalizer = StaffingPlanNormalizer()
    
    def generate_staffing_plan_recommendation(self, 
                                            sow_text: str, 
                                            project_info: ProjectInfo) -> OctagonStaffingPlan:
        """Generate complete staffing plan recommendation"""
        
        # Step 1: Analyze SOW requirements
        project_requirements = self.sow_analyzer.analyze_sow_content(sow_text, project_info)
        
        # Step 2: Get AI recommendations
        ai_recommendations = self.ai_engine.generate_ai_recommendations(project_requirements, project_info, sow_text)
        
        # Step 3: Generate heuristics-based allocations
        heuristics_allocations = StaffingHeuristics.get_department_allocation(
            project_requirements.project_type, 
            project_requirements.complexity
        )
        
        # Step 4: Apply Octagon business rules
        # First generate roles from AI recommendations
        ai_generated_roles = self._generate_synthesized_roles(
            project_requirements,
            ai_recommendations,
            heuristics_allocations,
            ai_recommendations["ai_analysis"]["allocation_suggestions"]["total_fte_recommended"],
            project_info
        )
        
        business_rules_adjusted_roles = StaffingHeuristics.apply_octagon_business_rules(
            ai_generated_roles,
            project_requirements.project_type,
            project_requirements.complexity
        )
        
        # Step 5: Synthesize into final staffing plan
        staffing_plan = self._synthesize_staffing_plan(
            project_requirements,
            ai_recommendations,
            heuristics_allocations,
            project_info,
            sow_text,
            business_rules_adjusted_roles
        )
        
        return staffing_plan
    
    def _synthesize_staffing_plan(self,
                                project_requirements: ProjectRequirements,
                                ai_recommendations: Dict[str, Any],
                                heuristics_allocations: Dict[str, float],
                                project_info: ProjectInfo,
                                sow_text: str,
                                business_rules_adjusted_roles: List[StaffingRole] = None) -> OctagonStaffingPlan:
        """Synthesize final staffing plan from all inputs"""
        
        # Calculate total FTE
        total_fte = ai_recommendations["ai_analysis"]["allocation_suggestions"]["total_fte_recommended"]
        
        # Use business rules adjusted roles if available, otherwise generate from AI recommendations
        if business_rules_adjusted_roles:
            roles = business_rules_adjusted_roles
        else:
            roles = self._generate_synthesized_roles(
                project_requirements,
                ai_recommendations,
                heuristics_allocations,
                total_fte,
                project_info
            )
        
        # Create financial structure
        financial_structure = self._create_financial_structure(project_requirements, total_fte)
        
        # Calculate department allocation
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
            total_fte_percentage=sum(role.normalized_fte_percentage or 0 for role in roles),
            service_line_allocation=department_allocation,
            extraction_confidence=ai_recommendations["confidence_scores"]["overall_confidence"],
            completeness_score=0.95,  # High completeness for AI-generated plans
            source_sow_file="ai_recommendation",
            raw_extraction_data={
                "project_requirements": project_requirements.__dict__,
                "ai_recommendations": ai_recommendations,
                "heuristics_allocations": heuristics_allocations,
                "business_rules_applied": True if business_rules_adjusted_roles else False
            }
        )
    
    def _generate_synthesized_roles(self,
                                  project_requirements: ProjectRequirements,
                                  ai_recommendations: Dict[str, Any],
                                  heuristics_allocations: Dict[str, float],
                                  total_fte: float,
                                  project_info: ProjectInfo) -> List[StaffingRole]:
        """Generate synthesized roles from AI and heuristics"""
        
        roles = []
        ai_role_recommendations = ai_recommendations["ai_analysis"]["role_recommendations"]
        
        for ai_role in ai_role_recommendations:
            # Map AI role to Octagon structure
            octagon_role, octagon_dept, octagon_level = self.normalizer.map_role_to_octagon_structure(ai_role["role"])
            
            if octagon_role and octagon_dept and octagon_level:
                # Calculate allocation based on AI recommendations and heuristics
                dept_allocation_pct = heuristics_allocations.get(octagon_dept.value, 0.25)
                role_allocation_pct = (ai_role["allocation_min"] + ai_role["allocation_max"]) / 2
                
                # Scale to total FTE
                final_allocation = min(role_allocation_pct, dept_allocation_pct * 100)
                
                role = StaffingRole(
                    role_title=ai_role["role"],
                    octagon_department=octagon_dept,
                    octagon_role=octagon_role,
                    octagon_level=octagon_level,
                    allocation_type=AllocationType.FTE_PERCENTAGE,
                    allocation_value=final_allocation,
                    billability=BillabilityType.BILLABLE,
                    project_duration_weeks=project_info.duration_weeks,
                    primary_responsibilities=[ai_role["rationale"]],
                    confidence_score=ai_recommendations["confidence_scores"]["role_mapping_confidence"],
                    extracted_fields=[
                        ExtractedField(
                            field_name="ai_recommendation",
                            raw_text=f"AI recommended {ai_role['role']} with {ai_role['allocation_min']}-{ai_role['allocation_max']}% allocation",
                            structured_value=ai_role["role"],
                            confidence_score=ai_recommendations["confidence_scores"]["role_mapping_confidence"],
                            source_section="AI Recommendation Engine",
                            extraction_method="ai"
                        )
                    ]
                )
                
                roles.append(role)
        
        return roles
    
    def _create_financial_structure(self, 
                                  project_requirements: ProjectRequirements,
                                  total_fte: float) -> FinancialStructure:
        """Create financial structure based on project requirements"""
        
        # Estimate budget based on complexity and duration
        base_hourly_rate = {
            ProjectComplexity.SIMPLE: 150,
            ProjectComplexity.MODERATE: 200,
            ProjectComplexity.COMPLEX: 275,
            ProjectComplexity.ENTERPRISE: 350
        }.get(project_requirements.complexity, 200)
        
        estimated_budget = total_fte * 40 * project_requirements.duration_weeks * base_hourly_rate
        
        return FinancialStructure(
            primary_fee_type=AllocationType.RETAINER,
            total_budget=estimated_budget,
            currency="USD",
            payment_schedule="Monthly",
            labor_costs=estimated_budget * 0.8,  # 80% labor, 20% other
            pass_through_costs=estimated_budget * 0.2  # 20% pass-through costs
        )


# ============================================================================
# MAIN RECOMMENDATION ENGINE
# ============================================================================

class OctagonStaffingRecommendationEngine:
    """Main engine that orchestrates the complete staffing recommendation process"""
    
    def __init__(self):
        self.synthesizer = StaffingRecommendationSynthesizer()
    
    def recommend_staffing_plan(self, sow_text: str, project_info: ProjectInfo) -> OctagonStaffingPlan:
        """Main method to generate staffing plan recommendations"""
        
        print(f"Analyzing SOW for project: {project_info.project_name}")
        print(f"Client: {project_info.client_name}")
        print(f"Duration: {project_info.duration_weeks} weeks")
        
        # Generate recommendation
        staffing_plan = self.synthesizer.generate_staffing_plan_recommendation(sow_text, project_info)
        
        print(f"Generated staffing plan with {len(staffing_plan.roles)} roles")
        print(f"Total FTE: {staffing_plan.total_fte_percentage:.1f}%")
        print(f"Confidence: {staffing_plan.extraction_confidence:.2f}")
        
        return staffing_plan


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def test_recommendation_engine():
    """Test the recommendation engine with sample data"""
    
    # Sample project info
    project_info = ProjectInfo(
        project_name="Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
        client_name="Company 1",
        project_id="SOW-001-2024",
        duration_weeks=52,
        project_type="Sponsorship Hospitality",
        complexity_score=7.0,
        contract_number="1124711 633889"
    )
    
    # Sample SOW text
    sow_text = """
    Project Title: Company 1 Americas 2024-2025 Sponsorship Hospitality Programs
    Client: Company 1
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
    
    # Generate recommendation
    engine = OctagonStaffingRecommendationEngine()
    staffing_plan = engine.recommend_staffing_plan(sow_text, project_info)
    
    print("\n=== STAFFING PLAN RECOMMENDATION ===")
    print(f"Project: {staffing_plan.project_info.project_name}")
    print(f"Total Roles: {len(staffing_plan.roles)}")
    print(f"Total FTE: {staffing_plan.total_fte_percentage:.1f}%")
    print(f"Estimated Budget: ${staffing_plan.financial_structure.total_budget:,.0f}")
    
    print("\n=== ROLE BREAKDOWN ===")
    for role in staffing_plan.roles:
        dept_name = role.octagon_department.value if role.octagon_department else "Unknown"
        level_name = f"Level {role.octagon_level.value}" if role.octagon_level else "Unknown"
        print(f"{role.role_title}: {role.normalized_fte_percentage:.1f}% FTE ({dept_name}, {level_name})")
    
    print("\n=== DEPARTMENT ALLOCATION ===")
    for dept, fte in staffing_plan.service_line_allocation.items():
        print(f"{dept.value}: {fte:.1f}% FTE")
    
    print("\n=== AI ANALYSIS ===")
    if staffing_plan.raw_extraction_data:
        project_reqs = staffing_plan.raw_extraction_data.get("project_requirements", {})
        print(f"Project Type: {project_reqs.get('project_type', 'Unknown')}")
        print(f"Complexity: {project_reqs.get('complexity', 'Unknown')}")
        print(f"Geographic Scope: {project_reqs.get('geographic_scope', 'Unknown')}")
        print(f"Events Count: {project_reqs.get('events_count', 0)}")
        print(f"Deliverables Count: {project_reqs.get('deliverables_count', 0)}")
    
    return staffing_plan


if __name__ == "__main__":
    test_recommendation_engine()
