#!/usr/bin/env python3
"""
Test for Cinematic Portrait Conversion with Gaussian Blur Background

This script tests the new FFmpeg implementation that creates a soft Gaussian-blurred 
background instead of black bars for TikTok/Instagram Reels aesthetics.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# Add parent directory to path to import project modules
sys.path.append(str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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

def test_cinematic_portrait():
    """
    Test cinematic portrait conversion with Gaussian blur background
    """
    logger.info("🎬 TESTING CINEMATIC PORTRAIT CONVERSION")
    logger.info("="*60)
    
    # Test with a cinematic landscape trailer
    test_movie = [
        {
            "id": 8888,
            "title": "Cinematic_Portrait_Test",
            "year": 2024,
            "trailer_url": "https://www.youtube.com/watch?v=-m5Qwjs_-rc",  # Sandman trailer (cinematic landscape)
            "platform": "HBO Max"
        }
    ]
    
    logger.info("🎭 TECHNIQUE: Gaussian Blur Background")
    logger.info("📺 Source: Cinematic landscape YouTube trailer")
    logger.info("🎯 Target: Portrait 1080x1920 (9:16) with blur background")
    logger.info("🎨 Enhancement: Contrast + Clarity + Saturation boost")
    logger.info("✨ Result: No black bars - artistic blur background")
    
    try:
        # Process with YouTube Shorts mode (now uses Gaussian blur)
        clip_urls = process_movie_trailers_to_clips(
            test_movie, 
            max_movies=1, 
            transform_mode="youtube_shorts"
        )
        
        if clip_urls:
            video_url = list(clip_urls.values())[0]
            logger.info("\n✅ CINEMATIC PORTRAIT CONVERSION SUCCESS!")
            logger.info("="*60)
            logger.info(f"🎬 Cinematic Portrait Video URL: {video_url}")
            logger.info("\n📱 VERIFICATION STEPS:")
            logger.info("1. Open the URL in your browser")
            logger.info("2. Check that the video is TALL (9:16 portrait)")
            logger.info("3. Verify NO black bars - instead soft blurred background")
            logger.info("4. Confirm original content is centered and clear")
            logger.info("5. Notice enhanced contrast and saturation for social media")
            
            # Save result
            os.makedirs("test_output", exist_ok=True)
            with open("test_output/cinematic_portrait_test_result.txt", 'w') as f:
                f.write(f"Cinematic Portrait Video URL: {video_url}\n")
                f.write("Expected: 1080x1920 portrait with Gaussian blur background\n")
                f.write("Technique: Blurred background + centered original + enhancement\n")
                f.write("Test: Cinematic landscape YouTube trailer -> Portrait with blur\n")
            
            logger.info(f"\n💾 Result saved to: test_output/cinematic_portrait_test_result.txt")
            
            logger.info("\n🎨 WHAT'S NEW:")
            logger.info("✅ Gaussian blurred background (no black bars)")
            logger.info("✅ Original frame centered and preserved")
            logger.info("✅ Enhanced contrast, brightness, and saturation")
            logger.info("✅ Sharpening filter for clarity")
            logger.info("✅ Optimized for TikTok/Instagram Reels aesthetics")
            
            return True
            
        else:
            logger.error("❌ Cinematic portrait conversion failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during cinematic portrait conversion test: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🎬 CINEMATIC PORTRAIT CONVERSION TEST")
    logger.info("="*60)
    logger.info("Testing: Landscape YouTube trailer → Cinematic Portrait with Gaussian Blur")
    
    success = test_cinematic_portrait()
    
    if success:
        logger.info("\n🎉 CINEMATIC PORTRAIT TEST PASSED!")
        logger.info("Your videos now have artistic blur backgrounds instead of black bars!")
    else:
        logger.error("\n❌ CINEMATIC PORTRAIT TEST FAILED!")
        logger.error("Please check the errors above.")
        sys.exit(1) 