#!/usr/bin/env python3
"""
Azure Document Intelligence Service (Layout + Tables)
====================================================

Thin wrapper around Azure Document Intelligence (prebuilt-layout) to extract
high-fidelity layout, text, and tables from PDFs and DOCX, including tables
rendered as images.

Requirements:
- Env vars: AZURE_DOCINT_ENDPOINT, AZURE_DOCINT_API_KEY, AZURE_DOCINT_API_VERSION
- Package: azure-ai-documentintelligence>=1.0.0b4
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
try:
    # New SDK (uses /documentintelligence and 2024 API versions)
    from azure.ai.documentintelligence import DocumentIntelligenceClient  # type: ignore
except Exception:  # pragma: no cover
    DocumentIntelligenceClient = None  # type: ignore
import time
import httpx


@dataclass
class TableCell:
    row_index: int
    column_index: int
    content: str


@dataclass
class TableResult:
    page_number: int
    row_count: int
    column_count: int
    cells: List[TableCell]

    def to_matrix(self) -> List[List[str]]:
        matrix: List[List[Optional[str]]] = [
            [None for _ in range(self.column_count)] for _ in range(self.row_count)
        ]
        for cell in self.cells:
            if 0 <= cell.row_index < self.row_count and 0 <= cell.column_index < self.column_count:
                matrix[cell.row_index][cell.column_index] = (cell.content or "").strip()
        return [[c or "" for c in row] for row in matrix]

    def to_markdown(self) -> str:
        matrix = self.to_matrix()
        if not matrix:
            return ""
        header = matrix[0] if matrix else []
        # Fallback header if first row looks empty
        if not any(h.strip() for h in header):
            header = [f"Col {i+1}" for i in range(self.column_count)]
        sep = ["---" for _ in header]
        lines = [" | ".join(header), " | ".join(sep)]
        for row in matrix[1:]:
            lines.append(" | ".join(row))
        return "\n".join(lines)


class AzureDocumentIntelligenceService:
    """High-level client for Azure Document Intelligence prebuilt-layout."""

    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None, api_version: Optional[str] = None):
        self.endpoint = endpoint or os.getenv("AZURE_DOCINT_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_DOCINT_API_KEY")
        # Note: SDK manages service versions; we keep for traceability
        self.api_version = api_version or os.getenv("AZURE_DOCINT_API_VERSION", "2023-07-31")

        if not self.endpoint or not self.api_key:
            raise ValueError("AZURE_DOCINT_ENDPOINT and AZURE_DOCINT_API_KEY must be set")
        self.client = None
        # Initialize SDK client only if using newer API; otherwise use REST for 2023-07-31
        if DocumentIntelligenceClient is not None and not self.api_version.startswith("2023-"):
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key),
            )

    def analyze_layout(self, file_path: Path, pages: Optional[str] = None) -> Dict[str, Any]:
        """
        Run prebuilt-layout analysis on the provided file.

        Args:
            file_path: Path to a PDF or DOCX file
            pages: Optional page range string, e.g., "1-10"

        Returns:
            Dict containing full text, per-page info, and extracted tables
        """
        if not file_path or not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content_type = "application/octet-stream"

        # Path A: Use SDK for newer API versions
        if self.client is not None:
            with open(file_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    analyze_request=f,
                    content_type=content_type,
                    pages=pages,
                )
            result = poller.result()
            # Normalize to common dict structure
            return self._normalize_sdk_result(result, file_path)

        # Path B: Use REST (Form Recognizer v3.0 - 2023-07-31)
        return self._analyze_layout_via_rest(file_path, pages)

    def _normalize_sdk_result(self, result: Any, file_path: Path) -> Dict[str, Any]:
        full_text_parts: List[str] = []
        for page in (result.pages or []):
            lines = [ln.content for ln in (page.lines or []) if getattr(ln, "content", None)]
            if lines:
                full_text_parts.append("\n".join(lines))
        full_text = "\n\n".join(full_text_parts)

        tables: List[TableResult] = []
        for tbl in (result.tables or []):
            cells: List[TableCell] = []
            for cell in (tbl.cells or []):
                cells.append(
                    TableCell(
                        row_index=getattr(cell, "row_index", 0) or 0,
                        column_index=getattr(cell, "column_index", 0) or 0,
                        content=(getattr(cell, "content", "") or "").strip(),
                    )
                )
            page_num = 1
            try:
                if getattr(tbl, "bounding_regions", None):
                    page_num = tbl.bounding_regions[0].page_number or 1
            except Exception:
                pass
            tables.append(
                TableResult(
                    page_number=page_num,
                    row_count=getattr(tbl, "row_count", 0) or 0,
                    column_count=getattr(tbl, "column_count", 0) or 0,
                    cells=cells,
                )
            )

        return {"file": str(file_path), "text": full_text, "pages": len(result.pages or []), "tables": tables}

    def _analyze_layout_via_rest(self, file_path: Path, pages: Optional[str]) -> Dict[str, Any]:
        api_version = self.api_version or "2023-07-31"
        analyze_url = f"{self.endpoint.rstrip('/')}/formrecognizer/documentModels/prebuilt-layout:analyze?api-version={api_version}"
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/octet-stream",
        }

        with open(file_path, "rb") as f:
            data = f.read()

        params = {}
        if pages:
            params["pages"] = pages

        # Submit analyze request
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(analyze_url, headers=headers, params=params, content=data)
            if resp.status_code not in (200, 202):
                raise RuntimeError(f"Analyze request failed: {resp.status_code} {resp.text}")
            # Operation-Location header for polling
            operation_url = resp.headers.get("operation-location") or resp.headers.get("Operation-Location")
            if not operation_url:
                # Some regions may return result directly
                try:
                    payload = resp.json()
                except Exception:
                    payload = {}
                return self._normalize_rest_result(payload, file_path)

            # Poll until succeeded/failed
            for _ in range(60):  # up to ~60 seconds
                poll = client.get(operation_url, headers={"Ocp-Apim-Subscription-Key": self.api_key})
                if poll.status_code != 200:
                    time.sleep(1)
                    continue
                payload = poll.json()
                status = (payload.get("status") or payload.get("analyzeResult", {}).get("status") or "").lower()
                if status in {"succeeded", "failed", "canceled"}:
                    if status != "succeeded":
                        raise RuntimeError(f"Analysis {status}: {payload}")
                    return self._normalize_rest_result(payload, file_path)
                time.sleep(1)

        raise RuntimeError("Analysis polling timed out")

    def _normalize_rest_result(self, payload: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        # FR 2023 returns { status, createdDateTime, lastUpdatedDateTime, analyzeResult: { pages, tables, ... } }
        result = payload.get("analyzeResult", payload)
        pages = result.get("pages", []) or []
        tables_json = result.get("tables", []) or []

        # Aggregate text from page lines
        text_parts: List[str] = []
        for page in pages:
            lines = page.get("lines", []) or []
            line_texts = [ln.get("content", "") for ln in lines if ln.get("content")]
            if line_texts:
                text_parts.append("\n".join(line_texts))
        full_text = "\n\n".join(text_parts)

        tables: List[TableResult] = []
        for tbl in tables_json:
            cells: List[TableCell] = []
            for cell in (tbl.get("cells", []) or []):
                cells.append(
                    TableCell(
                        row_index=int(cell.get("rowIndex", 0) or 0),
                        column_index=int(cell.get("columnIndex", 0) or 0),
                        content=(cell.get("content") or "").strip(),
                    )
                )
            page_num = 1
            try:
                regions = tbl.get("boundingRegions") or []
                if regions:
                    page_num = int(regions[0].get("pageNumber", 1) or 1)
            except Exception:
                pass
            tables.append(
                TableResult(
                    page_number=page_num,
                    row_count=int(tbl.get("rowCount", 0) or 0),
                    column_count=int(tbl.get("columnCount", 0) or 0),
                    cells=cells,
                )
            )

        return {"file": str(file_path), "text": full_text, "pages": len(pages), "tables": tables}

    def extract_tables_markdown(self, analysis: Dict[str, Any], max_tables: int = 10) -> List[str]:
        tables: List[TableResult] = analysis.get("tables", [])
        markdowns: List[str] = []
        for i, tbl in enumerate(tables[:max_tables], 1):
            md = tbl.to_markdown()
            if md.strip():
                markdowns.append(f"Table {i} (p{tbl.page_number}):\n{md}")
        return markdowns


