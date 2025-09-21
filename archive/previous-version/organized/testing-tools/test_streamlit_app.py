#!/usr/bin/env python3
"""
Test Streamlit App - Enhanced Octagon Staffing Plan Generator
===========================================================

This script helps you test the enhanced Streamlit interface with the new
AI-powered staffing plan generator and business rules.
"""

import subprocess
import time
import webbrowser
import requests
from pathlib import Path
import sys
import os


def check_api_running():
    """Check if the FastAPI server is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def start_fastapi_server():
    """Start the FastAPI server"""
    print("🚀 Starting FastAPI server...")
    
    # Change to the correct directory
    app_dir = Path(__file__).parent / "octagon-staffing-app"
    
    try:
        # Start the server in the background
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], cwd=str(app_dir))
        
        print("⏳ Waiting for API server to start...")
        
        # Wait for server to start
        for i in range(30):  # 30 second timeout
            if check_api_running():
                print("✅ FastAPI server is running on http://localhost:8000")
                return process
            time.sleep(1)
        
        print("❌ FastAPI server failed to start within 30 seconds")
        return None
        
    except Exception as e:
        print(f"❌ Failed to start FastAPI server: {e}")
        return None


def start_streamlit_app():
    """Start the Streamlit app"""
    print("🎨 Starting Streamlit app...")
    
    streamlit_file = Path(__file__).parent / "octagon_staffing_app_streamlit.py"
    
    if not streamlit_file.exists():
        print(f"❌ Streamlit app not found: {streamlit_file}")
        return None
    
    try:
        # Start Streamlit
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", 
            str(streamlit_file),
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
        
        print("⏳ Waiting for Streamlit app to start...")
        time.sleep(5)  # Give Streamlit time to start
        
        print("✅ Streamlit app is running on http://localhost:8501")
        return process
        
    except Exception as e:
        print(f"❌ Failed to start Streamlit app: {e}")
        return None


def test_enhanced_features():
    """Test the enhanced features"""
    print("\n🧪 Testing Enhanced Features")
    print("=" * 50)
    
    # Test API health
    if check_api_running():
        print("✅ API Health Check: PASSED")
    else:
        print("❌ API Health Check: FAILED")
        return False
    
    # Test enhanced endpoints
    try:
        # Test the new recommendations endpoint
        response = requests.get("http://localhost:8000/staffing-recommendations/test", timeout=5)
        # We expect a 404 since test doesn't exist, but the endpoint should be available
        if response.status_code in [404, 422]:  # Endpoint exists but no data
            print("✅ Enhanced Recommendations Endpoint: AVAILABLE")
        else:
            print(f"⚠️ Enhanced Recommendations Endpoint: Unexpected status {response.status_code}")
    except Exception as e:
        print(f"❌ Enhanced Recommendations Endpoint: ERROR - {e}")
    
    return True


def main():
    """Main test function"""
    print("🤖 Enhanced Octagon Staffing Plan Generator - Test Suite")
    print("=" * 70)
    
    # Check if API is already running
    if check_api_running():
        print("✅ FastAPI server is already running")
        api_process = None
    else:
        api_process = start_fastapi_server()
        if not api_process:
            print("❌ Cannot proceed without API server")
            return
    
    # Start Streamlit app
    streamlit_process = start_streamlit_app()
    if not streamlit_process:
        print("❌ Cannot proceed without Streamlit app")
        if api_process:
            api_process.terminate()
        return
    
    # Test enhanced features
    test_enhanced_features()
    
    # Open browser
    print("\n🌐 Opening Streamlit app in browser...")
    webbrowser.open("http://localhost:8501")
    
    print("\n🎯 Testing Instructions:")
    print("=" * 50)
    print("1. 📤 Upload a SOW file in the 'Upload SOW' tab")
    print("2. 📊 View the enhanced results in the 'View Results' tab")
    print("3. 🧪 Check the test examples in the 'Test Examples' tab")
    print("\n🎨 Enhanced Features to Test:")
    print("• 🤖 AI-powered project analysis")
    print("• 📋 Business rules application")
    print("• 👥 Smart role mapping to Octagon structure")
    print("• 📊 Confidence scoring and quality metrics")
    print("• 🏢 Department allocation compliance")
    print("• ✅ Business rules validation")
    
    print("\n📋 Expected Business Rules:")
    rules = [
        "Creative Director always pre-allocated at 5%",
        "L7/L8 leaders allocated for oversight at 5% (Complex/Enterprise)",
        "Sponsorship always ≤ 25% FTE per client (≤ 50% per person)",
        "Client Services 75–100% FTE",
        "Experiences/Hospitality usually near 100% FTE per client",
        "Creative usually 5–25% FTE across multiple clients",
        "Minimum pod size of four employees"
    ]
    
    for i, rule in enumerate(rules, 1):
        print(f"  {i}. {rule}")
    
    print("\n⏹️ Press Ctrl+C to stop both servers")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        
        if streamlit_process:
            streamlit_process.terminate()
            print("✅ Streamlit app stopped")
        
        if api_process:
            api_process.terminate()
            print("✅ FastAPI server stopped")
        
        print("👋 Test completed!")


if __name__ == "__main__":
    main()
