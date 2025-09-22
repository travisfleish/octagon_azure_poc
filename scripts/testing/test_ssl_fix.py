#!/usr/bin/env python3
"""
Test SSL fix for Azure Storage connection
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


async def test_ssl_fix():
    """Test SSL fix for Azure Storage"""
    print("🔧 Testing SSL Fix for Azure Storage")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    try:
        # Initialize service
        print("1. Initializing service with SSL fix...")
        service = SOWExtractionService(sows_directory="../sows")
        service.set_progress_callback(progress_callback)
        await service.initialize()
        print("✅ Service initialized successfully")
        
        # Test Azure Storage connection
        print("\n2. Testing Azure Storage connection...")
        if service.blob_service_client:
            print("✅ Azure Storage client created")
            
            # Try to list containers (this will test the connection)
            try:
                containers = service.blob_service_client.list_containers()
                container_list = []
                async for container in containers:
                    container_list.append(container)
                print(f"✅ Successfully connected to Azure Storage")
                print(f"   Found {len(container_list)} containers")
                for container in container_list:
                    print(f"   - {container.name}")
            except Exception as e:
                print(f"❌ Connection test failed: {e}")
                return False
        else:
            print("⚠️  Azure Storage client not initialized")
            return False
        
        print("\n✅ SSL fix test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ssl_fix())
    if success:
        print("\n✅ SSL fix is working! You can now try the Streamlit app.")
    else:
        print("\n❌ SSL fix failed. Check the errors above.")
    sys.exit(0 if success else 1)
