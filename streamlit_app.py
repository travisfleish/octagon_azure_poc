import io
import json
import re
import zipfile
import sys
import asyncio
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Add the app directory to the Python path for vector services
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from process_one_sow import extract_docx_text, extract_pdf_text, parse_fields_deterministic, process_blob
from enhanced_vector_search import EnhancedVectorSearch, run_async


ACCOUNT_URL = "https://octagonstaffingstg5nww.blob.core.windows.net/"
SRC_CONTAINER = "sows"
EXTRACTED_CONTAINER = "extracted"
PARSED_CONTAINER = "parsed"


def init_clients():
    cred = DefaultAzureCredential()
    svc = BlobServiceClient(account_url=ACCOUNT_URL, credential=cred)
    return (
        svc.get_container_client(SRC_CONTAINER),
        svc.get_container_client(EXTRACTED_CONTAINER),
        svc.get_container_client(PARSED_CONTAINER),
    )


# run_async is now imported from simple_vector_search

def index_document_for_search(blob_name, company, sow_id, full_text, structured_text):
    """Index a document for vector search using the existing enhanced_vector_search service"""
    try:
        # Create a simple document structure for indexing
        doc_data = {
            'blob_name': blob_name,
            'company': company,
            'sow_id': sow_id,
            'full_text': full_text,
            'structured_text': structured_text
        }
        
        # Use the existing vector search service to index
        vector_search = EnhancedVectorSearch()
        
        # Index the document using the new method
        result = run_async(vector_search.index_document(doc_data))
        return result
        
    except Exception as e:
        st.error(f"Indexing error: {e}")
        return False

def generate_sow_summary(text: str, query: str) -> str:
    """Generate a concise AI summary of the SOW based on the search query."""
    # Extract key information from the SOW text
    lines = text.split('\n')
    
    # Find key sections
    project_title = ""
    term_info = ""
    description = ""
    deliverables = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Look for project title
        if "project:" in line.lower() or "title of project:" in line.lower():
            project_title = line
            # Get next few lines for more context
            for j in range(i+1, min(i+3, len(lines))):
                if lines[j].strip():
                    project_title += " " + lines[j].strip()
            break
    
    # Look for term information
    for line in lines:
        if "term of project:" in line.lower() or "start date:" in line.lower():
            term_info = line
            break
    
    # Look for description
    for i, line in enumerate(lines):
        if "description:" in line.lower() or "scope of work:" in line.lower():
            description = line
            # Get next few lines
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip() and len(lines[j].strip()) > 10:
                    description += " " + lines[j].strip()
            break
    
    # Look for deliverables
    for i, line in enumerate(lines):
        if "deliverables:" in line.lower():
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip().startswith('•') or lines[j].strip().startswith('-'):
                    deliverables.append(lines[j].strip())
                elif lines[j].strip() and not lines[j].strip().startswith(('project', 'term', 'fee', 'agreement')):
                    deliverables.append(lines[j].strip())
                if len(deliverables) >= 5:
                    break
            break
    
    # Generate summary
    summary_parts = []
    
    if project_title:
        summary_parts.append(f"**Project:** {project_title}")
    
    if term_info:
        summary_parts.append(f"**Term:** {term_info}")
    
    if description:
        # Truncate description if too long
        if len(description) > 300:
            description = description[:300] + "..."
        summary_parts.append(f"**Description:** {description}")
    
    if deliverables:
        summary_parts.append("**Key Deliverables:**")
        for deliverable in deliverables[:5]:  # Limit to 5 deliverables
            summary_parts.append(f"• {deliverable}")
    
    # If no structured info found, create a general summary
    if not summary_parts:
        # Extract first few sentences as summary
        sentences = text.split('.')
        summary_text = '. '.join(sentences[:3]) + '.'
        if len(summary_text) > 200:
            summary_text = summary_text[:200] + "..."
        summary_parts.append(f"**Summary:** {summary_text}")
    
    return '\n\n'.join(summary_parts)

st.set_page_config(page_title="Octagon SOW Parser", page_icon="📄", layout="centered")
st.title("📄 Octagon SOW Parser")
st.caption("Upload a SOW file (.pdf or .docx). It will be uploaded to Azure Blob Storage, extracted, parsed with LLM, and results displayed.")

# Add tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["📤 Upload & Parse", "🔍 Vector Search", "📊 Index Management"])

with tab1:
    st.header("Upload & Parse SOW Documents")
    st.caption("Upload documents to be processed, parsed, and automatically indexed for search")
    
    uploaded = st.file_uploader("Choose a PDF or DOCX", type=["pdf", "docx"], accept_multiple_files=True)

if uploaded is not None:
        # Handle both single file and multiple files
        files_to_process = uploaded if isinstance(uploaded, list) else [uploaded]
        
        st.write(f"📁 {len(files_to_process)} file(s) selected for processing")
        
        if st.button("🚀 Process & Index Documents", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            successful_uploads = 0
            successful_indexes = 0
            
            # Initialize vector search for indexing
            vector_search = EnhancedVectorSearch()
            
            for i, uploaded_file in enumerate(files_to_process):
                try:
                    # Update progress
                    progress = (i + 1) / len(files_to_process)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {uploaded_file.name}...")
                    
                    file_bytes = uploaded_file.read()
                    blob_name = uploaded_file.name

                    st.write(f"📤 Uploading {blob_name} to Azure Blob Storage…")
                    src, extracted, parsed = init_clients()

                    # Upload original file to sows/
                    src.upload_blob(name=blob_name, data=file_bytes, overwrite=True)
                    st.success(f"✅ Uploaded {blob_name} to container '{SRC_CONTAINER}'")

                    with st.spinner(f"🔍 Extracting and parsing {blob_name} with LLM…"):
                        result_row = process_blob(src, extracted, parsed, blob_name)

                    st.success(f"✅ {blob_name} - Extraction and parsing complete!")
                    successful_uploads += 1
                    
                    # Index the document for vector search
                    try:
                        status_text.text(f"🔍 Indexing {blob_name} for search...")
                        
                        # Get the extracted text for indexing
                        stem = blob_name.rsplit(".", 1)[0]
                        extracted_blob_name = f"{stem}.txt"
                        
                        # Download the extracted text
                        extracted_client = src.get_container_client(EXTRACTED_CONTAINER)
                        extracted_text = extracted_client.download_blob(extracted_blob_name).readall().decode("utf-8")
                        
                        # Get the parsed JSON for structured data
                        parsed_client = src.get_container_client(PARSED_CONTAINER)
                        parsed_json = json.loads(parsed_client.download_blob(f"{stem}.json").readall().decode("utf-8"))
                        
                        # Create document for indexing
                        doc_data = {
                            'blob_name': extracted_blob_name,
                            'company': parsed_json.get('company', 'Unknown'),
                            'sow_id': parsed_json.get('sow_id', 'Unknown'),
                            'full_text': extracted_text,
                            'structured_text': json.dumps(parsed_json)
                        }
                        
                        # Index the document
                        st.info(f"📊 Indexing data: Company={doc_data['company']}, SOW ID={doc_data['sow_id']}")
                        index_result = run_async(vector_search.index_document(doc_data))
                        
                        if index_result:
                            successful_indexes += 1
                            st.success(f"🎉 {blob_name} - Successfully uploaded, parsed, and indexed for search!")
                        else:
                            st.warning(f"⚠️ {blob_name} - Uploaded and parsed, but indexing failed")
                            
                    except Exception as index_error:
                        st.warning(f"⚠️ {blob_name} - Uploaded and parsed, but indexing failed: {index_error}")

                    # Show results for this file
                    with st.expander(f"📄 Results for {blob_name}"):
                        st.subheader("Parsed Data")
                        st.json(result_row)
                        
                        # Show full parsed JSON
                        try:
                            parsed_json = json.loads(parsed_client.download_blob(f"{stem}.json").readall().decode("utf-8"))
                            st.subheader("Full Parsed JSON")
                            st.json(parsed_json)
                        except Exception as e:
                            st.warning(f"Could not fetch parsed JSON from storage: {e}")

                except Exception as e:
                    st.error(f"❌ Failed to process {uploaded_file.name}: {e}")
                    continue
            
            # Final status
            progress_bar.progress(1.0)
            status_text.text("Processing complete!")
            
            st.success(f"🎉 Successfully processed {successful_uploads} documents and indexed {successful_indexes} for search!")
            
            if successful_indexes > 0:
                st.info("💡 New documents are now searchable in the Vector Search tab!")
            
            # Clear the file uploader
            st.rerun()

with tab2:
    st.header("Vector Search")
    st.caption("Search for similar SOW documents using semantic similarity")
    
    # Initialize the enhanced vector search service
    vector_search = EnhancedVectorSearch()
    
    # Get available companies dynamically
    available_companies = run_async(vector_search.get_available_companies())
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input("Search query", placeholder="e.g., 'project management roles with 6 month duration'")
    
    with col2:
        search_type = st.selectbox("Search type", ["Vector", "Hybrid", "Text"])
    
    company_filter = st.selectbox("Filter by company (optional)", available_companies)
    
    if st.button("Search", type="primary"):
        if search_query:
            try:
                with st.spinner("Searching..."):
                    # Apply company filter
                    company = None if company_filter == "All" else company_filter
                    
                    results = run_async(vector_search.search_similar_documents_with_staffing(
                        query_text=search_query,
                        top_k=10,
                        search_type=search_type.lower(),
                        company_filter=company
                    ))
                
                if results:
                    st.success(f"Found {len(results)} similar documents")
                    
                    for i, result in enumerate(results, 1):
                        with st.expander(f"{i}. {result.get('blob_name', 'Unknown')} (Score: {result.get('score', 'N/A')})"):
                            st.write(f"**Company:** {result.get('company', 'N/A')}")
                            st.write(f"**SOW ID:** {result.get('sow_id', 'N/A')}")
                            
                            # Show AI summary of the SOW
                            full_text = result.get('full_text', '')
                            if full_text:
                                st.write("### 📋 SOW Summary")
                                # Generate a concise AI summary of the SOW
                                summary = generate_sow_summary(full_text, search_query)
                                st.write(summary)
                            
                            # Show staffing plan information
                            staffing_plan = result.get('staffing_plan', {})
                            if staffing_plan and not staffing_plan.get('error'):
                                st.write("### 👥 Staffing Plan")
                                
                                # Display structured staffing table
                                if staffing_plan.get('structured_staffing'):
                                    # Create a proper table with headers
                                    table_data = []
                                    for staff in staffing_plan['structured_staffing'][:10]:  # Limit to 10 staff
                                        table_data.append([
                                            staff['name'],
                                            staff['role'],
                                            staff['primary_role'],
                                            staff['percentage'],
                                            staff['location']
                                        ])
                                    
                                    if table_data:
                                        # Create a DataFrame for better table display
                                        df = pd.DataFrame(table_data, columns=['Name', 'Role', 'Primary Role', '%', 'Location'])
                                        st.table(df)
                                else:
                                    st.info("No structured staffing table found")
                            elif staffing_plan.get('error'):
                                st.warning(f"⚠️ Could not extract staffing plan: {staffing_plan['error']}")
                            else:
                                st.info("ℹ️ No staffing plan information found")
                else:
                    st.info("No similar documents found")
                    
            except Exception as e:
                st.error(f"Search failed: {e}")
        else:
            st.warning("Please enter a search query")

with tab3:
    st.header("Index Management")
    st.caption("Manage the vector search index")
    
    # Initialize the enhanced vector search service
    vector_search = EnhancedVectorSearch()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Show Statistics", type="primary"):
            try:
                with st.spinner("Getting statistics..."):
                    stats = run_async(vector_search.get_index_stats())
                
                st.metric("Document Count", stats.get('document_count', 'N/A'))
                st.metric("Index Name", stats.get('index_name', 'N/A'))
                st.success("✅ Vector search index is working!")
            except Exception as e:
                st.error(f"Failed to get statistics: {e}")
    
    with col2:
        if st.button("Test Search"):
            try:
                with st.spinner("Testing search..."):
                    results = run_async(vector_search.search_similar_documents(
                        query_text="project management",
                        top_k=3,
                        search_type="vector"
                    ))
                
                if results:
                    st.success(f"✅ Search working! Found {len(results)} results")
                    for i, result in enumerate(results, 1):
                        st.write(f"{i}. {result['blob_name']} ({result['company']})")
                        
                        # Show staffing plan preview
                        staffing_plan = result.get('staffing_plan', {})
                        if staffing_plan and not staffing_plan.get('error'):
                            if staffing_plan.get('roles'):
                                st.write(f"   👥 Roles: {', '.join(staffing_plan['roles'][:3])}")
                            if staffing_plan.get('hours'):
                                total_hours = sum(staffing_plan['hours'])
                                st.write(f"   ⏱️ Total Hours: {total_hours}")
                else:
                    st.warning("No results found")
            except Exception as e:
                st.error(f"Search test failed: {e}")
    
    with col3:
        if st.button("List Companies"):
            try:
                with st.spinner("Getting companies..."):
                    companies = run_async(vector_search.get_available_companies())
                
                st.write("**Available Companies:**")
                for company in companies:
                    st.write(f"• {company}")
            except Exception as e:
                st.error(f"Failed to get companies: {e}")

st.divider()
st.caption("✅ Vector search is working with the 'octagon-sows-text-only' index")


