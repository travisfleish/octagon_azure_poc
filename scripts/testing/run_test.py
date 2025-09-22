#!/usr/bin/env python3
"""
Quick test script to verify the Streamlit app setup
"""

import subprocess
import sys
import os
from pathlib import Path

def test_imports():
    """Test that all imports work"""
    print("🧪 Testing imports...")
    
    try:
        # Test service import
        sys.path.append(str(Path(__file__).parent / "services"))
        from sow_extraction_service import SOWExtractionService, ExtractionProgress
        print("✅ Service imports successful")
        
        # Test Streamlit import
        import streamlit as st
        print("✅ Streamlit import successful")
        
        # Test other imports
        import pandas as pd
        import json
        print("✅ Other imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_environment():
    """Test environment variables"""
    print("\n🔧 Testing environment...")
    
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set up your .env file")
        return False
    else:
        print("✅ Environment variables configured")
        return True

def test_file_structure():
    """Test file structure"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "app.py",
        "services/sow_extraction_service.py",
        "sow_data_extractor_cli.py",
        "test_extraction_service.py",
        "requirements.txt",
        "README.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("✅ All required files present")
        return True

def main():
    """Run all tests"""
    print("🚀 Running Streamlit App Tests")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_imports,
        test_environment
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed! Ready to run the app.")
        print("\n🚀 To run the app:")
        print("   streamlit run app.py")
        print("\n🧪 To test the service:")
        print("   python test_extraction_service.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
