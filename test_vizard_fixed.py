#!/usr/bin/env python3
"""
Test script for the fixed Vizard client
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Vizard client
from ai.vizard_client import VizardAIClient
from ai.extract_highlights import extract_highlights_with_vizard


def test_clip_urls_extraction(client, project_details):
    print("\n🧪 Testing video URL extraction...")
    
    # Extract videos array
    clips = []
    if "videos" in project_details:
        videos = project_details["videos"]
        print(f"Found {len(videos)} videos in 'videos' key")
        
        # Extract videoUrl from each video
        for video in videos:
            if "videoUrl" in video:
                clips.append(video["videoUrl"])
                print(f"  - Found video URL: {video['videoUrl'][:50]}...")
                if "title" in video:
                    print(f"    Title: {video['title']}")
    
    print(f"✅ Extracted {len(clips)} clip URLs")
    return clips
        
def test_download_highlights(client, project_id, output_dir):
    print("\n🧪 Testing download_highlights method...")
    
    # Download the highlights for the project
    downloaded_files = client.download_highlights(
        project_id=project_id, 
        output_dir=output_dir,
        force_download=True
    )
    
    print(f"✅ Downloaded {len(downloaded_files)} clips to {output_dir}")
    
    # Print the downloaded files
    for i, filepath in enumerate(downloaded_files):
        print(f"  - Clip {i+1}: {os.path.basename(filepath)}")
        filesize = os.path.getsize(filepath) / 1024 / 1024  # MB
        print(f"    Size: {filesize:.2f} MB")
        
    return downloaded_files

def main():
    print("\n🎬 StreamGank Vizard AI Fixed Client Test")
    print("===================================")
    
    # Create test output directory
    output_dir = "vizard_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test with a previously completed project ID from the dashboard
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        print(f"\n🔗 Using existing project ID: {project_id}")
    else:
        # Default to one from the screenshot
        project_id = "23157540"
        print(f"\n🔗 Using default project ID from screenshot: {project_id}")
    
    # Initialize client
    client = VizardAIClient()
    
    start_time = time.time()
    
    try:
        print("\n🚀 Testing fixed wait_for_completion method...")
        # Test the wait_for_completion method directly with a known completed project
        status = client.wait_for_completion(project_id, initial_delay=1, retry_delay=3)
        
        duration = time.time() - start_time
        
        if status:
            print(f"\n✅ Successfully retrieved project status in {duration:.1f} seconds!")
            
            # Check if we got videos directly in the status response
            if "videos" in status and isinstance(status["videos"], list) and len(status["videos"]) > 0:
                print(f"Found {len(status['videos'])} videos in direct response")
                for i, video in enumerate(status['videos']):
                    print(f"  - Video {i+1}: {video.get('title', 'Untitled')}")
                    print(f"    Video URL: {video.get('videoUrl', 'No URL found')[:50]}...")
                    
                # Test the video URL extraction
                clip_urls = test_clip_urls_extraction(client, status)
                
                # Test the download_highlights method
                if clip_urls:
                    downloaded_files = test_download_highlights(client, project_id, output_dir)
                    
                    if downloaded_files:
                        print(f"\n🎉 All tests passed! The fixed Vizard client is working correctly!")
                    else:
                        print(f"\n⚠️ Downloaded clips test failed. Check logs above.")
                else:
                    print(f"\n⚠️ Extract clips test failed. Check logs above.")
            else:
                print(f"\n⚠️ No videos found in direct response. Check response structure:")
                import json
                print(json.dumps(list(status.keys()), indent=2))
                if "data" in status and "videos" in status["data"]:
                    print(f"Found {len(status['data']['videos'])} videos in status['data']['videos']")
                    # Test with this structure instead
                    clip_urls = test_clip_urls_extraction(client, status["data"])
                    
                    # Continue with download test
                    if clip_urls:
                        downloaded_files = test_download_highlights(client, project_id, output_dir)
                    
                        if downloaded_files:
                            print(f"\n🎉 All tests passed! The fixed Vizard client is working correctly!")
                else:
                    print("❌ No videos found in any expected location in the response")
        else:
            print(f"\n❌ Failed to retrieve project status after {duration:.1f} seconds.")
            print("Check the logs above for error messages.")
            
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
