#!/usr/bin/env python3
"""
HeyGen-Creatomate Integration Module

This module handles the integration between HeyGen video generation and Creatomate processing:
1. Monitors HeyGen video generation status
2. Manages the waiting/loading screen during processing
3. Downloads completed HeyGen videos and uploads them to Cloudinary
4. Triggers Creatomate processing once all HeyGen videos are ready
5. Returns the final Creatomate video ID and status
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional, Union
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import from parent module
from automated_video_generator import (
    check_heygen_video_status,
    wait_for_heygen_video,
    download_heygen_video,
    create_creatomate_video
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_heygen_to_creatomate(
    heygen_video_ids: Dict[str, str],
    movie_data: List[Dict[str, Any]],
    cloudinary_urls: Dict[str, str] = None,
    max_wait_time: int = 900,  # 15 minutes max wait time
    polling_interval: int = 10,  # Check status every 10 seconds
    mock_mode: bool = False,  # Set to True to skip actual HeyGen processing
    use_direct_urls: bool = False  # Set to True to use direct HeyGen video URLs without downloading
) -> Dict[str, Any]:
    """
    Process HeyGen videos and send to Creatomate once completed
    
    Args:
        heygen_video_ids: Dictionary mapping video keys to HeyGen video IDs
        movie_data: List of movie data dictionaries with metadata
        cloudinary_urls: Optional dictionary of existing Cloudinary URLs
        max_wait_time: Maximum time to wait for HeyGen videos (in seconds)
        polling_interval: Time between status checks (in seconds)
        
    Returns:
        Dictionary with processing results including status and Creatomate video ID
    """
    logger.info(f"Starting HeyGen to Creatomate integration process")
    logger.info(f"Processing {len(heygen_video_ids)} HeyGen videos: {list(heygen_video_ids.keys())}")
    
    # Initialize result dictionary
    result = {
        "status": "pending",
        "message": "",
        "cloudinary_urls": {},
        "creatomate_id": ""
    }
    
    # Check if we're in mock mode or direct URL mode
    if mock_mode:
        logger.info("MOCK MODE: Simulating HeyGen video processing without actual API calls")
    elif use_direct_urls:
        logger.info("DIRECT URL MODE: Using HeyGen video URLs directly without downloading")
        
        # Generate direct URLs for each video ID and add them to result immediately
        for video_key, video_id in heygen_video_ids.items():
            # Use standard HeyGen CDN URL pattern
            direct_url = f"https://assets.heygen.ai/video/{video_id}.mp4"
            
            # Store direct URL
            result["cloudinary_urls"][video_key] = direct_url
            logger.info(f"Using direct URL for video '{video_key}': {direct_url}")
            
        # Skip the video processing loop entirely
        logger.info("DIRECT URL MODE: All video URLs generated, proceeding to Creatomate")
        # Proceed directly to Creatomate processing
        try:
            creatomate_id = create_creatomate_video(
                movie_data=movie_data,
                heygen_video_ids=heygen_video_ids,
                cloudinary_urls=result["cloudinary_urls"]
            )
            result["status"] = "success"
            result["creatomate_id"] = creatomate_id
            logger.info(f"Creatomate video created with ID: {creatomate_id}")
            return result
        except Exception as e:
            logger.error(f"Error processing HeyGen videos: {str(e)}")
            result["status"] = "error"
            result["message"] = f"Error creating Creatomate video: {str(e)}"
            return result
    
    # Initialize result dictionary
    result = {
        "status": "pending",
        "heygen_statuses": {},
        "cloudinary_urls": cloudinary_urls or {},
        "creatomate_id": None,
        "message": "Starting HeyGen video processing"
    }
    
    # Track whether this is the first display of the loading message
    first_display = True
    
    # Start time to track total duration
    start_time = time.time()
    
    # Track completed videos
    completed_videos = set()
    pending_videos = set(heygen_video_ids.keys())
    
    # Create a threading event to signal when to exit
    exit_event = threading.Event()
    
    # Create a thread for the loading animation
    def loading_animation():
        animation = "|/-\\"
        idx = 0
        while not exit_event.is_set():
            prefix = "\r" if not first_display else ""
            print(f"{prefix}Waiting for HeyGen videos to complete... {animation[idx % len(animation)]}", end="", flush=True)
            idx += 1
            time.sleep(0.5)
    
    # Start the loading animation in a separate thread
    loading_thread = threading.Thread(target=loading_animation, daemon=True)
    loading_thread.start()
    
    try:
        # If in mock mode, simulate successful processing
        if mock_mode:
            # Short artificial delay
            time.sleep(2)
            logger.info("MOCK MODE: Simulating successful video processing")
            
            # Simulate cloudinary URLs for each video
            for video_key, video_id in heygen_video_ids.items():
                result["cloudinary_urls"][video_key] = f"https://picsum.photos/1280/720?random={video_id[:8]}"
                completed_videos.add(video_key)
                pending_videos.remove(video_key)
            
            # Show completion message
            print("\rMOCK MODE: All videos processed successfully!      ")
        
        # If using direct URLs, generate them directly from HeyGen video IDs
        elif use_direct_urls:
            logger.info("DIRECT URL MODE: Generating direct HeyGen video URLs")
            
            # Generate direct URLs for each video ID
            for video_key, video_id in heygen_video_ids.items():
                # Use standard HeyGen CDN URL pattern
                direct_url = f"https://assets.heygen.ai/video/{video_id}.mp4"
                
                # Store as cloudinary URL (even though it's direct from HeyGen)
                if not result["cloudinary_urls"]:
                    result["cloudinary_urls"] = {}
                
                result["cloudinary_urls"][video_key] = direct_url
                completed_videos.add(video_key)
                pending_videos.remove(video_key)
                logger.info(f"Generated direct URL for video '{video_key}': {direct_url}")
            
            # Show completion message
            print("\rDIRECT URL MODE: All video URLs generated successfully!      ")
        
        # Regular processing mode
        else:
            # Monitor each HeyGen video until all are complete or timeout
            while pending_videos and (time.time() - start_time < max_wait_time):
                # Check status of all pending videos
                for video_key in list(pending_videos):  # Create a copy of the set to iterate
                    video_id = heygen_video_ids[video_key]
                    status = check_heygen_video_status(video_id)
                    result["heygen_statuses"][video_key] = status
                    
                    # If video completed, process it
                    if status == "completed":
                        logger.info(f"HeyGen video '{video_key}' (ID: {video_id}) is complete")
                        
                        # Download the video and upload to Cloudinary
                        cloudinary_url = download_heygen_video(video_id)
                        
                        if cloudinary_url:
                            # Store the Cloudinary URL
                            if not result["cloudinary_urls"]:
                                result["cloudinary_urls"] = {}
                            
                            result["cloudinary_urls"][video_key] = cloudinary_url
                            logger.info(f"Uploaded HeyGen video '{video_key}' to Cloudinary: {cloudinary_url}")
                            
                            # Mark video as completed
                            completed_videos.add(video_key)
                            pending_videos.remove(video_key)
                        else:
                            logger.error(f"Failed to download HeyGen video '{video_key}' (ID: {video_id})")
                    
                    # If video failed, log error
                    elif status == "failed":
                        logger.error(f"HeyGen video '{video_key}' (ID: {video_id}) failed processing")
                        pending_videos.remove(video_key)
                    
            # If videos are still pending, wait before checking again
            if pending_videos:
                time.sleep(polling_interval)
                
        # Stop the loading animation
        exit_event.set()
        loading_thread.join()
        print()  # New line after the loading animation
        
        # Check if all videos completed successfully
        if not pending_videos:
            # All videos are ready, create Creatomate video
            logger.info("All HeyGen videos are complete. Creating Creatomate video...")
            result["status"] = "ready_for_creatomate"
            result["message"] = "All HeyGen videos are ready for Creatomate processing"
            
            # Create the Creatomate video
            creatomate_id = create_creatomate_video(
                movie_data=movie_data,
                heygen_video_ids=heygen_video_ids,
                cloudinary_urls=result["cloudinary_urls"]
            )
            
            result["creatomate_id"] = creatomate_id
            result["status"] = "completed" if creatomate_id and not creatomate_id.startswith("error") else "failed"
            result["message"] = f"Creatomate video created with ID: {creatomate_id}" if result["status"] == "completed" \
                                else f"Creatomate video creation failed: {creatomate_id}"
                                
            logger.info(result["message"])
        else:
            # Timeout occurred
            result["status"] = "timeout"
            result["message"] = f"Timeout waiting for HeyGen videos. {len(completed_videos)}/{len(heygen_video_ids)} completed."
            logger.error(result["message"])
    
    except Exception as e:
        # Stop the loading animation
        exit_event.set()
        if loading_thread.is_alive():
            loading_thread.join()
            print()  # New line after the loading animation
            
        # Log the error
        logger.exception(f"Error processing HeyGen videos: {str(e)}")
        result["status"] = "error"
        result["message"] = f"Error processing HeyGen videos: {str(e)}"
    
    return result

def monitor_heygen_batch(
    heygen_batch_id: str,
    callback_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Monitor a batch of HeyGen videos and report status
    
    Args:
        heygen_batch_id: HeyGen batch ID to monitor
        callback_url: Optional URL to notify when processing is complete
        
    Returns:
        Status information for the batch
    """
    # Implementation for batch monitoring
    # This would typically involve checking a batch ID that represents multiple videos
    # and tracking overall status
    
    logger.info(f"Monitoring HeyGen batch ID: {heygen_batch_id}")
    
    # This would be implemented based on HeyGen's batch API functionality
    # For now, returning a placeholder
    
    return {
        "batch_id": heygen_batch_id,
        "status": "monitoring",
        "callback_url": callback_url
    }

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running test integration...")
        
        # Test data
        test_heygen_ids = {
            "intro_movie1": "6573ad55-43d0-4742-9eca-afd80117fb2e",
            "movie2": "7b105c8a-92c4-4e5d-8f7b-52e98b92c68f",
            "movie3": "9c31b282-6d5f-4b1c-a88e-fd72e3f12d9a"
        }
        
        test_movie_data = [
            {"title": "Movie 1", "year": 2023, "thumbnail_url": "https://example.com/movie1.jpg"},
            {"title": "Movie 2", "year": 2023, "thumbnail_url": "https://example.com/movie2.jpg"},
            {"title": "Movie 3", "year": 2023, "thumbnail_url": "https://example.com/movie3.jpg"}
        ]
        
        # Process the videos
        result = process_heygen_to_creatomate(test_heygen_ids, test_movie_data)
        
        # Print the result
        print(json.dumps(result, indent=2))
