from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal
from enum import Enum

from pydantic import BaseModel, Field


class SOWProcessingType(str, Enum):
    """Type of SOW processing workflow"""
    HISTORICAL = "historical"  # Adding existing SOW with staffing plan to database
    NEW_STAFFING = "new_staffing"  # New SOW needing staffing plan generation


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
    processing_type: SOWProcessingType = Field(description="Type of processing workflow")
    project_info: Optional[ProjectInfo] = None


class ProcessedSOW(BaseModel):
    """Structured SOW data parsed from Document Intelligence."""

    blob_name: str
    company: str
    sow_id: str
    project_title: str
    full_text: str
    processing_type: SOWProcessingType
    sections: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list)
    project_info: Optional[ProjectInfo] = None
    raw_extraction: Optional[dict] = None



