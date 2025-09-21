#!/usr/bin/env python3
"""
Test script for Streamlit interface
"""

import subprocess
import time
import webbrowser
from pathlib import Path


def test_streamlit_interface():
    """Test the Streamlit interface"""
    
    print("🖥️  Testing Streamlit Interface")
    print("=" * 50)
    
    # Check if streamlit app exists
    streamlit_app = Path("streamlit_app.py")
    if not streamlit_app.exists():
        print(f"❌ Streamlit app not found: {streamlit_app}")
        return
    
    print(f"📄 Found Streamlit app: {streamlit_app}")
    
    # Check if test files exist
    test_files = [
        "test_files/historical_sow_sample.docx",
        "test_files/new_staffing_sow_sample.docx"
    ]
    
    print(f"\n📋 Checking test files:")
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"✅ {test_file}")
        else:
            print(f"❌ {test_file}")
    
    print(f"\n🚀 To test Streamlit interface:")
    print(f"   1. Run: streamlit run streamlit_app.py")
    print(f"   2. Open: http://localhost:8501")
    print(f"   3. Test both workflows:")
    print(f"      - 📚 Historical SOWs tab")
    print(f"      - 🆕 New Staffing Plans tab")
    print(f"   4. Upload test files and verify processing")
    
    print(f"\n💡 Expected workflow:")
    print(f"   📚 Historical SOWs:")
    print(f"      - Upload historical_sow_sample.docx")
    print(f"      - Should extract existing staffing plan")
    print(f"      - Status: completed_historical")
    print(f"   🆕 New Staffing Plans:")
    print(f"      - Upload new_staffing_sow_sample.docx")
    print(f"      - Should generate AI staffing plan")
    print(f"      - Status: completed_new_staffing")


if __name__ == "__main__":
    test_streamlit_interface()
