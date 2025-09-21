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
    
    # Initialize extractor service
    extractor = SOWExtractionService()
    extractor.set_progress_callback(progress_callback)
    await extractor.initialize()
    
    # Process all SOWs
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
        
        print(f"\n✅ Extraction complete! Results saved to: {filename}")
    else:
        print("❌ No results to save")


if __name__ == "__main__":
    asyncio.run(main())
