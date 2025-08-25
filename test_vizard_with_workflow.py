#!/usr/bin/env python3
"""
Test Vizard AI with Workflow Integration

This script tests the Vizard AI within a simplified workflow that bypasses database dependencies.
It uses hardcoded movie data with real YouTube trailer URLs.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import necessary components from the StreamGank system
from ai.vizard_client import VizardAIClient
from ai.extract_highlights import extract_highlights_with_vizard, process_vizard_highlights_for_creatomate
from video.creatomate_client import send_creatomate_request
from video.clip_processor import prepare_clips_for_creatomate
from video.trailer_composition import create_composition_with_avatar, create_trailer_composition
from media.cloudinary_uploader import upload_clip_to_cloudinary

# Mock movie data with actual trailer URLs
MOCK_MOVIES = [
    {
        "id": "movie1",
        "title": "The Gray Man",
        "trailer_url": "https://www.youtube.com/watch?v=BmllggGO4pM",
        "year": 2022,
        "imdb": 6.5,
        "platform": "Netflix",
        "genre": "Action",
        "country": "US"
    },
    {
        "id": "movie2",
        "title": "Red Notice",
        "trailer_url": "https://www.youtube.com/watch?v=T6l3mM7AWew",
        "year": 2021,
        "imdb": 6.3,
        "platform": "Netflix",
        "genre": "Action",
        "country": "US"
    },
    {
        "id": "movie3",
        "title": "Extraction",
        "trailer_url": "https://www.youtube.com/watch?v=L6P3nI6VnlY",
        "year": 2020,
        "imdb": 6.7,
        "platform": "Netflix",
        "genre": "Action",
        "country": "US"
    }
]

def run_mock_workflow(num_movies=1, heygen_template_id=None):
    """
    Run a simplified workflow with mock data that tests Vizard AI integration
    
    Args:
        num_movies: Number of movies to process
        heygen_template_id: Optional HeyGen template ID
        
    Returns:
        Dictionary with workflow results
    """
    print(f"\n🎬 StreamGank Workflow Test with Vizard AI")
    print(f"=======================================\n")
    
    # Use fewer movies if requested
    movies_to_process = MOCK_MOVIES[:num_movies]
    
    print(f"[STEP 1/5] Mock Database Extraction - Using {num_movies} hardcoded movies")
    for i, movie in enumerate(movies_to_process, 1):
        print(f"   Movie {i}: {movie['title']} ({movie['year']}) - {movie['platform']} {movie['genre']}")
    
    # Create output directory if it doesn't exist
    output_dir = "vizard_workflow_test"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n[STEP 2/5] Vizard AI Highlight Extraction")
    highlight_clips = []
    trailer_movies = []
    
    for i, movie in enumerate(movies_to_process, 1):
        movie_title = movie.get('title', f"Movie {i}")
        trailer_url = movie.get('trailer_url')
        
        if not trailer_url or not trailer_url.startswith("https://www.youtube.com"):
            print(f"⚠️ No valid YouTube trailer URL for {movie_title}")
            continue
        
        print(f"\n   Processing {movie_title}")
        print(f"   📺 Trailer URL: {trailer_url}")
        
        print(f"   🔄 Extracting highlights with Vizard AI...")
        movie_clips = extract_highlights_with_vizard(
            youtube_url=trailer_url,
            movie_title=movie_title,
            num_clips=1,
            clip_length=1,  # Use short clips for testing
            output_dir=output_dir,
            max_wait_minutes=10  # Set reasonable timeout
        )
        
        if movie_clips:
            print(f"   ✅ Successfully extracted {len(movie_clips)} highlights for '{movie_title}'")
            highlight_clips.extend(movie_clips)
            trailer_movies.append(movie_title)
        else:
            print(f"   ❌ Failed to extract highlights for '{movie_title}'")
    
    # Error if no clips extracted
    if not highlight_clips:
        print(f"\n❌ No highlights extracted from any movies")
        return {"status": "ERROR", "error": "No highlights extracted"}
    
    print(f"\n[STEP 3/5] Processing {len(highlight_clips)} Vizard AI highlights for Cloudinary")
    
    cloudinary_urls = process_vizard_highlights_for_creatomate(
        highlight_clips=highlight_clips,
        folder="vizard_ai_test"
    )
    
    if not cloudinary_urls:
        print(f"\n❌ Failed to process highlights for Cloudinary")
        return {"status": "ERROR", "error": "Failed to upload to Cloudinary"}
    
    print(f"\n✅ Successfully processed {len(cloudinary_urls)} highlights to Cloudinary")
    
    print(f"\n[STEP 4/5] Create Composition - Setting up movie data")
    
    # Prepare a simplified mock composition data
    movie_data = []
    for i, movie in enumerate(movies_to_process):
        if i < len(cloudinary_urls):
            movie_data.append({
                "title": movie["title"],
                "year": movie["year"],
                "platform": movie["platform"],
                "genre": movie["genre"],
                "country": movie["country"],
                "clip_url": cloudinary_urls[i],
                "imdb_rating": movie.get("imdb", 7.0)
            })
    
    if not movie_data:
        print(f"\n❌ No movie data available for composition")
        return {"status": "ERROR", "error": "No movie data for composition"}
    
    print(f"\n   ℹ️ Prepared {len(movie_data)} movies for composition")
    
    print(f"\n[STEP 5/5] Creating trailer-only composition (skipping HeyGen)")
    
    try:
        composition = create_trailer_composition(
            clips=movie_data,
            output_name=f"vizard_test_composition_{int(time.time())}",
            with_subtitles=True
        )
        
        if composition and "render_id" in composition:
            render_id = composition["render_id"]
            print(f"\n✅ Successfully created composition!")
            print(f"   🎬 Render ID: {render_id}")
            print(f"   🔗 Creatomate will process this in the background")
            
            return {
                "status": "SUCCESS", 
                "render_id": render_id,
                "movies": [m["title"] for m in movie_data],
                "clip_count": len(cloudinary_urls)
            }
        else:
            print(f"\n❌ Failed to create composition")
            print(f"   Response: {composition}")
            return {"status": "ERROR", "error": "Failed to create composition"}
    
    except Exception as e:
        print(f"\n❌ Exception creating composition: {str(e)}")
        return {"status": "ERROR", "error": str(e)}

def main():
    """Main function"""
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("ℹ️ Using values from .env.example")
    
    # Process just one movie for testing
    result = run_mock_workflow(num_movies=1)
    
    if result["status"] == "SUCCESS":
        print("\n🎉 Workflow test with Vizard AI PASSED!")
        return 0
    else:
        print(f"\n❌ Workflow test FAILED: {result.get('error', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
