#!/usr/bin/env python3
"""
Simple Streamlit Test - Enhanced Octagon Staffing Plan Generator
==============================================================

A simplified version to test the enhanced staffing plan generator without complex dependencies.
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="🤖 Octagon AI Staffing Generator", 
    page_icon="🤖", 
    layout="wide"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_enhanced_staffing_directly():
    """Test the enhanced staffing service directly without file upload"""
    
    st.header("🧪 Direct Test of Enhanced Staffing Service")
    
    # Test the enhanced service directly
    try:
        # Import the enhanced service
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))
        
        from app.services.enhanced_staffing_service import EnhancedStaffingPlanService
        from app.models.sow import ProcessedSOW, SOWProcessingType
        
        st.success("✅ Enhanced staffing service imported successfully!")
        
        # Create sample data
        sample_llm_data = {
            "blob_name": "company_1_sow_1.pdf",
            "company": "Company 1",
            "sow_id": "SOW-001",
            "project_title": "Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
            "format": "pdf",
            "term": {
                "start": "2024-01-01",
                "end": "2024-12-31",
                "months": 12,
                "inferred": False
            },
            "roles_detected": [
                {"title": "Account Director", "canonical": "Account Director"},
                {"title": "Strategy Director", "canonical": "Strategy Director"},
                {"title": "Account Manager", "canonical": "Account Manager"},
                {"title": "Creative Director", "canonical": "Creative Director"}
            ],
            "scope_bullets": [
                "B2B hospitality programming for three Events",
                "Formula 1 – Las Vegas Race (2024)",
                "67th Annual GRAMMY Awards",
                "2025 API Tournament"
            ],
            "deliverables": [
                "High end hospitality programming for up to forty (40) BW guests/hosts",
                "Compliance documents and necessary approvals decks",
                "Program budgets for Hospitality Room, gift premiums, transportation",
                "Third party vendor management",
                "Guest communications",
                "Program recap and reporting"
            ],
            "units": {
                "explicit_hours": [2080, 1560, 1040],
                "fte_pct": [100, 75, 50],
                "fees": [],
                "rate_table": []
            },
            "assumptions": [],
            "provenance": {
                "quotes": [],
                "sections": [],
                "notes": "Generated from SOW text"
            }
        }
        
        # Create ProcessedSOW
        processed_sow = ProcessedSOW(
            blob_name="company_1_sow_1.pdf",
            sow_id="SOW-001",
            company="Company 1",
            project_title="Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
            processing_type=SOWProcessingType.NEW_STAFFING,
            full_text="""
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
            """,
            sections=["Scope of Work", "Deliverables", "Project Staffing Plan"],
            key_entities=["Company 1", "Formula 1", "GRAMMY Awards", "API Tournament"],
            raw_extraction=sample_llm_data
        )
        
        st.info("📊 Generating staffing plan with enhanced business rules...")
        
        # Generate staffing plan
        with st.spinner("🤖 AI is analyzing the SOW and applying business rules..."):
            service = EnhancedStaffingPlanService()
            staffing_plan = service.generate_staffing_plan_from_sow(processed_sow, sample_llm_data)
        
        st.success("✅ Enhanced staffing plan generated successfully!")
        
        # Display results
        st.header("🎯 Generated Staffing Plan")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_fte = sum(role.allocation_percent for role in staffing_plan.roles)
            st.metric("Total FTE", f"{total_fte}%")
        
        with col2:
            st.metric("Number of Roles", len(staffing_plan.roles))
        
        with col3:
            st.metric("Confidence Score", f"{staffing_plan.confidence:.2f}")
        
        with col4:
            departments = set(role.department for role in staffing_plan.roles if role.department)
            st.metric("Departments", len(departments))
        
        # Role breakdown
        st.header("👥 Role Breakdown")
        
        for role in staffing_plan.roles:
            with st.expander(f"**{role.role}** - {role.allocation_percent}% FTE"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Department:** {role.department or 'Unknown'}")
                    st.write(f"**Level:** {role.level or 'N/A'}")
                
                with col2:
                    st.write(f"**Allocation:** {role.allocation_percent}% FTE")
                    st.write(f"**Quantity:** {role.quantity}")
                
                with col3:
                    st.write(f"**Notes:** {role.notes or 'No notes'}")
        
        # Business rules validation
        st.header("📋 Business Rules Validation")
        
        # Check for Creative Director
        creative_director_found = any("creative director" in role.role.lower() and role.allocation_percent == 5 for role in staffing_plan.roles)
        st.write(f"✅ Creative Director (5% rule): {'Applied' if creative_director_found else 'Not Applied'}")
        
        # Check minimum pod size
        min_pod_size = len(staffing_plan.roles) >= 4
        st.write(f"✅ Minimum Pod Size (4 employees): {'Met' if min_pod_size else 'Not Met'} ({len(staffing_plan.roles)} roles)")
        
        # Check Client Services FTE
        client_services_fte = sum(role.allocation_percent for role in staffing_plan.roles if role.department and "client services" in role.department.lower())
        client_services_compliant = 75 <= client_services_fte <= 100
        st.write(f"✅ Client Services FTE (75-100%): {'Compliant' if client_services_compliant else 'Not Compliant'} ({client_services_fte:.1f}%)")
        
        # Department allocation summary
        st.header("📊 Department Allocation Summary")
        
        dept_allocations = {}
        for role in staffing_plan.roles:
            dept = role.department or 'Unknown'
            allocation = role.allocation_percent
            dept_allocations[dept] = dept_allocations.get(dept, 0) + allocation
        
        for dept, total_fte in dept_allocations.items():
            st.metric(f"{dept} Total FTE", f"{total_fte:.1f}%")
        
        # Show summary
        st.header("📝 AI-Enhanced Summary")
        st.text(staffing_plan.summary)
        
        # Export options
        st.header("📥 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV Export
            csv_data = []
            for role in staffing_plan.roles:
                csv_data.append({
                    "Role": role.role,
                    "Department": role.department or "",
                    "Level": role.level or "",
                    "Quantity": role.quantity,
                    "Allocation_Percent": role.allocation_percent,
                    "Notes": role.notes or ""
                })
            
            import pandas as pd
            df = pd.DataFrame(csv_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="📊 Download CSV",
                data=csv,
                file_name=f"staffing_plan_{staffing_plan.sow_id}.csv",
                mime="text/csv",
                type="primary"
            )
        
        with col2:
            # JSON Export
            json_data = json.dumps(staffing_plan.dict(), indent=2)
            st.download_button(
                label="📄 Download JSON",
                data=json_data,
                file_name=f"staffing_plan_{staffing_plan.sow_id}.json",
                mime="application/json"
            )
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error testing enhanced staffing service: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False

def main():
    """Main Streamlit application"""
    
    # Header
    st.title("🤖 Octagon AI Staffing Plan Generator - Direct Test")
    st.markdown("**Testing the enhanced AI-powered staffing plan generator with business rules**")
    
    # Check API health
    if check_api_health():
        st.success("✅ **API Connected** - FastAPI server is running")
    else:
        st.warning("⚠️ **API Not Connected** - FastAPI server may not be running")
    
    # Test the enhanced service directly
    if st.button("🧪 Test Enhanced Staffing Service", type="primary"):
        test_enhanced_staffing_directly()
    
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

if __name__ == "__main__":
    main()
