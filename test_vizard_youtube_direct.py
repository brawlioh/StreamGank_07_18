#!/usr/bin/env python3
"""
Direct YouTube URL Test for Vizard AI

This script tests the Vizard AI client with a direct YouTube URL without using the database.
"""

import os
import sys
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the VizardAIClient directly
from ai.vizard_client import VizardAIClient

def test_direct_youtube_extraction():
    """Test direct extraction from a YouTube URL"""
    
    # YouTube trailer URL to test
    youtube_url = "https://www.youtube.com/watch?v=BmllggGO4pM"  # The Gray Man trailer
    
    print(f"\n🎬 Testing Vizard AI with direct YouTube URL: {youtube_url}")
    print("===========================================================\n")
    
    # Check API key
    api_key = os.environ.get("VIZARD_API_KEY")
    if not api_key:
        print("❌ VIZARD_API_KEY is not set in environment variables")
        return False
    
    print(f"📝 Using Vizard API key: {api_key[:8]}...{api_key[-4:]}")
    
    # Initialize client
    vizard_client = VizardAIClient(api_key=api_key)
    
    # Create output directory
    output_dir = "vizard_direct_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Create project
    print("\n📋 Step 1: Creating Vizard AI project...")
    options = {
        "clipCount": 1,
        "minLength": 3,
        "maxLength": 5
    }
    
    project_response = vizard_client.create_project(youtube_url, options)
    if "error" in project_response:
        print(f"❌ Failed to create project: {project_response['error']}")
        return False
    
    project_id = project_response.get("projectId")
    if not project_id:
        print("❌ No project ID returned from create_project")
        print(f"Response: {json.dumps(project_response, indent=2)}")
        return False
    
    print(f"✅ Project created with ID: {project_id}")
    
    # Step 2: Wait for project completion
    print("\n📋 Step 2: Waiting for project to complete...")
    status_response = vizard_client.wait_for_completion(project_id, initial_delay=1, max_retries=120, retry_delay=5)
    
    if "error" in status_response:
        print(f"❌ Project failed: {status_response['error']}")
        return False
    
    print(f"✅ Project completed successfully")
    print(f"Response keys: {list(status_response.keys())}")
    
    # Debug output all available videos or clips in the response
    if "videos" in status_response and isinstance(status_response["videos"], list):
        videos = status_response["videos"]
        print(f"\n📋 Found {len(videos)} videos in response:")
        for i, video in enumerate(videos, 1):
            print(f"\n--- Video {i} ---")
            if isinstance(video, dict):
                # Print key fields for debugging
                print(f"Keys: {list(video.keys())}")
                for key in ["videoUrl", "url", "transcript", "title"]:
                    if key in video:
                        print(f"{key}: {video[key][:100]}...")
    else:
        print("No 'videos' field in response")
    
    # Step 3: Download the clips
    print("\n📋 Step 3: Downloading highlight clips...")
    
    clips = vizard_client.download_highlights(
        project_id=project_id,
        movie_title="TestMovie",
        output_dir=output_dir,
        force_download=True
    )
    
    if clips:
        print(f"\n✅ Successfully downloaded {len(clips)} clips:")
        for i, clip_path in enumerate(clips, 1):
            size_mb = os.path.getsize(clip_path) / (1024 * 1024)
            print(f"  {i}. {os.path.basename(clip_path)} ({size_mb:.2f} MB)")
        return True
    else:
        print("\n❌ Failed to download any clips")
        return False

def main():
    """Main function"""
    # Check .env file existence
    if not os.path.exists(".env"):
        print("❌ .env file not found")
        print("   Please create a .env file by copying .env.example and updating the API keys")
        return 1
    
    # Run the direct test
    success = test_direct_youtube_extraction()
    
    if success:
        print("\n🎉 Direct YouTube extraction test PASSED!")
        return 0
    else:
        print("\n❌ Direct YouTube extraction test FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
