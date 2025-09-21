#!/usr/bin/env python3
"""
Test Azure Storage upload with a small file
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Add the services directory to the path
sys.path.append(str(Path(__file__).parent / "services"))

from sow_extraction_service import SOWExtractionService, ExtractionProgress


def progress_callback(progress: ExtractionProgress):
    """Simple progress callback"""
    print(f"  {progress.stage}: {progress.message} ({progress.percentage}%)")


async def test_upload():
    """Test Azure Storage upload with a small file"""
    print("📤 Testing Azure Storage Upload")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    try:
        # Initialize service
        print("1. Initializing service...")
        service = SOWExtractionService(sows_directory="../sows")
        service.set_progress_callback(progress_callback)
        await service.initialize()
        print("✅ Service initialized")
        
        # Create a small test file
        print("\n2. Creating test file...")
        test_content = "This is a test SOW document for upload testing."
        test_file = Path("test_sow.txt")
        with open(test_file, 'w') as f:
            f.write(test_content)
        print(f"✅ Created test file: {test_file} ({len(test_content)} bytes)")
        
        # Test raw file upload
        print("\n3. Testing raw file upload...")
        try:
            await service.upload_raw_file_to_storage(test_file, "test_sow.txt")
            print("✅ Raw file upload successful")
        except Exception as e:
            print(f"❌ Raw file upload failed: {e}")
            return False
        
        # Test extracted text upload
        print("\n4. Testing extracted text upload...")
        try:
            await service.upload_extracted_text_to_storage("test_sow.txt", test_content)
            print("✅ Extracted text upload successful")
        except Exception as e:
            print(f"❌ Extracted text upload failed: {e}")
            return False
        
        # Test JSON upload
        print("\n5. Testing JSON upload...")
        test_data = {
            "client_name": "Test Client",
            "project_title": "Test Project",
            "scope_summary": "Test scope",
            "deliverables": ["Test deliverable"],
            "exclusions": ["Test exclusion"],
            "staffing_plan": [{"name": "Test Person", "role": "Test Role", "allocation": "100%"}]
        }
        try:
            await service.upload_json_to_storage("test_sow.txt", test_data)
            print("✅ JSON upload successful")
        except Exception as e:
            print(f"❌ JSON upload failed: {e}")
            return False
        
        # Clean up test file
        test_file.unlink()
        print("\n✅ All upload tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_upload())
    if success:
        print("\n✅ Upload test passed! The Streamlit app should work now.")
    else:
        print("\n❌ Upload test failed. Check the errors above.")
    sys.exit(0 if success else 1)
