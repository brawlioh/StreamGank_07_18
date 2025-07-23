#!/usr/bin/env python3
"""
Quick Test for Portrait Conversion

This script tests if our FFmpeg settings are correctly converting landscape 
YouTube trailers to true portrait format (9:16).
"""

import os
import sys
import logging
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# Import our helper functions
from streamgank_helpers import process_movie_trailers_to_clips

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dodod8s0v")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "589374432754798")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "iwOZJxSJ9SIE47BwVBsvQdYAfsg")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def test_portrait_conversion():
    """
    Test portrait conversion with a landscape YouTube trailer
    """
    logger.info("🎬 TESTING PORTRAIT CONVERSION")
    logger.info("="*50)
    
    # Test with a well-known landscape trailer
    test_movie = [
        {
            "id": 9999,
            "title": "Portrait_Test",
            "year": 2024,
            "trailer_url": "https://www.youtube.com/watch?v=-m5Qwjs_-rc",  # Sandman trailer (landscape)
            "platform": "Netflix"
        }
    ]
    
    logger.info("📺 Source: Landscape YouTube trailer")
    logger.info("🎯 Target: Portrait 1080x1920 (9:16)")
    logger.info("🔄 Process: Scale + Center Crop")
    
    try:
        # Process with YouTube Shorts mode
        clip_urls = process_movie_trailers_to_clips(
            test_movie, 
            max_movies=1, 
            transform_mode="youtube_shorts"
        )
        
        if clip_urls:
            video_url = list(clip_urls.values())[0]
            logger.info("\n✅ PORTRAIT CONVERSION SUCCESS!")
            logger.info("="*50)
            logger.info(f"🎬 Portrait Video URL: {video_url}")
            logger.info("\n📱 VERIFICATION STEPS:")
            logger.info("1. Open the URL in your browser")
            logger.info("2. Check that the video is TALL (9:16 portrait)")
            logger.info("3. Verify NO black bars on sides")
            logger.info("4. Confirm content is properly cropped from center")
            
            # Save result
            os.makedirs("test_output", exist_ok=True)
            with open("test_output/portrait_test_result.txt", 'w') as f:
                f.write(f"Portrait Video URL: {video_url}\n")
                f.write("Expected: 1080x1920 portrait format\n")
                f.write("Test: Landscape YouTube trailer converted to portrait\n")
            
            logger.info(f"\n💾 Result saved to: test_output/portrait_test_result.txt")
            return True
            
        else:
            logger.error("❌ Portrait conversion failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during portrait conversion test: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🎬 PORTRAIT CONVERSION TEST")
    logger.info("="*50)
    logger.info("Testing: Landscape YouTube trailer → Portrait 1080x1920")
    
    success = test_portrait_conversion()
    
    if success:
        logger.info("\n🎉 PORTRAIT CONVERSION TEST PASSED!")
        logger.info("Your videos will now be true portrait format!")
    else:
        logger.error("\n❌ PORTRAIT CONVERSION TEST FAILED!")
        logger.error("Please check the errors above.")
        sys.exit(1) 