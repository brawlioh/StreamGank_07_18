#!/usr/bin/env python3
"""
Test script for direct Vizard AI API integration with YouTube trailers.
This script extracts highlights from YouTube trailers using Vizard AI,
downloads the clips, and uploads them to Cloudinary for use with Creatomate.
"""

import os
import sys
import time
import argparse
from dotenv import load_dotenv

# Import Vizard modules
from ai.vizard_client import VizardAIClient
from ai.extract_highlights import extract_highlights_with_vizard, process_vizard_highlights_for_creatomate

def main():
    """Main function to run the test"""
    parser = argparse.ArgumentParser(description="Test Vizard AI API integration")
    parser.add_argument("--youtube-url", required=True, help="YouTube URL of the trailer to process")
    parser.add_argument("--movie-title", default="Test Movie", help="Movie title for naming the clips")
    parser.add_argument("--num-clips", type=int, default=3, help="Number of highlight clips to extract")
    parser.add_argument("--clip-length", type=int, default=2, choices=[1, 2, 3], 
                        help="Clip length: 1=short (3-8s), 2=medium (5-12s), 3=long (8-20s)")
    parser.add_argument("--output-dir", default="temp_clips", help="Directory for downloaded clips")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with full error output")
    
    args = parser.parse_args()
    
    # Load environment variables (including VIZARD_API_KEY)
    load_dotenv()
    
    # Check if API key is available
    api_key = os.environ.get("VIZARD_API_KEY")
    if not api_key:
        print("❌ Error: VIZARD_API_KEY environment variable not set")
        print("Please set it in your .env file or environment")
        return 1
    
    print(f"🚀 Starting Vizard AI API Test")
    print(f"===========================")
    print(f"YouTube URL: {args.youtube_url}")
    print(f"Movie Title: {args.movie_title}")
    print(f"Number of clips: {args.num_clips}")
    print(f"Clip length setting: {args.clip_length}")
    print(f"Output directory: {args.output_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Step 1: Try direct Vizard AI client first for testing API
    print(f"\n📋 Step 1: Testing direct Vizard AI client API connection")
    try:
        # Create Vizard client
        vizard_client = VizardAIClient(api_key)
        
        print(f"🔄 Testing API connectivity with direct client...")
        # Test by creating a project with the YouTube URL
        project_result = vizard_client.create_project(
            video_url=args.youtube_url,
            options={
                "clipCount": args.num_clips,
                "minLength": 5,  # Medium length default
                "maxLength": 10
            }
        )
        
        if "error" in project_result:
            print(f"❌ API test failed: {project_result['error']}")
            if args.debug:
                print(f"\n🔍 Debug info: {project_result}")
            return 1
            
        project_id = project_result.get("projectId") or project_result.get("id")
        if not project_id:
            print("❌ API test failed: No project ID returned")
            if args.debug:
                print(f"\n🔍 Debug info: {project_result}")
            return 1
            
        print(f"✅ API connection successful! Project ID: {project_id}")
    except Exception as e:
        print(f"❌ API test failed with exception: {str(e)}")
        if args.debug:
            import traceback
            print("\n🔍 Debug traceback:")
            traceback.print_exc()
        return 1
        
    # Step 2: Extract highlights using the extraction utility
    print(f"\n📋 Step 2: Extracting highlights with Vizard AI")
    try:
        highlight_clips = extract_highlights_with_vizard(
            youtube_url=args.youtube_url,
            movie_title=args.movie_title,
            num_clips=args.num_clips,
            clip_length=args.clip_length,
            output_dir=args.output_dir
        )
        
        if not highlight_clips:
            print("❌ Failed to extract any highlight clips")
            return 1
    except Exception as e:
        print(f"❌ Highlight extraction failed: {str(e)}")
        if args.debug:
            import traceback
            print("\n🔍 Debug traceback:")
            traceback.print_exc()
        return 1
    
    print(f"✅ Successfully extracted {len(highlight_clips)} highlights")
    
    # Step 2: Upload highlights to Cloudinary for Creatomate
    print(f"\n📋 Step 2: Uploading highlights to Cloudinary")
    cloudinary_urls = process_vizard_highlights_for_creatomate(
        highlight_clips=highlight_clips,
        folder="vizard_test_clips"
    )
    
    if not cloudinary_urls:
        print("❌ Failed to upload any clips to Cloudinary")
        return 1
    
    print(f"✅ Successfully uploaded {len(cloudinary_urls)} clips to Cloudinary")
    print(f"\nCloudinary URLs:")
    for i, url in enumerate(cloudinary_urls):
        print(f"{i+1}. {url}")
    
    print(f"\n🎉 Test completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
