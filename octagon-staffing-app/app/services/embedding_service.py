from __future__ import annotations

import json
from typing import List, Dict, Any

from openai import AsyncAzureOpenAI

from ..config import get_settings


class EmbeddingServiceError(Exception):
    """Raised when embedding operations fail."""


class EmbeddingService:
    """Service for generating embeddings using Azure OpenAI."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.aoai_endpoint or not settings.aoai_key:
            raise EmbeddingServiceError("Azure OpenAI configuration missing")
        
        self._client = AsyncAzureOpenAI(
            api_key=settings.aoai_key,
            api_version=settings.aoai_api_version,
            azure_endpoint=settings.aoai_endpoint,
        )
        self._deployment = "text-embedding-3-small"  # Use the small model for cost efficiency

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            response = await self._client.embeddings.create(
                model=self._deployment,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise EmbeddingServiceError(f"Failed to generate embedding: {e}") from e

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        try:
            # Filter out empty or None texts
            valid_texts = [text for text in texts if text and text.strip()]
            if not valid_texts:
                raise EmbeddingServiceError("No valid texts provided for embedding")
            
            print(f"Generating embeddings for {len(valid_texts)} texts")
            print(f"First text preview: {valid_texts[0][:100]}...")
            
            response = await self._client.embeddings.create(
                model=self._deployment,
                input=valid_texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise EmbeddingServiceError(f"Failed to generate batch embeddings: {e}") from e

    def prepare_content_for_embedding(self, full_text: str, parsed_data: Dict[str, Any]) -> str:
        """Prepare content for embedding by combining full text with structured data."""
        content_parts = []
        
        # Add full text
        content_parts.append(f"Document Content:\n{full_text}")
        
        # Add structured information from parsed data
        if parsed_data:
            llm_data = parsed_data.get("llm", {})
            
            # Add scope and deliverables
            if llm_data.get("scope_bullets"):
                content_parts.append(f"Scope of Work:\n" + "\n".join(f"• {bullet}" for bullet in llm_data["scope_bullets"]))
            
            if llm_data.get("deliverables"):
                content_parts.append(f"Deliverables:\n" + "\n".join(f"• {deliverable}" for deliverable in llm_data["deliverables"]))
            
            # Add roles and requirements
            if llm_data.get("roles_detected"):
                roles = [role.get("title", "") for role in llm_data["roles_detected"] if role.get("title")]
                if roles:
                    content_parts.append(f"Required Roles:\n" + ", ".join(roles))
            
            # Add assumptions
            if llm_data.get("assumptions"):
                content_parts.append(f"Assumptions:\n" + "\n".join(f"• {assumption}" for assumption in llm_data["assumptions"]))
            
            # Add term information
            term = llm_data.get("term", {})
            if term.get("start") or term.get("end"):
                term_info = []
                if term.get("start"):
                    term_info.append(f"Start: {term['start']}")
                if term.get("end"):
                    term_info.append(f"End: {term['end']}")
                if term.get("months"):
                    term_info.append(f"Duration: {term['months']} months")
                if term_info:
                    content_parts.append(f"Project Term:\n" + "\n".join(term_info))
            
            # Add rate information
            units = llm_data.get("units", {})
            if units.get("rate_table"):
                rate_info = []
                for rate in units["rate_table"]:
                    if rate.get("role") and rate.get("amount"):
                        rate_info.append(f"{rate['role']}: {rate['amount']} per {rate.get('unit', 'unit')}")
                if rate_info:
                    content_parts.append(f"Rate Information:\n" + "\n".join(rate_info))
        
        return "\n\n".join(content_parts)

    def prepare_structured_for_embedding(self, parsed_data: Dict[str, Any]) -> str:
        """Prepare structured data specifically for embedding."""
        if not parsed_data:
            return ""
        
        llm_data = parsed_data.get("llm", {})
        structured_parts = []
        
        # Company and SOW ID
        if llm_data.get("company"):
            structured_parts.append(f"Company: {llm_data['company']}")
        if llm_data.get("sow_id"):
            structured_parts.append(f"SOW ID: {llm_data['sow_id']}")
        
        # Scope and deliverables as structured text
        if llm_data.get("scope_bullets"):
            structured_parts.append("Scope: " + "; ".join(llm_data["scope_bullets"]))
        
        if llm_data.get("deliverables"):
            structured_parts.append("Deliverables: " + "; ".join(llm_data["deliverables"]))
        
        # Roles as structured text
        if llm_data.get("roles_detected"):
            roles = [role.get("title", "") for role in llm_data["roles_detected"] if role.get("title")]
            if roles:
                structured_parts.append("Roles: " + ", ".join(roles))
        
        # Term information
        term = llm_data.get("term", {})
        if term.get("months"):
            structured_parts.append(f"Duration: {term['months']} months")
        
        # Rate information
        units = llm_data.get("units", {})
        if units.get("rate_table"):
            rates = []
            for rate in units["rate_table"]:
                if rate.get("role") and rate.get("amount"):
                    rates.append(f"{rate['role']}: {rate['amount']}/{rate.get('unit', 'unit')}")
            if rates:
                structured_parts.append("Rates: " + "; ".join(rates))
        
        return " | ".join(structured_parts)

    async def create_document_vectors(
        self, 
        blob_name: str, 
        full_text: str, 
        parsed_data: Dict[str, Any]
    ) -> Dict[str, List[float]]:
        """Create both content and structured vectors for a document."""
        try:
            # Prepare content for embedding
            content_text = self.prepare_content_for_embedding(full_text, parsed_data)
            structured_text = self.prepare_structured_for_embedding(parsed_data)
            
            # Generate embeddings - handle case where structured_text might be empty
            texts_to_embed = [content_text]
            if structured_text and structured_text.strip():
                texts_to_embed.append(structured_text)
            
            embeddings = await self.get_embeddings_batch(texts_to_embed)
            
            # Use the same embedding for both if we only have one
            if len(embeddings) == 1:
                return {
                    "content_vector": embeddings[0],
                    "structured_vector": embeddings[0]  # Use same vector
                }
            else:
                return {
                    "content_vector": embeddings[0],
                    "structured_vector": embeddings[1]
                }
        except Exception as e:
            raise EmbeddingServiceError(f"Failed to create document vectors: {e}") from e
