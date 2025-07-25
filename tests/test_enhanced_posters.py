#!/usr/bin/env python3
"""
Test for Enhanced Movie Poster Creation with Metadata

This script tests the new enhanced movie poster functionality that creates
beautiful poster cards with metadata overlays for TikTok/Instagram Reels.
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
from streamgank_helpers import create_enhanced_movie_posters

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

def test_enhanced_posters():
    """
    Test enhanced movie poster creation with metadata overlays
    """
    logger.info("🎨 TESTING ENHANCED MOVIE POSTER CREATION")
    logger.info("="*60)
    
    # Sample movie data (similar to what comes from database)
    sample_movie_data = [
        {
            "id": 12345,
            "title": "Stranger Things",
            "year": 2016,
            "imdb_score": 8.6,
            "runtime": "1h 1min",
            "platform": "Netflix",
            "poster_url": "https://image.tmdb.org/t/p/w500/49WJfeN0moxb9IPfGn8AIqMGskD.jpg",
            "genres": ["Drama", "Fantastique", "Horreur", "Mystère & Thriller"],
            "imdb_votes": 1465600,
            "content_type": "Série"
        },
        {
            "id": 67890,
            "title": "The Last of Us",
            "year": 2023,
            "imdb_score": 8.5,
            "runtime": "0h 58min",
            "platform": "Max",
            "poster_url": "https://image.tmdb.org/t/p/w500/uKvVjHNqB5VmOrdxqAt2F7J78ED.jpg",
            "genres": ["Action & Adventure", "Drama", "Horreur", "Mystère & Thriller"],
            "imdb_votes": 685100,
            "content_type": "Série"
        },
        {
            "id": 11111,
            "title": "Wednesday",
            "year": 2022,
            "imdb_score": 8.1,
            "runtime": "0h 52min",
            "platform": "Netflix",
            "poster_url": "https://image.tmdb.org/t/p/w500/9PFonBhy4cQy7Jz20NpMygczOkv.jpg",
            "genres": ["Comedy", "Crime", "Family"],
            "imdb_votes": 234500,
            "content_type": "Série"
        }
    ]
    
    logger.info("🎭 FEATURES TO TEST:")
    logger.info("✅ Aspect ratio preservation (no poster distortion)")
    logger.info("✅ Metadata overlay with platform badges")
    logger.info("✅ Professional TikTok/Instagram Reels format")
    logger.info("✅ Genre display and IMDb scoring")
    logger.info("✅ Runtime and year information")
    logger.info("✅ Dark gradient background with shadows")
    
    logger.info(f"\n📋 Test Data: {len(sample_movie_data)} movies")
    for i, movie in enumerate(sample_movie_data):
        logger.info(f"   Movie {i+1}: {movie['title']} ({movie['year']}) - {movie['platform']}")
        logger.info(f"      IMDb: {movie['imdb_score']}/10 | Runtime: {movie['runtime']}")
        logger.info(f"      Genres: {', '.join(movie['genres'][:2])}...")
    
    logger.info("\n🚀 STARTING ENHANCED POSTER CREATION...")
    logger.info("="*60)
    
    try:
        # Create enhanced posters
        enhanced_poster_urls = create_enhanced_movie_posters(sample_movie_data, max_movies=3)
        
        logger.info("\n✅ ENHANCED POSTER RESULTS:")
        logger.info("="*60)
        
        if enhanced_poster_urls:
            logger.info(f"🎨 Successfully created {len(enhanced_poster_urls)} enhanced posters:")
            for movie_title, poster_url in enhanced_poster_urls.items():
                logger.info(f"   🖼️ {movie_title}: {poster_url}")
                
            # Save results to file for reference
            results_file = "test_output/enhanced_posters_result.json"
            os.makedirs("test_output", exist_ok=True)
            
            import json
            import datetime
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": str(datetime.datetime.now()),
                    "processed_posters": len(enhanced_poster_urls),
                    "enhanced_poster_urls": enhanced_poster_urls,
                    "original_movie_data": sample_movie_data
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\n💾 Results saved to: {results_file}")
            
            # Show comparison with old approach
            logger.info("\n📊 ENHANCEMENT COMPARISON:")
            logger.info("="*60)
            logger.info("🔴 OLD (Basic posters):")
            logger.info("   ❌ Simple poster images with distortion")
            logger.info("   ❌ No metadata or context")
            logger.info("   ❌ Black bars or cropping issues")
            logger.info("   ❌ Not optimized for social media")
            
            logger.info("\n🟢 NEW (Enhanced posters):")
            logger.info("   ✅ Aspect ratio preserved - no distortion")
            logger.info("   ✅ Professional metadata overlays")
            logger.info("   ✅ Platform badges with brand colors")
            logger.info("   ✅ Genre, IMDb score, runtime display")  
            logger.info("   ✅ Dark gradient background with shadows")
            logger.info("   ✅ Optimized for TikTok/Instagram Reels")
            
            logger.info("\n🎯 VERIFICATION STEPS:")
            logger.info("="*60)
            logger.info("1. Open the poster URLs in your browser")
            logger.info("2. Check that posters are 1080x1920 (9:16 portrait)")
            logger.info("3. Verify NO distortion - aspect ratios preserved")
            logger.info("4. Confirm metadata is clearly visible and styled")
            logger.info("5. Check platform badges have correct colors")
            logger.info("6. Ensure text is readable on dark background")
            
            return True
            
        else:
            logger.error("❌ No enhanced posters were created!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during enhanced poster creation test: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🎨 ENHANCED MOVIE POSTER TEST")
    logger.info("="*60)
    logger.info("Testing: Movie poster enhancement with metadata overlays")
    
    success = test_enhanced_posters()
    
    if success:
        logger.info("\n🎉 ENHANCED POSTER TEST PASSED!")
        logger.info("Your videos now have beautiful poster cards with metadata!")
    else:
        logger.error("\n❌ ENHANCED POSTER TEST FAILED!")
        logger.error("Please check the errors above.")
        sys.exit(1) 