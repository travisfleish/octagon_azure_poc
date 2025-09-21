#!/usr/bin/env python3
"""
SOW Processing Streamlit App
===========================

Main Streamlit application for SOW processing with 4 tabs:
1. Upload SOW (with staffing plan)
2. Upload SOW (no staffing plan) → Recommendation
3. Semantic Search (historical SOWs)
4. Standardized SOW Input
"""

import streamlit as st
import asyncio
import os
import sys
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Set SSL certificate environment variables to use certifi's certificate bundle
import certifi
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()

# Add the services directory to the path
sys.path.append(str(Path(__file__).parent / "services"))

from sow_extraction_service import SOWExtractionService, ExtractionProgress
from azure_search_service import get_search_service
from vector_search_service import get_vector_search_service
from hybrid_search_service import get_hybrid_search_service


# Page configuration
st.set_page_config(
    page_title="SOW Processing App",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Initialize session state
if 'extraction_service' not in st.session_state:
    st.session_state.extraction_service = None
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = []
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'search_service' not in st.session_state:
    st.session_state.search_service = None


@st.cache_resource
def get_extraction_service():
    """Get or create the extraction service (cached)"""
    if st.session_state.extraction_service is None:
        # Point to the parent directory where the sows folder is
        service = SOWExtractionService(sows_directory="../sows")
        return service
    return st.session_state.extraction_service


def process_uploaded_file(uploaded_file, progress_bar, status_text):
    """Process an uploaded file"""
    try:
        # Save uploaded file temporarily
        temp_path = Path("temp") / uploaded_file.name
        temp_path.parent.mkdir(exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Initialize service if needed
        service = get_extraction_service()
        if st.session_state.extraction_service is None:
            # Run async initialization
            asyncio.run(service.initialize())
            st.session_state.extraction_service = service
        
        # Set progress callback
        def progress_callback(progress: ExtractionProgress):
            progress_bar.progress(progress.percentage / 100)
            status_text.text(f"{progress.stage}: {progress.message}")
        
        service.set_progress_callback(progress_callback)
        
        # Process the file (run async function)
        result = asyncio.run(service.process_single_sow(temp_path))
        
        # Clean up temp file
        temp_path.unlink()
        
        return result
        
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None


def generate_sow_recommendations(sow_data, client_filter="All Clients", length_filter="All Lengths", top=3):
    """Generate recommendations based on similar historical SOWs"""
    try:
        # Initialize vector search service
        vector_search_service = get_vector_search_service()
        
        # Create search query from SOW data
        search_parts = []
        
        # Add client name if available
        if sow_data.get('client_name'):
            search_parts.append(sow_data['client_name'])
        
        # Add project title
        if sow_data.get('project_title'):
            search_parts.append(sow_data['project_title'])
        
        # Add scope summary (first 500 chars)
        if sow_data.get('scope_summary'):
            search_parts.append(sow_data['scope_summary'][:500])
        
        # Add deliverables (first few)
        if sow_data.get('deliverables'):
            search_parts.extend(sow_data['deliverables'][:3])
        
        # Combine into search query
        search_query = " ".join(search_parts)
        
        # Build filter expression
        filter_parts = []
        if client_filter != "All Clients":
            filter_parts.append(f"client_name eq '{client_filter}'")
        if length_filter != "All Lengths":
            filter_parts.append(f"project_length eq '{length_filter}'")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Perform vector search
        results = vector_search_service.vector_search(
            query=search_query,
            top=top * 2,  # Get more results to filter
            filter_expression=filter_expression
        )
        
        if results and 'value' in results:
            # Filter out low-relevance results and format
            formatted_results = []
            for doc in results['value']:
                score = doc.get('@search.score', 0.0)
                if score >= 0.3:  # Only include results with decent relevance
                    formatted_results.append({
                        'client_name': doc.get('client_name', 'Unknown'),
                        'project_title': doc.get('project_title', 'No title'),
                        'scope_summary': doc.get('scope_summary', 'No summary'),
                        'deliverables': doc.get('deliverables', []),
                        'staffing_plan': doc.get('staffing_plan', []),
                        'start_date': doc.get('start_date', ''),
                        'end_date': doc.get('end_date', ''),
                        'project_length': doc.get('project_length', ''),
                        'file_name': doc.get('file_name', ''),
                        'extraction_timestamp': doc.get('extraction_timestamp', ''),
                        'relevance_score': score
                    })
            
            # Return top N results
            return formatted_results[:top]
        
        return []
        
    except Exception as e:
        st.error(f"Error generating recommendations: {e}")
        return []


def main():
    """Main application"""
    st.title("📋 SOW Processing App")
    st.markdown("Process and analyze Statement of Work documents")
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Check Azure credentials
        required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            st.error(f"Missing environment variables: {', '.join(missing_vars)}")
            st.info("Please set up your .env file with Azure OpenAI credentials")
            return
        else:
            st.success("✅ Azure credentials configured")
        
        # Check Azure Search credentials
        search_vars = ["SEARCH_ENDPOINT", "SEARCH_KEY"]
        missing_search_vars = [var for var in search_vars if not os.getenv(var)]
        
        if missing_search_vars:
            st.warning(f"Missing search variables: {', '.join(missing_search_vars)}")
            st.info("Search functionality will not be available")
        else:
            st.success("✅ Azure Search configured")
        
        st.markdown("---")
        st.markdown("### 📊 Processing Status")
        if st.session_state.processing_results:
            successful = len([r for r in st.session_state.processing_results if r.success])
            total = len(st.session_state.processing_results)
            st.metric("Success Rate", f"{successful}/{total}")
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload SOW", 
        "🤖 Upload + Recommend", 
        "🔍 Search", 
        "📝 Standardized Input"
    ])
    
    with tab1:
        st.header("📤 Upload SOW (with staffing plan)")
        st.markdown("Upload a SOW document to extract structured data and staffing information.")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a SOW file",
            type=['pdf', 'docx'],
            help="Upload a PDF or DOCX SOW document"
        )
        
        if uploaded_file is not None:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🚀 Process SOW", type="primary"):
                    # Create progress indicators
                    progress_bar = st.progress(0)
                    status_text = st.text("Initializing...")
                    
                    # Process the file
                    with st.spinner("Processing SOW..."):
                        result = process_uploaded_file(uploaded_file, progress_bar, status_text)
                    
                    if result and result.success:
                        st.success("✅ SOW processed successfully!")
                        
                        # Store result
                        st.session_state.processing_results.append(result)
                        
                        # Display results
                        st.subheader("📊 Extraction Results")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Basic Information**")
                            st.write(f"**Client:** {result.data.get('client_name', 'N/A')}")
                            st.write(f"**Project:** {result.data.get('project_title', 'N/A')}")
                            st.write(f"**Duration:** {result.data.get('project_length', 'N/A')}")
                            st.write(f"**Start Date:** {result.data.get('start_date', 'N/A')}")
                            st.write(f"**End Date:** {result.data.get('end_date', 'N/A')}")
                        
                        with col2:
                            st.markdown("**Project Details**")
                            st.write(f"**Deliverables:** {len(result.data.get('deliverables', []))} items")
                            st.write(f"**Exclusions:** {len(result.data.get('exclusions', []))} items")
                            st.write(f"**Staffing Plan:** {len(result.data.get('staffing_plan', []))} people")
                            st.write(f"**Processing Time:** {result.processing_time:.2f}s")
                        
                        # Azure Storage upload info
                        st.subheader("☁️ Azure Storage Uploads")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.success("✅ Raw File")
                            st.write(f"**Container:** sows")
                            st.write(f"**File:** {result.file_name}")
                        
                        with col2:
                            st.success("✅ Extracted Text")
                            st.write(f"**Container:** extracted")
                            st.write(f"**File:** {result.file_name.replace('.pdf', '').replace('.docx', '')}.txt")
                        
                        with col3:
                            st.success("✅ Structured Data")
                            st.write(f"**Container:** parsed")
                            st.write(f"**File:** {result.file_name.replace('.pdf', '').replace('.docx', '')}_parsed.json")
                        
                        # Scope Summary
                        if result.data.get('scope_summary'):
                            st.subheader("📝 Scope Summary")
                            st.write(result.data['scope_summary'])
                        
                        # Deliverables
                        if result.data.get('deliverables'):
                            st.subheader("🎯 Deliverables")
                            for i, deliverable in enumerate(result.data['deliverables'], 1):
                                st.write(f"{i}. {deliverable}")
                        
                        # Staffing Plan
                        if result.data.get('staffing_plan'):
                            st.subheader("👥 Staffing Plan")
                            staffing_df = pd.DataFrame(result.data['staffing_plan'])
                            st.dataframe(staffing_df, use_container_width=True)
                        
                        # Download options
                        st.subheader("💾 Download Options")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # JSON download
                            json_data = json.dumps(result.data, indent=2)
                            st.download_button(
                                label="📄 Download JSON",
                                data=json_data,
                                file_name=f"{result.file_name}_extracted.json",
                                mime="application/json"
                            )
                        
                        with col2:
                            # Excel download
                            service = get_extraction_service()
                            excel_filename = service.save_to_spreadsheet([result])
                            with open(excel_filename, 'rb') as f:
                                st.download_button(
                                    label="📊 Download Excel",
                                    data=f.read(),
                                    file_name=excel_filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        
                        with col3:
                            # Raw text download (we don't have extracted_text in our data structure)
                            st.info("📝 Text extraction not available in current version")
                    
                    else:
                        st.error("❌ Failed to process SOW")
                        if result:
                            st.error(f"Error: {result.error}")
                        else:
                            st.error("No result returned from processing")
            
            with col2:
                st.info("💡 **Tips for better extraction:**\n"
                       "- Ensure the document has clear section headers\n"
                       "- Include explicit staffing information\n"
                       "- Use standard SOW formats\n"
                       "- Check that dates are in readable format")
    
    with tab2:
        st.header("🤖 Upload SOW (no staffing plan) → Recommendation")
        st.markdown("Upload a SOW without staffing information to get AI-powered recommendations based on similar historical SOWs.")
        
        # Initialize session state for this tab
        if 'uploaded_sow_data' not in st.session_state:
            st.session_state.uploaded_sow_data = None
        if 'similar_sows' not in st.session_state:
            st.session_state.similar_sows = []
        
        # File upload section
        st.subheader("📤 Upload SOW Document")
        uploaded_file = st.file_uploader(
            "Choose a SOW file (PDF or DOCX)",
            type=['pdf', 'docx'],
            help="Upload a SOW document to get recommendations based on similar historical projects",
            key="recommend_upload"
        )
        
        if uploaded_file is not None:
            # Process the uploaded file
            if st.button("🚀 Process & Extract Data", type="primary"):
                # Create progress indicators
                progress_bar = st.progress(0)
                status_text = st.text("Initializing...")
                
                # Process the file using existing extraction service
                with st.spinner("Processing SOW..."):
                    result = process_uploaded_file(uploaded_file, progress_bar, status_text)
                
                if result and result.success:
                    st.success("✅ SOW processed successfully!")
                    st.session_state.uploaded_sow_data = result.data
                    
                    # Display extracted data for review
                    st.subheader("📊 Extracted SOW Data")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Basic Information**")
                        st.write(f"**Client:** {result.data.get('client_name', 'N/A')}")
                        st.write(f"**Project:** {result.data.get('project_title', 'N/A')}")
                        st.write(f"**Duration:** {result.data.get('project_length', 'N/A')}")
                        st.write(f"**Start Date:** {result.data.get('start_date', 'N/A')}")
                        st.write(f"**End Date:** {result.data.get('end_date', 'N/A')}")
                    
                    with col2:
                        st.markdown("**Project Details**")
                        st.write(f"**Deliverables:** {len(result.data.get('deliverables', []))} items")
                        st.write(f"**Exclusions:** {len(result.data.get('exclusions', []))} items")
                        st.write(f"**Processing Time:** {result.processing_time:.2f}s")
                    
                    # Scope Summary
                    if result.data.get('scope_summary'):
                        st.markdown("**Scope Summary:**")
                        st.write(result.data['scope_summary'])
                    
                    # Deliverables
                    if result.data.get('deliverables'):
                        st.markdown("**Deliverables:**")
                        for i, deliverable in enumerate(result.data['deliverables'], 1):
                            st.write(f"{i}. {deliverable}")
                    
                    # Exclusions
                    if result.data.get('exclusions'):
                        st.markdown("**Exclusions:**")
                        for i, exclusion in enumerate(result.data['exclusions'], 1):
                            st.write(f"{i}. {exclusion}")
                    
                    # Show button to proceed to recommendations
                    st.markdown("---")
                    if st.button("🔍 Find Similar Historical SOWs", type="primary"):
                        st.rerun()
                
                else:
                    st.error("❌ Failed to process SOW")
                    if result:
                        st.error(f"Error: {result.error}")
        
        # Similar SOWs recommendation section
        if st.session_state.uploaded_sow_data:
            st.markdown("---")
            st.subheader("🔍 Similar Historical SOWs")
            
            # Filtering options
            with st.expander("🔧 Filter Options", expanded=False):
                filter_col1, filter_col2 = st.columns(2)
                
                with filter_col1:
                    # Get unique clients from search service
                    try:
                        search_service = get_search_service()
                        clients = search_service.get_unique_clients()
                        selected_client_filter = st.selectbox(
                            "Filter by Client",
                            ["All Clients"] + clients,
                            help="Filter similar SOWs by client"
                        )
                    except:
                        selected_client_filter = "All Clients"
                
                with filter_col2:
                    # Project length filter
                    try:
                        search_service = get_search_service()
                        lengths = search_service.get_unique_project_lengths()
                        selected_length_filter = st.selectbox(
                            "Filter by Project Length",
                            ["All Lengths"] + lengths,
                            help="Filter similar SOWs by project duration"
                        )
                    except:
                        selected_length_filter = "All Lengths"
            
            # Generate recommendations button
            if st.button("🎯 Generate Recommendations", type="primary"):
                with st.spinner("Finding similar historical SOWs..."):
                    # Generate recommendations using vector search
                    recommendations = generate_sow_recommendations(
                        st.session_state.uploaded_sow_data,
                        client_filter=selected_client_filter,
                        length_filter=selected_length_filter
                    )
                    
                    if recommendations:
                        st.session_state.similar_sows = recommendations
                        st.success(f"✅ Found {len(recommendations)} similar historical SOWs")
                    else:
                        st.warning("⚠️ No similar SOWs found. Try adjusting your filters.")
                        st.session_state.similar_sows = []
            
            # Display recommendations
            if st.session_state.similar_sows:
                st.markdown("---")
                st.subheader(f"📋 Top {len(st.session_state.similar_sows)} Similar SOWs")
                
                for i, similar_sow in enumerate(st.session_state.similar_sows, 1):
                    confidence_score = similar_sow.get('relevance_score', 0.0)
                    
                    with st.expander(f"#{i} {similar_sow['client_name']} - {similar_sow['project_title']} (Confidence: {confidence_score:.2f})", expanded=(i==1)):
                        # Basic info
                        info_col1, info_col2, info_col3 = st.columns(3)
                        
                        with info_col1:
                            st.write(f"**Client:** {similar_sow['client_name']}")
                            st.write(f"**Duration:** {similar_sow['project_length']}")
                            st.write(f"**File:** {similar_sow['file_name']}")
                        
                        with info_col2:
                            st.write(f"**Start Date:** {similar_sow['start_date']}")
                            st.write(f"**End Date:** {similar_sow['end_date']}")
                            extraction_time = similar_sow.get('extraction_timestamp', '')
                            if extraction_time:
                                st.write(f"**Extracted:** {extraction_time}")
                        
                        with info_col3:
                            deliverables_count = len(similar_sow.get('deliverables', []))
                            staffing_count = len(similar_sow.get('staffing_plan', []))
                            st.write(f"**Deliverables:** {deliverables_count} items")
                            st.write(f"**Staffing:** {staffing_count} people")
                            st.write(f"**Similarity:** {confidence_score:.2f}")
                        
                        # Scope summary
                        scope_summary = similar_sow.get('scope_summary', '')
                        if scope_summary:
                            st.markdown("**Scope Summary:**")
                            st.write(scope_summary[:500] + "..." if len(scope_summary) > 500 else scope_summary)
                        
                        # Deliverables
                        deliverables = similar_sow.get('deliverables', [])
                        if deliverables:
                            st.markdown("**Deliverables:**")
                            for j, deliverable in enumerate(deliverables[:5], 1):  # Show first 5
                                st.write(f"{j}. {deliverable}")
                            if len(deliverables) > 5:
                                st.write(f"... and {len(deliverables) - 5} more")
                        
                        # Staffing plan (this is what we're recommending from)
                        staffing_plan = similar_sow.get('staffing_plan', [])
                        if staffing_plan:
                            st.markdown("**Staffing Plan (Recommendation Source):**")
                            staffing_df = pd.DataFrame(staffing_plan)
                            st.dataframe(staffing_df, use_container_width=True)
                        else:
                            st.info("No staffing plan available in this historical SOW")
        
        # Information section
        st.markdown("---")
        with st.expander("ℹ️ How Recommendations Work", expanded=False):
            st.markdown("""
            **Recommendation Process:**
            1. **Upload & Extract**: Your SOW is processed to extract structured data (client, project details, deliverables, etc.)
            2. **Vector Embedding**: The extracted content is converted to AI embeddings for semantic comparison
            3. **Similarity Search**: We search our historical SOW database to find the most similar projects
            4. **Recommendations**: The top 3 most similar SOWs are displayed with their staffing plans as recommendations
            
            **Similarity Factors:**
            - Project scope and deliverables
            - Client industry and type
            - Project duration and complexity
            - Technology and methodology used
            
            **Using Recommendations:**
            - Review the staffing plans from similar historical SOWs
            - Consider the similarity scores (higher = more relevant)
            - Adapt the recommended staffing to your specific project needs
            - Download individual recommendations for detailed review
            """)
    
    with tab3:
        st.header("🔍 Search Historical SOWs")
        st.markdown("Search through previously processed SOW documents using Azure Search.")
        
        # Initialize search service
        try:
            if st.session_state.search_service is None:
                st.session_state.search_service = get_search_service()
            
            search_service = st.session_state.search_service
            
            # Get basic stats
            with st.spinner("Loading search index..."):
                stats = search_service.get_stats()
            
            # Display stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total SOWs", stats['total_documents'])
            with col2:
                st.metric("Unique Clients", stats['clients'])
            with col3:
                if stats['date_range']:
                    st.metric("Date Range", f"{stats['date_range']['earliest']} to {stats['date_range']['latest']}")
                else:
                    st.metric("Date Range", "N/A")
            with col4:
                st.metric("Search Index", "✅ Active")
            
            st.markdown("---")
            
            # Search interface
            search_col1, search_col2 = st.columns([2, 1])
            
            with search_col1:
                search_query = st.text_input(
                    "🔍 Search Query",
                    placeholder="Enter keywords, client name, project title, or staffing role...",
                    help="Search across all SOW fields including client names, project titles, deliverables, and staffing plans"
                )
            
            with search_col2:
                search_type = st.selectbox(
                    "Search Type",
                    ["All Fields", "Client Name", "Project Title", "Staffing Role", "Deliverables"],
                    help="Choose which fields to search"
                )
            
            # Search method selection
            search_method = st.radio(
                "🔍 Search Method",
                ["Hybrid Search (Full Text + Parsed)", "Vector Search (Semantic)", "Basic Search"],
                help="Choose your search method: Hybrid combines full text and parsed data, Vector uses parsed data only, Basic for exact keyword matches"
            )
            
            # Additional options
            col_options1, col_options2 = st.columns(2)
            with col_options1:
                show_strategy = st.checkbox(
                    "📊 Show Search Strategy", 
                    value=True,
                    help="Show which search strategy found each result"
                )
            with col_options2:
                show_scores = st.checkbox(
                    "📈 Show Relevance Scores", 
                    value=True,
                    help="Show relevance scores for each result"
                )
            
            # Advanced filters
            with st.expander("🔧 Advanced Filters", expanded=False):
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                
                with filter_col1:
                    # Client filter
                    clients = search_service.get_unique_clients()
                    selected_client = st.selectbox(
                        "Filter by Client",
                        ["All Clients"] + clients,
                        help="Filter results by specific client"
                    )
                
                with filter_col2:
                    # Project length filter
                    lengths = search_service.get_unique_project_lengths()
                    selected_length = st.selectbox(
                        "Filter by Project Length",
                        ["All Lengths"] + lengths,
                        help="Filter results by project duration"
                    )
                
                with filter_col3:
                    # Date range filter
                    date_filter = st.checkbox("Filter by Date Range")
                    if date_filter:
                        start_date = st.date_input("Start Date")
                        end_date = st.date_input("End Date")
                    else:
                        start_date = None
                        end_date = None
            
            # Search button
            search_button = st.button("🚀 Search", type="primary", use_container_width=True)
            
            # Perform search
            if search_button and search_query:
                with st.spinner("Searching..."):
                    # Determine search fields based on type
                    search_fields = None
                    if search_type == "Client Name":
                        search_fields = "client_name"
                    elif search_type == "Project Title":
                        search_fields = "project_title"
                    elif search_type == "Staffing Role":
                        search_fields = "staffing_plan"
                    elif search_type == "Deliverables":
                        search_fields = "deliverables"
                    
                    # Build filter expression
                    filter_parts = []
                    if selected_client != "All Clients":
                        filter_parts.append(f"client_name eq '{selected_client}'")
                    if selected_length != "All Lengths":
                        filter_parts.append(f"project_length eq '{selected_length}'")
                    if date_filter and start_date and end_date:
                        filter_parts.append(f"start_date ge '{start_date}' and end_date le '{end_date}'")
                    
                    filter_expression = " and ".join(filter_parts) if filter_parts else None
                    
                    # Perform search based on selected method
                    if search_method == "Hybrid Search (Full Text + Parsed)":
                        # Initialize hybrid search service
                        hybrid_search_service = get_hybrid_search_service()
                        results = hybrid_search_service.hybrid_vector_search(
                            query=search_query,
                            top=50,
                            filter_expression=filter_expression
                        )
                        
                        # Filter out low-relevance results (threshold: 0.01 for hybrid)
                        if results and 'value' in results:
                            filtered_results = []
                            for doc in results['value']:
                                score = doc.get('@search.score', 0.0)
                                if score >= 0.01:  # Lower threshold for hybrid search
                                    filtered_results.append(doc)
                            results['value'] = filtered_results
                        if results and 'value' in results:
                            # Format results for display
                            formatted_results = []
                            for doc in results['value']:
                                formatted_results.append({
                                    'client_name': doc.get('client_name', 'Unknown'),
                                    'project_title': doc.get('project_title', 'No title'),
                                    'scope_summary': doc.get('scope_summary', 'No summary'),
                                    'deliverables': doc.get('deliverables', []),
                                    'staffing_plan': doc.get('staffing_plan', []),
                                    'start_date': doc.get('start_date', ''),
                                    'end_date': doc.get('end_date', ''),
                                    'project_length': doc.get('project_length', ''),
                                    'file_name': doc.get('file_name', ''),
                                    'extraction_timestamp': doc.get('extraction_timestamp', ''),
                                    'raw_content': doc.get('raw_content', ''),
                                    'search_strategy': doc.get('search_strategy', 'hybrid_vector_search'),
                                    'relevance_score': doc.get('@search.score', 0.0)
                                })
                            st.session_state.search_results = formatted_results
                        else:
                            st.error("❌ Hybrid search failed. Please check your query and try again.")
                            st.session_state.search_results = []
                    
                    elif search_method == "Vector Search (Semantic)":
                        # Initialize vector search service
                        vector_search_service = get_vector_search_service()
                        results = vector_search_service.vector_search(
                            query=search_query,
                            top=50,
                            filter_expression=filter_expression
                        )
                        
                        # Filter out low-relevance results (threshold: 0.3)
                        if results and 'value' in results:
                            filtered_results = []
                            for doc in results['value']:
                                score = doc.get('@search.score', 0.0)
                                if score >= 0.3:  # Only show results with decent relevance
                                    filtered_results.append(doc)
                            results['value'] = filtered_results
                        if results and 'value' in results:
                            # Format results for display
                            formatted_results = []
                            for doc in results['value']:
                                formatted_results.append({
                                    'client_name': doc.get('client_name', 'Unknown'),
                                    'project_title': doc.get('project_title', 'No title'),
                                    'scope_summary': doc.get('scope_summary', 'No summary'),
                                    'deliverables': doc.get('deliverables', []),
                                    'staffing_plan': doc.get('staffing_plan', []),
                                    'start_date': doc.get('start_date', ''),
                                    'end_date': doc.get('end_date', ''),
                                    'project_length': doc.get('project_length', ''),
                                    'file_name': doc.get('file_name', ''),
                                    'extraction_timestamp': doc.get('extraction_timestamp', ''),
                                    'search_strategy': doc.get('search_strategy', 'vector_search'),
                                    'relevance_score': doc.get('@search.score', 0.0)
                                })
                            st.session_state.search_results = formatted_results
                        else:
                            st.error("❌ Vector search failed. Please check your query and try again.")
                            st.session_state.search_results = []
                    
                    else:  # Basic Search
                        results = search_service.search(
                            query=search_query,
                            search_fields=search_fields,
                            filter_expression=filter_expression,
                            top=50
                        )
                        if results:
                            st.session_state.search_results = search_service.format_search_results(results)
                        else:
                            st.error("❌ Search failed. Please check your query and try again.")
                            st.session_state.search_results = []
            
            # Display results
            if st.session_state.search_results:
                st.markdown("---")
                st.subheader(f"📊 Search Results ({len(st.session_state.search_results)} found)")
                
                # Results summary
                result_summary = st.container()
                with result_summary:
                    st.success(f"✅ Found {len(st.session_state.search_results)} matching SOWs")
                
                # Display each result
                for i, result in enumerate(st.session_state.search_results):
                    # Create expander title with search strategy info
                    expander_title = f"📋 {result['client_name']} - {result['project_title']}"
                    if show_strategy and 'search_strategy' in result:
                        strategy = result['search_strategy']
                        score = result.get('strategy_score', result.get('relevance_score', 0.0))
                        expander_title += f" [{strategy} - {score:.2f}]"
                    
                    with st.expander(expander_title, expanded=False):
                        # Basic info
                        info_col1, info_col2, info_col3 = st.columns(3)
                        
                        with info_col1:
                            st.write(f"**Client:** {result['client_name']}")
                            st.write(f"**Duration:** {result['project_length']}")
                            st.write(f"**File:** {result['file_name']}")
                        
                        with info_col2:
                            st.write(f"**Start Date:** {result['start_date']}")
                            st.write(f"**End Date:** {result['end_date']}")
                            extraction_time = result.get('extraction_timestamp', '')
                            if extraction_time:
                                st.write(f"**Extracted:** {extraction_time}")
                        
                        with info_col3:
                            deliverables_count = len(result.get('deliverables', []))
                            staffing_count = len(result.get('staffing_plan', []))
                            st.write(f"**Deliverables:** {deliverables_count} items")
                            st.write(f"**Staffing:** {staffing_count} people")
                            if show_scores and 'relevance_score' in result:
                                st.write(f"**Relevance Score:** {result['relevance_score']:.2f}")
                        
                        # Scope summary
                        scope_summary = result.get('scope_summary', '')
                        if scope_summary:
                            st.markdown("**Scope Summary:**")
                            st.write(scope_summary[:500] + "..." if len(scope_summary) > 500 else scope_summary)
                        
                        # Raw content (for hybrid search)
                        raw_content = result.get('raw_content', '')
                        if raw_content and search_method == "Hybrid Search (Full Text + Parsed)":
                            st.markdown("**Full Document Content:**")
                            st.write(raw_content[:1000] + "..." if len(raw_content) > 1000 else raw_content)
                        
                        # Deliverables preview
                        deliverables = result.get('deliverables', [])
                        if deliverables:
                            st.markdown("**Deliverables (first 3):**")
                            for j, deliverable in enumerate(deliverables[:3], 1):
                                st.write(f"{j}. {deliverable}")
                            if deliverables_count > 3:
                                st.write(f"... and {deliverables_count - 3} more")
                        
                        # Staffing preview
                        staffing_plan = result.get('staffing_plan', [])
                        if staffing_plan:
                            st.markdown("**Staffing Plan (first 3):**")
                            for j, staff in enumerate(staffing_plan[:3], 1):
                                st.write(f"{j}. {staff}")
                            if staffing_count > 3:
                                st.write(f"... and {staffing_count - 3} more")
                        
                        # Download options for this result
                        st.markdown("**Download Options:**")
                        download_col1, download_col2 = st.columns(2)
                        
                        with download_col1:
                            # JSON download
                            json_data = json.dumps(result, indent=2)
                            st.download_button(
                                label="📄 Download JSON",
                                data=json_data,
                                file_name=f"{result['file_name']}_search_result.json",
                                mime="application/json",
                                key=f"json_download_{i}"
                            )
                        
                        with download_col2:
                            # Markdown summary
                            markdown_content = f"""# SOW Search Result

**Client:** {result['client_name']}
**Project:** {result['project_title']}
**Duration:** {result['project_length']}
**Dates:** {result['start_date']} to {result['end_date']}

## Scope Summary
{result['scope_summary']}

## Deliverables
{chr(10).join([f"{j+1}. {d}" for j, d in enumerate(result['deliverables'])])}

## Staffing Plan
{chr(10).join([f"{j+1}. {s}" for j, s in enumerate(result['staffing_plan'])])}
"""
                            st.download_button(
                                label="📝 Download Summary",
                                data=markdown_content,
                                file_name=f"{result['file_name']}_summary.md",
                                mime="text/markdown",
                                key=f"md_download_{i}"
                            )
            
            elif search_button and not search_query:
                st.warning("⚠️ Please enter a search query")
            
            # Search explanation
            st.markdown("---")
            with st.expander("🔍 About Search Methods", expanded=False):
                st.markdown("""
                **Hybrid Search (Full Text + Parsed)**: 
                - Combines full document text with structured parsed data
                - Uses AI embeddings for both raw content and parsed fields
                - Most comprehensive search - finds details in original documents
                - Best for complex conceptual searches
                - **Recommended for most searches**
                
                **Vector Search (Semantic)**: 
                - Uses AI embeddings on structured parsed data only
                - Good for conceptual searches with clean, organized results
                - Handles synonyms and related concepts automatically
                - Faster than hybrid search
                
                **Basic Search**:
                - Traditional keyword matching using Azure Search
                - Fast and reliable for exact keyword searches
                - Good when you know the exact words in the document
                - Requires exact or very close matches
                """)
            
            # Quick search suggestions
            st.markdown("---")
            st.subheader("💡 Quick Search Suggestions")
            
            suggestion_col1, suggestion_col2, suggestion_col3, suggestion_col4 = st.columns(4)
            
            with suggestion_col1:
                if st.button("🏌️ Golf Events", use_container_width=True):
                    st.session_state.search_query = "golf related events"
                    st.rerun()
            
            with suggestion_col2:
                if st.button("🏨 Hospitality", use_container_width=True):
                    st.session_state.search_query = "hospitality programs"
                    st.rerun()
            
            with suggestion_col3:
                if st.button("📅 August Events", use_container_width=True):
                    st.session_state.search_query = "august tournament"
                    st.rerun()
            
            with suggestion_col4:
                if st.button("📊 All SOWs", use_container_width=True):
                    st.session_state.search_query = "*"
                    st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error initializing search service: {e}")
            st.info("Please ensure your Azure Search credentials are properly configured in the .env file")
    
    with tab4:
        st.header("📝 Standardized SOW Input")
        st.markdown("Create standardized SOW documents using a form wizard with AI assistance.")
        
        st.info("🚧 **Coming Soon!** This feature will provide:\n"
               "- Form wizard with required fields\n"
               "- AI assist for scope normalization\n"
               "- DOCX template generation\n"
               "- Conformance scoring and validation")


if __name__ == "__main__":
    main()
