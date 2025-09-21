# Obsolete Scripts

This directory contains scripts that have been superseded by newer implementations or are no longer needed for the main application.

## Duplicate Vector Search Scripts
- `simple_vector_search.py` - Superseded by `enhanced_vector_search.py`
- `simple_vector_index.py` - Superseded by `index_sows_vector.py`
- `minimal_vector_index.py` - Superseded by `index_sows_vector.py`
- `simple_text_index.py` - Superseded by `index_sows_vector.py`
- `simple_working_index.py` - Development artifact

## Obsolete Processing Scripts
- `extract_sows.py` - Superseded by `process_one_sow.py`
- `label_sows.py` - One-time tagging script, no longer needed
- `setup_vector_search.py` - Superseded by `index_sows_vector.py`

## Current Active Scripts
The following scripts are still in use and should remain in the root directory:
- `process_one_sow.py` - Used by streamlit_app.py
- `llm_extract.py` - Used by process_one_sow.py
- `enhanced_vector_search.py` - Used by streamlit_app.py
- `index_sows_vector.py` - Main vector indexing script
