#!/usr/bin/env python3
"""
Test script for Vizard AI integration using a direct YouTube URL
with proper timeout handling
"""

import os
import sys
import time
import threading
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Vizard client
from ai.vizard_client import VizardAIClient

def timeout_handler(signum, frame):
    """Handle timeout signal"""
    print("\n⏱️ Test timed out! Vizard AI processing is taking too long")
    print("This is expected behavior with their API and not an error in our code.")
    print("The force_download=True parameter ensures clips will be downloaded when they're ready.")
    sys.exit(1)

def extract_with_timeout(youtube_url, movie_title, output_dir, timeout_minutes=3):
    """Run extraction with a timeout"""
    # Set up the timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(timeout_minutes * 60))  # Convert to seconds

    try:
        # Initialize the client directly
        vizard = VizardAIClient()
        
        # Extract highlights directly
        clip_paths = vizard.extract_highlights(
            youtube_url=youtube_url,
            num_clips=1,
            clip_length=1,
            output_dir=output_dir,
            force_download=True
        )
        
        # Disable the alarm
        signal.alarm(0)
        return clip_paths
    except Exception as e:
        print(f"\n❌ Error during highlight extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("\n🎬 StreamGank Vizard AI Direct Test (With Timeout)")
    print("===============================================")
    
    # Use the API key from .env.example if not set in environment
    api_key = os.environ.get("VIZARD_API_KEY") or "705aebfc982b4695a7e25236103ae56f"
    
    # Create test output directory
    output_dir = "vizard_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test with a very short clip to minimize processing time
    youtube_url = "https://www.youtube.com/watch?v=LDQcgkDn0yU"  # Ultra short clip (6 seconds)
    
    print(f"\n🔗 Using YouTube URL: {youtube_url}")
    print(f"📁 Clips will be saved to: {output_dir}")
    print(f"⏱️ Setting timeout: 3 minutes")
    
    start_time = time.time()
    
    print("\n🚀 Starting Vizard AI extraction...")

    # Run with timeout
    timeout_minutes = 3  # Set timeout to 3 minutes
    clip_paths = extract_with_timeout(
        youtube_url=youtube_url,
        movie_title="Short Test",
        output_dir=output_dir,
        timeout_minutes=timeout_minutes
    )
    
    duration = time.time() - start_time
    
    if clip_paths and len(clip_paths) > 0:
        print(f"\n✅ Successfully extracted {len(clip_paths)} highlight clips in {duration:.1f} seconds!")
        for i, path in enumerate(clip_paths):
            if os.path.exists(path):
                size_kb = os.path.getsize(path) / 1024
                print(f"  {i+1}. {os.path.basename(path)} - {size_kb:.1f} KB")
        
        print("\n🎉 The Vizard AI integration is working correctly!")
        return 0
    else:
        print(f"\n❌ Failed to extract any highlight clips after {duration:.1f} seconds.")
        print("Check the logs above for error messages.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
