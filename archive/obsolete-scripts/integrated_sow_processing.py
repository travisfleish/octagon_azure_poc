#!/usr/bin/env python3
"""
Integrated SOW Processing Pipeline with Heuristics Engine

This script combines your existing SOW processing with the new heuristics engine
to generate staffing plans automatically.
"""

import io
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "octagon-staffing-app"))

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Import existing processing functions
from process_one_sow import extract_docx_text, extract_pdf_text, process_blob
from llm_extract import llm_parse_schema

# Import new heuristics engine
from app.services.staffing_plan_service import StaffingPlanService
from app.models.sow import ProcessedSOW

# Azure Storage configuration
ACCOUNT_URL = "https://octagonstaffingstg5nww.blob.core.windows.net/"
SRC_CONTAINER = "sows"
EXTRACTED_CONTAINER = "extracted"
PARSED_CONTAINER = "parsed"
STAFFING_CONTAINER = "staffing"  # New container for staffing plans


def process_sow_with_staffing_plan(blob_name: str) -> Dict[str, Any]:
    """
    Process a single SOW with integrated staffing plan generation
    
    Args:
        blob_name: Name of the blob in Azure Storage
        
    Returns:
        Dictionary with processing results including staffing plan
    """
    
    print(f"Processing {blob_name} with integrated staffing plan generation...")
    
    # Initialize Azure Storage clients
    cred = DefaultAzureCredential()
    svc = BlobServiceClient(account_url=ACCOUNT_URL, credential=cred)
    src = svc.get_container_client(SRC_CONTAINER)
    extracted = svc.get_container_client(EXTRACTED_CONTAINER)
    parsed = svc.get_container_client(PARSED_CONTAINER)
    
    # Create staffing container if it doesn't exist
    try:
        svc.create_container(STAFFING_CONTAINER)
        print(f"Created container: {STAFFING_CONTAINER}")
    except Exception:
        pass  # Container probably already exists
    
    staffing = svc.get_container_client(STAFFING_CONTAINER)
    
    # Step 1: Process the blob using existing pipeline
    print(f"  Step 1: Processing blob with existing pipeline...")
    result_row = process_blob(src, extracted, parsed, blob_name)
    
    # Step 2: Get the LLM extraction results
    print(f"  Step 2: Retrieving LLM extraction results...")
    stem = blob_name.rsplit(".", 1)[0]
    
    try:
        # Download the parsed JSON
        parsed_blob = parsed.get_blob_client(f"{stem}.json")
        parsed_data = json.loads(parsed_blob.download_blob().readall().decode("utf-8"))
        llm_data = parsed_data.get('llm', {})
        
        if not llm_data:
            print(f"  Warning: No LLM data found for {blob_name}")
            return {
                "status": "warning",
                "message": "LLM extraction completed but no data found",
                "blob_name": blob_name,
                "result_row": result_row
            }
        
        print(f"  Found LLM data with {len(llm_data.get('roles_detected', []))} roles")
        
    except Exception as e:
        print(f"  Error retrieving LLM data: {e}")
        return {
            "status": "error",
            "message": f"Failed to retrieve LLM data: {e}",
            "blob_name": blob_name,
            "result_row": result_row
        }
    
    # Step 3: Generate staffing plan using heuristics
    print(f"  Step 3: Generating staffing plan with heuristics engine...")
    
    try:
        # Create ProcessedSOW object
        processed_sow = ProcessedSOW(
            sow_id=stem,
            sections=llm_data.get('scope_bullets', []),
            key_entities=llm_data.get('roles_detected', []),
            raw_extraction=llm_data
        )
        
        # Generate staffing plan
        staffing_service = StaffingPlanService()
        staffing_plan = staffing_service.generate_staffing_plan_from_sow(processed_sow, llm_data)
        
        print(f"  Generated staffing plan with {len(staffing_plan.roles)} roles")
        print(f"  Confidence score: {staffing_plan.confidence}")
        
    except Exception as e:
        print(f"  Error generating staffing plan: {e}")
        return {
            "status": "error",
            "message": f"Failed to generate staffing plan: {e}",
            "blob_name": blob_name,
            "result_row": result_row,
            "llm_data": llm_data
        }
    
    # Step 4: Save staffing plan to Azure Storage
    print(f"  Step 4: Saving staffing plan to storage...")
    
    try:
        # Convert staffing plan to JSON
        staffing_json = staffing_plan.model_dump_json(indent=2)
        
        # Upload to staffing container
        staffing_blob_name = f"{stem}_staffing_plan.json"
        staffing.upload_blob(
            name=staffing_blob_name,
            data=staffing_json.encode("utf-8"),
            overwrite=True
        )
        
        print(f"  Saved staffing plan: {staffing_blob_name}")
        
    except Exception as e:
        print(f"  Warning: Failed to save staffing plan: {e}")
    
    # Step 5: Return comprehensive results
    return {
        "status": "success",
        "blob_name": blob_name,
        "result_row": result_row,
        "llm_data": llm_data,
        "staffing_plan": {
            "sow_id": staffing_plan.sow_id,
            "summary": staffing_plan.summary,
            "roles_count": len(staffing_plan.roles),
            "confidence": staffing_plan.confidence,
            "roles": [
                {
                    "role": role.role,
                    "quantity": role.quantity,
                    "allocation_percent": role.allocation_percent,
                    "notes": role.notes
                }
                for role in staffing_plan.roles
            ]
        },
        "staffing_blob_name": staffing_blob_name if 'staffing_blob_name' in locals() else None
    }


def process_all_sows_with_staffing():
    """Process all SOWs in the container with staffing plan generation"""
    
    print("=" * 60)
    print("INTEGRATED SOW PROCESSING WITH STAFFING PLANS")
    print("=" * 60)
    
    # Initialize Azure Storage
    cred = DefaultAzureCredential()
    svc = BlobServiceClient(account_url=ACCOUNT_URL, credential=cred)
    src = svc.get_container_client(SRC_CONTAINER)
    
    results = []
    successful = 0
    failed = 0
    
    # Process each SOW
    for blob in src.list_blobs():
        blob_name = blob.name
        if not blob_name.lower().endswith((".pdf", ".docx")):
            continue
            
        print(f"\nProcessing: {blob_name}")
        try:
            result = process_sow_with_staffing_plan(blob_name)
            results.append(result)
            
            if result["status"] == "success":
                successful += 1
                print(f"✅ Successfully processed {blob_name}")
            else:
                failed += 1
                print(f"⚠️ {result['status']}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            failed += 1
            error_result = {
                "status": "error",
                "blob_name": blob_name,
                "message": str(e)
            }
            results.append(error_result)
            print(f"❌ Failed to process {blob_name}: {e}")
    
    # Summary
    print(f"\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total documents: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if successful > 0:
        print(f"\n✅ Successfully generated staffing plans for {successful} documents")
        print("Staffing plans saved to 'staffing' container in Azure Storage")
    
    return results


def main():
    """Main function for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process SOWs with integrated staffing plan generation")
    parser.add_argument("--blob-name", type=str, help="Process a specific blob by name")
    parser.add_argument("--all", action="store_true", help="Process all SOWs in the container")
    
    args = parser.parse_args()
    
    if args.blob_name:
        result = process_sow_with_staffing_plan(args.blob_name)
        print(f"\nResult: {json.dumps(result, indent=2)}")
    elif args.all:
        process_all_sows_with_staffing()
    else:
        print("Please specify --blob-name or --all")


if __name__ == "__main__":
    main()
