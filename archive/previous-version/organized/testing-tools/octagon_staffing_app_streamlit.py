#!/usr/bin/env python3
"""
Enhanced Octagon Staffing Plan Generator - Streamlit Interface
=============================================================

This Streamlit app showcases the enhanced AI-powered staffing plan generator
with all 7 Octagon business rules integrated.
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
    page_title="🤖 Octagon AI Staffing Generator", 
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
    .business-rule {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .ai-enhanced {
        background-color: #f0fff0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #228b22;
        margin: 0.5rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    .role-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e9ecef;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust if your API runs on different port

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def upload_sow_for_staffing(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Upload SOW for staffing plan generation"""
    try:
        files = {"file": (filename, file_bytes, "application/octet-stream")}
        data = {"processing_type": "new_staffing"}
        
        response = requests.post(
            f"{API_BASE_URL}/upload-new-sow",
            files=files,
            data=data,
            timeout=30
        )
        
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

def display_business_rules():
    """Display the 7 Octagon business rules"""
    st.markdown("### 📋 Octagon Business Rules Applied")
    
    rules = [
        {
            "title": "Creative Director Pre-allocation",
            "description": "Creative Director always pre-allocated at 5%",
            "icon": "🎨"
        },
        {
            "title": "Executive Oversight",
            "description": "L7/L8 leaders allocated for oversight at 5% (Complex/Enterprise projects)",
            "icon": "👔"
        },
        {
            "title": "Sponsorship Limits",
            "description": "Sponsorship always ≤ 25% FTE per client (≤ 50% per person)",
            "icon": "🤝"
        },
        {
            "title": "Client Services FTE",
            "description": "Client Services 75–100% FTE",
            "icon": "👥"
        },
        {
            "title": "Experiences/Hospitality",
            "description": "Experiences/Hospitality usually near 100% FTE per client",
            "icon": "🏨"
        },
        {
            "title": "Creative Allocation",
            "description": "Creative usually 5–25% FTE across multiple clients",
            "icon": "✨"
        },
        {
            "title": "Minimum Pod Size",
            "description": "Minimum pod size of four employees",
            "icon": "🔢"
        }
    ]
    
    for rule in rules:
        st.markdown(f"""
        <div class="business-rule">
            <strong>{rule['icon']} {rule['title']}:</strong><br>
            {rule['description']}
        </div>
        """, unsafe_allow_html=True)

def display_staffing_plan(plan_data: Dict[str, Any]):
    """Display the generated staffing plan with enhanced formatting"""
    
    st.markdown("### 🎯 Generated Staffing Plan")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total FTE", f"{sum(role.get('allocation_percent', 0) for role in plan_data.get('roles', []))}%")
    
    with col2:
        st.metric("Number of Roles", len(plan_data.get('roles', [])))
    
    with col3:
        st.metric("Confidence Score", f"{plan_data.get('confidence', 0):.2f}")
    
    with col4:
        departments = set(role.get('department', 'Unknown') for role in plan_data.get('roles', []))
        st.metric("Departments", len(departments))
    
    # Role breakdown
    st.markdown("#### 👥 Role Breakdown")
    
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
        st.markdown("#### 📊 Department Allocation Summary")
        
        dept_allocations = {}
        for role in plan_data['roles']:
            dept = role.get('department', 'Unknown')
            allocation = role.get('allocation_percent', 0)
            dept_allocations[dept] = dept_allocations.get(dept, 0) + allocation
        
        for dept, total_fte in dept_allocations.items():
            st.metric(f"{dept} Total FTE", f"{total_fte:.1f}%")

def display_enhanced_recommendations(recommendations: Dict[str, Any]):
    """Display enhanced recommendations with business rules analysis"""
    
    st.markdown("### 🤖 AI-Enhanced Analysis")
    
    # Business rules status
    if recommendations.get('business_rules_applied'):
        st.success("✅ **Octagon Business Rules Applied Successfully**")
    else:
        st.warning("⚠️ **Business Rules Not Applied**")
    
    # Key metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("AI Augmented", "✅ Yes" if recommendations.get('ai_augmented') else "❌ No")
    
    with col2:
        st.metric("Status", recommendations.get('status', 'Unknown'))
    
    with col3:
        st.metric("Total FTE", f"{recommendations.get('total_fte', 0):.1f}")
    
    # Business rules details
    if recommendations.get('business_rules_details'):
        st.markdown("#### 📋 Business Rules Details")
        details = recommendations['business_rules_details']
        
        st.write(f"**Compliance Status:** {details.get('compliance_status', 'Unknown')}")
        
        if details.get('rules_checked'):
            st.write("**Rules Applied:**")
            for rule in details['rules_checked']:
                st.write(f"• {rule}")
        
        if details.get('warnings'):
            st.warning("**Warnings:**")
            for warning in details['warnings']:
                st.write(f"• {warning}")
    
    # Departments involved
    if recommendations.get('departments_involved'):
        st.markdown("#### 🏢 Departments Involved")
        for dept in recommendations['departments_involved']:
            st.write(f"• {dept}")

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<div class="main-header">🤖 Octagon AI Staffing Plan Generator</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="ai-enhanced">
        <strong>🚀 Enhanced with AI + Business Rules</strong><br>
        Upload SOWs to generate intelligent staffing plans that comply with all Octagon business rules.
    </div>
    """, unsafe_allow_html=True)
    
    # Check API health
    if not check_api_health():
        st.error("❌ **API Connection Failed** - Please ensure the FastAPI server is running on http://localhost:8000")
        st.info("To start the API server, run: `uvicorn octagon-staffing-app.app.main:app --reload`")
        return
    
    st.success("✅ **API Connected** - Ready to process SOWs")
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Quick Actions")
        
        # Display business rules
        display_business_rules()
        
        st.markdown("---")
        st.markdown("### 📊 Test Results")
        st.info("Upload a SOW file to see the enhanced AI staffing plan generator in action!")
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload SOW", "📊 View Results", "🧪 Test Examples"])
    
    with tab1:
        st.header("📤 Upload SOW for AI Staffing Plan Generation")
        
        st.markdown("""
        **Upload a new SOW to generate an intelligent staffing plan with:**
        - 🤖 AI-powered project analysis
        - 📋 Automatic business rules application
        - 👥 Smart role mapping to Octagon structure
        - 📊 Confidence scoring and quality metrics
        """)
        
        uploaded_file = st.file_uploader(
            "Choose a PDF or DOCX file",
            type=["pdf", "docx"],
            help="Upload a Statement of Work document to generate staffing recommendations"
        )
        
        if uploaded_file is not None:
            st.success(f"📁 **File Selected:** {uploaded_file.name}")
            
            # File info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
            with col2:
                st.metric("File Type", uploaded_file.type)
            with col3:
                st.metric("Upload Time", datetime.now().strftime("%H:%M:%S"))
            
            if st.button("🚀 Generate AI Staffing Plan", type="primary", use_container_width=True):
                # Upload file
                with st.spinner("📤 Uploading file to API..."):
                    file_bytes = uploaded_file.read()
                    upload_result = upload_sow_for_staffing(file_bytes, uploaded_file.name)
                
                if "error" in upload_result:
                    st.error(f"❌ Upload failed: {upload_result['error']}")
                    return
                
                file_id = upload_result.get('file_id')
                st.success(f"✅ File uploaded successfully! File ID: {file_id}")
                
                # Store file_id in session state
                st.session_state.file_id = file_id
                st.session_state.filename = uploaded_file.name
                
                # Monitor processing
                st.markdown("### ⏳ Processing Status")
                status_placeholder = st.empty()
                progress_bar = st.progress(0)
                
                max_attempts = 30  # 30 seconds timeout
                for attempt in range(max_attempts):
                    status_result = get_processing_status(file_id)
                    
                    if "error" in status_result:
                        st.error(f"❌ Status check failed: {status_result['error']}")
                        break
                    
                    status = status_result.get('status', 'unknown')
                    status_placeholder.text(f"Status: {status}")
                    
                    # Update progress based on status
                    if status == "queued":
                        progress_bar.progress(0.2)
                    elif status == "processing":
                        progress_bar.progress(0.5)
                    elif status == "completed_new_staffing":
                        progress_bar.progress(1.0)
                        st.success("✅ Processing completed!")
                        break
                    elif "error" in status:
                        st.error(f"❌ Processing failed: {status}")
                        break
                    
                    time.sleep(1)
                else:
                    st.warning("⏰ Processing timeout - please check the results tab")
                
                st.rerun()
    
    with tab2:
        st.header("📊 View Generated Results")
        
        if 'file_id' not in st.session_state:
            st.info("👆 Please upload a SOW file first to see results")
            return
        
        file_id = st.session_state.file_id
        filename = st.session_state.get('filename', 'Unknown')
        
        st.success(f"📁 **Viewing results for:** {filename}")
        
        # Get staffing plan
        with st.spinner("📊 Loading staffing plan..."):
            plan_result = get_staffing_plan(file_id)
        
        if "error" in plan_result:
            st.error(f"❌ Failed to load staffing plan: {plan_result['error']}")
            return
        
        # Display staffing plan
        display_staffing_plan(plan_result)
        
        # Get enhanced recommendations
        with st.spinner("🤖 Loading AI analysis..."):
            recommendations_result = get_enhanced_recommendations(file_id)
        
        if "error" not in recommendations_result:
            display_enhanced_recommendations(recommendations_result)
        
        # Export options
        st.markdown("### 📥 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV Export
            if plan_result.get('roles'):
                csv_data = []
                for role in plan_result['roles']:
                    csv_data.append({
                        "Role": role.get('role', ''),
                        "Department": role.get('department', ''),
                        "Level": role.get('level', ''),
                        "Quantity": role.get('quantity', 1),
                        "Allocation_Percent": role.get('allocation_percent', 0),
                        "Notes": role.get('notes', '')
                    })
                
                df = pd.DataFrame(csv_data)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="📊 Download CSV",
                    data=csv,
                    file_name=f"staffing_plan_{file_id}.csv",
                    mime="text/csv",
                    type="primary"
                )
        
        with col2:
            # JSON Export
            json_data = json.dumps(plan_result, indent=2)
            st.download_button(
                label="📄 Download JSON",
                data=json_data,
                file_name=f"staffing_plan_{file_id}.json",
                mime="application/json"
            )
        
        # Technical details
        with st.expander("🔧 Technical Details"):
            st.json(plan_result)
    
    with tab3:
        st.header("🧪 Test Examples")
        
        st.markdown("""
        **Try these sample SOWs to see the AI staffing plan generator in action:**
        """)
        
        # Sample SOW text
        sample_sow = """
        Project Title: Company 1 Americas 2024-2025 Sponsorship Hospitality Programs
        Client: Company 1
        Duration: 52 weeks
        
        Scope of Work:
        Develop B2B hospitality programming for three (3) Events:
        - Formula 1 – Las Vegas Race (2024)
        - 67th Annual GRAMMY Awards
        - 2025 API Tournament
        
        Deliverables:
        - High end hospitality programming for up to forty (40) B2B guests/hosts total at Event
        - Compliance documents and necessary approvals decks for guest approvals
        - Program budgets for Hospitality Room, gift premiums, transportation and GRAMMYs assets
        - Third party vendor management including A/V, décor, and gift premiums
        - Guest communications including pre-trip documents, welcome packets and branding elements
        - Program recap and reporting
        
        Project Staffing Plan:
        Account Director - Program Lead Formula 1 – Las Vegas Day to Day Manager
        Account Manager - API Day to Day Manager  
        SAE - GRAMMY's Day to Day Manager
        AE - Program Support
        
        Budget: $3,380 total hours allocated across team
        """
        
        st.text_area("Sample SOW Content:", value=sample_sow, height=300)
        
        st.info("💡 **Expected Results:**")
        st.markdown("""
        - **6 roles generated** (meets minimum pod size of 4)
        - **Creative Director at 5%** (business rule applied)
        - **Client Services allocation** (75-100% FTE range)
        - **Department mapping** to Octagon structure
        - **Confidence scoring** for quality assessment
        """)
        
        # Expected business rules
        st.markdown("#### ✅ Expected Business Rules Applied:")
        expected_rules = [
            "Creative Director pre-allocated at 5%",
            "Minimum pod size of 4 employees met",
            "Client Services FTE within 75-100% range",
            "Proper department allocation",
            "Sponsorship limits respected (if applicable)"
        ]
        
        for rule in expected_rules:
            st.write(f"• {rule}")

if __name__ == "__main__":
    main()
