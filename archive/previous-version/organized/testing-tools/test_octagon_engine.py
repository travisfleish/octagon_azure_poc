#!/usr/bin/env python3
"""
Test Octagon Staffing Recommendation Engine
==========================================

Direct test of the recommendation engine without document intelligence
"""

import asyncio
from datetime import datetime

from octagon_staffing_schema import ProjectInfo
from octagon_staffing_recommendation_engine import OctagonStaffingRecommendationEngine


async def test_recommendation_engine_direct():
    """Test the recommendation engine directly with sample data"""
    
    # Sample project info
    project_info = ProjectInfo(
        project_name="Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
        client_name="Company 1",
        project_id="SOW-001-2024",
        duration_weeks=52,
        project_type="Sponsorship Hospitality",
        complexity_score=7.0,
        contract_number="1124711 633889",
        effective_date=datetime(2024, 10, 1)
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
    
    # Initialize engine
    engine = OctagonStaffingRecommendationEngine()
    
    # Generate recommendation
    print("Generating staffing plan recommendation...")
    staffing_plan = engine.recommend_staffing_plan(sow_text, project_info)
    
    # Display results
    print("\n" + "="*80)
    print("OCTAGON STAFFING PLAN RECOMMENDATION")
    print("="*80)
    
    print(f"\nProject: {staffing_plan.project_info.project_name}")
    print(f"Client: {staffing_plan.project_info.client_name}")
    print(f"Duration: {staffing_plan.project_info.duration_weeks} weeks")
    print(f"Contract: {staffing_plan.project_info.contract_number}")
    
    print(f"\n=== STAFFING RECOMMENDATION ===")
    print(f"Total Roles: {len(staffing_plan.roles)}")
    print(f"Total FTE: {staffing_plan.total_fte_percentage:.1f}%")
    if staffing_plan.financial_structure and staffing_plan.financial_structure.total_budget:
        print(f"Estimated Budget: ${staffing_plan.financial_structure.total_budget:,.0f}")
    
    print(f"\n=== ROLE BREAKDOWN ===")
    for role in staffing_plan.roles:
        dept_name = role.octagon_department.value if role.octagon_department else "Unknown"
        level_name = f"Level {role.octagon_level.value}" if role.octagon_level else "Unknown"
        confidence = role.confidence_score
        hours = role.normalized_hours or 0
        print(f"{role.role_title}:")
        print(f"  - Department: {dept_name}")
        print(f"  - Level: {level_name}")
        print(f"  - Allocation: {role.normalized_fte_percentage:.1f}% FTE ({hours:.0f} hours)")
        print(f"  - Confidence: {confidence:.2f}")
        if role.primary_responsibilities:
            print(f"  - Responsibilities: {', '.join(role.primary_responsibilities)}")
        print()
    
    print(f"=== DEPARTMENT ALLOCATION ===")
    for dept, fte in staffing_plan.service_line_allocation.items():
        print(f"{dept.value}: {fte:.1f}% FTE")
    
    print(f"\n=== QUALITY METRICS ===")
    print(f"Extraction Confidence: {staffing_plan.extraction_confidence:.2f}")
    print(f"Completeness Score: {staffing_plan.completeness_score:.2f}")
    
    print(f"\n=== OCTAGON BUSINESS RULES APPLIED ===")
    if staffing_plan.raw_extraction_data:
        business_rules_applied = staffing_plan.raw_extraction_data.get("business_rules_applied", False)
        print(f"Business Rules Applied: {'✅ Yes' if business_rules_applied else '❌ No'}")
        
        # Check for specific business rule applications
        creative_director_found = any(
            role.role_title.lower() == "creative director" and role.normalized_fte_percentage == 5.0
            for role in staffing_plan.roles
        )
        print(f"Creative Director (5% rule): {'✅ Applied' if creative_director_found else '❌ Not applied'}")
        
        executive_oversight_found = any(
            role.octagon_level and role.octagon_level.value in [7, 8]
            for role in staffing_plan.roles
        )
        print(f"Executive Oversight (L7/L8 5% rule): {'✅ Applied' if executive_oversight_found else '❌ Not applied'}")
        
        minimum_pod_size = len(staffing_plan.roles) >= 4
        print(f"Minimum Pod Size (4 employees): {'✅ Met' if minimum_pod_size else '❌ Not met'}")
        
        # Check department FTE compliance
        client_services_fte = sum(
            role.normalized_fte_percentage or 0 
            for role in staffing_plan.roles 
            if role.octagon_department and role.octagon_department.value == "client_services"
        )
        client_services_compliant = 75.0 <= client_services_fte <= 100.0
        print(f"Client Services FTE (75-100%): {'✅ Compliant' if client_services_compliant else f'❌ {client_services_fte:.1f}%'}")

    print(f"\n=== AI ANALYSIS INSIGHTS ===")
    if staffing_plan.raw_extraction_data:
        project_reqs = staffing_plan.raw_extraction_data.get("project_requirements", {})
        if project_reqs:
            print(f"Project Type: {project_reqs.get('project_type', 'Unknown')}")
            print(f"Complexity: {project_reqs.get('complexity', 'Unknown')}")
            print(f"Geographic Scope: {project_reqs.get('geographic_scope', 'Unknown')}")
            print(f"Events Count: {project_reqs.get('events_count', 0)}")
            print(f"Deliverables Count: {project_reqs.get('deliverables_count', 0)}")
            print(f"Budget Range: {project_reqs.get('budget_range', 'Unknown')}")
            print(f"Client Size: {project_reqs.get('client_size', 'Unknown')}")
            
            special_reqs = project_reqs.get('special_requirements', [])
            if special_reqs:
                print(f"Special Requirements: {', '.join(special_reqs)}")
        
        ai_recs = staffing_plan.raw_extraction_data.get("ai_recommendations", {})
        if ai_recs and "ai_analysis" in ai_recs:
            ai_analysis = ai_recs["ai_analysis"]
            
            if "project_assessment" in ai_analysis:
                assessment = ai_analysis["project_assessment"]
                print(f"\nComplexity Justification: {assessment.get('complexity_justification', 'N/A')}")
                
                challenges = assessment.get('key_challenges', [])
                if challenges:
                    print(f"Key Challenges: {', '.join(challenges)}")
            
            if "risk_factors" in ai_analysis:
                risks = ai_analysis["risk_factors"]
                if risks:
                    print(f"Risk Factors: {', '.join(risks)}")
            
            if "success_factors" in ai_analysis:
                success_factors = ai_analysis["success_factors"]
                if success_factors:
                    print(f"Success Factors: {', '.join(success_factors)}")
    
    print(f"\n=== RECOMMENDATION SUMMARY ===")
    print(f"✅ Successfully generated staffing plan for {project_info.project_name}")
    print(f"✅ Mapped {len(staffing_plan.roles)} roles to Octagon organizational structure")
    print(f"✅ Calculated {staffing_plan.total_fte_percentage:.1f}% total FTE allocation")
    print(f"✅ Estimated budget and financial structure")
    print(f"✅ Provided confidence and quality metrics")
    
    return staffing_plan


if __name__ == "__main__":
    asyncio.run(test_recommendation_engine_direct())
