#!/usr/bin/env python3
"""
Test API Integration - Verify the enhanced staffing service works with the existing API
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the path
app_dir = Path(__file__).parent / "octagon-staffing-app"
sys.path.append(str(app_dir))

from app.services.enhanced_staffing_service import EnhancedStaffingPlanService
from app.models.sow import ProcessedSOW


async def test_api_integration():
    """Test the enhanced staffing service integration"""
    
    print("🧪 Testing Enhanced Staffing Service Integration")
    print("=" * 60)
    
    # Sample LLM data (what would come from your existing pipeline)
    sample_llm_data = {
        "blob_name": "company_1_sow_1.pdf",
        "company": "Company 1",
        "sow_id": "SOW-001",
        "project_title": "Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
        "format": "pdf",
        "term": {
            "start": "2024-01-01",
            "end": "2024-12-31",
            "months": 12,
            "inferred": False
        },
        "roles_detected": [
            {"title": "Account Director", "canonical": "Account Director"},
            {"title": "Strategy Director", "canonical": "Strategy Director"},
            {"title": "Account Manager", "canonical": "Account Manager"},
            {"title": "Creative Director", "canonical": "Creative Director"}
        ],
        "scope_bullets": [
            "B2B hospitality programming for three Events",
            "Formula 1 – Las Vegas Race (2024)",
            "67th Annual GRAMMY Awards",
            "2025 API Tournament"
        ],
        "deliverables": [
            "High end hospitality programming for up to forty (40) BW guests/hosts",
            "Compliance documents and necessary approvals decks",
            "Program budgets for Hospitality Room, gift premiums, transportation",
            "Third party vendor management",
            "Guest communications",
            "Program recap and reporting"
        ],
        "units": {
            "explicit_hours": [2080, 1560, 1040],
            "fte_pct": [100, 75, 50],
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
    from app.models.sow import SOWProcessingType
    processed_sow = ProcessedSOW(
        blob_name="company_1_sow_1.pdf",
        sow_id="SOW-001",
        company="Company 1",
        project_title="Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
        processing_type=SOWProcessingType.NEW_STAFFING,
        full_text="""
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
        """,
        sections=["Scope of Work", "Deliverables", "Project Staffing Plan"],
        key_entities=["Company 1", "Formula 1", "GRAMMY Awards", "API Tournament"],
        raw_extraction=sample_llm_data
    )
    
    try:
        # Test the enhanced service
        print("🔧 Initializing Enhanced Staffing Service...")
        service = EnhancedStaffingPlanService()
        
        print("📊 Generating staffing plan...")
        staffing_plan = service.generate_staffing_plan_from_sow(processed_sow, sample_llm_data)
        
        print("✅ Staffing plan generated successfully!")
        print(f"   • SOW ID: {staffing_plan.sow_id}")
        print(f"   • Confidence: {staffing_plan.confidence:.2f}")
        print(f"   • Roles: {len(staffing_plan.roles)}")
        print(f"   • Total FTE: {sum(role.allocation_percent for role in staffing_plan.roles)}%")
        
        print("\n📋 ROLE BREAKDOWN:")
        for role in staffing_plan.roles:
            print(f"   • {role.role}: {role.allocation_percent}% FTE")
            print(f"     Department: {role.department}")
            print(f"     Level: {role.level}")
            print(f"     Notes: {role.notes}")
            print()
        
        print("🎯 ENHANCED RECOMMENDATIONS:")
        recommendations = service.get_staffing_recommendations(processed_sow)
        
        print(f"   • Business Rules Applied: {recommendations['business_rules_applied']}")
        print(f"   • AI Augmented: {recommendations['ai_augmented']}")
        print(f"   • Status: {recommendations['status']}")
        print(f"   • Confidence: {recommendations['confidence']:.2f}")
        print(f"   • Total FTE: {recommendations['total_fte']:.1f}")
        print(f"   • Role Count: {recommendations['role_count']}")
        print(f"   • Departments: {', '.join(recommendations['departments_involved'])}")
        
        print("\n📝 SUMMARY:")
        print(staffing_plan.summary)
        
        print("\n✅ API Integration Test PASSED!")
        print("The enhanced staffing service is ready for production use.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ API Integration Test FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_api_integration())
    if success:
        print("\n🎉 Integration test completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Integration test failed!")
        sys.exit(1)
