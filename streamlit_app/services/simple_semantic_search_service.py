#!/usr/bin/env python3
"""
Simple Semantic Search Service for Azure Search
==============================================

This service provides semantic search capabilities using:
- Semantic ranking (without vector fields)
- Fuzzy matching with Lucene operators
- Synonym expansion
- Multiple search strategies
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


class SimpleSemanticSearchService:
    """Service for semantic search using Azure Search semantic ranking"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.index_name = "octagon-sows-parsed"
        self._load_environment()
        
        # Define synonyms for better matching
        self.synonyms = {
            "golf": ["masters", "augusta", "tournament", "championship", "golf club", "pga"],
            "augusta": ["august", "masters", "golf", "tournament", "national golf club"],
            "masters": ["augusta", "golf", "tournament", "championship", "masters tournament"],
            "hospitality": ["hosting", "event", "guest", "hospitality program", "entertainment"],
            "event": ["hospitality", "hosting", "program", "event management", "conference"],
            "sponsorship": ["sponsor", "partnership", "brand", "activation", "marketing"],
            "measurement": ["analytics", "reporting", "tracking", "metrics", "data"],
            "marketing": ["activation", "brand", "campaign", "promotion", "advertising"]
        }
    
    def _load_environment(self):
        """Load environment variables"""
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        self.search_endpoint = os.getenv('SEARCH_ENDPOINT')
        self.search_key = os.getenv('SEARCH_KEY')
        
        if not self.search_endpoint or not self.search_key:
            raise ValueError("Missing SEARCH_ENDPOINT or SEARCH_KEY in environment variables")
        
        # Remove trailing slash if present
        self.search_endpoint = self.search_endpoint.rstrip('/')
    
    def expand_query_with_synonyms(self, query: str) -> str:
        """Expand query with synonyms for better matching"""
        query_terms = query.lower().split()
        expanded_terms = []
        
        for term in query_terms:
            expanded_terms.append(term)  # Add original term
            if term in self.synonyms:
                expanded_terms.extend(self.synonyms[term])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in expanded_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return " ".join(unique_terms)
    
    def create_fuzzy_query(self, query: str) -> str:
        """Create a fuzzy query with Lucene operators"""
        terms = query.split()
        fuzzy_terms = []
        
        for term in terms:
            if len(term) > 2:  # Only apply fuzzy matching to longer terms
                # Add fuzzy matching (~1 means 1 character difference allowed)
                fuzzy_terms.append(f"{term}~1")
                # Add wildcard for partial matching
                fuzzy_terms.append(f"{term}*")
                # Add original term
                fuzzy_terms.append(term)
            else:
                fuzzy_terms.append(term)
        
        return " ".join(fuzzy_terms)
    
    def create_phonetic_query(self, query: str) -> str:
        """Create a phonetic query for better matching of similar-sounding words"""
        terms = query.split()
        phonetic_terms = []
        
        for term in terms:
            if len(term) > 3:  # Only apply phonetic matching to longer terms
                # Add phonetic variations
                phonetic_terms.append(term)
                # Add common phonetic variations
                if term.lower() == "august":
                    phonetic_terms.append("augusta")
                elif term.lower() == "augusta":
                    phonetic_terms.append("august")
                # Add fuzzy matching for phonetic similarity
                phonetic_terms.append(f"{term}~2")  # Allow 2 character differences
            else:
                phonetic_terms.append(term)
        
        return " ".join(phonetic_terms)
    
    def search_with_multiple_strategies(
        self, 
        query: str, 
        search_fields: Optional[str] = None,
        filter_expression: Optional[str] = None,
        top: int = 20,
        skip: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Perform search using multiple strategies and combine results
        """
        all_results = []
        seen_ids = set()
        
        # Strategy 1: Phonetic search for similar-sounding words
        phonetic_query = self.create_phonetic_query(query)
        if phonetic_query != query:
            results1 = self._search_single_strategy(
                phonetic_query, search_fields, filter_expression, top, skip
            )
            if results1 and results1.get('value'):
                for doc in results1['value']:
                    if doc['id'] not in seen_ids:
                        doc['search_strategy'] = 'phonetic_match'
                        doc['strategy_score'] = 1.0
                        all_results.append(doc)
                        seen_ids.add(doc['id'])
        
        # Strategy 2: Fuzzy search with Lucene operators
        fuzzy_query = self.create_fuzzy_query(query)
        if fuzzy_query != query:
            results2 = self._search_single_strategy(
                fuzzy_query, search_fields, filter_expression, top, skip
            )
            if results2 and results2.get('value'):
                for doc in results2['value']:
                    if doc['id'] not in seen_ids:
                        doc['search_strategy'] = 'fuzzy_match'
                        doc['strategy_score'] = 0.95
                        all_results.append(doc)
                        seen_ids.add(doc['id'])
        
        # Strategy 3: Original query
        results3 = self._search_single_strategy(
            query, search_fields, filter_expression, top, skip
        )
        if results3 and results3.get('value'):
            for doc in results3['value']:
                if doc['id'] not in seen_ids:
                    doc['search_strategy'] = 'exact_match'
                    doc['strategy_score'] = 0.9
                    all_results.append(doc)
                    seen_ids.add(doc['id'])
        
        # Strategy 4: Synonym expansion
        expanded_query = self.expand_query_with_synonyms(query)
        if expanded_query != query:
            results4 = self._search_single_strategy(
                expanded_query, search_fields, filter_expression, top, skip
            )
            if results4 and results4.get('value'):
                for doc in results4['value']:
                    if doc['id'] not in seen_ids:
                        doc['search_strategy'] = 'synonym_match'
                        doc['strategy_score'] = 0.8
                        all_results.append(doc)
                        seen_ids.add(doc['id'])
        
        # Strategy 5: Individual term search (for multi-word queries)
        if len(query.split()) > 1:
            for term in query.split():
                if len(term) > 2:  # Skip short terms
                    results5 = self._search_single_strategy(
                        term, search_fields, filter_expression, top//2, skip
                    )
                    if results5 and results5.get('value'):
                        for doc in results5['value']:
                            if doc['id'] not in seen_ids:
                                doc['search_strategy'] = 'term_match'
                                doc['strategy_score'] = 0.7
                                all_results.append(doc)
                                seen_ids.add(doc['id'])
        
        # Sort by strategy score (fuzzy matches first)
        all_results.sort(key=lambda x: x.get('strategy_score', 0), reverse=True)
        
        # Return in the same format as original search
        return {
            '@odata.count': len(all_results),
            'value': all_results[:top]
        }
    
    def _search_single_strategy(
        self, 
        query: str, 
        search_fields: Optional[str] = None,
        filter_expression: Optional[str] = None,
        top: int = 20,
        skip: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Perform a single search strategy"""
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        payload = {
            "search": query,
            "top": top,
            "skip": skip,
            "count": True,
            "queryType": "simple",
            "searchMode": "all"
        }
        
        if search_fields:
            payload["searchFields"] = search_fields
        
        if filter_expression:
            payload["filter"] = filter_expression
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Search error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Search error: {e}")
            return None
    
    def search(
        self, 
        query: str, 
        search_fields: Optional[str] = None,
        filter_expression: Optional[str] = None,
        top: int = 20,
        skip: int = 0,
        use_enhanced: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Enhanced search with multiple strategies
        
        Args:
            query: Search query string
            search_fields: Comma-separated list of fields to search
            filter_expression: OData filter expression
            top: Number of results to return
            skip: Number of results to skip
            use_enhanced: Whether to use enhanced multi-strategy search
        
        Returns:
            Search results dictionary or None if error
        """
        if use_enhanced:
            return self.search_with_multiple_strategies(
                query, search_fields, filter_expression, top, skip
            )
        else:
            return self._search_single_strategy(
                query, search_fields, filter_expression, top, skip
            )
    
    def search_by_client(self, client_name: str, top: int = 20, use_enhanced: bool = True) -> Optional[Dict[str, Any]]:
        """Search for SOWs by client name with enhanced matching"""
        return self.search(
            query=client_name,
            search_fields="client_name",
            top=top,
            use_enhanced=use_enhanced
        )
    
    def search_by_project_title(self, project_title: str, top: int = 20, use_enhanced: bool = True) -> Optional[Dict[str, Any]]:
        """Search for SOWs by project title with enhanced matching"""
        return self.search(
            query=project_title,
            search_fields="project_title",
            top=top,
            use_enhanced=use_enhanced
        )
    
    def search_by_staffing_role(self, role: str, top: int = 20, use_enhanced: bool = True) -> Optional[Dict[str, Any]]:
        """Search for SOWs by staffing role with enhanced matching"""
        return self.search(
            query=role,
            search_fields="staffing_plan",
            top=top,
            use_enhanced=use_enhanced
        )
    
    def search_by_deliverables(self, deliverable: str, top: int = 20, use_enhanced: bool = True) -> Optional[Dict[str, Any]]:
        """Search for SOWs by deliverable with enhanced matching"""
        return self.search(
            query=deliverable,
            search_fields="deliverables",
            top=top,
            use_enhanced=use_enhanced
        )
    
    def search_by_date_range(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        top: int = 20,
        use_enhanced: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Search for SOWs by date range"""
        filter_parts = []
        if start_date:
            filter_parts.append(f"start_date ge '{start_date}'")
        if end_date:
            filter_parts.append(f"end_date le '{end_date}'")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        return self.search(
            query="*",
            filter_expression=filter_expression,
            top=top,
            use_enhanced=use_enhanced
        )
    
    def search_by_project_length(self, project_length: str, top: int = 20, use_enhanced: bool = True) -> Optional[Dict[str, Any]]:
        """Search for SOWs by project length with enhanced matching"""
        return self.search(
            query=project_length,
            search_fields="project_length",
            top=top,
            use_enhanced=use_enhanced
        )
    
    def get_all_documents(self, top: int = 50, use_enhanced: bool = True) -> Optional[Dict[str, Any]]:
        """Get all documents from the index"""
        return self.search(query="*", top=top, use_enhanced=use_enhanced)
    
    def get_unique_clients(self) -> List[str]:
        """Get list of unique client names"""
        results = self.search(query="*", top=1000, use_enhanced=False)
        if not results:
            return []
        
        clients = set()
        for doc in results.get('value', []):
            client = doc.get('client_name', '').strip()
            if client:
                clients.add(client)
        
        return sorted(list(clients))
    
    def get_unique_project_lengths(self) -> List[str]:
        """Get list of unique project lengths"""
        results = self.search(query="*", top=1000, use_enhanced=False)
        if not results:
            return []
        
        lengths = set()
        for doc in results.get('value', []):
            length = doc.get('project_length', '').strip()
            if length:
                lengths.add(length)
        
        return sorted(list(lengths))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the index"""
        results = self.get_all_documents(top=1000, use_enhanced=False)
        if not results:
            return {"total_documents": 0, "clients": 0, "date_range": None}
        
        documents = results.get('value', [])
        total_docs = len(documents)
        
        # Count unique clients
        clients = set()
        for doc in documents:
            client = doc.get('client_name', '').strip()
            if client:
                clients.add(client)
        
        # Get date range
        dates = []
        for doc in documents:
            start_date = doc.get('start_date', '')
            if start_date:
                dates.append(start_date)
        
        date_range = None
        if dates:
            dates.sort()
            date_range = {"earliest": dates[0], "latest": dates[-1]}
        
        return {
            "total_documents": total_docs,
            "clients": len(clients),
            "date_range": date_range
        }
    
    def format_search_results(self, results: Dict[str, Any], show_details: bool = True) -> List[Dict[str, Any]]:
        """Format search results for display in Streamlit"""
        if not results:
            return []
        
        documents = results.get('value', [])
        formatted_results = []
        
        for doc in documents:
            formatted_doc = {
                "client_name": doc.get('client_name', 'Unknown Client'),
                "project_title": doc.get('project_title', 'No title'),
                "project_length": doc.get('project_length', 'Unknown'),
                "start_date": doc.get('start_date', 'N/A'),
                "end_date": doc.get('end_date', 'N/A'),
                "file_name": doc.get('file_name', 'Unknown'),
                "scope_summary": doc.get('scope_summary', ''),
                "deliverables": doc.get('deliverables', []),
                "staffing_plan": doc.get('staffing_plan', []),
                "exclusions": doc.get('exclusions', []),
                "extraction_timestamp": doc.get('extraction_timestamp', ''),
                "search_strategy": doc.get('search_strategy', 'unknown'),
                "strategy_score": doc.get('strategy_score', 0.0)
            }
            
            if show_details:
                # Truncate scope summary for display
                scope = formatted_doc['scope_summary']
                if scope and len(scope) > 200:
                    formatted_doc['scope_summary_preview'] = scope[:200] + "..."
                else:
                    formatted_doc['scope_summary_preview'] = scope
                
                # Limit deliverables for display
                deliverables = formatted_doc['deliverables']
                formatted_doc['deliverables_preview'] = deliverables[:3]
                formatted_doc['deliverables_count'] = len(deliverables)
                
                # Limit staffing for display
                staffing = formatted_doc['staffing_plan']
                formatted_doc['staffing_preview'] = staffing[:3]
                formatted_doc['staffing_count'] = len(staffing)
            
            formatted_results.append(formatted_doc)
        
        return formatted_results


# Global instance for caching
_simple_semantic_search_service = None

def get_simple_semantic_search_service() -> SimpleSemanticSearchService:
    """Get or create the simple semantic search service (cached)"""
    global _simple_semantic_search_service
    if _simple_semantic_search_service is None:
        _simple_semantic_search_service = SimpleSemanticSearchService()
    return _simple_semantic_search_service
