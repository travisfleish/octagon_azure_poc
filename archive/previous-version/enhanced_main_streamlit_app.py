#!/usr/bin/env python3
"""
Enhanced Main Streamlit App - Complete SOW Processing with Data Extraction
=======================================================================

This is the main Streamlit app that combines file upload, AI processing,
homogeneous data extraction display, and staffing plan generation.
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
    page_title="🤖 Octagon SOW AI Processor", 
    page_icon="🤖", 
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
    .staffing-box {
        background-color: #f0fff0;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #27ae60;
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
    .business-rule {
        background-color: #fff8dc;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 3px solid #ffd700;
        margin: 0.25rem 0;
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

def get_staffing_plan(sow_id: str) -> Dict[str, Any]:
    """Get generated staffing plan"""
    try:
        response = requests.get(f"{API_BASE_URL}/staffing-plan/{sow_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get staffing plan: {response.status_code}"}
    except Exception as e:
        return {"error": f"Staffing plan error: {str(e)}"}

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

def display_confidence_score(score: float, label: str = "Confidence"):
    """Display confidence score with appropriate styling"""
    if score >= 0.8:
        st.markdown(f'<span class="confidence-high">🎯 {label}: {score:.2f} (High)</span>', unsafe_allow_html=True)
    elif score >= 0.6:
        st.markdown(f'<span class="confidence-medium">⚠️ {label}: {score:.2f} (Medium)</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="confidence-low">❌ {label}: {score:.2f} (Low)</span>', unsafe_allow_html=True)

def display_homogeneous_data_extraction(extracted_data: Dict[str, Any]):
    """Display the structured data extraction results"""
    
    st.markdown('<div class="extraction-box">', unsafe_allow_html=True)
    st.markdown("### 📊 **Homogeneous Data Extraction Results**")
    st.markdown("*AI-powered extraction of structured data from heterogeneous SOW document*")
    
    # Basic Information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="field-header">📄 Document Information</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>File:</strong> {extracted_data.get("file_name", "Unknown")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Company:</strong> {extracted_data.get("company", "Unknown")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Project:</strong> {extracted_data.get("project_title", "Unknown")}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="field-header">⏱️ Project Details</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Duration:</strong> {extracted_data.get("duration_weeks", 0)} weeks</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Departments:</strong> {len(extracted_data.get("departments_involved", []))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Deliverables:</strong> {len(extracted_data.get("deliverables", []))}</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="field-header">🎯 Extraction Quality</div>', unsafe_allow_html=True)
        confidence = extracted_data.get("confidence_score", 0.0)
        display_confidence_score(confidence, "AI Confidence")
        st.markdown(f'<div class="field-value"><strong>Roles Found:</strong> {len(extracted_data.get("roles_mentioned", []))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Extracted:</strong> {extracted_data.get("extraction_timestamp", "Unknown")}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Departments Mapping
    st.markdown("#### 🏛️ **Octagon Department Mapping**")
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
    
    # Deliverables and Roles in expandable sections
    col1, col2 = st.columns(2)
    
    with col1:
        deliverables = extracted_data.get("deliverables", [])
        if deliverables:
            st.markdown("#### 📋 **Extracted Deliverables**")
            with st.expander(f"View {len(deliverables)} Deliverables", expanded=False):
                for i, deliverable in enumerate(deliverables, 1):
                    st.markdown(f"**{i}.** {deliverable}")
    
    with col2:
        roles = extracted_data.get("roles_mentioned", [])
        if roles:
            st.markdown("#### 👥 **Staffing Roles Identified**")
            with st.expander(f"View {len(roles)} Roles", expanded=False):
                for i, role in enumerate(roles, 1):
                    st.markdown(f"**{i}.** {role}")
    
    # Scope Description
    scope = extracted_data.get("scope_description", "")
    if scope:
        st.markdown("#### 📝 **Project Scope Summary**")
        st.info(scope)
    
    # Budget Information (if available)
    budget_info = extracted_data.get("budget_info", {})
    if budget_info and any(budget_info.values()):
        st.markdown("#### 💰 **Budget Information**")
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

def display_staffing_plan(plan_data: Dict[str, Any]):
    """Display the generated staffing plan"""
    
    st.markdown('<div class="staffing-box">', unsafe_allow_html=True)
    st.markdown("### 👥 **AI-Generated Staffing Plan**")
    st.markdown("*Intelligent staffing recommendations with Octagon business rules applied*")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_fte = sum(role.get('allocation_percent', 0) for role in plan_data.get('roles', []))
        st.metric("Total FTE", f"{total_fte}%")
    
    with col2:
        st.metric("Number of Roles", len(plan_data.get('roles', [])))
    
    with col3:
        display_confidence_score(plan_data.get('confidence', 0), "Plan Confidence")
    
    with col4:
        departments = set(role.get('department', 'Unknown') for role in plan_data.get('roles', []))
        st.metric("Departments", len(departments))
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Role breakdown
    st.markdown("#### 👥 **Role Breakdown**")
    
    for role in plan_data.get('roles', []):
        with st.expander(f"**{role.get('role', 'Unknown Role')}** - {role.get('allocation_percent', 0)}% FTE"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Department:** {role.get('department', 'Unknown')}")
                st.write(f"**Level:** {role.get('level', 'N/A')}")
            
            with col2:
                st.write(f"**Allocation:** {role.get('allocation_percent', 0)}% FTE")
                st.write(f"**Quantity:** {role.get('quantity', 1)}")
            
            with col3:
                st.write(f"**Notes:** {role.get('notes', 'No notes')}")
    
    # Department allocation summary
    if plan_data.get('roles'):
        st.markdown("#### 📊 **Department Allocation Summary**")
        
        dept_allocations = {}
        for role in plan_data['roles']:
            dept = role.get('department', 'Unknown')
            allocation = role.get('allocation_percent', 0)
            dept_allocations[dept] = dept_allocations.get(dept, 0) + allocation
        
        for dept, total_fte in dept_allocations.items():
            st.metric(f"{dept} Total FTE", f"{total_fte:.1f}%")

def display_business_rules_analysis(recommendations: Dict[str, Any]):
    """Display business rules analysis"""
    
    st.markdown("#### 📋 **Octagon Business Rules Analysis**")
    
    # Business rules status
    if recommendations.get('business_rules_applied'):
        st.success("✅ **All Octagon Business Rules Applied Successfully**")
    else:
        st.warning("⚠️ **Business Rules Not Applied**")
    
    # Display specific business rules
    rules_info = [
        ("Creative Director (5%)", "Creative Director always pre-allocated at 5%"),
        ("Executive Oversight (5%)", "L7/L8 leaders allocated for oversight at 5%"),
        ("Sponsorship Limits (≤25%)", "Sponsorship always ≤ 25% FTE per client"),
        ("Client Services (75-100%)", "Client Services 75–100% FTE"),
        ("Experiences (100%)", "Experiences/Hospitality usually near 100% FTE"),
        ("Creative (5-25%)", "Creative usually 5–25% FTE across multiple clients"),
        ("Minimum Pod (4)", "Minimum pod size of four employees")
    ]
    
    for rule_title, rule_description in rules_info:
        st.markdown(f'<div class="business-rule"><strong>{rule_title}:</strong> {rule_description}</div>', unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🤖 Octagon SOW AI Processor</h1>', unsafe_allow_html=True)
    st.markdown("**Complete SOW processing: Homogeneous data extraction → AI staffing plan generation**")
    
    # Sidebar
    st.sidebar.header("📊 Processing Options")
    
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
    
    # Business rules info
    st.sidebar.header("📋 Octagon Business Rules")
    rules = [
        "🎨 Creative Director always pre-allocated at 5%",
        "👔 L7/L8 leaders allocated for oversight at 5% (Complex/Enterprise)",
        "🤝 Sponsorship always ≤ 25% FTE per client (≤ 50% per person)",
        "👥 Client Services 75–100% FTE",
        "🏨 Experiences/Hospitality usually near 100% FTE per client",
        "✨ Creative usually 5–25% FTE across multiple clients",
        "🔢 Minimum pod size of four employees"
    ]
    
    for rule in rules:
        st.sidebar.write(rule)
    
    # Main content
    st.header("📤 Upload SOW Document")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a SOW file (PDF or DOCX)",
        type=['pdf', 'docx'],
        help="Upload a Statement of Work document for AI processing"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        # Upload and process button
        if st.button("🚀 Process with AI", type="primary"):
            
            with st.spinner("Uploading file and processing with Azure OpenAI..."):
                # Upload file
                upload_result = upload_sow_file(uploaded_file, processing_type)
                
                if "error" in upload_result:
                    st.error(f"❌ Upload failed: {upload_result['error']}")
                else:
                    file_id = upload_result.get("file_id")
                    st.success(f"✅ File uploaded successfully! ID: {file_id}")
                    
                    # Wait for processing
                    st.info("⏳ AI is analyzing the SOW and generating staffing plan...")
                    
                    max_attempts = 30
                    for attempt in range(max_attempts):
                        status_result = get_processing_status(file_id)
                        
                        if "error" in status_result:
                            st.error(f"❌ Status check failed: {status_result['error']}")
                            break
                        
                        status = status_result.get("status", "")
                        
                        if "completed" in status:
                            st.success("✅ Processing completed!")
                            
                            # Get enhanced recommendations (includes extraction data)
                            recommendations = get_enhanced_recommendations(file_id)
                            
                            if "error" in recommendations:
                                st.error(f"❌ Failed to get results: {recommendations['error']}")
                            else:
                                # Store results in session state
                                st.session_state['processing_results'] = {
                                    'file_id': file_id,
                                    'recommendations': recommendations,
                                    'uploaded_file': uploaded_file.name
                                }
                                st.success("🎉 AI processing completed! Results displayed below.")
                            break
                        
                        elif "error" in status:
                            st.error(f"❌ Processing failed: {status}")
                            break
                        
                        else:
                            time.sleep(2)
                            st.info(f"⏳ Processing... (Attempt {attempt + 1}/{max_attempts})")
                    
                    else:
                        st.error("⏰ Processing timeout. Please try again.")
    
    # Display results if available
    if 'processing_results' in st.session_state:
        results = st.session_state['processing_results']
        
        st.markdown("---")
        st.header("📊 **Processing Results**")
        
        # Display homogeneous data extraction
        if results['recommendations']:
            display_homogeneous_data_extraction(results['recommendations'])
            
            st.markdown("---")
            
            # Display staffing plan
            display_staffing_plan(results['recommendations'])
            
            st.markdown("---")
            
            # Display business rules analysis
            display_business_rules_analysis(results['recommendations'])
            
            st.markdown("---")
            
            # Export options
            st.header("💾 **Export Results**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # JSON Export
                json_data = json.dumps(results['recommendations'], indent=2)
                st.download_button(
                    label="📄 Download Complete Results (JSON)",
                    data=json_data,
                    file_name=f"sow_processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    type="primary"
                )
            
            with col2:
                # Create summary DataFrame
                extracted_data = results['recommendations']
                summary_data = {
                    'Field': ['Company', 'Project Title', 'Duration (weeks)', 'Departments', 'Total FTE', 'Roles Count', 'AI Confidence'],
                    'Value': [
                        extracted_data.get('company', ''),
                        extracted_data.get('project_title', ''),
                        extracted_data.get('duration_weeks', ''),
                        ', '.join(extracted_data.get('departments_involved', [])),
                        f"{sum(role.get('allocation_percent', 0) for role in extracted_data.get('roles', []))}%",
                        len(extracted_data.get('roles', [])),
                        extracted_data.get('confidence_score', 0.0)
                    ]
                }
                df = pd.DataFrame(summary_data)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="📊 Download Summary (CSV)",
                    data=csv,
                    file_name=f"sow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    else:
        st.info("👆 Upload and process a SOW document to see the complete AI analysis results here.")
        
        # Show example of what the app does
        st.markdown("---")
        st.header("🎯 **What This App Does**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 **Homogeneous Data Extraction**")
            st.markdown("""
            - **AI-powered analysis** using Azure OpenAI
            - **Structured data extraction** from any SOW format
            - **10 standardized fields** consistently extracted
            - **4 Octagon departments** properly mapped
            - **Quality confidence scoring** for each extraction
            """)
        
        with col2:
            st.markdown("#### 👥 **Intelligent Staffing Plan Generation**")
            st.markdown("""
            - **AI + Heuristics hybrid** approach
            - **7 Octagon business rules** automatically applied
            - **Role mapping** to Octagon org chart
            - **FTE allocation** with confidence scoring
            - **Department coordination** recommendations
            """)

if __name__ == "__main__":
    main()
