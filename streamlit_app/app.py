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
import re
from pathlib import Path
from dotenv import load_dotenv
import base64

# Page configuration - MUST be first Streamlit call
st.set_page_config(
    page_title="Staffing Plan Assistant",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Inter font into the document head
def _load_inter_font():
    try:
        st.markdown(
            """
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass

# Load custom CSS (visual only)
def _load_global_styles():
    styles_path = Path(__file__).parent / "styles.css"
    if styles_path.exists():
        try:
            with open(styles_path, "r", encoding="utf-8") as f:
                css = f.read()
            # Safe visual-only injection
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        except Exception:
            pass

# Optional brand logo support
def _get_logo_path():
    env_path = os.getenv("APP_LOGO_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    candidate_names = [
        "octagon_logo.png", "octagon_logo.jpg", "octagon_logo.jpeg",
        "logo.png", "logo.jpg", "logo.jpeg", "logo.svg"
    ]
    for name in candidate_names:
        p = Path(__file__).parent / "assets" / name
        if p.exists():
            return str(p)
    return None

def render_brand_header():
    logo_path = _get_logo_path()
    # Only render text here; logo will be placed in the header bar
    st.title("Staffing Plan Assistant")
    st.caption("Process and analyze Statement of Work documents with Azure AI")

def render_header_logo():
    """Render a centered logo in the fixed header bar."""
    logo_path = _get_logo_path()
    if not logo_path:
        return
    try:
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        # Use a CSS pseudo-element to ensure the logo renders inside the header bar
        st.markdown(
            f"""
            <style>
            header[data-testid='stHeader'] {{ position: relative; min-height: 96px; }}
            header[data-testid='stHeader']::after {{
                content: '';
                position: absolute;
                left: 50%;
                transform: translateX(-50%);
                top: -45px;
                width: 1000px;
                height: 200px;
                background: url('data:image/png;base64,{encoded}') no-repeat center center / contain;
                pointer-events: none;
                z-index: 10000;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass

def render_logo_below_tabs():
    """Render a centered logo just below the tabs area inside each tab content."""
    logo_path = _get_logo_path()
    if not logo_path:
        return
    spacer_left, center, spacer_right = st.columns([1, 2, 1])
    with center:
        st.image(logo_path, width=120)

def _parse_staffing_item_to_columns(item):
    """Convert one staffing entry (dict or string) into a normalized row with name, title, allocation.

    Supported string patterns (examples):
    - "Christine Franklin (EVP Global Account lead): 2%"
    - "Christine Franklin - EVP Global Account lead - 2%"
    - "EVP Global Account lead: 2%" (title only)
    - "Analyst: 900 hours"
    """
    if isinstance(item, dict):
        name = item.get('name') or ''
        title = item.get('title') or item.get('role') or ''
        allocation = ''
        if item.get('hours_pct') is not None:
            try:
                allocation = f"{float(item['hours_pct']):.1f}%"
            except Exception:
                allocation = str(item['hours_pct'])
        elif item.get('hours') is not None:
            try:
                allocation = f"{float(item['hours']):.0f} hours"
            except Exception:
                allocation = f"{item['hours']} hours"
        return {"name": name, "title": title, "allocation": allocation}

    text = str(item).strip()

    # 1) name (title): 10%
    m = re.match(r"^\s*([^:(\-]+?)\s*(?:\(([^)]*)\))?\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*$", text)
    if m:
        name, title, pct = m.group(1).strip(), (m.group(2) or '').strip(), m.group(3)
        return {"name": name, "title": title, "allocation": f"{float(pct):.1f}%"}

    # 2) name - title - 10%
    m = re.match(r"^\s*([^:]+?)[\s\-–—]+([^:]+?)[\s\-–—]+([0-9]+(?:\.[0-9]+)?)\s*%\s*$", text)
    if m:
        return {"name": m.group(1).strip(), "title": m.group(2).strip(), "allocation": f"{float(m.group(3)):.1f}%"}

    # 3) title: 900 hours
    m = re.match(r"^\s*([^:]+?)\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*(?:hours|hrs)\s*$", text, re.IGNORECASE)
    if m:
        return {"name": '', "title": m.group(1).strip(), "allocation": f"{float(m.group(2)):.0f} hours"}

    # Fallback: try to split on ':' or '-' and extract a number with %
    pct = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", text)
    allocation = f"{pct.group(1)}%" if pct else ''
    # Try parentheses for title
    name = text
    title_match = re.search(r"\(([^)]*)\)", text)
    title = title_match.group(1).strip() if title_match else ''
    if title:
        name = text.split('(')[0].strip().rstrip(':-')
    else:
        # Try split by ' - '
        parts = [p.strip() for p in re.split(r"\s*[\-–—]\s*", text)]
        if len(parts) >= 2:
            name, title = parts[0], parts[1]
    return {"name": name, "title": title, "allocation": allocation}

def _normalize_staffing_plan_to_dataframe(staffing_plan):
    """Return a pandas DataFrame with Name, Title, Allocation.

    Prefers structured JSON fields when available:
    - dict with key 'entries' -> uses that list
    - list of dicts with keys like 'name', 'title', 'primary_role', 'role', 'hours_pct', 'hours'
    Falls back to parsing strings.
    """
    # Coerce JSON strings into Python structures when necessary
    if isinstance(staffing_plan, str):
        try:
            staffing_plan = json.loads(staffing_plan)
        except Exception:
            pass

    # If wrapped in an object (e.g., {"entries": [...]})
    if isinstance(staffing_plan, dict) and isinstance(staffing_plan.get('entries'), list):
        items = staffing_plan['entries']
    else:
        items = staffing_plan or []

    normalized_rows = []
    for item in items:
        if isinstance(item, dict) and (item.get('name') or item.get('title') or item.get('role') or item.get('primary_role')):
            name = (item.get('name') or '').strip()
            base_title = (item.get('title') or item.get('role') or '').strip()
            primary_role = (item.get('primary_role') or '').strip()
            # Prefer combining title and primary_role, but avoid duplicating last names in title
            title_parts = [p for p in [base_title, primary_role] if p]
            title = ' — '.join(title_parts)
            allocation = ''
            if item.get('hours_pct') is not None:
                try:
                    allocation = f"{float(item['hours_pct']):.1f}%"
                except Exception:
                    allocation = str(item['hours_pct'])
            elif item.get('hours') is not None:
                try:
                    allocation = f"{float(item['hours']):.0f} hours"
                except Exception:
                    allocation = f"{item['hours']} hours"
            normalized_rows.append({"Name": name, "Title": title, "Allocation": allocation})
        else:
            parsed = _parse_staffing_item_to_columns(item)
            normalized_rows.append({
                "Name": parsed.get('name', ''),
                "Title": parsed.get('title', ''),
                "Allocation": parsed.get('allocation', ''),
            })

    df = pd.DataFrame(normalized_rows)
    # Ensure columns exist in correct order
    for col in ["Name", "Title", "Allocation"]:
        if col not in df.columns:
            df[col] = ''
    df = df[["Name", "Title", "Allocation"]]
    return df

def _looks_like_structured_staffing(staffing_plan) -> bool:
    """Heuristically determine if staffing_plan contains structured dict data."""
    if not staffing_plan:
        return False
    plan = staffing_plan
    if isinstance(plan, str):
        try:
            plan = json.loads(plan)
        except Exception:
            return False
    if isinstance(plan, dict) and isinstance(plan.get('entries'), list):
        return True
    if isinstance(plan, list) and len(plan) > 0 and isinstance(plan[0], dict):
        keys = set(plan[0].keys())
        structured_keys = {"name", "title", "role", "primary_role", "hours", "hours_pct"}
        return len(keys.intersection(structured_keys)) > 0
    return False

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



# Apply global styles
_load_inter_font()
_load_global_styles()

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
            # Defer initialization into the extraction flow's event loop
            st.session_state.extraction_service = service
        
        # Set progress callback
        def progress_callback(progress: ExtractionProgress):
            progress_bar.progress(progress.percentage / 100)
            status_text.text(f"{progress.stage}: {progress.message}")
        
        service.set_progress_callback(progress_callback)
        
        # Process in a fresh loop to ensure Azure clients are created/used within the same loop
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(service.process_single_sow(temp_path))
        finally:
            loop.close()
        
        # Clean up temp file
        temp_path.unlink()
        
        return result
        
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None


def normalize_staffing_data(staffing_plan):
    """Normalize staffing plan data to use percentage-based allocations"""
    try:
        # Initialize extraction service to use normalization functions
        service = get_extraction_service()
        return service.normalize_staffing_plan(staffing_plan)
    except Exception as e:
        st.error(f"Error normalizing staffing data: {e}")
        return staffing_plan


def _ensure_extraction_initialized():
    """Ensure the SOWExtractionService is initialized (for Azure Storage access)."""
    service = get_extraction_service()
    if st.session_state.extraction_service is None:
        asyncio.run(service.initialize())
        st.session_state.extraction_service = service
    return service


def fetch_staffing_from_blob(file_name: str):
    """Fetch staffing_plan from parsed blob when search index lacks it."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient
        
        # Get storage account URL from environment
        storage_account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        if not storage_account_url:
            return []
        
        # Initialize synchronous blob client
        cred = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=cred)
        
        blob_name = f"{file_name.replace('.pdf', '').replace('.docx', '')}_parsed.json"
        blob_client = blob_service_client.get_blob_client(container="parsed", blob=blob_name)
        
        # Download blob content synchronously
        blob_data = blob_client.download_blob()
        content = blob_data.readall()
        data = json.loads(content.decode('utf-8'))
        
        return data.get('staffing_plan', [])
    except Exception:
        return []


def generate_sow_recommendations(sow_data, client_filter="All Clients", length_filter="All Lengths", top=3):
    """Generate recommendations using HYBRID vector search and return unique SOWs."""
    try:
        # Initialize hybrid search service (vector + parsed)
        hybrid_search_service = get_hybrid_search_service()
        
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
        
        # Perform hybrid search with more candidates, dedup later
        results = hybrid_search_service.hybrid_vector_search(
            query=search_query,
            top=top * 5,
            filter_expression=filter_expression
        )
        
        if results and 'value' in results:
            # Deduplicate by file_name and keep highest hybrid strategy score
            dedup = {}
            for doc in results['value']:
                key = (doc.get('file_name') or '').strip() or doc.get('id')
                score = doc.get('strategy_score', doc.get('@search.score', 0.0))
                if not key:
                    continue
                if key not in dedup or score > dedup[key]['relevance_score']:
                    # Prefer structured staffing data from blob hydration, fallback to search index data
                    staffing_plan = doc.get('staffing_plan_structured') or doc.get('staffing_plan', [])
                    
                    dedup[key] = {
                        'client_name': doc.get('client_name', 'Unknown'),
                        'project_title': doc.get('project_title', 'No title'),
                        'scope_summary': doc.get('scope_summary', 'No summary'),
                        'deliverables': doc.get('deliverables', []),
                        'staffing_plan': staffing_plan,
                        'staffing_plan_structured': doc.get('staffing_plan_structured'),
                        'start_date': doc.get('start_date', ''),
                        'end_date': doc.get('end_date', ''),
                        'project_length': doc.get('project_length', ''),
                        'file_name': doc.get('file_name', ''),
                        'extraction_timestamp': doc.get('extraction_timestamp', ''),
                        'relevance_score': score,
                        'search_strategy': doc.get('search_strategy', 'hybrid')
                    }

            # Sort by score and return top N unique
            unique_sorted = sorted(dedup.values(), key=lambda d: d['relevance_score'], reverse=True)
            return unique_sorted[:top]
        
        return []
        
    except Exception as e:
        st.error(f"Error generating recommendations: {e}")
        return []








def main():
    """Main application"""
    render_header_logo()
    render_brand_header()
    
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
        "Upload SOW", 
        "Historical Analog", 
        "Search", 
        "Standardized Input"
    ])
    
    with tab1:
        st.header("Upload SOW (with staffing plan)")
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
                if st.button("Process SOW", type="primary"):
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
                        st.subheader("Extraction Results")
                        
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
                        st.subheader("Azure Storage Uploads")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.success("Raw File")
                            st.write(f"**Container:** sows")
                            st.write(f"**File:** {result.file_name}")
                        
                        with col2:
                            st.success("Extracted Text")
                            st.write(f"**Container:** extracted")
                            st.write(f"**File:** {result.file_name.replace('.pdf', '').replace('.docx', '')}.txt")
                        
                        with col3:
                            st.success("Structured Data")
                            st.write(f"**Container:** parsed")
                            st.write(f"**File:** {result.file_name.replace('.pdf', '').replace('.docx', '')}_parsed.json")
                        
                        # Scope Summary
                        if result.data.get('scope_summary'):
                            st.subheader("Scope Summary")
                            st.write(result.data['scope_summary'])
                        
                        # Deliverables
                        if result.data.get('deliverables'):
                            st.subheader("Deliverables")
                            for i, deliverable in enumerate(result.data['deliverables'], 1):
                                st.write(f"{i}. {deliverable}")
                        
                        # Staffing Plan
                        if result.data.get('staffing_plan'):
                            st.subheader("Staffing Plan")
                            staffing_df = pd.DataFrame(result.data['staffing_plan'])
                            st.dataframe(staffing_df, use_container_width=True)
                        
                        # Download options
                        st.subheader("Download Options")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # JSON download
                            json_data = json.dumps(result.data, indent=2)
                            st.download_button(
                                label="Download JSON",
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
                                    label="Download Excel",
                                    data=f.read(),
                                    file_name=excel_filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        
                        with col3:
                            # Raw text download (we don't have extracted_text in our data structure)
                            st.info("Text extraction not available in current version")
                    
                    else:
                        st.error("❌ Failed to process SOW")
                        if result:
                            st.error(f"Error: {result.error}")
                        else:
                            st.error("No result returned from processing")
            
            with col2:
                st.info("**Tips for better extraction:**\n"
                       "- Ensure the document has clear section headers\n"
                       "- Include explicit staffing information\n"
                       "- Use standard SOW formats\n"
                       "- Check that dates are in readable format")
    
    with tab2:
        st.header("Upload SOW (no staffing plan) → Recommendation")
        st.markdown("Upload a SOW without staffing information to get AI-powered recommendations based on similar historical SOWs.")
        
        # Initialize session state for this tab
        if 'uploaded_sow_data' not in st.session_state:
            st.session_state.uploaded_sow_data = None
        if 'similar_sows' not in st.session_state:
            st.session_state.similar_sows = []
        
        # File upload section
        uploaded_file = st.file_uploader(
            "Choose a SOW file (PDF or DOCX)",
            type=['pdf', 'docx'],
            help="Upload a SOW document to get recommendations based on similar historical projects",
            key="recommend_upload"
        )
        
        if uploaded_file is not None:
            # Process the uploaded file
            if st.button("Process & Extract Data", type="primary"):
                # Create progress indicators
                progress_bar = st.progress(0)
                status_text = st.text("Initializing...")
                
                # Process the file using existing extraction service
                with st.spinner("Processing SOW..."):
                    # Process without uploads for this tab
                    try:
                        # Save uploaded file temporarily
                        temp_path = Path("temp") / uploaded_file.name
                        temp_path.parent.mkdir(exist_ok=True)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        service = get_extraction_service()
                        if st.session_state.extraction_service is None:
                            st.session_state.extraction_service = service

                        def progress_callback(progress: ExtractionProgress):
                            progress_bar.progress(progress.percentage / 100)
                            status_text.text(f"{progress.stage}: {progress.message}")
                        service.set_progress_callback(progress_callback)

                        try:
                            result = asyncio.run(service.process_single_sow(temp_path, skip_uploads=True))
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(service.process_single_sow(temp_path, skip_uploads=True))
                            loop.close()
                    finally:
                        try:
                            temp_path.unlink()
                        except Exception:
                            pass
                
                if result and result.success:
                    st.success("SOW processed successfully!")
                    st.session_state.uploaded_sow_data = result.data
                    
                    # Display extracted data for review
                    st.subheader("Extracted SOW Data")
                    
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
                    
                    # Proceed to recommendations using the button in the Filter Options section below
                    st.markdown("---")
                
                else:
                    st.error("❌ Failed to process SOW")
                    if result:
                        st.error(f"Error: {result.error}")
        
        # Similar SOWs recommendation section
        if st.session_state.uploaded_sow_data:
            st.markdown("---")
            st.subheader("Similar Historical SOWs")
            
            # Filtering options
            with st.expander("Filter Options", expanded=False):
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
            
            # Action button: generate with current filters
            if st.button("Find Similar Historical SOWs", type="primary", key="find_similar_filtered"):
                with st.spinner("Finding similar historical SOWs..."):
                    try:
                        recs = generate_sow_recommendations(
                            st.session_state.uploaded_sow_data,
                            client_filter=selected_client_filter,
                            length_filter=selected_length_filter,
                            top=3
                        )
                        st.session_state.similar_sows = recs
                        st.success(f"✅ Found {len(recs)} similar historical SOWs")
                    except Exception as e:
                        st.error(f"❌ Failed to generate recommendations: {e}")
            
            # Display recommendations
            if st.session_state.similar_sows:
                st.markdown("---")
                st.subheader(f"Top {len(st.session_state.similar_sows)} Similar SOWs")
                
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
                        # Prefer structured plan hydrated from blob if available
                        staffing_plan = similar_sow.get('staffing_plan_structured') or similar_sow.get('staffing_plan', [])
                        # If not structured or missing, fetch from blob as a reliable source
                        if (not _looks_like_structured_staffing(staffing_plan)) and similar_sow.get('file_name'):
                            blob_plan = fetch_staffing_from_blob(similar_sow['file_name'])
                            if blob_plan:
                                staffing_plan = blob_plan
                        
                        if staffing_plan:
                            st.markdown("**Staffing Plan (Recommendation Source):**")
                            try:
                                # If structured dicts exist, show full schema columns
                                if isinstance(staffing_plan, list) and staffing_plan and isinstance(staffing_plan[0], dict):
                                    df = pd.DataFrame(staffing_plan)
                                    # Ensure preferred column order and presence
                                    preferred = ["name", "level", "title", "primary_role", "hours", "hours_pct"]
                                    for c in preferred:
                                        if c not in df.columns:
                                            df[c] = ''
                                    df = df[preferred]
                                    st.dataframe(df, use_container_width=True)
                                else:
                                    staffing_df = _normalize_staffing_plan_to_dataframe(staffing_plan)
                                    st.dataframe(staffing_df, use_container_width=True)
                            except Exception:
                                # Fallback to list rendering
                                for j, staff in enumerate(staffing_plan, 1):
                                    parsed = _parse_staffing_item_to_columns(staff)
                                    st.write(f"{j}. {parsed.get('name','')} - {parsed.get('title','')} {parsed.get('allocation','')}")
                        else:
                            st.info("No staffing plan available in this historical SOW")
        
        # Information section
        st.markdown("---")
        with st.expander("How Recommendations Work", expanded=False):
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
            
            **Staffing Data Normalization:**
            - All staffing allocations are automatically normalized to percentages
            - Hours are converted using 1800-hour annual basis (1800 hours = 100%)
            - Examples: 180 hours → 10.0%, 900 hours → 50.0%, 1800 hours → 100.0%
            - This ensures consistent comparison across all historical SOWs
            
            **Using Recommendations:**
            - Review the staffing plans from similar historical SOWs
            - Consider the similarity scores (higher = more relevant)
            - Adapt the recommended staffing to your specific project needs
            - Download individual recommendations for detailed review
            """)
    
    with tab3:
        st.header("Search Historical SOWs")
        st.markdown("Search through previously processed SOW documents using Azure Search.")
        
        # Initialize search service
        try:
            if st.session_state.search_service is None:
                st.session_state.search_service = get_search_service()
            
            search_service = st.session_state.search_service
            
            # Search interface
            search_col1, search_col2 = st.columns([2, 1])
            
            with search_col1:
                search_query = st.text_input(
                    "Search Query",
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
                "Search Method",
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
            search_button = st.button("Search", type="primary", use_container_width=True)
            
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
                        # Use service.search to enable hydration of structured staffing from blobs
                        results = hybrid_search_service.search(
                            query=search_query,
                            search_type="hybrid",
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
                                    'staffing_plan_structured': doc.get('staffing_plan_structured'),
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
                st.subheader(f"Search Results ({len(st.session_state.search_results)} found)")
                
                # Results summary
                result_summary = st.container()
                with result_summary:
                    st.success(f"✅ Found {len(st.session_state.search_results)} matching SOWs")
                
                # Display each result
                for i, result in enumerate(st.session_state.search_results):
                    # Create expander title with search strategy info
                    expander_title = f"{result['client_name']} - {result['project_title']}"
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
                        
                        # Full document content intentionally omitted to keep results concise
                        
                        # Deliverables with toggle (avoid nested expanders)
                        deliverables = result.get('deliverables', [])
                        if deliverables:
                            show_deliverables = st.checkbox(
                                "Show Deliverables",
                                value=False,
                                key=f"show_deliverables_{i}"
                            )
                            if show_deliverables:
                                for j, deliverable in enumerate(deliverables, 1):
                                    st.write(f"{j}. {deliverable}")
                        
                        # Staffing plan emphasized as table (fallback to blob if needed)
                        # Prefer structured plan hydrated from blob if available
                        staffing_plan = result.get('staffing_plan_structured') or result.get('staffing_plan', [])
                        # If not structured or missing, fetch from blob as a reliable source
                        if (not _looks_like_structured_staffing(staffing_plan)) and result.get('file_name'):
                            blob_plan = fetch_staffing_from_blob(result['file_name'])
                            if blob_plan:
                                staffing_plan = blob_plan
                        if staffing_plan:
                            try:
                                # If structured dicts exist, show full schema columns
                                if isinstance(staffing_plan, list) and staffing_plan and isinstance(staffing_plan[0], dict):
                                    st.markdown("**Staffing Plan:**")
                                    df = pd.DataFrame(staffing_plan)
                                    # Ensure preferred column order and presence
                                    preferred = ["name", "level", "title", "primary_role", "hours", "hours_pct"]
                                    for c in preferred:
                                        if c not in df.columns:
                                            df[c] = ''
                                    df = df[preferred]
                                    st.dataframe(df, use_container_width=True)
                                else:
                                    staffing_df = _normalize_staffing_plan_to_dataframe(staffing_plan)
                                    st.markdown("**Staffing Plan:**")
                                    st.dataframe(staffing_df, use_container_width=True)
                            except Exception:
                                # Fallback to list rendering
                                st.markdown("**Staffing Plan:**")
                                for j, staff in enumerate(staffing_plan, 1):
                                    parsed = _parse_staffing_item_to_columns(staff)
                                    st.write(f"{j}. {parsed.get('name','')} - {parsed.get('title','')} {parsed.get('allocation','')}")
                        
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
            with st.expander("About Search Methods", expanded=False):
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
