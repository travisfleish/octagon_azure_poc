#!/usr/bin/env python3
"""
Enhanced Streamlit App - Focus on Homogeneous Data Extraction
===========================================================

This Streamlit app focuses on displaying the structured data extraction
from heterogeneous SOW documents using Azure OpenAI.
"""

import streamlit as st
import pandas as pd
import json
import requests
import time
from datetime import datetime
from typing import Dict, Any
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

# Configure Streamlit page
st.set_page_config(
    page_title="🤖 Octagon SOW Data Extraction", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .extraction-box {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .field-header {
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .field-value {
        background-color: #ffffff;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border: 1px solid #e0e0e0;
        margin: 0.25rem 0;
    }
    .confidence-high {
        color: #27ae60;
        font-weight: bold;
    }
    .confidence-medium {
        color: #f39c12;
        font-weight: bold;
    }
    .confidence-low {
        color: #e74c3c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000"

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def upload_sow_file(file, processing_type: str) -> Dict[str, Any]:
    """Upload SOW file for processing"""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {"processing_type": processing_type}
        
        response = requests.post(f"{API_BASE_URL}/upload-new-sow", files=files, data=data, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Upload failed: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Upload error: {str(e)}"}

def get_processing_status(file_id: str) -> Dict[str, Any]:
    """Get processing status for a SOW"""
    try:
        response = requests.get(f"{API_BASE_URL}/process-sow/{file_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status check failed: {response.status_code}"}
    except Exception as e:
        return {"error": f"Status check error: {str(e)}"}

def get_enhanced_recommendations(sow_id: str) -> Dict[str, Any]:
    """Get enhanced recommendations with business rules"""
    try:
        response = requests.get(f"{API_BASE_URL}/staffing-recommendations/{sow_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get recommendations: {response.status_code}"}
    except Exception as e:
        return {"error": f"Recommendations error: {str(e)}"}

def display_confidence_score(score: float):
    """Display confidence score with appropriate styling"""
    if score >= 0.8:
        st.markdown(f'<span class="confidence-high">🎯 Confidence: {score:.2f} (High)</span>', unsafe_allow_html=True)
    elif score >= 0.6:
        st.markdown(f'<span class="confidence-medium">⚠️ Confidence: {score:.2f} (Medium)</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="confidence-low">❌ Confidence: {score:.2f} (Low)</span>', unsafe_allow_html=True)

def display_extracted_data(extracted_data: Dict[str, Any]):
    """Display the structured data extraction results"""
    
    st.markdown('<div class="extraction-box">', unsafe_allow_html=True)
    st.markdown("### 📊 **Structured Data Extraction Results**")
    
    # Basic Information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="field-header">📄 File Information</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>File:</strong> {extracted_data.get("file_name", "Unknown")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Company:</strong> {extracted_data.get("company", "Unknown")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Project:</strong> {extracted_data.get("project_title", "Unknown")}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="field-header">⏱️ Project Details</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Duration:</strong> {extracted_data.get("duration_weeks", 0)} weeks</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Departments:</strong> {len(extracted_data.get("departments_involved", []))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Deliverables:</strong> {len(extracted_data.get("deliverables", []))}</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="field-header">🎯 Quality Metrics</div>', unsafe_allow_html=True)
        confidence = extracted_data.get("confidence_score", 0.0)
        display_confidence_score(confidence)
        st.markdown(f'<div class="field-value"><strong>Roles Found:</strong> {len(extracted_data.get("roles_mentioned", []))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Extraction Time:</strong> {extracted_data.get("extraction_timestamp", "Unknown")}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Departments Mapping
    st.markdown("### 🏛️ **Octagon Department Mapping**")
    departments = extracted_data.get("departments_involved", [])
    
    if departments:
        dept_mapping = {
            'client_services': 'Client Services (Account Management, Client Relationships)',
            'strategy': 'Strategy (Strategic Planning, Insights, Analytics)',
            'planning_creative': 'Planning & Creative (Creative Development, Brand Work, Campaign Planning)',
            'integrated_production_experiences': 'Integrated Production & Experiences (Events, Hospitality, Activations, Production)'
        }
        
        cols = st.columns(2)
        for i, dept in enumerate(departments):
            col_idx = i % 2
            with cols[col_idx]:
                st.markdown(f'✅ **{dept.replace("_", " ").title()}**')
                st.caption(dept_mapping.get(dept, "Department mapping"))
    else:
        st.warning("No departments identified in the SOW")
    
    # Deliverables
    st.markdown("### 📋 **Extracted Deliverables**")
    deliverables = extracted_data.get("deliverables", [])
    
    if deliverables:
        with st.expander(f"View {len(deliverables)} Deliverables", expanded=False):
            for i, deliverable in enumerate(deliverables, 1):
                st.markdown(f"**{i}.** {deliverable}")
    else:
        st.warning("No deliverables identified in the SOW")
    
    # Roles Mentioned
    st.markdown("### 👥 **Staffing Roles Identified**")
    roles = extracted_data.get("roles_mentioned", [])
    
    if roles:
        with st.expander(f"View {len(roles)} Roles", expanded=False):
            for i, role in enumerate(roles, 1):
                st.markdown(f"**{i}.** {role}")
    else:
        st.warning("No roles identified in the SOW")
    
    # Scope Description
    st.markdown("### 📝 **Project Scope Summary**")
    scope = extracted_data.get("scope_description", "")
    if scope:
        st.info(scope)
    else:
        st.warning("No scope description extracted")
    
    # Budget Information (if available)
    budget_info = extracted_data.get("budget_info", {})
    if budget_info and any(budget_info.values()):
        st.markdown("### 💰 **Budget Information**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if budget_info.get("total_budget"):
                st.metric("Total Budget", f"${budget_info['total_budget']:,.2f}")
        
        with col2:
            if budget_info.get("budget_currency"):
                st.metric("Currency", budget_info["budget_currency"])
        
        with col3:
            if budget_info.get("budget_breakdown"):
                st.metric("Breakdown Items", len(budget_info["budget_breakdown"]))

def display_homogeneous_vs_heterogeneous():
    """Display the concept of homogeneous extraction from heterogeneous sources"""
    
    st.markdown("### 🔄 **Homogeneous Data Extraction Process**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 **Heterogeneous Input**")
        st.markdown("""
        - **Mixed formats**: PDF, DOCX, different layouts
        - **Inconsistent terminology**: Various department names
        - **Different structures**: No standardized fields
        - **Varied detail levels**: Some detailed, some brief
        """)
    
    with col2:
        st.markdown("#### 📊 **Homogeneous Output**")
        st.markdown("""
        - **Standardized fields**: 10 consistent data fields
        - **Mapped departments**: 4 Octagon departments
        - **Structured format**: JSON schema
        - **Quality scoring**: Confidence metrics
        """)
    
    st.markdown("### 🎯 **Standardized Fields Extracted**")
    
    fields_info = [
        ("company", "Client company name"),
        ("project_title", "Project or campaign title"),
        ("duration_weeks", "Project duration in weeks"),
        ("departments_involved", "4 Octagon departments mapped"),
        ("deliverables", "Specific deliverables/outputs"),
        ("roles_mentioned", "Staffing roles identified"),
        ("scope_description", "Project scope summary"),
        ("budget_info", "Financial information (if available)"),
        ("confidence_score", "AI extraction confidence (0.0-1.0)"),
        ("extraction_timestamp", "When extraction was performed")
    ]
    
    cols = st.columns(2)
    for i, (field, description) in enumerate(fields_info):
        col_idx = i % 2
        with cols[col_idx]:
            st.markdown(f"**{field}**: {description}")

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🤖 Octagon SOW Data Extraction</h1>', unsafe_allow_html=True)
    st.markdown("**Transform heterogeneous SOW documents into homogeneous, structured data**")
    
    # Sidebar
    st.sidebar.header("📊 Data Extraction Options")
    
    # Processing type selection
    processing_type = st.sidebar.selectbox(
        "Select Processing Type:",
        ["NEW_STAFFING", "HISTORICAL_STAFFING"],
        help="NEW_STAFFING: Generate new staffing plan\nHISTORICAL_STAFFING: Analyze historical data"
    )
    
    # API health check
    if check_api_health():
        st.sidebar.success("✅ **API Connected** - FastAPI server is running")
    else:
        st.sidebar.warning("⚠️ **API Not Connected** - FastAPI server may not be running")
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Extract", "📊 Extraction Results", "ℹ️ About Data Extraction"])
    
    with tab1:
        st.header("📤 Upload SOW Document")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a SOW file (PDF or DOCX)",
            type=['pdf', 'docx'],
            help="Upload a Statement of Work document for structured data extraction"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            # Upload button
            if st.button("🚀 Extract Structured Data", type="primary"):
                
                with st.spinner("Uploading file and extracting data..."):
                    # Upload file
                    upload_result = upload_sow_file(uploaded_file, processing_type)
                    
                    if "error" in upload_result:
                        st.error(f"❌ Upload failed: {upload_result['error']}")
                    else:
                        file_id = upload_result.get("file_id")
                        st.success(f"✅ File uploaded successfully! ID: {file_id}")
                        
                        # Wait for processing
                        st.info("⏳ Processing document with Azure OpenAI...")
                        
                        max_attempts = 30
                        for attempt in range(max_attempts):
                            status_result = get_processing_status(file_id)
                            
                            if "error" in status_result:
                                st.error(f"❌ Status check failed: {status_result['error']}")
                                break
                            
                            status = status_result.get("status", "")
                            
                            if "completed" in status:
                                st.success("✅ Processing completed!")
                                
                                # Get enhanced recommendations (which include extraction data)
                                recommendations = get_enhanced_recommendations(file_id)
                                
                                if "error" in recommendations:
                                    st.error(f"❌ Failed to get results: {recommendations['error']}")
                                else:
                                    # Store results in session state
                                    st.session_state['extracted_data'] = recommendations
                                    st.success("🎉 Data extraction completed! Check the 'Extraction Results' tab.")
                                break
                            
                            elif "error" in status:
                                st.error(f"❌ Processing failed: {status}")
                                break
                            
                            else:
                                time.sleep(2)
                                st.info(f"⏳ Processing... (Attempt {attempt + 1}/{max_attempts})")
                        
                        else:
                            st.error("⏰ Processing timeout. Please try again.")
    
    with tab2:
        st.header("📊 Structured Data Extraction Results")
        
        if 'extracted_data' in st.session_state:
            display_extracted_data(st.session_state['extracted_data'])
            
            # Export options
            st.markdown("### 💾 **Export Options**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # JSON Export
                json_data = json.dumps(st.session_state['extracted_data'], indent=2)
                st.download_button(
                    label="📄 Download JSON",
                    data=json_data,
                    file_name=f"sow_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    type="primary"
                )
            
            with col2:
                # Create DataFrame for CSV export
                extracted_data = st.session_state['extracted_data']
                df_data = {
                    'Field': ['Company', 'Project Title', 'Duration (weeks)', 'Departments', 'Deliverables Count', 'Roles Count', 'Confidence Score'],
                    'Value': [
                        extracted_data.get('company', ''),
                        extracted_data.get('project_title', ''),
                        extracted_data.get('duration_weeks', ''),
                        ', '.join(extracted_data.get('departments_involved', [])),
                        len(extracted_data.get('deliverables', [])),
                        len(extracted_data.get('roles_mentioned', [])),
                        extracted_data.get('confidence_score', 0.0)
                    ]
                }
                df = pd.DataFrame(df_data)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="📊 Download CSV",
                    data=csv,
                    file_name=f"sow_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("👆 Upload and process a SOW document to see extraction results here.")
    
    with tab3:
        st.header("ℹ️ About Homogeneous Data Extraction")
        display_homogeneous_vs_heterogeneous()

if __name__ == "__main__":
    main()
