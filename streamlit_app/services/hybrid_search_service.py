#!/usr/bin/env python3
"""
Hybrid Search Service
====================

Combines full text and parsed data vector search for comprehensive results.
This service provides:
- Full text vector search using raw document content
- Parsed data vector search using structured fields
- Hybrid ranking that combines both approaches
- Multiple vector field search capabilities
"""

import os
import json
import requests
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential
from azure.storage.blob import BlobServiceClient as SyncBlobServiceClient


class HybridSearchService:
    """Hybrid search service using both full text and parsed data vectors"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.openai_api_key = None
        self.openai_endpoint = None
        self.openai_deployment = None
        self.index_name = "octagon-sows-hybrid"
        self._load_environment()
        self._blob_client = None
    
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
        self.storage_account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        
        if not all([self.search_endpoint, self.search_key, self.openai_api_key, 
                   self.openai_endpoint, self.openai_deployment]):
            raise ValueError("Missing required environment variables")
        
        # Remove trailing slash if present
        self.search_endpoint = self.search_endpoint.rstrip('/')

    async def _ensure_blob_client(self):
        if self._blob_client is None and self.storage_account_url:
            cred = DefaultAzureCredential()
            self._blob_client = BlobServiceClient(account_url=self.storage_account_url, credential=cred)

    async def _download_parsed_json(self, file_name: str) -> Optional[Dict[str, Any]]:
        try:
            await self._ensure_blob_client()
            if not self._blob_client:
                return None
            base = file_name.replace('.pdf', '').replace('.docx', '')
            blob_name = f"{base}_parsed.json"
            bc = self._blob_client.get_blob_client(container="parsed", blob=blob_name)
            data = await bc.download_blob()
            content = await data.readall()
            return json.loads(content.decode('utf-8'))
        except Exception:
            return None

    def _hydrate_structured_staffing(self, docs: List[Dict[str, Any]]):
        """Attach structured staffing from parsed blobs to result docs.
        Uses synchronous blob download to avoid asyncio event loop conflicts in Streamlit.
        """
        try:
            # Initialize synchronous blob client
            if not hasattr(self, '_sync_blob_client') and self.storage_account_url:
                cred = SyncDefaultAzureCredential()
                self._sync_blob_client = SyncBlobServiceClient(account_url=self.storage_account_url, credential=cred)
            
            if not self._sync_blob_client:
                return
                
            for d in docs:
                fn = (d.get('file_name') or d.get('id') or '').strip()
                if not fn:
                    continue
                
                try:
                    # Use synchronous blob download
                    base = fn.replace('.pdf', '').replace('.docx', '')
                    blob_name = f"{base}_parsed.json"
                    blob_client = self._sync_blob_client.get_blob_client(container="parsed", blob=blob_name)
                    
                    # Download blob content synchronously
                    blob_data = blob_client.download_blob()
                    content = blob_data.readall()
                    parsed = json.loads(content.decode('utf-8'))
                    
                    if isinstance(parsed, dict) and isinstance(parsed.get('staffing_plan'), list):
                        d['staffing_plan_structured'] = parsed['staffing_plan']
                except Exception:
                    # If blob download fails, continue without structured data
                    continue
        except Exception:
            # If blob client initialization fails, continue without hydration
            pass
    
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
    
    def hybrid_vector_search(
        self, 
        query: str, 
        top: int = 10,
        skip: int = 0,
        filter_expression: Optional[str] = None,
        full_text_weight: float = 0.6,
        parsed_weight: float = 0.4
    ) -> Dict[str, Any]:
        """Perform hybrid vector search by combining individual vector searches"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_query_embedding(query))
                    query_embedding = future.result()
            else:
                query_embedding = asyncio.run(self.get_query_embedding(query))
        except:
            query_embedding = asyncio.run(self.get_query_embedding(query))
            
        if not query_embedding:
            return {"error": "Failed to get query embedding"}
        
        # Get results from both individual searches
        full_text_results = self.full_text_vector_search(query, top=top*2, skip=skip, filter_expression=filter_expression)
        parsed_results = self.parsed_data_vector_search(query, top=top*2, skip=skip, filter_expression=filter_expression)
        
        # Combine and deduplicate results
        all_results = []
        seen_ids = set()
        
        # Add full text results with weight
        if full_text_results and 'value' in full_text_results:
            for doc in full_text_results['value']:
                if doc['id'] not in seen_ids:
                    doc['search_strategy'] = 'hybrid_full_text'
                    doc['strategy_score'] = doc.get('@search.score', 0.0) * full_text_weight
                    all_results.append(doc)
                    seen_ids.add(doc['id'])
        
        # Add parsed results with weight
        if parsed_results and 'value' in parsed_results:
            for doc in parsed_results['value']:
                if doc['id'] not in seen_ids:
                    doc['search_strategy'] = 'hybrid_parsed'
                    doc['strategy_score'] = doc.get('@search.score', 0.0) * parsed_weight
                    all_results.append(doc)
                    seen_ids.add(doc['id'])
                else:
                    # If document already exists, combine scores
                    for existing_doc in all_results:
                        if existing_doc['id'] == doc['id']:
                            existing_doc['strategy_score'] += doc.get('@search.score', 0.0) * parsed_weight
                            existing_doc['search_strategy'] = 'hybrid_combined'
                            break
        
        # Deduplicate by file_name (fallback to id) keeping the highest score
        dedup: Dict[str, Any] = {}
        for doc in all_results:
            key = (doc.get('file_name') or '').strip() or doc.get('id')
            if key not in dedup or doc.get('strategy_score', 0.0) > dedup[key].get('strategy_score', 0.0):
                dedup[key] = doc

        deduped_results = list(dedup.values())
        deduped_results.sort(key=lambda x: x.get('strategy_score', 0.0), reverse=True)
        
        # Return top results
        return {
            'value': deduped_results[:top],
            '@odata.count': len(deduped_results)
        }
    
    def full_text_vector_search(
        self, 
        query: str, 
        top: int = 10,
        skip: int = 0,
        filter_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform vector search using only full text embeddings"""
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Get query embedding
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_query_embedding(query))
                    query_embedding = future.result()
            else:
                query_embedding = asyncio.run(self.get_query_embedding(query))
        except:
            query_embedding = asyncio.run(self.get_query_embedding(query))
            
        if not query_embedding:
            return {"error": "Failed to get query embedding"}
        
        payload = {
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": query_embedding,
                    "k": top,
                    "fields": "full_text_vector"
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
                for doc in result.get('value', []):
                    doc['search_strategy'] = 'full_text_vector_search'
                    doc['strategy_score'] = doc.get('@search.score', 0.0)
                return result
            else:
                return {"error": f"Search failed: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"Search failed: {e}"}
    
    def parsed_data_vector_search(
        self, 
        query: str, 
        top: int = 10,
        skip: int = 0,
        filter_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform vector search using only parsed data embeddings"""
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Get query embedding
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_query_embedding(query))
                    query_embedding = future.result()
            else:
                query_embedding = asyncio.run(self.get_query_embedding(query))
        except:
            query_embedding = asyncio.run(self.get_query_embedding(query))
            
        if not query_embedding:
            return {"error": "Failed to get query embedding"}
        
        payload = {
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": query_embedding,
                    "k": top,
                    "fields": "parsed_content_vector"
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
                for doc in result.get('value', []):
                    doc['search_strategy'] = 'parsed_data_vector_search'
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
        """Perform semantic search with ranking using the hybrid index"""
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
                "staffing_plan",
                "raw_content"
            ]
        }
        
        if filter_expression:
            payload["filter"] = filter_expression
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
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
        if search_type == "hybrid":
            result = self.hybrid_vector_search(query, top=top, skip=skip, filter_expression=filter_expression)
        elif search_type == "full_text":
            result = self.full_text_vector_search(query, top=top, skip=skip, filter_expression=filter_expression)
        elif search_type == "parsed":
            result = self.parsed_data_vector_search(query, top=top, skip=skip, filter_expression=filter_expression)
        elif search_type == "semantic":
            result = self.semantic_search(query, top=top, skip=skip, filter_expression=filter_expression)
        else:
            return {"error": f"Unknown search type: {search_type}"}

        # Hydrate structured staffing JSON alongside searchable flattened strings
        try:
            docs = result.get('value', []) if isinstance(result, dict) else []
            if docs:
                self._hydrate_structured_staffing(docs)
        except Exception:
            pass
        return result


def get_hybrid_search_service() -> HybridSearchService:
    """Get an instance of the hybrid search service"""
    return HybridSearchService()


# Test function
async def test_hybrid_search():
    """Test the hybrid search service"""
    print("🔍 Testing Hybrid Search Service")
    print("=" * 50)
    
    try:
        service = get_hybrid_search_service()
        
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
        
        print("\n🎉 Hybrid search test completed!")
        
    except Exception as e:
        print(f"❌ Error testing hybrid search: {e}")


if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
