#!/usr/bin/env python3
"""
Test script for the updated DocumentIntelligenceService
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from app.services.document_intelligence import DocumentIntelligenceService


async def test_document_intelligence():
    """Test the document intelligence service with sample files"""
    
    print("🧪 Testing Document Intelligence Service")
    print("=" * 50)
    
    # Initialize the service
    service = DocumentIntelligenceService()
    
    # Test files from your sows directory
    test_files = [
        "sows/company_1_sow_1.docx",
        "sows/company_1_sow_2.pdf",
        "test_files/historical_sow_sample.docx",
        "test_files/new_staffing_sow_sample.docx"
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
            
            # Test text extraction (without LLM for now)
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
            print(f"📝 Text preview: {text[:200]}...")
            
            # Test deterministic parsing
            deterministic = service._parse_fields_deterministic(text)
            print(f"🔍 Roles detected: {len(deterministic.get('roles_detected', []))}")
            print(f"🔍 Scope bullets: {len(deterministic.get('scope_bullets', []))}")
            print(f"🔍 Deliverables: {len(deterministic.get('deliverables', []))}")
            
            if deterministic.get('roles_detected'):
                print(f"👥 Sample roles: {[r.get('title', '') for r in deterministic['roles_detected'][:3]]}")
                
            print(f"✅ Basic extraction successful")
            
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()


async def test_llm_extraction():
    """Test LLM extraction with a sample file"""
    
    print(f"\n🤖 Testing LLM Extraction")
    print("=" * 50)
    
    # Check if we have environment variables set
    import os
    if not os.getenv('AZURE_OPENAI_ENDPOINT'):
        print("⚠️  Skipping LLM test - Azure OpenAI environment variables not set")
        print("   Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, etc.")
        return
    
    service = DocumentIntelligenceService()
    
    # Use a test file
    test_file = Path("sows/company_1_sow_1.docx")
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
        
    try:
        with open(test_file, 'rb') as f:
            file_bytes = f.read()
            
        text = service._extract_docx_text(file_bytes)
        
        print(f"📄 Testing LLM extraction on: {test_file.name}")
        print(f"📝 Text length: {len(text):,} characters")
        
        # Test LLM extraction
        llm_data = await service._llm_parse_schema(
            blob_name=test_file.name,
            file_format="docx", 
            text=text[:10000]  # Limit for testing
        )
        
        print(f"✅ LLM extraction successful!")
        print(f"🏢 Company: {llm_data.get('company', 'Not detected')}")
        print(f"🆔 SOW ID: {llm_data.get('sow_id', 'Not detected')}")
        print(f"📋 Project Title: {llm_data.get('project_title', 'Not detected')}")
        print(f"👥 Roles: {len(llm_data.get('roles_detected', []))}")
        print(f"📝 Scope bullets: {len(llm_data.get('scope_bullets', []))}")
        
        if llm_data.get('roles_detected'):
            print(f"👥 Sample roles: {[r.get('title', '') for r in llm_data['roles_detected'][:3]]}")
            
    except Exception as e:
        print(f"❌ LLM extraction failed: {e}")
        import traceback
        traceback.print_exc()


async def test_full_extraction():
    """Test the complete extraction process"""
    
    print(f"\n🚀 Testing Full Extraction Process")
    print("=" * 50)
    
    service = DocumentIntelligenceService()
    
    # Use a test file
    test_file = Path("sows/company_1_sow_1.docx")
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
        
    try:
        with open(test_file, 'rb') as f:
            file_bytes = f.read()
            
        print(f"📄 Testing full extraction on: {test_file.name}")
        
        # Test complete extraction
        result = await service.extract_structure(file_bytes, test_file.name)
        
        print(f"✅ Full extraction successful!")
        print(f"📊 Result keys: {list(result.keys())}")
        print(f"🏢 Company: {result.get('company', 'Not detected')}")
        print(f"🆔 SOW ID: {result.get('sow_id', 'Not detected')}")
        print(f"📋 Project Title: {result.get('project_title', 'Not detected')}")
        print(f"📝 Full text length: {len(result.get('full_text', '')):,} characters")
        print(f"🔍 Sections: {len(result.get('sections', []))}")
        print(f"🏷️  Key entities: {len(result.get('key_entities', []))}")
        
        # Check deterministic results
        det = result.get('deterministic', {})
        print(f"🔍 Deterministic roles: {len(det.get('roles_detected', []))}")
        
        # Check LLM results
        llm = result.get('llm', {})
        print(f"🤖 LLM roles: {len(llm.get('roles_detected', []))}")
        
        if llm.get('roles_detected'):
            print(f"👥 LLM roles: {[r.get('title', '') for r in llm['roles_detected'][:3]]}")
            
    except Exception as e:
        print(f"❌ Full extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Document Intelligence Service Test Suite")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_document_intelligence())
    asyncio.run(test_llm_extraction())
    asyncio.run(test_full_extraction())
    
    print(f"\n🎉 Testing complete!")
