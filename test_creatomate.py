#!/usr/bin/env python3
"""
Test script for CreatoMate integration
This script provides a simplified way to test the CreatoMate API integration
without loading all the dependencies of the main script.
"""

import os
import sys
import json
import time
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_creatomate_video(cloudinary_urls=None):
    """Create a video with CreatoMate API"""
    logger.info("Creating video with CreatoMate...")
    
    # Get API key from environment
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        logger.error("CREATOMATE_API_KEY is not set in environment variables")
        return "error_no_api_key"
    
    logger.info(f"Using CreatoMate API key: {api_key[:4]}...{api_key[-4:]}")
    
    # Use default URLs if none provided
    if not cloudinary_urls:
        cloudinary_urls = {
            "intro_movie1": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652709/heygen_videos/heygen_intro_movie1.mp4",
            "movie2": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652716/heygen_videos/heygen_movie2.mp4",
            "movie3": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652720/heygen_videos/heygen_movie3.mp4"
        }
    
    # Movie covers
    cloudinary_movie_covers = [
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png"
    ]
    
    # Movie clips
    clip_url1 = "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4"
    clip_url2 = "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4"
    clip_url3 = "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
    
    # Create a sequential timeline with all source elements
    source = {
        "width": 720,
        "height": 1280,
        "elements": [
            # HeyGen intro video + movie1
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": cloudinary_urls.get("intro_movie1", "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652709/heygen_videos/heygen_intro_movie1.mp4")
            },
            # Movie 1 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": cloudinary_movie_covers[0],
                "duration": 3
            },
            # Movie 1 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": clip_url1,
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie2 video
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": cloudinary_urls.get("movie2", "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652716/heygen_videos/heygen_movie2.mp4")
            },
            # Movie 2 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": cloudinary_movie_covers[1],
                "duration": 3
            },
            # Movie 2 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": clip_url2,
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie3 video
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": cloudinary_urls.get("movie3", "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652720/heygen_videos/heygen_movie3.mp4")
            },
            # Movie 3 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": cloudinary_movie_covers[2],
                "duration": 3
            },
            # Movie 3 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": clip_url3,
                "trim_end": 8,
                "trim_start": 0
            }
        ],
        "frame_rate": 30,
        "output_format": "mp4",
        "timeline_type": "sequential"
    }
    
    # Prepare the payload for the Creatomate API
    payload = {
        "source": source,
        "output_format": "mp4",
        "render_scale": 1
    }
    
    logger.info("Sending request to CreatoMate API...")
    
    try:
        # Make the API request to Creatomate
        response = requests.post(
            "https://api.creatomate.com/v1/renders",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"CreatoMate API response status: {response.status_code}")
        
        if response.status_code in [200, 201, 202]:  # 202 Accepted is valid for async processing
            result = response.json()
            logger.info(f"CreatoMate API response: {result}")
            
            if isinstance(result, list) and len(result) > 0:
                creatomate_id = result[0].get("id", "")
            elif isinstance(result, dict):
                creatomate_id = result.get("id", "")
            else:
                creatomate_id = f"unknown_format"
                
            logger.info(f"Generated CreatoMate video ID: {creatomate_id}")
            
            # Save response to file
            with open("creatomate_response.json", "w") as f:
                if isinstance(result, list):
                    json.dump(result[0], f, indent=2)
                else:
                    json.dump(result, f, indent=2)
            
            return creatomate_id
        else:
            logger.error(f"CreatoMate API error: {response.status_code} - {response.text}")
            return f"error_{response.status_code}"
    except Exception as e:
        logger.error(f"Exception when calling CreatoMate API: {str(e)}")
        return f"exception_{e}"

def check_creatomate_status(render_id):
    """Check the status of a CreatoMate render job"""
    logger.info(f"Checking status of CreatoMate render: {render_id}")
    
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        logger.error("CREATOMATE_API_KEY is not set in environment variables")
        return {"error": "API key not found"}
    
    try:
        response = requests.get(
            f"https://api.creatomate.com/v1/renders/{render_id}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"CreatoMate status: {result}")
            return result
        else:
            logger.error(f"Error checking CreatoMate status: {response.status_code} - {response.text}")
            return {"error": f"API error: {response.status_code}", "details": response.text}
    
    except Exception as e:
        logger.error(f"Exception when checking CreatoMate status: {str(e)}")
        return {"error": str(e)}


def wait_for_completion(render_id, timeout_seconds=300, interval_seconds=10):
    """Wait for a CreatoMate render to complete"""
    logger.info(f"Waiting for CreatoMate render {render_id} to complete")
    start_time = time.time()
    elapsed_time = 0
    
    while elapsed_time < timeout_seconds:
        status = check_creatomate_status(render_id)
        
        # Check if there's an error in the response
        if "error" in status:
            logger.error(f"Error checking status: {status['error']}")
            return status
        
        # Check if the render is complete
        if status.get("status") in ["succeeded", "failed"]:
            logger.info(f"Render complete with status: {status.get('status')}")
            return status
        
        # Save current status to file
        status_file = f"creatomate_status_{render_id}.json"
        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)
            
        logger.info(f"Render status: {status.get('status')}. Waiting {interval_seconds} seconds...")
        
        # Sleep and update elapsed time
        time.sleep(interval_seconds)
        elapsed_time = time.time() - start_time
    
    logger.warning(f"Timeout after {timeout_seconds} seconds waiting for render completion")
    return {"error": "timeout", "render_id": render_id, "elapsed_time": elapsed_time}


def download_creatomate_video(render_id, output_dir="videos"):
    """Download a completed CreatoMate video"""
    logger.info(f"Downloading CreatoMate video {render_id}")
    
    # First check status to get URL
    status = check_creatomate_status(render_id)
    
    if "error" in status:
        return {"error": status["error"], "message": "Failed to check status"}
    
    if status.get("status") != "succeeded":
        return {"error": "render_not_complete", "status": status.get("status")}
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get download URL
    download_url = status.get("url")
    if not download_url:
        return {"error": "no_download_url", "status": status}
    
    try:
        # Download the video
        output_path = os.path.join(output_dir, f"creatomate_{render_id}.mp4")
        
        logger.info(f"Downloading from {download_url} to {output_path}")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Video downloaded to {output_path}")
        return {"success": True, "file_path": output_path}
    
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return {"error": str(e), "message": "Failed to download video"}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test CreatoMate Integration")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true", help="Create a new CreatoMate video")
    group.add_argument("--check", help="Check the status of a CreatoMate render")
    group.add_argument("--wait", help="Wait for a CreatoMate render to complete")
    group.add_argument("--download", help="Download a completed CreatoMate video")
    
    # Additional options
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds when waiting (default: 300)")
    parser.add_argument("--output-dir", default="videos", help="Directory to save downloaded videos (default: videos)")
    
    args = parser.parse_args()
    
    if args.create:
        print("Creating CreatoMate video...")
        render_id = create_creatomate_video()
        print(f"CreatoMate render ID: {render_id}")
        
        # Ask if user wants to wait for completion
        wait_choice = input("Wait for CreatoMate rendering to complete? (y/n): ").lower()
        if wait_choice == 'y' or wait_choice == 'yes':
            status = wait_for_completion(render_id, timeout_seconds=args.timeout)
            print(json.dumps(status, indent=2))
            
            if status.get("status") == "succeeded":
                download_choice = input("Video is ready! Download now? (y/n): ").lower()
                if download_choice == 'y' or download_choice == 'yes':
                    result = download_creatomate_video(render_id, output_dir=args.output_dir)
                    print(json.dumps(result, indent=2))
    
    elif args.check:
        print(f"Checking status of render: {args.check}")
        status = check_creatomate_status(args.check)
        print(json.dumps(status, indent=2))
        
    elif args.wait:
        print(f"Waiting for render to complete: {args.wait}")
        status = wait_for_completion(args.wait, timeout_seconds=args.timeout)
        print(json.dumps(status, indent=2))
        
    elif args.download:
        print(f"Downloading CreatoMate video: {args.download}")
        result = download_creatomate_video(args.download, output_dir=args.output_dir)
        print(json.dumps(result, indent=2))
