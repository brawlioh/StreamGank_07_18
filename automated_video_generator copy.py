



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
    python3 automated_video_generator.py --country FR --platform Netflix --genre Horreur --content-type Film
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

# Import StreamGank helper functions for country-specific mappings
from streamgank_helpers import (
    get_genre_mapping_by_country,
    get_platform_mapping_by_country,
    get_content_type_mapping_by_country,
    build_streamgank_url,
    process_movie_trailers_to_clips
)

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


def capture_streamgank_screenshots(country=None, genre=None, platform=None, content_type=None):
    """
    Capture screenshots of StreamGank in mobile format - fully dynamic based on CLI arguments
    
    Args:
        country (str): Country code for filtering (from CLI args)
        genre (str): Genre to filter by (from CLI args)  
        platform (str): Platform to filter by (from CLI args)
        content_type (str): Content type to filter by (from CLI args)
        
    Returns:
        list: List of screenshot file paths
    """
    # Comprehensive logging of arguments
    logger.info(f"📸 CAPTURE_STREAMGANK_SCREENSHOTS FUNCTION CALLED")
    logger.info(f"📋 CLI Arguments Received:")
    logger.info(f"   --country: {country}")
    logger.info(f"   --genre: {genre}")
    logger.info(f"   --platform: {platform}")
    logger.info(f"   --content-type: {content_type}")
    
    # Build dynamic StreamGank URL using helper function
    url = build_streamgank_url(country, genre, platform, content_type)
    
    # Log the constructed URL with parameter details
    logger.info(f"🌐 CONSTRUCTED STREAMGANK URL:")
    logger.info(f"   {url}")
    
    # Log individual parameters for transparency
    if country:
        logger.info(f"   ✅ URL param added: country={country}")
    if genre:
        genre_mapping = get_genre_mapping_by_country(country)
        streamgank_genre = genre_mapping.get(genre, genre)
        logger.info(f"   ✅ URL param added: genres={streamgank_genre} (country: {country})")
    if platform:
        platform_mapping = get_platform_mapping_by_country(country)
        streamgank_platform = platform_mapping.get(platform, platform.lower())
        logger.info(f"   ✅ URL param added: platforms={streamgank_platform} (country: {country})")
    if content_type:
        type_mapping = get_content_type_mapping_by_country(country)
        streamgank_type = type_mapping.get(content_type, content_type)
        logger.info(f"   ✅ URL param added: type={streamgank_type} (country: {country})")
    
    if not any([country, genre, platform, content_type]):
        logger.warning("⚠️ No CLI arguments provided, using default StreamGank homepage")
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

def extract_movie_data(num_movies=3, country=None, genre=None, platform=None, content_type=None, debug=False):
    """
    Extract top movies by IMDB score from Supabase with exact filtering
    
    This function is fully dynamic - it uses the exact parameters passed from command line arguments
    instead of hardcoded defaults, making it responsive to user input. If no movies match the exact
    criteria specified, it returns simulated data rather than relaxing filters.
    
    Args:
        num_movies (int): Number of movies to extract (default: 3)
        country (str): Country code for filtering (passed from CLI args, None = no filter)
        genre (str): Genre to filter by (passed from CLI args, None = no filter)
        platform (str): Platform to filter by (passed from CLI args, None = no filter)
        content_type (str): Content type to filter by (passed from CLI args, None = no filter)
        debug (bool): Enable debug mode with connection testing and detailed logging
        
    Returns:
        list: List of top movies by IMDB score matching exact criteria, or simulated data if no matches
    """
    # Comprehensive logging of arguments and context
    logger.info(f"🎬 EXTRACT_MOVIE_DATA FUNCTION CALLED")
    logger.info(f"📋 CLI Arguments Received:")
    logger.info(f"   --num-movies: {num_movies}")
    logger.info(f"   --country: {country}")
    logger.info(f"   --genre: {genre}")
    logger.info(f"   --platform: {platform}")
    logger.info(f"   --content-type: {content_type}")
    logger.info(f"   --debug: {debug}")
    logger.info(f"🎯 Extracting top {num_movies} movies by IMDB score")
    
    # Test Supabase connection first
    if not test_supabase_connection():
        logger.error("❌ SUPABASE CONNECTION FAILED or unavailable")
        logger.error("🛑 STOPPING SCRIPT EXECUTION - Cannot access movie database")
        logger.error("💡 Check your SUPABASE_URL and SUPABASE_KEY environment variables")
        return None  # Return None to indicate connection failure
    
    # Debug mode: Check database structure and available data
    if debug:
        logger.info("DEBUG MODE: Analyzing database structure and available data...")
        try:
            # Check available movies
            movies_sample = supabase.from_("movies").select("*").limit(3).execute()
            if hasattr(movies_sample, 'data') and movies_sample.data:
                logger.info(f"✅ Found {len(movies_sample.data)} sample movies in database")
            else:
                logger.warning("❌ No movies found in database!")
                
            # Check available localizations
            loc_sample = supabase.from_("movie_localizations").select("*").limit(3).execute()
            if hasattr(loc_sample, 'data') and loc_sample.data:
                logger.info(f"✅ Found {len(loc_sample.data)} localizations")
                
                # Show available filters
                countries = {loc.get('country_code') for loc in loc_sample.data if loc.get('country_code')}
                platforms = {loc.get('platform_name') for loc in loc_sample.data if loc.get('platform_name')}
                logger.info(f"Available countries: {countries}")
                logger.info(f"Available platforms: {platforms}")
            else:
                logger.warning("❌ No movie_localizations found!")
                
        except Exception as e:
            logger.error(f"Debug query failed: {str(e)}")
    
            # Main database query with exact filtering
    try:
        # Build the query with proper joins
        query = (supabase
                .from_("movies")
                .select("""
                    movie_id,
                    content_type,
                    imdb_score,
                    imdb_votes,
                    runtime,
                    release_year,
                    movie_localizations!inner(
                        title,
                        country_code,
                        platform_name,
                        poster_url,
                        cloudinary_poster_url,
                        trailer_url,
                        streaming_url
                    ),
                    movie_genres!inner(
                        genre
                    )
                """))
        
        # Apply exact filters - only if values are provided
        logger.info(f"🔍 BUILDING SUPABASE QUERY:")
        logger.info(f"   Base query: movies with joins to movie_localizations and movie_genres")
        
        filters_applied = []
        if content_type:
            query = query.eq("content_type", content_type)
            filters_applied.append(f"content_type={content_type}")
            logger.info(f"   ✅ Filter added: content_type = '{content_type}'")
        if country:
            query = query.eq("movie_localizations.country_code", country)
            filters_applied.append(f"country={country}")
            logger.info(f"   ✅ Filter added: movie_localizations.country_code = '{country}'")
        if platform:
            query = query.eq("movie_localizations.platform_name", platform)
            filters_applied.append(f"platform={platform}")
            logger.info(f"   ✅ Filter added: movie_localizations.platform_name = '{platform}'")
        if genre:
            query = query.eq("movie_genres.genre", genre)
            filters_applied.append(f"genre={genre}")
            logger.info(f"   ✅ Filter added: movie_genres.genre = '{genre}'")
            
        # Execute query with applied filters
        query = query.order("imdb_score", desc=True).limit(num_movies)
        logger.info(f"   📊 Order by: imdb_score DESC")
        logger.info(f"   📋 Limit: {num_movies} results")
        
        if filters_applied:
            logger.info(f"🚀 EXECUTING QUERY with filters: {', '.join(filters_applied)}")
        else:
            logger.info("🚀 EXECUTING QUERY with no filters - getting top movies globally by IMDB score")
        
        response = query.execute()
        logger.info(f"📊 QUERY RESULT: {len(response.data) if hasattr(response, 'data') and response.data else 0} movies returned")
        
        # Check if we got results from the database
        if not hasattr(response, 'data') or len(response.data) == 0:
            filter_summary = f"country={country}, genre={genre}, platform={platform}, content_type={content_type}"
            logger.error(f"❌ NO MOVIES FOUND in database matching criteria: {filter_summary}")
            logger.error("🛑 STOPPING SCRIPT EXECUTION - No content available for video generation")
            logger.error("💡 Try different filter criteria (country, genre, platform, or content-type)")
            return None  # Return None to indicate no real data found
        
        movies_raw = response.data
        logger.info(f"Successfully retrieved {len(movies_raw)} movies from database")
        
        # Process results into standardized format
        movie_data = []
        for movie in movies_raw:
            try:
                # Extract localization data
                localization = movie.get('movie_localizations', [])
                if isinstance(localization, list) and len(localization) > 0:
                    localization = localization[0]
                elif not isinstance(localization, dict):
                    logger.warning(f"No localization data for movie {movie.get('movie_id')}")
                    continue
                
                # Extract genre data
                genres_data = movie.get('movie_genres', [])
                if isinstance(genres_data, list):
                    genres = [g.get('genre') for g in genres_data if g.get('genre')]
                else:
                    genres = [genres_data.get('genre')] if genres_data.get('genre') else []
                
                # Format IMDB score
                imdb_score = movie.get('imdb_score', 0)
                imdb_votes = movie.get('imdb_votes', 0)
                imdb_formatted = f"{imdb_score}/10 ({imdb_votes} votes)" if imdb_votes > 0 else f"{imdb_score}/10"
                
                # Create standardized movie info
                movie_info = {
                    'id': movie.get('movie_id'),
                    'title': localization.get('title', 'Unknown Title'),
                    'year': movie.get('release_year', 'Unknown'),
                    'imdb': imdb_formatted,
                    'imdb_score': imdb_score,
                    'runtime': f"{movie.get('runtime', 0)} min",
                    'platform': localization.get('platform_name', platform or 'Unknown'),
                    'poster_url': localization.get('poster_url', ''),
                    'cloudinary_poster_url': localization.get('cloudinary_poster_url', ''),
                    'trailer_url': localization.get('trailer_url', ''),
                    'streaming_url': localization.get('streaming_url', ''),
                    'genres': genres,
                    'content_type': movie.get('content_type', content_type or 'Unknown')
                }
                
                movie_data.append(movie_info)
                logger.debug(f"Processed: {movie_info['title']} - IMDB: {movie_info['imdb']}")
                
            except Exception as e:
                logger.error(f"Error processing movie {movie.get('movie_id', 'unknown')}: {str(e)}")
                continue
        
        # Ensure proper sorting by IMDB score (highest first)
        movie_data.sort(key=lambda x: x.get('imdb_score', 0), reverse=True)
        
        if movie_data:
            logger.info(f"✅ Successfully extracted {len(movie_data)} movies")
            logger.info(f"Top movie: {movie_data[0]['title']} - IMDB: {movie_data[0]['imdb']}")
        else:
            logger.error("❌ NO MOVIES could be processed from database results")
            logger.error("🛑 STOPPING SCRIPT EXECUTION - Database returned data but could not be processed")
            logger.error("💡 Check database schema or try different filter criteria")
            return None  # Return None to indicate processing failure
            
        return movie_data
        
    except Exception as e:
        logger.error(f"❌ DATABASE QUERY FAILED: {str(e)}")
        logger.error("🛑 STOPPING SCRIPT EXECUTION - Cannot connect to database")
        logger.error("💡 Check your SUPABASE_URL and SUPABASE_KEY environment variables")
        return None  # Return None to indicate database failure

# Simulation logic for when database access fails or no matches found
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
    
    return movie_data

def enrich_movie_data(movie_data, country=None, genre=None, platform=None, content_type=None):
    """
    Enrich movie data with ChatGPT for more engaging descriptions - fully dynamic based on CLI arguments
    
    Args:
        movie_data: List of movie data dictionaries
        country (str): Country code for language and cultural context (from CLI args)
        genre (str): Genre for specialized prompts (from CLI args)
        platform (str): Platform for context-specific content (from CLI args)
        content_type (str): Film/Série for appropriate terminology (from CLI args)
        
    Returns:
        List of movie data dictionaries with enriched descriptions
    """
    # Create dynamic context based on CLI arguments
    language_map = {
        'FR': {'language': 'French', 'code': 'fr'},
        'US': {'language': 'English', 'code': 'en'},
        'UK': {'language': 'English', 'code': 'en'},
        'CA': {'language': 'English', 'code': 'en'},
        'DE': {'language': 'German', 'code': 'de'},
        'ES': {'language': 'Spanish', 'code': 'es'},
        'IT': {'language': 'Italian', 'code': 'it'},
    }
    
    # Determine language from country (default to English)
    lang_info = language_map.get(country or 'US', {'language': 'English', 'code': 'en'})
    is_french = lang_info['code'] == 'fr'
    
    # Dynamic genre context
    genre_contexts = {
        'Horreur': {'fr': 'film d\'horreur', 'en': 'horror movie', 'expert': 'horror'},
        'Horror': {'fr': 'film d\'horreur', 'en': 'horror movie', 'expert': 'horror'},
        'Action': {'fr': 'film d\'action', 'en': 'action movie', 'expert': 'action'},
        'Drama': {'fr': 'drame', 'en': 'drama', 'expert': 'drama'},
        'Drame': {'fr': 'drame', 'en': 'drama', 'expert': 'drama'},
        'Comedy': {'fr': 'comédie', 'en': 'comedy', 'expert': 'comedy'},
        'Comédie': {'fr': 'comédie', 'en': 'comedy', 'expert': 'comedy'},
        'Thriller': {'fr': 'thriller', 'en': 'thriller', 'expert': 'thriller'},
        'Sci-Fi': {'fr': 'film de science-fiction', 'en': 'sci-fi movie', 'expert': 'sci-fi'},
        'Romance': {'fr': 'film romantique', 'en': 'romance', 'expert': 'romance'},
    }
    
    # Dynamic content type terminology
    content_type_map = {
        'Film': {'fr': 'film', 'en': 'movie'},
        'Série': {'fr': 'série', 'en': 'series'},
        'Series': {'fr': 'série', 'en': 'series'},
    }
    
    # Get dynamic context
    genre_context = genre_contexts.get(genre or 'Horror', {'fr': 'contenu', 'en': 'content', 'expert': 'entertainment'})
    content_context = content_type_map.get(content_type or 'Film', {'fr': 'contenu', 'en': 'content'})
    
    # Comprehensive logging of arguments and context
    logger.info(f"🤖 ENRICH_MOVIE_DATA FUNCTION CALLED")
    logger.info(f"📋 CLI Arguments Received:")
    logger.info(f"   --country: {country}")
    logger.info(f"   --genre: {genre}")
    logger.info(f"   --platform: {platform}")
    logger.info(f"   --content-type: {content_type}")
    logger.info(f"🌍 Dynamic Context Built:")
    logger.info(f"   Language: {lang_info['language']} (code: {lang_info['code']})")
    logger.info(f"   Genre Context: {genre or 'General'} -> {genre_context.get(lang_info['code'], 'content')}")
    logger.info(f"   Platform Context: {platform or 'Any'}")
    logger.info(f"   Content Type Context: {content_type or 'Any'} -> {content_context.get(lang_info['code'], 'content')}")
    logger.info(f"🎬 Processing {len(movie_data)} movies for enrichment")
    
    for movie in movie_data:
        try:
            # Create dynamic system message based on genre and language
            if is_french:
                system_message = f"Tu es un expert en {genre_context['expert']} qui crée du contenu court et engageant pour les réseaux sociaux."
            else:
                system_message = f"You are a {genre_context['expert']} expert who creates short and engaging content for social media."
            
            # Create fully dynamic prompt based on all CLI arguments
            if is_french:
                platform_context = f" sur {platform}" if platform else ""
                prompt = f"""
                Génère une description courte et engageante pour le {genre_context['fr']} "{movie['title']}" pour une vidéo TikTok/YouTube{platform_context}.
                
                Informations:
                - Titre: {movie['title']}
                - Score IMDb: {movie['imdb']}
                - Année: {movie['year']}
                - Genres: {', '.join(movie.get('genres', ['Divers']))}
                - Type: {content_context['fr'].title()}
                {f"- Plateforme: {platform}" if platform else ""}
                
                Critères:
                1. 1-2 phrases maximum (TRÈS COURT)
                2. Ton décontracté qui accroche un public jeune
                3. Mentionne le score IMDb et l'année
                4. Ne révèle pas trop l'intrigue
                {f"5. Adapté pour {content_context['fr']}" if content_type else ""}
                
                Réponds UNIQUEMENT avec le texte enrichi, sans préambule.
                """
            else:
                platform_context = f" on {platform}" if platform else ""
                prompt = f"""
                Generate a short and engaging description for the {genre_context['en']} "{movie['title']}" for a TikTok/YouTube video{platform_context}.
                
                Information:
                - Title: {movie['title']}
                - IMDb Score: {movie['imdb']}
                - Year: {movie['year']}
                - Genres: {', '.join(movie.get('genres', ['Various']))}
                - Type: {content_context['en'].title()}
                {f"- Platform: {platform}" if platform else ""}
                
                Criteria:
                1. 1-2 sentences maximum (VERY SHORT)
                2. Casual tone that hooks young audiences
                3. Mention the IMDb score and year
                4. Don't spoil too much of the plot
                {f"5. Adapted for {content_context['en']}" if content_type else ""}
                
                Respond ONLY with the enriched text, no preamble.
                """
            
            # Log the OpenAI request details
            logger.info(f"🚀 CALLING OPENAI API for movie: {movie['title']}")
            logger.info(f"   Model: gpt-4o")
            logger.info(f"   Temperature: 0.7")
            logger.info(f"   Max tokens: 100")
            logger.info(f"📝 SYSTEM MESSAGE:")
            logger.info(f"   {system_message}")
            logger.info(f"📝 USER PROMPT (first 200 chars):")
            logger.info(f"   {prompt[:200]}...")
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
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
            
            # Dynamic fallback description based on CLI arguments
            genre_fallback = genre_context.get(lang_info['code'], 'content')
            content_fallback = content_context.get(lang_info['code'], 'content')
            
            if is_french:
                movie["enriched_description"] = f"Ce {content_fallback} de {movie['year']} avec un score IMDb de {movie['imdb']} vous captivera !"
            else:
                movie["enriched_description"] = f"This {content_fallback} from {movie['year']} with an IMDb score of {movie['imdb']} will captivate you!"
    
    return movie_data

def generate_script(enriched_movies, cloudinary_urls, country=None, genre=None, platform=None, content_type=None):
    """
    Generate scripts for REELS-TYPE videos (60-90 seconds total)
    
    REELS-OPTIMIZED RULES (based on 2.5 words/second speaking pace):
    - Intro+movie1: 35-40 seconds (85-100 words) - Quick intro + first movie
    - Movie2: 15-25 seconds (40-60 words) - Brief second movie mention  
    - Movie3: 15-25 seconds (40-60 words) - Brief third movie mention
    - TOTAL: 65-90 seconds (165-220 words) - Perfect for reels!
    
    Args:
        enriched_movies: List of movie data dictionaries
        cloudinary_urls: URLs for images
        country (str): Country code for language context (from CLI args)
        genre (str): Genre for specialized terminology (from CLI args)
        platform (str): Platform for specific context (from CLI args)
        content_type (str): Film/Série for appropriate terminology (from CLI args)
    """
    # Create dynamic context based on CLI arguments
    language_map = {
        'FR': {'language': 'French', 'code': 'fr'},
        'US': {'language': 'English', 'code': 'en'},
        'UK': {'language': 'English', 'code': 'en'},
        'CA': {'language': 'English', 'code': 'en'},
        'DE': {'language': 'German', 'code': 'de'},
        'ES': {'language': 'Spanish', 'code': 'es'},
        'IT': {'language': 'Italian', 'code': 'it'},
    }
    
    # Dynamic genre contexts for script generation
    genre_contexts = {
        'Horreur': {'fr': {'fans': 'fans d\'horreur', 'content': 'films d\'horreur', 'roundup': 'sélection horreur hebdomadaire', 'cinema': 'cinéma d\'horreur de qualité'}, 
                   'en': {'fans': 'horror fans', 'content': 'horror films', 'roundup': 'weekly horror roundup', 'cinema': 'quality horror cinema'}},
        'Horror': {'fr': {'fans': 'fans d\'horreur', 'content': 'films d\'horreur', 'roundup': 'sélection horreur hebdomadaire', 'cinema': 'cinéma d\'horreur de qualité'},
                  'en': {'fans': 'horror fans', 'content': 'horror films', 'roundup': 'weekly horror roundup', 'cinema': 'quality horror cinema'}},
        'Action': {'fr': {'fans': 'fans d\'action', 'content': 'films d\'action', 'roundup': 'sélection action hebdomadaire', 'cinema': 'cinéma d\'action de qualité'},
                  'en': {'fans': 'action fans', 'content': 'action movies', 'roundup': 'weekly action roundup', 'cinema': 'quality action cinema'}},
        'Drama': {'fr': {'fans': 'amateurs de drames', 'content': 'drames', 'roundup': 'sélection drame hebdomadaire', 'cinema': 'cinéma dramatique de qualité'},
                 'en': {'fans': 'drama lovers', 'content': 'drama films', 'roundup': 'weekly drama roundup', 'cinema': 'quality drama cinema'}},
        'Comedy': {'fr': {'fans': 'fans de comédie', 'content': 'comédies', 'roundup': 'sélection comédie hebdomadaire', 'cinema': 'comédie de qualité'},
                  'en': {'fans': 'comedy fans', 'content': 'comedies', 'roundup': 'weekly comedy roundup', 'cinema': 'quality comedy cinema'}},
        'Thriller': {'fr': {'fans': 'fans de thriller', 'content': 'thrillers', 'roundup': 'sélection thriller hebdomadaire', 'cinema': 'thriller de qualité'},
                    'en': {'fans': 'thriller fans', 'content': 'thrillers', 'roundup': 'weekly thriller roundup', 'cinema': 'quality thriller cinema'}},
    }
    
    # Dynamic content type terminology
    content_type_map = {
        'Film': {'fr': {'single': 'film', 'plural': 'films', 'experience': 'expérience cinématographique'}, 
                'en': {'single': 'movie', 'plural': 'movies', 'experience': 'cinematic experience'}},
        'Série': {'fr': {'single': 'série', 'plural': 'séries', 'experience': 'expérience télévisuelle'}, 
                 'en': {'single': 'series', 'plural': 'series', 'experience': 'viewing experience'}},
    }
    
    # Get dynamic context
    lang_info = language_map.get(country or 'US', {'language': 'English', 'code': 'en'})
    is_french = lang_info['code'] == 'fr'
    
    # Default to Horror if no genre specified
    genre_context = genre_contexts.get(genre or 'Horror', {
        'fr': {'fans': 'cinéphiles', 'content': 'contenus', 'roundup': 'sélection hebdomadaire', 'cinema': 'cinéma de qualité'},
        'en': {'fans': 'movie fans', 'content': 'films', 'roundup': 'weekly roundup', 'cinema': 'quality cinema'}
    })
    
    content_context = content_type_map.get(content_type or 'Film', {
        'fr': {'single': 'contenu', 'plural': 'contenus', 'experience': 'expérience'},
        'en': {'single': 'content', 'plural': 'content', 'experience': 'experience'}
    })
    
    # Comprehensive logging of arguments and context
    logger.info(f"📝 GENERATE_SCRIPT FUNCTION CALLED")
    logger.info(f"📋 CLI Arguments Received:")
    logger.info(f"   --country: {country}")
    logger.info(f"   --genre: {genre}")
    logger.info(f"   --platform: {platform}")
    logger.info(f"   --content-type: {content_type}")
    logger.info(f"🌍 Dynamic Context Built:")
    logger.info(f"   Language: {lang_info['language']} (code: {lang_info['code']})")
    logger.info(f"   Genre Context: {genre or 'General'}")
    logger.info(f"   Platform Context: {platform or 'Any'}")
    logger.info(f"   Content Type Context: {content_type or 'Any'}")
    logger.info(f"🎬 Processing {len(enriched_movies)} movies for script generation")
    
    # Helper function to get full description from movie data with dynamic fallback
    def _get_full_description(movie):
        """Extract 2-3 sentence description from enriched or short description with dynamic fallback"""
        if movie.get('enriched_description'):
            # Use first 2-3 sentences from enriched description
            desc = movie['enriched_description']
            # Split by sentence endings (.!?) followed by a space and take first 2-3
            sentences = re.split(r'[.!?] ', desc)
            if len(sentences) > 3:
                return '. '.join(sentences[:3]) + '.' 
            return desc
        elif movie.get('short_description'):
            return movie['short_description']
        else:
            # Dynamic fallback based on CLI arguments
            if is_french:
                return f"Ce {content_context['fr']['single']} captivant vous tiendra en haleine avec son intrigue suspensieuse et son atmosphère envoûtante."
            else:
                return f"This captivating {content_context['en']['single']} will keep you on the edge of your seat with its suspenseful storyline and atmospheric tension."
    
    # Helper function to format vote counts in a readable way
    def format_votes(vote_count):
        if not vote_count or vote_count == 0:
            return ""
        if vote_count < 1000:
            return f"with {vote_count} votes"
        if vote_count < 10000:
            return f"with thousands of viewers rating it"
        if vote_count < 100000:
            return f"with tens of thousands of ratings"
        return f"with over {vote_count:,} votes"
    
    # Determine genre properly
    def get_primary_genre(movie):
        genres = movie.get('genres', [])
        if not genres:
            return "horror"
            
        # Convert French genre names to English equivalents if needed
        genre_map = {"Horreur": "horror", "Fantastique": "fantasy", "Science-Fiction": "sci-fi"}
        
        # Try to find horror first
        for genre in genres:
            if genre.lower() == "horror" or genre == "Horreur":
                return "horror"
                
        # Otherwise use first genre and translate if needed
        primary = genres[0]
        return genre_map.get(primary, primary.lower())
    
    # Generate dynamic scripts using OpenAI with precise word counts for exact target durations
    # Get dynamic text elements based on CLI arguments
    lang_code = lang_info['code']
    genre_text = genre_context.get(lang_code, genre_context['en'])
    content_text = content_context.get(lang_code, content_context['en'])
    
    # Dynamic platform context
    platform_context = f" {platform}" if platform else ""
    
    # Generate scripts using OpenAI with strict timing rules
    scripts_data = []
    
    # REELS-OPTIMIZED Script rules for 60-90 second videos
    script_rules = [
        {
            "name": "intro_movie1",
            "duration": "35-40 seconds", 
            "word_count": "85-100 words",
            "movie_index": 0,
            "type": "quick introduction + first movie highlight"
        },
        {
            "name": "movie2", 
            "duration": "15-25 seconds",
            "word_count": "40-60 words", 
            "movie_index": 1,
            "type": "brief second movie mention"
        },
        {
            "name": "movie3",
            "duration": "15-25 seconds", 
            "word_count": "40-60 words",
            "movie_index": 2, 
            "type": "brief third movie mention"
        }
    ]
    
    # Log the reels timing rules being applied
    logger.info(f"⏱️  REELS TIMING RULES APPLIED:")
    for rule in script_rules:
        logger.info(f"   {rule['name']}: {rule['duration']} ({rule['word_count']}) - {rule['type']}")
    total_min_words = sum([int(rule['word_count'].split('-')[0]) for rule in script_rules])
    total_max_words = sum([int(rule['word_count'].split('-')[1].split(' ')[0]) for rule in script_rules])
    estimated_duration_min = total_min_words / 2.5
    estimated_duration_max = total_max_words / 2.5
    logger.info(f"   🎯 TOTAL TARGET: {total_min_words}-{total_max_words} words = {estimated_duration_min:.0f}-{estimated_duration_max:.0f} seconds")
    
    generated_scripts = {}
    
    for rule in script_rules:
        movie = enriched_movies[rule["movie_index"]]
        
        try:
            # Create dynamic system message based on genre and language
            if is_french:
                system_message = f"Tu es un expert en {genre_context.get('expert', 'divertissement')} qui crée des scripts engageants pour des vidéos TikTok/YouTube. Tu respectes PRÉCISÉMENT les contraintes de timing et de nombre de mots."
            else:
                system_message = f"You are a {genre_context.get('expert', 'entertainment')} expert who creates engaging scripts for TikTok/YouTube videos. You follow timing and word count constraints PRECISELY."
                
            # Create dynamic prompt based on all CLI arguments and timing rules
            if is_french:
                if rule["name"] == "intro_movie1":
                    prompt = f"""
                    Crée un script TRÈS COURT pour un REEL de 60-90 secondes{platform_context}.
                    
                    CONTRAINTES CRITIQUES - REELS:
                    - Durée: {rule['duration']} (MAXIMUM {rule['word_count']} - PAS UN MOT DE PLUS!)
                    - Format: REEL court, punchy, accrocher immédiatement
                    - Rythme: Rapide, énergique, pas de temps mort
                    
                    CONTENU {content_text['single'].upper()}:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    STRUCTURE ULTRA-COURTE:
                    1. Accroche rapide (5-10 mots)
                    2. {movie['title']} + score + 1 phrase d'impact
                    3. Teaser rapide des 2 autres
                    
                    STYLE: Dynamique, percutant, TikTok/Instagram Reels.
                    RAPPEL: {rule['word_count']} MAXIMUM - Chaque mot compte!
                    
                    Réponds UNIQUEMENT avec le script final.
                    """
                else:
                    prompt = f"""
                    Crée un script ULTRA-COURT pour un REEL rapide{platform_context}.
                    
                    CONTRAINTES EXTRÊMES - REELS:
                    - Durée: {rule['duration']} (MAXIMUM {rule['word_count']} - AUCUN MOT EN PLUS!)
                    - Format: Mention rapide, efficace, percutante
                    
                    CONTENU:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    STRUCTURE MINIMAL:
                    1. Transition (1-2 mots: "Ensuite" ou "Enfin")
                    2. Titre + score + 1 mot-clé d'impact
                    3. Pas de détails - juste l'essentiel!
                    
                    STYLE: Rapide, direct, TikTok/Reels.
                    IMPÉRATIF: {rule['word_count']} MAXIMUM!
                    
                    Réponds UNIQUEMENT avec le script final.
                    """
            else:
                if rule["name"] == "intro_movie1":
                    prompt = f"""
                    Create a SUPER SHORT script for a 60-90 second REEL{platform_context}.
                    
                    CRITICAL CONSTRAINTS - REELS:
                    - Duration: {rule['duration']} (MAXIMUM {rule['word_count']} - NOT ONE WORD MORE!)
                    - Format: Short reel, punchy, hook immediately
                    - Pace: Fast, energetic, no dead time
                    
                    CONTENT:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    ULTRA-SHORT STRUCTURE:
                    1. Quick hook (5-10 words)
                    2. {movie['title']} + score + 1 impact phrase
                    3. Quick tease of 2 others
                    
                    STYLE: Dynamic, punchy, TikTok/Instagram Reels.
                    REMINDER: {rule['word_count']} MAXIMUM - Every word counts!
                    
                    Respond ONLY with the final script.
                    """
                else:
                    prompt = f"""
                    Create an ULTRA-SHORT script for a fast REEL{platform_context}.
                    
                    EXTREME CONSTRAINTS - REELS:
                    - Duration: {rule['duration']} (MAXIMUM {rule['word_count']} - NO EXTRA WORDS!)
                    - Format: Quick mention, efficient, punchy
                    
                    CONTENT:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    MINIMAL STRUCTURE:
                    1. Transition (1-2 words: "Next" or "Finally")
                    2. Title + score + 1 impact keyword
                    3. No details - just essentials!
                    
                    STYLE: Fast, direct, TikTok/Reels.
                    IMPERATIVE: {rule['word_count']} MAXIMUM!
                    
                    Respond ONLY with the final script.
                    """
            
            # Log the OpenAI request details for script generation
            max_tokens = 180 if rule["name"] == "intro_movie1" else 100
            logger.info(f"🚀 CALLING OPENAI API for script: {rule['name']}")
            logger.info(f"   Movie: {movie['title']} ({movie['year']})")
            logger.info(f"   Target: {rule['duration']} ({rule['word_count']})")
            logger.info(f"   Model: gpt-4o")
            logger.info(f"   Temperature: 0.7")
            logger.info(f"   Max tokens: {max_tokens}")
            logger.info(f"📝 SYSTEM MESSAGE:")
            logger.info(f"   {system_message}")
            logger.info(f"📝 USER PROMPT (first 200 chars):")
            logger.info(f"   {prompt[:200]}...")
            
            # Generate script with OpenAI (REELS-optimized token limits)
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=max_tokens  # Reels-optimized but sufficient for target word counts
            )
            
            generated_script = response.choices[0].message.content.strip()
            generated_scripts[rule["name"]] = generated_script
            
            logger.info(f"✅ Generated {rule['name']} script ({rule['duration']}, target: {rule['word_count']})")
            logger.info(f"   Actual word count: {len(generated_script.split())} words")
            
        except Exception as e:
            logger.error(f"❌ Error generating {rule['name']} script: {str(e)}")
            
            # Dynamic fallback based on CLI arguments
            if is_french:
                fallback_script = f"""Salut {genre_text['fans']} ! Découvrez {movie['title']} de {movie['year']}, un {content_text['single']} exceptionnel avec un score de {movie.get('imdb', '7+')} sur IMDb. {_get_full_description(movie)} C'est un incontournable pour tous les amateurs de {genre_text['cinema']}."""
            else:
                fallback_script = f"""Hello {genre_text['fans']}! Discover {movie['title']} from {movie['year']}, an exceptional {content_text['single']} with {movie.get('imdb', '7+')} on IMDb. {_get_full_description(movie)} This is a must-watch for all {genre_text['cinema']} enthusiasts."""
            
            generated_scripts[rule["name"]] = fallback_script
    
    # Use the generated scripts
    script_intro_movie1 = generated_scripts.get("intro_movie1", "Script generation failed.")
    script_movie2 = generated_scripts.get("movie2", "Script generation failed.")  
    script_movie3 = generated_scripts.get("movie3", "Script generation failed.")

    
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
        with open(script_data["path"], "w", encoding='utf-8') as f:
            f.write(script_data["text"])
    
    logger.info(f"✅ Dynamic OpenAI-generated scripts created with precise timing rules and saved to videos directory")
    
    # Return combined script for compatibility with existing functions
    combined_script = script_intro_movie1 + "\n\n" + script_movie2 + "\n\n" + script_movie3
    combined_path = "videos/combined_script.txt"
    with open(combined_path, "w", encoding='utf-8') as f:
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

def check_heygen_video_status(video_id: str, silent: bool = False) -> dict:
    """
    Check the processing status of a HeyGen video using the official status API
    
    Args:
        video_id: HeyGen video ID
        silent: If True, reduce logging verbosity (for polling loops)
        
    Returns:
        Dictionary with status information: {'status': str, 'video_url': str, 'data': dict}
    """
    if not silent:
        logger.debug(f"Checking status of HeyGen video {video_id[:8]}...")
    
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        logger.error("HEYGEN_API_KEY not found in environment variables")
        return {"status": "unknown", "video_url": "", "data": {}}
    
    # Use the specific endpoint suggested by the user
    status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }
    
    try:
        response = requests.get(status_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Only log full response in debug mode or when not silent
            if not silent:
                logger.debug(f"HeyGen API response: {json.dumps(data, indent=2)}")
            
            # Extract status and video URL from response
            if 'data' in data:
                video_data = data['data']
                status = video_data.get('status', 'unknown')
                video_url = video_data.get('video_url', '') or video_data.get('url', '')
                
                # Reduced logging during polling
                if not silent:
                    logger.debug(f"HeyGen video {video_id[:8]}... status: {status}")
                
                return {
                    "status": status,
                    "video_url": video_url,
                    "data": video_data
                }
            else:
                if not silent:
                    logger.warning(f"No 'data' field in response: {data}")
                return {"status": "unknown", "video_url": "", "data": data}
                
        else:
            if not silent:
                logger.error(f"HeyGen API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
            
            # Try fallback endpoints
            return _try_fallback_status_endpoints(video_id, headers, silent)
            
    except Exception as e:
        if not silent:
            logger.error(f"Exception calling HeyGen status API: {str(e)}")
        # Try fallback endpoints
        return _try_fallback_status_endpoints(video_id, headers, silent)

def _try_fallback_status_endpoints(video_id: str, headers: dict, silent: bool = False) -> dict:
    """
    Try fallback endpoints if the primary status endpoint fails
    
    Args:
        video_id: HeyGen video ID
        headers: Request headers with API key
        silent: If True, reduce logging verbosity (for polling loops)
        
    Returns:
        Dictionary with status information
    """
    if not silent:
        logger.debug("Trying fallback status endpoints...")
    
    # Fallback endpoints to try
    fallback_endpoints = [
        f"https://api.heygen.com/v1/video.status?video_id={video_id}",
        f"https://api.heygen.com/v1/video_status?video_id={video_id}",
        f"https://api.heygen.com/v2/video/{video_id}/status"
    ]
    
    for endpoint in fallback_endpoints:
        try:
            if not silent:
                logger.debug(f"Trying fallback endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if not silent:
                    logger.debug(f"Fallback endpoint success: {endpoint}")
                
                if 'data' in data:
                    video_data = data['data']
                    status = video_data.get('status', 'unknown')
                    video_url = video_data.get('video_url', '') or video_data.get('url', '')
                    
                    return {
                        "status": status,
                        "video_url": video_url,
                        "data": video_data
                    }
                    
        except Exception as e:
            if not silent:
                logger.debug(f"Fallback endpoint {endpoint} failed: {str(e)}")
            continue
    
    # All fallback endpoints failed
    if not silent:
        logger.warning(f"All fallback status endpoints failed for video {video_id[:8]}...")
    
    return {"status": "unknown", "video_url": "", "data": {}}

def wait_for_heygen_video(video_id: str, script_length: int = None, max_wait_minutes: int = 15) -> dict:
    """
    Intelligently wait for a HeyGen video with dynamic timeout and progress estimation
    
    Args:
        video_id: HeyGen video ID
        script_length: Length of the script in characters (for time estimation)
        max_wait_minutes: Maximum total wait time in minutes (default: 15)
        
    Returns:
        Dictionary with status info: {'success': bool, 'status': str, 'video_url': str, 'data': dict}
    """
    # Spinner animation frames
    spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    # Estimate processing time based on script complexity
    estimated_minutes = estimate_heygen_processing_time(script_length)
    
    # Dynamic timeout: use estimated time + buffer, but respect max limit
    timeout_minutes = min(max(estimated_minutes + 5, 8), max_wait_minutes)  # At least 8 min, up to max
    max_total_seconds = timeout_minutes * 60
    
    # Progressive intervals: start fast, then slow down
    def get_interval(attempt_num: int, elapsed_seconds: int) -> int:
        """Get dynamic interval based on attempt number and elapsed time"""
        if elapsed_seconds < 120:  # First 2 minutes: check every 10 seconds
            return 10
        elif elapsed_seconds < 300:  # Next 3 minutes: check every 15 seconds  
            return 15
        elif elapsed_seconds < 600:  # Next 5 minutes: check every 20 seconds
            return 20
        else:  # After 10 minutes: check every 30 seconds
            return 30
    
    # Start message with estimation
    logger.info(f"⏳ Waiting for HeyGen video {video_id[:8]}... (estimated: ~{estimated_minutes} min)")
    
    start_time = time.time()
    attempt = 0
    next_check_time = start_time
    
    while True:
        current_time = time.time()
        elapsed_seconds = current_time - start_time
        
        # Check if we've exceeded total timeout
        if elapsed_seconds > max_total_seconds:
            elapsed_time = int(elapsed_seconds)
            minutes, seconds = divmod(elapsed_time, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            print(f"\r⏰ HeyGen video timeout    [{'░' * 30}] ----  │ {time_str} │ Max time reached{' ' * 10}")
            logger.warning(f"HeyGen video {video_id[:8]}... exceeded max wait time of {timeout_minutes} minutes")
            
            return {
                'success': False,
                'status': 'timeout',
                'video_url': '',
                'data': {}
            }
        
        # Only check status at scheduled intervals
        if current_time >= next_check_time:
            attempt += 1
            
            # Calculate progress based on time vs estimated completion
            time_progress = min(elapsed_seconds / (estimated_minutes * 60) * 100, 95)
            attempt_progress = min(elapsed_seconds / max_total_seconds * 100, 95)
            progress = max(time_progress, attempt_progress)  # Use whichever is higher
            
            elapsed_time = int(elapsed_seconds)
            minutes, seconds = divmod(elapsed_time, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # Estimate remaining time
            remaining_seconds = max(0, (estimated_minutes * 60) - elapsed_seconds)
            if remaining_seconds > 0 and progress < 90:
                remaining_minutes, remaining_secs = divmod(int(remaining_seconds), 60)
                eta_str = f"ETA ~{remaining_minutes:02d}:{remaining_secs:02d}"
            else:
                eta_str = "Almost ready..."
            
            # Spinner animation
            spinner = spinner_frames[attempt % len(spinner_frames)]
            
            # Progress bar
            bar_length = 30
            filled_length = int(bar_length * progress / 100)
            bar = f"[{'█' * filled_length}{'░' * (bar_length - filled_length)}]"
            
            # Enhanced progress display with ETA
            progress_line = f"\r{spinner} Processing HeyGen video {bar} {progress:5.1f}% │ {time_str} │ {eta_str}"
            print(progress_line, end='', flush=True)
            
            # Get status (with reduced logging)
            status_info = check_heygen_video_status(video_id, silent=True)
            status = status_info.get('status', 'unknown')
            video_url = status_info.get('video_url', '')
            
            if status == "completed":
                # Clear progress line and show success
                print(f"\r✅ HeyGen video completed! [{'█' * bar_length}] 100.0% │ {time_str} │ Ready!{' ' * 15}")
                if video_url:
                    logger.info(f"🎬 Video completed in {minutes}:{seconds:02d} (estimated {estimated_minutes} min)")
                else:
                    logger.info("🎬 Video completed successfully")
                
                return {
                    'success': True,
                    'status': status,
                    'video_url': video_url,
                    'data': status_info.get('data', {})
                }
                
            elif status in ["failed", "error"]:
                # Clear progress line and show error
                print(f"\r❌ HeyGen video failed!   [{'X' * bar_length}] ERROR │ {time_str} │ Processing failed{' ' * 10}")
                logger.error(f"HeyGen video {video_id[:8]}... processing failed after {minutes}:{seconds:02d}")
                
                return {
                    'success': False,
                    'status': status,
                    'video_url': video_url,
                    'data': status_info.get('data', {})
                }
            
            # Set next check time with progressive interval
            current_interval = get_interval(attempt, elapsed_seconds)
            next_check_time = current_time + current_interval
            
            # Reduce logging frequency (every 6th attempt or every 3 minutes)
            if attempt % 6 == 0 or elapsed_seconds % 180 < current_interval:
                logger.debug(f"Video {video_id[:8]}... still processing ({minutes}:{seconds:02d} elapsed, checking every {current_interval}s)")
        
        # Sleep briefly to avoid busy waiting
        time.sleep(1)

def estimate_heygen_processing_time(script_length: int = None) -> int:
    """
    Estimate HeyGen video processing time based on script complexity
    
    Args:
        script_length: Length of script in characters
        
    Returns:
        Estimated processing time in minutes
    """
    # Base processing time
    base_minutes = 3
    
    if script_length is None:
        # Default estimate for unknown length
        return 6
    
    # Estimate based on script length
    # Roughly 1 additional minute per 200 characters of script
    additional_minutes = script_length // 200
    
    # HeyGen typical processing patterns:
    # - Short scripts (< 300 chars): 3-5 minutes
    # - Medium scripts (300-800 chars): 5-8 minutes  
    # - Long scripts (> 800 chars): 8-12 minutes
    
    if script_length <= 300:
        estimated = base_minutes + 1  # 4 minutes
    elif script_length <= 800:
        estimated = base_minutes + 3  # 6 minutes
    else:
        estimated = base_minutes + min(additional_minutes, 9)  # Cap at 12 minutes
    
    return estimated

def get_heygen_videos_for_creatomate(heygen_video_ids: dict, scripts: dict = None) -> dict:
    """
    Get HeyGen video URLs using the status API for direct use with Creatomate
    
    Args:
        heygen_video_ids: Dictionary of HeyGen video IDs {'intro_movie1': 'id1', 'movie2': 'id2', etc.}
        scripts: Dictionary of script data for time estimation (optional)
        
    Returns:
        Dictionary with video URLs ready for Creatomate: {'intro_movie1': 'url1', 'movie2': 'url2', etc.}
    """
    logger.info(f"Getting HeyGen video URLs for {len(heygen_video_ids)} videos...")
    
    video_urls = {}
    fallback_url = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    
    for key, video_id in heygen_video_ids.items():
        if not video_id or video_id.startswith('placeholder'):
            logger.debug(f"Skipping placeholder ID for {key}")
            continue
            
        # Extract script length for intelligent estimation
        script_length = None
        if scripts and key in scripts:
            script_data = scripts[key]
            if isinstance(script_data, dict) and 'text' in script_data:
                script_text = script_data['text']
            elif isinstance(script_data, str):
                script_text = script_data
            else:
                script_text = str(script_data)
            script_length = len(script_text) if script_text else None
            
        logger.info(f"Processing {key}: {video_id} ({script_length or 'unknown'} chars)")
        
        # Wait intelligently based on script complexity
        status_result = wait_for_heygen_video(
            video_id, 
            script_length=script_length,
            max_wait_minutes=25  # Increased for complex videos
        )
        
        if status_result['success'] and status_result['video_url']:
            video_url = status_result['video_url']
            video_urls[key] = video_url
            logger.info(f"✅ Got URL for {key}")
                
        else:
            # Use fallback or incomplete URL
            if status_result.get('video_url'):
                video_urls[key] = status_result['video_url']
                logger.warning(f"⚠️ Using incomplete URL for {key}")
            else:
                video_urls[key] = fallback_url
                logger.warning(f"⚠️ Using fallback URL for {key}")
    
    logger.info(f"✅ Obtained {len(video_urls)} video URLs")
    return video_urls

def create_creatomate_video_from_heygen_urls(
    heygen_video_urls: dict,
    movie_data: List[Dict[str, Any]] = None
) -> str:
    """
    Create a Creatomate video using HeyGen video URLs directly from the status API
    
    Args:
        heygen_video_urls: Dictionary with HeyGen video URLs {'intro_movie1': 'url1', 'movie2': 'url2', etc.}
        movie_data: List of movie data dictionaries (optional, uses defaults if not provided)
        
    Returns:
        str: Creatomate video ID or error message
    """
    logger.info("Creating Creatomate video using direct HeyGen URLs...")
    
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        logger.error("CREATOMATE_API_KEY is not set in environment variables")
        return f"error_no_api_key_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # === DYNAMIC MOVIE ASSETS BASED ON MOVIE_DATA ===
    if movie_data and len(movie_data) >= 3:
        logger.info("🎬 Using DYNAMIC movie assets from movie_data")
        
        # Use dynamic movie covers from movie_data
        movie_covers = []
        for i, movie in enumerate(movie_data[:3]):
            cover_url = movie.get('cloudinary_poster_url') or movie.get('poster_url')
            if cover_url:
                movie_covers.append(cover_url)
                logger.info(f"   Movie {i+1} cover: {movie['title']} -> {cover_url}")
            else:
                # Fallback to default if no cover available
                fallback_covers = [
                    "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
                    "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
                    "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png"
                ]
                movie_covers.append(fallback_covers[i])
                logger.warning(f"   Movie {i+1} cover: Using fallback for {movie['title']}")
        
        # === DYNAMIC MOVIE CLIPS FROM TRAILERS ===
        logger.info("🎞️ Processing dynamic movie clips from trailers...")
        logger.info("📱 Using YouTube Shorts PREMIUM quality: 1080x1920 with 3000k bitrate")
        dynamic_clips = process_movie_trailers_to_clips(movie_data, max_movies=3, transform_mode="youtube_shorts")
        
        # Create movie_clips array from dynamic processing
        movie_clips = []
        fallback_clips = [
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
        ]
        
        for i, movie in enumerate(movie_data[:3]):
            movie_title = movie.get('title', f'Movie_{i+1}')
            
            if movie_title in dynamic_clips:
                # Use dynamically generated clip
                movie_clips.append(dynamic_clips[movie_title])
                logger.info(f"   Movie {i+1} clip: {movie_title} -> DYNAMIC CLIP")
            else:
                # Use fallback clip
                movie_clips.append(fallback_clips[i])
                logger.warning(f"   Movie {i+1} clip: {movie_title} -> FALLBACK CLIP")
        
        logger.info(f"✅ Dynamic assets prepared: {len(movie_covers)} covers, {len(movie_clips)} clips")
        
    else:
        # === FALLBACK TO DEFAULT ASSETS ===
        logger.warning("⚠️ Using DEFAULT movie assets (no movie_data provided)")
        movie_covers = [
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png"
        ]
        
        movie_clips = [
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
        ]
    
    # Get HeyGen video URLs with fallbacks
    heygen_intro = heygen_video_urls.get(
        "intro_movie1", 
        "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    )
    heygen_movie2 = heygen_video_urls.get(
        "movie2", 
        "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    )
    heygen_movie3 = heygen_video_urls.get(
        "movie3", 
        "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    )
    
    logger.debug(f"HeyGen URLs: {len([url for url in [heygen_intro, heygen_movie2, heygen_movie3] if url])} videos")
    
    # Create sequential timeline (YouTube Shorts format)
    source = {
        "width": 1080,
        "height": 1920,
        "elements": [
             {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1753263646/streamGank_intro_cwefmt.jpg",
                "duration": 1
            },
             # StreamGank banner at top of videos (starts after intro image)
            {
                "id": "streamgank-banner",
                "name": "streamgank_logo",
                "type": "image",
                "y": "6.25%",
                "height": "12.5%",
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1752587056/streamgankbanner_uempzb.jpg",
                "time_offset": 1,  # Start after the 1-second intro image
                "duration": "99%"  # Maintain banner for the rest of the video
            },
            # HeyGen intro video + movie1
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_intro
            },
            # Movie 1 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": movie_covers[0],
                "duration": 3
            },
            # Movie 1 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": movie_clips[0],
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie2 video
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_movie2
            },
            # Movie 2 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": movie_covers[1],
                "duration": 3
            },
            # Movie 2 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": movie_clips[1],
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie3 video
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_movie3
            },
            # Movie 3 cover
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": movie_covers[2],
                "duration": 3
            },
            # Movie 3 clip
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": movie_clips[2],
                "trim_end": 8,
                "trim_start": 0
            },
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1752587571/streamgank_bg_heecu7.png",
                "duration": 2
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
        response = requests.post(
            "https://api.creatomate.com/v1/renders",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code in [200, 201, 202]:
            result = response.json()
            logger.info(f"Creatomate API success (HTTP {response.status_code})")
            
            if isinstance(result, list) and len(result) > 0:
                creatomate_data = result[0]
                creatomate_id = creatomate_data.get("id", "")
                status = creatomate_data.get("status", "unknown")
                logger.info(f"Render {creatomate_id[:8]}... status: {status}")
                    
            elif isinstance(result, dict):
                creatomate_id = result.get("id", "")
                status = result.get("status", "unknown")
                logger.info(f"Render {creatomate_id[:8]}... status: {status}")
            else:
                creatomate_id = f"unknown_format_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            return creatomate_id
            
        else:
            logger.error(f"Creatomate API error: {response.status_code} - {response.text}")
            return f"error_{response.status_code}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
    except Exception as e:
        logger.error(f"❌ Exception when calling Creatomate API: {str(e)}")
        return f"exception_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

def check_creatomate_render_status(render_id: str) -> dict:
    """
    Check the status of a Creatomate render
    
    Args:
        render_id: Creatomate render ID
        
    Returns:
        Dictionary with render status information
    """
    logger.info(f"Checking Creatomate render status for ID: {render_id}")
    
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        logger.error("CREATOMATE_API_KEY is not set in environment variables")
        return {"status": "error", "message": "No API key"}
    
    try:
        response = requests.get(
            f"https://api.creatomate.com/v1/renders/{render_id}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get("status", "unknown")
            url = result.get("url", "")
            
            logger.info(f"Creatomate render {render_id} status: {status}")
            if url and status == "completed":
                logger.info(f"Video ready at: {url}")
                
            return {
                "status": status,
                "url": url,
                "data": result
            }
        else:
            logger.error(f"Failed to check render status: {response.status_code} - {response.text}")
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Exception checking render status: {str(e)}")
        return {"status": "error", "message": str(e)}

def wait_for_creatomate_completion(render_id: str, max_attempts: int = 30, interval: int = 10) -> dict:
    """
    Wait for a Creatomate render to complete with progress feedback
    
    Args:
        render_id: Creatomate render ID
        max_attempts: Maximum polling attempts
        interval: Seconds between status checks
        
    Returns:
        Final status dictionary
    """
    logger.info(f"Waiting for Creatomate render {render_id} to complete...")
    
    print(f"\n{'=' * 70}")
    print(f"RENDERING: Creatomate video {render_id}")
    print(f"{'=' * 70}")
    
    for attempt in range(1, max_attempts + 1):
        # Progress bar
        progress = min(attempt / max_attempts * 100, 99)
        bar_length = 40
        filled_length = int(bar_length * progress / 100)
        progress_bar = f"[{'█' * filled_length}{' ' * (bar_length - filled_length)}] {progress:.1f}%"
        print(f"\rRendering: {progress_bar}", end="")
        sys.stdout.flush()
        
        # Check status
        status_info = check_creatomate_render_status(render_id)
        status = status_info.get("status", "unknown")
        
        if status == "completed":
            print(f"\r\n{'=' * 70}")
            print(f"SUCCESS: Creatomate video completed! [{'█' * bar_length}] 100%")
            print(f"Video URL: {status_info.get('url', 'No URL provided')}")
            print(f"{'=' * 70}\n")
            return status_info
            
        elif status in ["failed", "error"]:
            print(f"\r\n{'=' * 70}")
            print(f"FAILED: Creatomate render failed! [{'X' * bar_length}]")
            print(f"{'=' * 70}\n")
            return status_info
            
        # Wait before next check
        time.sleep(interval)
    
    print(f"\r\n{'=' * 70}")
    print(f"TIMEOUT: Render timed out after {max_attempts} attempts")
    print(f"{'=' * 70}\n")
    
    # Return last status
    return check_creatomate_render_status(render_id)

def process_existing_heygen_videos(heygen_video_ids: dict, output_file: str = None) -> dict:
    """
    Process existing HeyGen video IDs using the status API and create Creatomate video
    
    Args:
        heygen_video_ids: Dictionary with HeyGen video IDs {'intro_movie1': 'id1', 'movie2': 'id2', etc.}
        output_file: Optional file path to save results
        
    Returns:
        Dictionary with processing results
    """
    logger.info("Processing existing HeyGen video IDs with new API approach...")
    
    results = {
        'input_video_ids': heygen_video_ids,
        'timestamp': datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    }
    
    try:
        # Step 1: Get HeyGen video URLs using status API
        logger.info("Step 1: Getting HeyGen video URLs using status API...")
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids)
        results['heygen_video_urls'] = heygen_video_urls
        
        if not heygen_video_urls:
            logger.error("No HeyGen video URLs obtained")
            results['status'] = 'failed'
            results['error'] = 'No HeyGen video URLs obtained'
            return results
        
        logger.info(f"✅ Successfully obtained {len(heygen_video_urls)} HeyGen video URLs")
        
        # Step 2: Create Creatomate video
        logger.info("Step 2: Creating Creatomate video...")
        creatomate_id = create_creatomate_video_from_heygen_urls(heygen_video_urls, movie_data=None)
        results['creatomate_id'] = creatomate_id
        
        if creatomate_id.startswith('error') or creatomate_id.startswith('exception'):
            logger.error(f"❌ Creatomate video creation failed: {creatomate_id}")
            results['status'] = 'failed'
            results['error'] = f'Creatomate creation failed: {creatomate_id}'
        else:
            logger.info(f"🎬 Successfully submitted Creatomate video: {creatomate_id}")
            results['status'] = 'success'
            results['creatomate_status'] = 'submitted'
            results['status_check_command'] = f"python automated_video_generator.py --check-creatomate {creatomate_id}"
        
        # Step 3: Save results if output file provided
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"Results saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save results to {output_file}: {str(e)}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing existing HeyGen videos: {str(e)}")
        results['status'] = 'error'
        results['error'] = str(e)
        return results

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
    # Validate API key
    heygen_api_key = os.getenv("HEYGEN_API_KEY")
    if not heygen_api_key:
        logger.error("HEYGEN_API_KEY is not set in environment variables")
        return None
        
    # Validate script data
    if script_data is None:
        logger.error("No script data provided for video creation")
        return None
        
    logger.info(f"Creating HeyGen videos using {'template' if use_template else 'standard'} approach")
    
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
            with open(output_path, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data stored locally at: {output_path}")
        
        return group_id
    except Exception as e:
        logger.error(f"Error storing data in database: {str(e)}")
        # Store locally as backup
        try:
            backup_path = os.path.join("videos", f"backup_{timestamp}.json")
            with open(backup_path, "w", encoding='utf-8') as f:
                json.dump({
                    "movies": movie_data,
                    "cloudinary_urls": cloudinary_urls,
                    "video_id": video_id,
                    "script_path": script_path,
                    "error": str(e)
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Backup data stored at: {backup_path}")
        except Exception as backup_error:
            logger.error(f"Error creating backup: {str(backup_error)}")
        
        return f"error_{timestamp}"

# NOTE: process_heygen_videos_with_creatomate() function removed - no longer needed
# This function has been replaced by the more efficient process_existing_heygen_videos()


def run_full_workflow(num_movies=3, country="FR", genre="Horreur", platform="Netflix", content_type="Série", output=None):
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
        # Step 1: Query database for movies FIRST (before wasting time on screenshots)
        logger.info(f"Step 1: Checking database for {num_movies} movies ({country}, {genre}, {platform}, {content_type})")
        movies = extract_movie_data(num_movies, country, genre, platform, content_type)
        
        # Check if database query failed or returned no results - EXIT IMMEDIATELY
        if movies is None:
            logger.error("🚫 WORKFLOW TERMINATED - Database query failed or no movies found")
            logger.error("🔄 Script execution stopped. Please resolve the issue and try again.")
            import sys
            sys.exit(1)  # Exit with error code
        
        if len(movies) == 0:
            logger.error(f"📭 WORKFLOW TERMINATED - Empty movie list returned")
            logger.error("🔄 Script execution stopped. Please try different filter criteria.")
            import sys
            sys.exit(1)  # Exit with error code
        
        logger.info(f"✅ Found {len(movies)} movies in database - proceeding with workflow")
        
        # Step 2: Now capture screenshots from StreamGank (only if movies exist)
        logger.info("Step 2: Capturing screenshots from StreamGank")
        screenshot_paths = capture_streamgank_screenshots(country, genre, platform, content_type)
        results['screenshots'] = screenshot_paths
        logger.info(f"Captured {len(screenshot_paths)} screenshots")
        
        # Step 3: Upload screenshots to Cloudinary
        logger.info("Step 3: Uploading screenshots to Cloudinary")
        cloudinary_urls = upload_to_cloudinary(screenshot_paths)
        results['cloudinary_urls'] = {f"screenshot_{i}": url for i, url in enumerate(cloudinary_urls)}
        logger.info(f"Uploaded {len(cloudinary_urls)} screenshots to Cloudinary")
        
        # Ensure we have exactly num_movies movies
        movies = movies[:num_movies] if len(movies) >= num_movies else movies
        
        # If we still don't have enough movies, pad with simulated data
        if len(movies) < num_movies:
            logger.warning(f"Only found {len(movies)} movies, padding with simulated data")
            simulated = _simulate_movie_data(num_movies - len(movies))
            movies.extend(simulated[:num_movies - len(movies)])
        
        # Step 4: Enrich movie data with ChatGPT (using dynamic CLI arguments)
        logger.info("Step 4: Enriching movie data with AI")
        enriched_movies = enrich_movie_data(movies, country, genre, platform, content_type)
        results['enriched_movies'] = enriched_movies
        
        # Save enriched data for debugging or future use
        with open("videos/enriched_data.json", "w", encoding='utf-8') as f:
            json.dump(enriched_movies, f, indent=2, ensure_ascii=False)
        logger.info(f"Extracted and enriched {len(enriched_movies)} movies")
        
        # Step 5: Generate script for the avatar (using dynamic CLI arguments)
        logger.info("Step 5: Generating script for the avatar")
        combined_script, script_path, scripts = generate_script(enriched_movies, results['cloudinary_urls'], country, genre, platform, content_type)
        results['script'] = combined_script
        results['script_path'] = script_path
        results['script_sections'] = scripts
        logger.info("Generated script for the avatar")
        
        # Step 6: Create HeyGen videos
        logger.info("Step 6: Creating HeyGen videos")
        heygen_video_ids = create_heygen_video(scripts)
        results['video_ids'] = heygen_video_ids
        
        # Get HeyGen video URLs using intelligent waiting with script complexity analysis
        logger.info("Getting HeyGen video URLs for Creatomate integration...")
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids, scripts)
        results['heygen_video_urls'] = heygen_video_urls
        logger.info(f"Successfully obtained {len(heygen_video_urls)} HeyGen video URLs for Creatomate")
        
        # Step 6: Create final video with Creatomate
        logger.info("Step 6: Creating final video with Creatomate...")
        creatomate_id = create_creatomate_video_from_heygen_urls(heygen_video_urls, movie_data=enriched_movies)
        results['creatomate_id'] = creatomate_id
        
        if creatomate_id.startswith('error') or creatomate_id.startswith('exception'):
            logger.error(f"Creatomate creation failed: {creatomate_id}")
        else:
            logger.info(f"✅ Creatomate video submitted: {creatomate_id}")
            results['creatomate_status'] = 'submitted'
            results['status_check_command'] = f"python automated_video_generator.py --check-creatomate {creatomate_id}"
        
        # Step 7: Finalize results
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results['group_id'] = f"workflow_{timestamp}"
        logger.info(f"✅ Complete workflow finished with group ID: {results['group_id']}")
        
        # Save results to output file if specified
        if output:
            with open(output, "w", encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
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
                with open(output, "w", encoding='utf-8') as f:
                    results['error'] = str(e)
                    results['traceback'] = traceback.format_exc()
                    json.dump(results, f, indent=2, ensure_ascii=False)
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
        parser.add_argument("--process-heygen", help="Process existing HeyGen video IDs from JSON file (use with HeyGen video IDs)")
        parser.add_argument("--check-creatomate", help="Check the status of a Creatomate render by ID")
        parser.add_argument("--wait-creatomate", help="Wait for a Creatomate render to complete by ID")
        
        # Core parameters for customization
        parser.add_argument("--num-movies", type=int, default=3, help="Number of movies to extract (default: 3)")
        parser.add_argument("--country", default="FR", help="Country code for content filtering (default: FR)")
        parser.add_argument("--genre", default="Horreur", help="Genre to filter by (default: Horreur)")
        parser.add_argument("--platform", default="Netflix", help="Platform to filter by (default: Netflix)")
        parser.add_argument("--content-type", default="Série", help="Content type (Film/Série) to filter by (default: Série)")
        
        # HeyGen video processing
        parser.add_argument("--heygen-ids", help="JSON string or file path with HeyGen video IDs")
        
        # Debug and output options
        parser.add_argument("--output", help="Output file path to save results to")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")
        
        args = parser.parse_args()
        
        # Handle different execution modes
        if args.check_creatomate:
            # Check Creatomate render status
            print(f"\n🎬 StreamGank Video Generator - Creatomate Status Check")
            print(f"Checking status for render ID: {args.check_creatomate}")
            
            try:
                status_info = check_creatomate_render_status(args.check_creatomate)
                status = status_info.get("status", "unknown")
                
                print(f"\n📊 Render Status: {status}")
                if status_info.get("url"):
                    print(f"📹 Video URL: {status_info['url']}")
                    
                if status == "completed":
                    print("✅ Video is ready for download!")
                elif status == "planned":
                    print("⏳ Video is queued for rendering")
                elif status == "processing":
                    print("🔄 Video is currently being rendered")
                elif status in ["failed", "error"]:
                    print("❌ Video rendering failed")
                    
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(status_info, f, indent=2, ensure_ascii=False)
                    print(f"📁 Status saved to: {args.output}")
                    
            except Exception as e:
                print(f"❌ Error checking status: {str(e)}")
                sys.exit(1)
                
        elif args.wait_creatomate:
            # Wait for Creatomate render completion
            print(f"\n🎬 StreamGank Video Generator - Wait for Creatomate")
            print(f"Waiting for render ID: {args.wait_creatomate}")
            
            try:
                final_status = wait_for_creatomate_completion(args.wait_creatomate)
                status = final_status.get("status", "unknown")
                
                if status == "completed":
                    print(f"✅ Video completed successfully!")
                    print(f"📹 Download URL: {final_status.get('url', 'No URL')}")
                else:
                    print(f"❌ Video rendering ended with status: {status}")
                    
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(final_status, f, indent=2, ensure_ascii=False)
                    print(f"📁 Final status saved to: {args.output}")
                    
            except Exception as e:
                print(f"❌ Error waiting for completion: {str(e)}")
                sys.exit(1)
                
        elif args.process_heygen or args.heygen_ids:
            # Process existing HeyGen video IDs
            print(f"\n🎬 StreamGank Video Generator - HeyGen Processing Mode")
            
            heygen_video_ids = {}
            
            # Get HeyGen video IDs from command line or file
            if args.heygen_ids:
                try:
                    # Try to load from file first
                    if os.path.exists(args.heygen_ids):
                        with open(args.heygen_ids, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                heygen_video_ids = data.get('video_ids', data)
                            else:
                                logger.error("Invalid JSON format in HeyGen IDs file")
                                sys.exit(1)
                    else:
                        # Try to parse as JSON string
                        heygen_video_ids = json.loads(args.heygen_ids)
                except Exception as e:
                    logger.error(f"Error loading HeyGen video IDs: {str(e)}")
                    sys.exit(1)
                    
            elif args.process_heygen:
                try:
                    with open(args.process_heygen, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        heygen_video_ids = data.get('video_ids', data)
                except Exception as e:
                    logger.error(f"Error loading HeyGen video IDs from {args.process_heygen}: {str(e)}")
                    sys.exit(1)
            
            if not heygen_video_ids:
                logger.error("No HeyGen video IDs provided")
                sys.exit(1)
            
            print(f"Processing HeyGen video IDs: {list(heygen_video_ids.keys())}")
            
            try:
                results = process_existing_heygen_videos(heygen_video_ids, args.output)
                print("\n✅ HeyGen processing completed!")
                
                # Print summary
                if results.get('status') == 'success':
                    print(f"🎬 Successfully submitted Creatomate video: {results.get('creatomate_id')}")
                    print(f"📹 Status: {results.get('creatomate_status', 'submitted')}")
                    if results.get('status_check_command'):
                        print(f"💡 Check status: {results['status_check_command']}")
                else:
                    print(f"❌ Processing failed: {results.get('error')}")
                    
                if args.output:
                    print(f"📁 Results saved to: {args.output}")
                    
            except Exception as e:
                print(f"❌ Error during HeyGen processing: {str(e)}")
                sys.exit(1)
                
        else:
            # Run full workflow (default behavior)
            
            # Set default to --all if no specific arguments provided
            if not any([args.country != "FR", args.genre != "Horreur", args.platform != "netflix", 
                        args.content_type != "Film", args.num_movies != 3, args.debug, args.output]):
                args.all = True
                
            # Print execution parameters
            print(f"\n🎬 StreamGank Video Generator - Full Workflow Mode")
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
                        print(f"🎞️  Final video submitted to Creatomate ID: {results['creatomate_id']}")
                        print(f"📹 Status: {results.get('creatomate_status', 'submitted')}")
                        if results.get('status_check_command'):
                            print(f"💡 Check status: {results['status_check_command']}")
                        
                    if 'group_id' in results:
                        print(f"💾 All data stored with group ID: {results['group_id']}")
                        
                if args.output:
                    print(f"\n📁 Full results saved to: {args.output}")
                    
            except Exception as e:
                print(f"\n❌ Error during execution: {str(e)}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Unhandled exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
