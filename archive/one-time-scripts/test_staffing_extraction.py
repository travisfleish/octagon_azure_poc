#!/usr/bin/env python3
"""
Test Staffing Plan Extraction
=============================

Test the improved staffing plan extraction on previously failed SOWs
"""

import os
import json
import asyncio
from pathlib import Path
from sow_data_extractor import SOWDataExtractor

async def test_staffing_extraction():
    """Test staffing extraction on specific files"""
    
    # Files that previously failed staffing extraction
    failed_files = [
        "company_2_sow_1.pdf",
        "company_2_sow_3.pdf", 
        "company_3_sow_1.docx",
        "company_1_sow_4.pdf",
        "company_1_sow_3.pdf"
    ]
    
    print("🧪 TESTING IMPROVED STAFFING EXTRACTION")
    print("=" * 50)
    
    # Initialize extractor
    extractor = SOWDataExtractor()
    await extractor.initialize()
    
    results = []
    
    for file_name in failed_files:
        print(f"\n📄 Testing: {file_name}")
        
        file_path = Path("sows") / file_name
        if not file_path.exists():
            print(f"  ❌ File not found: {file_path}")
            continue
        
        # Extract text
        text = extractor.extract_text_from_file(file_path)
        if not text:
            print(f"  ❌ Failed to extract text")
            continue
        
        print(f"  📝 Extracted {len(text)} characters")
        
        # Extract structured data
        data = await extractor.extract_sow_data(file_name, text)
        
        # Check staffing plan results
        staffing_plan = data.get("staffing_plan", [])
        print(f"  👥 Staffing Plan: {len(staffing_plan)} people found")
        
        if staffing_plan:
            print("  ✅ SUCCESS! Staffing plan extracted:")
            for i, person in enumerate(staffing_plan[:3], 1):
                name = person.get("name", "N/A")
                role = person.get("role", "N/A")
                allocation = person.get("allocation", "N/A")
                print(f"    {i}. {name} - {role}: {allocation}")
            if len(staffing_plan) > 3:
                print(f"    ... and {len(staffing_plan)-3} more")
        else:
            print("  ❌ No staffing plan found")
            
            # Show some context about what was found
            client = data.get("client_name", "Unknown")
            project = data.get("project_title", "Unknown")
            print(f"    Client: {client}")
            print(f"    Project: {project}")
        
        results.append({
            "file": file_name,
            "staffing_count": len(staffing_plan),
            "success": len(staffing_plan) > 0,
            "data": data
        })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"✅ Successful extractions: {len(successful)}/{len(results)}")
    print(f"❌ Failed extractions: {len(failed)}/{len(results)}")
    
    if successful:
        print(f"\n✅ SUCCESSFUL:")
        for result in successful:
            print(f"  • {result['file']}: {result['staffing_count']} people")
    
    if failed:
        print(f"\n❌ STILL FAILING:")
        for result in failed:
            print(f"  • {result['file']}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_staffing_extraction())
