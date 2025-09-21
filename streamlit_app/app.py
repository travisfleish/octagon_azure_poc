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
        st.markdown("Upload a SOW without staffing information to get AI-powered recommendations.")
        
        st.info("🚧 **Coming Soon!** This feature will provide:\n"
               "- Rules-based baseline staffing recommendations\n"
               "- LLM fine-tuning for specific project needs\n"
               "- Interactive sliders to adjust assumptions\n"
               "- One-pager summary with justification")
    
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
                ["Vector Search (Semantic)", "Basic Search"],
                help="Choose your search method: Vector for semantic understanding, Basic for exact keyword matches"
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
                    if search_method == "Vector Search (Semantic)":
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
                **Vector Search (Semantic)**: 
                - Uses AI embeddings to understand meaning and context
                - Best for conceptual searches (e.g., "golf related events" finds Masters programs)
                - Handles synonyms and related concepts automatically
                - Most accurate for complex queries
                - **Recommended for most searches**
                
                **Basic Search**:
                - Traditional keyword matching using Azure Search
                - Fast and reliable for exact keyword searches
                - Good when you know the exact words in the document
                - Requires exact or very close matches
                """)
            
            # Quick search suggestions
            st.markdown("---")
            st.subheader("💡 Quick Search Suggestions")
            
            suggestion_col1, suggestion_col2, suggestion_col3 = st.columns(3)
            
            with suggestion_col1:
                if st.button("🔍 All SOWs", use_container_width=True):
                    st.session_state.search_results = search_service.format_search_results(
                        search_service.get_all_documents()
                    )
                    st.rerun()
            
            with suggestion_col2:
                if st.button("🏢 All Clients", use_container_width=True):
                    clients = search_service.get_unique_clients()
                    st.write("**Available Clients:**")
                    for client in clients:
                        st.write(f"• {client}")
            
            with suggestion_col3:
                if st.button("📊 Index Stats", use_container_width=True):
                    stats = search_service.get_stats()
                    st.write("**Index Statistics:**")
                    st.write(f"• Total Documents: {stats['total_documents']}")
                    st.write(f"• Unique Clients: {stats['clients']}")
                    if stats['date_range']:
                        st.write(f"• Date Range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
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
