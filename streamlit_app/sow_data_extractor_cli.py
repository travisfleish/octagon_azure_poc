#!/usr/bin/env python3
"""
SOW Data Extractor CLI
======================

Command-line interface for the SOW Data Extractor using the SOWExtractionService.
This maintains the original functionality while using the new service architecture.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import argparse

# Add the services directory to the path
sys.path.append(str(Path(__file__).parent / "services"))

from sow_extraction_service import SOWExtractionService, ExtractionProgress


def progress_callback(progress: ExtractionProgress):
    """Progress callback for CLI output"""
    print(f"  {progress.stage}: {progress.message} ({progress.percentage}%)")


async def main():
    """Main execution function"""
    print("🚀 SOW Data Extractor Starting...")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # CLI args
    parser = argparse.ArgumentParser(description="SOW Data Extractor")
    parser.add_argument('--file', dest='single_file', type=str, default='', help='Process only this file path')
    parser.add_argument('--skip-uploads', dest='skip_uploads', action='store_true', help='Skip Azure Storage uploads')
    args = parser.parse_args()

    # Initialize extractor service
    extractor = SOWExtractionService()
    extractor.set_progress_callback(progress_callback)
    await extractor.initialize()
    
    # Process single file or all
    results = []
    if args.single_file:
        target = Path(args.single_file)
        if not target.is_absolute():
            # Resolve relative to repo root
            target = Path(__file__).parent.parent / target
        if not target.exists():
            print(f"❌ Target file not found: {target}")
            return
        res = await extractor.process_single_sow(target, skip_uploads=args.skip_uploads)
        results = [res]
    else:
        results = await extractor.process_all_sows()
    
    if results:
        # Save to spreadsheet
        filename = extractor.save_to_spreadsheet(results)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 EXTRACTION SUMMARY")
        print("=" * 50)
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        print(f"✅ Successful: {len(successful_results)}")
        print(f"❌ Failed: {len(failed_results)}")
        
        for result in successful_results:
            if result.data:
                print(f"\n📄 {result.file_name}")
                print(f"   Client: {result.data.get('client_name', 'Unknown')}")
                print(f"   Project: {result.data.get('project_title', 'Unknown')}")
                print(f"   Length: {result.data.get('project_length', 'Unknown')}")
                print(f"   Deliverables: {len(result.data.get('deliverables', []))} items")
                print(f"   Exclusions: {len(result.data.get('exclusions', []))} items")
                print(f"   Staffing Plan: {len(result.data.get('staffing_plan', []))} people")
                print(f"   Processing Time: {result.processing_time:.2f}s")
        
        if failed_results:
            print(f"\n❌ Failed Extractions:")
            for result in failed_results:
                print(f"   {result.file_name}: {result.error}")
        
        if not args.single_file:
            print(f"\n✅ Extraction complete! Results saved to: {filename}")
        else:
            # For single file, pretty-print staffing plan for verification
            r = results[0]
            if r.success and r.data:
                import json as _json
                plan = r.data.get('staffing_plan', [])
                print("\n📄 Staffing plan (minimal entries):")
                print(_json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        print("❌ No results to save")


if __name__ == "__main__":
    asyncio.run(main())
