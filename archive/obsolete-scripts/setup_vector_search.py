#!/usr/bin/env python3
"""
Setup script for Azure AI Search vector database.

This script helps set up the necessary Azure resources and environment variables
for the vector search functionality.

Usage:
    python setup_vector_search.py
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from app.services.vector_indexer import VectorIndexer, VectorIndexerError


def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY", 
        "AZURE_OPENAI_DEPLOYMENT",
        "SEARCH_ENDPOINT",
        "SEARCH_KEY",
        "STORAGE_BLOB_ENDPOINT"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        return False
    
    print("✅ All required environment variables are set")
    return True


def create_sample_env():
    """Create a sample .env file with the required variables."""
    env_content = """# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Azure AI Search Configuration
SEARCH_ENDPOINT=https://your-search-service.search.windows.net
SEARCH_KEY=your-search-key
SEARCH_INDEX_NAME=octagon-sows

# Azure Storage Configuration
STORAGE_BLOB_ENDPOINT=https://yourstorageaccount.blob.core.windows.net/

# Application Configuration
ENVIRONMENT=dev
LOG_LEVEL=INFO
"""
    
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️ .env file already exists. Not overwriting.")
        return
    
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print("✅ Created sample .env file. Please update with your actual values.")


async def test_vector_search():
    """Test the vector search functionality."""
    try:
        print("Testing vector search setup...")
        
        # Test indexer initialization
        indexer = VectorIndexer()
        print("✅ Vector indexer initialized successfully")
        
        # Test index creation
        print("Creating search index...")
        await indexer.create_index()
        print("✅ Search index created successfully")
        
        # Test index statistics
        stats = await indexer.get_index_statistics()
        print(f"✅ Index statistics retrieved: {stats}")
        
        return True
        
    except VectorIndexerError as e:
        print(f"❌ Vector search test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during test: {e}")
        return False


def main():
    print("🚀 Azure AI Search Vector Database Setup")
    print("=" * 50)
    
    # Check environment variables
    if not check_environment():
        print("\n📝 Creating sample .env file...")
        create_sample_env()
        print("\nPlease update the .env file with your actual Azure resource values and run this script again.")
        return
    
    # Test vector search functionality
    import asyncio
    print("\n🧪 Testing vector search functionality...")
    success = asyncio.run(test_vector_search())
    
    if success:
        print("\n🎉 Vector search setup completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python index_sows_vector.py --create-index' to create the search index")
        print("2. Run 'python index_sows_vector.py' to index all existing SOW documents")
        print("3. Run 'streamlit run streamlit_app.py' to use the enhanced app with vector search")
    else:
        print("\n❌ Vector search setup failed. Please check your configuration.")


if __name__ == "__main__":
    main()
