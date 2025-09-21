#!/usr/bin/env python3
"""
Azure Search Service for Streamlit Integration
=============================================

This service provides Azure Search functionality for the Streamlit app,
allowing users to search through parsed SOW data with various filters and options.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


class AzureSearchService:
    """Service for querying Azure Search index with parsed SOW data"""
    
    def __init__(self):
        self.search_endpoint = None
        self.search_key = None
        self.index_name = "octagon-sows-parsed"
        self._load_environment()
    
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
    
    def search(
        self, 
        query: str = "*", 
        search_fields: Optional[str] = None,
        filter_expression: Optional[str] = None,
        top: int = 20,
        skip: int = 0,
        order_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Perform a search query against the Azure Search index
        
        Args:
            query: Search query string
            search_fields: Comma-separated list of fields to search
            filter_expression: OData filter expression
            top: Number of results to return
            skip: Number of results to skip
            order_by: Field to sort by
        
        Returns:
            Search results dictionary or None if error
        """
        url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }
        
        # Build search payload
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
        
        if order_by:
            payload["orderby"] = order_by
        
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
    
    def search_by_client(self, client_name: str, top: int = 20) -> Optional[Dict[str, Any]]:
        """Search for SOWs by client name"""
        return self.search(
            query=client_name,
            search_fields="client_name",
            top=top
        )
    
    def search_by_project_title(self, project_title: str, top: int = 20) -> Optional[Dict[str, Any]]:
        """Search for SOWs by project title"""
        return self.search(
            query=project_title,
            search_fields="project_title",
            top=top
        )
    
    def search_by_staffing_role(self, role: str, top: int = 20) -> Optional[Dict[str, Any]]:
        """Search for SOWs by staffing role"""
        return self.search(
            query=role,
            search_fields="staffing_plan",
            top=top
        )
    
    def search_by_deliverables(self, deliverable: str, top: int = 20) -> Optional[Dict[str, Any]]:
        """Search for SOWs by deliverable"""
        return self.search(
            query=deliverable,
            search_fields="deliverables",
            top=top
        )
    
    def search_by_date_range(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        top: int = 20
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
            top=top
        )
    
    def search_by_project_length(self, project_length: str, top: int = 20) -> Optional[Dict[str, Any]]:
        """Search for SOWs by project length"""
        return self.search(
            query=project_length,
            search_fields="project_length",
            top=top
        )
    
    def get_all_documents(self, top: int = 50) -> Optional[Dict[str, Any]]:
        """Get all documents from the index"""
        return self.search(query="*", top=top)
    
    def get_unique_clients(self) -> List[str]:
        """Get list of unique client names"""
        results = self.search(query="*", top=1000)
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
        results = self.search(query="*", top=1000)
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
        results = self.get_all_documents(top=1000)
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
                "extraction_timestamp": doc.get('extraction_timestamp', '')
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
_search_service = None

def get_search_service() -> AzureSearchService:
    """Get or create the search service (cached)"""
    global _search_service
    if _search_service is None:
        _search_service = AzureSearchService()
    return _search_service
