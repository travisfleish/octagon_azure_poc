# Vector Search for SOW Documents

This implementation adds vector search capabilities to the Octagon SOW Parser, allowing for semantic similarity search across both full document text and structured parsed data.

## Features

- **Vector Database**: Azure AI Search with vector search capabilities
- **Dual Embeddings**: Separate embeddings for full text content and structured data
- **Hybrid Search**: Combines text search with vector similarity
- **Semantic Search**: Find similar SOWs based on meaning, not just keywords
- **Filtering**: Filter results by company, document type, etc.
- **Streamlit UI**: Enhanced web interface with search capabilities

## Architecture

```
SOW Documents → Text Extraction → LLM Parsing → Vector Embeddings → Azure AI Search
                     ↓                ↓              ↓
              Full Text Content  Structured Data  Vector Database
                     ↓                ↓              ↓
              Content Vector    Structured Vector  Search Index
```

## Components

### 1. Vector Service (`app/services/vector_service.py`)
- Manages Azure AI Search index operations
- Handles vector search queries
- Supports hybrid search (text + vector)

### 2. Embedding Service (`app/services/embedding_service.py`)
- Generates embeddings using Azure OpenAI
- Creates dual embeddings for content and structured data
- Prepares text for optimal embedding generation

### 3. Vector Indexer (`app/services/vector_indexer.py`)
- Orchestrates the indexing process
- Processes documents and generates vectors
- Provides search functionality

### 4. Enhanced Streamlit App (`streamlit_app.py`)
- Three-tab interface: Upload & Parse, Vector Search, Index Management
- Real-time search with filtering options
- Index management and statistics

## Setup

### Prerequisites

1. **Azure AI Search Service**
   - Create an Azure AI Search service
   - Note the endpoint and admin key

2. **Azure OpenAI Service**
   - Deploy `text-embedding-3-small` model
   - Note the endpoint, API key, and deployment name

3. **Environment Variables**
   ```bash
   # Azure OpenAI
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your-api-key
   AZURE_OPENAI_DEPLOYMENT=text-embedding-3-small
   AZURE_OPENAI_API_VERSION=2024-08-01-preview

   # Azure AI Search
   SEARCH_ENDPOINT=https://your-search-service.search.windows.net
   SEARCH_KEY=your-search-key
   SEARCH_INDEX_NAME=octagon-sows

   # Azure Storage
   STORAGE_BLOB_ENDPOINT=https://yourstorageaccount.blob.core.windows.net/
   ```

### Installation

1. **Install Dependencies**
   ```bash
   pip install -r octagon-staffing-app/requirements.txt
   ```

2. **Setup Vector Search**
   ```bash
   python setup_vector_search.py
   ```

3. **Create Search Index**
   ```bash
   python index_sows_vector.py --create-index
   ```

4. **Index Existing Documents**
   ```bash
   python index_sows_vector.py
   ```

5. **Run Enhanced App**
   ```bash
   streamlit run streamlit_app.py
   ```

## Usage

### Vector Search Tab

1. **Search Query**: Enter a natural language query
   - Example: "project management roles with 6 month duration"
   - Example: "data analysis deliverables for healthcare"

2. **Search Type**:
   - **Hybrid**: Combines text search with vector similarity
   - **Vector Only**: Pure semantic similarity search

3. **Company Filter**: Filter results by specific company

4. **Results**: View similar documents with:
   - Relevance score
   - Company and SOW ID
   - Scope bullets and deliverables
   - Required roles

### Index Management Tab

1. **Create Index**: Set up the search index schema
2. **Index All Documents**: Process all SOWs in the source container
3. **Show Statistics**: View index metrics and document counts

## Search Index Schema

The vector search index includes:

### Text Fields
- `full_text`: Complete document content
- `scope_bullets`: Array of scope items
- `deliverables`: Array of deliverables
- `roles_detected`: Array of detected roles
- `assumptions`: Array of assumptions

### Vector Fields
- `content_vector`: Embedding of full text + structured data
- `structured_vector`: Embedding of structured data only

### Metadata Fields
- `blob_name`, `company`, `sow_id`, `format`
- `term_start`, `term_end`, `term_months`
- `explicit_hours`, `fte_pct`
- `has_llm_parsing`, `text_length`

## API Usage

### Search Similar Documents
```python
from app.services.vector_indexer import VectorIndexer

indexer = VectorIndexer()

# Vector search
results = await indexer.search_similar_documents(
    query="project management roles",
    top_k=5,
    company_filter="Company 1"
)

# Hybrid search
results = await indexer.hybrid_search_documents(
    query="data analysis deliverables",
    top_k=10
)
```

### Index Single Document
```python
# Index a specific document
result = await indexer.index_single_document("company_1_sow_1.pdf")
```

### Batch Index All Documents
```python
# Index all documents
results = await indexer.index_all_documents()
```

## Command Line Tools

### Index Management
```bash
# Create index
python index_sows_vector.py --create-index

# Index all documents
python index_sows_vector.py

# Index specific document
python index_sows_vector.py --blob-name "company_1_sow_1.pdf"

# Show statistics
python index_sows_vector.py --stats
```

### Setup and Testing
```bash
# Setup vector search
python setup_vector_search.py

# Test configuration
python setup_vector_search.py
```

## Performance Considerations

### Embedding Generation
- Uses `text-embedding-3-small` for cost efficiency
- 1536-dimensional vectors
- Batch processing for multiple documents

### Search Performance
- HNSW algorithm for fast approximate nearest neighbor search
- Cosine similarity for vector comparison
- Configurable result limits and filters

### Index Size
- Typical document: ~1-5KB of vector data
- 1000 documents ≈ 1.5-7.5MB vector index
- Azure AI Search handles scaling automatically

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   ```bash
   python setup_vector_search.py
   ```

2. **Index Creation Fails**
   - Check Azure AI Search permissions
   - Verify search service is active
   - Ensure unique index name

3. **Embedding Generation Fails**
   - Verify Azure OpenAI deployment
   - Check API key and endpoint
   - Ensure text-embedding-3-small is deployed

4. **Search Returns No Results**
   - Check if documents are indexed
   - Verify search query format
   - Check company filter settings

### Debug Commands

```bash
# Check index statistics
python index_sows_vector.py --stats

# Test single document
python index_sows_vector.py --blob-name "test_document.pdf"

# Verify environment
python setup_vector_search.py
```

## Cost Optimization

### Embedding Costs
- Uses `text-embedding-3-small` (cheapest model)
- Batch processing reduces API calls
- Caches embeddings in search index

### Search Costs
- Azure AI Search charges per search operation
- Vector search is more expensive than text search
- Consider hybrid search for cost/quality balance

### Storage Costs
- Vector data is stored in Azure AI Search
- No additional blob storage for vectors
- Index size scales with document count

## Future Enhancements

1. **Advanced Filtering**: Date ranges, role types, budget ranges
2. **Query Expansion**: Automatic query enhancement
3. **Result Ranking**: Custom scoring algorithms
4. **Analytics**: Search analytics and insights
5. **Real-time Updates**: Automatic re-indexing on document changes
