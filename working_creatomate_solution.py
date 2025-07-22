#!/usr/bin/env python3
"""
Working Creatomate Solution - Based on Archive Scripts

This script uses the exact working approach from the archive scripts that successfully
created videos with Creatomate. Key elements:
- timeline_type: "sequential" for automatic element arrangement
- source instead of src
- fit: "cover" for proper scaling
- track: 1 for all elements
"""

import os
import json
import requests
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("working-creatomate")

# Load environment variables
load_dotenv()

# Get Creatomate API key from environment variables
CREATOMATE_API_KEY = os.getenv("CREATOMATE_API_KEY")
if not CREATOMATE_API_KEY:
    logger.error("CREATOMATE_API_KEY not found in environment variables")
    CREATOMATE_API_KEY = "API_KEY"  # Fallback to placeholder

def create_working_sequential_video():
    """
    Create a sequential video using the EXACT working approach from archive scripts
    """
    logger.info("Creating video using the proven working approach from archive scripts...")
    
    # Asset URLs - using the working combination approach
    assets = {
        # Test with your uploaded HeyGen videos first
        "heygen_intro_movie1": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752902942/Video_for_intro_movie1_q2wb38.mp4",
        "heygen_movie2": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752902950/Video_for_movie2_rwk9go.mp4",
        "heygen_movie3": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752902951/Video_for_movie3_opof5z.mp4",
        
        # Movie covers (using working URLs from archive)
        "movie1_cover": "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
        "movie2_cover": "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
        "movie3_cover": "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png",
        
        # Movie clips (known working)
        "movie1_clip": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4",
        "movie2_clip": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4",
        "movie3_clip": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
    }
    
    # Creatomate API endpoint
    url = "https://api.creatomate.com/v1/renders"
    
    # Define headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CREATOMATE_API_KEY}"
    }
    
    # Set fixed durations for static assets (images)
    cover_duration = 3  # 3 seconds for cover images
    
    # Create composition using the EXACT working approach from archive
    composition = {
        "output_format": "mp4",
        "width": 720,
        "height": 1280,  # Portrait mode for reels/shorts
        "frame_rate": 30,
        "timeline_type": "sequential",  # KEY: Use sequential timeline
        "elements": [
            # 1. Intro + Movie 1 HeyGen Video
            {
                "type": "video",
                "source": assets["heygen_intro_movie1"],  # KEY: Use 'source' not 'src'
                "fit": "cover",  # KEY: Use 'fit' for proper scaling
                "track": 1
            },
            # 2. Movie 1 Cover
            {
                "type": "image",
                "source": assets["movie1_cover"],
                "duration": cover_duration,
                "fit": "cover",
                "track": 1
            },
            # 3. Movie 1 Clip
            {
                "type": "video",
                "source": assets["movie1_clip"],
                "fit": "cover",
                "track": 1,
                "trim_start": 0,  # Start from beginning
                "trim_end": 8      # Limit to 8 seconds
            },
            # 4. Movie 2 HeyGen Video
            {
                "type": "video",
                "source": assets["heygen_movie2"],
                "fit": "cover",
                "track": 1
            },
            # 5. Movie 2 Cover
            {
                "type": "image",
                "source": assets["movie2_cover"],
                "duration": cover_duration,
                "fit": "cover",
                "track": 1
            },
            # 6. Movie 2 Clip
            {
                "type": "video",
                "source": assets["movie2_clip"],
                "fit": "cover",
                "track": 1,
                "trim_start": 0,  # Start from beginning
                "trim_end": 8      # Limit to 8 seconds
            },
            # 7. Movie 3 HeyGen Video
            {
                "type": "video",
                "source": assets["heygen_movie3"],
                "fit": "cover",
                "track": 1
            },
            # 8. Movie 3 Cover
            {
                "type": "image",
                "source": assets["movie3_cover"],
                "duration": cover_duration,
                "fit": "cover",
                "track": 1
            },
            # 9. Movie 3 Clip
            {
                "type": "video",
                "source": assets["movie3_clip"],
                "fit": "cover",
                "track": 1,
                "trim_start": 0,  # Start from beginning
                "trim_end": 8      # Limit to 8 seconds
            }
        ]
    }
    
    # Prepare the request data
    data = {
        "source": composition
    }
    
    logger.info("Creating sequential video using PROVEN working approach...")
    logger.info(f"Key differences from previous attempts:")
    logger.info(f"  - timeline_type: 'sequential' (automatic element arrangement)")
    logger.info(f"  - 'source' instead of 'src' for element URLs")
    logger.info(f"  - 'fit': 'cover' for proper video scaling")
    logger.info(f"  - Consistent 'track': 1 for all elements")
    logger.info(f"Video sequence: Intro+Movie1 -> Movie1 Cover -> Movie1 Clip -> Movie2 HeyGen -> Movie2 Cover -> Movie2 Clip -> Movie3 HeyGen -> Movie3 Cover -> Movie3 Clip")
    
    try:
        # Make the request
        response = requests.post(url, json=data, headers=headers)
        
        # Check if successful
        if response.status_code in [200, 201, 202]:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                result = result[0]  # Get first result
                
            render_id = result.get("id", "")
            status = result.get("status", "")
            video_url = result.get("url", "")
            
            logger.info(f"✅ Creatomate video creation {status}!")
            logger.info(f"🆔 Render ID: {render_id}")
            logger.info(f"🔗 Video URL: {video_url}")
            
            # Save response to file
            with open("working_solution_response.json", "w") as f:
                if isinstance(result, list):
                    json.dump(result, f, indent=2)
                else:
                    json.dump([result], f, indent=2)
            
            logger.info("Response saved to working_solution_response.json")
            
            return render_id
        else:
            logger.error(f"❌ Failed to create Creatomate video: Status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Error creating Creatomate video: {str(e)}")
        return None

def create_fallback_with_known_working_videos():
    """
    Fallback approach: Use only known working videos in place of HeyGen videos
    This will create a working video immediately while we resolve HeyGen video issues
    """
    logger.info("Creating fallback video using ONLY known working videos...")
    
    # Use only known working videos
    assets = {
        # Use known working movie clips in place of HeyGen videos
        "heygen_intro_movie1": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4",
        "heygen_movie2": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4",
        "heygen_movie3": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4",
        
        # Movie covers
        "movie1_cover": "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
        "movie2_cover": "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
        "movie3_cover": "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png",
        
        # Movie clips
        "movie1_clip": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4",
        "movie2_clip": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4",
        "movie3_clip": "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
    }
    
    # Same composition structure as above but with known working videos
    composition = {
        "output_format": "mp4",
        "width": 720,
        "height": 1280,
        "frame_rate": 30,
        "timeline_type": "sequential",
        "elements": [
            {"type": "video", "source": assets["heygen_intro_movie1"], "fit": "cover", "track": 1, "trim_end": 10},
            {"type": "image", "source": assets["movie1_cover"], "duration": 3, "fit": "cover", "track": 1},
            {"type": "video", "source": assets["movie1_clip"], "fit": "cover", "track": 1, "trim_end": 8},
            {"type": "video", "source": assets["heygen_movie2"], "fit": "cover", "track": 1, "trim_end": 10},
            {"type": "image", "source": assets["movie2_cover"], "duration": 3, "fit": "cover", "track": 1},
            {"type": "video", "source": assets["movie2_clip"], "fit": "cover", "track": 1, "trim_end": 8},
            {"type": "video", "source": assets["heygen_movie3"], "fit": "cover", "track": 1, "trim_end": 10},
            {"type": "image", "source": assets["movie3_cover"], "duration": 3, "fit": "cover", "track": 1},
            {"type": "video", "source": assets["movie3_clip"], "fit": "cover", "track": 1, "trim_end": 8}
        ]
    }
    
    data = {"source": composition}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CREATOMATE_API_KEY}"}
    
    try:
        response = requests.post("https://api.creatomate.com/v1/renders", json=data, headers=headers)
        if response.status_code in [200, 201, 202]:
            result = response.json()[0] if isinstance(response.json(), list) else response.json()
            logger.info(f"✅ Fallback video created successfully!")
            logger.info(f"🆔 Render ID: {result.get('id', '')}")
            logger.info(f"🔗 Video URL: {result.get('url', '')}")
            return result.get('id', '')
        else:
            logger.error(f"❌ Fallback creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Error creating fallback video: {str(e)}")
        return None

if __name__ == "__main__":
    print("🎬 Testing Working Creatomate Solution")
    print("=" * 50)
    
    print("\n1️⃣ Attempting with your uploaded HeyGen videos...")
    result1 = create_working_sequential_video()
    
    if result1:
        print(f"✅ Success with HeyGen videos! Render ID: {result1}")
    else:
        print("❌ HeyGen videos still have compatibility issues")
        print("\n2️⃣ Creating fallback video with known working assets...")
        result2 = create_fallback_with_known_working_videos()
        
        if result2:
            print(f"✅ Fallback video created successfully! Render ID: {result2}")
            print("💡 This proves the approach works - we just need to fix the HeyGen video encoding")
        else:
            print("❌ Both approaches failed - there may be an API configuration issue")
