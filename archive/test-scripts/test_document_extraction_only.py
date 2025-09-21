#!/usr/bin/env python3
"""
Test just the document extraction without Azure services
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from app.services.document_intelligence import DocumentIntelligenceService


async def test_extraction_without_llm():
    """Test document extraction without LLM (Azure OpenAI)"""
    
    print("🧪 Testing Document Extraction (No LLM)")
    print("=" * 50)
    
    service = DocumentIntelligenceService()
    
    # Test files
    test_files = [
        "test_files/historical_sow_sample.docx",
        "test_files/new_staffing_sow_sample.docx",
        "sows/company_1_sow_1.docx",
        "sows/company_1_sow_2.pdf"
    ]
    
    for file_path in test_files:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"\n📄 Testing: {file_path.name}")
        print("-" * 30)
        
        try:
            # Read file bytes
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            print(f"📊 File size: {len(file_bytes):,} bytes")
            
            # Test text extraction only
            if file_bytes.startswith(b'%PDF'):
                text = service._extract_pdf_text(file_bytes)
                fmt = "pdf"
            elif file_bytes.startswith(b'PK'):
                text = service._extract_docx_text(file_bytes)
                fmt = "docx"
            else:
                print(f"❌ Unsupported file type")
                continue
                
            print(f"📝 Format: {fmt}")
            print(f"📝 Text length: {len(text):,} characters")
            print(f"📝 Text preview: {text[:150]}...")
            
            # Test deterministic parsing
            deterministic = service._parse_fields_deterministic(text)
            print(f"🔍 Roles detected: {len(deterministic.get('roles_detected', []))}")
            print(f"🔍 Scope bullets: {len(deterministic.get('scope_bullets', []))}")
            print(f"🔍 Deliverables: {len(deterministic.get('deliverables', []))}")
            
            if deterministic.get('roles_detected'):
                print(f"👥 Sample roles: {[r.get('title', '') for r in deterministic['roles_detected'][:3]]}")
            
            # Test creating a mock ProcessedSOW
            mock_processed_sow = {
                "blob_name": file_path.name,
                "company": "Test Company",
                "sow_id": "TEST-001",
                "project_title": "Test Project",
                "full_text": text,
                "sections": ["Scope", "Deliverables"],
                "key_entities": ["Test Company", "Test Project"],
                "deterministic": deterministic,
                "llm": {}  # Empty LLM data for testing
            }
            
            print(f"✅ Extraction successful!")
            print(f"📊 Mock ProcessedSOW created with {len(text):,} characters of text")
            print(f"🔍 Found {len(deterministic.get('roles_detected', []))} roles via regex")
                
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()


async def test_heuristics_engine():
    """Test the heuristics engine with extracted roles"""
    
    print(f"\n🎯 Testing Heuristics Engine")
    print("=" * 50)
    
    try:
        from app.services.heuristics_engine import HeuristicsEngine
        
        engine = HeuristicsEngine()
        
        # Test with sample roles
        test_roles = ["Account Manager", "Creative Director", "Project Manager", "Strategy Analyst"]
        
        print(f"👥 Input roles: {test_roles}")
        
        # Test role mapping
        mapped_roles = engine.map_sow_roles_to_org(test_roles)
        print(f"🗺️  Mapped roles: {[(r.title, r.department.value, r.level) for r in mapped_roles]}")
        
        # Test baseline allocations
        allocations = engine.generate_baseline_allocations(test_roles)
        print(f"📊 Departments: {list(allocations.get('departments', {}).keys())}")
        print(f"📊 Total FTE: {allocations.get('total_allocated_fte', 0):.1%}")
        print(f"📊 Special rules: {len(allocations.get('special_rules', []))}")
        
        print(f"✅ Heuristics engine working!")
        
    except Exception as e:
        print(f"❌ Heuristics engine error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Document Extraction & Heuristics Test Suite")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_extraction_without_llm())
    asyncio.run(test_heuristics_engine())
    
    print(f"\n🎉 Testing complete!")
