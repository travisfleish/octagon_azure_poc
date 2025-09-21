from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, File, HTTPException, UploadFile, Form

from ..models import ProcessedSOW, SOWDocument, StaffingPlan, SOWProcessingType
from ..services import AzureStorageService, DocumentIntelligenceService, OpenAIService, SearchService, StaffingPlanService
from ..services.enhanced_staffing_service import EnhancedStaffingPlanService


router = APIRouter(prefix="", tags=["sow"])


# In-memory job tracking for demo purposes
JOB_STATUS: Dict[str, str] = {}
SOW_STORE: Dict[str, SOWDocument] = {}
PROCESSED_STORE: Dict[str, ProcessedSOW] = {}
STAFFING_STORE: Dict[str, StaffingPlan] = {}


@router.post("/upload-sow")
async def upload_sow(
    file: UploadFile = File(...),
    processing_type: str = Form(...)
) -> dict:
    """Upload a SOW file to Azure Blob Storage with specified processing type."""

    if file.content_type not in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    
    # Validate processing type
    try:
        processing_type_enum = SOWProcessingType(processing_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid processing type. Must be one of: {[t.value for t in SOWProcessingType]}"
        )

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
        processing_type=processing_type_enum,
    )
    SOW_STORE[file_id] = sow_doc

    # Kick off background processing based on type
    JOB_STATUS[file_id] = "queued"
    asyncio.create_task(_process_sow_job(file_id, blob_name, processing_type_enum))

    return {
        "file_id": file_id, 
        "blob_url": blob_url, 
        "processing_type": processing_type_enum.value,
        "status": JOB_STATUS[file_id]
    }


async def _process_sow_job(file_id: str, blob_name: str, processing_type: SOWProcessingType) -> None:
    JOB_STATUS[file_id] = "processing"
    storage = AzureStorageService()
    di = DocumentIntelligenceService()
    
    try:
        file_bytes = await storage.download_bytes(blob_name)
        raw = await di.extract_structure(file_bytes, blob_name)
        processed = ProcessedSOW(
            blob_name=raw.get("blob_name", blob_name),
            company=raw.get("company", "Unknown"),
            sow_id=raw.get("sow_id", file_id),
            project_title=raw.get("project_title", "Unknown Project"),
            full_text=raw.get("full_text", ""),
            processing_type=processing_type,
            sections=raw.get("sections", []),
            key_entities=raw.get("key_entities", []),
            raw_extraction=raw
        )
        PROCESSED_STORE[file_id] = processed

        if processing_type == SOWProcessingType.HISTORICAL:
            # Historical SOW: Extract existing staffing plan for database
            # This would extract the staffing plan that already exists in the document
            # For now, we'll mark it as historical data
            staffing_plan = StaffingPlan(
                sow_id=file_id,
                summary="Historical SOW - Existing staffing plan extracted",
                roles=[],  # Would be populated from document extraction
                confidence=1.0,  # Historical data is considered accurate
                related_projects=[]
            )
            JOB_STATUS[file_id] = "completed_historical"
            
        elif processing_type == SOWProcessingType.NEW_STAFFING:
            # New SOW: Generate staffing plan using enhanced business rules engine
            enhanced_service = EnhancedStaffingPlanService()
            # Use the LLM data from the extraction
            llm_data = raw.get("llm", {})
            staffing_plan = enhanced_service.generate_staffing_plan_from_sow(processed, llm_data)
            JOB_STATUS[file_id] = "completed_new_staffing"
        
        STAFFING_STORE[file_id] = staffing_plan
        
        # TODO: Add vector search for similar projects in future iteration
        # search = SearchService()
        # related = await search.find_similar(text=str(staffing_plan.model_dump()))
        
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


@router.get("/staffing-recommendations/{sow_id}")
async def get_staffing_recommendations(sow_id: str) -> dict:
    """Get enhanced staffing recommendations with business rules information"""
    
    # Get the processed SOW
    processed_sow = PROCESSED_STORE.get(sow_id)
    if not processed_sow:
        raise HTTPException(status_code=404, detail="Processed SOW not found")
    
    # Get the staffing plan
    staffing_plan = STAFFING_STORE.get(sow_id)
    if not staffing_plan:
        raise HTTPException(status_code=404, detail="Staffing plan not found")
    
    # Generate enhanced recommendations
    enhanced_service = EnhancedStaffingPlanService()
    recommendations = enhanced_service.get_staffing_recommendations(processed_sow)
    
    # Add basic plan information
    recommendations.update({
        "sow_id": sow_id,
        "plan_summary": staffing_plan.summary,
        "role_count": len(staffing_plan.roles),
        "total_fte_percentage": sum(role.allocation_percent for role in staffing_plan.roles),
        "processing_timestamp": datetime.utcnow(),
        "status": JOB_STATUS.get(sow_id, "unknown")
    })
    
    return recommendations


@router.post("/upload-historical-sow")
async def upload_historical_sow(file: UploadFile = File(...)) -> dict:
    """Upload a historical SOW (with existing staffing plan) to add to the database."""
    
    return await upload_sow(file, SOWProcessingType.HISTORICAL.value)


@router.post("/upload-new-sow")
async def upload_new_sow(file: UploadFile = File(...)) -> dict:
    """Upload a new SOW to generate a directional staffing plan."""
    
    return await upload_sow(file, SOWProcessingType.NEW_STAFFING.value)


@router.get("/sows")
async def list_sows() -> dict:
    """List uploaded SOWs and their status."""

    return {
        "items": [
            {
                "id": s.id,
                "file_name": s.file_name,
                "uploaded_at": s.uploaded_at,
                "processing_type": s.processing_type.value,
                "status": JOB_STATUS.get(s.id, "unknown"),
            }
            for s in SOW_STORE.values()
        ]
    }


@router.get("/sows/historical")
async def list_historical_sows() -> dict:
    """List only historical SOWs."""

    return {
        "items": [
            {
                "id": s.id,
                "file_name": s.file_name,
                "uploaded_at": s.uploaded_at,
                "status": JOB_STATUS.get(s.id, "unknown"),
            }
            for s in SOW_STORE.values()
            if s.processing_type == SOWProcessingType.HISTORICAL
        ]
    }


@router.get("/sows/new-staffing")
async def list_new_staffing_sows() -> dict:
    """List only new SOWs for staffing plan generation."""

    return {
        "items": [
            {
                "id": s.id,
                "file_name": s.file_name,
                "uploaded_at": s.uploaded_at,
                "status": JOB_STATUS.get(s.id, "unknown"),
            }
            for s in SOW_STORE.values()
            if s.processing_type == SOWProcessingType.NEW_STAFFING
        ]
    }



