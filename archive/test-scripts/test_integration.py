#!/usr/bin/env python3
"""
Test script for the integrated SOW processing with heuristics engine
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

def test_heuristics_integration():
    """Test the heuristics engine integration without Azure dependencies"""
    
    print("=" * 60)
    print("TESTING HEURISTICS ENGINE INTEGRATION")
    print("=" * 60)
    
    try:
        # Import the services
        from app.services.staffing_plan_service import StaffingPlanService
        from app.models.sow import ProcessedSOW
        
        print("✅ Successfully imported staffing plan service")
        
        # Create sample data (simulating what would come from your LLM extraction)
        sample_llm_data = {
            "blob_name": "test_sow.pdf",
            "company": "Test Company",
            "sow_id": "TEST-001",
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
                "notes": "Generated from test SOW"
            }
        }
        
        print("✅ Created sample LLM data")
        
        # Create ProcessedSOW object
        processed_sow = ProcessedSOW(
            sow_id="TEST-001",
            sections=["Scope", "Deliverables"],
            key_entities=["Test Company", "Marketing Campaign"],
            raw_extraction=sample_llm_data
        )
        
        print("✅ Created ProcessedSOW object")
        
        # Test the staffing plan service
        service = StaffingPlanService()
        print("✅ Initialized StaffingPlanService")
        
        # Generate staffing plan
        staffing_plan = service.generate_staffing_plan_from_sow(processed_sow, sample_llm_data)
        
        print("✅ Generated staffing plan")
        
        # Display results
        print(f"\n📊 STAFFING PLAN RESULTS:")
        print(f"SOW ID: {staffing_plan.sow_id}")
        print(f"Confidence: {staffing_plan.confidence}")
        print(f"Number of roles: {len(staffing_plan.roles)}")
        
        print(f"\n📋 SUMMARY:")
        print(staffing_plan.summary)
        
        print(f"\n👥 ROLES:")
        for i, role in enumerate(staffing_plan.roles, 1):
            print(f"  {i}. {role.role}")
            print(f"     Quantity: {role.quantity}")
            print(f"     Allocation: {role.allocation_percent}%")
            print(f"     Notes: {role.notes}")
        
        print(f"\n✅ Integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_heuristics_engine_directly():
    """Test the heuristics engine directly"""
    
    print("\n" + "=" * 60)
    print("TESTING HEURISTICS ENGINE DIRECTLY")
    print("=" * 60)
    
    try:
        from app.services.heuristics_engine import HeuristicsEngine
        
        # Test with sample roles
        test_roles = ["Account Manager", "Creative Director", "Project Manager", "Strategy Analyst"]
        
        engine = HeuristicsEngine()
        result = engine.generate_baseline_allocations(test_roles)
        
        print(f"✅ Heuristics engine working")
        print(f"Departments allocated: {list(result['departments'].keys())}")
        print(f"Total FTE: {result['total_allocated_fte']:.1%}")
        print(f"Special rules: {len(result['special_rules'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Heuristics engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Starting integration tests...\n")
    
    # Test heuristics engine directly
    heuristics_ok = test_heuristics_engine_directly()
    
    # Test full integration
    integration_ok = test_heuristics_integration()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Heuristics Engine: {'✅ PASS' if heuristics_ok else '❌ FAIL'}")
    print(f"Integration: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    
    if heuristics_ok and integration_ok:
        print("\n🎉 All tests passed! Integration is ready.")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
