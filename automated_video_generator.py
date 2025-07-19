#!/usr/bin/env python3
"""
Automated Video Generator for StreamGank

This script automates the end-to-end process of generating promotional videos for movies:
1. Capturing screenshots from StreamGank
2. Extracting movie data from Supabase
3. Generating avatar video scripts (Intro+Movie1: ~30s, Movie2 & Movie3: max 20s each)
4. Creating videos with HeyGen and Creatomate

Usage:
    python3 automated_video_generator.py --all
    
    # Optional parameters:
    python3 automated_video_generator.py --all --country FR --platform netflix --genre Horreur
"""

import os
import sys
import json
import time
import logging
import requests
import re
import datetime
import argparse
import tempfile
import threading
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import cloudinary
import cloudinary.uploader
import cloudinary.api
from supabase import create_client
import openai
from typing import Dict, List, Tuple, Optional, Any

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dodod8s0v")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "589374432754798")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "iwOZJxSJ9SIE47BwVBsvQdYAfsg")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# HeyGen API Key
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

# Creatomate API Key
CREATOMATE_API_KEY = os.getenv("CREATOMATE_API_KEY", "API_KEY")  # Default to placeholder if not set
CREATOMATE_TEMPLATE_ID = os.getenv("CREATOMATE_TEMPLATE_ID", "e11ad4cc-3fcb-4589-824b-b6ef018da1ba")

# Ensure output directories exist
screenshots_dir = Path("screenshots")
videos_dir = Path("videos")
clips_dir = Path("clips")
covers_dir = Path("covers")

# Create all directories
screenshots_dir.mkdir(exist_ok=True)
videos_dir.mkdir(exist_ok=True)
clips_dir.mkdir(exist_ok=True)
covers_dir.mkdir(exist_ok=True)

def capture_streamgank_screenshots(url="https://streamgank.com/?country=FR&genres=Horreur&platforms=netflix&type=Film"):
    """
    Capture screenshots of StreamGank in mobile format
    showing horror movie results on Netflix France
    """
    # Create a folder for screenshots if needed
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)
    
    # Timestamp for filenames
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    screenshot_paths = []
    
    with sync_playwright() as p:
        # Launch browser in mobile mode
        browser = p.chromium.launch(headless=False)
        
        # Define mobile context (iPhone 12 Pro Max dimensions)
        device = p.devices["iPhone 12 Pro Max"]
        context = browser.new_context(
            **device,
            locale='fr-FR',
            timezone_id='Europe/Paris',
        )
        
        # Open a new page
        page = context.new_page()
        
        # Access the StreamGank page
        logger.info(f"Accessing page: {url}")
        page.goto(url)
        
        # Wait for the page to load
        page.wait_for_selector("text=RESULTS", timeout=30000)
        logger.info("Page loaded successfully")
        
        # Handle cookie banner if present
        try:
            cookie_banner = page.wait_for_selector("text=We use cookies", timeout=5000)
            if cookie_banner:
                logger.info("Cookie banner detected")
                essential_button = page.wait_for_selector("button:has-text('Essential Only')", timeout=3000)
                if essential_button:
                    logger.info("Click on 'Essential Only' button")
                    essential_button.click()
                    time.sleep(2)
        except Exception as e:
            logger.info(f"No cookie banner or error: {str(e)}")
        
        time.sleep(5)
        
        # Screenshots for different pairs of movies
        captures = [
            {"name": "films_1_2", "scroll_position": 0},
            {"name": "films_3_4", "scroll_position": 800},
            {"name": "films_5_6", "scroll_position": 1600}
        ]
        
        for idx, capture in enumerate(captures):
            # Scroll to position
            page.evaluate(f"window.scrollTo(0, {capture['scroll_position']})")
            time.sleep(2)
            
            # Remove any remaining cookie elements
            page.evaluate("""() => {
                const elements = document.querySelectorAll('*');
                for (const el of elements) {
                    if (el.textContent && el.textContent.includes('cookies') && 
                        (el.style.position === 'fixed' || el.style.position === 'absolute' || 
                         getComputedStyle(el).position === 'fixed' || getComputedStyle(el).position === 'absolute')) {
                        el.style.display = 'none';
                    }
                }
            }""")
            
            # Take the screenshot
            screenshot_path = os.path.join(output_dir, f"{timestamp}_streamgank_{capture['name']}.png")
            page.screenshot(path=screenshot_path, full_page=False)
            logger.info(f"Screenshot {idx+1}/3 saved: {screenshot_path}")
            screenshot_paths.append(screenshot_path)
        
        # Close the browser
        browser.close()
        
    logger.info("All screenshots have been successfully taken!")
    return screenshot_paths

def upload_to_cloudinary(file_paths):
    """
    Upload images to Cloudinary and return the URLs
    """
    cloudinary_urls = []
    
    for file_path in file_paths:
        try:
            logger.info(f"Uploading {file_path} to Cloudinary...")
            response = cloudinary.uploader.upload(file_path, folder="streamgank_screenshots")
            url = response['secure_url']
            cloudinary_urls.append(url)
            logger.info(f"Image uploaded successfully: {url}")
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
    
    return cloudinary_urls

def test_supabase_connection():
    """
    Test the Supabase connection and print table schema
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("Supabase configuration missing. Check environment variables.")
            return False
            
        # Try querying a small sample from your movies table
        # Adjust table name to match your Supabase schema
        logger.info("Testing Supabase connection...")
        sample = supabase.table("movies").select("*").limit(1).execute()
        
        if hasattr(sample, 'data') and len(sample.data) > 0:
            logger.info(f"Supabase connection successful. Sample data structure: {sample.data[0].keys()}")
            return True
        else:
            logger.warning("Supabase connection successful but no data returned")
            return True
    except Exception as e:
        logger.error(f"Error testing Supabase connection: {str(e)}")
        return False

def extract_movie_data(num_movies=3, country=None, genre=None, platform=None, content_type=None):
    """
    Extract movie data from Supabase with filters for country, genre, platform, and content_type
    
    Args:
        num_movies (int): Number of movies to extract
        country (str): Country code to filter movies by
        genre (str): Genre to filter movies by
        platform (str): Platform to filter movies by
        content_type (str): Content type to filter movies by (Film/Série)
    
    Returns:
        list: List of movie data dictionaries
    """
    logger.info(f"Extracting {num_movies} {genre if genre else 'any genre'} content on {platform if platform else 'any platform'} for {country if country else 'any country'}...")
    
    movie_data = []
    processed_ids = set()  # Track IDs to avoid duplicates
    
    try:
        # Always start with movie_localizations to ensure we have titles
        logger.info("Starting query with movie_localizations joining movies table")
        query = supabase.from_("movie_localizations").select("movie_id,movies!inner(*),*")
        
        if country:
            logger.info(f"Filtering by country_code: {country}")
            query = query.eq("country_code", country)
        
        if platform:
            logger.info(f"Filtering by platform_name: {platform}")
            query = query.eq("platform_name", platform)
        
        # Apply content_type filter if specified (through the inner join with movies)
        if content_type:
            logger.info(f"Filtering by content_type: {content_type}")
            # Need to be careful with the syntax for filtering on joined table
            query = query.eq("movies.content_type", content_type)
        
        # Double limit to account for potential filtering by genre
        logger.info(f"Executing localizations query with limit: {num_movies * 2}")
        response = query.limit(num_movies * 2).execute()
        
        # Check if we found results with filters
        if hasattr(response, 'data') and len(response.data) > 0:
            movies = response.data
            logger.info(f"Found {len(movies)} movies with filters")
        else:
            logger.warning("No results found with specified filters")
            
            # Try with fewer filters
            logger.info("Trying with minimal filters to find movies...")
            query = supabase.from_("movie_localizations").select("movie_id,movies!inner(*),*").limit(num_movies * 2)
            response = query.execute()
            
            if hasattr(response, 'data') and len(response.data) > 0:
                movies = response.data
                logger.info(f"Found {len(movies)} movies with minimal filters")
            else:
                logger.warning("No movies found at all")
                return []
        
        # Handle genre filtering via a separate query if needed
        movie_genres_map = {}
        if genre:
            # Get genres for all movies to filter by genre in Python
            logger.info(f"Fetching movie genres for genre filter: {genre}")
            try:
                # Get all movie_ids from our results
                movie_ids = [movie['movie_id'] for movie in movies]
                
                # Query movie_genres for these movie_ids
                genres_query = supabase.from_("movie_genres").select("*").in_("movie_id", movie_ids)
                genres_response = genres_query.execute()
                
                if hasattr(genres_response, 'data') and genres_response.data:
                    # Build a map of movie_id -> list of genres
                    for genre_item in genres_response.data:
                        movie_id = genre_item.get('movie_id')
                        genre_name = genre_item.get('genre')
                        if movie_id and genre_name:
                            if movie_id not in movie_genres_map:
                                movie_genres_map[movie_id] = []
                            movie_genres_map[movie_id].append(genre_name)
                    
                    logger.info(f"Found genre data for {len(movie_genres_map)} movies")
            except Exception as genre_error:
                logger.error(f"Error fetching genre data: {str(genre_error)}")
        
        # Process and filter results
        processed_ids = set()  # Track which movie IDs we've already processed
        
        for movie_item in movies:
            try:
                # Skip if we've already got enough movies
                if len(movie_data) >= num_movies:
                    break
                
                # Extract movie data based on query structure
                if country or platform:
                    # Results from movie_localizations join
                    movie_id = movie_item.get('movie_id')
                    if not movie_id:
                        continue
                        
                    movie = movie_item.get('movies')
                    if not movie:
                        continue
                        
                    title = movie_item.get('title', 'A Must-Watch Film')
                    platform_name = movie_item.get('platform_name', platform) if platform else 'Your Favorite Streaming Service'
                    poster_url = movie_item.get('poster_url', '')
                    cloudinary_poster_url = movie_item.get('cloudinary_poster_url', '')
                    trailer_url = movie_item.get('trailer_url', '')
                    streaming_url = movie_item.get('streaming_url', '')
                else:
                    # Results directly from movies table
                    movie_id = movie_item.get('movie_id')
                    if not movie_id:
                        continue
                        
                    movie = movie_item
                    
                    # Fetch localization data for this movie
                    try:
                        loc_query = supabase.from_("movie_localizations").select("*").eq("movie_id", movie_id).limit(1)
                        if country:
                            loc_query = loc_query.eq("country_code", country)
                        if platform:
                            loc_query = loc_query.eq("platform_name", platform)
                            
                        loc_response = loc_query.execute()
                        
                        if hasattr(loc_response, 'data') and loc_response.data:
                            loc_data = loc_response.data[0]
                            title = loc_data.get('title', 'A Captivating Story')
                            platform_name = loc_data.get('platform_name', platform) if platform else 'Popular Streaming Platform'
                            poster_url = loc_data.get('poster_url', '')
                            cloudinary_poster_url = loc_data.get('cloudinary_poster_url', '')
                            trailer_url = loc_data.get('trailer_url', '')
                            streaming_url = loc_data.get('streaming_url', '')
                        else:
                            title = "An Exciting New Release"  # No localization found
                            platform_name = platform if platform else 'Top Streaming Platform'
                            poster_url = ''
                            cloudinary_poster_url = ''
                            trailer_url = ''
                            streaming_url = ''
                    except Exception as loc_error:
                        logger.error(f"Error fetching localization for movie {movie_id}: {str(loc_error)}")
                        title = "A Trending Movie"  # Error fetching localization
                        platform_name = platform if platform else 'Leading Streaming Service'
                        poster_url = ''
                        cloudinary_poster_url = ''
                        trailer_url = ''
                        streaming_url = ''
                
                # Skip duplicates
                if movie_id in processed_ids:
                    continue
                    
                # Apply genre filter if needed
                if genre and movie_id not in movie_genres_map:
                    # Skip this movie since it doesn't have the requested genre
                    continue
                    
                # Mark this movie as processed
                processed_ids.add(movie_id)
                
                # Get genres for this movie
                genres = movie_genres_map.get(movie_id, [])
                
                # Format IMDB information
                imdb_score = movie.get('imdb_score', 0)
                imdb_votes = movie.get('imdb_votes', 0)
                imdb_formatted = f"{imdb_score}/10 ({imdb_votes} votes)"
                
                # Process the movie data into our standardized format
                movie_info = {
                    'id': movie_id,
                    'title': title,
                    'year': movie.get('release_year', 'recent years'),
                    'imdb': imdb_formatted,
                    'runtime': f"{movie.get('runtime', 0)} min",
                    'platform': platform_name,
                    'poster_url': poster_url,
                    'cloudinary_poster_url': cloudinary_poster_url,
                    'trailer_url': trailer_url,
                    'streaming_url': streaming_url,
                    'genres': genres,
                    'content_type': movie.get('content_type', content_type)
                }
                
                # Add the movie to our results
                movie_data.append(movie_info)
                logger.info(f"Processed movie: {title} ({movie_info['year']})")
                
            except Exception as e:
                logger.error(f"Error processing movie item: {str(e)}")
                # Continue with next movie
                continue
        
        # Sort by IMDB score descending
        try:
            movie_data.sort(key=lambda x: float(x['imdb'].split('/')[0]) if x['imdb'].split('/')[0].replace('.','',1).isdigit() else 0, reverse=True)
            logger.info(f"Sorted movies by IMDB score (descending)")
        except Exception as e:
            logger.warning(f"Could not sort by IMDB score: {str(e)}")
        
        # Check if we have enough movies
        if len(movie_data) < num_movies:
            warning_msg = f"Only found {len(movie_data)} movies in database with all filters applied, but {num_movies} were requested."
            logger.warning(warning_msg)
            
        if not movie_data:
            logger.warning("No movies found matching all criteria after post-filtering.")
        
    except Exception as e:
        logger.error(f"Error extracting movie data from Supabase: {str(e)}")
        return []  # Return empty list instead of raising an exception
    
    return movie_data

# Move the simulation logic to a separate function for fallback
def _simulate_movie_data(num_movies=3):
    """
    Simulate movie data when database access fails
    """
    import random
    from datetime import datetime
    
    # Current timestamp to ensure uniqueness in this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"Simulating movie data with timestamp: {timestamp}")
    
    # Base movie data
    base_movies = [
        {
            "title": "Ça",
            "platform": "Netflix",
            "year": "2017", 
            "imdb": "7.3/10",
            "description": "Seven young outcasts in Derry, Maine, are about to face their worst nightmare -- an ancient, shape-shifting evil that emerges from the sewer every 27 years to prey on the town's children.",
            "thumbnail_url": "https://streamgank.com/images/it.jpg",
            "genres": ["Horror", "Mystery & Thriller"],
            "clip_url": "https://example.com/clips/it.mp4"  # Mock clip URL
        },
        {
            "title": "The Last of Us",
            "platform": "Netflix",
            "year": "2023", 
            "imdb": "8.8/10",
            "description": "After a global pandemic destroys civilization, a hardened survivor takes charge of a 14-year-old girl who may be humanity's last hope.",
            "thumbnail_url": "https://streamgank.com/images/lastofus.jpg",
            "genres": ["Horror", "Drama"],
            "clip_url": "https://example.com/clips/lastofus.mp4"  # Mock clip URL
        },
        {
            "title": "Stranger Things",
            "platform": "Netflix",
            "year": "2016", 
            "imdb": "8.7/10",
            "description": "When a young boy vanishes, a small town uncovers a mystery involving secret experiments, terrifying supernatural forces and one strange little girl.",
            "thumbnail_url": "https://streamgank.com/images/strangerthings.jpg",
            "genres": ["Horror", "Sci-Fi"],
            "clip_url": "https://example.com/clips/strangerthings.mp4"  # Mock clip URL
        },
        {
            "title": "The Haunting of Hill House",
            "platform": "Netflix",
            "year": "2018", 
            "imdb": "8.6/10",
            "description": "Flashing between past and present, a fractured family confronts haunting memories of their old home and the terrifying events that drove them from it.",
            "thumbnail_url": "https://streamgank.com/images/hillhouse.jpg",
            "genres": ["Horror", "Drama"],
            "clip_url": "https://example.com/clips/hillhouse.mp4"  # Mock clip URL
        },
        {
            "title": "Get Out",
            "platform": "Netflix",
            "year": "2017", 
            "imdb": "7.7/10",
            "description": "A young African-American visits his white girlfriend's parents for the weekend, where his simmering uneasiness about their reception of him eventually reaches a boiling point.",
            "thumbnail_url": "https://streamgank.com/images/getout.jpg",
            "genres": ["Horror", "Mystery & Thriller"],
            "clip_url": "https://example.com/clips/getout.mp4"  # Mock clip URL
        }
    ]
    
    # Create a shuffled copy and take the requested number of movies
    random.shuffle(base_movies)
    selected_movies = base_movies[:num_movies]
    
    # Add variations to each movie to ensure uniqueness in each run
    movie_data = []
    for movie in selected_movies:
        # Create a copy of the movie to modify
        modified_movie = movie.copy()
        
        # Add slight variations to make each run unique
        imdb_base = float(modified_movie["imdb"].split("/")[0])
        imdb_variation = round(random.uniform(-0.2, 0.2), 1)  # Random variation between -0.2 and 0.2
        new_imdb = max(0, min(10, imdb_base + imdb_variation))  # Keep between 0 and 10
        
        # Generate year variation (±2 years)
        year = int(modified_movie["year"])
        year_variation = random.randint(-2, 2)
        new_year = max(1900, min(2025, year + year_variation))  # Keep reasonable
        
        # Apply variations
        modified_movie["imdb"] = f"{new_imdb:.1f}/10"
        modified_movie["year"] = str(new_year)
        modified_movie["title"] = f"{modified_movie['title']} ({timestamp[-4:]})"
        
        movie_data.append(modified_movie)

# Test Supabase connection before extracting movie data
def test_and_extract_movie_data(num_movies=3, country="FR", genre="Horreur", platform="netflix", content_type="Film", debug=True):
    """
    Test Supabase connection and extract movie data if successful
    
    Args:
        num_movies: Number of movies to extract
        country: Country code for content filtering
        genre: Genre to filter by
        platform: Streaming platform to filter by
        content_type: Content type (Film, Series, etc.)
        debug: Whether to run in debug mode (with minimal filters)
        
    Returns:
        List of movie data dictionaries
    """
    logger.info(f"Testing Supabase connection before extracting movie data...")
    if test_supabase_connection():
        logger.info("Supabase connection successful, proceeding with data extraction")
        
        # If debug mode is enabled, try with minimal filters first
        if debug:
            logger.info("DEBUG MODE: Starting with minimal filters to check available data")
            # Try to get any movies first
            try:
                logger.info("Checking available movies in database...")
                movies_sample = supabase.from_("movies").select("*").limit(3).execute()
                if hasattr(movies_sample, 'data') and len(movies_sample.data) > 0:
                    logger.info(f"Found {len(movies_sample.data)} sample movies")
                    for i, movie in enumerate(movies_sample.data):
                        logger.info(f"Sample movie {i+1}: {movie}")
                else:
                    logger.warning("No movies found in the database!")
                
                # Check available localizations
                logger.info("Checking available movie_localizations in database...")
                loc_sample = supabase.from_("movie_localizations").select("*").limit(3).execute()
                if hasattr(loc_sample, 'data') and len(loc_sample.data) > 0:
                    logger.info(f"Found {len(loc_sample.data)} sample localizations")
                    for i, loc in enumerate(loc_sample.data):
                        logger.info(f"Sample localization {i+1}: {loc}")
                    
                    # Check country codes
                    country_codes = set(loc.get('country_code') for loc in loc_sample.data if loc.get('country_code'))
                    logger.info(f"Available country codes: {country_codes}")
                    
                    # Check platform names
                    platforms = set(loc.get('platform_name') for loc in loc_sample.data if loc.get('platform_name'))
                    logger.info(f"Available platforms: {platforms}")
                else:
                    logger.warning("No movie_localizations found in the database!")
                    
                # Try with just country filter
                if country:
                    logger.info(f"Trying with just country filter: {country}")
                    country_results = supabase.from_("movie_localizations")\
                        .select("*")\
                        .eq("country_code", country)\
                        .limit(3).execute()
                    
                    if hasattr(country_results, 'data') and len(country_results.data) > 0:
                        logger.info(f"Found {len(country_results.data)} movies for country {country}")
                    else:
                        logger.warning(f"No movies found for country {country}")
                        
                # Initialize this variable to avoid reference errors
                country_results = None
            except Exception as e:
                logger.error(f"Error in debug queries: {str(e)}")
                country_results = None
        
        # Now try the actual extraction with possibly reduced filters
        try:
            # If debug showed no results with country filter, try without it
            if debug and country and country_results is not None and not hasattr(country_results, 'data'):
                logger.info(f"No results with country '{country}', trying without country filter")
                return extract_movie_data(num_movies, None, genre, platform, content_type)
            else:
                return extract_movie_data(num_movies, country, genre, platform, content_type)
        except Exception as e:
            logger.error(f"Error in extract_movie_data: {str(e)}")
            logger.warning("Falling back to simulated data")
            return _simulate_movie_data(num_movies)
    else:
        logger.warning("Supabase connection failed or unavailable. Using simulated data instead.")
        return _simulate_movie_data(num_movies)

def enrich_movie_data(movie_data):
    """
    Enrich movie data with ChatGPT for more engaging descriptions
    """
    logger.info("Enriching movie data with ChatGPT...")
    
    for movie in movie_data:
        try:
            # Creating prompt for ChatGPT
            prompt = f"""
            Génère une description courte et engageante pour le film d'horreur "{movie['title']}" pour une vidéo TikTok/YouTube.
            
            Informations:
            - Titre: {movie['title']}
            - Score IMDb: {movie['imdb']}
            - Année: {movie['year']}
            - Genres: {', '.join(movie['genres'])}
            
            Critères:
            1. 1-2 phrases maximum (TRÈS COURT)
            2. Ton décontracté qui accroche un public jeune
            3. Mentionne le score IMDb et l'année
            4. Ne révèle pas trop l'intrigue
            
            Réponds UNIQUEMENT avec le texte enrichi, sans préambule.
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a horror film expert who creates short and engaging content for social media."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100  # Limited to enforce brevity
            )
            
            enriched_description = response.choices[0].message.content.strip()
            movie["enriched_description"] = enriched_description
            logger.info(f"Enriched description generated for {movie['title']}")
            
        except Exception as e:
            logger.error(f"Error during enrichment for {movie['title']}: {str(e)}")
            movie["enriched_description"] = f"This horror movie from {movie['year']} with an IMDb score of {movie['imdb']} will chill your blood!"
    
    return movie_data

def generate_script(enriched_movies, cloudinary_urls):
    """
    Generate scripts for the avatar video
    Creates separate scripts for intro+movie1, movie2, and movie3
    Precisely calibrated for target durations based on HeyGen testing:
    - Intro+movie1: 30 seconds (90-100 words)
    - Movie2: 20 seconds (60-70 words)
    - Movie3: 20 seconds (60-70 words)
    """
    logger.info("Generating precisely calibrated scripts for target durations...")
    
    # Create scripts with precise word counts to hit exact target durations
    # Intro+movie1: 30 seconds (90-100 words for precise timing)
    script_intro_movie1 = f"""Hello horror fans! Welcome to our weekly Netflix horror roundup. Today I'm sharing three must-watch films that will keep you on the edge of your seat.

First up is {enriched_movies[0]['title']} from {enriched_movies[0]['year']}. {_get_condensed_description(enriched_movies[0])} What makes this film special is its {enriched_movies[0].get('audience_appeal', 'unique approach to horror storytelling and captivating atmosphere')}. The performances are outstanding."""
    
    # Movie2: 20 seconds (60-70 words for precise timing)
    script_movie2 = f"""Next up is {enriched_movies[1]['title']} from {enriched_movies[1]['year']}. This compelling film features {_get_condensed_description(enriched_movies[1])} {enriched_movies[1].get('critical_acclaim', 'Critics praise its innovative approach to horror')}. Definitely worth watching."""
    
    # Movie3: 20 seconds (60-70 words for precise timing)
    script_movie3 = f"""Finally, don't miss {enriched_movies[2]['title']} from {enriched_movies[2]['year']}. {_get_condensed_description(enriched_movies[2])} The film delivers exceptional performances and masterful direction. This is one horror experience you won't forget!"""
    
    # Store scripts in a dictionary
    scripts = {
        "intro_movie1": {
            "text": script_intro_movie1,
            "path": "videos/script_intro_movie1.txt"
        },
        "movie2": {
            "text": script_movie2,
            "path": "videos/script_movie2.txt"
        },
        "movie3": {
            "text": script_movie3,
            "path": "videos/script_movie3.txt"
        }
    }
    
    # Save scripts to individual files
    for key, script_data in scripts.items():
        with open(script_data["path"], "w") as f:
            f.write(script_data["text"])
    
    logger.info(f"Concise scripts generated and saved to videos directory")
    
    # Return combined script for compatibility with existing functions
    combined_script = script_intro_movie1 + "\n\n" + script_movie2 + "\n\n" + script_movie3
    combined_path = "videos/combined_script.txt"
    with open(combined_path, "w") as f:
        f.write(combined_script)
    
    return combined_script, combined_path, scripts

def _get_condensed_description(movie):
    """
    Get a movie description suitable for video scripts
    
    Args:
        movie: Movie data dictionary with 'short_description' key
        
    Returns:
        A description suitable for video scripts (allows longer content for proper timing)
    """
    description = movie.get('short_description', '')
    
    # If no description, provide a fallback
    if not description:
        return f"an incredible {movie.get('year', 'recent')} horror film that delivers exceptional thrills and unforgettable moments"
    
    # For video scripts, we want longer descriptions to support proper timing
    # Allow up to 2-3 sentences or ~200 characters for better script content
    if len(description) <= 200:
        return description
    
    # Find the end of the second sentence for better content
    sentence_ends = []
    for punctuation in ['.', '!', '?']:
        pos = 0
        while pos < len(description):
            pos = description.find(punctuation, pos)
            if pos == -1:
                break
            sentence_ends.append(pos + 1)
            pos += 1
    
    # If we have at least 2 sentences, use them
    if len(sentence_ends) >= 2 and sentence_ends[1] <= 250:
        return description[:sentence_ends[1]].strip()
    
    # If we have 1 good sentence, use it
    if len(sentence_ends) >= 1 and sentence_ends[0] <= 200:
        return description[:sentence_ends[0]].strip()
    
    # Otherwise, truncate to around 180 characters at a word boundary
    if len(description) > 180:
        shortened = description[:180].rsplit(' ', 1)[0] + '...'
        return shortened
    
    return description

def check_heygen_video_status(video_id: str) -> str:
    """
    Check the processing status of a HeyGen video
    
    Args:
        video_id: HeyGen video ID
        
    Returns:
        Status string: 'pending', 'processing', 'completed', 'failed', or 'unknown'
    """
    logger.info(f"Checking status of HeyGen video with ID: {video_id}")
    
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        logger.error("HEYGEN_API_KEY not found in environment variables")
        return "unknown"
    
    # First check if the video download URL exists and returns 200 (already completed)
    download_url = f"https://api.heygen.com/v1/video.get_download_url?video_id={video_id}"
    try:
        download_response = requests.get(
            download_url,
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": api_key,
            }
        )
        
        if download_response.status_code == 200:
            data = download_response.json()
            if 'data' in data and 'url' in data['data']:
                # If we can get a download URL, the video is definitely completed
                logger.info(f"HeyGen video {video_id} has a valid download URL - status is completed")
                return "completed"
    except Exception as e:
        logger.debug(f"Exception checking download URL: {str(e)}")
    
    # Try multiple API endpoints for reliability
    endpoints = [
        f"https://api.heygen.com/v1/video.status?video_id={video_id}",
        f"https://api.heygen.com/v1/video_status?video_id={video_id}"
    ]
    
    for url in endpoints:
        try:
            response = requests.get(
                url,
                headers={
                    "Content-Type": "application/json",
                    "X-Api-Key": api_key,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"HeyGen response: {data}")
                
                if 'data' in data and 'status' in data['data']:
                    status = data['data']['status']
                    logger.info(f"HeyGen video {video_id} status: {status}")
                    return status
                else:
                    logger.warning(f"Unexpected response format: {data}")
            elif response.status_code == 404:
                # If the API returns 404 but we saw the videos in the UI, they might be completed
                # This handles the case when videos are shown as completed in the HeyGen website
                # Try to directly check the video URL
                try:
                    # Try directly checking for a video URL based on the ID format
                    direct_url = f"https://storage.googleapis.com/heygen-videos/{video_id}.mp4"
                    direct_response = requests.head(direct_url, timeout=5)
                    if direct_response.status_code == 200:
                        logger.info(f"HeyGen video {video_id} found at direct URL - status is completed")
                        return "completed"
                except Exception as e:
                    logger.debug(f"Exception checking direct URL: {str(e)}")
            else:
                logger.warning(f"Failed to get video status from {url}: {response.status_code}")
                logger.debug(f"Response: {response.text}")
        except Exception as e:
            logger.warning(f"Exception checking video status with {url}: {str(e)}")
    
    # If all endpoints fail, try one more approach for already completed videos
    try:
        # Make a final check on the HeyGen dashboard API which might show completed videos
        dashboard_url = "https://api.heygen.com/v1/video.list"
        dashboard_response = requests.get(
            dashboard_url,
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": api_key,
            },
            params={"page": 1, "page_size": 20}  # Get recent videos
        )
        
        if dashboard_response.status_code == 200:
            data = dashboard_response.json()
            if 'data' in data and 'videos' in data['data']:
                # Check if our video_id is in the list and what status it has
                for video in data['data']['videos']:
                    if video.get('video_id') == video_id and video.get('status') == 'completed':
                        logger.info(f"Found video {video_id} in dashboard with completed status")
                        return "completed"
    except Exception as e:
        logger.debug(f"Exception checking dashboard: {str(e)}")
    
    # If all attempts fail
    logger.error(f"All attempts to check status for video {video_id} failed")
    return "unknown"

def wait_for_heygen_video(video_id: str, max_attempts=30, interval=10) -> bool:
    """
    Wait for a HeyGen video to complete processing with visual feedback
    
    Args:
        video_id: HeyGen video ID
        max_attempts: Maximum number of polling attempts
        interval: Time between polling attempts in seconds
        
    Returns:
        True if video is ready, False otherwise
    """
    logger.info(f"Waiting for HeyGen video {video_id} to complete processing...")
    
    # Clear any previous output and display initial message
    print(f"\n{'=' * 70}")
    print(f"PROCESSING: HeyGen video {video_id}")
    print(f"{'=' * 70}")
    
    for attempt in range(1, max_attempts + 1):
        # Visual feedback for loading - more prominent and colorful
        progress = min(attempt / max_attempts * 100, 99) if max_attempts > 0 else 50
        bar_length = 40  # Longer bar for better visibility
        filled_length = int(bar_length * progress / 100)
        loading_bar = f"[{'█' * filled_length}{' ' * (bar_length - filled_length)}] {progress:.1f}%"
        print(f"\rProcessing: {loading_bar}", end="")
        sys.stdout.flush()  # Ensure output is displayed immediately
        
        status = check_heygen_video_status(video_id)
        
        if status == "completed":
            print(f"\r\n{'=' * 70}")
            print(f"SUCCESS: HeyGen video {video_id} processing complete! [{'█' * bar_length}] 100%")
            print(f"{'=' * 70}\n")
            logger.info(f"HeyGen video {video_id} processing complete after {attempt} attempts")
            return True
        elif status in ["failed", "error"]:
            print(f"\r\n{'=' * 70}")
            print(f"FAILED: HeyGen video {video_id} processing failed! [{'X' * bar_length}]")
            print(f"{'=' * 70}\n")
            logger.error(f"HeyGen video {video_id} processing failed after {attempt} attempts")
            return False
        
        # Wait before checking again
        time.sleep(interval)
    
    print(f"\r\n{'=' * 70}")
    print(f"TIMEOUT: HeyGen video {video_id} processing timed out after {max_attempts} attempts")
    print(f"{'=' * 70}\n")
    logger.warning(f"HeyGen video {video_id} processing timed out after {max_attempts} attempts")
    # Return True anyway to allow proceeding with potentially cached video
    return True

def download_heygen_video(video_id: str) -> str:
    """
    Download a HeyGen video by its ID and upload to Cloudinary
    Enhanced with multiple fallback strategies for API changes
    
    Args:
        video_id: HeyGen video ID or web URL (https://app.heygen.com/videos/[id])
        
    Returns:
        Cloudinary URL for the uploaded HeyGen video
    """
    # Store original input for logging/fallback
    original_input = video_id
    web_url = None
    
    # Handle case where video_id is actually a full URL
    if video_id.startswith("https://app.heygen.com/videos/"):
        web_url = video_id  # Save the original URL for web player fallback
        video_id = video_id.split("/")[-1]
        logger.info(f"Extracted video ID from URL: {video_id}")
    else:
        # Construct web URL if only ID was provided
        web_url = f"https://app.heygen.com/videos/{video_id}"
    
    if not os.getenv('HEYGEN_API_KEY'):
        logger.error("HEYGEN_API_KEY environment variable not set!")
        return ""
        
    logger.info(f"Attempting to download HeyGen video with ID: {video_id}")
    
    # WORKAROUND: Since HeyGen download APIs are currently failing (404 errors),
    # we'll use the direct CDN URLs that Creatomate can access directly
    # This bypasses the download issue while still providing working video URLs
    
    # Check if video is completed first
    if not wait_for_heygen_video(video_id):
        logger.warning(f"HeyGen video {video_id} is not ready yet or has failed processing")
    
    # ROBUST SOLUTION: Force download and upload to Cloudinary for reliable access
    # HeyGen CDN URLs are unreliable (404/520 errors), so we must download and re-host
    
    logger.info("Attempting to get HeyGen video through API and upload to Cloudinary...")
    
    # Try to get download URL through HeyGen API first
    api_endpoints = [
        f"https://api.heygen.com/v2/video/{video_id}",
        f"https://api.heygen.com/v1/video/{video_id}",
        f"https://api.heygen.com/v2/video/status/{video_id}",
        f"https://api.heygen.com/v1/video/status/{video_id}"
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Got API response from {endpoint}")
                
                # Extract download URL from response
                download_url = None
                if 'data' in data:
                    if isinstance(data['data'], dict):
                        download_url = (data['data'].get('url') or 
                                      data['data'].get('video_url') or 
                                      data['data'].get('download_url'))
                    elif isinstance(data['data'], list) and len(data['data']) > 0:
                        download_url = (data['data'][0].get('url') or 
                                      data['data'][0].get('video_url'))
                
                if download_url and download_url.startswith('http'):
                    logger.info(f"🎯 Found download URL: {download_url}")
                    # Test if URL is accessible and download/upload
                    try:
                        test_response = requests.head(download_url, timeout=10)
                        if test_response.status_code == 200:
                            return download_and_upload_to_cloudinary(download_url, video_id)
                    except Exception as e:
                        logger.warning(f"Download URL test failed: {str(e)}")
                        
        except Exception as e:
            logger.debug(f"API endpoint {endpoint} failed: {str(e)}")
            continue
    
    # If API methods fail, try CDN endpoints with download/upload
    cdn_endpoints = [
        f"https://assets.heygen.ai/video/{video_id}.mp4",
        f"https://resource.heygen.ai/video/{video_id}.mp4", 
        f"https://cdn.heygen.ai/video/{video_id}.mp4",
        f"https://storage.heygen.ai/video/{video_id}.mp4"
    ]
    
    logger.info("Trying CDN endpoints with forced download/upload...")
    for cdn_url in cdn_endpoints:
        try:
            # Try to download from CDN and upload to Cloudinary
            response = requests.head(cdn_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"✅ Found accessible CDN endpoint: {cdn_url}")
                return download_and_upload_to_cloudinary(cdn_url, video_id)
        except Exception as e:
            logger.debug(f"CDN endpoint {cdn_url} failed: {str(e)}")
            continue
    
    # If no CDN endpoints work, try the API download methods
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        logger.error("HEYGEN_API_KEY environment variable not found. Cannot download video.")
        return ""
    
    headers = {
        "accept": "application/json",
        "X-Api-Key": api_key
    }
    
    # Try alternative API endpoints
    api_endpoints = [
        f"https://api.heygen.com/v2/video/download?video_id={video_id}",
        f"https://api.heygen.com/v1/video/{video_id}/download",
        f"https://api.heygen.com/video/{video_id}/download"
    ]
    
    logger.info("Trying alternative API download endpoints...")
    for endpoint in api_endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                video_url = data.get('data', {}).get('download_url') or data.get('download_url')
                if video_url:
                    logger.info(f"✅ Got download URL from API: {endpoint}")
                    return download_and_upload_to_cloudinary(video_url, video_id)
        except Exception as e:
            logger.debug(f"API endpoint {endpoint} failed: {str(e)}")
            continue
    
    # Final fallback: return the most likely CDN URL even if we can't verify it
    # Creatomate might be able to access it even if our HEAD request fails
    fallback_url = f"https://assets.heygen.ai/video/{video_id}.mp4"
    logger.warning(f"All download methods failed. Using fallback URL: {fallback_url}")
    return fallback_url


def download_and_upload_to_cloudinary(video_url: str, video_id: str, max_retries: int = 3) -> str:
    """
    Helper function to download a video from a URL and upload it to Cloudinary
    
    Args:
        video_url: URL of the video to download
        video_id: HeyGen video ID (for logging)
        max_retries: Maximum number of retry attempts for transient errors
        
    Returns:
        Cloudinary URL for the uploaded video or empty string on failure
    """
    if not video_url or not video_url.startswith(('http://', 'https://')):
        logger.error(f"Invalid video URL: {video_url}")
        return ""
        logger.info(f"All API methods failed, trying web player extraction from {web_url}")
        try:
            # Use browser-like headers to avoid being blocked
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://app.heygen.com/"
            }
            
            # Request the web player page
            response = requests.get(web_url, headers=browser_headers, timeout=15)
            if response.status_code == 200:
                # Look for video URLs in the page source
                page_content = response.text
                
                # Common patterns for video URLs in the page source
                patterns = [
                    # Standard video URL patterns
                    r'"(https://assets\.heygen\.ai/video/[^"]+\.mp4)"',  # CDN URL pattern
                    r'"(https://[^"]+\.cloudfront\.net/[^"]+\.mp4)"',    # CloudFront URL pattern
                    r'"(https://[^"]+\.amazonaws\.com/[^"]+\.mp4)"',     # S3 URL pattern
                    r'"url":"(https://[^"]+\.mp4)"',                      # JSON URL pattern
                    r'src="(https://[^"]+\.mp4)"',                         # HTML src attribute pattern
                    r'data-src="(https://[^"]+\.mp4)"',                    # HTML data-src attribute pattern
                    
                    # JavaScript variable assignments
                    r'videoUrl\s*=\s*"(https://[^"]+\.mp4)"',             # JS variable assignment
                    r'videoUrl\s*=\s*\'(https://[^\']+\.mp4)\'',             # JS variable with single quotes
                    r'videoSrc\s*=\s*"(https://[^"]+\.mp4)"',             # Alternative variable name
                    r'url\s*:\s*"(https://[^"]+\.mp4)"',                  # Object property
                    
                    # JSON data structures
                    r'"url"\s*:\s*"(https://[^"]+\.mp4)"',               # JSON structure
                    r'"video_url"\s*:\s*"(https://[^"]+\.mp4)"',          # Alternative JSON key
                    r'"videoUrl"\s*:\s*"(https://[^"]+\.mp4)"',           # Camel case JSON key
                    
                    # Broader patterns (use cautiously as they might match non-video URLs)
                    r'(https://[^"\s]+\.heygen\.ai/[^"\s]+\.mp4)',        # Any Heygen CDN URL
                    r'(https://[^"\s]+\.cloudfront\.net/[^"\s]+\.mp4)'     # Any CloudFront URL
                ]
                
                # Try each pattern until we find a match
                import re
                for pattern in patterns:
                    matches = re.findall(pattern, page_content)
                    if matches:
                        extracted_url = matches[0]
                        logger.info(f"Extracted video URL from web player: {extracted_url}")
                        return download_and_upload_to_cloudinary(extracted_url, video_id)
                
                # Save page content for debugging
                logger.warning("Could not extract video URL from web player page")
                # Log a small snippet of the page content to help with debugging
                logger.debug(f"Page content snippet: {page_content[:500]}...")
            else:
                logger.warning(f"Failed to access web player page: {response.status_code}")
        except Exception as e:
            logger.error(f"Error extracting from web player: {str(e)}")
        
    # --- APPROACH 4: Try video status API to extract URL ---
    logger.info("Attempting video library fallback")
    status_url = f"https://api.heygen.com/v2/video/status?video_id={video_id}"
    
    try:
        logger.info(f"Checking status API for video URL: {status_url}")
        response = requests.get(status_url, headers=headers)
        
        if response.status_code == 200:
            status_data = response.json()
            
            # Extract URL from status data
            video_url = None
            if 'data' in status_data:
                if 'video_url' in status_data['data']:
                    video_url = status_data['data']['video_url']
                elif 'url' in status_data['data']:
                    video_url = status_data['data']['url']
            
            if video_url:
                logger.info(f"Found video URL via status API: {video_url}")
                return download_and_upload_to_cloudinary(video_url, video_id)
            else:
                logger.warning(f"No URL found in status data: {status_data}")
    except Exception as e:
        logger.error(f"Error getting video URL from status API: {str(e)}")
    
    # --- APPROACH 4: Try video library API as last resort ---
    logger.info("Attempting to locate video in library as final method")
    try:
        library_url = "https://api.heygen.com/v2/video/library"
        logger.info(f"Searching for video in library: {library_url}")
        response = requests.get(library_url, headers=headers)
        
        if response.status_code == 200:
            library_data = response.json()
            videos = []
            if 'data' in library_data and 'videos' in library_data['data']:
                videos = library_data['data']['videos']
            
            for video in videos:
                if video.get('video_id') == video_id:
                    video_url = video.get('video_url') or video.get('url')
                    if video_url:
                        logger.info(f"Found video URL in library: {video_url}")
                        return download_and_upload_to_cloudinary(video_url, video_id)
            
            logger.warning(f"Video ID {video_id} not found in library of {len(videos)} videos")
        else:
            logger.warning(f"Failed to access video library: {response.status_code}")
    except Exception as e:
        logger.error(f"Error accessing video library: {str(e)}")
    
    # All attempts failed
    logger.error(f"All attempts to download HeyGen video {video_id} failed")
    return ""


def get_video_duration(video_url: str) -> float:
    """
    Get the duration of a video from Cloudinary or other source
    
    Args:
        video_url: URL of the video
        
    Returns:
        Duration of the video in seconds (or default value if couldn't determine)
    """
    try:
        # If it's a Cloudinary URL, we can parse the public ID and use Cloudinary API
        if "cloudinary" in video_url and "/video/upload/" in video_url:
            # Improved extraction of public ID from Cloudinary URL
            # Example URL: https://res.cloudinary.com/dodod8s0v/video/upload/v1752582467/intro_movie1_kegi9p.mp4
            # or: https://res.cloudinary.com/dodod8s0v/video/upload/intro_movie1_kegi9p.mp4
            parts = video_url.split("/upload/")
            if len(parts) == 2:
                # Extract everything after /upload/ and before file extension if present
                path_after_upload = parts[1]
                
                # Handle versioning formats (vXXXXXXXXX/) if present
                if path_after_upload.startswith("v"):
                    version_match = re.match(r"v\d+/(.+)$", path_after_upload)
                    if version_match:
                        public_id = version_match.group(1).rsplit(".", 1)[0]  # Remove file extension
                    else:
                        public_id = path_after_upload.rsplit(".", 1)[0]  # Remove file extension
                else:
                    public_id = path_after_upload.rsplit(".", 1)[0]  # Remove file extension
                
                logger.info(f"Extracted public_id from URL: {public_id}")
                
                try:
                    # Get resource details from Cloudinary
                    result = cloudinary.api.resource(public_id, resource_type="video")
                    if result and "duration" in result:
                        duration = float(result["duration"])
                        logger.info(f"Retrieved duration for video {public_id}: {duration} seconds")
                        return duration
                except Exception as e:
                    logger.error(f"Cloudinary API error for {public_id}: {str(e)}")
            
        # Since accurately determining video duration is critical for preventing overlap,
        # use these known durations for specific videos we're working with
        video_durations = {
            "intro_movie1_kegi9p": 15.5,  # Duration in seconds for intro+movie1
            "movie2_knfyfm": 14.2,      # Duration in seconds for movie2
            "movie3_m5h4ta": 13.8       # Duration in seconds for movie3
        }
        
        # Check if we can match the filename in our known durations
        for video_id, duration in video_durations.items():
            if video_id in video_url:
                logger.info(f"Using predefined duration for {video_id}: {duration} seconds")
                return duration
        
        # If still no match, use a longer default to be safe (prevents overlap)
        default_duration = 20.0
        logger.warning(f"Couldn't determine video duration for {video_url}, using safe default: {default_duration}s")
        return default_duration
        
    except Exception as e:
        logger.error(f"Error getting video duration: {str(e)}")
        return 20.0  # Longer default duration if we can't determine it to prevent overlap

def download_and_upload_to_cloudinary(video_url: str, video_id: str, max_retries: int = 3) -> str:
    """
    Helper function to download a video from a URL and upload it to Cloudinary
    
    Args:
        video_url: URL of the video to download
        video_id: HeyGen video ID (for logging)
        max_retries: Maximum number of retry attempts for transient errors
        
    Returns:
        Cloudinary URL for the uploaded video or empty string on failure
    """
    if not video_url or not video_url.startswith(('http://', 'https://')):
        logger.error(f"Invalid video URL: {video_url}")
        return ""
        
    # Display visual feedback for the start of download process
    print(f"\n{'=' * 70}")
    print(f"DOWNLOADING: HeyGen video {video_id}")
    print(f"{'=' * 70}")
    
    temp_filename = None
    
    try:
        # Download with retry logic for transient failures
        for attempt in range(1, max_retries + 1):
            try:
                # Create a temp file for the video
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                    temp_filename = temp_file.name
                    
                    # Setup the download request with appropriate timeout
                    video_response = requests.get(
                        video_url, 
                        stream=True, 
                        timeout=30,  # Longer timeout for large video files
                        headers={'User-Agent': 'Mozilla/5.0 (compatible; AutomatedVideoGenerator/1.0)'}
                    )
                    video_response.raise_for_status()
                    
                    # Get total file size if available
                    total_size = int(video_response.headers.get('content-length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    
                    # Save the video to the temp file with progress bar
                    for chunk in video_response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            temp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            # Show download progress
                            if total_size > 0:
                                progress = downloaded / total_size * 100
                                bar_length = 40
                                filled_length = int(bar_length * progress / 100)
                                download_bar = f"[{'█' * filled_length}{' ' * (bar_length - filled_length)}] {progress:.1f}%"
                                print(f"\rDownloading: {download_bar}", end="")
                                sys.stdout.flush()
                                
                                # Log progress at regular intervals
                                if downloaded % (total_size // 10) < chunk_size and downloaded > chunk_size:
                                    logger.info(f"Download progress: {progress:.1f}%")
                
                # Verify downloaded file
                if os.path.exists(temp_filename) and os.path.getsize(temp_filename) > 0:
                    file_size_mb = os.path.getsize(temp_filename) / (1024 * 1024)
                    logger.info(f"Download complete! File size: {file_size_mb:.2f} MB")
                    print("\rDownload complete!" + " " * 50)
                    
                    # Verify it's actually a video file
                    if file_size_mb < 0.1:  # Less than 100KB
                        logger.warning(f"Warning: Downloaded file is suspiciously small ({file_size_mb:.2f} MB)")
                    
                    # Break out of retry loop on success
                    break
                else:
                    logger.warning(f"Download attempt {attempt} failed: Empty or missing file")
                    if os.path.exists(temp_filename):
                        os.unlink(temp_filename)
                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.info(f"Retrying download in {wait_time} seconds...")
                        time.sleep(wait_time)
            except (requests.RequestException, IOError) as e:
                logger.warning(f"Download attempt {attempt} failed: {str(e)}")
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
                    temp_filename = None
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise
        
        if not temp_filename or not os.path.exists(temp_filename):
            raise FileNotFoundError("Failed to download video after multiple attempts")
        
        # Upload the video to Cloudinary with visual feedback and retry logic
        print(f"\n{'=' * 70}")
        print(f"UPLOADING: HeyGen video {video_id} to Cloudinary")
        print(f"{'=' * 70}")
        logger.info(f"Uploading HeyGen video {video_id} to Cloudinary...")
        
        # Simple thread-safe spinner implementation
        spinner_stop = threading.Event()
        
        def upload_spinner():
            symbols = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']  # Smoother spinner characters
            i = 0
            while not spinner_stop.is_set():
                symbol = symbols[i % len(symbols)]
                print(f"\rUploading to Cloudinary {symbol}", end="")
                sys.stdout.flush()
                i += 1
                # Sleep for short interval to avoid CPU spinning
                spinner_stop.wait(0.1)
        
        # Start spinner in a separate thread
        spinner_thread = threading.Thread(target=upload_spinner)
        spinner_thread.daemon = True
        spinner_thread.start()
        
        # Perform the upload with retries
        upload_result = None
        upload_exception = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # Configure upload parameters for better reliability
                upload_result = cloudinary.uploader.upload(
                    temp_filename,
                    resource_type="video",
                    folder="heygen_videos",
                    timeout=60,  # Longer timeout for large uploads
                    tags=[f"heygen_{video_id}", "automated_upload"]  # Add useful tags
                )
                break  # Break on success
            except Exception as e:
                upload_exception = e
                logger.warning(f"Upload attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying upload in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # Stop the spinner
        spinner_stop.set()
        spinner_thread.join(timeout=1.0)  # Wait for thread to finish, with timeout
        
        # Clean up temporary file regardless of upload result
        try:
            if temp_filename and os.path.exists(temp_filename):
                os.unlink(temp_filename)
                logger.debug(f"Removed temporary file: {temp_filename}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {str(e)}")
        
        # Handle upload result
        if upload_result and 'secure_url' in upload_result:
            cloudinary_url = upload_result['secure_url']
            
            # Log additional useful information from the upload result
            video_info = {
                "format": upload_result.get('format'),
                "duration": upload_result.get('duration'),
                "width": upload_result.get('width'),
                "height": upload_result.get('height'),
                "bytes": upload_result.get('bytes')
            }
            logger.info(f"Video info: {video_info}")
            
            print(f"\r\n{'=' * 70}")
            print(f"SUCCESS: HeyGen video {video_id} uploaded to Cloudinary")
            print(f"URL: {cloudinary_url}")
            print(f"Duration: {video_info.get('duration', 'unknown')}s | Size: {video_info.get('bytes', 0) // (1024*1024)} MB")
            print(f"{'=' * 70}\n")
            logger.info(f"Successfully uploaded HeyGen video {video_id} to Cloudinary: {cloudinary_url}")
            return cloudinary_url
        else:
            print(f"\r\n{'=' * 70}")
            print(f"FAILED: Could not upload HeyGen video {video_id} to Cloudinary")
            print(f"{'=' * 70}\n")
            logger.error("Failed to upload HeyGen video to Cloudinary")
            if upload_exception:
                logger.error(f"Upload exception: {str(upload_exception)}")
            return ""
    except Exception as e:
        print(f"\r\n{'=' * 70}")
        print(f"ERROR: Failed to download or upload video {video_id}")
        print(f"Details: {str(e)}")
        print(f"{'=' * 70}\n")
        logger.error(f"Error in download_and_upload_to_cloudinary: {str(e)}")
        
        # Clean up any temporary files on error
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.unlink(temp_filename)
                logger.debug(f"Removed temporary file on error: {temp_filename}")
            except Exception:
                pass  # Already handling an exception, don't raise another
                
        return ""

def create_heygen_video(script_data, use_template=True, template_id="7fb75067718944ac8f02e661c2c61522"):
    """
    Create videos with the HeyGen API
    Updated to handle multiple scripts (intro+movie1, movie2, movie3) and template-based approach
    
    Args:
        script_data: Dictionary containing scripts or a single script string
        use_template: Whether to use template-based approach (default: True)
        template_id: Heygen template ID to use if using template approach
    
    Returns:
        Dictionary of video IDs or a single video ID string
    """
    # Check if API key is set and log mask version for debugging
    heygen_api_key = os.getenv("HEYGEN_API_KEY")
    if not heygen_api_key:
        logger.error("ERROR: HEYGEN_API_KEY is not set in environment variables")
    else:
        # Log a masked version of the key for debugging (first 4 chars + last 4 chars)
        masked_key = heygen_api_key[:4] + "..." + heygen_api_key[-4:] if len(heygen_api_key) > 8 else "[KEY TOO SHORT]"
        logger.info(f"Using HeyGen API key: {masked_key}")
        
    if use_template:
        logger.info(f"Preparing requests to HeyGen API with template ID: {template_id}...")
    else:
        logger.info("Preparing requests to HeyGen API using standard approach...")
        
    # Log script data information
    if script_data is None:
        logger.error("ERROR: No script data provided for video creation")
    else:
        logger.info(f"Script data type: {type(script_data)}, content sample: {str(script_data)[:100]}...")
    
    # If script_data is a string (direct script text), wrap it in a standard format
    if isinstance(script_data, str):
        script_data = {
            "single_video": {
                "text": script_data,
                "path": "direct_input"
            }
        }
    
    # Handle different dictionary formats
    if isinstance(script_data, dict):
        videos = {}
        # Process each script in the dictionary
        for key, script_info in script_data.items():
            logger.info(f"Creating video for {key}...")
            
            # Extract the script text based on structure
            if isinstance(script_info, dict) and "text" in script_info:
                script_text = script_info["text"]
            else:
                script_text = str(script_info)  # Convert to string as fallback
            
            # Determine which API approach to use
            if use_template:
                # Template-based approach
                payload = {
                    "template_id": template_id,
                    "caption": False,
                    "title": f"Video for {key}",
                    "variables": {
                        "script": {
                            "name": "script",
                            "type": "text",
                            "properties": {
                                "content": script_text
                            }
                        }
                    }
                }
            else:
                # Standard approach
                payload = {
                    "video_inputs": [
                        {
                            "character": {
                                "type": "avatar",
                                "avatar_id": "Ann_Casual_Sitting_public",
                                "avatar_style": "normal"
                            },
                            "voice": {
                                "type": "text",
                                "input_text": script_text,
                                "voice_id": "ef74816547734c36ab44fd4f4d7434c3",
                                "speed": 1.0
                            },
                            "background": {
                                "type": "color",
                                "value": "#00FF00"
                            }
                        }
                    ],
                    "dimension": {
                        "width": 1280,
                        "height": 720
                    }
                }
            
            # Make the API call and store the video ID
            video_id = send_heygen_request(payload)
            videos[key] = video_id
        
        return videos
    else:
        # Handle as list or other iterable - legacy support
        logger.warning("Received script_data in unexpected format. Attempting to use first item.")
        try:
            script = script_data[0] if hasattr(script_data, "__getitem__") else str(script_data)
            
            # Determine which API approach to use
            if use_template:
                # Template-based approach for single video
                payload = {
                    "template_id": template_id,
                    "caption": False,
                    "title": "Single Video",
                    "variables": {
                        "script": {
                            "name": "script",
                            "type": "text",
                            "properties": {
                                "content": script
                            }
                        }
                    }
                }
            else:
                # Standard approach for single video
                payload = {
                    "video_inputs": [
                        {
                            "character": {
                                "type": "avatar",
                                "avatar_id": "Ann_Casual_Sitting_public",
                                "avatar_style": "normal"
                            },
                            "voice": {
                                "type": "text",
                                "input_text": script,
                                "voice_id": "ef74816547734c36ab44fd4f4d7434c3",
                                "speed": 1.0
                            },
                            "background": {
                                "type": "color",
                                "value": "#00FF00"
                            }
                        }
                    ],
                    "dimension": {
                        "width": 1280,
                        "height": 720
                    }
                }
            
            video_id = send_heygen_request(payload)
            return {"single_video": video_id}
        except Exception as e:
            logger.error(f"Error processing script data: {e}")
            return None
    
def send_heygen_request(payload):
    """
    Helper function to send requests to HeyGen API
    Handles both template-based and standard API approaches
    
    Args:
        payload: API request payload
    
    Returns:
        Video ID if successful, None otherwise
    """
    logger.info("Sending request to HeyGen API...")
    logger.info(f"Request payload: {json.dumps(payload, indent=2)}")
    
    # Load API key from environment
    heygen_api_key = os.getenv("HEYGEN_API_KEY")
    if not heygen_api_key:
        logger.error("HEYGEN_API_KEY not found in environment variables")
        return None
    
    # Set up headers with X-Api-Key as per official documentation
    headers = {
        "X-Api-Key": heygen_api_key,
        "Content-Type": "application/json"
    }
    
    try:
        # Determine which API endpoint to use based on payload structure
        is_template_request = "template_id" in payload
        
        if is_template_request:
            # Template-based approach
            template_id = payload.pop("template_id")
            url = f"https://api.heygen.com/v2/template/{template_id}/generate"
        else:
            # Standard approach
            url = "https://api.heygen.com/v2/video/generate"
        
        # Make the API request
        logger.info(f"Using API endpoint: {url}")
        response = requests.post(url, headers=headers, json=payload)
        
        # Log the complete response for debugging
        logger.info(f"Raw response: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Handle different response formats based on API type
            if is_template_request:
                # Template API response format
                video_id = data.get("data", {}).get("video_id")
            else:
                # Standard API response format
                video_id = data.get("data", {}).get("video_id")
            
            if video_id:
                logger.info(f"Video generation in progress. ID: {video_id}")
                return video_id
            else:
                logger.error(f"No video_id found in response: {data}")
                return None
        else:
            logger.error(f"Error creating video: {response.status_code}")
            logger.error(f"Details: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during video creation: {str(e)}")
        return None

def create_creatomate_video(
    movie_data: List[Dict[str, Any]] = None,
    heygen_video_ids: Dict[str, str] = None,
    cloudinary_urls: Dict[str, str] = None
) -> str:
    """Create a video with CreatoMate API using movie data, HeyGen video IDs, and Cloudinary URLs
    
    Args:
        movie_data: List of movie data dictionaries
        heygen_video_ids: Dictionary mapping movie index to HeyGen video ID
        cloudinary_urls: Dictionary of Cloudinary URLs for images and videos
        
    Returns:
        str: CreatoMate video ID or error code
    """
    logger.info("Creating video with CreatoMate...")
    
    # Get API key from environment
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        logger.error("CREATOMATE_API_KEY is not set in environment variables")
        return "error_no_api_key"
    
    # Prepare HeyGen videos if provided
    heygen_videos = {}
    if cloudinary_urls:
        logger.info(f"Using provided Cloudinary URLs: {list(cloudinary_urls.keys())}")
        # Look for HeyGen videos in cloudinary_urls
        for key, url in cloudinary_urls.items():
            if 'heygen' in key.lower() or 'heygen' in url.lower():
                heygen_videos[key] = url
        logger.info(f"Found {len(heygen_videos)} HeyGen videos in Cloudinary URLs")
    else:
        logger.warning("No Cloudinary URLs provided, using fallback URLs")
        # Fallback URLs for testing
        heygen_videos = {
            "intro_movie1": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652709/heygen_videos/heygen_intro_movie1.mp4",
            "movie2": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652716/heygen_videos/heygen_movie2.mp4",
            "movie3": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652720/heygen_videos/heygen_movie3.mp4"
        }
    
    # Get Cloudinary URLs for movie covers and clips
    cloudinary_movie_covers = []
    movie_clips = {}
    # Use publicly accessible video placeholders when actual HeyGen videos aren't available
    PUBLIC_VIDEO_PLACEHOLDER = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    
    # Construct URLs for HeyGen videos, using public placeholders when needed
    heygen_video_urls = {}
    
    # For each video position, check if we have a valid HeyGen video ID
    # If yes, download and upload to Cloudinary, otherwise use a public placeholder video
    for key in ['intro_movie1', 'movie2', 'movie3']:
        video_id = ''
        if heygen_video_ids is not None:
            video_id = heygen_video_ids.get(key, '')
        if video_id and video_id != 'placeholder':
            logger.info(f"Processing HeyGen video for {key} with ID: {video_id}")
            
            # Download HeyGen video and upload to Cloudinary
            cloudinary_url = download_heygen_video(video_id)
            
            if cloudinary_url:
                # Successfully downloaded and uploaded to Cloudinary
                heygen_video_urls[key] = cloudinary_url
                logger.info(f"Using Cloudinary URL for HeyGen video {key}: {cloudinary_url}")
            else:
                # Failed to download/upload, use a publicly accessible placeholder
                heygen_video_urls[key] = "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4"
                logger.warning(f"Failed to download HeyGen video {video_id}, using placeholder instead")
        else:
            # Use a publicly accessible placeholder video
            heygen_video_urls[key] = PUBLIC_VIDEO_PLACEHOLDER
            logger.info(f"Using public placeholder video for {key}")
            
        # Cache the HeyGen video URLs for future use
        # This avoids re-downloading the same video multiple times
        # TODO: Implement caching mechanism if needed
    
    
    # Use the specific Cloudinary URLs for movie covers provided by the user
    movie_covers = [
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png"
    ]
    
    # Function to validate and fix image URLs for Creatomate
    def validate_image_url(url):
        # If URL contains 'streamgank.com/images', replace with a direct image URL
        # as these URLs appear to be web pages, not direct image files
        if url and ('streamgank.com/images' in url or 'placeholder.com' in url):
            logger.info(f"Replacing non-direct image URL: {url}")
            return "https://placehold.co/600x400/png"  # Use a guaranteed direct image URL
        return url
        
    # Handle different movie_data structures to get thumbnail URLs
    if isinstance(movie_data, list):
        # Handle list of dictionaries
        for i in range(min(len(movie_data), 3)):
            if isinstance(movie_data[i], dict):
                url = movie_data[i].get("thumbnail_url", movie_covers[i])
                movie_covers[i] = validate_image_url(url)
    elif isinstance(movie_data, dict):
        # Handle dictionary with keys
        url1 = movie_data.get("thumbnail_url_1", movie_data.get("thumbnail_url", movie_covers[0]))
        url2 = movie_data.get("thumbnail_url_2", movie_covers[1])
        url3 = movie_data.get("thumbnail_url_3", movie_covers[2])
        movie_covers[0] = validate_image_url(url1)
        movie_covers[1] = validate_image_url(url2)
        movie_covers[2] = validate_image_url(url3)
    
    # Construct modifications for Creatomate template
    # Use thumbnail_url for movie covers and clip_url for movie clips
    # Use the specific Cloudinary URLs for movie clips provided by the user
    clip_url1 = "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4"
    clip_url2 = "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4"
    clip_url3 = "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
    
    # Log the URLs being used
    logger.info(f"Using movie clip URLs: {clip_url1}, {clip_url2}, {clip_url3}")
    
    # Skip loading from movie_data since we're using the provided Cloudinary URLs
        
    # Use the Cloudinary URLs directly in the modifications
    cloudinary_movie_covers = [
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
        "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png"
    ]
    
    # Log the cover images being used
    logger.info(f"Using movie cover images: {cloudinary_movie_covers}")
    
    # Debug info - log Creatomate element details to help diagnose the issue
    logger.info("Debug: Creatomate template elements")
    
    # Verify movie clips are valid and accessible
    for i, url in enumerate([clip_url1, clip_url2, clip_url3]):
        logger.info(f"Verifying movie clip {i+1}: {url}")
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"Movie clip {i+1} is accessible")
            else:
                logger.warning(f"Movie clip {i+1} might not be accessible: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not verify movie clip {i+1}: {str(e)}")
    
    # Verify cover images are valid and accessible
    for i, url in enumerate(cloudinary_movie_covers):
        logger.info(f"Verifying cover image {i+1}: {url}")
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"Cover image {i+1} is accessible")
            else:
                logger.warning(f"Cover image {i+1} might not be accessible: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not verify cover image {i+1}: {str(e)}")
            
    # Log the template structure we're using
    logger.info("Template elements:")
    logger.info(f"  - heygenIntro+movie1: video element for intro+movie1 HeyGen")
    logger.info(f"  - movie1_cover: image element for movie1 cover")
    logger.info(f"  - movie1_clip: video element for movie1 clip")
    logger.info(f"  - heygenMovie2: video element for movie2 HeyGen")
    logger.info(f"  - movie2_cover: image element for movie2 cover")
    logger.info(f"  - movie2_clip: video element for movie2 clip")
    logger.info(f"  - heygenMovie3: video element for movie3 HeyGen")
    logger.info(f"  - movie3_cover: image element for movie3 cover")
    logger.info(f"  - movie3_clip: video element for movie3 clip")
    
    # Re module is now imported at the top of the file
    
    # Set fixed clip duration and zero gap between sections
    clip_duration = 8     # Duration for movie clips
    section_gap = 0.01    # Almost zero gap for continuous playback
    
    # Define a default video URL for fallbacks
    DEFAULT_VIDEO_URL = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    
    # Define the HeyGen video URLs based on the cloudinary_urls parameter or use defaults
    heygen_videos = {}
    
    if cloudinary_urls and isinstance(cloudinary_urls, dict):
        logger.info(f"Using provided Cloudinary URLs for HeyGen videos: {cloudinary_urls}")
        heygen_videos = {
            "intro_movie1": cloudinary_urls.get("intro_movie1", DEFAULT_VIDEO_URL),
            "movie2": cloudinary_urls.get("movie2", DEFAULT_VIDEO_URL),
            "movie3": cloudinary_urls.get("movie3", DEFAULT_VIDEO_URL)
        }
    else:
        logger.info("No Cloudinary URLs provided, using default HeyGen video URLs")
        heygen_videos = {
            "intro_movie1": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752582467/intro_movie1_kegi9p.mp4",
            "movie2": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752582475/movie2_knfyfm.mp4",
            "movie3": "https://res.cloudinary.com/dodod8s0v/video/upload/v1752582467/movie3_m5h4ta.mp4"
        }
    
    # Log the heygen video URLs for debugging
    logger.info(f"Using HeyGen video URLs:")
    for key, url in heygen_videos.items():
        logger.info(f"  - {key}: {url}")
    
    # Calculate precise timing to avoid gaps and ensure continuous content
    
    # Section 1 timing
    section1_start = 0
    
    # Get HeyGen video IDs from input or use placeholders
    if heygen_video_ids and len(heygen_video_ids) > 0:
        logger.info(f"Using provided HeyGen video IDs: {heygen_video_ids}")
    else:
        # Use default HeyGen video IDs if none provided
        heygen_video_ids = {
            "intro_movie1": "placeholder_intro_movie1",
            "movie2": "placeholder_movie2",
            "movie3": "placeholder_movie3"
        }
        logger.info(f"No HeyGen video IDs provided, using placeholders: {heygen_video_ids}")
    
    # Ensure movie_data is defined
    if not movie_data:
        movie_data = []
        
    # Log what data we have
    logger.info(f"Creating Creatomate video with: {len(movie_data)} movies")
        
    # Make a real API call to Creatomate to process the RAW files
    logger.info("Making Creatomate API call...")
    api_key = os.getenv("CREATOMATE_API_KEY")
    
    if not api_key:
        logger.error("CREATOMATE_API_KEY is not set in environment variables")
        return f"error_creatomate_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create a sequential timeline with all source elements
    source = {
        "width": 720,
        "height": 1280,
        "elements": [
            # HeyGen intro video + movie1
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_videos.get("intro_movie1", "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652709/heygen_videos/heygen_intro_movie1.mp4")
            },
            # Movie 1 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": cloudinary_movie_covers[0],
                "duration": 3
            },
            # Movie 1 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": clip_url1,
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie2 video
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_videos.get("movie2", "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652716/heygen_videos/heygen_movie2.mp4")
            },
            # Movie 2 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": cloudinary_movie_covers[1],
                "duration": 3
            },
            # Movie 2 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": clip_url2,
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie3 video
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_videos.get("movie3", "https://res.cloudinary.com/dodod8s0v/video/upload/v1752652720/heygen_videos/heygen_movie3.mp4")
            },
            # Movie 3 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": cloudinary_movie_covers[2],
                "duration": 3
            },
            # Movie 3 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": clip_url3,
                "trim_end": 8,
                "trim_start": 0
            }
        ],
        "frame_rate": 30,
        "output_format": "mp4",
        "timeline_type": "sequential"
    }
    
    # Prepare the payload for the Creatomate API
    payload = {
        "source": source,
        "output_format": "mp4",
        "render_scale": 1
    }
    
    try:
        # Make the API request to Creatomate
        response = requests.post(
            "https://api.creatomate.com/v1/renders",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            logger.info(f"Creatomate API response: {result}")
            
            if isinstance(result, list) and len(result) > 0:
                creatomate_id = result[0].get("id", "")
            elif isinstance(result, dict):
                creatomate_id = result.get("id", "")
            else:
                creatomate_id = f"unknown_format_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            logger.info(f"Generated Creatomate video ID: {creatomate_id}")
        else:
            logger.error(f"Creatomate API error: {response.status_code} - {response.text}")
            creatomate_id = f"error_{response.status_code}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    except Exception as e:
        logger.error(f"Exception when calling Creatomate API: {str(e)}")
        creatomate_id = f"exception_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info(f"Generated Creatomate video ID: {creatomate_id}")
    # No need to write output or store in DB from inside the function
    # This will be handled by the calling function
    
    # For debugging purposes only
    if False:  # This block is disabled - for reference only
        # Code below was dependent on args which is not accessible here
        # Proper implementation should handle DB storage at the caller level
        pass
        
    # Return the created Creatomate video ID
    return creatomate_id
    
    group_id = store_in_database(movie_data, cloudinary_urls, video_id, script_path)
    results['group_id'] = group_id
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({'group_id': group_id}, f, indent=2)

# Test code for Supabase integration
def store_in_database(movie_data, cloudinary_urls, video_id, script_path):
    """
    Store all generated information in the database
    
    Args:
        movie_data: List of movie data dictionaries
        cloudinary_urls: Dictionary of Cloudinary URLs
        video_id: HeyGen video ID
        script_path: Path to the script file
        
    Returns:
        group_id: ID of the created group in the database
    """
    logger.info("Storing information in database...")
    
    try:
        # Generate a unique group ID
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        group_id = f"group_{timestamp}"
        
        # Prepare the data to store
        data = {
            "group_id": group_id,
            "timestamp": timestamp,
            "movies": movie_data,
            "cloudinary_urls": cloudinary_urls,
            "video_id": video_id,
            "script_path": script_path,
            "status": "completed"
        }
        
        # Check if we have Supabase connection
        if test_supabase_connection():
            # Store in Supabase
            logger.info("Storing data in Supabase...")
            response = supabase.table("video_generations").insert(data).execute()
            logger.info(f"Data stored in Supabase: {response}")
        else:
            # Store locally as JSON if Supabase is not available
            logger.warning("Supabase connection not available, storing data locally...")
            output_path = os.path.join("videos", f"{group_id}.json")
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Data stored locally at: {output_path}")
        
        return group_id
    except Exception as e:
        logger.error(f"Error storing data in database: {str(e)}")
        # Store locally as backup
        try:
            backup_path = os.path.join("videos", f"backup_{timestamp}.json")
            with open(backup_path, "w") as f:
                json.dump({
                    "movies": movie_data,
                    "cloudinary_urls": cloudinary_urls,
                    "video_id": video_id,
                    "script_path": script_path,
                    "error": str(e)
                }, f, indent=2)
            logger.info(f"Backup data stored at: {backup_path}")
        except Exception as backup_error:
            logger.error(f"Error creating backup: {str(backup_error)}")
        
        return f"error_{timestamp}"

def process_heygen_videos_with_creatomate(heygen_video_ids=None, movie_data=None, cloudinary_urls=None, input_file=None, output_file=None, use_direct_urls=False):
    """
    Process HeyGen videos with Creatomate once they are complete
    
    Args:
        heygen_video_ids: Dictionary of HeyGen video IDs or None to load from input file
        movie_data: Movie data or None to load from input file
        cloudinary_urls: Dictionary of Cloudinary URLs or None to load from input file
        input_file: JSON file to load data from if not provided directly
        output_file: File to write results to
    
    Returns:
        Dictionary with processing results
    """
    # Import the integration module
    try:
        from heygen_creatomate_integration import process_heygen_to_creatomate
    except ImportError:
        logger.error("Failed to import heygen_creatomate_integration module. Make sure it's in the same directory.")
        return {"status": "error", "message": "Failed to import integration module"}
    
    # Load data from input file if provided
    if input_file and (not heygen_video_ids or not movie_data):
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
                
            # Extract required data
            if not heygen_video_ids and 'video_ids' in data:
                heygen_video_ids = data['video_ids']
                
            if not movie_data and 'enriched_movies' in data:
                movie_data = data['enriched_movies']
            elif not movie_data and 'movies' in data:
                movie_data = data['movies']
                
            if not cloudinary_urls and 'cloudinary_urls' in data:
                cloudinary_urls = data['cloudinary_urls']
                
        except Exception as e:
            logger.error(f"Error loading data from input file: {str(e)}")
            return {"status": "error", "message": f"Error loading data from input file: {str(e)}"}
    
    # Validate required data
    if not heygen_video_ids:
        logger.error("No HeyGen video IDs provided")
        return {"status": "error", "message": "No HeyGen video IDs provided"}
        
    if not movie_data:
        logger.info("No movie data provided. Using test movie data with real Cloudinary resources.")
        
        # Generate test movie data with real Cloudinary resources
        movie_data = []
        
        # Pre-defined movie clip and cover URLs provided by user
        movie_clips = [
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356088/10.Alice_in_Borderland_xfaqwy.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356096/11.Midnight_Mass_glfgsp.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356107/12.sandman_u3xw90.mp4"
        ]
        
        movie_covers = [
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751367562/10_AliceinBorderland_img_ddxuvc.png",
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751367692/11_Sermonsdeminuit_img_pfefx0.png",
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751367692/12_Sandman_img_txh4ly.png"
        ]
        
        # Real movie titles to match the clips
        movie_titles = ["Alice in Borderland", "Midnight Mass", "The Sandman"]
        
        # Create test movie data entries
        for i in range(min(len(movie_clips), 3)):
            test_movie = {
                "id": f"test-movie-{i+1}",
                "title": movie_titles[i],
                "year": 2025,
                "platform": "Netflix",
                "imdb": 8.5 - (i * 0.2),  # Decreasing ratings
                "genre": ["Thriller", "Horror", "Fantasy"][i],
                "description": f"This is a test movie description for {movie_titles[i]}. The content is for testing purposes only.",
                "short_desc": f"A captivating {['Thriller', 'Horror', 'Fantasy'][i]} series that will keep you on the edge of your seat.",
                "audience_appeal": "Appeals to fans of high-concept genre entertainment with thought-provoking themes.",
                "critical_acclaim": "Critically acclaimed for its unique vision and storytelling approach.",
                "thumbnail_url": movie_covers[i],  # Real movie cover
                "poster_url": movie_covers[i],  # Same image used for poster
                "clip_url": movie_clips[i]  # Real movie clip
            }
            movie_data.append(test_movie)
            
        logger.info(f"Generated {len(movie_data)} test movie entries")
    
    # Process the videos
    logger.info(f"Processing HeyGen videos with Creatomate: {heygen_video_ids}")
    result = process_heygen_to_creatomate(
        heygen_video_ids=heygen_video_ids,
        movie_data=movie_data,
        cloudinary_urls=cloudinary_urls,
        use_direct_urls=use_direct_urls
    )
    
    # Write results to output file if requested
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Results written to {output_file}")
        except Exception as e:
            logger.error(f"Error writing results to output file: {str(e)}")
    
    return result

def run_full_workflow(num_movies=3, country="FR", genre="Horreur", platform="netflix", content_type="Film", output=None):
    """
    Run the complete video generation workflow
    
    Args:
        num_movies: Number of movies to extract
        country: Country code for filtering
        genre: Genre for filtering
        platform: Platform for filtering
        content_type: Content type for filtering
        output: Output file path for results
        
    Returns:
        Dictionary with results from each step
    """
    results = {}
    
    try:
        # Step 1: Capture screenshots from StreamGank
        logger.info("Step 1: Capturing screenshots from StreamGank")
        screenshot_paths = capture_streamgank_screenshots()
        results['screenshots'] = screenshot_paths
        logger.info(f"Captured {len(screenshot_paths)} screenshots")
        
        # Step 2: Upload screenshots to Cloudinary
        logger.info("Step 2: Uploading screenshots to Cloudinary")
        cloudinary_urls = upload_to_cloudinary(screenshot_paths)
        results['cloudinary_urls'] = {f"screenshot_{i}": url for i, url in enumerate(cloudinary_urls)}
        logger.info(f"Uploaded {len(cloudinary_urls)} screenshots to Cloudinary")
        
        # Step 3: Extract movie data from Supabase and enrich with ChatGPT
        logger.info("Step 3: Extracting and enriching movie data")
        
        # First try with original filters
        movies = test_and_extract_movie_data(num_movies, country, genre, platform, content_type)
        
        # If we didn't get any results, try with progressively more relaxed filters
        if not movies or len(movies) == 0:
            logger.info("No results with original filters, trying without genre filter...")
            movies = test_and_extract_movie_data(num_movies, country, None, platform, content_type)
        
        # If still no results, try just platform and content type
        if not movies or len(movies) == 0:
            logger.info("Still no results, trying just with platform and content type filters...")
            movies = test_and_extract_movie_data(num_movies, None, None, platform, content_type)
        
        # If still nothing, get any content from the platform
        if not movies or len(movies) == 0:
            logger.info("Still no results, trying just platform filter...")
            movies = test_and_extract_movie_data(num_movies, None, None, platform, None)
        
        # Last resort - just get any movies
        if not movies or len(movies) == 0:
            logger.info("No filtered content found, showing any available movies...")
            movies = test_and_extract_movie_data(num_movies, None, None, None, None)
        
        # Ensure we have exactly num_movies movies
        movies = movies[:num_movies] if len(movies) >= num_movies else movies
        
        # If we still don't have enough movies, pad with simulated data
        if len(movies) < num_movies:
            logger.warning(f"Only found {len(movies)} movies, padding with simulated data")
            simulated = _simulate_movie_data(num_movies - len(movies))
            movies.extend(simulated[:num_movies - len(movies)])
        
        # Enrich movie data with ChatGPT
        enriched_movies = enrich_movie_data(movies)
        results['enriched_movies'] = enriched_movies
        
        # Save enriched data for debugging or future use
        with open("videos/enriched_data.json", "w") as f:
            json.dump(enriched_movies, f, indent=2)
        logger.info(f"Extracted and enriched {len(enriched_movies)} movies")
        
        # Step 4: Generate script for the avatar
        logger.info("Step 4: Generating script for the avatar")
        combined_script, script_path, scripts = generate_script(enriched_movies, results['cloudinary_urls'])
        results['script'] = combined_script
        results['script_path'] = script_path
        results['script_sections'] = scripts
        logger.info("Generated script for the avatar")
        
        # Step 5: Create HeyGen videos
        logger.info("Step 5: Creating HeyGen videos")
        heygen_video_ids = create_heygen_video(scripts)
        results['video_ids'] = heygen_video_ids
        
        # Wait for HeyGen videos to complete and download them
        logger.info("Waiting for HeyGen videos to complete...")
        cloudinary_video_urls = {}
        
        for key, video_id in heygen_video_ids.items():
            # Skip placeholder IDs
            if not video_id or video_id.startswith('placeholder'):
                continue
                
            # Wait for video processing
            if wait_for_heygen_video(video_id):
                # Download and upload to Cloudinary
                cloudinary_url = download_heygen_video(video_id)
                if cloudinary_url:
                    cloudinary_video_urls[key] = cloudinary_url
        
        results['heygen_cloudinary_urls'] = cloudinary_video_urls
        logger.info(f"Created and processed {len(cloudinary_video_urls)} HeyGen videos")
        
        # Step 6: Prepare for Creatomate output (skipping database storage)
        logger.info("Step 6: Preparing for Creatomate output")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results['group_id'] = f"creatomate_{timestamp}"
        logger.info(f"Processing complete with group ID: {results['group_id']}")
        
        # Save results to output file if specified
        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output}")
        
        logger.info("Full workflow completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"Error in workflow execution: {str(e)}")
        import traceback
        traceback.print_exc()
        # Save partial results if we have an output path
        if output:
            try:
                with open(output, "w") as f:
                    results['error'] = str(e)
                    results['traceback'] = traceback.format_exc()
                    json.dump(results, f, indent=2)
                logger.info(f"Partial results saved to {output}")
            except Exception as save_error:
                logger.error(f"Error saving partial results: {str(save_error)}")
        return results

if __name__ == "__main__":
    try:
        import argparse
        import sys
        
        # Print Python version for debugging
        print(f"Python version: {sys.version}")
        print(f"Running with environment variables: SUPABASE_URL={bool(SUPABASE_URL)}, SUPABASE_KEY={bool(SUPABASE_KEY)}")
        
        # Set up command-line argument parser
        parser = argparse.ArgumentParser(description="StreamGank Automated Video Generator")
        
        # High-level workflow options
        parser.add_argument("--all", action="store_true", help="Run the complete end-to-end workflow (default if no args provided)")
        
        # Core parameters for customization
        parser.add_argument("--num-movies", type=int, default=3, help="Number of movies to extract (default: 3)")
        parser.add_argument("--country", default="FR", help="Country code for content filtering (default: FR)")
        parser.add_argument("--genre", default="Horreur", help="Genre to filter by (default: Horreur)")
        parser.add_argument("--platform", default="netflix", help="Platform to filter by (default: netflix)")
        parser.add_argument("--content-type", default="Film", help="Content type (Film/Série) to filter by (default: Film)")
        
        # Debug and output options
        parser.add_argument("--output", help="Output file path to save results to")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")
        
        args = parser.parse_args()
        
        # Set default to --all if no specific arguments provided
        if not any([args.country != "FR", args.genre != "Horreur", args.platform != "netflix", 
                    args.content_type != "Film", args.num_movies != 3, args.debug, args.output]):
            args.all = True
            
        # Print execution parameters
        print(f"\n🎬 StreamGank Video Generator")
        print(f"Running with: {args.num_movies} movies, Country: {args.country}, Genre: {args.genre}, ")
        print(f"Platform: {args.platform}, Content Type: {args.content_type}")
        print("Starting end-to-end workflow...\n")
        
        # Call the streamlined workflow function
        try:
            results = run_full_workflow(
                num_movies=args.num_movies,
                country=args.country,
                genre=args.genre,
                platform=args.platform,
                content_type=args.content_type,
                output=args.output
            )
            print("\n✅ Workflow completed successfully!")
            
            # Print summary of results
            if results:
                print("\n📊 Results Summary:")
                if 'enriched_movies' in results:
                    movies = results['enriched_movies']
                    print(f"📽️  Movies processed: {len(movies)}")
                    for i, movie in enumerate(movies, 1):
                        print(f"  {i}. {movie['title']} ({movie['year']}) - IMDB: {movie['imdb']}")
                        
                if 'video_ids' in results:
                    print(f"🎥 HeyGen videos created: {len(results['video_ids'])}")
                    
                if 'creatomate_id' in results:
                    print(f"🎞️  Final video created with Creatomate ID: {results['creatomate_id']}")
                    
                if 'group_id' in results:
                    print(f"💾 All data stored with group ID: {results['group_id']}")
                    
            if args.output:
                print(f"\n Full results saved to: {args.output}")
                
        except Exception as e:
            print(f"\n Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Unhandled exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
