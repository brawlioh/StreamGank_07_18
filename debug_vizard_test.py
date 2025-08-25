#!/usr/bin/env python3
"""
Debug script for Vizard AI API testing with detailed output and error tracing.
"""

import os
import sys
import traceback
from dotenv import load_dotenv
import json

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
    
    # Initialize client with explicit debugging
    try:
        print("🔄 Initializing VizardAIClient...")
        client = VizardAIClient(api_key)
        print(f"✅ Client initialized with API endpoint: {client.API_ENDPOINT}")
    except Exception as e:
        print(f"❌ Error initializing client: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    
    # Test YouTube URL
    youtube_url = "https://www.youtube.com/watch?v=sefHlA4neas"
    print(f"🎬 Testing with YouTube URL: {youtube_url}")
    
    # Try creating a project
    try:
        print("🔄 Creating Vizard AI project...")
        options = {
            "clipCount": 1,
            "minLength": 5,
            "maxLength": 10
        }
        print(f"📋 Options: {json.dumps(options, indent=2)}")
        
        print("\n=== CREATING TEST PROJECT ===")
        project_result = client.create_project(
            video_url=youtube_url,
            options={"title": "Debug Vizard Test"}
        )
        
        if "error" in project_result:
            print(f"❌ Failed to create project: {project_result['error']}")
            sys.exit(1)
            
        print(f"\n=== PROJECT CREATION RESPONSE ===")
        print(json.dumps(project_result, indent=2))
        
        # Show successful endpoint that was tracked
        if "success_endpoint" in project_result:
            print(f"\n=== SUCCESSFUL ENDPOINT TRACKED ===")
            print(f"✅ Successful endpoint: {project_result['success_endpoint']}")
            print(f"✅ This endpoint will be prioritized for future API calls with this project ID")
        
        # Show endpoint tracking information
        print("\n=== CLIENT ENDPOINT TRACKING ===")
        print(f"Successful endpoints: {client.successful_endpoints}")
        print(f"Project endpoint map: {client.project_endpoint_map}")
        
        project_id = project_result.get("projectId") or project_result.get("id")
        if not project_id:
            print("❌ No project ID returned")
            sys.exit(1)
            
        print(f"✅ Project created with ID: {project_id}")
        
        # Store the raw project ID for consistent use
        raw_project_id = project_id
        
        # Check status before waiting
        print("\n=== CHECKING PROJECT STATUS ===")
        status_response = client.get_project_status(raw_project_id)
        print(f"Initial status: {json.dumps(status_response, indent=2)}")
        
        # Show endpoint tracking information after status check
        print("\n=== UPDATED ENDPOINT TRACKING AFTER STATUS CHECK ===")
        print(f"Successful endpoints: {client.successful_endpoints}")
        print(f"Project endpoint map: {client.project_endpoint_map}")
        
        # Check if the status check used the same endpoint as project creation
        if "success_endpoint" in status_response:
            success_endpoint = status_response["success_endpoint"]
            if raw_project_id in client.project_endpoint_map and \
               success_endpoint == client.project_endpoint_map[raw_project_id]:
                print(f"✅ Success! Status check used the same base endpoint as project creation")
            else:
                print(f"🔔 Status check used a different endpoint than project creation")
                print(f"   Status endpoint: {success_endpoint}")
                print(f"   Project creation endpoint: {client.project_endpoint_map.get(raw_project_id, 'Not found')}")
        else:
            print(f"⚠️ Status response doesn't contain success_endpoint information")
        
        # Wait for project completion
        print("🕒 Waiting for project to complete...")
        status_result = client.wait_for_completion(project_id)
        print(f"📋 Final status: {json.dumps(status_result, indent=2)}")
        
        # Download highlights
        print("📥 Downloading highlights...")
        clip_paths = client.download_highlights(
            project_id=project_id,
            movie_title="Test Movie",
            output_dir="temp_clips",
            force_download=True  # Force download even if project is in UNKNOWN state for testing
        )
        
        print(f"📋 Downloaded clips: {clip_paths}")
        print(f"✅ Testing completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
