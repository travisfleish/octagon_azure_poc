#!/usr/bin/env python3
"""
Simple test for FastAPI upload endpoint
"""

import asyncio
import httpx
from pathlib import Path


async def test_simple_upload():
    """Test a simple file upload"""
    
    print("🧪 Simple Upload Test")
    print("=" * 30)
    
    base_url = "http://localhost:8080"
    
    # Test with a small file
    test_file = Path("test_files/historical_sow_sample.docx")
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test health first
        try:
            response = await client.get(f"{base_url}/health")
            print(f"🏥 Health: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # Test upload
        try:
            with open(test_file, 'rb') as f:
                files = {"file": (test_file.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                data = {"processing_type": "historical"}
                
                print(f"📤 Uploading {test_file.name}...")
                response = await client.post(f"{base_url}/upload-sow", files=files, data=data)
                
                print(f"📊 Response: {response.status_code}")
                print(f"📝 Content: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Upload successful!")
                    print(f"📋 File ID: {result.get('file_id')}")
                    print(f"📊 Status: {result.get('status')}")
                else:
                    print(f"❌ Upload failed: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_upload())
