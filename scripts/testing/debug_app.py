#!/usr/bin/env python3
"""
Debug version of the Streamlit app with more detailed error reporting
"""

import streamlit as st
import asyncio
import os
import sys
import json
import pandas as pd
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Add the services directory to the path
sys.path.append(str(Path(__file__).parent / "services"))

from sow_extraction_service import SOWExtractionService, ExtractionProgress


# Page configuration
st.set_page_config(
    page_title="SOW Processing App - Debug",
    page_icon="🐛",
    layout="wide"
)

# Load environment variables
load_dotenv()

# Initialize session state
if 'extraction_service' not in st.session_state:
    st.session_state.extraction_service = None


def get_extraction_service():
    """Get or create the extraction service"""
    if st.session_state.extraction_service is None:
        # Point to the parent directory where the sows folder is
        service = SOWExtractionService(sows_directory="../sows")
        return service
    return st.session_state.extraction_service


def process_uploaded_file_debug(uploaded_file):
    """Process an uploaded file with detailed debugging"""
    try:
        st.write("🔍 **Debug: Starting file processing**")
        
        # Save uploaded file temporarily
        temp_path = Path("temp") / uploaded_file.name
        temp_path.parent.mkdir(exist_ok=True)
        
        st.write(f"🔍 **Debug: Saving file to {temp_path}**")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.write(f"🔍 **Debug: File saved, size: {temp_path.stat().st_size} bytes**")
        
        # Initialize service if needed
        service = get_extraction_service()
        if st.session_state.extraction_service is None:
            st.write("🔍 **Debug: Initializing service**")
            asyncio.run(service.initialize())
            st.session_state.extraction_service = service
            st.write("🔍 **Debug: Service initialized**")
        
        # Set progress callback
        def progress_callback(progress: ExtractionProgress):
            st.write(f"📊 Progress: {progress.stage} - {progress.message} ({progress.percentage}%)")
        
        service.set_progress_callback(progress_callback)
        
        # Process the file
        st.write("🔍 **Debug: Starting file processing**")
        result = asyncio.run(service.process_single_sow(temp_path))
        
        # Clean up temp file
        temp_path.unlink()
        st.write("🔍 **Debug: Temp file cleaned up**")
        
        return result
        
    except Exception as e:
        st.error(f"❌ **Debug Error: {e}**")
        st.error(f"❌ **Traceback:**")
        st.code(traceback.format_exc())
        return None


def main():
    """Main application"""
    st.title("🐛 SOW Processing App - Debug Mode")
    st.markdown("Debug version with detailed error reporting")
    
    # Environment check
    st.subheader("🔧 Environment Check")
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing environment variables: {', '.join(missing_vars)}")
        return
    else:
        st.success("✅ Environment variables configured")
    
    # File upload
    st.subheader("📤 Upload SOW Document")
    uploaded_file = st.file_uploader(
        "Choose a SOW file",
        type=['pdf', 'docx'],
        help="Upload a PDF or DOCX SOW document"
    )
    
    if uploaded_file is not None:
        st.write(f"📄 **File:** {uploaded_file.name}")
        st.write(f"📊 **Size:** {uploaded_file.size} bytes")
        st.write(f"📋 **Type:** {uploaded_file.type}")
        
        if st.button("🚀 Process SOW (Debug Mode)", type="primary"):
            with st.spinner("Processing SOW..."):
                result = process_uploaded_file_debug(uploaded_file)
            
            if result:
                st.write("🔍 **Debug: Processing completed**")
                st.write(f"✅ **Success:** {result.success}")
                
                if result.success and result.data:
                    st.success("✅ SOW processed successfully!")
                    
                    # Display results
                    st.subheader("📊 Extraction Results")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Basic Information**")
                        st.write(f"**Client:** {result.data.get('client_name', 'N/A')}")
                        st.write(f"**Project:** {result.data.get('project_title', 'N/A')}")
                        st.write(f"**Duration:** {result.data.get('project_length', 'N/A')}")
                    
                    with col2:
                        st.markdown("**Project Details**")
                        st.write(f"**Deliverables:** {len(result.data.get('deliverables', []))} items")
                        st.write(f"**Staffing Plan:** {len(result.data.get('staffing_plan', []))} people")
                        st.write(f"**Processing Time:** {result.processing_time:.2f}s")
                    
                    # Show raw data
                    st.subheader("🔍 Raw Data")
                    st.json(result.data)
                    
                else:
                    st.error("❌ Processing failed")
                    if result.error:
                        st.error(f"**Error:** {result.error}")
            else:
                st.error("❌ No result returned")


if __name__ == "__main__":
    main()
