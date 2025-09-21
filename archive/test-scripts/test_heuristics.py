#!/usr/bin/env python3
"""
Standalone test script for the Heuristics Engine
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

# Import the heuristics engine
from app.services.heuristics_engine import HeuristicsEngine, Department

def test_heuristics_engine():
    """Test the heuristics engine with sample SOW roles"""
    
    print("=" * 60)
    print("OCTAGON STAFFING PLAN HEURISTICS ENGINE TEST")
    print("=" * 60)
    
    # Initialize the engine
    engine = HeuristicsEngine()
    
    # Test cases with different SOW scenarios
    test_cases = [
        {
            "name": "Typical Marketing Campaign",
            "roles": ["Account Manager", "Creative Director", "Project Manager", "Strategy Analyst", "VP"]
        },
        {
            "name": "Sponsorship Activation",
            "roles": ["Account Executive", "Sponsorship Strategy Manager", "Producer", "Creative Manager"]
        },
        {
            "name": "Digital Campaign",
            "roles": ["Digital Media Manager", "Social Media Analyst", "UX Designer", "Account Director"]
        },
        {
            "name": "Experiential Event",
            "roles": ["Event Manager", "Production Coordinator", "Creative Director", "Account Manager"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        print(f"Input roles: {test_case['roles']}")
        
        # Generate baseline allocations
        result = engine.generate_baseline_allocations(test_case['roles'])
        
        # Display results
        print(f"\n📊 DEPARTMENTS ALLOCATED:")
        for dept, allocation in result['departments'].items():
            print(f"  {dept.replace('_', ' ').title()}: {allocation['suggested_fte']:.1%} FTE")
            if allocation['detected_roles']:
                print(f"    └─ Roles: {', '.join(allocation['detected_roles'])}")
        
        if result['special_rules']:
            print(f"\n🎯 SPECIAL RULES APPLIED:")
            for rule in result['special_rules']:
                print(f"  {rule['role']}: {rule['fte']:.1%} FTE ({rule['rule']})")
        
        print(f"\n📈 TOTAL ALLOCATION: {result['total_allocated_fte']:.1%} FTE")
        
        # Show notes
        if result['notes']:
            print(f"\n📝 NOTES:")
            for note in result['notes']:
                print(f"  • {note}")
    
    print("\n" + "=" * 60)
    print("HEURISTICS ENGINE TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_heuristics_engine()
