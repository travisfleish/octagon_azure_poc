#!/usr/bin/env python3
"""
Test script for FastAPI endpoints
"""

import asyncio
import httpx
import json
from pathlib import Path


async def test_fastapi_endpoints():
    """Test the FastAPI endpoints with real file uploads"""
    
    print("🚀 Testing FastAPI Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8080"
    
    # Test files
    test_files = [
        ("sows/company_1_sow_1.docx", "historical"),
        ("sows/company_1_sow_2.pdf", "new_staffing"),
        ("test_files/historical_sow_sample.docx", "historical"),
        ("test_files/new_staffing_sow_sample.docx", "new_staffing")
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # Test health endpoint
        print("🏥 Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Health endpoint working")
            else:
                print(f"❌ Health endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health endpoint error: {e}")
            return
        
        # Test file uploads
        for file_path, processing_type in test_files:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                continue
                
            print(f"\n📄 Testing upload: {file_path.name} ({processing_type})")
            print("-" * 40)
            
            try:
                # Upload file
                with open(file_path, 'rb') as f:
                    # Set correct MIME type based on file extension
                    if file_path.suffix.lower() == '.pdf':
                        mime_type = "application/pdf"
                    elif file_path.suffix.lower() == '.docx':
                        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    else:
                        mime_type = "application/octet-stream"
                    
                    files = {"file": (file_path.name, f, mime_type)}
                    data = {"processing_type": processing_type}
                    
                    response = await client.post(
                        f"{base_url}/upload-sow",
                        files=files,
                        data=data
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    file_id = result.get("file_id")
                    print(f"✅ Upload successful - File ID: {file_id}")
                    print(f"📊 Status: {result.get('status')}")
                    
                    # Poll for processing status
                    await poll_processing_status(client, base_url, file_id)
                    
                else:
                    print(f"❌ Upload failed: {response.status_code}")
                    print(f"📝 Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Upload error: {e}")


async def poll_processing_status(client, base_url, file_id, max_attempts=10):
    """Poll the processing status until complete"""
    
    print(f"⏳ Polling processing status for {file_id}...")
    
    for attempt in range(max_attempts):
        try:
            response = await client.get(f"{base_url}/process-sow/{file_id}")
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                print(f"📊 Status: {status}")
                
                if status in ["completed_historical", "completed_new_staffing"]:
                    print(f"✅ Processing completed!")
                    
                    # Test getting the staffing plan
                    await test_get_staffing_plan(client, base_url, file_id)
                    break
                    
                elif status.startswith("error"):
                    print(f"❌ Processing failed: {status}")
                    break
                    
                else:
                    print(f"⏳ Still processing... (attempt {attempt + 1}/{max_attempts})")
                    await asyncio.sleep(2)
                    
            else:
                print(f"❌ Status check failed: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            break


async def test_get_staffing_plan(client, base_url, file_id):
    """Test getting the staffing plan"""
    
    print(f"📋 Testing staffing plan retrieval...")
    
    try:
        response = await client.get(f"{base_url}/staffing-plan/{file_id}")
        
        if response.status_code == 200:
            plan = response.json()
            print(f"✅ Staffing plan retrieved!")
            print(f"📊 SOW ID: {plan.get('sow_id')}")
            print(f"📝 Summary: {plan.get('summary', '')[:100]}...")
            print(f"👥 Roles: {len(plan.get('roles', []))}")
            print(f"🎯 Confidence: {plan.get('confidence')}")
            
            if plan.get('roles'):
                print(f"👥 Sample roles:")
                for role in plan['roles'][:3]:
                    print(f"   - {role.get('role')}: {role.get('allocation_percent')}% ({role.get('department')})")
                    
        else:
            print(f"❌ Staffing plan retrieval failed: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Staffing plan retrieval error: {e}")


async def test_list_sows(client, base_url):
    """Test listing SOWs"""
    
    print(f"\n📋 Testing SOW listing...")
    
    try:
        response = await client.get(f"{base_url}/sows")
        
        if response.status_code == 200:
            result = response.json()
            sows = result.get("items", [])
            print(f"✅ Found {len(sows)} SOWs")
            
            for sow in sows[:3]:  # Show first 3
                print(f"   - {sow.get('file_name')}: {sow.get('processing_type')} ({sow.get('status')})")
                
        else:
            print(f"❌ SOW listing failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ SOW listing error: {e}")


if __name__ == "__main__":
    print("🚀 FastAPI Endpoints Test Suite")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_fastapi_endpoints())
    
    print(f"\n🎉 FastAPI testing complete!")
    print("\n💡 To run the FastAPI server:")
    print("   cd octagon-staffing-app")
    print("   uvicorn app.main:app --reload --port 8080")
