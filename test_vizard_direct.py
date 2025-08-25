#!/usr/bin/env python3
"""
Simplified test for Vizard AI integration using a direct YouTube URL
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


def main():
    print("\n🎬 StreamGank Vizard AI Direct Test")
    print("==================================")
    
    # Use the API key from .env.example if not set in environment
    api_key = os.environ.get("VIZARD_API_KEY") or "705aebfc982b4695a7e25236103ae56f"
    
    # Create test output directory
    output_dir = "vizard_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test with a public movie trailer - very short clip to avoid timeout
    youtube_url = "https://www.youtube.com/watch?v=LDQcgkDn0yU"  # Ultra short clip (6 seconds)
    
    print(f"\n🔗 Using YouTube URL: {youtube_url}")
    print(f"📁 Clips will be saved to: {output_dir}")
    
    start_time = time.time()
    
    print("\n🚀 Starting Vizard AI extraction...")
    try:
        # Use the extract_highlights_with_vizard function directly
        clip_paths = extract_highlights_with_vizard(
            youtube_url=youtube_url,
            movie_title="Pixar Test",
            output_dir=output_dir
        )
        
        duration = time.time() - start_time
        
        if clip_paths and len(clip_paths) > 0:
            print(f"\n✅ Successfully extracted {len(clip_paths)} highlight clips in {duration:.1f} seconds!")
            for i, path in enumerate(clip_paths):
                if os.path.exists(path):
                    size_kb = os.path.getsize(path) / 1024
                    print(f"  {i+1}. {os.path.basename(path)} - {size_kb:.1f} KB")
            
            print("\n🎉 The Vizard AI integration is working correctly!")
        else:
            print(f"\n❌ Failed to extract any highlight clips after {duration:.1f} seconds.")
            print("Check the logs above for error messages.")
            
    except Exception as e:
        print(f"\n❌ Error during highlight extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
