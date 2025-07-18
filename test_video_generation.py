#!/usr/bin/env python3
"""
Test script for video generation components of the automated_video_generator.py

This script focuses on testing three key components:
1. Movie data enrichment with ChatGPT
2. Script generation
3. HeyGen video clip generation

It assumes movie data has already been extracted.
"""

import os
import json
import logging
from dotenv import load_dotenv
from automated_video_generator import (
    test_and_extract_movie_data, 
    enrich_movie_data,
    generate_script,
    create_heygen_video,
    check_heygen_video_status,
    wait_for_heygen_video,
    download_heygen_video,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for required API keys
openai_key = os.getenv("OPENAI_API_KEY")
heygen_key = os.getenv("HEYGEN_API_KEY")

# Create output directory
os.makedirs("test_output", exist_ok=True)

def main():
    """Main test workflow"""
    
    # 1. Extract movie data (using the function we already fixed)
    logger.info("1. Extracting movie data...")
    try:
        # First try with genre filter
        movies = test_and_extract_movie_data(
            num_movies=3, 
            country="FR", 
            genre="Horreur", 
            platform="netflix", 
            content_type="Film"
        )
        
        # If we didn't get enough movies, try without genre filter
        if not movies or len(movies) < 3:
            logger.warning("Not enough movies with genre filter, trying without...")
            movies = test_and_extract_movie_data(
                num_movies=3, 
                country="FR", 
                genre=None, 
                platform="netflix", 
                content_type="Film"
            )
            
        # Last resort - just get any movies
        if not movies or len(movies) < 3:
            logger.warning("Still not enough movies, trying with minimal filters...")
            movies = test_and_extract_movie_data(
                num_movies=3, 
                country=None, 
                genre=None, 
                platform=None, 
                content_type=None
            )
            
        # Save the extracted movie data
        with open("test_output/movie_data.json", "w") as f:
            json.dump(movies, f, indent=4)
            
        logger.info(f"Extracted {len(movies)} movies")
        
    except Exception as e:
        logger.error(f"Error extracting movie data: {str(e)}")
        return
        
    # Check if we have enough movies
    if not movies or len(movies) < 3:
        logger.error("Failed to extract enough movies. Need at least 3 movies.")
        return
        
    # 2. Enrich movie data with ChatGPT
    if openai_key:
        logger.info("2. Enriching movie data with ChatGPT...")
        try:
            enriched_movies = enrich_movie_data(movies)
            
            # Save the enriched movie data
            with open("test_output/enriched_movie_data.json", "w") as f:
                json.dump(enriched_movies, f, indent=4)
                
            logger.info("Movie data enrichment complete")
            
        except Exception as e:
            logger.error(f"Error enriching movie data: {str(e)}")
            # Continue with original movie data
            enriched_movies = movies
            for movie in enriched_movies:
                movie["enriched_description"] = f"A {', '.join(movie.get('genres', []))} movie from {movie['year']} with an IMDb score of {movie['imdb']}."
    else:
        logger.warning("OpenAI API key not found. Skipping enrichment step.")
        enriched_movies = movies
        for movie in enriched_movies:
            movie["enriched_description"] = f"A {', '.join(movie.get('genres', []))} movie from {movie['year']} with an IMDb score of {movie['imdb']}."
        
    # 3. Generate script
    logger.info("3. Generating script...")
    try:
        # Create a placeholder for Cloudinary URLs (not used in this test)
        cloudinary_urls = {
            "screenshot_1": "https://placeholder.com/screenshot1",
            "screenshot_2": "https://placeholder.com/screenshot2",
            "screenshot_3": "https://placeholder.com/screenshot3",
        }
        
        combined_script, script_path, script_segments = generate_script(enriched_movies, cloudinary_urls)
        
        logger.info(f"Generated script saved to {script_path}")
        
        # Save the script segments
        with open("test_output/script_segments.json", "w") as f:
            script_data = {key: value["text"] for key, value in script_segments.items()}
            json.dump(script_data, f, indent=4)
            
    except Exception as e:
        logger.error(f"Error generating script: {str(e)}")
        return
        
    # 4. Create HeyGen video (if API key is available)
    if heygen_key:
        logger.info("4. Creating HeyGen videos...")
        try:
            # Use the separate script segments for more targeted videos
            video_ids = create_heygen_video(script_segments)
            
            # Save the video IDs
            with open("test_output/heygen_video_ids.json", "w") as f:
                json.dump(video_ids, f, indent=4)
                
            logger.info(f"HeyGen videos created: {video_ids}")
            
            # Wait for and download the first video as a test (if available)
            if video_ids and len(video_ids) > 0:
                first_key = next(iter(video_ids))
                first_video_id = video_ids[first_key]
                
                logger.info(f"Waiting for video processing: {first_key} ({first_video_id})...")
                if wait_for_heygen_video(first_video_id, max_attempts=3, interval=10):
                    logger.info(f"Video ready, downloading: {first_video_id}")
                    cloudinary_url = download_heygen_video(first_video_id)
                    logger.info(f"Video uploaded to Cloudinary: {cloudinary_url}")
                else:
                    logger.warning(f"Video processing timeout: {first_video_id}")
            
        except Exception as e:
            logger.error(f"Error creating HeyGen videos: {str(e)}")
    else:
        logger.warning("HeyGen API key not found. Skipping video creation.")
        
    logger.info("Test workflow complete!")

if __name__ == "__main__":
    main()
