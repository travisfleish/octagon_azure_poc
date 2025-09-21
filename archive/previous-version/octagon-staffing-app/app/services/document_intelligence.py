from __future__ import annotations

import io
import re
import zipfile
from typing import Dict, Any, Optional

from PyPDF2 import PdfReader
from openai import AsyncOpenAI

from ..config import get_settings


class DocumentIntelligenceError(Exception):
    """Raised when Document Intelligence operations fail."""


class DocumentIntelligenceService:
    """Document processing service using PyPDF2 and zipfile for PDF/DOCX extraction."""

    def __init__(self) -> None:
        self._openai_client: Optional[AsyncOpenAI] = None

    async def _get_openai_client(self) -> AsyncOpenAI:
        if self._openai_client is None:
            settings = get_settings()
            if not settings.aoai_endpoint or not settings.aoai_key:
                raise DocumentIntelligenceError("Azure OpenAI configuration missing")
            self._openai_client = AsyncOpenAI(
                api_key=settings.aoai_key,
                base_url=f"{settings.aoai_endpoint}/openai/deployments/{settings.aoai_deployment}",
                default_query={"api-version": settings.aoai_api_version},
            )
        return self._openai_client

    def _extract_docx_text(self, data: bytes) -> str:
        """Fast DOCX text extraction via document.xml."""
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", " ", xml)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_pdf_text(self, data: bytes) -> str:
        """Lightweight PDF text extraction."""
        reader = PdfReader(io.BytesIO(data))
        out = []
        # Cap to first 10 pages for speed
        for page in reader.pages[:10]:
            try:
                out.append(page.extract_text() or "")
            except Exception:
                pass
        return re.sub(r"\s+", " ", "\n".join(out)).strip()

    def _parse_fields_deterministic(self, text: str) -> Dict[str, Any]:
        """First-pass heuristics for auditability."""
        scope = re.findall(r"(?:Scope of Work|Scope|Services)[:\-]\s*(.+?)(?=(?:Deliverables|Term|Timeline|$))", text, re.I)
        deliverables = re.findall(r"(?:Deliverables?)[:\-]\s*(.+?)(?=(?:Term|Timeline|$))", text, re.I)
        dates = re.findall(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b", text, re.I)
        roles = re.findall(r"\b(Account|Manager|Director|Analyst|Coordinator|Designer|Strategist|Producer|Engineer)\b", text, re.I)
        fte = re.findall(r"\b(\d{1,3})\s*%?\s*FTE\b", text, re.I)
        hours = re.findall(r"\b(\d{1,4})\s*(?:hours|hrs)\b", text, re.I)
        rate_hits = re.findall(r"\b(rate|fee)s?\b.*?\b(hour|daily|monthly)\b", text, re.I)

        return {
            "term": {"start": None, "end": None, "months": None, "inferred": False},
            "scope_bullets": [scope[0]] if scope else [],
            "deliverables": [deliverables[0]] if deliverables else [],
            "units": {
                "explicit_hours": [int(h) for h in hours[:5]] if hours else None,
                "fte_pct": [int(x) for x in fte[:5]] if fte else None,
                "fees": [],
                "rate_table": [{"hit": " ".join(hit)} for hit in rate_hits[:5]]
            },
            "roles_detected": [{"title": r} for r in sorted(set(roles), key=str.lower)],
            "assumptions": [],
            "provenance": {"text_source": "pdf_or_docx", "sample_dates": dates[:3]}
        }

    async def _llm_parse_schema(self, blob_name: str, file_format: str, text: str) -> Dict[str, Any]:
        """LLM-powered schema extraction using Azure OpenAI."""
        # Trim text to keep token usage predictable
        doc = text[:60_000]

        # JSON Schema for structured output
        json_schema = {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "sow_id": {"type": "string"},
                "project_title": {"type": "string"},
                "term": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "months": {"type": "integer"},
                        "inferred": {"type": "boolean"}
                    }
                },
                "scope_bullets": {"type": "array", "items": {"type": "string"}},
                "deliverables": {"type": "array", "items": {"type": "string"}},
                "roles_detected": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "canonical": {"type": "string"}
                        }
                    }
                },
                "units": {
                    "type": "object",
                    "properties": {
                        "explicit_hours": {"type": "array", "items": {"type": "integer"}},
                        "fte_pct": {"type": "array", "items": {"type": "integer"}},
                        "fees": {"type": "array", "items": {"type": "number"}},
                        "rate_table": {"type": "array", "items": {"type": "object"}}
                    }
                },
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "provenance": {
                    "type": "object",
                    "properties": {
                        "quotes": {"type": "array", "items": {"type": "string"}},
                        "sections": {"type": "array", "items": {"type": "string"}},
                        "notes": {"type": "string"}
                    }
                }
            },
            "required": ["company", "sow_id", "project_title", "term", "scope_bullets", "deliverables", "units", "roles_detected", "assumptions", "provenance"]
        }

        system_prompt = """You are an expert SOW-to-staffing parser. Extract ONLY what is present in the text.
- Do not invent values.
- If uncertain, return null and add a brief reason in provenance.notes.
- Return short bullet strings (not paragraphs).
- For dates, prefer explicit dates; otherwise leave null and set term.inferred=false.
- If fees/rates are in tables, normalize each row into rate_table with role/unit/amount/notes.
- Include 2–5 short supporting quotes in provenance.quotes and brief section/page hints in provenance.sections."""

        user_prompt = f"""Document: {blob_name}
Format: {file_format}

Extract the schema from the following SOW text:

<<<SOW_TEXT_BEGIN>>>
{doc}
<<<SOW_TEXT_END>>>"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Use JSON schema for structured output
        response_format = {"type": "json_schema", "json_schema": {"name": "sow_extraction", "schema": json_schema}}

        # Retry for transient issues
        last_err = None
        for attempt in range(3):
            try:
                client = await self._get_openai_client()
                response = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=messages,
                    response_format=response_format
                )
                import json
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                last_err = e
                continue

        raise DocumentIntelligenceError(f"LLM extraction failed after 3 attempts: {last_err}")

    async def extract_structure(self, file_bytes: bytes, blob_name: str = "unknown") -> dict:
        """Extract structure from PDF/DOCX bytes using PyPDF2 and zipfile."""

        try:
            # Determine file type and extract text
            if file_bytes.startswith(b'%PDF'):
                text = self._extract_pdf_text(file_bytes)
                fmt = "pdf"
            elif file_bytes.startswith(b'PK'):  # ZIP/DOCX signature
                text = self._extract_docx_text(file_bytes)
                fmt = "docx"
            else:
                raise DocumentIntelligenceError(f"Unsupported file type for {blob_name}")

            # Deterministic field parsing
            deterministic = self._parse_fields_deterministic(text)

            # LLM-powered schema extraction
            llm_data = await self._llm_parse_schema(blob_name, fmt, text)

            # Create complete extraction record
            return {
                "blob_name": blob_name,
                "format": fmt,
                "full_text": text,
                "company": llm_data.get("company"),
                "sow_id": llm_data.get("sow_id"),
                "project_title": llm_data.get("project_title"),
                "sections": llm_data.get("sections", []),
                "key_entities": llm_data.get("key_entities", []),
                "deterministic": deterministic,
                "llm": llm_data
            }

        except Exception as exc:  # noqa: BLE001
            raise DocumentIntelligenceError(str(exc)) from exc



