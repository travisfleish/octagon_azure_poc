from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectInfo(BaseModel):
    """Extracted project details from a SOW."""

    title: Optional[str] = None
    client_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_weeks: Optional[int] = None
    scope_summary: Optional[str] = None


class SOWDocument(BaseModel):
    """Raw SOW metadata and content reference."""

    id: str
    file_name: str
    blob_url: str
    content_type: str = Field(description="MIME type such as application/pdf")
    uploaded_at: datetime
    project_info: Optional[ProjectInfo] = None


class ProcessedSOW(BaseModel):
    """Structured SOW data parsed from Document Intelligence."""

    sow_id: str
    sections: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list)
    project_info: Optional[ProjectInfo] = None
    raw_extraction: Optional[dict] = None



