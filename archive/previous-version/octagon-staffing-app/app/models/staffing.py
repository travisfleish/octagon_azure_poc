from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class StaffingRole(BaseModel):
    role: str
    department: Optional[str] = None
    level: Optional[int] = None
    quantity: int
    allocation_percent: int = Field(ge=0, le=100)
    notes: Optional[str] = None


class StaffingPlan(BaseModel):
    """Final staffing recommendations for a SOW."""

    sow_id: str
    summary: Optional[str] = None
    roles: List[StaffingRole] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    related_projects: List[str] = Field(default_factory=list)



