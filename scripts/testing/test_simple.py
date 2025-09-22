#!/usr/bin/env python3
"""
Simple test to verify the extraction service works
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the services directory to the path
sys.path.append(str(Path(__file__).parent / "services"))

from sow_extraction_service import SOWExtractionService, ExtractionProgress


def progress_callback(progress: ExtractionProgress):
    """Simple progress callback"""
    print(f"  {progress.stage}: {progress.message} ({progress.percentage}%)")


async def test_simple():
    """Simple test of the extraction service"""
    print("🧪 Simple Service Test")
    print("=" * 40)
    
    # Load environment
    load_dotenv()
    
    # Check environment
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    try:
        # Initialize service
        print("1. Initializing service...")
        # Point to the parent directory where the sows folder is
        service = SOWExtractionService(sows_directory="../sows")
        service.set_progress_callback(progress_callback)
        await service.initialize()
        print("✅ Service initialized")
        
        # Check for SOW files
        print("\n2. Checking for SOW files...")
        files = service.get_sow_files()
        print(f"Found {len(files)} SOW files")
        
        if not files:
            print("⚠️  No SOW files found. Please add some PDF or DOCX files to the 'sows' directory")
            return False
        
        # Test with first file
        print(f"\n3. Testing with: {files[0].name}")
        result = await service.process_single_sow(files[0])
        
        if result.success:
            print("✅ Processing successful!")
            print(f"   Client: {result.data.get('client_name', 'N/A')}")
            print(f"   Project: {result.data.get('project_title', 'N/A')}")
            print(f"   Staffing: {len(result.data.get('staffing_plan', []))} people")
            print(f"   Time: {result.processing_time:.2f}s")
            return True
        else:
            print(f"❌ Processing failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_simple())
    if success:
        print("\n✅ Test passed! The service is working correctly.")
    else:
        print("\n❌ Test failed! Check the errors above.")
    sys.exit(0 if success else 1)
