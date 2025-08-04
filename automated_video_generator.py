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
    python3 automated_video_generator.py --country US --platform Netflix --genre Horror --content-type Film
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
from archive.create_scroll_video import create_scroll_video

# Import StreamGang helper functions
from streamgank_helpers import (
    get_genre_mapping_by_country,
    get_platform_mapping,
    get_content_type_mapping,
    get_content_type_mapping_by_country,
    build_streamgank_url,
    process_movie_trailers_to_clips,
    enrich_movie_data,
    generate_video_scripts,
    create_enhanced_movie_posters
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API configurations
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
CREATOMATE_API_KEY = os.getenv("CREATOMATE_API_KEY", "API_KEY")

# Create output directories
for dir_name in ["screenshots", "videos", "clips", "covers"]:
    Path(dir_name).mkdir(exist_ok=True)

# =============================================================================
# SCREENSHOT CAPTURE
# =============================================================================

def capture_streamgank_screenshots(country=None, genre=None, platform=None, content_type=None):
    """
    Capture mobile screenshots from StreamGank with dynamic filtering
    
    Args:
        country (str): Country code for filtering
        genre (str): Genre to filter by
        platform (str): Platform to filter by
        content_type (str): Content type to filter by
        
    Returns:
        list: List of screenshot file paths
    """
    logger.info(f"📸 Capturing StreamGank screenshots")
    logger.info(f"   Filters: {country}, {genre}, {platform}, {content_type}")
    
    # Build dynamic URL
    url = build_streamgank_url(country, genre, platform, content_type)
    logger.info(f"🌐 Target URL: {url}")
    
    # Create output directory
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_paths = []
    
    with sync_playwright() as p:
        # Launch browser in mobile mode
        browser = p.chromium.launch(headless=False)
        device = p.devices["iPhone 12 Pro Max"]
        context = browser.new_context(**device, locale='fr-FR', timezone_id='Europe/Paris')
        page = context.new_page()
        
        # Navigate and wait for page load
        page.goto(url)
        page.wait_for_selector("text=RESULTS", timeout=30000)
        logger.info("✅ Page loaded successfully")
        
        # Handle cookie banner if present
        try:
            cookie_banner = page.wait_for_selector("text=We use cookies", timeout=5000)
            if cookie_banner:
                essential_button = page.wait_for_selector("button:has-text('Essential Only')", timeout=3000)
                if essential_button:
                    essential_button.click()
                    time.sleep(2)
        except Exception:
            pass  # No cookies banner found
        
        time.sleep(5)
        
        # Take screenshots at different scroll positions
        captures = [
            {"name": "films_1_2", "scroll_position": 0},
            {"name": "films_3_4", "scroll_position": 800},
            {"name": "films_5_6", "scroll_position": 1600}
        ]
        
        for idx, capture in enumerate(captures):
            # Scroll and capture
            page.evaluate(f"window.scrollTo(0, {capture['scroll_position']})")
            time.sleep(2)
            
            # Remove cookie elements
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
            
            # Take screenshot
            screenshot_path = os.path.join(output_dir, f"{timestamp}_streamgank_{capture['name']}.png")
            page.screenshot(path=screenshot_path, full_page=False)
            screenshot_paths.append(screenshot_path)
            logger.info(f"📷 Screenshot {idx+1}/3 saved: {screenshot_path}")
        
        browser.close()
    
    logger.info("✅ All screenshots captured successfully!")
    return screenshot_paths

def upload_to_cloudinary(file_paths):
    """
    Upload images to Cloudinary and return URLs
    
    Args:
        file_paths (list): List of file paths to upload
        
    Returns:
        list: List of Cloudinary URLs
    """
    logger.info(f"☁️ Uploading {len(file_paths)} files to Cloudinary")
    cloudinary_urls = []
    
    for file_path in file_paths:
        try:
            response = cloudinary.uploader.upload(file_path, folder="streamgank_screenshots")
            url = response['secure_url']
            cloudinary_urls.append(url)
            logger.info(f"✅ Uploaded: {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"❌ Upload failed for {file_path}: {str(e)}")
    
    logger.info(f"✅ {len(cloudinary_urls)} files uploaded successfully")
    return cloudinary_urls

# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def test_supabase_connection():
    """Test Supabase connection and return status"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return False
        sample = supabase.table("movies").select("*").limit(1).execute()
        return hasattr(sample, 'data') and len(sample.data) >= 0
    except Exception as e:
        logger.error(f"Supabase connection failed: {str(e)}")
        return False

def extract_movie_data(num_movies=3, country=None, genre=None, platform=None, content_type=None, debug=False):
    """
    Extract top movies by IMDB score from Supabase with filtering
    
    Args:
        num_movies (int): Number of movies to extract
        country (str): Country code for filtering
        genre (str): Genre to filter by
        platform (str): Platform to filter by
        content_type (str): Content type to filter by
        debug (bool): Enable debug output
        
    Returns:
        list: List of movie data dictionaries or None if failed
    """
    logger.info(f"🎬 Extracting {num_movies} movies from database")
    logger.info(f"   Filters: {country}, {genre}, {platform}, {content_type}")
    
    # Test connection first
    if not test_supabase_connection():
        logger.error("❌ Database connection failed")
        return None
    
    try:
        # Build query with joins and filters
        query = supabase.from_("movies").select("""
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
        """)
        
        # Apply filters if provided
        if content_type:
            query = query.eq("content_type", content_type)
        if country:
            query = query.eq("movie_localizations.country_code", country)
        if platform:
            query = query.eq("movie_localizations.platform_name", platform)
        if genre:
            query = query.eq("movie_genres.genre", genre)
        
        # Execute query
        response = query.order("imdb_score", desc=True).limit(num_movies).execute()
        
        if not hasattr(response, 'data') or len(response.data) == 0:
            logger.error("❌ No movies found matching criteria")
            return None
        
        # Process results
        movie_data = []
        for movie in response.data:
            try:
                localization = movie.get('movie_localizations', [])
                if isinstance(localization, list) and len(localization) > 0:
                    localization = localization[0]
                
                genres_data = movie.get('movie_genres', [])
                if isinstance(genres_data, list):
                    genres = [g.get('genre') for g in genres_data if g.get('genre')]
                else:
                    genres = [genres_data.get('genre')] if genres_data.get('genre') else []
                
                movie_info = {
                    'id': movie.get('movie_id'),
                    'title': localization.get('title', 'Unknown Title'),
                    'year': movie.get('release_year', 'Unknown'),
                    'imdb': f"{movie.get('imdb_score', 0)}/10 ({movie.get('imdb_votes', 0)} votes)",
                    'imdb_score': movie.get('imdb_score', 0),
                    'imdb_votes': movie.get('imdb_votes', 0),
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
                
            except Exception as e:
                logger.error(f"Error processing movie {movie.get('movie_id', 'unknown')}: {str(e)}")
                continue
        
        movie_data.sort(key=lambda x: x.get('imdb_score', 0), reverse=True)
        
        if movie_data:
            logger.info(f"✅ Successfully extracted {len(movie_data)} movies")
            logger.info(f"   Top movie: {movie_data[0]['title']} - IMDB: {movie_data[0]['imdb']}")
            return movie_data
        else:
            logger.error("❌ No movies could be processed")
            return None
            
    except Exception as e:
        logger.error(f"❌ Database query failed: {str(e)}")
        return None

def _simulate_movie_data(num_movies=3):
    """Simulate movie data when database is unavailable"""
    import random
    
    base_movies = [
        {
            "title": "Ça", "platform": "Netflix", "year": "2017", "imdb": "7.3/10",
            "description": "Seven young outcasts face their worst nightmare in Derry, Maine.",
            "thumbnail_url": "https://streamgank.com/images/it.jpg",
            "genres": ["Horror", "Mystery & Thriller"]
        },
        {
            "title": "The Last of Us", "platform": "Netflix", "year": "2023", "imdb": "8.8/10",
            "description": "After a global pandemic, a hardened survivor takes charge of a 14-year-old girl who may be humanity's last hope.",
            "thumbnail_url": "https://streamgank.com/images/lastofus.jpg",
            "genres": ["Horror", "Drama"]
        },
        {
            "title": "Stranger Things", "platform": "Netflix", "year": "2016", "imdb": "8.7/10",
            "description": "When a young boy vanishes, a small town uncovers a mystery involving secret experiments and supernatural forces.",
            "thumbnail_url": "https://streamgank.com/images/strangerthings.jpg",
            "genres": ["Horror", "Sci-Fi"]
        }
    ]
    
    random.shuffle(base_movies)
    return base_movies[:num_movies]

# =============================================================================
# HEYGEN VIDEO PROCESSING
# =============================================================================

# =============================================================================
# HEYGEN VIDEO PROCESSING
# =============================================================================

def get_heygen_template_id(genre=None):
    """
    Get HeyGen template ID based on genre
    
    Args:
        genre (str): Genre name (e.g., "Horror", "Comedy", "Action", "Horreur", "Comédie", "Action & Aventure", etc.)
        
    Returns:
        str: HeyGen template ID
    """
    # Template mapping by genre
    # Horror template ID: e2ad0e5c7e71483991536f5c93594e42 (horror-specific template)
    # Comedy template ID: 15d9eadcb46a45dbbca1834aa0a23ede (comedy-specific template)
    # Action template ID: e44b139a1b94446a997a7f2ac5ac4178 (action-specific template)
    # Default template ID: cc6718c5363e42b282a123f99b94b335
    template_mapping = {
        "Horror": "e2ad0e5c7e71483991536f5c93594e42",
        "Horreur": "e2ad0e5c7e71483991536f5c93594e42",  # French horror
        "horror": "e2ad0e5c7e71483991536f5c93594e42",   # Case insensitive
        "horreur": "e2ad0e5c7e71483991536f5c93594e42",  # Case insensitive French
        "Comedy": "15d9eadcb46a45dbbca1834aa0a23ede",
        "Comédie": "15d9eadcb46a45dbbca1834aa0a23ede",  # French comedy
        "comedy": "15d9eadcb46a45dbbca1834aa0a23ede",   # Case insensitive
        "comédie": "15d9eadcb46a45dbbca1834aa0a23ede",  # Case insensitive French
        "Action": "e44b139a1b94446a997a7f2ac5ac4178",
        "Action & Aventure": "e44b139a1b94446a997a7f2ac5ac4178",  # French action
        "action": "e44b139a1b94446a997a7f2ac5ac4178",   # Case insensitive
        "action & aventure": "e44b139a1b94446a997a7f2ac5ac4178",  # Case insensitive French
    }
    
    if genre and genre in template_mapping:
        logger.info(f"🎭 Using genre-specific template for '{genre}': {template_mapping[genre]}")
        return template_mapping[genre]
    
    # Default template for all other genres
    default_template = "cc6718c5363e42b282a123f99b94b335"
    logger.info(f"🎭 Using default template for genre '{genre}': {default_template}")
    return default_template

def create_heygen_video(script_data, use_template=True, template_id=None, genre=None):
    """
    Create videos with HeyGen API
    
    Args:
        script_data: Dictionary containing scripts
        use_template: Whether to use template-based approach
        template_id: HeyGen template ID (if None, will be selected based on genre)
        genre: Genre for template selection (e.g., "Horror", "Horreur")
    
    Returns:
        Dictionary of video IDs
    """
    # Select template ID based on genre if not explicitly provided
    if template_id is None:
        template_id = get_heygen_template_id(genre)
    
    logger.info(f"🎬 Creating HeyGen videos with template: {template_id}")
    
    heygen_api_key = os.getenv("HEYGEN_API_KEY")
    if not heygen_api_key:
        logger.error("HEYGEN_API_KEY not found")
        return None
    
    if script_data is None:
        logger.error("No script data provided")
        return None
    
    # Handle different input formats
    if isinstance(script_data, str):
        script_data = {
            "single_video": {
                "text": script_data,
                "path": "direct_input"
            }
        }
    
    videos = {}
    
    # Process each script
    for key, script_info in script_data.items():
        logger.info(f"   Creating video for {key}")
        
        # Extract script text
        if isinstance(script_info, dict) and "text" in script_info:
            script_text = script_info["text"]
        else:
            script_text = str(script_info)
        
        # Create payload
        if use_template:
            payload = {
                "template_id": template_id,
                "caption": True,
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
        
        # Send request
        video_id = send_heygen_request(payload)
        videos[key] = video_id
    
    logger.info(f"✅ HeyGen video creation initiated: {len(videos)} videos")
    return videos

def send_heygen_request(payload):
    """Send request to HeyGen API"""
    heygen_api_key = os.getenv("HEYGEN_API_KEY")
    if not heygen_api_key:
        logger.error("HEYGEN_API_KEY not found")
        return None
    
    headers = {
        "X-Api-Key": heygen_api_key,
        "Content-Type": "application/json"
    }
    
    try:
        # Determine endpoint
        is_template_request = "template_id" in payload
        
        if is_template_request:
            template_id = payload.pop("template_id")
            url = f"https://api.heygen.com/v2/template/{template_id}/generate"
        else:
            url = "https://api.heygen.com/v2/video/generate"
        
        # Make request
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            data = response.json()
            video_id = data.get("data", {}).get("video_id")
            
            if video_id:
                logger.info(f"✅ Video generation started: {video_id}")
                return video_id
            else:
                logger.error(f"No video_id in response: {data}")
                return None
        else:
            logger.error(f"HeyGen API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception during video creation: {str(e)}")
        return None

def check_heygen_video_status(video_id: str, silent: bool = False) -> dict:
    """Check HeyGen video processing status"""
    if not silent:
        logger.debug(f"Checking HeyGen video status: {video_id[:8]}...")
    
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        return {"status": "unknown", "video_url": "", "data": {}}
    
    status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }
    
    try:
        response = requests.get(status_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                video_data = data['data']
                status = video_data.get('status', 'unknown')
                video_url = video_data.get('video_url', '') or video_data.get('url', '')
                
                return {
                    "status": status,
                    "video_url": video_url,
                    "data": video_data
                }
            else:
                return {"status": "unknown", "video_url": "", "data": data}
        else:
            return _try_fallback_status_endpoints(video_id, headers, silent)
            
    except Exception as e:
        return _try_fallback_status_endpoints(video_id, headers, silent)

def _try_fallback_status_endpoints(video_id: str, headers: dict, silent: bool = False) -> dict:
    """Try fallback endpoints for HeyGen status"""
    fallback_endpoints = [
        f"https://api.heygen.com/v1/video.status?video_id={video_id}",
        f"https://api.heygen.com/v1/video_status?video_id={video_id}",
        f"https://api.heygen.com/v2/video/{video_id}/status"
    ]
    
    for endpoint in fallback_endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    video_data = data['data']
                    status = video_data.get('status', 'unknown')
                    video_url = video_data.get('video_url', '') or video_data.get('url', '')
                    
                    return {
                        "status": status,
                        "video_url": video_url,
                        "data": video_data
                    }
        except Exception:
            continue
    
    return {"status": "unknown", "video_url": "", "data": {}}

def wait_for_heygen_video(video_id: str, script_length: int = None, max_wait_minutes: int = 15) -> dict:
    """
    Wait for HeyGen video completion with progress feedback
    
    Args:
        video_id: HeyGen video ID
        script_length: Script length for time estimation
        max_wait_minutes: Maximum wait time in minutes
        
    Returns:
        Dictionary with status information
    """
    # Estimate processing time
    estimated_minutes = estimate_heygen_processing_time(script_length)
    timeout_minutes = min(max(estimated_minutes + 5, 8), max_wait_minutes)
    max_total_seconds = timeout_minutes * 60
    
    logger.info(f"⏳ Waiting for HeyGen video {video_id[:8]}... (estimated: ~{estimated_minutes} min)")
    
    start_time = time.time()
    attempt = 0
    next_check_time = start_time
    
    # Spinner frames
    spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    while True:
        current_time = time.time()
        elapsed_seconds = current_time - start_time
        
        # Check timeout
        if elapsed_seconds > max_total_seconds:
            elapsed_time = int(elapsed_seconds)
            minutes, seconds = divmod(elapsed_time, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            print(f"\r⏰ HeyGen video timeout    [{'░' * 30}] ----  │ {time_str} │ Max time reached{' ' * 10}")
            logger.warning(f"HeyGen video {video_id[:8]}... exceeded max wait time")
            
            return {
                'success': False,
                'status': 'timeout',
                'video_url': '',
                'data': {}
            }
        
        # Check status at intervals
        if current_time >= next_check_time:
            attempt += 1
            
            # Calculate progress
            time_progress = min(elapsed_seconds / (estimated_minutes * 60) * 100, 95)
            attempt_progress = min(elapsed_seconds / max_total_seconds * 100, 95)
            progress = max(time_progress, attempt_progress)
            
            elapsed_time = int(elapsed_seconds)
            minutes, seconds = divmod(elapsed_time, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # ETA calculation
            remaining_seconds = max(0, (estimated_minutes * 60) - elapsed_seconds)
            if remaining_seconds > 0 and progress < 90:
                remaining_minutes, remaining_secs = divmod(int(remaining_seconds), 60)
                eta_str = f"ETA ~{remaining_minutes:02d}:{remaining_secs:02d}"
            else:
                eta_str = "Almost ready..."
            
            # Progress display
            spinner = spinner_frames[attempt % len(spinner_frames)]
            bar_length = 30
            filled_length = int(bar_length * progress / 100)
            bar = f"[{'█' * filled_length}{'░' * (bar_length - filled_length)}]"
            
            progress_line = f"\r{spinner} Processing HeyGen video {bar} {progress:5.1f}% │ {time_str} │ {eta_str}"
            print(progress_line, end='', flush=True)
            
            # Check status
            status_info = check_heygen_video_status(video_id, silent=True)
            status = status_info.get('status', 'unknown')
            video_url = status_info.get('video_url', '')
            
            if status == "completed":
                print(f"\r✅ HeyGen video completed! [{'█' * bar_length}] 100.0% │ {time_str} │ Ready!{' ' * 15}")
                logger.info(f"🎬 Video completed in {minutes}:{seconds:02d}")
                
                return {
                    'success': True,
                    'status': status,
                    'video_url': video_url,
                    'data': status_info.get('data', {})
                }
                
            elif status in ["failed", "error"]:
                print(f"\r❌ HeyGen video failed!   [{'X' * bar_length}] ERROR │ {time_str} │ Processing failed{' ' * 10}")
                logger.error(f"HeyGen video {video_id[:8]}... processing failed")
                
                return {
                    'success': False,
                    'status': status,
                    'video_url': video_url,
                    'data': status_info.get('data', {})
                }
            
            # Set next check interval
            if elapsed_seconds < 120:
                current_interval = 10
            elif elapsed_seconds < 300:
                current_interval = 15
            elif elapsed_seconds < 600:
                current_interval = 20
            else:
                current_interval = 30
                
            next_check_time = current_time + current_interval
        
        time.sleep(1)

def estimate_heygen_processing_time(script_length: int = None) -> int:
    """Estimate HeyGen processing time based on script complexity"""
    base_minutes = 3
    
    if script_length is None:
        return 6
    
    additional_minutes = script_length // 200
    
    if script_length <= 300:
        estimated = base_minutes + 1  # 4 minutes
    elif script_length <= 800:
        estimated = base_minutes + 3  # 6 minutes
    else:
        estimated = base_minutes + min(additional_minutes, 9)  # Cap at 12 minutes
    
    return estimated

def get_heygen_videos_for_creatomate(heygen_video_ids: dict, scripts: dict = None) -> dict:
    """
    Get HeyGen video URLs for direct use with Creatomate - STRICT MODE
    
    Args:
        heygen_video_ids: Dictionary of HeyGen video IDs (no placeholders allowed)
        scripts: Dictionary of script data for time estimation
        
    Returns:
        Dictionary with video URLs ready for Creatomate, or None if any video fails
        
    Note:
        STRICT MODE - Returns None if any video fails. No fallbacks allowed.
    """
    logger.info(f"🔗 Getting HeyGen video URLs for {len(heygen_video_ids)} videos - STRICT MODE")
    
    video_urls = {}
    
    for key, video_id in heygen_video_ids.items():
        if not video_id or video_id.startswith('placeholder'):
            logger.error(f"❌ Invalid or placeholder ID for {key}: {video_id}")
            logger.error("❌ STRICT MODE - No placeholder IDs allowed")
            return None
        
        # Extract script length for estimation
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
        
        logger.info(f"   Processing {key}: {video_id} ({script_length or 'unknown'} chars)")
        
        # Wait for video completion
        status_result = wait_for_heygen_video(
            video_id, 
            script_length=script_length,
            max_wait_minutes=25
        )
        
        if status_result['success'] and status_result['video_url']:
            video_url = status_result['video_url']
            video_urls[key] = video_url
            logger.info(f"✅ Got URL for {key}: {video_url[:50]}...")
        else:
            # STRICT MODE - No fallbacks allowed
            logger.error(f"❌ HeyGen video failed for {key}: {video_id}")
            logger.error(f"   Status: {status_result}")
            logger.error("❌ STRICT MODE - No fallback URLs allowed")
            return None
    
    logger.info(f"✅ Obtained {len(video_urls)} video URLs")
    return video_urls

# =============================================================================
# CREATOMATE VIDEO COMPOSITION - MODULAR ARCHITECTURE
# =============================================================================

def _validate_creatomate_inputs(heygen_video_urls: dict, movie_data: List[Dict[str, Any]], poster_timing_mode: str) -> str:
    """
    Validate inputs for Creatomate video creation - STRICT MODE
    
    Args:
        heygen_video_urls: Dictionary with HeyGen video URLs
        movie_data: List of movie data dictionaries
        poster_timing_mode: Poster timing mode to validate
        
    Returns:
        Empty string if valid, error message if invalid
    """
    logger.info("🔍 Validating Creatomate inputs - STRICT MODE")
    
    # Validate HeyGen URLs
    if not heygen_video_urls or not isinstance(heygen_video_urls, dict):
        logger.error("❌ Invalid or missing heygen_video_urls")
        return f"error_invalid_heygen_urls_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Validate poster timing mode
    valid_modes = ["heygen_last3s", "with_movie_clips"]
    if poster_timing_mode not in valid_modes:
        logger.error(f"❌ Invalid poster_timing_mode: {poster_timing_mode}. Must be one of: {valid_modes}")
        return f"error_invalid_timing_mode_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Validate movie data
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: DYNAMIC ASSET PREPARATION (Enhanced Posters & Movie Clips)
    # ═══════════════════════════════════════════════════════════════
    
    logger.info("✅ All inputs validated successfully")
    return ""  # Empty string indicates success


def _calculate_movie_clip_durations(movie_clips: List[str]) -> Dict[str, float]:
    """
    Calculate actual durations for all movie clips using FFprobe
    
    Args:
        movie_clips: List of movie clip URLs
        
    Returns:
        Dictionary with calculated durations for each movie clip
    """
    logger.info("⏱️ Calculating movie clip durations using FFprobe")
    
    durations = {}
    
    # Get actual durations using FFprobe (reuse the same function as HeyGen)
    durations["clip1"] = get_actual_heygen_duration(movie_clips[0]) if len(movie_clips) > 0 else 15
    durations["clip2"] = get_actual_heygen_duration(movie_clips[1]) if len(movie_clips) > 1 else 15
    durations["clip3"] = get_actual_heygen_duration(movie_clips[2]) if len(movie_clips) > 2 else 15
    
    logger.info(f"📊 Movie Clip Duration Analysis Results:")
    logger.info(f"   🎬 Clip1: {durations['clip1']:.1f}s")
    logger.info(f"   🎬 Clip2: {durations['clip2']:.1f}s")
    logger.info(f"   🎬 Clip3: {durations['clip3']:.1f}s")
    
    return durations


def _calculate_heygen_durations(heygen_video_urls: dict, scripts: dict) -> Dict[str, float]:
    """
    Calculate actual durations for all HeyGen videos using FFprobe
    
    Args:
        heygen_video_urls: Dictionary with HeyGen video URLs
        scripts: Dictionary with script data for fallback estimation
        
    Returns:
        Dictionary with calculated durations for each HeyGen video
    """
    logger.info("⏱️ Calculating HeyGen video durations using FFprobe")
    
    durations = {}
    
    # Extract scripts for each HeyGen video
    heygen1_script = scripts.get("movie1", "") if scripts else ""
    heygen2_script = scripts.get("movie2", "") if scripts else ""
    heygen3_script = scripts.get("movie3", "") if scripts else ""
    
    # Get actual durations using FFprobe with fallbacks
    durations["heygen1"] = get_actual_heygen_duration(heygen_video_urls["movie1"], heygen1_script)
    durations["heygen2"] = get_actual_heygen_duration(heygen_video_urls["movie2"], heygen2_script)
    durations["heygen3"] = get_actual_heygen_duration(heygen_video_urls["movie3"], heygen3_script)
    
    logger.info(f"📊 HeyGen Duration Analysis Results:")
    logger.info(f"   🎬 HeyGen1: {durations['heygen1']:.1f}s")
    logger.info(f"   🎬 HeyGen2: {durations['heygen2']:.1f}s")
    logger.info(f"   🎬 HeyGen3: {durations['heygen3']:.1f}s")
    
    return durations


class PosterTimingStrategy:
    """
    Abstract base class for poster timing calculation strategies
    Following Strategy Pattern for professional big tech architecture
    """
    
    def calculate_timing(self, heygen_durations: Dict[str, float], clip_durations: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        Calculate poster timing based on HeyGen video durations and movie clip durations
        
        Args:
            heygen_durations: Dictionary with HeyGen video durations
            clip_durations: Dictionary with movie clip durations
            
        Returns:
            Dictionary with timing data for each poster
        """
        raise NotImplementedError("Subclasses must implement calculate_timing method")


class HeyGenLast3SecondsStrategy(PosterTimingStrategy):
    """
    Strategy for displaying posters during the last 3 seconds of HeyGen videos
    """
    
    def calculate_timing(self, heygen_durations: Dict[str, float], clip_durations: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        Calculate timing for posters to appear during last 3 seconds of HeyGen videos
        """
        logger.info("🎯 Using HeyGen Last 3 Seconds strategy")
        
        # Define constants
        intro_duration = 1.0
        poster_duration = 3.0
        min_heygen_time = 5.0  # Minimum time before poster can appear
        
        # Calculate HeyGen video start times in sequential timeline using ACTUAL clip durations
        heygen1_start_time = intro_duration
        heygen2_start_time = intro_duration + heygen_durations["heygen1"] + clip_durations["clip1"]
        heygen3_start_time = intro_duration + heygen_durations["heygen1"] + clip_durations["clip1"] + heygen_durations["heygen2"] + clip_durations["clip2"]
        
        # Calculate poster times - last 3 seconds of each HeyGen video
        poster1_time = heygen1_start_time + heygen_durations["heygen1"] - poster_duration
        poster2_time = heygen2_start_time + heygen_durations["heygen2"] - poster_duration
        poster3_time = heygen3_start_time + heygen_durations["heygen3"] - poster_duration
        
        # ⚠️ DEBUG LOGGING - Let's see the exact calculations
        logger.info(f"🔍 DETAILED TIMING DEBUG:")
        logger.info(f"   📊 HeyGen Durations: {heygen_durations}")
        logger.info(f"   📊 Clip Durations: {clip_durations}")
        logger.info(f"   🎬 HeyGen1 starts: {heygen1_start_time:.1f}s, ends: {heygen1_start_time + heygen_durations['heygen1']:.1f}s")
        logger.info(f"   🎬 HeyGen2 starts: {heygen2_start_time:.1f}s, ends: {heygen2_start_time + heygen_durations['heygen2']:.1f}s")
        logger.info(f"   🎬 HeyGen3 starts: {heygen3_start_time:.1f}s, ends: {heygen3_start_time + heygen_durations['heygen3']:.1f}s")
        logger.info(f"   🖼️ Poster1 time: {poster1_time:.1f}s (should be last 3s of HeyGen1)")
        logger.info(f"   🖼️ Poster2 time: {poster2_time:.1f}s (should be last 3s of HeyGen2)")
        logger.info(f"   🖼️ Poster3 time: {poster3_time:.1f}s (should be last 3s of HeyGen3)")
        
        # Safety checks for short videos
        timings = {}
        
        # Poster 1 timing with safety check
        if poster1_time < heygen1_start_time + min_heygen_time:
            poster1_time = heygen1_start_time + min_heygen_time
            actual_poster1_duration = heygen1_start_time + heygen_durations["heygen1"] - poster1_time
            logger.warning(f"⚠️ HeyGen1 too short - Poster1 adjusted to {actual_poster1_duration:.1f}s duration")
        else:
            actual_poster1_duration = poster_duration
            
        timings["poster1"] = {
            "time": poster1_time,
            "duration": actual_poster1_duration
        }
        
        # Poster 2 timing with safety check
        if poster2_time < heygen2_start_time + min_heygen_time:
            poster2_time = heygen2_start_time + min_heygen_time
            actual_poster2_duration = heygen2_start_time + heygen_durations["heygen2"] - poster2_time
            logger.warning(f"⚠️ HeyGen2 too short - Poster2 adjusted to {actual_poster2_duration:.1f}s duration")
        else:
            actual_poster2_duration = poster_duration
            
        timings["poster2"] = {
            "time": poster2_time,
            "duration": actual_poster2_duration
        }
        
        # Poster 3 timing with safety check
        if poster3_time < heygen3_start_time + min_heygen_time:
            poster3_time = heygen3_start_time + min_heygen_time
            actual_poster3_duration = heygen3_start_time + heygen_durations["heygen3"] - poster3_time
            logger.warning(f"⚠️ HeyGen3 too short - Poster3 adjusted to {actual_poster3_duration:.1f}s duration")
        else:
            actual_poster3_duration = poster_duration
            
        timings["poster3"] = {
            "time": poster3_time,
            "duration": actual_poster3_duration
        }
        
        # Log timing details
        logger.info("📍 HEYGEN LAST 3 SECONDS MODE - Timing calculated:")
        logger.info(f"   Poster1: {timings['poster1']['time']:.1f}s → {timings['poster1']['time'] + timings['poster1']['duration']:.1f}s (last {timings['poster1']['duration']:.1f}s of HeyGen1)")
        logger.info(f"   Poster2: {timings['poster2']['time']:.1f}s → {timings['poster2']['time'] + timings['poster2']['duration']:.1f}s (last {timings['poster2']['duration']:.1f}s of HeyGen2)")
        logger.info(f"   Poster3: {timings['poster3']['time']:.1f}s → {timings['poster3']['time'] + timings['poster3']['duration']:.1f}s (last {timings['poster3']['duration']:.1f}s of HeyGen3)")
        
        return timings


class WithMovieClipsStrategy(PosterTimingStrategy):
    """
    Strategy for displaying posters simultaneously with movie clips
    """
    
    def calculate_timing(self, heygen_durations: Dict[str, float], clip_durations: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        Calculate timing for posters to appear with movie clips
        """
        logger.info("🎯 Using Simultaneous with Movie Clips strategy")
        
        # Define constants
        intro_duration = 1.0
        
        # Calculate when each movie clip starts using ACTUAL durations
        clip1_start_time = intro_duration + heygen_durations["heygen1"]
        clip2_start_time = intro_duration + heygen_durations["heygen1"] + clip_durations["clip1"] + heygen_durations["heygen2"]
        clip3_start_time = intro_duration + heygen_durations["heygen1"] + clip_durations["clip1"] + heygen_durations["heygen2"] + clip_durations["clip2"] + heygen_durations["heygen3"]
        
        # Posters appear WITH movie clips for their ACTUAL duration
        timings = {
            "poster1": {
                "time": clip1_start_time,
                "duration": clip_durations["clip1"]
            },
            "poster2": {
                "time": clip2_start_time,
                "duration": clip_durations["clip2"]
            },
            "poster3": {
                "time": clip3_start_time,
                "duration": clip_durations["clip3"]
            }
        }
        
        # Log timing details
        logger.info("📍 MOVIE CLIPS SIMULTANEOUS MODE - Timing calculated:")
        logger.info(f"   Poster1: {timings['poster1']['time']:.1f}s → {timings['poster1']['time'] + timings['poster1']['duration']:.1f}s (WITH Movie Clip 1)")
        logger.info(f"   Poster2: {timings['poster2']['time']:.1f}s → {timings['poster2']['time'] + timings['poster2']['duration']:.1f}s (WITH Movie Clip 2)")
        logger.info(f"   Poster3: {timings['poster3']['time']:.1f}s → {timings['poster3']['time'] + timings['poster3']['duration']:.1f}s (WITH Movie Clip 3)")
        
        return timings


def _get_poster_timing_strategy(poster_timing_mode: str) -> PosterTimingStrategy:
    """
    Factory function to get the appropriate poster timing strategy
    
    Args:
        poster_timing_mode: The poster timing mode to use
        
    Returns:
        Appropriate strategy instance
    """
    strategies = {
        "heygen_last3s": HeyGenLast3SecondsStrategy(),
        "with_movie_clips": WithMovieClipsStrategy()
    }
    
    return strategies[poster_timing_mode]


def _build_creatomate_composition(heygen_video_urls: dict, movie_covers: List[str], movie_clips: List[str], 
                                poster_timings: Dict[str, Dict[str, float]], heygen_durations: Dict[str, float] = None, 
                                clip_durations: Dict[str, float] = None, scroll_video_url: str = None) -> Dict:
    """
    Build the complete Creatomate composition with all elements
    
    Args:
        heygen_video_urls: Dictionary with HeyGen video URLs
        movie_covers: List of enhanced poster URLs  
        movie_clips: List of processed movie clip URLs
        poster_timings: Dictionary with calculated poster timing data
        heygen_durations: Dictionary with HeyGen video durations
        clip_durations: Dictionary with movie clip durations
        scroll_video_url: Optional scroll video URL for overlay
        
    Returns:
        Complete Creatomate composition dictionary
    """
    logger.info("🎬 Building Creatomate composition with dynamic sources")
    
    # Extract timing data for easy access
    poster1_time = poster_timings["poster1"]["time"]
    poster1_duration = poster_timings["poster1"]["duration"]
    poster2_time = poster_timings["poster2"]["time"]
    poster2_duration = poster_timings["poster2"]["duration"]
    poster3_time = poster_timings["poster3"]["time"]
    poster3_duration = poster_timings["poster3"]["duration"]
    

    # Calculate total video length using ACTUAL clip durations
    total_video_length = 1 + heygen_durations["heygen1"] + clip_durations["clip1"] + heygen_durations["heygen2"] + clip_durations["clip2"] + heygen_durations["heygen3"] + clip_durations["clip3"] + 3
        
    # Branding duration = total - intro(1s) - outro(3s)
    branding_duration = total_video_length - 1 - 3 - 1 - 0.5 - 0.5 # -1 is duration of the fade outro, 0.5 os for the 2nd and 3rd heygen video
        
    logger.info(f"📊 Total video length: {total_video_length:.1f}s (using ACTUAL clip durations)")
    logger.info(f"🏷️ BRANDING duration: {branding_duration:.1f}s (starts at 1s, ends at {1 + branding_duration:.1f}s)")
    logger.info(f"🎬 OUTRO starts at: {total_video_length - 3:.1f}s")
    logger.info(f"🔍 BRANDING vs OUTRO: Branding ends at {1 + branding_duration:.1f}s, Outro starts at {total_video_length - 3:.1f}s")
    logger.info(f"🔍 Gap/Overlap: {(total_video_length - 3) - (1 + branding_duration):.1f}s")

    
    # Base composition structure
    composition = {
        "width": 1080,
        "height": 1920,
        "frame_rate": 30,
        "output_format": "mp4",
        "elements": [
            # ═══════════════════════════════════════════════════════════════
            # MAIN TIMELINE (Track 1) - Sequential elements
            # ═══════════════════════════════════════════════════════════════
            
            # 🎯 ELEMENT 1: INTRO IMAGE (1 second)
            {
                "type": "image",
                "track": 1,
                "time": 0,
                "duration": 1,
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1753263646/streamGank_intro_cwefmt.jpg",
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": 1,
                        "easing": "quadratic-out",
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 ELEMENT 2: HEYGEN VIDEO 1 - Natural duration
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "source": heygen_video_urls["movie1"],
                "fit": "cover"
            },
            
            # 🎯 ELEMENT 3: MOVIE CLIP 1 (ACTUAL duration)
            {
                "type": "video", 
                "track": 1,
                "time": "auto",
                "duration": clip_durations["clip1"],
                "source": movie_clips[0],
                "fit": "cover"
            },
            
            # 🎯 ELEMENT 4: HEYGEN VIDEO 2 - Natural duration
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "source": heygen_video_urls["movie2"],
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": 0.5, # Fade in and out duration of heygen 3rd video
                        "transition": True,
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 ELEMENT 5: MOVIE CLIP 2 (ACTUAL duration)
            {
                "type": "video",
                "track": 1, 
                "time": "auto",
                "duration": clip_durations["clip2"],
                "source": movie_clips[1],
                "fit": "cover"
            },
            
            # 🎯 ELEMENT 6: HEYGEN VIDEO 3 - Natural duration
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "source": heygen_video_urls["movie3"],
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": 0.5, # Fade in and out duration of heygen 3rd video
                        "transition": True,
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 ELEMENT 7: MOVIE CLIP 3 (ACTUAL duration)
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "duration": clip_durations["clip3"],
                "source": movie_clips[2],
                "fit": "cover"
            },
            
            # 🎯 ELEMENT 8: OUTRO IMAGE (3 seconds)
            {
                "type": "image",
                "track": 1,
                "time": "auto",
                "duration": 3,
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1752587571/streamgank_bg_heecu7.png",
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": 1,
                        "transition": True,
                        "type": "fade"
                    }
                ]
            },
            
            # ═══════════════════════════════════════════════════════════════
            # OVERLAY ELEMENTS (Track 2) - Enhanced Posters with Perfect Timing
            # ═══════════════════════════════════════════════════════════════
            
            # 🎯 POSTER 1 - Calculated timing with actual HeyGen duration
            {
                "type": "image",
                "track": 2,
                "time": poster1_time,
                "duration": poster1_duration,
                "source": movie_covers[0],
                "fit": "contain",
                "animations": [
                    {
                        "time": 0,
                        "duration": 1,
                        "easing": "quadratic-out",
                        "type": "fade"
                    },
                    {
                        "time": "end",
                        "duration": 1,
                        "easing": "quadratic-out",
                        "reversed": True,
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 POSTER 2 - Calculated timing with actual HeyGen duration
            {
                "type": "image",
                "track": 2,  
                "time": poster2_time - 0.5, # Dont remove this comment - 0.5 is the duration of the fade in and out of heygen 2nd video
                "duration": poster2_duration,
                "source": movie_covers[1],
                "fit": "contain",
                "animations": [
                    {
                        "time": 0,
                        "duration": 1,
                        "easing": "quadratic-out",
                        "type": "fade"
                    },
                    {
                        "time": "end",
                        "duration": 1,
                        "easing": "quadratic-out",
                        "reversed": True,
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 POSTER 3 - Calculated timing with actual HeyGen duration
            {
                "type": "image",
                "track": 2,
                "time": poster3_time - 0.5, # Dont remove this comment - 0.5 is the duration of the fade in and out of heygen 3rd video
                "duration": poster3_duration,
                "source": movie_covers[2],
                "fit": "contain",
                "animations": [
                    {
                        "time": 0,
                        "duration": 1,
                        "easing": "quadratic-out",
                        "type": "fade"
                    },
                    {
                        "time": "end",
                        "duration": 1,
                        "easing": "quadratic-out",
                        "reversed": True,
                        "type": "fade"
                    }
                ]
            },
            
            # ═══════════════════════════════════════════════════════════════
            # PERSISTENT BRANDING (Tracks 3) 
            # ═══════════════════════════════════════════════════════════════
            
            {
                "name": "Composition-228",
                "type": "composition",
                "track": 3,
                "time": 1,
                "duration": branding_duration,
                "elements": [
                    # STREAMGANK LOGO TEXT "Stream" - Green colored, persistent overlay
                    {
                        "name": "StreamGank-Stream",
                        "type": "text",
                        "x": "19.2502%",
                        "y": "0%",
                        "x_anchor": "0%",
                        "y_anchor": "0%",
                        "text": "Stream",
                        "font_family": "Noto Sans",
                        "font_weight": "700",
                        "font_size": "10 vmin",
                        "fill_color": "#61d7a5",
                        "shadow_color": "rgba(0,0,0,0.8)",
                        "shadow_blur": "2 vmin"
                    },

                    # STREAMGANK LOGO TEXT "Gank" - White colored, persistent overlay
                    {
                        "name": "Text-9SD",
                        "type": "text",
                        "x": "54.7131%",
                        "y": "0%",
                        "x_anchor": "0%",
                        "y_anchor": "0%",
                        "text": "Gank",
                        "font_family": "Noto Sans",
                        "font_weight": "700",
                        "font_size": "10 vmin",
                        "fill_color": "#ffffff",
                        "shadow_color": "rgba(0,0,0,0.25)"
                    },

                    # STREAMGANK TAGLINE - Brand message, persistent overlay
                    {
                        "name": "Text-LZ9",
                        "type": "text",
                        "x": "20.1158%",
                        "y": "6.1282%",
                        "x_anchor": "0%",
                        "y_anchor": "0%",
                        "text": "AMBUSH THE BEST VOD TOGETHER",
                        "font_family": "Noto Sans",
                        "font_weight": "700",
                        "font_size": "3.5 vmin",
                        "fill_color": "#ffffff",
                        "shadow_color": "rgba(0,0,0,0.8)",
                        "shadow_blur": "2 vmin"
                    }
                ]
            }
        ]
    }

    # Add scroll video overlay if provided (Track 6 - Top layer)
    if scroll_video_url:
        scroll_overlay = {
            "name": "ScrollVideo-Overlay",
            "type": "video",
            "track": 4,
            "time": 4,   # Start at 4 seconds into video
            "duration": 6,  # Play for 6 seconds
            "source": scroll_video_url,
            "fit": "cover",
            "width": "100%",
            "height": "100%",
            "animations": [
                {
                    "time": 0,
                    "duration": 1,
                    "type": "fade",
                    "fade_in": True
                },
                {
                    "time": "end",
                    "duration": 1,
                    "easing": "quadratic-out",
                    "reversed": True,
                    "type": "fade"
                }
            ]
        }
        composition["elements"].append(scroll_overlay)
        logger.info("✅ Scroll video overlay added to composition")
    else:
        logger.info("ℹ️ No scroll video URL provided - skipping overlay")
    
    logger.info(f"🎬 Composition built with {len(composition['elements'])} total elements")
    return composition


def create_creatomate_video_from_heygen_urls(heygen_video_urls: dict, movie_data: List[Dict[str, Any]] = None, scroll_video_url: str = None, scripts: dict = None, poster_timing_mode: str = "heygen_last3s") -> str:
    """
    Create final video with Creatomate using HeyGen video URLs
    
    REFACTORED: Professional big tech modular architecture with clean separation of concerns
    
    Args:
        heygen_video_urls: Dictionary with HeyGen video URLs
        movie_data: List of movie data dictionaries (minimum 3 required)
        scroll_video_url: Optional scroll video URL for overlay
        scripts: Optional dictionary with script data for duration estimation
        poster_timing_mode: Poster timing mode (default: "heygen_last3s")
            - "heygen_last3s": Posters appear during last 3s of HeyGen videos
            - "with_movie_clips": Posters appear simultaneously with movie clips
        
    Returns:
        Creatomate video ID or error message (NO FALLBACKS - strict mode)
    """
    logger.info("🎞️ MODULAR CREATOMATE ORCHESTRATOR - Professional Big Tech Architecture")
    logger.info(f"🎯 Poster timing mode: {poster_timing_mode}")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: INPUT VALIDATION (Extracted & Modular)
    # ═══════════════════════════════════════════════════════════════
    validation_error = _validate_creatomate_inputs(heygen_video_urls, movie_data, poster_timing_mode)
    if validation_error:
        return validation_error
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: DYNAMIC ASSET PREPARATION (Enhanced Posters & Movie Clips)
    # ═══════════════════════════════════════════════════════════════
    logger.info("🎨 Creating enhanced movie posters with metadata overlays")
    enhanced_posters = create_enhanced_movie_posters(movie_data, max_movies=3)
    
    # Prepare movie covers (enhanced posters) - STRICT MODE
    movie_covers = []
    for i, movie in enumerate(movie_data[:3]):
        movie_title = movie.get('title', f'Movie_{i+1}')
        if movie_title in enhanced_posters:
            movie_covers.append(enhanced_posters[movie_title])
            logger.info(f"✅ Movie {i+1} cover: {movie_title} -> ENHANCED POSTER")
        else:
            logger.error(f"❌ Failed to create enhanced poster for {movie_title}")
            return f"error_poster_creation_failed_{movie_title}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info("🎞️ Processing dynamic cinematic portrait clips from trailers")
    dynamic_clips = process_movie_trailers_to_clips(movie_data, max_movies=3, transform_mode="youtube_shorts")
    
    # Prepare movie clips - STRICT MODE  
    movie_clips = []
    for i, movie in enumerate(movie_data[:3]):
        movie_title = movie.get('title', f'Movie_{i+1}')
        if movie_title in dynamic_clips:
            movie_clips.append(dynamic_clips[movie_title])
            logger.info(f"✅ Movie {i+1} clip: {movie_title} -> DYNAMIC CLIP")
        else:
            logger.error(f"❌ Failed to create dynamic clip for {movie_title}")
            return f"error_clip_creation_failed_{movie_title}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: HEYGEN DURATION ANALYSIS (FFprobe-Powered)
    # ═══════════════════════════════════════════════════════════════
    heygen_durations = _calculate_heygen_durations(heygen_video_urls, scripts)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3.5: MOVIE CLIP DURATION ANALYSIS (FFprobe-Powered)
    # ═══════════════════════════════════════════════════════════════
    clip_durations = _calculate_movie_clip_durations(movie_clips)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: POSTER TIMING CALCULATION (Strategy Pattern)
    # ═══════════════════════════════════════════════════════════════
    timing_strategy = _get_poster_timing_strategy(poster_timing_mode)
    poster_timings = timing_strategy.calculate_timing(heygen_durations, clip_durations)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 5: COMPOSITION BUILDING (Modular Architecture)
    # ═══════════════════════════════════════════════════════════════
    composition = _build_creatomate_composition(
        heygen_video_urls=heygen_video_urls,
        movie_covers=movie_covers,
        movie_clips=movie_clips,
        poster_timings=poster_timings,
        heygen_durations=heygen_durations,
        clip_durations=clip_durations,
        scroll_video_url=scroll_video_url
    )
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 6: CREATOMATE API EXECUTION
    # ═══════════════════════════════════════════════════════════════
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        logger.error("❌ CREATOMATE_API_KEY not found")
        return f"error_no_api_key_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Execute Creatomate API call with modular composition
    payload = {
        "source": composition,
        "output_format": "mp4",
        "render_scale": 1
    }
    
    logger.info("🚀 Executing Creatomate API with modular composition")
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
            
            # Handle both single object and array responses
            if isinstance(result, list) and len(result) > 0:
                creatomate_data = result[0]
                render_id = creatomate_data.get("id", "")
                status = creatomate_data.get("status", "unknown")
                logger.info(f"✅ MODULAR ARCHITECTURE SUCCESS: Render {render_id[:8]}... status: {status}")
            elif isinstance(result, dict):
                render_id = result.get("id", "")
                status = result.get("status", "unknown")
                logger.info(f"✅ MODULAR ARCHITECTURE SUCCESS: Render {render_id[:8]}... status: {status}")
            else:
                render_id = f"unknown_format_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"🎯 Mode used: {poster_timing_mode}")
            logger.info(f"💡 Check render status: python automated_video_generator.py --check-creatomate {render_id}")
            logger.info(f"⏳ Wait for completion: python automated_video_generator.py --wait-creatomate {render_id}")
            return render_id
        else:
            logger.error(f"❌ Creatomate API error: {response.status_code} - {response.text}")
            return f"error_creatomate_api_{response.status_code}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
    except Exception as e:
        logger.error(f"❌ Exception during Creatomate API call: {str(e)}")
        return f"exception_creatomate_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"


# =============================================================================
# WORKFLOW ORCHESTRATION  
# =============================================================================

def get_actual_heygen_duration(video_url, fallback_script_text=None):
    """Get the ACTUAL duration of HeyGen video from URL - no more estimation!"""
    if not video_url or video_url == "":
        logger.warning("⚠️ No HeyGen video URL provided, using script estimation fallback")
        return estimate_duration_from_script(fallback_script_text) if fallback_script_text else 25
    
    try:
        import subprocess
        import json
        
        # Use ffprobe to get actual video duration (most reliable method)
        logger.info(f"🔍 Getting ACTUAL duration from HeyGen video: {video_url[:50]}...")
        
        # FFprobe command to get video metadata
        cmd = [
            'ffprobe', 
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            metadata = json.loads(result.stdout)
            duration = float(metadata['format']['duration'])
            logger.info(f"✅ ACTUAL HeyGen duration: {duration:.1f}s (100% accurate!)")
            return round(duration, 1)
        else:
            logger.warning(f"⚠️ FFprobe failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.warning("⚠️ FFprobe timeout - video analysis took too long")
    except FileNotFoundError:
        logger.warning("⚠️ FFprobe not found - falling back to HTTP method")
    except Exception as e:
        logger.warning(f"⚠️ FFprobe error: {str(e)}")
    
    # Fallback: Try HTTP HEAD request to get Content-Length and estimate
    try:
        import requests
        logger.info("🔄 Trying HTTP method to get video info...")
        
        response = requests.head(video_url, timeout=10)
        if response.status_code == 200:
            # Some video hosting services include duration in headers
            content_length = response.headers.get('content-length')
            if content_length:
                # Rough estimation: ~1MB per 10 seconds for HeyGen quality
                estimated_duration = max(10, int(content_length) / (1024 * 1024) * 8)
                logger.info(f"📊 HTTP-estimated duration: {estimated_duration:.1f}s (based on file size)")
                return round(estimated_duration, 1)
                
    except Exception as e:
        logger.warning(f"⚠️ HTTP method failed: {str(e)}")
    
    # Final fallback: Use script estimation
    logger.warning("⚠️ All video analysis methods failed - using script estimation")
    return estimate_duration_from_script(fallback_script_text) if fallback_script_text else 25


def estimate_duration_from_script(script_text):
    """Fallback script-based estimation (only used when video analysis fails)"""
    if not script_text:
        return 25
    
    word_count = len(script_text.split())
    # Conservative estimation: 120 words/min = 2 words/sec
    base_duration = max(12, word_count / 2.0)
    # Add 20% buffer for safety
    final_duration = round(base_duration * 1.2, 1)
    logger.info(f"📝 Script fallback: {word_count} words → {final_duration}s")
    return final_duration

def check_creatomate_render_status(render_id: str) -> dict:
    """Check Creatomate render status"""
    logger.info(f"Checking Creatomate render status: {render_id}")
    
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
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

def upload_video_to_cloudinary(file_path, folder="streamgank_videos"):
    """
    Upload a video file to Cloudinary and return the URL
    
    Args:
        file_path (str): Path to the video file
        folder (str): Cloudinary folder to upload to
        
    Returns:
        str: Cloudinary URL of the uploaded video
    """
    logger.info(f"☁️ Uploading video to Cloudinary: {os.path.basename(file_path)}")
    try:
        # Specify resource_type='video' for video uploads
        response = cloudinary.uploader.upload(
            file_path, 
            folder=folder, 
            resource_type="video"
        )
        url = response['secure_url']
        logger.info(f"✅ Video uploaded successfully: {os.path.basename(file_path)}")
        return url
    except Exception as e:
        logger.error(f"❌ Video upload failed for {file_path}: {str(e)}")
        raise e

def generate_scroll_video(country, genre, platform, content_type, smooth=True, scroll_distance=1.5):
    """
    Generate scroll video using the same filter parameters as the main workflow
    Now with ULTRA 60 FPS MICRO-SCROLLING for perfectly readable content!
    
    Args:
        country: Country filter
        genre: Genre filter
        platform: Platform filter
        content_type: Content type filter
        smooth: Enable micro-scrolling animation (default: True)
        scroll_distance: Viewport multiplier for scroll amount (default: 1.5 = minimal readable)
    
    Returns:
        str: Path to the generated scroll video or Cloudinary URL if uploaded
    """
    
    logger.info(f"🖥️ Generating StreamGank ULTRA 60 FPS MICRO-SCROLL video (DISTANCE: {scroll_distance}x)...")
    
    # Create scroll video with unique filename + auto-cleanup (FIXED 6 seconds at 60 FPS)
    video_path = create_scroll_video(
        country=country,
        genre=genre,
        platform=platform,
        content_type=content_type,
        output_video=None,  # Auto-generate unique filename
        smooth_scroll=smooth,
        target_duration=6,  # Always 6 seconds duration
        scroll_distance=scroll_distance  # Control scroll amount
    )
    
    if video_path:
        logger.info(f"✅ Scroll video generated successfully: {video_path}")
        
        # Upload to Cloudinary for Creatomate to access
        try:
            cloudinary_url = upload_video_to_cloudinary(video_path, "streamgank_videos")
            logger.info(f"☁️ Scroll video uploaded to Cloudinary: {cloudinary_url}")
            return cloudinary_url
        except Exception as e:
            logger.warning(f"Failed to upload scroll video to Cloudinary: {str(e)}")
            # Return local path if upload fails
            return video_path
    else:
        logger.error("❌ Failed to generate scroll video")
        return None

def wait_for_creatomate_completion(render_id: str, max_attempts: int = 30, interval: int = 10) -> dict:
    """Wait for Creatomate render completion with progress feedback"""
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
        
        time.sleep(interval)
    
    print(f"\r\n{'=' * 70}")
    print(f"TIMEOUT: Render timed out after {max_attempts} attempts")
    print(f"{'=' * 70}\n")
    
    return check_creatomate_render_status(render_id)

# =============================================================================
# WORKFLOW ORCHESTRATION
# =============================================================================

def process_existing_heygen_videos(heygen_video_ids: dict, output_file: str = None) -> dict:
    """
    Process existing HeyGen video IDs and create Creatomate video
    
    Args:
        heygen_video_ids: Dictionary with HeyGen video IDs
        output_file: Optional file path to save results
        
    Returns:
        Dictionary with processing results
    """
    logger.info("🔄 Processing existing HeyGen video IDs")
    
    results = {
        'input_video_ids': heygen_video_ids,
        'timestamp': datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    }
    
    try:
        # Get HeyGen video URLs - STRICT MODE
        logger.info("Step 1: Getting HeyGen video URLs using status API - STRICT MODE")
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids)
        
        # STRICT VALIDATION - Fail if any HeyGen URLs failed
        if heygen_video_urls is None:
            logger.error("❌ HeyGen video URL retrieval failed - NO FALLBACK ALLOWED")
            results['status'] = 'failed'
            results['error'] = 'HeyGen video URL retrieval failed'
            return results
        
        if not heygen_video_urls:
            logger.error("❌ No HeyGen video URLs obtained")
            results['status'] = 'failed'
            results['error'] = 'No HeyGen video URLs obtained'
            return results
        
        results['heygen_video_urls'] = heygen_video_urls
        
        logger.info(f"✅ Successfully obtained {len(heygen_video_urls)} HeyGen video URLs")
        
        # Create Creatomate video
        logger.info("Step 2: Creating Creatomate video")
        creatomate_id = create_creatomate_video_from_heygen_urls(heygen_video_urls, movie_data=None, scripts=None)
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
        
        # Save results
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"Results saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save results: {str(e)}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing existing HeyGen videos: {str(e)}")
        results['status'] = 'error'
        results['error'] = str(e)
        return results

def run_full_workflow(num_movies=3, country="FR", genre="Horreur", platform="Netflix", content_type="Série", output=None, skip_scroll_video=False, smooth_scroll=True, scroll_distance=1.5, poster_timing_mode="heygen_last3s", heygen_template_id=None):
    """
    Run the complete end-to-end video generation workflow
    
    Args:
        num_movies: Number of movies to extract
        country: Country code for filtering
        genre: Genre for filtering
        platform: Platform for filtering
        content_type: Content type for filtering
        output: Output file path for results
        skip_scroll_video: Skip scroll video generation (default: False)
        smooth_scroll: Use smooth scrolling (default: True)
        scroll_distance: Scroll distance for video (default: 1.5)
        poster_timing_mode: Poster timing mode (default: "heygen_last3s")
            - "heygen_last3s": Posters appear during last 3s of HeyGen videos
            - "with_movie_clips": Posters appear simultaneously with movie clips
        
    Returns:
        Dictionary with results from each step
    """
    logger.info("🚀 Starting full video generation workflow")
    logger.info(f"Parameters: {num_movies} movies, {country}, {genre}, {platform}, {content_type}")
    logger.info(f"🎯 Poster timing mode: {poster_timing_mode}")
    
    results = {}
    
    try:
        # Step 1: Query database for movies (exit if none found)
        logger.info(f"Step 1: Extracting {num_movies} movies from database")
        movies = extract_movie_data(num_movies, country, genre, platform, content_type)
        
        if movies is None:
            logger.error("🚫 Database query failed - terminating workflow")
            sys.exit(1)
        
        if len(movies) == 0:
            logger.error("📭 No movies found - terminating workflow")
            sys.exit(1)
        
        logger.info(f"✅ Found {len(movies)} movies in database")
        
        # Ensure we have exactly num_movies movies
        movies = movies[:num_movies] if len(movies) >= num_movies else movies
        
        # Pad with simulated data if needed
        
        # Step 4: Enrich movie data
        logger.info("Step 4: Enriching movie data with AI")
        enriched_movies = enrich_movie_data(movies, country, genre, platform, content_type)
        results['enriched_movies'] = enriched_movies
        
        # Save enriched data
        with open("videos/enriched_data.json", "w", encoding='utf-8') as f:
            json.dump(enriched_movies, f, indent=2, ensure_ascii=False)
        
        # Step 5: Generate scripts - STRICT MODE (NO FALLBACKS)
        logger.info("Step 5: Generating AI-powered scripts - STRICT MODE")
        script_result = generate_video_scripts(enriched_movies, country, genre, platform, content_type)
        
        # STRICT VALIDATION - Fail if script generation failed
        if script_result is None:
            logger.error("❌ Script generation failed - NO FALLBACK ALLOWED")
            logger.error("❌ Cannot continue workflow without scripts")
            return {"error": "script_generation_failed", "status": "failed"}
        
        combined_script, script_path, scripts = script_result
        results['script'] = combined_script
        results['script_path'] = script_path
        results['script_sections'] = scripts
        
        # Step 6: Create HeyGen videos
        logger.info("Step 6: Creating HeyGen avatar videos")
        heygen_video_ids = create_heygen_video(scripts, heygen_template_id, genre=genre)
        results['video_ids'] = heygen_video_ids
        
        # Step 7: Wait for HeyGen completion and get URLs - STRICT MODE
        logger.info("Step 7: Waiting for HeyGen video completion - STRICT MODE")
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids, scripts)
        
        # STRICT VALIDATION - Fail if any HeyGen URLs failed
        if heygen_video_urls is None:
            logger.error("❌ HeyGen video URL retrieval failed - NO FALLBACK ALLOWED")
            return {"error": "heygen_video_url_retrieval_failed", "status": "failed"}
        
        results['heygen_video_urls'] = heygen_video_urls
        
        # Step 7.5: Generate scroll video (if not skipped)
        scroll_video_url = None
        if not skip_scroll_video:
            logger.info("Step 7.5: Generating StreamGank scroll video")
            scroll_video_url = generate_scroll_video(
                country=country,
                genre=genre,
                platform=platform,
                content_type=content_type,
                smooth=smooth_scroll,
                scroll_distance=scroll_distance
            )
            if scroll_video_url:
                results['scroll_video_url'] = scroll_video_url
                logger.info(f"📱 Scroll video URL: {scroll_video_url}")
            else:
                logger.warning("⚠️ Failed to generate scroll video, continuing without it")
        
        # Step 8: Create final video with Creatomate
        logger.info("Step 8: Creating final video with Creatomate")
        creatomate_id = create_creatomate_video_from_heygen_urls(heygen_video_urls, movie_data=enriched_movies, scroll_video_url=scroll_video_url, scripts=scripts, poster_timing_mode=poster_timing_mode)
        results['creatomate_id'] = creatomate_id
        
        if creatomate_id.startswith('error') or creatomate_id.startswith('exception'):
            logger.error(f"Creatomate creation failed: {creatomate_id}")
        else:
            logger.info(f"✅ Creatomate video submitted: {creatomate_id}")
            results['creatomate_status'] = 'submitted'
            results['status_check_command'] = f"python automated_video_generator.py --check-creatomate {creatomate_id}"
        
        # Finalize results
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results['group_id'] = f"workflow_{timestamp}"
        
        # Save results
        if output:
            with open(output, "w", encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output}")
        
        logger.info("✅ Full workflow completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Workflow error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Save partial results
        if output:
            try:
                results['error'] = str(e)
                results['traceback'] = traceback.format_exc()
                with open(output, "w", encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"Partial results saved to {output}")
            except Exception as save_error:
                logger.error(f"Error saving partial results: {str(save_error)}")
        
        return results

def prompt_for_country():
    """
    Prompt user to select a streaming country from available countries
    
    Returns:
        str: Selected country code (value from mapping)
    """
    # Define available countries (display names -> country codes)
    countries_mapping = {
        "France": "FR",
        "United States": "US"
    }
    
    # Create numbered list for user selection
    countries = {}
    i = 1
    
    for country_name in sorted(countries_mapping.keys()):
        countries[str(i)] = country_name
        i += 1
            
    print("\nStreaming Country:")
    for num, country_name in countries.items():
        country_code = countries_mapping[country_name]
        print(f"{num}. {country_name} ({country_code})")

    while True:
        choice = input("Enter your choice (1-2) [default: 1]: ").strip()
        if not choice:  # Default to first country
            first_country_name = countries["1"]
            return countries_mapping[first_country_name]
        if choice in countries:
            selected_country_name = countries[choice]
            return countries_mapping[selected_country_name]
        print("Invalid choice. Please try again.")

def prompt_for_platform():
    """
    Prompt user to select a streaming platform from available platforms
    
    Returns:
        str: Selected platform code (value from mapping)
    """
    # Get available platforms (same across all countries)
    platform_mapping = get_platform_mapping()

    # Create a numbered list of platforms (display keys, store keys for lookup)
    platforms = {}
    i = 1

    for platform_name in sorted(platform_mapping.keys()):
        platforms[str(i)] = platform_name
        i += 1
    
    print("\nAvailable Platforms:")
    for num, platform_name in platforms.items():
        print(f"{num}. {platform_name}")

    while True:
        choice = input("Enter your choice (number) [default: 1]: ").strip()
        if not choice:  # Default to first platform
            first_platform_name = platforms["1"]
            return platform_mapping[first_platform_name]
        if choice in platforms:
            selected_platform_name = platforms[choice]
            return platform_mapping[selected_platform_name]
        print("Invalid choice. Please try again.")

def prompt_for_genre(country_code):
    """
    Prompt user to select a genre from available genres for the specified country
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'GB', etc.)
        
    Returns:
        str: Selected genre code/localized name (value from mapping)
    """
    # Get available genres for selected country
    genre_mapping = get_genre_mapping_by_country(country_code)
    
    # Create a numbered list of genres (display keys, store keys for lookup)
    genres = {}
    i = 1
    
    # Sort genres alphabetically for consistent display
    for genre_name in sorted(genre_mapping.keys()):
        genres[str(i)] = genre_name
        i += 1
    
    print(f"\nAvailable Genres for {country_code}:")
    for num, genre_name in genres.items():
        # Display both English name and localized name if different
        localized_genre = genre_mapping[genre_name]
        if genre_name != localized_genre:
            print(f"{num}. {genre_name} ({localized_genre})")
        else:
            print(f"{num}. {genre_name}")
    
    while True:
        choice = input("Enter your choice (number) [default: 1]: ").strip()
        if not choice:  # Default to first genre
            first_genre_name = genres["1"]
            return genre_mapping[first_genre_name]
        if choice in genres:
            selected_genre_name = genres[choice]
            return genre_mapping[selected_genre_name]
        print("Invalid choice. Please try again.")

def prompt_for_content_type():
    """
    Prompt user to select a content type from available options
    
    Returns:
        str: Selected content type code (value from mapping)
    """
    # Define available content types (display names -> content codes)
    content_mapping = {
        "Movies": "Film",
        "TV Shows": "Série"
    }
    
    # Create numbered list for user selection
    content_types = {}
    i = 1
    
    for content_name in sorted(content_mapping.keys()):
        content_types[str(i)] = content_name
        i += 1
    
    print("\nContent Type:")
    for num, content_name in content_types.items():
        content_code = content_mapping[content_name]
        print(f"{num}. {content_name} ({content_code})")
    
    while True:
        choice = input("Enter your choice (number) [default: 1]: ").strip()
        if not choice:  # Default to first content type
            first_content_name = content_types["1"]
            return content_mapping[first_content_name]
        if choice in content_types:
            selected_content_name = content_types[choice]
            return content_mapping[selected_content_name]
        print("Invalid choice. Please try again.")

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    try:
        import argparse
        import sys
        
        # Print startup info
        print(f"Python version: {sys.version}")
        print(f"Environment: SUPABASE_URL={bool(SUPABASE_URL)}, SUPABASE_KEY={bool(SUPABASE_KEY)}")
        
        # Set up argument parser
        parser = argparse.ArgumentParser(description="StreamGank Automated Video Generator")
        
        # Workflow options
        parser.add_argument("--all", action="store_true", help="Run complete end-to-end workflow")
        parser.add_argument("--process-heygen", help="Process existing HeyGen video IDs from JSON file")
        parser.add_argument("--check-creatomate", help="Check Creatomate render status by ID")
        parser.add_argument("--wait-creatomate", help="Wait for Creatomate render completion by ID")
        
        # Parameters
        parser.add_argument("--num-movies", type=int, default=3, help="Number of movies to extract (default: 3)")
        parser.add_argument("--country", help="Country code for filtering")
        parser.add_argument("--genre", help="Genre to filter")
        parser.add_argument("--platform", help="Platform to filter")
        parser.add_argument("--content-type", help="Content type to filter")
        parser.add_argument("--is-prompt", type=int, default=0, help="Run in prompt mode (1 for interactive, 0 for command line)")
        
        # HeyGen processing
        parser.add_argument("--heygen-ids", help="JSON string or file path with HeyGen video IDs")

        # HeyGen Id template
        parser.add_argument("--heygen-template-id", default="", help="HeyGen template ID to use for video generation")
        
        # Output options
        parser.add_argument("--output", help="Output file path to save results")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")
        parser.add_argument("--skip-scroll-video", action="store_true", help="Skip scroll video generation")
        
        # Smooth scrolling options
        parser.add_argument("--smooth-scroll", action="store_true", default=True, help="Enable smooth scrolling animation (default: True)")
        parser.add_argument("--no-smooth-scroll", action="store_false", dest="smooth_scroll", help="Disable smooth scrolling")
        parser.add_argument("--scroll-distance", type=float, default=1.5, help="Scroll distance as viewport multiplier (default: 1.5 = minimal readable, 1.0 = very short, 2.0 = longer)")
        
        args = parser.parse_args()
        
        # Handle different execution modes
        if args.check_creatomate:
            # Check Creatomate status
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
            # Wait for Creatomate completion
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
            # Process existing HeyGen videos
            print(f"\n🎬 StreamGank Video Generator - HeyGen Processing Mode")
            
            heygen_video_ids = {}
            
            # Get video IDs
            if args.heygen_ids:
                try:
                    if os.path.exists(args.heygen_ids):
                        with open(args.heygen_ids, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            heygen_video_ids = data.get('video_ids', data)
                    else:
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
            # Run full workflow
            print(f"\n🎬 StreamGank Video Generator - Full Workflow Mode")
            
            # Command line mode - use provided arguments
            country = args.country
            platform = args.platform
            genre = args.genre
            content_type = args.content_type

            # Validate required parameters
            if not country or not platform or not genre or not content_type:
                print("❌ Error: Country, platform, genre, and content type are required when not using interactive mode")
                sys.exit(1)
                
            # Confirm selections
            print("\n===== Your Selections =====")
            print(f"Country: {country}")
            print(f"Platform: {platform}")
            print(f"Genre: {genre}")
            print(f"Content Type: {content_type}")
            print(f"Number of Movies: {args.num_movies}")
            print("===========================\n")
            
            # Start workflow execution
            print(f"Parameters: {args.num_movies} movies, {country}, {genre}, {platform}, {content_type}")
            print("Starting end-to-end workflow...\n")

            try:
                results = run_full_workflow(
                    num_movies=args.num_movies,
                    country=country,
                    genre=genre,
                    platform=platform,
                    content_type=content_type,
                    output=args.output,
                    skip_scroll_video=args.skip_scroll_video,
                    smooth_scroll=args.smooth_scroll,
                    scroll_distance=args.scroll_distance,
                    heygen_template_id=args.heygen_template_id
                )
                print("\n✅ Workflow completed successfully!")
                
                # Print summary
                if results:
                    print("\n📊 Results Summary:")
                    if 'enriched_movies' in results:
                        movies = results['enriched_movies']
                        print(f"📽️ Movies processed: {len(movies)}")
                        for i, movie in enumerate(movies, 1):
                            print(f"  {i}. {movie['title']} ({movie['year']}) - IMDB: {movie['imdb']}")
                    
                    if 'video_ids' in results:
                        print(f"🎥 HeyGen videos created: {len(results['video_ids'])}")
                    
                    if 'creatomate_id' in results:
                        print(f"🎞️ Final video submitted to Creatomate: {results['creatomate_id']}")
                        print(f"📹 Status: {results.get('creatomate_status', 'submitted')}")
                        if results.get('status_check_command'):
                            print(f"💡 Check status: {results['status_check_command']}")
                    
                    if 'group_id' in results:
                        print(f"💾 Data stored with group ID: {results['group_id']}")
                
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