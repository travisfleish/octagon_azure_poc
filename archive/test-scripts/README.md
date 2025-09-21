# Test Scripts

This directory contains test and debug scripts that are useful for development and troubleshooting but not needed for production.

## Test Scripts
- `simple_query_test.py` - Basic vector search testing (superseded by query_vector_index.py)
- `query_vector_index.py` - Comprehensive vector search testing
- `test_openai_api` - Simple Azure OpenAI connection test
- `verify_azure.py` - Azure Storage connection verification

## Usage
These scripts can be run for testing and debugging purposes:
```bash
# Test Azure OpenAI connection
python test_openai_api

# Test Azure Storage connection
python verify_azure.py

# Test vector search functionality
python query_vector_index.py
```

## Note
These are development/testing tools and are not part of the main application workflow.
