#!/usr/bin/env python3
"""
Test Script for Dynamic Movie Clips Processing

This script demonstrates how to use the new dynamic clip processing functionality
to fetch YouTube trailers, extract 10-second highlights, and upload to Cloudinary.
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

def test_dynamic_clips():
    """
    Test the dynamic movie clips processing using sample movie data
    """
    logger.info("🧪 TESTING DYNAMIC MOVIE CLIPS PROCESSING")
    logger.info("="*50)
    
    # Sample movie data (similar to what extract_movie_data returns)
    sample_movie_data = [
        {
            "id": 3917,
            "title": "Sandman",
            "year": 2022,
            "imdb": "7.7/10 (190476 votes)",
            "platform": "Netflix",
            "trailer_url": "https://www.youtube.com/watch?v=-m5Qwjs_-rc",
            "cloudinary_poster_url": "https://res.cloudinary.com/dodod8s0v/image/upload/v1742219186/movie-posters/bd07bdb34bff7ad39f81de78505b9586.avif",
            "genres": ["Action & Aventure", "Drame", "Fantastique", "Horreur", "Science-Fiction"],
            "content_type": "Série"
        },
        {
            "id": 4857,
            "title": "Lupin",
            "year": 2021,
            "imdb": "7.5/10 (150475 votes)",
            "platform": "Netflix",
            "trailer_url": "https://www.youtube.com/watch?v=ga0iTWXCGa0",
            "cloudinary_poster_url": "https://res.cloudinary.com/dodod8s0v/image/upload/v1742219151/movie-posters/669613790c6c1641e6ca38e904c68dda.avif",
            "genres": ["Action & Aventure", "Crime & Thriller", "Drame", "Mystère & Thriller"],
            "content_type": "Série"
        },
        {
            "id": 4863,
            "title": "1899",
            "year": 2022,
            "imdb": "7.3/10 (117658 votes)",
            "platform": "Netflix",
            "trailer_url": "https://www.youtube.com/watch?v=ulOOON_KYHs",
            "cloudinary_poster_url": "https://res.cloudinary.com/dodod8s0v/image/upload/v1742219188/movie-posters/f594f430e403b33e2e66ce2d9b8610bc.avif",
            "genres": ["Drame", "Horreur", "Mystère & Thriller", "Science-Fiction"],
            "content_type": "Série"
        }
    ]
    
    logger.info(f"📋 Test Data: {len(sample_movie_data)} movies")
    for i, movie in enumerate(sample_movie_data):
        logger.info(f"   Movie {i+1}: {movie['title']} ({movie['year']})")
        logger.info(f"   Trailer: {movie['trailer_url']}")
    
    logger.info("\n🚀 STARTING DYNAMIC PROCESSING...")
    logger.info("="*50)
    
    # Process the movie trailers to create dynamic clips
    try:
        clip_urls = process_movie_trailers_to_clips(sample_movie_data, max_movies=3)
        
        logger.info("\n✅ PROCESSING RESULTS:")
        logger.info("="*50)
        
        if clip_urls:
            logger.info(f"🎬 Successfully processed {len(clip_urls)} movie clips:")
            for movie_title, clip_url in clip_urls.items():
                logger.info(f"   • {movie_title}: {clip_url}")
                
            # Save results to file for reference
            results_file = "test_output/dynamic_clips_result.json"
            os.makedirs("test_output", exist_ok=True)
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": str(datetime.datetime.now()),
                    "processed_movies": len(clip_urls),
                    "clip_urls": clip_urls,
                    "original_movie_data": sample_movie_data
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Results saved to: {results_file}")
            
            # Show comparison with old hardcoded approach
            logger.info("\n📊 COMPARISON:")
            logger.info("="*50)
            logger.info("🔴 OLD (Hardcoded):")
            old_clips = [
                "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4",
                "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4",
                "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
            ]
            for i, url in enumerate(old_clips):
                logger.info(f"   Movie {i+1}: {url}")
            
            logger.info("\n🟢 NEW (Dynamic):")
            for movie_title, clip_url in clip_urls.items():
                logger.info(f"   {movie_title}: {clip_url}")
                
        else:
            logger.error("❌ No clips were processed successfully")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during processing: {str(e)}")
        return False
    
    logger.info("\n🎉 DYNAMIC CLIPS TEST COMPLETED!")
    logger.info("="*50)
    return True

def verify_dependencies():
    """
    Verify that all required dependencies are available
    """
    logger.info("🔍 VERIFYING DEPENDENCIES...")
    
    dependencies = {
        'yt-dlp': 'yt_dlp',
        'ffmpeg': 'subprocess',
        'cloudinary': 'cloudinary'
    }
    
    missing_deps = []
    
    for dep_name, import_name in dependencies.items():
        try:
            if import_name == 'subprocess':
                # Check if ffmpeg is available
                import subprocess
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    missing_deps.append('ffmpeg (command not found)')
            else:
                __import__(import_name)
            logger.info(f"   ✅ {dep_name}: Available")
        except (ImportError, subprocess.TimeoutExpired, FileNotFoundError):
            missing_deps.append(dep_name)
            logger.error(f"   ❌ {dep_name}: Missing")
    
    if missing_deps:
        logger.error(f"\n⚠️ MISSING DEPENDENCIES: {', '.join(missing_deps)}")
        logger.error("Please install missing dependencies:")
        logger.error("   pip install yt-dlp ffmpeg-python")
        logger.error("   # Also install FFmpeg system binary")
        return False
    
    logger.info("✅ All dependencies are available!")
    return True

if __name__ == "__main__":
    import datetime
    
    logger.info("🎬 DYNAMIC MOVIE CLIPS TEST SCRIPT")
    logger.info("="*50)
    
    # Check dependencies first
    if not verify_dependencies():
        logger.error("❌ Cannot proceed without required dependencies")
        sys.exit(1)
    
    # Run the test
    success = test_dynamic_clips()
    
    if success:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("Your dynamic clips processing is ready to use!")
    else:
        logger.error("\n❌ TESTS FAILED!")
        logger.error("Please check the errors above and try again.")
        sys.exit(1) 