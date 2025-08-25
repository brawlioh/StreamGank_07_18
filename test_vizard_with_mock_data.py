#!/usr/bin/env python3
"""
Test Vizard AI with Mock Data

This script tests the Vizard AI functionality without requiring database connection.
It uses hardcoded movie data with real YouTube trailer URLs.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Vizard client and highlight extraction
from ai.vizard_client import VizardAIClient
from ai.extract_highlights import extract_highlights_with_vizard, process_vizard_highlights_for_creatomate

# Mock movie data with actual trailer URLs
MOCK_MOVIES = [
    {
        "id": "movie1",
        "title": "The Gray Man",
        "trailer_url": "https://www.youtube.com/watch?v=BmllggGO4pM",
        "year": 2022,
        "imdb": 6.5,
        "platform": "Netflix"
    },
    {
        "id": "movie2",
        "title": "Red Notice",
        "trailer_url": "https://www.youtube.com/watch?v=T6l3mM7AWew",
        "year": 2021,
        "imdb": 6.3,
        "platform": "Netflix"
    },
    {
        "id": "movie3",
        "title": "Extraction",
        "trailer_url": "https://www.youtube.com/watch?v=L6P3nI6VnlY",
        "year": 2020,
        "imdb": 6.7,
        "platform": "Netflix"
    }
]

def main():
    """Main function to test Vizard AI with mock data"""
    print("\n🎬 Vizard AI Test with Mock Movie Data")
    print("=====================================\n")
    
    # Create output directory if it doesn't exist
    output_dir = "vizard_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each movie with Vizard AI
    highlight_clips = []
    trailer_movies = []
    
    for i, movie in enumerate(MOCK_MOVIES, 1):
        movie_title = movie.get('title', f"Movie {i}")
        trailer_url = movie.get('trailer_url')
        
        if not trailer_url or not trailer_url.startswith("https://www.youtube.com"):
            print(f"⚠️ No valid YouTube trailer URL for {movie_title}")
            continue
        
        print(f"\n[MOVIE {i}/3] Processing {movie_title}")
        print(f"📺 Trailer URL: {trailer_url}")
        
        print(f"🔄 Extracting highlights with Vizard AI...")
        movie_clips = extract_highlights_with_vizard(
            youtube_url=trailer_url,
            movie_title=movie_title,
            num_clips=1,
            clip_length=1,  # Use short clips
            output_dir=output_dir,
            max_wait_minutes=10  # Set reasonable timeout
        )
        
        if movie_clips:
            print(f"✅ Successfully extracted {len(movie_clips)} highlights for '{movie_title}'")
            highlight_clips.extend(movie_clips)
            trailer_movies.append(movie_title)
        else:
            print(f"❌ Failed to extract highlights for '{movie_title}'")
    
    # Process Vizard highlights for Creatomate if we have any
    if highlight_clips:
        print(f"\n🎬 Processing {len(highlight_clips)} Vizard AI highlights for Cloudinary...")
        
        cloudinary_urls = process_vizard_highlights_for_creatomate(
            highlight_clips=highlight_clips,
            folder="vizard_ai_test"
        )
        
        if cloudinary_urls:
            print(f"\n✅ Successfully processed {len(cloudinary_urls)} highlights:")
            for i, url in enumerate(cloudinary_urls, 1):
                print(f"  {i}. {url[:80]}...")
            
            print("\n🎉 TEST PASSED! Vizard AI highlight extraction is working correctly!")
        else:
            print("\n❌ TEST FAILED: Could not process highlight clips for Cloudinary")
    else:
        print("\n❌ TEST FAILED: No highlights extracted from any movies")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
