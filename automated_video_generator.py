#!/usr/bin/env python3
"""
StreamGank Automated Video Generator

A streamlined video generation pipeline that:
1. Captures screenshots from StreamGank
2. Extracts movie data from Supabase
3. Generates AI-powered scripts
4. Creates HeyGen avatar videos
5. Composes final videos with Creatomate

Author: StreamGang Team
Version: 2.0 (Refactored)
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
    process_movie_trailers_to_clips
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
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dodod8s0v")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "589374432754798")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "iwOZJxSJ9SIE47BwVBsvQdYAfsg")

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
# AI CONTENT GENERATION
# =============================================================================

def enrich_movie_data(movie_data, country=None, genre=None, platform=None, content_type=None):
    """
    Enrich movie data with AI-generated descriptions
    
    Args:
        movie_data: List of movie data dictionaries
        country (str): Country code for language context
        genre (str): Genre for specialized prompts
        platform (str): Platform for context
        content_type (str): Film/Série for terminology
        
    Returns:
        List of enriched movie data dictionaries
    """
    logger.info(f"🤖 Enriching {len(movie_data)} movies with AI descriptions")
    
    # Language mapping
    language_map = {
        'FR': {'language': 'French', 'code': 'fr'},
        'US': {'language': 'English', 'code': 'en'},
        'UK': {'language': 'English', 'code': 'en'},
        'CA': {'language': 'English', 'code': 'en'},
        'DE': {'language': 'German', 'code': 'de'},
        'ES': {'language': 'Spanish', 'code': 'es'},
        'IT': {'language': 'Italian', 'code': 'it'},
    }
    
    lang_info = language_map.get(country or 'US', {'language': 'English', 'code': 'en'})
    is_french = lang_info['code'] == 'fr'
    
    # Process each movie
    for movie in movie_data:
        try:
            # Create system message
            if is_french:
                system_message = f"Tu es un expert en {genre or 'divertissement'} qui crée du contenu court et engageant pour les réseaux sociaux."
            else:
                system_message = f"You are a {genre or 'entertainment'} expert who creates short and engaging content for social media."
            
            # Create prompt
            if is_french:
                prompt = f"""
                Génère une description courte et engageante pour le {content_type or 'film'} "{movie['title']}" pour une vidéo TikTok/YouTube.
                
                Informations:
                - Titre: {movie['title']}
                - Score IMDb: {movie['imdb']}
                - Année: {movie['year']}
                - Genres: {', '.join(movie.get('genres', ['Divers']))}
                
                Critères:
                1. 1-2 phrases maximum (TRÈS COURT)
                2. Ton décontracté qui accroche un public jeune
                3. Mentionne le score IMDb et l'année
                4. Ne révèle pas trop l'intrigue
                
                Réponds UNIQUEMENT avec le texte enrichi, sans préambule.
                """
            else:
                prompt = f"""
                Generate a short and engaging description for the {content_type or 'movie'} "{movie['title']}" for a TikTok/YouTube video.
                
                Information:
                - Title: {movie['title']}
                - IMDb Score: {movie['imdb']}
                - Year: {movie['year']}
                - Genres: {', '.join(movie.get('genres', ['Various']))}
                
                Criteria:
                1. 1-2 sentences maximum (VERY SHORT)
                2. Casual tone that hooks young audiences
                3. Mention the IMDb score and year
                4. Don't spoil too much of the plot
                
                Respond ONLY with the enriched text, no preamble.
                """
            
            # Call OpenAI
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            enriched_description = response.choices[0].message.content.strip()
            movie["enriched_description"] = enriched_description
            logger.info(f"✅ Enriched: {movie['title']}")
            
        except Exception as e:
            logger.error(f"❌ Enrichment failed for {movie['title']}: {str(e)}")
            # Fallback description
            if is_french:
                movie["enriched_description"] = f"Ce {content_type or 'film'} de {movie['year']} avec un score IMDb de {movie['imdb']} vous captivera !"
            else:
                movie["enriched_description"] = f"This {content_type or 'movie'} from {movie['year']} with an IMDb score of {movie['imdb']} will captivate you!"
    
    logger.info("✅ Movie data enrichment completed")
    return movie_data

def generate_script(enriched_movies, cloudinary_urls, country=None, genre=None, platform=None, content_type=None):
    """
    Generate scripts for reels-style videos (60-90 seconds total)
    
    Args:
        enriched_movies: List of enriched movie data
        cloudinary_urls: Dictionary of image URLs
        country (str): Country code for language context
        genre (str): Genre for specialized terminology
        platform (str): Platform for context
        content_type (str): Film/Série for terminology
        
    Returns:
        tuple: (combined_script, script_path, scripts_dict)
    """
    logger.info(f"📝 Generating scripts for {len(enriched_movies)} movies")
    
    # Language configuration
    language_map = {
        'FR': {'language': 'French', 'code': 'fr'},
        'US': {'language': 'English', 'code': 'en'},
        'UK': {'language': 'English', 'code': 'en'},
        'CA': {'language': 'English', 'code': 'en'},
    }
    
    lang_info = language_map.get(country or 'US', {'language': 'English', 'code': 'en'})
    is_french = lang_info['code'] == 'fr'
    
    # Script timing rules for reels (based on 2.5 words/second)
    script_rules = [
        {
            "name": "intro_movie1",
            "duration": "35-40 seconds", 
            "word_count": "85-100 words",
            "movie_index": 0,
            "type": "introduction + first movie highlight"
        },
        {
            "name": "movie2", 
            "duration": "15-25 seconds",
            "word_count": "40-60 words", 
            "movie_index": 1,
            "type": "second movie mention"
        },
        {
            "name": "movie3",
            "duration": "15-25 seconds", 
            "word_count": "40-60 words",
            "movie_index": 2, 
            "type": "third movie mention"
        }
    ]
    
    logger.info(f"⏱️ Using reels timing rules:")
    for rule in script_rules:
        logger.info(f"   {rule['name']}: {rule['duration']} ({rule['word_count']})")
    
    generated_scripts = {}
    
    # Generate each script section
    for rule in script_rules:
        movie = enriched_movies[rule["movie_index"]]
        
        try:
            # System message
            if is_french:
                system_message = f"Tu es un expert en {genre or 'divertissement'} qui crée des scripts engageants pour des vidéos TikTok/YouTube. Tu respectes PRÉCISÉMENT les contraintes de timing et de nombre de mots."
            else:
                system_message = f"You are a {genre or 'entertainment'} expert who creates engaging scripts for TikTok/YouTube videos. You follow timing and word count constraints PRECISELY."
            
            # Create prompt based on script type
            if is_french:
                if rule["name"] == "intro_movie1":
                    prompt = f"""
                    Crée un script TRÈS COURT pour un REEL de 60-90 secondes{f' sur {platform}' if platform else ''}.
                    
                    CONTRAINTES CRITIQUES - REELS:
                    - Durée: {rule['duration']} (MAXIMUM {rule['word_count']} - PAS UN MOT DE PLUS!)
                    - Format: REEL court, punchy, accrocher immédiatement
                    
                    CONTENU:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    STRUCTURE ULTRA-COURTE:
                    1. Accroche rapide (5-10 mots)
                    2. {movie['title']} + score + 1 phrase d'impact
                    3. Teaser rapide des 2 autres
                    
                    RAPPEL: {rule['word_count']} MAXIMUM!
                    Réponds UNIQUEMENT avec le script final.
                    """
                else:
                    prompt = f"""
                    Crée un script ULTRA-COURT pour un REEL rapide{f' sur {platform}' if platform else ''}.
                    
                    CONTRAINTES EXTRÊMES - REELS:
                    - Durée: {rule['duration']} (MAXIMUM {rule['word_count']} - AUCUN MOT EN PLUS!)
                    
                    CONTENU:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    STRUCTURE MINIMAL:
                    1. Transition (1-2 mots: "Ensuite" ou "Enfin")
                    2. Titre + score + 1 mot-clé d'impact
                    
                    IMPÉRATIF: {rule['word_count']} MAXIMUM!
                    Réponds UNIQUEMENT avec le script final.
                    """
            else:
                if rule["name"] == "intro_movie1":
                    prompt = f"""
                    Create a SUPER SHORT script for a 60-90 second REEL{f' on {platform}' if platform else ''}.
                    
                    CRITICAL CONSTRAINTS - REELS:
                    - Duration: {rule['duration']} (MAXIMUM {rule['word_count']} - NOT ONE WORD MORE!)
                    - Format: Short reel, punchy, hook immediately
                    
                    CONTENT:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    ULTRA-SHORT STRUCTURE:
                    1. Quick hook (5-10 words)
                    2. {movie['title']} + score + 1 impact phrase
                    3. Quick tease of 2 others
                    
                    REMINDER: {rule['word_count']} MAXIMUM!
                    Respond ONLY with the final script.
                    """
                else:
                    prompt = f"""
                    Create an ULTRA-SHORT script for a fast REEL{f' on {platform}' if platform else ''}.
                    
                    EXTREME CONSTRAINTS - REELS:
                    - Duration: {rule['duration']} (MAXIMUM {rule['word_count']} - NO EXTRA WORDS!)
                    
                    CONTENT:
                    - {movie['title']} ({movie['year']}) - {movie.get('imdb', '7+')}
                    
                    MINIMAL STRUCTURE:
                    1. Transition (1-2 words: "Next" or "Finally")
                    2. Title + score + 1 impact keyword
                    
                    IMPERATIVE: {rule['word_count']} MAXIMUM!
                    Respond ONLY with the final script.
                    """
            
            # Generate script
            max_tokens = 180 if rule["name"] == "intro_movie1" else 100
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=max_tokens
            )
            
            generated_script = response.choices[0].message.content.strip()
            generated_scripts[rule["name"]] = generated_script
            
            word_count = len(generated_script.split())
            logger.info(f"✅ Generated {rule['name']}: {word_count} words")
            
        except Exception as e:
            logger.error(f"❌ Script generation failed for {rule['name']}: {str(e)}")
            
            # Fallback script
            if is_french:
                fallback = f"Découvrez {movie['title']} de {movie['year']}, un {content_type or 'film'} exceptionnel avec {movie.get('imdb', '7+')} sur IMDb."
            else:
                fallback = f"Discover {movie['title']} from {movie['year']}, an exceptional {content_type or 'movie'} with {movie.get('imdb', '7+')} on IMDb."
            
            generated_scripts[rule["name"]] = fallback
    
    # Create scripts dictionary
    scripts = {
        "intro_movie1": {
            "text": generated_scripts.get("intro_movie1", "Script generation failed."),
            "path": "videos/script_intro_movie1.txt"
        },
        "movie2": {
            "text": generated_scripts.get("movie2", "Script generation failed."),
            "path": "videos/script_movie2.txt"
        },
        "movie3": {
            "text": generated_scripts.get("movie3", "Script generation failed."),
            "path": "videos/script_movie3.txt"
        }
    }
    
    # Save individual scripts
    for key, script_data in scripts.items():
        try:
            with open(script_data["path"], "w", encoding='utf-8') as f:
                f.write(script_data["text"])
        except Exception as e:
            logger.error(f"Failed to save script {key}: {str(e)}")
    
    # Create combined script
    combined_script = "\n\n".join([scripts[key]["text"] for key in ["intro_movie1", "movie2", "movie3"]])
    combined_path = "videos/combined_script.txt"
    
    try:
        with open(combined_path, "w", encoding='utf-8') as f:
            f.write(combined_script)
    except Exception as e:
        logger.error(f"Failed to save combined script: {str(e)}")
    
    logger.info("✅ Script generation completed")
    return combined_script, combined_path, scripts

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

def create_creatomate_video_from_heygen_urls(heygen_video_urls: dict, movie_data: List[Dict[str, Any]] = None) -> str:
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
        
        # Movie covers
        movie_covers = []
        for i, movie in enumerate(movie_data[:3]):
            cover_url = movie.get('poster_url') or movie.get('cloudinary_poster_url') 
            if cover_url:
                movie_covers.append(cover_url)
                logger.info(f"   Movie {i+1} cover: {movie['title']} -> {cover_url}")
            else:
                # Fallback covers
                fallback_covers = [
                    "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373016/1_TheLastOfUs_w5l6o7.png",
                    "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373201/2_Strangerthings_bidszb.png",
                    "https://res.cloudinary.com/dodod8s0v/image/upload/v1751373245/3_Thehaunting_grxuop.png"
                ]
                movie_covers.append(fallback_covers[i])
                logger.warning(f"   Movie {i+1} cover: Using fallback for {movie['title']}")
        
        # Dynamic movie clips
        logger.info("🎞️ Processing dynamic movie clips from trailers")
        logger.info("📱 Using YouTube Shorts quality: 1080x1920 with premium settings")
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
        
        logger.info(f"✅ Dynamic assets prepared: {len(movie_covers)} covers, {len(movie_clips)} clips")
        
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
                "duration": 1
            },
            # StreamGank banner (persists throughout video)
            {
                "id": "streamgank-banner",
                "name": "streamgank_logo",
                "type": "image",
                "y": "6.25%",
                "height": "12.5%",
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1752587056/streamgankbanner_uempzb.jpg",
                "time_offset": 1,
                "duration": "99%"
            },
            # HeyGen intro + movie1
            {
                "fit": "cover",
                "type": "video",
                "track": 1,
                "source": heygen_intro
            },
            # Movie 1 assets
            {
                "fit": "cover",
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
                "source": heygen_movie2
            },
            # Movie 2 assets
            {
                "fit": "cover",
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
                "source": heygen_movie3
            },
            # Movie 3 assets
            {
                "fit": "cover",
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

def run_full_workflow(num_movies=3, country="FR", genre="Horreur", platform="Netflix", content_type="Série", output=None):
    """
    Run the complete end-to-end video generation workflow
    
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
    logger.info("🚀 Starting full video generation workflow")
    logger.info(f"Parameters: {num_movies} movies, {country}, {genre}, {platform}, {content_type}")
    
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
        combined_script, script_path, scripts = generate_script(enriched_movies, results['cloudinary_urls'], country, genre, platform, content_type)
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
        
        # Step 8: Create final video with Creatomate
        logger.info("Step 8: Creating final video with Creatomate")
        creatomate_id = create_creatomate_video_from_heygen_urls(heygen_video_urls, movie_data=enriched_movies)
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
        parser.add_argument("--country", default="FR", help="Country code for filtering (default: FR)")
        parser.add_argument("--genre", default="Horreur", help="Genre to filter by (default: Horreur)")
        parser.add_argument("--platform", default="Netflix", help="Platform to filter by (default: Netflix)")
        parser.add_argument("--content-type", default="Série", help="Content type to filter by (default: Série)")
        
        # HeyGen processing
        parser.add_argument("--heygen-ids", help="JSON string or file path with HeyGen video IDs")
        
        # Output options
        parser.add_argument("--output", help="Output file path to save results")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")
        
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
            if not any([args.country != "FR", args.genre != "Horreur", args.platform != "Netflix", 
                        args.content_type != "Série", args.num_movies != 3, args.debug, args.output]):
                args.all = True
            
            print(f"\n🎬 StreamGank Video Generator - Full Workflow Mode")
            print(f"Parameters: {args.num_movies} movies, {args.country}, {args.genre}, {args.platform}, {args.content_type}")
            print("Starting end-to-end workflow...\n")
            
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
