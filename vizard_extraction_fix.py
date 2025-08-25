#!/usr/bin/env python3
"""
Test the fixed Vizard extraction process with proper video URL handling
"""

import os
import sys
import time
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Vizard client
from ai.vizard_client import VizardAIClient
from ai.extract_highlights import extract_highlights_with_vizard


def main():
    print("\n🎬 StreamGank Vizard AI Video Extraction Test")
    print("==========================================")
    
    # Use the API key from .env
    api_key = os.environ.get("VIZARD_API_KEY")
    if not api_key:
        print("❌ Error: VIZARD_API_KEY not found in environment")
        return 1
    
    # Create test output directory
    output_dir = "vizard_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test with a completed project ID
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        # Default to one from previous tests
        project_id = "23157540"
        
    print(f"\n🔗 Using project ID: {project_id}")
    
    # Initialize client
    client = VizardAIClient()
    
    # First, get project details to confirm videos are available
    print("\n🔍 Getting project details")
    project_details = client.get_existing_project(project_id)
    
    if not project_details or "error" in project_details:
        print(f"❌ Error: Failed to get project details")
        return 1
        
    # Print project structure
    if isinstance(project_details, dict):
        print(f"Project details keys: {list(project_details.keys())}")
        
        # Look for videos
        videos = None
        if "videos" in project_details:
            videos = project_details["videos"]
        elif "data" in project_details and "videos" in project_details["data"]:
            videos = project_details["data"]["videos"]
            
        if videos and isinstance(videos, list):
            print(f"✅ Found {len(videos)} videos in project")
            
            # Extract URLs
            video_urls = []
            for video in videos:
                if isinstance(video, dict) and "videoUrl" in video:
                    video_urls.append(video["videoUrl"])
                    print(f"  - Title: {video.get('title', 'Unknown')}")
                    print(f"    URL: {video['videoUrl'][:50]}...")
                    
            print(f"Total video URLs found: {len(video_urls)}")
            
            if video_urls:
                # Try downloading using client's download_clips_from_urls method
                print("\n📥 Downloading videos")
                try:
                    downloaded_paths = client.download_clips_from_urls(
                        clip_urls=video_urls,
                        movie_title="TestMovie",
                        output_dir=output_dir
                    )
                    
                    if downloaded_paths:
                        print(f"✅ Successfully downloaded {len(downloaded_paths)} videos:")
                        for path in downloaded_paths:
                            print(f"  - {path}")
                    else:
                        print(f"❌ No videos were downloaded")
                        
                except Exception as e:
                    print(f"❌ Error downloading videos: {str(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            print("❌ No videos found in project details")
            
    # Now, test the direct highlight extraction with a YouTube URL
    if len(sys.argv) > 2:
        youtube_url = sys.argv[2]
        print(f"\n🎥 Testing direct extraction with YouTube URL: {youtube_url}")
        
        try:
            # Test the extract_highlights_with_vizard function
            clip_paths = extract_highlights_with_vizard(
                youtube_url=youtube_url,
                movie_title="TestDirectExtraction",
                num_clips=1,
                clip_length=1,
                output_dir=output_dir
            )
            
            if clip_paths:
                print(f"✅ Successfully extracted {len(clip_paths)} highlights directly:")
                for path in clip_paths:
                    print(f"  - {path}")
            else:
                print(f"❌ No highlights were extracted from YouTube URL")
                
        except Exception as e:
            print(f"❌ Error during direct extraction: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
