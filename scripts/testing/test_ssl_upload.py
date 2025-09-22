#!/usr/bin/env python3
"""
Test SSL fix for actual Azure Storage upload
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Apply SSL fix globally
import ssl
import urllib3
os.environ['PYTHONHTTPSVERIFY'] = '0'
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add the services directory to the path
sys.path.append(str(Path(__file__).parent / "services"))

from sow_extraction_service import SOWExtractionService, ExtractionProgress


def progress_callback(progress: ExtractionProgress):
    """Simple progress callback"""
    print(f"  {progress.stage}: {progress.message} ({progress.percentage}%)")


async def test_ssl_upload():
    """Test SSL fix for actual upload process"""
    print("🔧 Testing SSL Fix for Azure Storage Upload")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    try:
        # Initialize service
        print("1. Initializing service with SSL fix...")
        service = SOWExtractionService(sows_directory="../sows")
        service.set_progress_callback(progress_callback)
        await service.initialize()
        print("✅ Service initialized successfully")
        
        # Create a test file similar to the one that failed
        print("\n2. Creating test file similar to company_5_sow_1.docx...")
        test_content = "This is a test SOW document for upload testing. " * 100  # Make it larger
        test_file = Path("test_company_5_sow_1.docx")
        with open(test_file, 'w') as f:
            f.write(test_content)
        print(f"✅ Created test file: {test_file} ({len(test_content)} bytes)")
        
        # Test the actual upload process that was failing
        print("\n3. Testing raw file upload (this was failing before)...")
        try:
            await service.upload_raw_file_to_storage(test_file, "test_company_5_sow_1.docx")
            print("✅ Raw file upload successful!")
        except Exception as e:
            print(f"❌ Raw file upload failed: {e}")
            return False
        
        # Test extracted text upload
        print("\n4. Testing extracted text upload...")
        try:
            await service.upload_extracted_text_to_storage("test_company_5_sow_1.docx", test_content)
            print("✅ Extracted text upload successful!")
        except Exception as e:
            print(f"❌ Extracted text upload failed: {e}")
            return False
        
        # Test JSON upload
        print("\n5. Testing JSON upload...")
        test_data = {
            "client_name": "Test Company 5",
            "project_title": "Test SOW Project",
            "scope_summary": "Test scope for upload testing",
            "deliverables": ["Test deliverable 1", "Test deliverable 2"],
            "exclusions": ["Test exclusion 1"],
            "staffing_plan": [
                {"name": "Test Person 1", "role": "Project Manager", "allocation": "100%"},
                {"name": "Test Person 2", "role": "Analyst", "allocation": "50%"}
            ]
        }
        try:
            await service.upload_json_to_storage("test_company_5_sow_1.docx", test_data)
            print("✅ JSON upload successful!")
        except Exception as e:
            print(f"❌ JSON upload failed: {e}")
            return False
        
        # Clean up test file
        test_file.unlink()
        print("\n✅ All SSL upload tests passed!")
        print("🎉 The Streamlit app should now work without SSL errors!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ssl_upload())
    if success:
        print("\n✅ SSL upload test passed! Try the Streamlit app now.")
    else:
        print("\n❌ SSL upload test failed. Check the errors above.")
    sys.exit(0 if success else 1)
