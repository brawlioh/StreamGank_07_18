#!/usr/bin/env python3
"""
Test script for downloading highlights from an existing Vizard project.
"""

import os
import sys
import json
from dotenv import load_dotenv
import traceback

# Try importing the Vizard modules
try:
    from ai.vizard_client import VizardAIClient
    print("✅ Successfully imported VizardAIClient")
except Exception as e:
    print(f"❌ Error importing VizardAIClient: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

def main():
    # Load environment variables
    load_dotenv()
    print("📋 Environment loaded")
    
    # Check API key
    api_key = os.environ.get("VIZARD_API_KEY")
    if not api_key:
        print("❌ VIZARD_API_KEY not found in environment")
        sys.exit(1)
    else:
        print(f"✅ VIZARD_API_KEY found (length: {len(api_key)})")
    
    # Initialize client
    try:
        print("🔄 Initializing VizardAIClient...")
        client = VizardAIClient(api_key)
        print(f"✅ Client initialized with API endpoint: {client.API_ENDPOINT}")
    except Exception as e:
        print(f"❌ Error initializing client: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    
    # This is where we would use an existing project ID
    # For example: project_id = "23104656"
    project_id = input("Enter existing project ID: ")
    
    print(f"🔍 Testing with existing project ID: {project_id}")
    
    # Try getting project status
    try:
        print("\n=== CHECKING PROJECT STATUS ===")
        status_result = client.get_project_status(project_id)
        print(f"Current status: {json.dumps(status_result, indent=2)}")
        
        # Show endpoint tracking information
        print("\n=== CLIENT ENDPOINT TRACKING ===")
        print(f"Successful endpoints: {client.successful_endpoints}")
        print(f"Project endpoint map: {client.project_endpoint_map}")
    except Exception as e:
        print(f"❌ Error checking project status: {str(e)}")
        traceback.print_exc()
    
    # Try downloading highlights
    try:
        print("\n=== DOWNLOADING HIGHLIGHTS ===")
        output_dir = "./test_existing_vizard_clips"
        print(f"Output directory: {output_dir}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        clip_paths = client.download_highlights(
            project_id=project_id,
            movie_title="Test Existing Movie",
            output_dir=output_dir,
            force_download=True  # Force download even if project status is unknown
        )
        
        print(f"\n=== DOWNLOADED CLIPS ===")
        print(f"Number of clips: {len(clip_paths)}")
        for i, path in enumerate(clip_paths):
            print(f"{i+1}. {path}")
        
        return 0
    except Exception as e:
        print(f"❌ Error downloading highlights: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
