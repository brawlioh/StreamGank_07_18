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
    python3 automated_video_generator.py # User will be prompted interactively for these settings when the script runs
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

# Import StreamGang helper functions
from streamgank_helpers import (
    get_genre_mapping_by_country,
    get_platform_mapping_by_country, 
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

def create_heygen_video(script_data, use_template=True, template_id="7fb75067718944ac8f02e661c2c61522"):
    """
    Create videos with HeyGen API
    
    Args:
        script_data: Dictionary containing scripts
        use_template: Whether to use template-based approach
        template_id: HeyGen template ID
    
    Returns:
        Dictionary of video IDs
    """
    logger.info(f"🎬 Creating HeyGen videos")
    
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
    Get HeyGen video URLs for direct use with Creatomate
    
    Args:
        heygen_video_ids: Dictionary of HeyGen video IDs
        scripts: Dictionary of script data for time estimation
        
    Returns:
        Dictionary with video URLs ready for Creatomate
    """
    logger.info(f"🔗 Getting HeyGen video URLs for {len(heygen_video_ids)} videos")
    
    video_urls = {}
    fallback_url = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    
    for key, video_id in heygen_video_ids.items():
        if not video_id or video_id.startswith('placeholder'):
            logger.debug(f"Skipping placeholder ID for {key}")
            continue
        
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
            logger.info(f"✅ Got URL for {key}")
        else:
            # Use fallback
            if status_result.get('video_url'):
                video_urls[key] = status_result['video_url']
                logger.warning(f"⚠️ Using incomplete URL for {key}")
            else:
                video_urls[key] = fallback_url
                logger.warning(f"⚠️ Using fallback URL for {key}")
    
    logger.info(f"✅ Obtained {len(video_urls)} video URLs")
    return video_urls

# =============================================================================
# CREATOMATE VIDEO COMPOSITION
# =============================================================================

def create_creatomate_video_from_heygen_urls(heygen_video_urls: dict, movie_data: List[Dict[str, Any]] = None, scroll_video_url: str = None) -> str:
    """
    Create final video with Creatomate using HeyGen video URLs
    
    Args:
        heygen_video_urls: Dictionary with HeyGen video URLs
        movie_data: List of movie data dictionaries
        
    Returns:
        Creatomate video ID or error message
    """
    logger.info("🎞️ Creating Creatomate video using HeyGen URLs")
    
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        logger.error("CREATOMATE_API_KEY not found")
        return f"error_no_api_key_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Get movie assets
    if movie_data and len(movie_data) >= 3:
        logger.info("🎬 Using dynamic movie assets from movie_data")
        
        # Create enhanced movie poster cards with metadata
        logger.info("🎨 Creating ENHANCED MOVIE POSTERS with metadata overlays")
        logger.info("📱 Style: Professional TikTok/Instagram Reels format with aspect ratio preservation")
        logger.info("🖼️ Features: Platform badges, genres, IMDb scores, runtime, year")
        enhanced_posters = create_enhanced_movie_posters(movie_data, max_movies=3)
        
        # Movie covers (enhanced posters with metadata)
        movie_covers = []
        fallback_covers = [
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
            "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png"
        ]
        
        for i, movie in enumerate(movie_data[:3]):
            movie_title = movie.get('title', f'Movie_{i+1}')
            
            if movie_title in enhanced_posters:
                movie_covers.append(enhanced_posters[movie_title])
                logger.info(f"   Movie {i+1} cover: {movie_title} -> ENHANCED POSTER WITH METADATA")
            else:
                movie_covers.append(fallback_covers[i])
                logger.warning(f"   Movie {i+1} cover: {movie_title} -> FALLBACK POSTER")
        
        # Dynamic movie clips
        logger.info("🎞️ Processing dynamic CINEMATIC PORTRAIT clips from trailers")
        logger.info("📱 Using Gaussian blur backgrounds + enhanced quality for TikTok/Instagram Reels")
        logger.info("🎬 Format: 1080x1920 with premium settings")
        dynamic_clips = process_movie_trailers_to_clips(movie_data, max_movies=3, transform_mode="youtube_shorts")
        
        # Create clips array
        movie_clips = []
        fallback_clips = [
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751353401/the_last_of_us_zljllt.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751355284/Stranger_Things_uyxt3a.mp4",
            "https://res.cloudinary.com/dodod8s0v/video/upload/v1751356566/The_Haunting_of_Hill_House_jhztq4.mp4"
        ]
        
        for i, movie in enumerate(movie_data[:3]):
            movie_title = movie.get('title', f'Movie_{i+1}')
            
            if movie_title in dynamic_clips:
                movie_clips.append(dynamic_clips[movie_title])
                logger.info(f"   Movie {i+1} clip: {movie_title} -> DYNAMIC CLIP")
            else:
                movie_clips.append(fallback_clips[i])
                logger.warning(f"   Movie {i+1} clip: {movie_title} -> FALLBACK CLIP")
        
        logger.info(f"✅ Dynamic assets prepared: {len(movie_covers)} enhanced posters, {len(movie_clips)} clips")
        logger.info(f"🎨 Enhanced posters include: Platform badges, genres, IMDb scores, metadata")
        
    else:
        # Default assets
        logger.warning("⚠️ Using default movie assets")
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
    
    # Get HeyGen URLs with fallbacks
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
    
    # Create composition (YouTube Shorts format: 1080x1920)
    source = {
        "width": 1080,
        "height": 1920,
        "elements": [
            # Intro image (1 second)
            {
                "fit": "cover",
                "type": "image",
                "track": 1,
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1753263646/streamGank_intro_cwefmt.jpg",
                "duration": 1,
                "animations": [
                    {
                        "type": "fade",
                        "fade_out": True,
                        "duration": 1     # 1-second fade-out
                    }
                ]
            },
            # StreamGank banner text top
            {
                "name": "stream",
                "type": "text",
                "track": 5,
                "time": 2,
                "x": "16.8633%",
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
            {
                "name": "slogan",
                "type": "text",
                "track": 6,
                "time": 2,
                "x": "15.8467%",
                "y": "6.1282%",
                "x_anchor": "0%",
                "y_anchor": "0%",
                "text": "AMBUSH THE BEST VOD TOGETHER",
                "font_family": "Noto Sans",
                "font_weight": "700",
                "font_size": "4 vmin",
                "fill_color": "#ffffff",
                "shadow_color": "rgba(0,0,0,0.8)",
                "shadow_blur": "2 vmin"
            },
            {
                "name": "Gank",
                "type": "text",
                "track": 7,
                "time": 2,
                "x": "54.7589%",
                "y": "0%",
                "x_anchor": "0%",
                "y_anchor": "0%",
                "text": "Gank",
                "font_family": "Noto Sans",
                "font_weight": "700",
                "font_size": "10 vmin",
                "fill_color": "#ffffff",
                "shadow_color": "rgba(0,0,0,0.8)"
            },
            
            # HeyGen intro + movie1
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_intro,
                "animations": [
                    
                    {
                        "type": "fade",
                        "fade_out": True,
                        "duration": 1     # 1-second fade-out
                    }
                ]
            },
            
            # Scroll video overlay (full screen with fade-in/out animation)
            *([scroll_video_url and {
                "fit": "cover",          # Use "cover" to fill the screen
                "type": "video",
                "track": 3,              # Use track 3 to overlay on top of everything
                "source": scroll_video_url,
                "time": 4,               # Start at 4-seconds mark
                "duration": 6,           # Play for 6 seconds
                "width": "100%",         # Full screen width
                "height": "100%",        # Full screen height
                "x": "50%",              # Center position
                "y": "50%",              # Center position
                "animations": [           # Add fade-in and fade-out animations
                    {
                        "type": "fade",
                        "fade_in": True,
                        "duration": 1     # 1-second fade-in
                    },
                    {
                        "type": "fade",
                        "fade_out": True,
                        "duration": 1     # 1-second fade-out
                    }
                ],
            }] or []),
            # Movie 1 assets (enhanced poster with metadata)
            {
                "fit": "contain",  # Preserve aspect ratio of enhanced poster
                "type": "image", 
                "track": 1,
                "source": movie_covers[0],
                "duration": 3
            },
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": movie_clips[0],
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie2
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_movie2,
                "animations": [
                    {
                        "type": "fade",
                        "fade_out": True,
                        "duration": 1     # 1-second fade-out
                    }
                ]
            },
            # Movie 2 assets (enhanced poster with metadata)
            {
                "fit": "contain",  # Preserve aspect ratio of enhanced poster
                "type": "image",
                "track": 1,
                "source": movie_covers[1],
                "duration": 3
            },
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": movie_clips[1],
                "trim_end": 8,
                "trim_start": 0
            },
            # HeyGen movie3
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_movie3,
                "animations": [
                    {
                        "type": "fade",
                        "fade_out": True,
                        "duration": 1     # 1-second fade-out
                    }
                ]
            },
            # Movie 3 assets (enhanced poster with metadata)
            {
                "fit": "contain",  # Preserve aspect ratio of enhanced poster
                "type": "image",
                "track": 1,
                "source": movie_covers[2],
                "duration": 3
            },
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": movie_clips[2],
                "trim_end": 8,
                "trim_start": 0
            },
            # Outro
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
    
    # Create payload
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

def generate_scroll_video(country, genre, platform, content_type, smooth=True, scroll_distance=1.0):
    """
    Generate a scroll video for StreamGank
    
    Args:
        country: Country code
        genre: Genre filter
        platform: Platform filter
        content_type: Content type filter
        smooth: Whether to use smooth scrolling
        scroll_distance: Scroll distance multiplier (how far to scroll)
        
    Returns:
        str: URL of uploaded video or None if failed
    """
    from archive.create_scroll_video import create_scroll_video
    
    logger.info(f"💻 Generating StreamGank ULTRA 60 FPS MICRO-SCROLL video (DISTANCE: {scroll_distance}x)...")
    
    # Set default values for None parameters to prevent errors
    safe_country = country if country is not None else "Any"
    safe_genre = genre if genre is not None else "Any"
    safe_platform = platform if platform is not None else "Any"
    safe_content_type = content_type if content_type is not None else "Any"
    
    # Create scroll video with unique filename + auto-cleanup (FIXED 6 seconds at 60 FPS)
    video_path = create_scroll_video(
        country=safe_country,
        genre=safe_genre,
        platform=safe_platform,
        content_type=safe_content_type,
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
        # Get HeyGen video URLs
        logger.info("Step 1: Getting HeyGen video URLs using status API")
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids)
        results['heygen_video_urls'] = heygen_video_urls
        
        if not heygen_video_urls:
            logger.error("No HeyGen video URLs obtained")
            results['status'] = 'failed'
            results['error'] = 'No HeyGen video URLs obtained'
            return results
        
        logger.info(f"✅ Successfully obtained {len(heygen_video_urls)} HeyGen video URLs")
        
        # Create Creatomate video
        logger.info("Step 2: Creating Creatomate video")
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

def run_full_workflow(num_movies=3, country=None, genre=None, platform=None, content_type=None, output=None, skip_scroll_video=False, smooth_scroll=True, scroll_distance=1.5):
    """
    Run the complete end-to-end workflow
    
    Args:
        num_movies (int): Number of movies to extract
        country (str): Country code for filtering
        genre (str): Genre to filter by
        platform (str): Platform to filter by
        content_type (str): Content type to filter by
        output (str): Output file path
        skip_scroll_video (bool): Skip scroll video generation
        smooth_scroll (bool): Use smooth scrolling for screenshots
        scroll_distance (float): Scroll distance multiplier
    
    Returns:
        dict: Results dictionary or None if failed
    """
    logger.info(f"🚀 Starting full video generation workflow")
    logger.info(f"Parameters: {num_movies} movies, {country}, {genre}, {platform}, {content_type}")
    
    # Generate a unique group ID for this run
    group_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        'status': 'starting',
        'group_id': group_id
    }
    
    # Step 1: Extract movies from database
    logger.info(f"Step 1: Extracting {num_movies} movies from database")
    movies = extract_movie_data(num_movies, country, genre, platform, content_type)
    
    # If no movies found, try some fallback options
    if not movies:
        fallback_attempts = [
            # Try without genre
            {"message": "No movies found with specified genre. Trying without genre filter...", 
             "params": {"num_movies": num_movies, "country": country, "genre": None, "platform": platform, "content_type": content_type}},
            # Try without content_type
            {"message": "Still no results. Trying without content type filter...", 
             "params": {"num_movies": num_movies, "country": country, "genre": genre, "platform": platform, "content_type": None}},
            # Try popular platforms if specified platform has no results
            {"message": "Still no results. Trying with Netflix as platform...", 
             "params": {"num_movies": num_movies, "country": country, "genre": genre, "platform": "Netflix", "content_type": content_type}},
            # Try without platform
            {"message": "Still no results. Trying without platform filter...", 
             "params": {"num_movies": num_movies, "country": country, "genre": genre, "platform": None, "content_type": content_type}},
            # Last resort - just get top movies for country
            {"message": "Last attempt: Getting top movies for selected country...", 
             "params": {"num_movies": num_movies, "country": country, "genre": None, "platform": None, "content_type": None}}
        ]
        
        for attempt in fallback_attempts:
            if platform != "Netflix" and attempt["params"]["platform"] == "Netflix":
                # Skip the Netflix fallback if we're already trying Netflix
                continue
                
            logger.warning(attempt["message"])
            print(f"⚠️ {attempt['message']}")
            
            fallback_params = attempt["params"]
            movies = extract_movie_data(**fallback_params)
            
            if movies:
                # We found movies with this fallback, update our parameters to match what worked
                country = fallback_params["country"]
                genre = fallback_params["genre"]
                platform = fallback_params["platform"]
                content_type = fallback_params["content_type"]
                
                print(f"✅ Found movies using modified filters: Country={country}, Genre={genre if genre else 'Any'}, "
                      f"Platform={platform if platform else 'Any'}, Content Type={content_type if content_type else 'Any'}")
                break
    
    try:
        # If still no movies found after all fallbacks, terminate workflow
        if not movies:
            logger.error(f"🚫 Database query failed with all fallback attempts - terminating workflow")
            return None
            
        if len(movies) == 0:
            logger.error("📭 No movies found - terminating workflow")
            sys.exit(1)
            
        logger.info(f"✅ Found {len(movies)} movies in database")
        
        # Step 2: Capture screenshots
        logger.info("Step 2: Capturing StreamGank screenshots")
        screenshot_paths = capture_streamgank_screenshots(country, genre, platform, content_type)
        results['screenshots'] = screenshot_paths
        
        # Step 3: Upload screenshots
        logger.info("Step 3: Uploading screenshots to Cloudinary")
        cloudinary_urls = upload_to_cloudinary(screenshot_paths)
        results['cloudinary_urls'] = {f"screenshot_{i}": url for i, url in enumerate(cloudinary_urls)}
        
        # Ensure we have exactly num_movies movies
        movies = movies[:num_movies] if len(movies) >= num_movies else movies
        
        # Pad with simulated data if needed
        if len(movies) < num_movies:
            logger.warning(f"Only found {len(movies)} movies, padding with simulated data")
            simulated = _simulate_movie_data(num_movies - len(movies))
            movies.extend(simulated[:num_movies - len(movies)])
        
        # Step 4: Enrich movie data
        logger.info("Step 4: Enriching movie data with AI")
        enriched_movies = enrich_movie_data(movies, country, genre, platform, content_type)
        results['enriched_movies'] = enriched_movies
        
        # Save enriched data
        with open("videos/enriched_data.json", "w", encoding='utf-8') as f:
            json.dump(enriched_movies, f, indent=2, ensure_ascii=False)
        
        # Step 5: Generate scripts
        logger.info("Step 5: Generating AI-powered scripts")
        combined_script, script_path, scripts = generate_video_scripts(enriched_movies, country, genre, platform, content_type)
        results['script'] = combined_script
        results['script_path'] = script_path
        results['script_sections'] = scripts
        
        # Step 6: Create HeyGen videos
        logger.info("Step 6: Creating HeyGen avatar videos")
        heygen_video_ids = create_heygen_video(scripts)
        results['video_ids'] = heygen_video_ids
        
        # Step 7: Wait for HeyGen completion and get URLs
        logger.info("Step 7: Waiting for HeyGen video completion")
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids, scripts)
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
        creatomate_id = create_creatomate_video_from_heygen_urls(heygen_video_urls, movie_data=enriched_movies, scroll_video_url=scroll_video_url)
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
                logger.info(f"Partial results saved to: {output}")
            except Exception as save_error:
                logger.error(f"Error saving partial results: {str(save_error)}")
        
        return results

# =============================================================================
# MAIN FUNCTION
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Print startup info
    print(f"Python version: {sys.version}")
    print(f"Environment: SUPABASE_URL={bool(SUPABASE_URL)}, SUPABASE_KEY={bool(SUPABASE_KEY)}")
    
    try:
        
        # Check if any command line arguments were provided for maintenance tasks
        if len(sys.argv) > 1:
            import argparse
            
            # Set up argument parser for maintenance tasks only
            parser = argparse.ArgumentParser(description="StreamGank Automated Video Generator - Maintenance Mode")
            parser.add_argument("--check-creatomate", help="Check Creatomate render status by ID")
            parser.add_argument("--wait-creatomate", help="Wait for Creatomate render completion by ID")
            parser.add_argument("--process-heygen", help="Process existing HeyGen video IDs from JSON file")
            parser.add_argument("--heygen-ids", help="JSON string or file path with HeyGen video IDs")
            parser.add_argument("--output", help="Output file path to save results")
            
            args = parser.parse_args()
            
            # Handle maintenance tasks
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
                sys.exit(0)
                    
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
                sys.exit(0)
                    
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
                sys.exit(0)
        
        # Interactive prompt functions
        def prompt_for_country():
            # Define available countries
            countries = {
                "1": "FR",  # France
                "2": "US",  # United States
                "3": "GB",  # Great Britain
                "4": "CA",  # Canada
                "5": "AU"   # Australia
            }
            
            print("\nStreaming Country:")
            for num, code in countries.items():
                country_name = {
                    "FR": "France",
                    "US": "United States",
                    "GB": "United Kingdom",
                    "CA": "Canada",
                    "AU": "Australia"
                }.get(code, code)
                print(f"{num}. {country_name} ({code})")
            
            while True:
                choice = input("Enter your choice (1-5) [default: 1 for France]: ").strip()
                if not choice:  # Default to France
                    return "FR"
                if choice in countries:
                    return countries[choice]
                print("Invalid choice. Please try again.")
        
        def prompt_for_platform(country_code):
            # Get available platforms for selected country
            from streamgank_helpers import get_platform_mapping_by_country
            platform_mapping = get_platform_mapping_by_country(country_code)
            
            # Create a numbered list of platforms
            platforms = {}
            i = 1
            for platform_name in sorted(set(platform_mapping.keys())):
                platforms[str(i)] = platform_name
                i += 1
            
            print("\nPlatform:")
            for num, platform in platforms.items():
                print(f"{num}. {platform}")
            
            while True:
                choice = input("Enter your choice (number) [default: Netflix]: ").strip()
                if not choice:  # Default to Netflix
                    return "Netflix"
                if choice in platforms:
                    return platforms[choice]
                print("Invalid choice. Please try again.")
        
        def prompt_for_genre(country_code):
            # Get available genres for selected country
            from streamgank_helpers import get_genre_mapping_by_country
            genre_mapping = get_genre_mapping_by_country(country_code)
            
            # Create a numbered list of genres (unique and sorted)
            genres = {}
            i = 1
            
            # Get unique genre display names (not URL parameters)
            unique_genres = sorted(set(key for key in genre_mapping.keys() 
                                      if not key.startswith('%') and '&' not in key and ' ' not in key))
            
            for genre_name in unique_genres:
                genres[str(i)] = genre_name
                i += 1
            
            print("\nGenre:")
            for num, genre in genres.items():
                print(f"{num}. {genre}")
            
            while True:
                choice = input("Enter your choice (number) [default: Horror/Horreur]: ").strip()
                if not choice:  # Default based on country
                    return "Horreur" if country_code == "FR" else "Horror"
                if choice in genres:
                    # Return the selected genre
                    selected_genre = genres[choice]
                    
                    # Check if we need to convert between French/English genre names
                    # Common translations that might need conversion
                    translations = {
                        "Horror": "Horreur",
                        "Horreur": "Horror",
                        "Action": "Action",  # Same in both languages
                        "Comedy": "Comédie",
                        "Comédie": "Comedy",
                        "Drama": "Drame",
                        "Drame": "Drama",
                        "Sci-Fi": "Science-Fiction",
                        "Science-Fiction": "Sci-Fi"
                    }
                    
                    # If we selected a French genre but are in English region (or vice versa)
                    # try to convert it to the appropriate language
                    if country_code != "FR" and selected_genre in translations:
                        # Convert French genre to English equivalent if needed
                        if selected_genre in ["Horreur", "Comédie", "Drame", "Science-Fiction"]:
                            logger.info(f"Converting genre '{selected_genre}' to '{translations[selected_genre]}' for country {country_code}")
                            return translations[selected_genre]
                    elif country_code == "FR" and selected_genre in translations:
                        # Convert English genre to French equivalent if needed
                        if selected_genre in ["Horror", "Comedy", "Drama", "Sci-Fi"]:
                            logger.info(f"Converting genre '{selected_genre}' to '{translations[selected_genre]}' for country {country_code}")
                            return translations[selected_genre]
                    
                    return selected_genre
                
                print("Invalid choice. Please try again.")
        
        def prompt_for_content_type(country_code):
            # Get content types for selected country
            from streamgank_helpers import get_content_type_mapping_by_country
            content_type_mapping = get_content_type_mapping_by_country(country_code)
            
            # Create a numbered list of content types (unique)
            content_types = {}
            i = 1
            
            # Remove duplicates and mappings
            unique_types = []
            for key in content_type_mapping.keys():
                if key not in unique_types and key in ["Film", "Movie", "Série", "Series"]:
                    unique_types.append(key)
            
            # Sort and create numbered mapping
            for type_name in sorted(unique_types):
                content_types[str(i)] = type_name
                i += 1
            
            print("\nContent Type:")
            for num, content_type in content_types.items():
                print(f"{num}. {content_type}")
            
            while True:
                choice = input("Enter your choice (number) [default: Series/Série]: ").strip()
                if not choice:  # Default based on country
                    return "Série" if country_code == "FR" else "Series"
                if choice in content_types:
                    return content_types[choice]
                print("Invalid choice. Please try again.")
        
        # Get user inputs through interactive prompts
        print("\n===== StreamGank Automated Video Generator =====\n")
        print("Please select options for your video generation:")
        
        country = prompt_for_country()
        platform = prompt_for_platform(country)
        genre = prompt_for_genre(country)
        content_type = prompt_for_content_type(country)
        num_movies = 3  # Default number of movies
        
        # Allow customizing number of movies
        while True:
            movie_count = input("\nNumber of movies to include (1-5) [default: 3]: ").strip()
            if not movie_count:  # Default
                break
            try:
                num_movies = int(movie_count)
                if 1 <= num_movies <= 5:
                    break
                print("Please enter a number between 1 and 5.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Confirm selections
        print("\n===== Your Selections =====")
        print(f"Country: {country}")
        print(f"Platform: {platform}")
        print(f"Genre: {genre}")
        print(f"Content Type: {content_type}")
        print(f"Number of Movies: {num_movies}")
        print("===========================\n")
        
        # Run full workflow with interactive inputs
        print(f"\n🎬 StreamGank Video Generator - Full Workflow Mode")
        print(f"Parameters: {num_movies} movies, {country}, {genre}, {platform}, {content_type}")
        print("Starting end-to-end workflow...\n")
        
        # Set default values for workflow options
        output = None
        skip_scroll_video = False
        smooth_scroll = True
        scroll_distance = 1.5
        
        try:
            results = run_full_workflow(
                num_movies=num_movies,
                country=country,
                genre=genre,
                platform=platform,
                content_type=content_type,
                output=output,
                skip_scroll_video=skip_scroll_video,
                smooth_scroll=smooth_scroll,
                scroll_distance=scroll_distance
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