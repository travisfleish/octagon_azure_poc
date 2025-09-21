# Octagon Staffing Plan Generator

A comprehensive system for processing Statement of Work (SOW) documents, extracting structured data using AI, and providing vector search capabilities for finding similar projects and staffing plans.

## Project Structure

### Core Application
- `octagon-staffing-app/` - FastAPI application with Azure services integration
- `streamlit_app.py` - Main Streamlit interface for document processing and search
- `setup_octagon_azure.py` - Azure infrastructure setup script

### Active Scripts
- `process_one_sow.py` - Document processing pipeline
- `llm_extract.py` - LLM-based data extraction
- `enhanced_vector_search.py` - Vector search service
- `index_sows_vector.py` - Vector indexing for search

### Documentation
- `VECTOR_SEARCH_README.md` - Detailed vector search documentation
- `requirements.txt` - Python dependencies

### Sample Data
- `sows/` - Sample SOW documents for testing

### Archived Files
- `archive/obsolete-scripts/` - Superseded scripts (kept for reference)
- `archive/test-scripts/` - Development and testing utilities
- `archive/sample-files/` - Test documents and sample files

## Quick Start

1. **Setup Azure Infrastructure**
   ```bash
   python setup_octagon_azure.py
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r octagon-staffing-app/requirements.txt
   ```

3. **Create Vector Search Index**
   ```bash
   python index_sows_vector.py --create-index
   ```

4. **Index Existing Documents**
   ```bash
   python index_sows_vector.py
   ```

5. **Run Streamlit Application**
   ```bash
   streamlit run streamlit_app.py
   ```

## Features

- **Document Processing**: Upload and process PDF/DOCX SOW documents
- **AI Extraction**: Extract structured data using Azure OpenAI
- **Vector Search**: Semantic search across processed documents
- **Staffing Plans**: Generate and compare staffing recommendations
- **Azure Integration**: Full Azure services integration (Storage, AI, Search)

## Architecture

The system uses a three-tier architecture:
1. **Document Processing**: Azure Document Intelligence + custom text extraction
2. **AI Processing**: Azure OpenAI for structured data extraction
3. **Search & Storage**: Azure AI Search with vector embeddings + Azure Blob Storage

For detailed information, see `VECTOR_SEARCH_README.md`.
