#!/usr/bin/env python3
"""
Fully Automated HeyGen → Creatomate Pipeline
Eliminates manual download/upload by using HeyGen video URLs directly in Creatomate.

This script:
1. Creates HeyGen videos with precise timing
2. Automatically waits for HeyGen processing completion
3. Fetches direct HeyGen video URLs
4. Uses URLs directly in Creatomate (no manual upload needed)
"""

import os
import json
import logging
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

# Import functions from existing scripts
from automated_video_generator import (
    capture_streamgank_screenshots,
    upload_to_cloudinary,
    extract_movie_data,
    enrich_movie_data,
    generate_script
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('automated-pipeline')

# API Keys
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
CREATOMATE_API_KEY = os.getenv("CREATOMATE_API_KEY")

def send_heygen_request(payload):
    """
    Send request to HeyGen API for template-based video creation
    
    Args:
        payload: API request payload
        
    Returns:
        Video ID if successful, None otherwise
    """
    template_id = payload.pop('template_id')
    url = f"https://api.heygen.com/v2/template/{template_id}/generate"
    
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": HEYGEN_API_KEY
    }
    
    try:
        logger.info("Sending request to HeyGen API...")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            data = response.json()
            video_id = data.get("data", {}).get("task_id") or data.get("data", {}).get("video_id")
            if video_id:
                logger.info(f"Successfully created video with ID: {video_id}")
                return video_id
            else:
                logger.error(f"No video_id or task_id found in response: {data}")
        else:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
        
        return None
    except Exception as e:
        logger.error(f"Error sending request to HeyGen: {str(e)}")
        return None

def check_video_status(video_id):
    """
    Check the status of a HeyGen video and get its URL
    
    Args:
        video_id: HeyGen video ID or task ID
        
    Returns:
        Status information with video URL
    """
    url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    
    headers = {
        "X-Api-Key": HEYGEN_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            data_section = data.get("data", {})
            status = data_section.get("status")
            
            # Extract video URL directly from data section (as per HeyGen API docs)
            video_url = data_section.get("video_url")
            
            # Log the full response for debugging
            logger.info(f"HeyGen API response for {video_id}: {data}")
            
            if video_url:
                logger.info(f"Video URL found: {video_url}")
            elif status == "completed":
                logger.warning(f"Video {video_id} completed but no video_url in response")
            
            return {
                "status": status,
                "video_url": video_url,
                "raw_data": data_section
            }
        else:
            logger.error(f"Status check failed: {response.status_code} - {response.text}")
            return {"status": "error"}
    except Exception as e:
        logger.error(f"Error checking video status: {str(e)}")
        return {"status": "error"}

def wait_for_videos(video_ids, timeout=300, interval=15):
    """
    Wait for HeyGen videos to be processed and get their URLs
    
    Args:
        video_ids: Dictionary of video IDs
        timeout: Maximum time to wait in seconds
        interval: Time between status checks in seconds
        
    Returns:
        Dictionary with video URLs
    """
    if not video_ids:
        logger.error("No video IDs provided")
        return {}
    
    logger.info(f"🕐 Waiting for {len(video_ids)} HeyGen videos to be processed...")
    
    video_urls = {}
    start_time = time.time()
    
    while True:
        all_done = True
        
        for key, video_id in video_ids.items():
            if key not in video_urls:
                status_data = check_video_status(video_id)
                status = status_data.get("status")
                
                if status == "completed" or status == "success":
                    video_url = status_data.get("video_url")
                    if video_url:
                        video_urls[key] = video_url
                        logger.info(f"✅ Video for {key} is ready: {video_url}")
                    else:
                        logger.warning(f"⚠️ Video for {key} completed but no URL found")
                        all_done = False
                elif status in ["failed", "error"]:
                    logger.error(f"❌ Video for {key} failed processing")
                    video_urls[key] = None
                else:
                    logger.info(f"⏳ Video for {key} status: {status}")
                    all_done = False
        
        if all_done:
            logger.info("🎉 All HeyGen videos are processed!")
            break
            
        if time.time() - start_time > timeout:
            logger.warning(f"⏰ Timeout reached after {timeout} seconds")
            break
            
        logger.info(f"💤 Waiting {interval} seconds before next check...")
        time.sleep(interval)
    
    return video_urls

def create_heygen_videos(scripts):
    """
    Create HeyGen videos for all scripts
    
    Args:
        scripts: Dictionary with script content for each segment
        
    Returns:
        Dictionary with HeyGen video IDs
    """
    logger.info("🎬 Creating HeyGen videos...")
    
    # HeyGen template configuration (using working template ID from archive)
    template_id = "7fb75067718944ac8f02e661c2c61522"
    
    video_ids = {}
    
    for segment_name, script_data in scripts.items():
        logger.info(f"📝 Creating video for {segment_name}...")
        
        # Extract text content from script data structure
        if isinstance(script_data, dict) and "text" in script_data:
            script_content = script_data["text"]
        else:
            script_content = str(script_data)
        
        logger.info(f"Script content for {segment_name}: {script_content[:100]}...")
        
        # Use correct HeyGen API format from archive scripts
        payload = {
            "template_id": template_id,
            "caption": False,
            "title": f"Video for {segment_name}",
            "variables": {
                "script": {
                    "name": "script",
                    "type": "text",
                    "properties": {
                        "content": script_content
                    }
                }
            }
        }
        
        video_id = send_heygen_request(payload)
        if video_id:
            video_ids[segment_name] = video_id
            logger.info(f"✅ {segment_name} video queued with ID: {video_id}")
        else:
            logger.error(f"❌ Failed to create video for {segment_name}")
    
    return video_ids

def create_creatomate_video_with_heygen_urls(movie_data, heygen_video_urls):
    """
    Create Creatomate video using direct HeyGen URLs (no manual upload needed)
    
    Args:
        movie_data: Movie information
        heygen_video_urls: Dictionary with HeyGen video URLs
        
    Returns:
        Creatomate render ID
    """
    logger.info("🎥 Creating Creatomate video with HeyGen URLs...")
    
    # Build sequential video elements
    elements = []
    current_time = 0
    
    # Banner image
    banner_url = "https://res.cloudinary.com/dodod8s0v/image/upload/v1752587056/streamgankbanner_uempzb.jpg"
    elements.append({
        "type": "image",
        "source": banner_url,
        "duration": 2,
        "fit": "cover",
        "track": 1
    })
    current_time += 2
    
    # Process each movie segment
    for i, movie in enumerate(movie_data):
        segment_name = "intro_movie1" if i == 0 else f"movie{i+1}"
        
        # HeyGen video segment
        if segment_name in heygen_video_urls and heygen_video_urls[segment_name]:
            elements.append({
                "type": "video",
                "source": heygen_video_urls[segment_name],
                "fit": "cover",
                "track": 1
            })
            logger.info(f"✅ Added HeyGen video for {segment_name}")
        
        # Movie cover image
        if movie.get('cover_image_url'):
            elements.append({
                "type": "image",
                "source": movie['cover_image_url'],
                "duration": 3,
                "fit": "cover",
                "track": 1
            })
        
        # Movie clip
        if movie.get('video_clip_url'):
            elements.append({
                "type": "video",
                "source": movie['video_clip_url'],
                "duration": 8,
                "fit": "cover",
                "track": 1
            })
    
    # Create Creatomate composition
    composition = {
        "source": {
            "timeline_type": "sequential",
            "width": 720,
            "height": 1280,
            "elements": elements,
            "output_format": "mp4"
        }
    }
    
    # Send to Creatomate API
    url = "https://api.creatomate.com/v1/renders"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CREATOMATE_API_KEY}"
    }
    
    try:
        logger.info("📤 Sending composition to Creatomate...")
        response = requests.post(url, json=composition, headers=headers)
        
        if response.status_code in [200, 201, 202]:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                render_id = result[0].get("id")
                video_url = f"https://f002.backblazeb2.com/file/creatomate-c8xg3hsxdu/{render_id}.mp4"
                logger.info(f"🎉 Creatomate video queued! ID: {render_id}")
                logger.info(f"🔗 Video URL: {video_url}")
                return render_id
            else:
                logger.error("❌ Unexpected response format from Creatomate")
                return None
        else:
            logger.error(f"❌ Creatomate API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Error creating Creatomate video: {str(e)}")
        return None

def main():
    """
    Run the complete automated pipeline
    """
    logger.info("🚀 Starting Automated HeyGen → Creatomate Pipeline")
    logger.info("=" * 60)
    
    try:
        # Step 1: Capture screenshots
        logger.info("📸 Step 1: Capturing screenshots...")
        screenshot_paths = capture_streamgank_screenshots()
        
        # Step 2: Upload to Cloudinary
        logger.info("☁️ Step 2: Uploading to Cloudinary...")
        cloudinary_urls = upload_to_cloudinary(screenshot_paths)
        
        # Step 3: Extract movie data
        logger.info("🎬 Step 3: Extracting movie data...")
        movie_data = extract_movie_data(num_movies=3)
        
        # Step 4: Enrich with ChatGPT
        logger.info("🤖 Step 4: Enriching with ChatGPT...")
        enriched_movies = enrich_movie_data(movie_data)
        
        # Step 5: Generate scripts
        logger.info("📝 Step 5: Generating scripts...")
        combined_script, combined_path, scripts = generate_script(enriched_movies, cloudinary_urls)
        
        # Step 6: Create HeyGen videos
        logger.info("🎭 Step 6: Creating HeyGen videos...")
        video_ids = create_heygen_videos(scripts)
        
        if not video_ids:
            logger.error("❌ No HeyGen videos were created successfully")
            return
        
        # Step 7: Wait for HeyGen videos and get URLs
        logger.info("⏳ Step 7: Waiting for HeyGen videos...")
        heygen_video_urls = wait_for_videos(video_ids)
        
        if not heygen_video_urls:
            logger.error("❌ No HeyGen video URLs were retrieved")
            return
        
        # Step 8: Create final Creatomate video
        logger.info("🎥 Step 8: Creating final Creatomate video...")
        render_id = create_creatomate_video_with_heygen_urls(enriched_movies, heygen_video_urls)
        
        if render_id:
            logger.info("🎉 SUCCESS! Automated pipeline completed!")
            logger.info(f"🆔 Final video render ID: {render_id}")
            logger.info(f"🔗 Video URL: https://f002.backblazeb2.com/file/creatomate-c8xg3hsxdu/{render_id}.mp4")
        else:
            logger.error("❌ Failed to create final Creatomate video")
            
    except Exception as e:
        logger.error(f"❌ Pipeline error: {str(e)}")

if __name__ == "__main__":
    main()
