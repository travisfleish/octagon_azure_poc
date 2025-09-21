#!/usr/bin/env python3
"""
Test runner for the updated document intelligence service
"""

import subprocess
import sys
from pathlib import Path


def run_test(test_name, test_script):
    """Run a test script"""
    
    print(f"\n🧪 Running {test_name}")
    print("=" * 60)
    
    if not Path(test_script).exists():
        print(f"❌ Test script not found: {test_script}")
        return False
    
    try:
        result = subprocess.run([sys.executable, test_script], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            print(f"✅ {test_name} completed successfully")
            return True
        else:
            print(f"❌ {test_name} failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        return False


def main():
    """Run all tests"""
    
    print("🧪 Document Intelligence Service Test Suite")
    print("=" * 60)
    
    tests = [
        ("Document Intelligence Unit Tests", "test_document_intelligence.py"),
        ("Streamlit Interface Tests", "test_streamlit_interface.py"),
    ]
    
    results = []
    
    for test_name, test_script in tests:
        success = run_test(test_name, test_script)
        results.append((test_name, success))
    
    print(f"\n📊 Test Results Summary")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Set up Azure OpenAI environment variables if needed")
    print(f"   2. Run FastAPI server: cd octagon-staffing-app && uvicorn app.main:app --reload --port 8080")
    print(f"   3. Run FastAPI tests: python test_fastapi_endpoints.py")
    print(f"   4. Run Streamlit app: streamlit run streamlit_app.py")


if __name__ == "__main__":
    main()
