from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..models import ProcessedSOW, SOWDocument, StaffingPlan
from ..services import AzureStorageService, DocumentIntelligenceService, OpenAIService, SearchService


router = APIRouter(prefix="", tags=["sow"])


# In-memory job tracking for demo purposes
JOB_STATUS: Dict[str, str] = {}
SOW_STORE: Dict[str, SOWDocument] = {}
PROCESSED_STORE: Dict[str, ProcessedSOW] = {}
STAFFING_STORE: Dict[str, StaffingPlan] = {}


@router.post("/upload-sow")
async def upload_sow(file: UploadFile = File(...)) -> dict:
    """Upload a SOW file to Azure Blob Storage. Accept PDF or DOCX only."""

    if file.content_type not in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    storage = AzureStorageService()
    file_id = str(uuid.uuid4())
    blob_name = f"{file_id}-{file.filename}"
    blob_url = await storage.upload_file(file, blob_name)

    sow_doc = SOWDocument(
        id=file_id,
        file_name=file.filename,
        blob_url=blob_url,
        content_type=file.content_type,
        uploaded_at=datetime.utcnow(),
    )
    SOW_STORE[file_id] = sow_doc

    # Kick off background processing
    JOB_STATUS[file_id] = "queued"
    asyncio.create_task(_process_sow_job(file_id, blob_name))

    return {"file_id": file_id, "blob_url": blob_url, "status": JOB_STATUS[file_id]}


async def _process_sow_job(file_id: str, blob_name: str) -> None:
    JOB_STATUS[file_id] = "processing"
    storage = AzureStorageService()
    di = DocumentIntelligenceService()
    try:
        file_bytes = await storage.download_bytes(blob_name)
        raw = await di.extract_structure(file_bytes)
        processed = ProcessedSOW(sow_id=file_id, raw_extraction=raw)
        PROCESSED_STORE[file_id] = processed

        # Enrich with LLM + search
        llm = OpenAIService()
        search = SearchService()
        plan_dict = await llm.suggest_staffing(processed.model_dump())
        related = await search.find_similar(text=str(plan_dict))
        plan = StaffingPlan(sow_id=file_id, related_projects=related, **plan_dict)
        STAFFING_STORE[file_id] = plan
        JOB_STATUS[file_id] = "completed"
    except Exception as exc:  # noqa: BLE001
        JOB_STATUS[file_id] = f"error: {exc}"


@router.get("/process-sow/{file_id}")
async def process_sow_status(file_id: str) -> dict:
    """Return processing status for a SOW file."""

    status = JOB_STATUS.get(file_id, "not_found")
    if status == "not_found":
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_id": file_id, "status": status}


@router.get("/staffing-plan/{sow_id}")
async def get_staffing_plan(sow_id: str) -> StaffingPlan:
    plan = STAFFING_STORE.get(sow_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Staffing plan not found")
    return plan


@router.get("/sows")
async def list_sows() -> dict:
    """List uploaded SOWs and their status."""

    return {
        "items": [
            {
                "id": s.id,
                "file_name": s.file_name,
                "uploaded_at": s.uploaded_at,
                "status": JOB_STATUS.get(s.id, "unknown"),
            }
            for s in SOW_STORE.values()
        ]
    }



