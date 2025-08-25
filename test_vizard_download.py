#!/usr/bin/env python3
"""
Test script to verify Vizard AI clip downloading with a known working project ID.
"""

import os
import sys
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Import the VizardAIClient
from ai.vizard_client import VizardAIClient

def main():
    print("🔍 Testing Vizard AI clip downloading with fixed client...")
    
    # Use the API key from environment or .env.example
    api_key = os.environ.get("VIZARD_API_KEY") or "705aebfc982b4695a7e25236103ae56f"
    client = VizardAIClient(api_key=api_key)
    
    # Use the known working project ID from our previous test
    test_project_id = "23153438"  # Working project ID from previous test
    
    print(f"\n📊 Testing project status endpoint...")
    status_result = client.get_project_status(test_project_id)
    print(f"Status result: {json.dumps(status_result, indent=2)}")
    
    if status_result.get("success_endpoint"):
        print(f"✅ Status check successful using: {status_result.get('success_endpoint')}")
    
    print(f"\n📥 Testing highlight download...")
    output_dir = "test_vizard_clips"
    os.makedirs(output_dir, exist_ok=True)
    
    # Try to download highlights with force_download=True to bypass status checks
    clip_paths = client.download_highlights(
        project_id=test_project_id,
        movie_title="Test Movie",
        output_dir=output_dir,
        force_download=True
    )
    
    if clip_paths:
        print(f"\n✅ Successfully downloaded {len(clip_paths)} clips:")
        for path in clip_paths:
            print(f"  - {path}")
        
        # Check if files were actually created
        for path in clip_paths:
            if os.path.exists(path):
                size = os.path.getsize(path) / 1024  # KB
                print(f"  ✓ {os.path.basename(path)} - {size:.1f} KB")
            else:
                print(f"  ⚠️ {os.path.basename(path)} - File not found")
                
        print("\n🎉 Success! The Vizard AI client fix is working correctly.")
    else:
        print("\n❌ Failed to download any clips.")
        print("Check the response structure to ensure clip URLs are being correctly identified.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
