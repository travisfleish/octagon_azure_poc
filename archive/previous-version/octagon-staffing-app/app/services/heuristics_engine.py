"""
Deterministic Heuristics Engine for Octagon Staffing Plan Generation

This module implements the baseline allocation rules and role mapping logic
based on the Octagon organizational structure.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from difflib import SequenceMatcher


class Department(Enum):
    """Octagon departments"""
    CLIENT_SERVICES = "client_services"
    STRATEGY = "strategy"
    PLANNING_CREATIVE = "planning_creative"
    INTEGRATED_PRODUCTION = "integrated_production"


@dataclass
class Role:
    """Individual role definition"""
    title: str
    level: int
    department: Department
    aliases: List[str] = None  # Alternative titles/names
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class OctagonOrgChart:
    """Codified organizational structure for heuristics engine"""
    
    # Complete role hierarchy based on org chart
    ROLES = [
        # Client Services
        Role("Exec Vice President", 9, Department.CLIENT_SERVICES, ["EVP", "Executive VP", "Executive Vice President"]),
        Role("Sr Vice President", 8, Department.CLIENT_SERVICES, ["SVP", "Senior VP", "Senior Vice President"]),
        Role("Vice President", 7, Department.CLIENT_SERVICES, ["VP", "Vice Pres"]),
        Role("Group Director", 6, Department.CLIENT_SERVICES, ["Group Dir", "Group Director"]),
        Role("Account Director", 5, Department.CLIENT_SERVICES, ["Account Dir", "Account Director"]),
        Role("Sr. Account Manager", 4, Department.CLIENT_SERVICES, ["Senior Account Manager", "Sr Account Manager"]),
        Role("Account Manager", 3, Department.CLIENT_SERVICES, ["Account Mgr", "Account Manager"]),
        Role("Sr. Account Executive", 2, Department.CLIENT_SERVICES, ["Senior Account Executive", "Sr Account Executive"]),
        Role("Account Executive", 1, Department.CLIENT_SERVICES, ["Account Exec", "Account Executive"]),
        Role("Account Trainee", 0, Department.CLIENT_SERVICES, ["Trainee", "Account Trainee"]),
        
        # Strategy
        Role("Executive Vice President, Strategy", 9, Department.STRATEGY, ["EVP Strategy", "Strategy EVP"]),
        Role("Senior Vice President", 8, Department.STRATEGY, ["SVP Innovation", "SVP Sponsorship Strategy", "SVP Digital Media", "SVP Social Media"]),
        Role("Vice President", 7, Department.STRATEGY, ["VP Sponsorship Strategy", "VP Innovation", "VP Digital Media", "VP Social Media"]),
        Role("Group Director", 6, Department.STRATEGY, ["Group Dir Sponsorship Strategy", "Group Dir CRM Strategy", "Group Dir Innovation", "Group Dir Digital Media", "Group Dir Social Media"]),
        Role("Director", 5, Department.STRATEGY, ["Director Analytics Developer", "Director UX/UI Innovation", "Director Digital Media", "Director Social Media", "Director Products Analytics", "Director CRM Strategy", "Director Sponsorship Strategy", "Director Experiential Strategist", "Director Sr Full Stack Developer"]),
        Role("Senior Manager", 4, Department.STRATEGY, ["Sr Manager"]),
        Role("Manager", 3, Department.STRATEGY, ["Manager Sponsorship Strategy", "Manager Research", "Manager CRM Strategy", "Manager Digital Copywriter", "Manager Digital Media", "Manager Social Media", "Manager Sponsorship Planner", "Manager Full Stack Developer", "Manager Account Executive CRM"]),
        Role("Planner", 2, Department.STRATEGY, ["Sponsorship Strategy Planner"]),
        Role("Analyst", 2, Department.STRATEGY, ["Digital Media Analyst", "Social Media Analyst"]),
        Role("Analytics Developer", 2, Department.STRATEGY, ["Analytics Dev"]),
        Role("Digital Trainee", 1, Department.STRATEGY, ["Jr Planner"]),
        
        # Planning & Creative
        Role("Executive Vice President, Creative", 9, Department.PLANNING_CREATIVE, ["EVP Creative", "Creative EVP"]),
        Role("Senior Vice President", 8, Department.PLANNING_CREATIVE, ["SVP Concept", "SVP Creative Services"]),
        Role("Vice President", 7, Department.PLANNING_CREATIVE, ["VP Executive Producer", "VP Creative Planner", "VP Creative Director"]),
        Role("Group Director", 6, Department.PLANNING_CREATIVE, ["Group Dir Creative Director", "Group Dir Creative Planner", "Group Dir Design"]),
        Role("Director", 5, Department.PLANNING_CREATIVE, ["ACD Design", "Associate Creative Director", "ACD 3D Design", "Sr Content Editor", "Sr Planner"]),
        Role("Senior Manager", 4, Department.PLANNING_CREATIVE, ["Sr Manager"]),
        Role("Manager", 3, Department.PLANNING_CREATIVE, ["Manager Content Producer", "Manager Content Editor", "Manager Project Manager", "Manager 3D Designer", "Manager Art Director", "Manager Jr"]),
        Role("Producer", 2, Department.PLANNING_CREATIVE, ["Strategist", "Sr Project Coordinator"]),
        Role("Jr. Director", 1, Department.PLANNING_CREATIVE, ["Jr Producer", "Jr Developer"]),
        
        # Integrated Production/Experiences
        Role("Executive Vice President", 9, Department.INTEGRATED_PRODUCTION, ["EVP"]),
        Role("Senior Vice President", 8, Department.INTEGRATED_PRODUCTION, ["SVP"]),
        Role("Vice President", 7, Department.INTEGRATED_PRODUCTION, ["VP"]),
        Role("Group Director", 6, Department.INTEGRATED_PRODUCTION, ["Group Dir"]),
        Role("Account Director", 5, Department.INTEGRATED_PRODUCTION, ["Account Dir"]),
        Role("Sr. Account Manager", 4, Department.INTEGRATED_PRODUCTION, ["Senior Account Manager"]),
        Role("Account Manager", 3, Department.INTEGRATED_PRODUCTION, ["Account Mgr"]),
        Role("Sr. Account Executive", 2, Department.INTEGRATED_PRODUCTION, ["Senior Account Executive"]),
        Role("Account Executive", 1, Department.INTEGRATED_PRODUCTION, ["Account Exec"]),
        Role("Trainee", 0, Department.INTEGRATED_PRODUCTION, ["Trainee"]),
    ]
    
    @classmethod
    def get_role_by_title(cls, title: str) -> Optional[Role]:
        """Find role by title or alias with fuzzy matching"""
        title_lower = title.lower().strip()
        
        # First try exact matches
        for role in cls.ROLES:
            # Check exact title match
            if title_lower == role.title.lower():
                return role
            
            # Check aliases
            for alias in role.aliases:
                if title_lower == alias.lower():
                    return role
        
        # Try fuzzy matching for common variations
        best_match = None
        best_ratio = 0.0
        
        for role in cls.ROLES:
            # Check fuzzy match against title
            ratio = SequenceMatcher(None, title_lower, role.title.lower()).ratio()
            if ratio > best_ratio and ratio > 0.8:  # 80% similarity threshold
                best_ratio = ratio
                best_match = role
            
            # Check fuzzy match against aliases
            for alias in role.aliases:
                ratio = SequenceMatcher(None, title_lower, alias.lower()).ratio()
                if ratio > best_ratio and ratio > 0.8:
                    best_ratio = ratio
                    best_match = role
        
        return best_match
    
    @classmethod
    def get_roles_by_department(cls, department: Department) -> List[Role]:
        """Get all roles for a specific department"""
        return [role for role in cls.ROLES if role.department == department]
    
    @classmethod
    def get_roles_by_level_range(cls, min_level: int, max_level: int) -> List[Role]:
        """Get roles within a level range"""
        return [role for role in cls.ROLES if min_level <= role.level <= max_level]
    
    @classmethod
    def get_l7_l8_leaders(cls) -> List[Role]:
        """Get L7/L8 leadership roles (for 5% oversight rule)"""
        return cls.get_roles_by_level_range(7, 8)
    
    @classmethod
    def map_common_sow_patterns(cls, detected_roles: List[str]) -> List[Role]:
        """Map common SOW role patterns to organizational roles"""
        mapped_roles = []
        
        # Common SOW role patterns and their mappings
        sow_patterns = {
            # Generic patterns
            r".*project\s+manager.*": "Manager",
            r".*account\s+manager.*": "Account Manager", 
            r".*account\s+executive.*": "Account Executive",
            r".*account\s+director.*": "Account Director",
            r".*creative\s+director.*": "Vice President",  # Creative Director maps to VP level
            r".*creative\s+manager.*": "Manager",
            r".*strategy.*": "Manager",  # Generic strategy roles
            r".*planner.*": "Planner",
            r".*analyst.*": "Analyst",
            r".*producer.*": "Producer",
            r".*coordinator.*": "Sr Project Coordinator",
            r".*director.*": "Director",  # Generic director
            r".*manager.*": "Manager",   # Generic manager
            r".*executive.*": "Account Executive",  # Generic executive
            r".*vice\s+president.*": "Vice President",
            r".*president.*": "Senior Vice President",
        }
        
        for role_text in detected_roles:
            role_found = False
            
            # Try pattern matching first
            for pattern, mapped_role in sow_patterns.items():
                if re.search(pattern, role_text, re.IGNORECASE):
                    mapped = cls.get_role_by_title(mapped_role)
                    if mapped and mapped not in mapped_roles:
                        mapped_roles.append(mapped)
                        role_found = True
                        break
            
            # If no pattern match, try direct lookup
            if not role_found:
                mapped = cls.get_role_by_title(role_text)
                if mapped and mapped not in mapped_roles:
                    mapped_roles.append(mapped)
        
        return mapped_roles


class BaselineAllocationRules:
    """Baseline allocation rules for deterministic heuristics"""
    
    # Baseline FTE allocations by department
    BASELINE_ALLOCATIONS = {
        Department.CLIENT_SERVICES: {"min_fte": 0.75, "max_fte": 1.00},
        Department.STRATEGY: {"min_fte": 0.05, "max_fte": 0.25},
        Department.PLANNING_CREATIVE: {"min_fte": 0.05, "max_fte": 0.25},
        Department.INTEGRATED_PRODUCTION: {"min_fte": 0.95, "max_fte": 1.00},
    }
    
    # Special rules
    CREATIVE_DIRECTOR_FTE = 0.05  # Always pre-allocated at 5%
    L7_L8_OVERSIGHT_FTE = 0.05    # L7/L8 leaders for oversight at 5%
    SPONSORSHIP_MAX_FTE_PER_CLIENT = 0.25  # ≤25% FTE per client
    SPONSORSHIP_MAX_FTE_PER_PERSON = 0.50  # ≤50% FTE per person
    
    @classmethod
    def get_baseline_allocation(cls, department: Department) -> Dict[str, float]:
        """Get baseline allocation for a department"""
        return cls.BASELINE_ALLOCATIONS.get(department, {"min_fte": 0.0, "max_fte": 0.25})
    
    @classmethod
    def apply_creative_director_rule(cls) -> Dict[str, any]:
        """Apply creative director 5% rule"""
        creative_roles = OctagonOrgChart.get_roles_by_department(Department.PLANNING_CREATIVE)
        creative_directors = [role for role in creative_roles if "creative director" in role.title.lower()]
        
        if creative_directors:
            return {
                "role": creative_directors[0].title,
                "department": Department.PLANNING_CREATIVE,
                "fte": cls.CREATIVE_DIRECTOR_FTE,
                "rule": "creative_director_baseline"
            }
        return {}
    
    @classmethod
    def apply_l7_l8_oversight_rule(cls) -> List[Dict[str, any]]:
        """Apply L7/L8 oversight rule"""
        l7_l8_roles = OctagonOrgChart.get_l7_l8_leaders()
        
        allocations = []
        for role in l7_l8_roles:
            allocations.append({
                "role": role.title,
                "department": role.department,
                "fte": cls.L7_L8_OVERSIGHT_FTE,
                "rule": "l7_l8_oversight"
            })
        
        return allocations


class HeuristicsEngine:
    """Main heuristics engine for staffing plan generation"""
    
    def __init__(self):
        self.org_chart = OctagonOrgChart()
        self.baseline_rules = BaselineAllocationRules()
    
    def map_sow_roles_to_org(self, detected_roles: List[str]) -> List[Role]:
        """Map roles detected in SOW to organizational structure"""
        # Use the improved pattern-based mapping
        mapped_roles = self.org_chart.map_common_sow_patterns(detected_roles)
        
        # Log any unmapped roles for debugging
        mapped_titles = [role.title for role in mapped_roles]
        for role_title in detected_roles:
            if not any(role_title.lower() in mapped_title.lower() or mapped_title.lower() in role_title.lower() for mapped_title in mapped_titles):
                print(f"Warning: Unmapped role detected: {role_title}")
        
        return mapped_roles
    
    def generate_baseline_allocations(self, detected_roles: List[str]) -> Dict[str, any]:
        """Generate baseline staffing allocations based on detected roles and rules"""
        
        print(f"DEBUG: Input detected_roles: {detected_roles}")
        
        # Map SOW roles to org structure
        mapped_roles = self.map_sow_roles_to_org(detected_roles)
        print(f"DEBUG: Mapped roles: {[(r.title, r.department.value, r.level) for r in mapped_roles]}")
        
        # Initialize allocation structure
        allocations = {
            "departments": {},
            "special_rules": [],
            "total_allocated_fte": 0.0,
            "notes": []
        }
        
        # Apply baseline department allocations
        for department in Department:
            baseline = self.baseline_rules.get_baseline_allocation(department)
            
            # Check if department is needed based on detected roles
            dept_roles = [role for role in mapped_roles if role.department == department]
            if dept_roles:
                allocations["departments"][department.value] = {
                    "min_fte": baseline["min_fte"],
                    "max_fte": baseline["max_fte"],
                    "suggested_fte": (baseline["min_fte"] + baseline["max_fte"]) / 2,
                    "detected_roles": [role.title for role in dept_roles],
                    "rule": "baseline_department_allocation"
                }
                allocations["total_allocated_fte"] += (baseline["min_fte"] + baseline["max_fte"]) / 2
        
        # Apply special rules
        creative_director = self.baseline_rules.apply_creative_director_rule()
        if creative_director:
            allocations["special_rules"].append(creative_director)
            allocations["total_allocated_fte"] += creative_director["fte"]
        
        l7_l8_oversight = self.baseline_rules.apply_l7_l8_oversight_rule()
        for oversight in l7_l8_oversight:
            allocations["special_rules"].append(oversight)
            allocations["total_allocated_fte"] += oversight["fte"]
        
        # Add notes
        allocations["notes"].append("AI DRAFT - Review and adjust based on institutional knowledge")
        allocations["notes"].append(f"Total baseline allocation: {allocations['total_allocated_fte']:.1%}")
        
        return allocations


# Example usage and testing
if __name__ == "__main__":
    # Test the heuristics engine
    engine = HeuristicsEngine()
    
    # Example detected roles from SOW
    test_roles = ["Account Manager", "Creative Director", "VP", "Project Manager"]
    
    # Generate baseline allocations
    result = engine.generate_baseline_allocations(test_roles)
    
    print("Baseline Allocations Generated:")
    print(f"Departments: {result['departments']}")
    print(f"Special Rules: {result['special_rules']}")
    print(f"Total FTE: {result['total_allocated_fte']:.1%}")
    print(f"Notes: {result['notes']}")
