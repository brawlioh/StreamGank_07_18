#!/usr/bin/env python3
"""
CreatoMate Status Checker

This script is used to check the status of a CreatoMate video rendering job
and download the completed video when it's ready.

Usage:
    python creatomate_status.py --check-status <render_id>
    python creatomate_status.py --download <render_id>
"""

import os
import sys
import json
import time
import requests
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def check_creatomate_status(render_id):
    """
    Check the status of a CreatoMate rendering job
    
    Args:
        render_id (str): The ID of the CreatoMate rendering job
        
    Returns:
        dict: The rendering job status information
    """
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
            logger.info(f"CreatoMate status: {result.get('status', 'unknown')}")
            
            # Save the response to a file for reference
            output_dir = Path("videos")
            output_dir.mkdir(exist_ok=True)
            with open(output_dir / f"creatomate_status_{render_id}.json", "w") as f:
                json.dump(result, f, indent=2)
            
            return result
        else:
            logger.error(f"Error checking CreatoMate status: {response.status_code} - {response.text}")
            return {"error": f"API error: {response.status_code}", "details": response.text}
    
    except Exception as e:
        logger.error(f"Exception when checking CreatoMate status: {str(e)}")
        return {"error": str(e)}

def download_creatomate_video(render_id):
    """
    Download a completed CreatoMate video
    
    Args:
        render_id (str): The ID of the CreatoMate rendering job
        
    Returns:
        str: Path to the downloaded video file or error message
    """
    # First check the status to make sure it's completed
    status = check_creatomate_status(render_id)
    
    if "error" in status:
        return f"Error: {status['error']}"
    
    if status.get("status") != "succeeded":
        return f"Error: Video is not ready yet. Current status: {status.get('status', 'unknown')}"
    
    video_url = status.get("url")
    if not video_url:
        return "Error: No video URL found in the status response"
    
    try:
        # Create output directory
        output_dir = Path("videos")
        output_dir.mkdir(exist_ok=True)
        
        # Define output file path
        output_path = output_dir / f"creatomate_{render_id}.mp4"
        
        # Download the video
        logger.info(f"Downloading video from {video_url}")
        response = requests.get(video_url, stream=True)
        
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Video downloaded successfully to {output_path}")
            return str(output_path)
        else:
            logger.error(f"Error downloading video: {response.status_code} - {response.text}")
            return f"Error downloading video: {response.status_code}"
    
    except Exception as e:
        logger.error(f"Exception when downloading CreatoMate video: {str(e)}")
        return f"Error: {str(e)}"

def wait_for_completion(render_id, max_attempts=30, interval=10):
    """
    Wait for a CreatoMate video to complete rendering
    
    Args:
        render_id (str): The ID of the CreatoMate rendering job
        max_attempts (int): Maximum number of polling attempts
        interval (int): Time between polling attempts in seconds
        
    Returns:
        dict: The final status response or error information
    """
    logger.info(f"Waiting for CreatoMate render {render_id} to complete...")
    
    for attempt in range(max_attempts):
        status = check_creatomate_status(render_id)
        
        if "error" in status:
            logger.error(f"Error checking status: {status['error']}")
            return status
        
        current_status = status.get("status")
        logger.info(f"Attempt {attempt+1}/{max_attempts}: Status is '{current_status}'")
        
        if current_status == "succeeded":
            logger.info("Rendering completed successfully!")
            return status
        elif current_status in ["failed", "canceled"]:
            logger.error(f"Rendering {current_status}!")
            return status
        
        # Status is still pending, planned, or rendering
        print(f"Waiting for completion... Status: {current_status}")
        time.sleep(interval)
    
    logger.warning(f"Max attempts ({max_attempts}) reached. Final status: {current_status}")
    return {"error": "Timeout waiting for completion", "last_status": current_status}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CreatoMate Status Checker and Downloader")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-status", help="Check the status of a CreatoMate rendering job")
    group.add_argument("--download", help="Download a completed CreatoMate video")
    group.add_argument("--wait", help="Wait for a CreatoMate rendering job to complete")
    
    parser.add_argument("--max-attempts", type=int, default=30, help="Maximum number of polling attempts")
    parser.add_argument("--interval", type=int, default=10, help="Time between polling attempts in seconds")
    
    args = parser.parse_args()
    
    if args.check_status:
        result = check_creatomate_status(args.check_status)
        print(json.dumps(result, indent=2))
    
    elif args.download:
        result = download_creatomate_video(args.download)
        print(result)
    
    elif args.wait:
        result = wait_for_completion(args.wait, args.max_attempts, args.interval)
        print(json.dumps(result, indent=2))
        
        # If video is ready, offer to download it
        if result.get("status") == "succeeded":
            download = input("Video is ready! Download it now? (y/n): ").lower()
            if download == "y" or download == "yes":
                download_path = download_creatomate_video(args.wait)
                print(f"Video downloaded to: {download_path}")
