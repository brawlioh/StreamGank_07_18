#!/usr/bin/env python3
"""
StreamGank Helper Functions

This module contains helper functions for StreamGank URL construction and country-specific mappings.
Also includes dynamic movie trailer processing for creating 10-second highlight clips.
Also includes AI content generation with dynamic language support.
"""

import os
import re
import time
import tempfile
import logging
import subprocess
from typing import Dict, List, Optional, Tuple
import yt_dlp
import cloudinary
import cloudinary.uploader
from pathlib import Path
import openai

# Set up logging
logger = logging.getLogger(__name__)

# =============================================================================
# AI CONTENT GENERATION - DYNAMIC LANGUAGE SYSTEM
# =============================================================================

def get_translations():
    """Get all translations for dynamic language support (descriptions + scripts)"""
    return {
        'en': {
            # Movie Description Generation
            'desc_expert_role': "You are a cinema expert who writes {focus} descriptions for social media.",
            'desc_task_instruction': "You ALWAYS write exactly 2 complete sentences that precisely describe the given movie/series content.",
            'desc_task_critical': "CRITICAL TASK: Write EXACTLY 2 precise sentences for \"{title}\".",
            'desc_search_context': "SEARCH CONTEXT:",
            'desc_user_search': "User search: {search}",
            'desc_found_content': "This {content_type} found{platform}{country}",
            'desc_precise_info': "PRECISE {content_type_upper} INFORMATION:",
            'desc_exact_title': "Exact title: {title}",
            'desc_imdb_score': "IMDb Score: {score}",
            'desc_year': "Year: {year}",
            'desc_actual_genres': "Actual genres: {genres}",
            'desc_mandatory_instructions': "MANDATORY INSTRUCTIONS:",
            'desc_first_sentence': "1. FIRST SENTENCE: Description of real {content_type} content (20-35 words)",
            'desc_use_genres': "   - Use actual genres: {genres}",
            'desc_mention_platform': "   - Mention{platform}{genre}",
            'desc_authentic_content': "   - Describe authentic content, not generic",
            'desc_second_sentence': "2. SECOND SENTENCE: Score + year + contextual recommendation (15-25 words)",
            'desc_exact_score': "   - Exact score: {score}",
            'desc_exact_year': "   - Exact year: {year}",
            'desc_personalized_rec': "   - Personalized recommendation for your search",
            'desc_response_instruction': "RESPONSE (2 precise sentences based on real content):",
            'content_movie': "movie",
            'content_series': "series",
            'focus_detailed': "detailed and structured",
            'focus_simple': "simple and direct", 
            'focus_creative': "creative but focused",
            
            # Script Generation
            'script_system_role': "You are a {genre} expert who creates engaging scripts for TikTok/YouTube videos. You follow timing and word count constraints PRECISELY.",
            'script_intro_prompt': "Create a brief introduction and present the first {content_type}. Keep it conversational and engaging.",
            'script_movie_prompt': "Present this {content_type} recommendation. Be concise and compelling.",
            'script_constraints': "CONSTRAINTS: Duration: {duration} | Max words: {word_count} | Max sentences: {sentence_limit}",
            'script_content_info': "Content: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Respond ONLY with the final script text.",
            'script_fallback_intro': "Hey! Check out {title} from {year} with {imdb} on IMDb.",
            'script_fallback_movie': "{title} from {year} - {imdb}."
        },
        'fr': {
            # Movie Description Generation
            'desc_expert_role': "Tu es un expert en cinéma qui écrit des descriptions {focus} pour les réseaux sociaux.",
            'desc_task_instruction': "Tu écris TOUJOURS exactement 2 phrases complètes qui décrivent précisément le contenu du film/série donné.",
            'desc_task_critical': "TÂCHE CRITIQUE: Écrire EXACTEMENT 2 phrases précises pour \"{title}\".",
            'desc_search_context': "CONTEXTE DE RECHERCHE:",
            'desc_user_search': "Recherche utilisateur: {search}",
            'desc_found_content': "Ce {content_type} trouvé{platform}{country}",
            'desc_precise_info': "INFORMATIONS PRÉCISES DU {content_type_upper}:",
            'desc_exact_title': "Titre exact: {title}",
            'desc_imdb_score': "Score IMDb: {score}",
            'desc_year': "Année: {year}",
            'desc_actual_genres': "Genres réels: {genres}",
            'desc_mandatory_instructions': "INSTRUCTIONS OBLIGATOIRES:",
            'desc_first_sentence': "1. PREMIÈRE PHRASE: Description du contenu réel du {content_type} (20-35 mots)",
            'desc_use_genres': "   - Utilisez les genres réels: {genres}",
            'desc_mention_platform': "   - Mentionnez{platform}{genre}",
            'desc_authentic_content': "   - Décrivez le contenu authentique, pas générique",
            'desc_second_sentence': "2. DEUXIÈME PHRASE: Score + année + recommandation contextuelle (15-25 mots)",
            'desc_exact_score': "   - Score exact: {score}",
            'desc_exact_year': "   - Année exacte: {year}",
            'desc_personalized_rec': "   - Recommandation personnalisée pour votre recherche",
            'desc_response_instruction': "RÉPONSE (2 phrases précises basées sur le vrai contenu):",
            'content_film': "film",
            'content_serie': "série",
            'focus_detailed': "détaillées et structurées",
            'focus_simple': "simples et directes",
            'focus_creative': "créatives mais focalisées",
            
            # Script Generation
            'script_system_role': "Tu es un expert en {genre} qui crée des scripts engageants pour des vidéos TikTok/YouTube. Tu respectes PRÉCISÉMENT les contraintes de timing et de nombre de mots.",
            'script_intro_prompt': "Crée une brève introduction et présente le premier {content_type}. Reste conversationnel et engageant.",
            'script_movie_prompt': "Présente cette recommandation de {content_type}. Sois concis et convaincant.",
            'script_constraints': "CONTRAINTES: Durée: {duration} | Max mots: {word_count} | Max phrases: {sentence_limit}",
            'script_content_info': "Contenu: {title} ({year}) - IMDb: {imdb}",
            'script_instruction': "Réponds UNIQUEMENT avec le texte du script final.",
            'script_fallback_intro': "Salut ! Découvrez {title} de {year} avec {imdb} sur IMDb.",
            'script_fallback_movie': "{title} de {year} - {imdb}."
        }
    }

def get_language_code(country):
    """Get language code from country - simple mapping"""
    return 'fr' if country == 'FR' else 'en'

def build_context_elements(country, platform, genre, lang):
    """Build context elements dynamically"""
    t = get_translations()[lang]
    
    # Country context
    if lang == 'fr':
        country_ctx = " en France" if country == 'FR' else (f" en {country}" if country else "")
        platform_ctx = f" sur {platform}" if platform else ""
    else:
        country_ctx = " in France" if country == 'FR' else (f" in {country}" if country and country != 'US' else "")
        platform_ctx = f" on {platform}" if platform else ""
    
    genre_ctx = f" {genre.lower()}" if genre else ""
    
    return {
        'country': country_ctx,
        'platform': platform_ctx,
        'genre': genre_ctx
    }

def create_dynamic_prompt(movie, search_summary, context_elements, content_type, lang):
    """Create fully dynamic prompt using translations"""
    t = get_translations()[lang]
    
    title = movie.get('title', 'Unknown')
    genres = ', '.join(movie.get('genres', ['Divers'] if lang == 'fr' else ['Various']))
    content_name = content_type or (t['content_film'] if lang == 'fr' else t['content_movie'])
    content_upper = content_name.upper()
    
    return f"""{t['desc_task_critical'].format(title=title)}

{t['desc_search_context']}
- {t['desc_user_search'].format(search=search_summary)}
- {t['desc_found_content'].format(content_type=content_name, platform=context_elements['platform'], country=context_elements['country'])}

{t['desc_precise_info'].format(content_type_upper=content_upper)}
- {t['desc_exact_title'].format(title=title)}
- {t['desc_imdb_score'].format(score=movie['imdb'])}
- {t['desc_year'].format(year=movie['year'])}
- {t['desc_actual_genres'].format(genres=genres)}

{t['desc_mandatory_instructions']}
{t['desc_first_sentence'].format(content_type=content_name)}
{t['desc_use_genres'].format(genres=genres)}
{t['desc_mention_platform'].format(platform=context_elements['platform'], genre=context_elements['genre'])}
{t['desc_authentic_content']}

{t['desc_second_sentence']}
{t['desc_exact_score'].format(score=movie['imdb'])}
{t['desc_exact_year'].format(year=movie['year'])}
{t['desc_personalized_rec']}

{t['desc_response_instruction']}"""

def generate_movie_description_simple(movie, search_summary, context_elements, content_type, lang, strategy):
    """Generate description - simplified version"""
    t = get_translations()[lang]
    
    # Get focus text dynamically
    focus_map = {
        'detailed_structured': t['focus_detailed'],
        'simple_direct': t['focus_simple'],
        'creative_flexible': t['focus_creative']
    }
    focus = focus_map.get(strategy['name'], t['focus_simple'])
    
    # Create messages
    system_msg = f"{t['desc_expert_role'].format(focus=focus)} {t['desc_task_instruction']}"
    user_prompt = create_dynamic_prompt(movie, search_summary, context_elements, content_type, lang)
    
    # Call OpenAI
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt}
        ],
        temperature=strategy['temperature'],
        max_tokens=strategy['max_tokens'],
        presence_penalty=0.1,
        frequency_penalty=0.1
    )
    
    return response.choices[0].message.content.strip()

def validate_and_fix_description(text):
    """Simple validation and fix"""
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    
    if len(sentences) >= 2 and len(text) > 50:
        return {
            'valid': True,
            'text': f"{sentences[0]}. {sentences[1]}.",
            'count': len(sentences)
        }
    else:
        return {
            'valid': False,
            'text': text,
            'count': len(sentences)
        }

def enrich_movie_data(movie_data, country=None, genre=None, platform=None, content_type=None):
    """
    Simplified movie data enrichment with dynamic language support
    """
    logger.info(f"🤖 Enriching {len(movie_data)} movies with AI descriptions")
    
    # Get language and build context once
    lang = get_language_code(country)
    search_summary = ", ".join([f"{k}: {v}" for k, v in {
        'country': country, 'genre': genre, 'platform': platform, 'type': content_type
    }.items() if v and (k != 'country' or v != 'US')])
    
    context_elements = build_context_elements(country, platform, genre, lang)
    
    # Simple strategy list
    strategies = [
        {"name": "detailed_structured", "temperature": 0.3, "max_tokens": 300},
        {"name": "simple_direct", "temperature": 0.1, "max_tokens": 250},
        {"name": "creative_flexible", "temperature": 0.5, "max_tokens": 350}
    ]
    
    # Process each movie
    for movie in movie_data:
        title = movie.get('title', 'Unknown')
        logger.info(f"🎯 Processing: {title}")
        
        description = None
        
        # Try strategies until success
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"   Strategy {i+1}/3: {strategy['name']}")
                
                # Generate description
                generated = generate_movie_description_simple(
                    movie, search_summary, context_elements, content_type, lang, strategy
                )
                
                # Validate
                result = validate_and_fix_description(generated)
                
                if result['valid']:
                    description = result['text']
                    logger.info(f"   ✅ SUCCESS: {result['count']} sentences")
                    break
                else:
                    logger.warning(f"   ⚠️ Invalid: {result['count']} sentences")
                    if i == len(strategies) - 1:
                        logger.error(f"❌ All strategies failed for {title}")
                        raise Exception(f"Failed to generate description for {title}")
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Error: {str(e)}")
                if i == len(strategies) - 1:
                    logger.error(f"❌ Critical failure for {title}")
                    raise Exception(f"Critical: Failed for {title}")
        
        # Store result
        if not description:
            raise Exception(f"No description generated for {title}")
            
        movie["enriched_description"] = description
        logger.info(f"✅ DONE: {title}")
        logger.info(f"   Text: {description}")
        
        time.sleep(0.8)  # Rate limiting
    
    logger.info("✅ All movies enriched")
    return movie_data

# =============================================================================
# SCRIPT GENERATION - DYNAMIC LANGUAGE SYSTEM
# =============================================================================

def create_script_prompt(movie, rule, content_type, genre, platform, lang):
    """Create dynamic script prompt using translations"""
    t = get_translations()[lang]
    
    title = movie.get('title', 'Unknown')
    year = movie.get('year', 'Unknown')
    imdb = movie.get('imdb', '7+')
    
    # Choose prompt type
    if rule['name'] == 'intro_movie1':
        prompt_type = t['script_intro_prompt']
    else:
        prompt_type = t['script_movie_prompt']
    
    return f"""{prompt_type.format(content_type=content_type or ('film' if lang == 'fr' else 'movie'))}

{t['script_constraints'].format(
    duration=rule['duration'],
    word_count=rule['word_count'],
    sentence_limit=rule['sentence_limit']
)}

{t['script_content_info'].format(title=title, year=year, imdb=imdb)}

{t['script_instruction']}"""

def generate_single_script(movie, rule, content_type, genre, platform, lang):
    """Generate a single script section"""
    t = get_translations()[lang]
    
    try:
        # Create system message
        system_msg = t['script_system_role'].format(genre=genre or ('divertissement' if lang == 'fr' else 'entertainment'))
        
        # Create user prompt
        user_prompt = create_script_prompt(movie, rule, content_type, genre, platform, lang)
        
        # Generate script
        max_tokens = 180 if rule["name"] == "intro_movie1" else 100
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        
        generated_script = response.choices[0].message.content.strip()
        word_count = len(generated_script.split())
        logger.info(f"✅ Generated {rule['name']}: {word_count} words")
        return generated_script
        
    except Exception as e:
        logger.error(f"❌ Script generation failed for {rule['name']}: {str(e)}")
        
        # Simple fallback
        title = movie.get('title', 'Unknown')
        year = movie.get('year', 'Unknown')
        imdb = movie.get('imdb', '7+')
        
        if rule['name'] == 'intro_movie1':
            return t['script_fallback_intro'].format(title=title, year=year, imdb=imdb)
        else:
            return t['script_fallback_movie'].format(title=title, year=year, imdb=imdb)

def generate_video_scripts(enriched_movies, country=None, genre=None, platform=None, content_type=None):
    """
    Generate scripts for video segments using dynamic language support
    """
    logger.info(f"📝 Generating scripts for {len(enriched_movies)} movies")
    
    # Get language
    lang = get_language_code(country)
    
    # Script timing rules for reels (60-90 seconds total)
    script_rules = [
        {
            "name": "intro_movie1",
            "duration": "25-30 seconds", 
            "word_count": "50-70",
            "sentence_limit": "2",
            "movie_index": 0
        },
        {
            "name": "movie2", 
            "duration": "15-20 seconds",
            "word_count": "30-45", 
            "sentence_limit": "1-2",
            "movie_index": 1
        },
        {
            "name": "movie3",
            "duration": "15-20 seconds", 
            "word_count": "30-45",
            "sentence_limit": "1-2",
            "movie_index": 2
        }
    ]
    
    # Generate scripts
    generated_scripts = {}
    
    for rule in script_rules:
        movie = enriched_movies[rule["movie_index"]]
        script = generate_single_script(movie, rule, content_type, genre, platform, lang)
        generated_scripts[rule["name"]] = script
    
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
# EXISTING STREAMGANK HELPER FUNCTIONS
# =============================================================================

def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various YouTube URL formats
    
    Args:
        url (str): YouTube URL in various formats
        
    Returns:
        str: YouTube video ID or None if not found
    """
    # Various YouTube URL patterns
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    logger.warning(f"Could not extract YouTube video ID from URL: {url}")
    return None

def download_youtube_trailer(trailer_url: str, output_dir: str = "temp_trailers") -> Optional[str]:
    """
    Download YouTube trailer video using yt-dlp
    
    Args:
        trailer_url (str): YouTube trailer URL
        output_dir (str): Directory to save downloaded video
        
    Returns:
        str: Path to downloaded video file or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract video ID for consistent naming
        video_id = extract_youtube_video_id(trailer_url)
        if not video_id:
            logger.error(f"Invalid YouTube URL: {trailer_url}")
            return None
        
        # Configure yt-dlp options for best quality video
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',  # Prefer 720p MP4
            'outtmpl': os.path.join(output_dir, f'{video_id}_trailer.%(ext)s'),
            'quiet': True,  # Reduce verbose output
            'no_warnings': True,
        }
        
        logger.info(f"🎬 Downloading YouTube trailer: {trailer_url}")
        logger.info(f"   Video ID: {video_id}")
        logger.info(f"   Output directory: {output_dir}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download the video
            ydl.download([trailer_url])
            
            # Find the downloaded file
            for file in os.listdir(output_dir):
                if video_id in file and file.endswith(('.mp4', '.webm', '.mkv')):
                    downloaded_path = os.path.join(output_dir, file)
                    logger.info(f"✅ Successfully downloaded: {downloaded_path}")
                    return downloaded_path
        
        logger.error(f"❌ Could not find downloaded file for video ID: {video_id}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error downloading YouTube trailer {trailer_url}: {str(e)}")
        return None

def extract_10_second_highlight(video_path: str, start_time: int = 30, output_dir: str = "temp_clips") -> Optional[str]:
    """
    Extract a 10-second highlight clip from a video and convert to PORTRAIT format (9:16)
    
    This function converts landscape YouTube trailers to portrait format by:
    1. Scaling the video to ensure it covers the full 1080x1920 area
    2. Cropping the center portion to create true portrait video
    
    Args:
        video_path (str): Path to the source video file (typically landscape YouTube trailer)
        start_time (int): Start time in seconds (default: 30s to skip intros)
        output_dir (str): Directory to save the portrait highlight clip
        
    Returns:
        str: Path to the extracted PORTRAIT highlight clip or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        video_name = Path(video_path).stem
        output_path = os.path.join(output_dir, f"{video_name}_10s_highlight.mp4")
        
        logger.info(f"🎞️ Extracting 5-second highlight from: {video_path}")
        logger.info(f"   Start time: {start_time}s")
        logger.info(f"   Output: {output_path}")
        
        # Use FFmpeg to extract 10-second clip with TRUE portrait conversion (crop landscape to portrait)
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,           # Input file
            '-ss', str(start_time),     # Start time
            '-t', '5',                 # Duration (5 seconds)
            '-c:v', 'libx264',         # Video codec
            '-c:a', 'aac',             # Audio codec
            '-crf', '16',              # Very high quality (16 = near-lossless for YouTube Shorts)
            '-preset', 'slow',         # Better compression efficiency
            '-profile:v', 'high',      # H.264 high profile for better quality
            '-level:v', '4.0',         # H.264 level 4.0 for high resolution
            '-movflags', '+faststart', # Optimize for web streaming
            '-pix_fmt', 'yuv420p',     # Ensure compatibility
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920', # Smart scale and center crop to portrait
            '-r', '30',                # 30 FPS for smooth playback
            '-maxrate', '3000k',       # Max bitrate for high quality
            '-bufsize', '6000k',       # Buffer size
            '-y',                       # Overwrite output file
            output_path
        ]
        
        # Run FFmpeg command
        result = subprocess.run(
            ffmpeg_cmd, 
            capture_output=True, 
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully extracted 10-second highlight: {output_path}")
            return output_path
        else:
            logger.error(f"❌ FFmpeg error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ FFmpeg timeout while processing: {video_path}")
        return None
    except Exception as e:
        logger.error(f"❌ Error extracting highlight from {video_path}: {str(e)}")
        return None

def upload_clip_to_cloudinary(clip_path: str, movie_title: str, movie_id: str = None, transform_mode: str = "youtube_shorts") -> Optional[str]:
    """
    Upload a video clip to Cloudinary with optimized settings
    
    Args:
        clip_path (str): Path to the video clip file
        movie_title (str): Movie title for naming
        movie_id (str): Movie ID for unique identification
        transform_mode (str): Transformation mode - "fit", "pad", "scale", or "auto"
        
    Returns:
        str: Cloudinary URL of uploaded clip or None if failed
    """
    try:
        # Create a clean filename from movie title
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', movie_title.lower())
        clean_title = re.sub(r'_+', '_', clean_title).strip('_')
        
        # Create unique public ID
        public_id = f"movie_clips/{clean_title}_{movie_id}_10s" if movie_id else f"movie_clips/{clean_title}_10s"
        
        logger.info(f"☁️ Uploading clip to Cloudinary: {clip_path}")
        logger.info(f"   Movie: {movie_title}")
        logger.info(f"   Public ID: {public_id}")
        logger.info(f"   Transform mode: {transform_mode}")
        
        # YouTube Shorts optimized transformation modes (9:16 portrait - 1080x1920)
        transform_modes = {
            "fit": [
                {"width": 1080, "height": 1920, "crop": "fit", "background": "black"},  # YouTube Shorts standard resolution
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "2000k"}  # High bitrate for crisp quality
            ],
            "smart_fit": [
                {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},  # Smart crop with center focus
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "2500k"},  # Even higher bitrate
                {"flags": "progressive"}  # Progressive scan for smooth playbook
            ],
            "pad": [
                {"width": 1080, "height": 1920, "crop": "pad", "background": "auto"},   # Smart padding with auto background
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"bit_rate": "2000k"}
            ],
            "scale": [
                {"width": 1080, "height": 1920, "crop": "scale"},                      # Scale to fit (may distort)
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"bit_rate": "1800k"}
            ],
            "youtube_shorts": [
                {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},  # YouTube Shorts optimized
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "3000k"},  # Premium bitrate for YouTube Shorts quality
                {"flags": "progressive"},
                {"audio_codec": "aac"},
                {"audio_frequency": 48000}  # High quality audio
            ]
        }
        
        # Get the transformation based on mode
        transformation = transform_modes.get(transform_mode, transform_modes["youtube_shorts"])
        
        # Upload to Cloudinary with video optimization (using selected transformation)
        upload_result = cloudinary.uploader.upload(
            clip_path,
            resource_type="video",
            public_id=public_id,
            folder="movie_clips",
            overwrite=True,
            quality="auto",              # Automatic quality optimization
            format="mp4",               # Ensure MP4 format
            video_codec="h264",         # Use H.264 codec for compatibility
            audio_codec="aac",          # Use AAC audio codec
            transformation=transformation
        )
        
        cloudinary_url = upload_result.get('secure_url')
        logger.info(f"✅ Successfully uploaded to Cloudinary: {cloudinary_url}")
        
        return cloudinary_url
        
    except Exception as e:
        logger.error(f"❌ Error uploading {clip_path} to Cloudinary: {str(e)}")
        return None

def process_movie_trailers_to_clips(movie_data: List[Dict], max_movies: int = 3, transform_mode: str = "fit") -> Dict[str, str]:
    """
    Process movie trailers to create 10-second highlight clips and upload to Cloudinary
    
    Args:
        movie_data (List[Dict]): List of movie data dictionaries with trailer_url
        max_movies (int): Maximum number of movies to process
        transform_mode (str): Transformation mode - "fit", "pad", "scale", or "auto"
        
    Returns:
        Dict[str, str]: Dictionary mapping movie titles to Cloudinary clip URLs
    """
    clip_urls = {}
    temp_dirs = ["temp_trailers", "temp_clips"]
    
    try:
        # Create temporary directories
        for temp_dir in temp_dirs:
            os.makedirs(temp_dir, exist_ok=True)
        
        logger.info(f"🎬 PROCESSING MOVIE TRAILERS TO CLIPS")
        logger.info(f"📋 Processing {min(len(movie_data), max_movies)} movies")
        
        # Process each movie (up to max_movies)
        for i, movie in enumerate(movie_data[:max_movies]):
            movie_title = movie.get('title', f'Movie_{i+1}')
            movie_id = str(movie.get('id', i+1))
            trailer_url = movie.get('trailer_url', '')
            
            logger.info(f"🎯 Processing Movie {i+1}: {movie_title}")
            logger.info(f"   Movie ID: {movie_id}")
            logger.info(f"   Trailer URL: {trailer_url}")
            
            if not trailer_url:
                logger.warning(f"⚠️ No trailer URL for {movie_title}, skipping...")
                continue
            
            # Step 1: Download YouTube trailer
            downloaded_trailer = download_youtube_trailer(trailer_url)
            if not downloaded_trailer:
                logger.error(f"❌ Failed to download trailer for {movie_title}")
                continue
            
            # Step 2: Extract 10-second highlight
            highlight_clip = extract_10_second_highlight(downloaded_trailer)
            if not highlight_clip:
                logger.error(f"❌ Failed to extract highlight for {movie_title}")
                continue
            
            # Step 3: Upload to Cloudinary
            cloudinary_url = upload_clip_to_cloudinary(highlight_clip, movie_title, movie_id, transform_mode)
            if cloudinary_url:
                clip_urls[movie_title] = cloudinary_url
                logger.info(f"✅ Successfully processed {movie_title}: {cloudinary_url}")
            else:
                logger.error(f"❌ Failed to upload clip for {movie_title}")
        
        logger.info(f"🏁 PROCESSING COMPLETE: {len(clip_urls)}/{min(len(movie_data), max_movies)} clips processed")
        
        return clip_urls
        
    except Exception as e:
        logger.error(f"❌ Error in process_movie_trailers_to_clips: {str(e)}")
        return clip_urls
        
    finally:
        # Clean up temporary files
        try:
            import shutil
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.info(f"🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Could not clean up temporary files: {str(e)}")

# === EXISTING STREAMGANK HELPER FUNCTIONS ===

def get_genre_mapping_by_country(country_code):
    """
    Get genre mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'DE', etc.)
        
    Returns:
        dict: Mapping from database genre names to StreamGank URL genre parameters
        
    Example:
        >>> mapping = get_genre_mapping_by_country('FR')
        >>> mapping.get('Horreur')  # Returns 'Horreur'
        >>> mapping.get('Horror')   # Returns 'Horreur' (cross-language support)
    """
    
    # Base English genre mapping (default for most countries)
    english_genres = {
        'Action & Adventure': 'Action%20%26%20Adventure',
        'Action': 'Action%20%26%20Adventure', 
        'Adventure': 'Action%20%26%20Adventure',
        'Animation': 'Animation',
        'Comedy': 'Comedy',
        'Crime': 'Crime',
        'Documentary': 'Documentary',
        'Drama': 'Drama',
        'Drame': 'Drama',  # Handle French input
        'Fantasy': 'Fantasy',
        'Fantastique': 'Fantasy',  # Handle French input
        'History': 'History',
        'Histoire': 'History',  # Handle French input
        'Horror': 'Horror',
        'Horreur': 'Horror',  # Handle French input
        'Kids & Family': 'Kids%20%26%20Family',
        'Family': 'Kids%20%26%20Family',
        'Made in Europe': 'Made%20in%20Europe',
        'Music & Musical': 'Music%20%26%20Musical',
        'Musical': 'Music%20%26%20Musical',
        'Mystery & Thriller': 'Mystery%20%26%20Thriller',
        'Mystery': 'Mystery%20%26%20Thriller',
        'Thriller': 'Mystery%20%26%20Thriller',
        'Reality TV': 'Reality%20TV',
        'Romance': 'Romance',
        'Science-Fiction': 'Science-Fiction',
        'Sci-Fi': 'Science-Fiction',
        'Sport': 'Sport',
        'War & Military': 'War%20%26%20Military',
        'War': 'War%20%26%20Military',
        'Military': 'War%20%26%20Military',
        'Western': 'Western'
    }
    
    # French genre mapping for StreamGank France
    french_genres = {
        # French database genres → French StreamGank URL parameters
        'Action & Aventure': 'Action%20%26%20Aventure',
        'Action': 'Action%20%26%20Aventure',
        'Aventure': 'Action%20%26%20Aventure',
        'Animation': 'Animation',
        'Comédie': 'Comédie',
        'Comedy': 'Comédie',  # Handle English input
        'Comédie Romantique': 'Comédie%20Romantique',
        'Romantic Comedy': 'Comédie%20Romantique',
        'Crime & Thriller': 'Crime%20%26%20Thriller',
        'Crime': 'Crime%20%26%20Thriller',
        'Thriller': 'Crime%20%26%20Thriller',
        'Documentaire': 'Documentaire',
        'Documentary': 'Documentaire',  # Handle English input
        'Drame': 'Drame',
        'Drama': 'Drame',  # Handle English input
        'Fantastique': 'Fantastique',
        'Fantasy': 'Fantastique',  # Handle English input
        'Film de guerre': 'Film%20de%20guerre',
        'War': 'Film%20de%20guerre',
        'War & Military': 'Film%20de%20guerre',
        'Histoire': 'Histoire',
        'History': 'Histoire',  # Handle English input
        'Horreur': 'Horreur',
        'Horror': 'Horreur',  # Handle English input
        'Musique & Comédie Musicale': 'Musique%20%26%20Comédie%20Musicale',
        'Music & Musical': 'Musique%20%26%20Comédie%20Musicale',
        'Musical': 'Musique%20%26%20Comédie%20Musicale',
        'Mystère & Thriller': 'Mystère%20%26%20Thriller',
        'Mystery & Thriller': 'Mystère%20%26%20Thriller',
        'Mystery': 'Mystère%20%26%20Thriller',
        'Pour enfants': 'Pour%20enfants',
        'Kids & Family': 'Pour%20enfants',
        'Family': 'Pour%20enfants',
        'Reality TV': 'Reality%20TV',
        'Romance': 'Romance',
        'Réalisé en Europe': 'Réalisé%20en%20Europe',
        'Made in Europe': 'Réalisé%20en%20Europe',
        'Science-Fiction': 'Science-Fiction',
        'Sci-Fi': 'Science-Fiction',
        'Sport & Fitness': 'Sport%20%26%20Fitness',
        'Sport': 'Sport%20%26%20Fitness',
        'Fitness': 'Sport%20%26%20Fitness',
        'Western': 'Western'
    }
    
    # Country-specific genre mappings
    country_mappings = {
        'FR': french_genres,
        'US': english_genres,
        'GB': english_genres,
        'UK': english_genres,
        'CA': english_genres,
        'AU': english_genres,
        # Add more countries as needed
        # 'DE': german_genres,  # Could add German mapping later
        # 'ES': spanish_genres,  # Could add Spanish mapping later
        # 'IT': italian_genres,  # Could add Italian mapping later
    }
    
    # Return country-specific mapping or default to English
    return country_mappings.get(country_code, english_genres)


def get_platform_mapping_by_country(country_code):
    """
    Get platform mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'DE', etc.)
        
    Returns:
        dict: Mapping from database platform names to StreamGank URL platform parameters
        
    Example:
        >>> mapping = get_platform_mapping_by_country('FR')
        >>> mapping.get('Canal+')  # Returns 'canal' (French-specific)
        >>> mapping.get('Netflix') # Returns 'netflix' (universal)
    """
    
    # Base platform mapping (consistent across most countries)
    base_platforms = {
        'Netflix': 'netflix',
        'Disney+': 'disney',
        'Disney Plus': 'disney',
        'Amazon Prime': 'amazon',
        'Prime Video': 'amazon',
        'Amazon Prime Video': 'amazon',
        'HBO Max': 'hbo',
        'HBO': 'hbo',
        'Apple TV+': 'apple',
        'Apple TV': 'apple',
        'Hulu': 'hulu',
        'Paramount+': 'paramount',
        'Paramount Plus': 'paramount'
    }
    
    # Country-specific platform mappings (can extend for localized platform names)
    french_platforms = {
        **base_platforms,
        # Add French-specific platform names
        'Canal+': 'canal',
        'France TV': 'francetv',
        'MyCanal': 'canal'
    }
    
    country_mappings = {
        'FR': french_platforms,
        'US': base_platforms,
        'GB': base_platforms,
        'UK': base_platforms,
        'CA': base_platforms,
        'AU': base_platforms,
    }
    
    return country_mappings.get(country_code, base_platforms)


def get_content_type_mapping_by_country(country_code):
    """
    Get content type mapping dictionary based on country code for StreamGank URL parameters
    
    Args:
        country_code (str): Country code (e.g., 'FR', 'US', 'DE', etc.)
        
    Returns:
        dict: Mapping from database content types to StreamGank URL type parameters
        
    Example:
        >>> mapping = get_content_type_mapping_by_country('FR')
        >>> mapping.get('Série')    # Returns 'Serie'
        >>> mapping.get('Émission') # Returns 'Serie' (French TV show term)
    """
    
    # Base content type mapping
    english_types = {
        'Film': 'Film',
        'Movie': 'Film',
        'Série': 'Serie',
        'Series': 'Serie',
        'TV Show': 'Serie',
        'TV Series': 'Serie'
    }
    
    # French content type mapping
    french_types = {
        'Film': 'Film',
        'Movie': 'Film',
        'Série': 'Serie',
        'Series': 'Serie',
        'TV Show': 'Serie',
        'TV Series': 'Serie',
        'Émission': 'Serie'  # French TV show term
    }
    
    country_mappings = {
        'FR': french_types,
        'US': english_types,
        'GB': english_types,
        'UK': english_types,
        'CA': english_types,
        'AU': english_types,
    }
    
    return country_mappings.get(country_code, english_types)


def build_streamgank_url(country=None, genre=None, platform=None, content_type=None):
    """
    Build a complete StreamGank URL with localized parameters based on country
    
    Args:
        country (str): Country code for localization
        genre (str): Genre to filter by
        platform (str): Platform to filter by  
        content_type (str): Content type to filter by
        
    Returns:
        str: Complete StreamGank URL with properly encoded parameters
        
    Example:
        >>> url = build_streamgank_url('FR', 'Horreur', 'Netflix', 'Série')
        >>> print(url)
        https://streamgank.com/?country=FR&genres=Horreur&platforms=netflix&type=Serie
    """
    
    base_url = "https://streamgank.com/?"
    url_params = []
    
    if country:
        url_params.append(f"country={country}")
    
    if genre:
        # Use country-specific genre mapping
        genre_mapping = get_genre_mapping_by_country(country)
        streamgank_genre = genre_mapping.get(genre, genre)
        url_params.append(f"genres={streamgank_genre}")
    
    if platform:
        # Use country-specific platform mapping
        platform_mapping = get_platform_mapping_by_country(country)
        streamgank_platform = platform_mapping.get(platform, platform.lower())
        url_params.append(f"platforms={streamgank_platform}")
    
    if content_type:
        # Use country-specific content type mapping
        type_mapping = get_content_type_mapping_by_country(country)
        streamgank_type = type_mapping.get(content_type, content_type)
        url_params.append(f"type={streamgank_type}")
    
    # Construct final URL
    if url_params:
        return base_url + "&".join(url_params)
    else:
        return "https://streamgank.com/"  # Default homepage if no params


def get_supported_countries():
    """
    Get list of supported country codes
    
    Returns:
        list: List of supported country codes
        
    Example:
        >>> countries = get_supported_countries()
        >>> print(countries)
        ['FR', 'US', 'GB', 'UK', 'CA', 'AU']
    """
    
    return ['FR', 'US', 'GB', 'UK', 'CA', 'AU']


def get_available_genres_for_country(country_code):
    """
    Get all available genres for a specific country
    
    Args:
        country_code (str): Country code
        
    Returns:
        list: List of available genre names for the country
        
    Example:
        >>> genres = get_available_genres_for_country('FR')
        >>> print(len(genres))  # Should show French + English genre names
    """
    
    mapping = get_genre_mapping_by_country(country_code)
    return list(mapping.keys())


def get_available_platforms_for_country(country_code):
    """
    Get all available platforms for a specific country
    
    Args:
        country_code (str): Country code
        
    Returns:
        list: List of available platform names for the country
    """
    
    mapping = get_platform_mapping_by_country(country_code)
    return list(mapping.keys())


# For backward compatibility and convenience
def get_all_mappings_for_country(country_code):
    """
    Get all mappings (genres, platforms, content types) for a country in one call
    
    Args:
        country_code (str): Country code
        
    Returns:
        dict: Dictionary containing all mappings
        
    Example:
        >>> mappings = get_all_mappings_for_country('FR')
        >>> print(mappings.keys())
        dict_keys(['genres', 'platforms', 'content_types'])
    """
    
    return {
        'genres': get_genre_mapping_by_country(country_code),
        'platforms': get_platform_mapping_by_country(country_code),
        'content_types': get_content_type_mapping_by_country(country_code)
    } 