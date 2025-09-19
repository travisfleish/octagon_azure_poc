from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from .embedding_service import EmbeddingService
from .vector_service import VectorService
from ..config import get_settings


class VectorIndexerError(Exception):
    """Raised when vector indexing operations fail."""


class VectorIndexer:
    """Service for indexing SOW documents with vector embeddings."""

    def __init__(self) -> None:
        settings = get_settings()
        self._embedding_service = EmbeddingService()
        self._vector_service = VectorService()
        
        # Azure Storage configuration
        self._account_url = settings.storage_blob_endpoint
        self._src_container = "sows"
        self._extracted_container = "extracted"
        self._parsed_container = "parsed"
        
        # Initialize storage client
        self._credential = DefaultAzureCredential()
        self._blob_service = BlobServiceClient(
            account_url=self._account_url,
            credential=self._credential
        )

    async def create_index(self) -> None:
        """Create the vector search index."""
        try:
            await self._vector_service.create_index()
            print("✅ Vector search index created successfully")
        except Exception as e:
            raise VectorIndexerError(f"Failed to create index: {e}") from e

    async def index_single_document(self, blob_name: str) -> Dict[str, Any]:
        """Index a single SOW document."""
        try:
            # Get container clients
            src_container = self._blob_service.get_container_client(self._src_container)
            extracted_container = self._blob_service.get_container_client(self._extracted_container)
            parsed_container = self._blob_service.get_container_client(self._parsed_container)
            
            # Download and process the document
            result = await self._process_and_index_blob(
                src_container, extracted_container, parsed_container, blob_name
            )
            
            return result
        except Exception as e:
            raise VectorIndexerError(f"Failed to index document {blob_name}: {e}") from e

    async def index_all_documents(self) -> List[Dict[str, Any]]:
        """Index all SOW documents in the source container."""
        try:
            # Get container clients
            src_container = self._blob_service.get_container_client(self._src_container)
            extracted_container = self._blob_service.get_container_client(self._extracted_container)
            parsed_container = self._blob_service.get_container_client(self._parsed_container)
            
            results = []
            
            # List all blobs in source container
            blobs = list(src_container.list_blobs())
            print(f"Found {len(blobs)} documents to process")
            
            for blob in blobs:
                if not blob.name.lower().endswith(('.pdf', '.docx')):
                    continue
                
                try:
                    result = await self._process_and_index_blob(
                        src_container, extracted_container, parsed_container, blob.name
                    )
                    results.append(result)
                    print(f"✅ Processed: {blob.name}")
                except Exception as e:
                    print(f"⚠️ Failed to process {blob.name}: {e}")
                    results.append({
                        "blob_name": blob.name,
                        "status": "failed",
                        "error": str(e)
                    })
            
            return results
        except Exception as e:
            raise VectorIndexerError(f"Failed to index all documents: {e}") from e

    async def _process_and_index_blob(
        self, 
        src_container, 
        extracted_container, 
        parsed_container, 
        blob_name: str
    ) -> Dict[str, Any]:
        """Process a single blob and index it with vectors."""
        try:
            # Download the original document
            blob_client = src_container.get_blob_client(blob_name)
            blob_props = blob_client.get_blob_properties()
            blob_data = blob_client.download_blob().readall()
            
            # Get metadata and tags
            metadata = blob_props.metadata or {}
            try:
                tags_resp = blob_client.get_blob_tags()
                tags = tags_resp.get("tags", {}) if isinstance(tags_resp, dict) else {}
            except Exception:
                tags = {}
            
            # Extract text (reuse existing logic)
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent.parent))
            from process_one_sow import extract_docx_text, extract_pdf_text
            
            if blob_name.lower().endswith('.docx'):
                full_text = extract_docx_text(blob_data)
                file_format = "docx"
            elif blob_name.lower().endswith('.pdf'):
                full_text = extract_pdf_text(blob_data)
                file_format = "pdf"
            else:
                raise ValueError(f"Unsupported file format: {blob_name}")
            
            # Get parsed data if it exists
            parsed_data = None
            stem = blob_name.rsplit('.', 1)[0]
            try:
                parsed_blob = parsed_container.get_blob_client(f"{stem}.json")
                parsed_json = json.loads(parsed_blob.download_blob().readall().decode('utf-8'))
                parsed_data = parsed_json
            except Exception:
                print(f"⚠️ No parsed data found for {blob_name}, using only full text")
            
            # Generate vectors
            vectors = await self._embedding_service.create_document_vectors(
                blob_name, full_text, parsed_data
            )
            
            # Prepare document for indexing
            document = self._prepare_document_for_indexing(
                blob_name, full_text, parsed_data, vectors, metadata, tags, file_format
            )
            
            # Index the document
            await self._vector_service.index_document(document)
            
            return {
                "blob_name": blob_name,
                "status": "success",
                "text_length": len(full_text),
                "has_parsed_data": parsed_data is not None,
                "has_vectors": True
            }
            
        except Exception as e:
            raise VectorIndexerError(f"Failed to process blob {blob_name}: {e}") from e

    def _prepare_document_for_indexing(
        self,
        blob_name: str,
        full_text: str,
        parsed_data: Optional[Dict[str, Any]],
        vectors: Dict[str, List[float]],
        metadata: Dict[str, str],
        tags: Dict[str, str],
        file_format: str
    ) -> Dict[str, Any]:
        """Prepare a document for indexing in the vector database."""
        
        # Extract basic information
        company = None
        sow_id = None
        term_start = None
        term_end = None
        term_months = None
        
        if parsed_data:
            llm_data = parsed_data.get("llm", {})
            company = llm_data.get("company") or metadata.get("company") or tags.get("company")
            sow_id = llm_data.get("sow_id") or metadata.get("sow_id") or tags.get("sow_id")
            
            # Extract term information
            term = llm_data.get("term", {})
            if term.get("start"):
                try:
                    term_start = datetime.fromisoformat(term["start"].replace('Z', '+00:00'))
                except:
                    term_start = None
            if term.get("end"):
                try:
                    term_end = datetime.fromisoformat(term["end"].replace('Z', '+00:00'))
                except:
                    term_end = None
            term_months = term.get("months")
            if term_months is not None:
                try:
                    term_months = int(term_months)
                except:
                    term_months = None
        
        # Extract structured data - ensure all arrays are never None
        scope_bullets = []
        deliverables = []
        roles_detected = []
        assumptions = []
        explicit_hours = []
        fte_pct = []
        
        if parsed_data and parsed_data.get("llm"):
            llm_data = parsed_data["llm"]
            
            # Ensure arrays are never None
            scope_bullets = llm_data.get("scope_bullets") or []
            deliverables = llm_data.get("deliverables") or []
            assumptions = llm_data.get("assumptions") or []
            
            # Extract roles
            roles = llm_data.get("roles_detected") or []
            roles_detected = [role.get("title", "") for role in roles if role.get("title")]
            
            # Extract units - ensure these are lists, not None
            units = llm_data.get("units", {})
            explicit_hours = units.get("explicit_hours") or []
            fte_pct = units.get("fte_pct") or []
        
        # Final safety check - ensure no None values
        scope_bullets = scope_bullets if scope_bullets is not None else []
        deliverables = deliverables if deliverables is not None else []
        roles_detected = roles_detected if roles_detected is not None else []
        assumptions = assumptions if assumptions is not None else []
        explicit_hours = explicit_hours if explicit_hours is not None else []
        fte_pct = fte_pct if fte_pct is not None else []
        
        # Create the document - only include non-None values
        document = {
            "id": blob_name,  # Use blob name as unique ID
            "blob_name": blob_name,
            "company": company,
            "sow_id": sow_id,
            "format": file_format,
            
            # Text content
            "full_text": full_text,
            "scope_bullets": scope_bullets,
            "deliverables": deliverables,
            "roles_detected": roles_detected,
            "assumptions": assumptions,
            
            # Units
            "explicit_hours": explicit_hours,
            "fte_pct": fte_pct,
            
            # Vectors
            "content_vector": vectors["content_vector"],
            "structured_vector": vectors["structured_vector"],
            
            # Metadata
            "text_length": len(full_text),
        }
        
        # Only add term fields if they have values
        if term_start is not None:
            document["term_start"] = term_start
        if term_end is not None:
            document["term_end"] = term_end
        if term_months is not None:
            document["term_months"] = term_months
        
        return document

    async def search_similar_documents(
        self, 
        query: str, 
        top_k: int = 5,
        company_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity."""
        try:
            # Generate query vector
            query_vector = await self._embedding_service.get_embedding(query)
            
            # Build filter expression
            filter_expr = None
            if company_filter:
                filter_expr = f"company eq '{company_filter}'"
            
            # Perform vector search
            results = await self._vector_service.search_similar(
                query_vector=query_vector,
                top_k=top_k,
                filter_expression=filter_expr
            )
            
            return results
        except Exception as e:
            raise VectorIndexerError(f"Search failed: {e}") from e

    async def hybrid_search_documents(
        self,
        query: str,
        top_k: int = 5,
        company_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining text and vector search."""
        try:
            # Generate query vector
            query_vector = await self._embedding_service.get_embedding(query)
            
            # Build filter expression
            filter_expr = None
            if company_filter:
                filter_expr = f"company eq '{company_filter}'"
            
            # Perform hybrid search
            results = await self._vector_service.hybrid_search(
                query_text=query,
                query_vector=query_vector,
                top_k=top_k,
                filter_expression=filter_expr
            )
            
            return results
        except Exception as e:
            raise VectorIndexerError(f"Hybrid search failed: {e}") from e

    async def get_index_statistics(self) -> Dict[str, Any]:
        """Get statistics about the vector index."""
        try:
            return await self._vector_service.get_index_stats()
        except Exception as e:
            raise VectorIndexerError(f"Failed to get index statistics: {e}") from e
