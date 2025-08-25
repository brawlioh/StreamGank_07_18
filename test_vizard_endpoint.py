#!/usr/bin/env python3
from ai.vizard_client import VizardAIClient
import os
import sys

def main():
    print("Testing Vizard AI client with updated endpoint configuration...")
    # Use the API key from .env.example
    api_key = "705aebfc982b4695a7e25236103ae56f"
    client = VizardAIClient(api_key=api_key)
    
    # Test with a project ID
    test_project_id = "23153438"  # Use the project ID from your example
    
    print(f"Testing get_project_status with project ID: {test_project_id}")
    status_result = client.get_project_status(test_project_id)
    print(f"Status result: {status_result}")
    
    if "error" in status_result and status_result.get("status") == "UNKNOWN":
        print("⚠️ Status check still failing with 404 errors")
    else:
        print("✅ Successfully retrieved project status!")
        
    # Try to download clips directly using the project query endpoint
    print(f"\nTesting download_highlights with project ID: {test_project_id}")
    output_dir = "test_vizard_clips"
    os.makedirs(output_dir, exist_ok=True)
    clip_paths = client.download_highlights(test_project_id, movie_title="Test Movie", 
                                          output_dir=output_dir, force_download=True)
    
    if clip_paths:
        print(f"✅ Successfully downloaded {len(clip_paths)} clips")
        for path in clip_paths:
            print(f"  - {path}")
    else:
        print("❌ Failed to download any clips")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
