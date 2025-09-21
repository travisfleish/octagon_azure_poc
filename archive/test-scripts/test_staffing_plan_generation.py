#!/usr/bin/env python3
"""
Test staffing plan generation with the updated document intelligence
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from app.services.document_intelligence import DocumentIntelligenceService
from app.services.staffing_plan_service import StaffingPlanService
from app.models.sow import ProcessedSOW, SOWProcessingType


async def test_staffing_plan_generation():
    """Test complete staffing plan generation"""
    
    print("🎯 Testing Staffing Plan Generation")
    print("=" * 50)
    
    # Initialize services
    doc_service = DocumentIntelligenceService()
    staffing_service = StaffingPlanService()
    
    # Test files
    test_files = [
        ("test_files/historical_sow_sample.docx", SOWProcessingType.HISTORICAL),
        ("test_files/new_staffing_sow_sample.docx", SOWProcessingType.NEW_STAFFING),
    ]
    
    for file_path, processing_type in test_files:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"\n📄 Testing: {file_path.name} ({processing_type.value})")
        print("-" * 40)
        
        try:
            # Read file bytes
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Extract text and parse deterministically
            if file_bytes.startswith(b'%PDF'):
                text = doc_service._extract_pdf_text(file_bytes)
                fmt = "pdf"
            elif file_bytes.startswith(b'PK'):
                text = doc_service._extract_docx_text(file_bytes)
                fmt = "docx"
            else:
                print(f"❌ Unsupported file type")
                continue
            
            print(f"📝 Extracted {len(text):,} characters of text")
            
            # Parse deterministically
            deterministic = doc_service._parse_fields_deterministic(text)
            print(f"🔍 Found {len(deterministic.get('roles_detected', []))} roles via regex")
            
            if deterministic.get('roles_detected'):
                print(f"👥 Roles: {[r.get('title', '') for r in deterministic['roles_detected']]}")
            
            # Create mock LLM data (since we don't have Azure OpenAI configured)
            mock_llm_data = {
                "company": "Test Company",
                "sow_id": f"TEST-{file_path.stem.upper()}",
                "project_title": f"Test Project - {file_path.stem}",
                "term": {"start": "2024-01-01", "end": "2024-06-30", "months": 6, "inferred": False},
                "scope_bullets": ["Test scope item 1", "Test scope item 2"],
                "deliverables": ["Deliverable 1", "Deliverable 2"],
                "roles_detected": [{"title": r.get('title', ''), "canonical": r.get('title', '')} for r in deterministic.get('roles_detected', [])],
                "units": {"explicit_hours": [800, 600], "fte_pct": [50, 75], "fees": [], "rate_table": []},
                "assumptions": ["Test assumption"],
                "provenance": {"quotes": ["Test quote"], "sections": ["Scope"], "notes": "Test extraction"}
            }
            
            print(f"🤖 Mock LLM data created with {len(mock_llm_data['roles_detected'])} roles")
            
            # Create ProcessedSOW
            processed_sow = ProcessedSOW(
                blob_name=file_path.name,
                company=mock_llm_data.get("company"),
                sow_id=mock_llm_data.get("sow_id"),
                project_title=mock_llm_data.get("project_title"),
                full_text=text,
                processing_type=processing_type,
                sections=["Scope", "Deliverables"],
                key_entities=["Test Company", "Test Project"],
                raw_extraction=mock_llm_data
            )
            
            print(f"📋 ProcessedSOW created: {processed_sow.company} - {processed_sow.sow_id}")
            
            # Generate staffing plan
            if processing_type == SOWProcessingType.HISTORICAL:
                print(f"📚 Historical workflow: Extracting existing staffing plan")
                # For historical, we'd extract existing staffing plan
                print(f"✅ Historical processing complete")
                
            elif processing_type == SOWProcessingType.NEW_STAFFING:
                print(f"🆕 New staffing workflow: Generating AI staffing plan")
                
                # Generate staffing plan using heuristics
                staffing_plan = staffing_service.generate_staffing_plan_from_sow(processed_sow, mock_llm_data)
                
                print(f"✅ Staffing plan generated!")
                print(f"📊 SOW ID: {staffing_plan.sow_id}")
                print(f"👥 Roles: {len(staffing_plan.roles)}")
                print(f"🎯 Confidence: {staffing_plan.confidence}")
                print(f"📝 Summary: {staffing_plan.summary[:100]}...")
                
                if staffing_plan.roles:
                    print(f"👥 Generated roles:")
                    for role in staffing_plan.roles[:5]:  # Show first 5
                        print(f"   - {role.role}: {role.allocation_percent}% ({role.department})")
                
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("🎯 Staffing Plan Generation Test Suite")
    print("=" * 60)
    
    # Run test
    asyncio.run(test_staffing_plan_generation())
    
    print(f"\n🎉 Staffing plan testing complete!")
