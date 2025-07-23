#!/usr/bin/env python3
"""
Video Quality Test Script

This script tests different Cloudinary transformation modes to help you choose 
the best quality settings for your movie clips.
"""

import os
import sys
import json
import logging
from pathlib import Path
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

# Configure Cloudinary (with same defaults as main script)
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dodod8s0v")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "589374432754798")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "iwOZJxSJ9SIE47BwVBsvQdYAfsg")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def test_transformation_modes():
    """
    Test different Cloudinary transformation modes for video quality
    """
    logger.info("🎬 TESTING VIDEO TRANSFORMATION MODES")
    logger.info("="*60)
    
    # Use one movie for testing different modes
    test_movie = [
        {
            "id": 3917,
            "title": "Sandman_Quality_Test",
            "year": 2022,
            "trailer_url": "https://www.youtube.com/watch?v=-m5Qwjs_-rc",
            "platform": "Netflix"
        }
    ]
    
    # Test different transformation modes (YouTube Shorts optimized)
    modes_to_test = {
        "fit": "📐 FIT: 1080x1920 with black bars (preserves aspect ratio)",
        "smart_fit": "🎯 SMART_FIT: 1080x1920 with intelligent cropping (YouTube Shorts style)",
        "youtube_shorts": "📱 YOUTUBE_SHORTS: Premium 1080x1920 with max quality (3000k bitrate)",
        "pad": "📏 PAD: 1080x1920 with smart background matching",
        "scale": "📈 SCALE: 1080x1920 stretched (may distort aspect ratio)"
    }
    
    results = {}
    
    logger.info("🧪 Testing transformation modes:")
    for mode, description in modes_to_test.items():
        logger.info(f"   {description}")
    
    logger.info("\n🚀 PROCESSING MODES...")
    logger.info("="*60)
    
    for mode, description in modes_to_test.items():
        try:
            logger.info(f"\n🎯 Testing mode: {mode.upper()}")
            logger.info(f"📝 Description: {description}")
            
            # Process with this transformation mode
            clip_urls = process_movie_trailers_to_clips(
                test_movie, 
                max_movies=1, 
                transform_mode=mode
            )
            
            if clip_urls:
                video_url = list(clip_urls.values())[0]
                results[mode] = {
                    "url": video_url,
                    "description": description,
                    "status": "success"
                }
                logger.info(f"✅ {mode.upper()} mode successful!")
                logger.info(f"   URL: {video_url}")
            else:
                results[mode] = {
                    "status": "failed",
                    "description": description
                }
                logger.error(f"❌ {mode.upper()} mode failed!")
                
        except Exception as e:
            logger.error(f"❌ Error testing {mode}: {str(e)}")
            results[mode] = {
                "status": "error",
                "error": str(e),
                "description": description
            }
    
    # Display results
    logger.info("\n🏁 TRANSFORMATION TEST RESULTS")
    logger.info("="*60)
    
    successful_modes = []
    for mode, result in results.items():
        if result.get("status") == "success":
            successful_modes.append(mode)
            logger.info(f"✅ {mode.upper()}: {result['url']}")
        else:
            logger.error(f"❌ {mode.upper()}: {result.get('status', 'unknown')}")
    
    if successful_modes:
        logger.info(f"\n🎉 SUCCESS! {len(successful_modes)} transformation modes working")
        logger.info("\n📋 RECOMMENDATIONS (YouTube Shorts Quality):")
        logger.info("="*60)
        logger.info("🏆 SMART_FIT: BEST for YouTube Shorts - intelligent cropping at 1080x1920")
        logger.info("🥇 YOUTUBE_SHORTS: Premium quality with 3000k bitrate - ultimate quality")
        logger.info("🔸 FIT: Conservative option with black bars - preserves all content")
        logger.info("🔸 PAD: Good alternative with smart background matching")
        logger.info("🔸 SCALE: Avoid unless you don't mind aspect ratio distortion")
        
        logger.info(f"\n🎬 QUALITY COMPARISON:")
        logger.info("Open these URLs in your browser to compare quality:")
        for mode in successful_modes:
            logger.info(f"   {mode.upper()}: {results[mode]['url']}")
            
        # Save results
        os.makedirs("test_output", exist_ok=True)
        with open("test_output/video_quality_test.json", 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": str(datetime.datetime.now()),
                "test_results": results,
                "recommendation": "Use 'fit' mode for best quality without cropping"
            }, f, indent=2, ensure_ascii=False)
            
        logger.info(f"\n💾 Results saved to: test_output/video_quality_test.json")
        
    else:
        logger.error("❌ No transformation modes worked successfully!")
        return False
    
    return True

if __name__ == "__main__":
    import datetime
    
    logger.info("🎬 VIDEO QUALITY TRANSFORMATION TEST")
    logger.info("="*60)
    logger.info("This will test different Cloudinary transformation modes")
    logger.info("to help you choose the best quality settings.\n")
    
    success = test_transformation_modes()
    
    if success:
        logger.info("\n🎉 QUALITY TEST COMPLETED!")
        logger.info("Check the URLs above to see which transformation")
        logger.info("mode produces the best quality for your needs.")
        logger.info("\nTo use a specific mode in your main script:")
        logger.info("Modify the process_movie_trailers_to_clips() call")
        logger.info("to include transform_mode parameter.")
    else:
        logger.error("\n❌ QUALITY TEST FAILED!")
        logger.error("Please check the errors above and try again.")
        sys.exit(1) 