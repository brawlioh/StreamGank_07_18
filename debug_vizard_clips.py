#!/usr/bin/env python3
"""
Debug script to examine video clip extraction from Vizard API responses
"""

import os
import json
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Vizard client
from ai.vizard_client import VizardAIClient

def explore_dict(data, prefix="", max_depth=3, current_depth=0):
    """Recursively explore dictionary structure to find video URLs"""
    if current_depth >= max_depth:
        return []
    
    found_paths = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            # Check if this key might contain a video URL
            if isinstance(value, str) and any(x in value.lower() for x in ["http", "mp4", "video", "m3u8"]):
                found_paths.append((current_path, value))
            
            # Recursively check nested structures
            if isinstance(value, (dict, list)):
                found_paths.extend(explore_dict(value, current_path, max_depth, current_depth + 1))
                
    elif isinstance(data, list) and data:
        # Only explore the first item in lists to avoid too much output
        if data and isinstance(data[0], (dict, list)):
            found_paths.extend(explore_dict(data[0], f"{prefix}[0]", max_depth, current_depth + 1))
            
        # Also check if any list item is a URL string
        for i, item in enumerate(data):
            if isinstance(item, str) and any(x in item.lower() for x in ["http", "mp4", "video", "m3u8"]):
                found_paths.append((f"{prefix}[{i}]", item))
    
    return found_paths

def main():
    # Check if we have a project ID from command line
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        # Default to one from the previous tests
        project_id = "23157540"

    print(f"\n🔍 Vizard API Clip Extraction Debugger")
    print(f"==================================")
    print(f"Examining project ID: {project_id}")

    # Initialize client
    client = VizardAIClient()

    # Test 1: Get project status and examine response for video content
    print("\n🧪 Test 1: Project Status Response Structure")
    print("-------------------------------------------")
    status_response = client.get_project_status(project_id)
    
    # Print the keys to understand the structure
    if isinstance(status_response, dict):
        print(f"Top-level keys: {list(status_response.keys())}")
        
        # Look for videos array
        if "videos" in status_response:
            videos = status_response["videos"]
            print(f"Found 'videos' array with {len(videos)} items")
            if videos:
                print(f"First video structure: {json.dumps(videos[0], indent=2)}")
        elif "data" in status_response and "videos" in status_response["data"]:
            videos = status_response["data"]["videos"]
            print(f"Found 'data.videos' array with {len(videos)} items")
            if videos:
                print(f"First video structure: {json.dumps(videos[0], indent=2)}")
                
        # Recursively look for any video URLs in the response
        print("\nSearching for potential video URLs in response:")
        video_paths = explore_dict(status_response)
        for path, url in video_paths:
            print(f"  - {path}: {url[:100]}...")
    else:
        print(f"Response is not a dictionary: {status_response}")

    # Test 2: Try the extract_clips method directly
    print("\n🧪 Test 2: Direct Clip Extraction")
    print("-------------------------------")
    output_dir = "vizard_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Try different variants of project ID format
        test_formats = [
            project_id,
            f"project-{project_id}",
            f"open-api-{project_id}"
        ]
        
        for format_id in test_formats:
            print(f"\nTrying format: {format_id}")
            start_time = time.time()
            
            # Test the extract_clips method
            clip_paths = client.extract_clips(
                project_id=format_id,
                force_download=True,
                output_dir=output_dir,
                movie_title="TestMovie"
            )
            
            duration = time.time() - start_time
            
            if clip_paths:
                print(f"✅ Successfully extracted {len(clip_paths)} clips in {duration:.1f} seconds!")
                for path in clip_paths:
                    print(f"  - {path}")
                # First success is enough
                break
            else:
                print(f"❌ No clips extracted with format: {format_id}")
                
    except Exception as e:
        print(f"❌ Error during clip extraction: {str(e)}")
        import traceback
        traceback.print_exc()

    # Test 3: Examine extract_clips source code paths
    print("\n🧪 Test 3: Understanding JSON Structure Path to Video URLs")
    print("------------------------------------------------------")
    
    # First get the raw response data
    project_details = client.get_existing_project(project_id)
    
    if isinstance(project_details, dict):
        print(f"Project details has keys: {list(project_details.keys())}")
        
        # Check for clips in different paths
        for path in ["clips", "data.clips", "videos", "data.videos", "highlights", "data.highlights"]:
            parts = path.split(".")
            data = project_details
            valid_path = True
            
            for part in parts:
                if part in data:
                    data = data[part]
                else:
                    valid_path = False
                    break
            
            if valid_path and isinstance(data, list):
                print(f"✓ Found array at '{path}' with {len(data)} items")
                if data and isinstance(data[0], dict):
                    print(f"  First item keys: {list(data[0].keys())}")
                    # Look for URL fields
                    for key in ["url", "videoUrl", "fileUrl", "downloadUrl", "highlightUrl"]:
                        if key in data[0]:
                            print(f"  ✓ Contains '{key}': {data[0][key][:100]}...")
            else:
                print(f"✗ Path '{path}' not found or not an array")
        
        # Try to use the same extract logic as the client
        clips = []
        
        if isinstance(project_details, list):
            clips = project_details
        elif "highlights" in project_details:
            clips = project_details["highlights"]
        elif "data" in project_details and "highlights" in project_details["data"]:
            clips = project_details["data"]["highlights"]
        elif "clips" in project_details:
            clips = project_details["clips"]
        elif "data" in project_details and "clips" in project_details["data"]:
            clips = project_details["data"]["clips"]
        elif "videos" in project_details:
            clips = project_details["videos"]
        elif "data" in project_details and "videos" in project_details["data"]:
            clips = project_details["data"]["videos"]
            
        print(f"\nExtracted {len(clips)} clips using client logic")
        
        # Now extract URLs like the client does
        clip_urls = []
        for clip in clips:
            if isinstance(clip, str):
                clip_urls.append(clip)
                print(f"  Found direct URL string: {clip[:50]}...")
            elif isinstance(clip, dict):
                # Try various known field names for the URL
                for url_field in ["url", "videoUrl", "fileUrl", "downloadUrl", "highlightUrl"]:
                    if url_field in clip:
                        clip_urls.append(clip[url_field])
                        print(f"  Found URL in '{url_field}' field: {clip[url_field][:50]}...")
                        break
        
        print(f"\nTotal URLs extracted: {len(clip_urls)}")

if __name__ == "__main__":
    main()
