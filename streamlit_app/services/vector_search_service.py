#!/usr/bin/env python3
"""
Vector Search Service
====================

True semantic search using Azure Search vector capabilities.
This service provides:
- Vector search using embeddings
- Hybrid search (lexical + vector + semantic ranking)
- Semantic ranking for better relevance
"""

import os
import json
import requests
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv


class VectorSearchService:
    """True vector search service using Azure Search"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.openai_api_key = None
        self.openai_endpoint = None
        self.openai_deployment = None
        self.index_name = "octagon-sows-vector"
        self._load_environment()
    
    def _load_environment(self):
        """Load environment variables"""
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        self.search_endpoint = os.getenv('SEARCH_ENDPOINT')
        self.search_key = os.getenv('SEARCH_KEY')
        self.openai_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.openai_deployment = os.getenv('AOAI_DEPLOYMENT')
        
        if not all([self.search_endpoint, self.search_key, self.openai_api_key, 
                   self.openai_endpoint, self.openai_deployment]):
            raise ValueError("Missing required environment variables")
        
        # Remove trailing slash if present
        self.search_endpoint = self.search_endpoint.rstrip('/')
    
    async def get_query_embedding(self, query: str) -> List[float]:
        """Get vector embedding for search query"""
        try:
            url = f"{self.openai_endpoint}openai/deployments/{self.openai_deployment}/embeddings?api-version=2024-08-01-preview"
            headers = {
                'api-key': self.openai_api_key,
                'Content-Type': 'application/json'
            }
            data = {
                'input': query
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['data'][0]['embedding']
                    else:
                        error_text = await response.text()
                        print(f"❌ Error getting query embedding: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"❌ Error getting query embedding: {e}")
            return None
    
    def vector_search(
        self, 
        query: str, 
        vector_field: str = "content_vector",
        top: int = 10,
        skip: int = 0,
        filter_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform pure vector search using embeddings"""
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Get query embedding
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_query_embedding(query))
                    query_embedding = future.result()
            else:
                query_embedding = asyncio.run(self.get_query_embedding(query))
        except:
            # Fallback: run in new event loop
            query_embedding = asyncio.run(self.get_query_embedding(query))
            
        if not query_embedding:
            return {"error": "Failed to get query embedding"}
        
        payload = {
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": query_embedding,
                    "k": top,
                    "fields": vector_field
                }
            ],
            "select": "*",
            "top": top,
            "skip": skip
        }
        
        if filter_expression:
            payload["filter"] = filter_expression
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                # Add search strategy info to results
                for doc in result.get('value', []):
                    doc['search_strategy'] = 'vector_search'
                    doc['strategy_score'] = doc.get('@search.score', 0.0)
                return result
            else:
                return {"error": f"Search failed: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"Search failed: {e}"}
    
    def hybrid_search(
        self, 
        query: str, 
        top: int = 10,
        skip: int = 0,
        filter_expression: Optional[str] = None,
        vector_weight: float = 0.7,
        lexical_weight: float = 0.3
    ) -> Dict[str, Any]:
        """Perform hybrid search combining lexical and vector search"""
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Get query embedding
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_query_embedding(query))
                    query_embedding = future.result()
            else:
                query_embedding = asyncio.run(self.get_query_embedding(query))
        except:
            # Fallback: run in new event loop
            query_embedding = asyncio.run(self.get_query_embedding(query))
            
        if not query_embedding:
            return {"error": "Failed to get query embedding"}
        
        payload = {
            "search": query,
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": query_embedding,
                    "k": top,
                    "fields": "content_vector"
                }
            ],
            "select": "*",
            "top": top,
            "skip": skip,
            "queryType": "semantic",
            "semanticConfiguration": "default",
            "captions": "extractive",
            "answers": "extractive",
            "searchFields": [
                "client_name",
                "project_title", 
                "scope_summary",
                "deliverables",
                "staffing_plan"
            ]
        }
        
        if filter_expression:
            payload["filter"] = filter_expression
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                # Add search strategy info to results
                for doc in result.get('value', []):
                    doc['search_strategy'] = 'hybrid_search'
                    doc['strategy_score'] = doc.get('@search.score', 0.0)
                return result
            else:
                return {"error": f"Search failed: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"Search failed: {e}"}
    
    def semantic_search(
        self, 
        query: str, 
        top: int = 10,
        skip: int = 0,
        filter_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform semantic search with ranking"""
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        payload = {
            "search": query,
            "select": "*",
            "top": top,
            "skip": skip,
            "queryType": "semantic",
            "semanticConfiguration": "default",
            "captions": "extractive",
            "answers": "extractive",
            "searchFields": [
                "client_name",
                "project_title", 
                "scope_summary",
                "deliverables",
                "staffing_plan"
            ]
        }
        
        if filter_expression:
            payload["filter"] = filter_expression
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                # Add search strategy info to results
                for doc in result.get('value', []):
                    doc['search_strategy'] = 'semantic_search'
                    doc['strategy_score'] = doc.get('@search.score', 0.0)
                return result
            else:
                return {"error": f"Search failed: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"Search failed: {e}"}
    
    def search(
        self, 
        query: str, 
        search_type: str = "hybrid",
        top: int = 10,
        skip: int = 0,
        filter_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Main search method with different search types"""
        if search_type == "vector":
            return self.vector_search(query, top=top, skip=skip, filter_expression=filter_expression)
        elif search_type == "hybrid":
            return self.hybrid_search(query, top=top, skip=skip, filter_expression=filter_expression)
        elif search_type == "semantic":
            return self.semantic_search(query, top=top, skip=skip, filter_expression=filter_expression)
        else:
            return {"error": f"Unknown search type: {search_type}"}


def get_vector_search_service() -> VectorSearchService:
    """Get an instance of the vector search service"""
    return VectorSearchService()


# Test function
async def test_vector_search():
    """Test the vector search service"""
    print("🔍 Testing Vector Search Service")
    print("=" * 50)
    
    try:
        service = get_vector_search_service()
        
        # Test queries
        test_queries = [
            "augusta masters golf",
            "golf related events",
            "august tournament",
            "hospitality programs",
            "sponsorship events"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing: '{query}'")
            print("-" * 40)
            
            # Test hybrid search
            results = service.search(query, search_type="hybrid", top=3)
            if results and results.get('value'):
                print(f"✅ Hybrid search found {len(results['value'])} results:")
                for i, doc in enumerate(results['value'], 1):
                    strategy = doc.get('search_strategy', 'unknown')
                    score = doc.get('strategy_score', 0.0)
                    print(f"   {i}. {doc.get('client_name', 'Unknown')} - {doc.get('project_title', 'No title')}")
                    print(f"      Strategy: {strategy} (score: {score:.2f})")
            else:
                print("   ❌ No results found")
                if 'error' in results:
                    print(f"   Error: {results['error']}")
        
        print("\n🎉 Vector search test completed!")
        
    except Exception as e:
        print(f"❌ Error testing vector search: {e}")


if __name__ == "__main__":
    asyncio.run(test_vector_search())
