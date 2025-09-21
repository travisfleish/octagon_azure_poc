#!/usr/bin/env python3
"""
Direct Data Extraction Demo - Streamlit App
==========================================

This Streamlit app demonstrates the homogeneous data extraction directly
using the real SOW analyzer without needing the FastAPI backend.
"""

import streamlit as st
import pandas as pd
import json
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add paths for imports
sys.path.append('octagon-staffing-app')
sys.path.append('organized/analysis-results')

# Configure Streamlit page
st.set_page_config(
    page_title="📊 Direct SOW Data Extraction Demo", 
    page_icon="📊", 
    layout="wide"
)

# Custom CSS
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
</style>
""", unsafe_allow_html=True)

def load_existing_results():
    """Load existing analysis results"""
    try:
        with open('organized/analysis-results/real_sow_analysis_results.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def display_sow_extraction(sow_data):
    """Display extracted data for a single SOW"""
    
    st.markdown('<div class="extraction-box">', unsafe_allow_html=True)
    st.markdown(f"### 📄 **{sow_data['file_name']}**")
    
    # Basic Information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="field-header">🏢 Company & Project</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Company:</strong> {sow_data.get("company", "Unknown")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Project:</strong> {sow_data.get("project_title", "Unknown")}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="field-header">⏱️ Duration & Scope</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Duration:</strong> {sow_data.get("duration_weeks", 0)} weeks</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Departments:</strong> {len(sow_data.get("departments_involved", []))}</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="field-header">🎯 Quality Metrics</div>', unsafe_allow_html=True)
        confidence = sow_data.get("confidence_score", 0.0)
        if confidence >= 0.8:
            st.markdown(f'<div class="field-value" style="color: #27ae60;"><strong>Confidence:</strong> {confidence:.2f} (High)</div>', unsafe_allow_html=True)
        elif confidence >= 0.6:
            st.markdown(f'<div class="field-value" style="color: #f39c12;"><strong>Confidence:</strong> {confidence:.2f} (Medium)</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="field-value" style="color: #e74c3c;"><strong>Confidence:</strong> {confidence:.2f} (Low)</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="field-value"><strong>Deliverables:</strong> {len(sow_data.get("deliverables", []))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value"><strong>Roles:</strong> {len(sow_data.get("roles_mentioned", []))}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Departments
    departments = sow_data.get("departments_involved", [])
    if departments:
        st.markdown("#### 🏛️ **Octagon Department Mapping**")
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
                st.markdown(f"✅ **{dept.replace('_', ' ').title()}**")
                st.caption(dept_mapping.get(dept, "Department mapping"))
    
    # Deliverables
    deliverables = sow_data.get("deliverables", [])
    if deliverables:
        st.markdown("#### 📋 **Sample Deliverables**")
        with st.expander(f"View {len(deliverables)} Deliverables", expanded=False):
            for i, deliverable in enumerate(deliverables[:10], 1):  # Show first 10
                st.markdown(f"**{i}.** {deliverable}")
            if len(deliverables) > 10:
                st.caption(f"... and {len(deliverables) - 10} more deliverables")
    
    # Roles
    roles = sow_data.get("roles_mentioned", [])
    if roles:
        st.markdown("#### 👥 **Staffing Roles Identified**")
        with st.expander(f"View {len(roles)} Roles", expanded=False):
            for i, role in enumerate(roles, 1):
                st.markdown(f"**{i}.** {role}")

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">📊 Direct SOW Data Extraction Demo</h1>', unsafe_allow_html=True)
    st.markdown("**Real homogeneous data extraction from heterogeneous SOW documents**")
    
    # Load existing results
    results = load_existing_results()
    
    if results is None:
        st.error("❌ No analysis results found. Please run the real SOW analyzer first.")
        st.info("Run: `python organized/analysis-results/real_sow_analyzer.py`")
        return
    
    # Summary statistics
    st.markdown("### 📊 **Extraction Summary**")
    
    summary = results['analysis_summary']
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total SOWs", summary['total_sows_analyzed'])
    
    with col2:
        st.metric("Success Rate", f"{(summary['successful_extractions']/summary['total_sows_analyzed']*100):.1f}%")
    
    with col3:
        st.metric("Avg Confidence", f"{summary['average_confidence']:.2f}")
    
    with col4:
        st.metric("Companies", len(results['companies']))
    
    # Department usage
    st.markdown("### 🏛️ **Department Usage Across All SOWs**")
    
    dept_data = []
    for dept, count in results['departments'].items():
        dept_data.append({
            'Department': dept.replace('_', ' ').title(),
            'Count': count,
            'Percentage': f"{(count / summary['successful_extractions']) * 100:.1f}%"
        })
    
    dept_df = pd.DataFrame(dept_data)
    st.dataframe(dept_df, use_container_width=True)
    
    # Individual SOW results
    st.markdown("### 📄 **Individual SOW Extraction Results**")
    
    successful_results = [r for r in results['detailed_results'] if r['confidence_score'] > 0]
    
    # Filter by company if desired
    companies = list(set(r['company'] for r in successful_results if r['company'] != 'ERROR'))
    selected_company = st.selectbox("Filter by Company:", ["All"] + companies)
    
    if selected_company != "All":
        filtered_results = [r for r in successful_results if r['company'] == selected_company]
    else:
        filtered_results = successful_results
    
    # Display results
    for sow_data in filtered_results:
        display_sow_extraction(sow_data)
        st.markdown("---")
    
    # Export options
    st.markdown("### 💾 **Export All Results**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON Export
        st.download_button(
            label="📄 Download Complete Results (JSON)",
            data=json.dumps(results, indent=2, default=str),
            file_name=f"complete_sow_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            type="primary"
        )
    
    with col2:
        # CSV Export
        sow_summary = []
        for sow in successful_results:
            sow_summary.append({
                'File': sow['file_name'],
                'Company': sow['company'],
                'Project': sow['project_title'],
                'Duration_Weeks': sow['duration_weeks'],
                'Departments': ', '.join(sow['departments_involved']),
                'Deliverables_Count': len(sow['deliverables']),
                'Roles_Count': len(sow['roles_mentioned']),
                'Confidence_Score': sow['confidence_score']
            })
        
        df = pd.DataFrame(sow_summary)
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="📊 Download Summary (CSV)",
            data=csv,
            file_name=f"sow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Homogeneous vs Heterogeneous explanation
    st.markdown("### 🔄 **Homogeneous Data Extraction Process**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 **Heterogeneous Input**")
        st.markdown("""
        - **9 different SOW files** in mixed formats
        - **Various company structures** and terminology
        - **Inconsistent layouts** and field naming
        - **Different levels of detail** and completeness
        """)
    
    with col2:
        st.markdown("#### 📊 **Homogeneous Output**")
        st.markdown("""
        - **10 standardized fields** extracted consistently
        - **4 Octagon departments** properly mapped
        - **Structured JSON format** for all documents
        - **Quality confidence scoring** for each extraction
        """)

if __name__ == "__main__":
    main()
