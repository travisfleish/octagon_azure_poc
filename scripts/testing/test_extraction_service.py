#!/usr/bin/env python3
"""
Test script for SOW Extraction Service
=====================================

Simple test to verify the service works correctly.
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
    """Progress callback for testing"""
    print(f"  {progress.stage}: {progress.message} ({progress.percentage}%)")


async def test_service():
    """Test the extraction service"""
    print("🧪 Testing SOW Extraction Service")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if we have the required environment variables
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set up your .env file with Azure OpenAI credentials")
        return False
    
    try:
        # Initialize service
        print("1. Initializing service...")
        service = SOWExtractionService()
        service.set_progress_callback(progress_callback)
        await service.initialize()
        print("✅ Service initialized successfully")
        
        # Test file discovery
        print("\n2. Testing file discovery...")
        files = service.get_sow_files()
        print(f"✅ Found {len(files)} SOW files")
        
        if files:
            # Test processing a single file
            print(f"\n3. Testing single file processing...")
            print(f"   Processing: {files[0].name}")
            
            result = await service.process_single_sow(files[0])
            
            if result.success:
                print("✅ File processed successfully")
                print(f"   Client: {result.data.get('client_name', 'Unknown')}")
                print(f"   Project: {result.data.get('project_title', 'Unknown')}")
                print(f"   Staffing: {len(result.data.get('staffing_plan', []))} people")
                print(f"   Processing time: {result.processing_time:.2f}s")
            else:
                print(f"❌ File processing failed: {result.error}")
                return False
        else:
            print("⚠️  No SOW files found to test with")
            print("   Please add some PDF or DOCX files to the 'sows' directory")
        
        print("\n✅ Service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_service())
    sys.exit(0 if success else 1)
