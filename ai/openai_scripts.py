"""
StreamGank AI Script Generator with Multi-Model Fallback

This module handles AI-powered script generation with intelligent fallback system:
- Primary: OpenAI GPT models for high-quality viral scripts
- Fallback: Google Gemini when OpenAI fails/quota exceeded
- Hook sentence generation (10-18 words, viral language)
- Intro script generation (collection introduction)
- Genre-specific prompt customization
- Batch processing for multiple movies
- Robust error handling and retry logic
- Script validation and optimization

Version: 3.0.0 - Professional Multi-Model Fallback System
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Any
import openai
from openai import OpenAI

from config.settings import get_api_config
from utils.formatters import sanitize_script_text, format_hook_sentence, format_intro_text
from utils.validators import validate_environment_variables
from ai.prompt_templates import get_hook_prompt_template, get_intro_prompt_template, build_context_prompt
from ai.script_manager import validate_script_content, process_script_text

logger = logging.getLogger(__name__)

# Import Gemini fallback client
try:
    from ai.gemini_client import GeminiClient
    GEMINI_FALLBACK_AVAILABLE = True
except ImportError:
    GEMINI_FALLBACK_AVAILABLE = False
    logger.warning("⚠️ Gemini fallback not available. Install with: pip install google-generativeai")

# =============================================================================
# OPENAI CLIENT MANAGEMENT
# =============================================================================

def _get_openai_client() -> Optional[OpenAI]:
    """
    Get configured OpenAI client instance.
    
    Returns:
        OpenAI: Configured client or None if API key missing
    """
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ Missing OpenAI API key (OPENAI_API_KEY)")
            return None
        
        client = OpenAI(api_key=api_key)
        logger.debug("✅ OpenAI client initialized")
        return client
        
    except Exception as e:
        logger.error(f"❌ Error initializing OpenAI client: {str(e)}")
        return None

# =============================================================================
# MAIN SCRIPT GENERATION FUNCTIONS
# =============================================================================

def generate_video_scripts(raw_movies: List[Dict], 
                          country: str = "US",
                          genre: Optional[str] = None, 
                          platform: Optional[str] = None, 
                          content_type: Optional[str] = None) -> Tuple[str, str, Dict]:
    """
    Generate complete video scripts including intro and movie hooks.
    
    STRICT MODE: All script generation must succeed. No fallbacks used.
    Process stops immediately if any script generation or processing fails.
    
    This is the main function for script generation that creates:
    1. Collection intro script (15-25 words)
    2. Individual movie hook scripts (10-18 words each)
    3. Combined script for final video
    
    Args:
        raw_movies (List[Dict]): Raw movie data from database (REQUIRED - exactly 3 movies)
        country (str): Country code for localization
        genre (str): Genre for context and customization (REQUIRED)
        platform (str): Platform name for optimization (REQUIRED)
        content_type (str): Content type for targeting (REQUIRED)
        
    Returns:
        Tuple[str, str, Dict]: (combined_script, script_path, individual_scripts)
        
    Raises:
        ValueError: If required data is missing or invalid
        RuntimeError: If script generation fails
    """
    logger.info(f"🚀 DIRECT SCRIPT GENERATION STRICT MODE: {len(raw_movies)} movies (no fallbacks)")
    logger.info(f"   Genre: {genre}, Platform: {platform}, Content: {content_type}")
    
    # STRICT: Validate inputs
    if not raw_movies or len(raw_movies) != 3:
        raise ValueError("❌ CRITICAL: Exactly 3 movies required for script generation")
    
    if not genre or not platform or not content_type:
        raise ValueError("❌ CRITICAL: Genre, platform, and content_type are required")
    
    # STRICT: Validate OpenAI configuration
    client = _get_openai_client()
    if not client:
        raise RuntimeError("❌ CRITICAL: OpenAI client not available - cannot generate scripts")
    
    # STRICT: Get API configuration
    api_config = get_api_config('openai')
    if not api_config:
        raise RuntimeError("❌ CRITICAL: OpenAI API configuration not available")
    
    generated_scripts = {}
    
    # STRICT: Step 1 - Generate intro script (must succeed)
    logger.info("🎬 Generating collection intro script (STRICT mode)...")
    intro_script = generate_intro_script(genre, platform, content_type, api_config)
    
    if not intro_script:
        raise RuntimeError("❌ CRITICAL: Failed to generate intro script - cannot proceed")
    
    generated_scripts["intro"] = intro_script
    logger.info(f"✅ Intro: {intro_script}")
    
    # STRICT: Step 2 - Generate movie hook scripts (all must succeed)
    logger.info(f"🎣 Generating {len(raw_movies)} movie hook scripts (STRICT mode)...")
    
    for i, movie in enumerate(raw_movies[:3]):  # Exactly 3 movies
        movie_name = f"movie{i+1}"
        movie_title = movie.get('title', f'Movie {i+1}')
        
        # Validate movie data
        if not movie.get('title'):
            raise ValueError(f"❌ CRITICAL: Movie {i+1} missing title - cannot generate hook")
        
        logger.info(f"🎯 Movie {i+1}: {movie_title} (STRICT mode)")
        
        # Generate hook for this movie (must succeed)
        hook_script = generate_hook_script(movie, genre, platform, api_config)
        
        if not hook_script:
            raise RuntimeError(f"❌ CRITICAL: Failed to generate hook for {movie_title} - cannot proceed")
        
        generated_scripts[movie_name] = hook_script
        logger.info(f"✅ Hook: {hook_script}")
    
    # STRICT: Must have exactly 4 scripts (intro + 3 movies)
    expected_scripts = 4
    if len(generated_scripts) != expected_scripts:
        raise RuntimeError(f"❌ CRITICAL: Expected {expected_scripts} scripts, got {len(generated_scripts)}")
    
    # COMBINE intro with movie1 for the first HeyGen video
    # HeyGen Video 1: Intro + Movie 1 hook
    # HeyGen Video 2: Movie 2 hook only  
    # HeyGen Video 3: Movie 3 hook only
    if "intro" in generated_scripts and "movie1" in generated_scripts:
        # Combine intro + movie1 into a single script
        combined_movie1 = f"{generated_scripts['intro']} {generated_scripts['movie1']}"
        generated_scripts["movie1"] = combined_movie1
        logger.info(f"✅ INTRO INTEGRATED: Combined intro + movie1 script")
        logger.info(f"   📝 Combined script: {combined_movie1}")
    
    # STRICT: Step 3 - Process scripts (all must succeed)
    logger.info("🔧 Processing scripts (STRICT mode)...")
    processed_scripts = {}
    for name, script in generated_scripts.items():
        # Skip intro for HeyGen processing - it's now combined with movie1
        if name == "intro":
            processed_scripts[name] = process_script_text(script)
            continue
            
        processed_script = process_script_text(script)
        if not processed_script:
            raise RuntimeError(f"❌ CRITICAL: Script processing failed for {name} - cannot proceed")
        
        processed_scripts[name] = processed_script
    
    # STRICT: Step 4 - Create combined script (must succeed)
    logger.info("🔗 Creating combined script (STRICT mode)...")
    script_order = ["intro", "movie1", "movie2", "movie3"]
    combined_parts = []
    
    for name in script_order:
        if name not in processed_scripts:
            raise RuntimeError(f"❌ CRITICAL: Missing processed script for {name}")
        combined_parts.append(processed_scripts[name])
    
    combined_script = "\n\n".join(combined_parts)
    
    if not combined_script or len(combined_script.strip()) == 0:
        raise RuntimeError("❌ CRITICAL: Combined script is empty - cannot proceed")
    
    # STRICT: Step 5 - Save scripts to files (must succeed)
    logger.info("💾 Saving scripts to files (STRICT mode)...")
    script_path = save_scripts_to_files(processed_scripts, combined_script)
    
    if not script_path:
        raise RuntimeError("❌ CRITICAL: Failed to save scripts to files")
    
    # Create HeyGen scripts (excluding intro - it's now combined with movie1)
    heygen_scripts = {name: script for name, script in processed_scripts.items() if name != "intro"}
    
    # Final validation
    word_count = len(combined_script.split())
    if word_count < 10:  # Minimum reasonable word count
        raise RuntimeError(f"❌ CRITICAL: Combined script too short ({word_count} words)")
    
    logger.info("🚀 DIRECT SCRIPT GENERATION COMPLETED SUCCESSFULLY!")
    logger.info(f"📊 {len(heygen_scripts)} HeyGen videos (movie1 includes intro hook) | {word_count} total words")
    
    return (combined_script, script_path, heygen_scripts)


def generate_hook_script(movie_data: Dict, 
                        genre: Optional[str] = None,
                        platform: Optional[str] = None,
                        api_config: Optional[Dict] = None) -> Optional[str]:
    """
    Generate a viral hook script for a single movie.
    
    Args:
        movie_data (Dict): Movie information
        genre (str): Genre for context
        platform (str): Target platform
        api_config (Dict): OpenAI API configuration
        
    Returns:
        str: Generated hook script or None if failed
    """
    try:
        client = _get_openai_client()
        if not client:
            return None
        
        # Get configuration
        if not api_config:
            api_config = get_api_config('openai')
        
        # Build prompt
        system_prompt, user_prompt = get_hook_prompt_template(movie_data, genre, platform)
        
        logger.debug(f"🎣 Generating hook for: {movie_data.get('title', 'Unknown')}")
        
        # Generate hook using OpenAI
        response = client.chat.completions.create(
            model=api_config.get('model', 'gpt-4'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=api_config.get('temperature', 0.9),
            max_tokens=api_config.get('hook_max_tokens', 40)
        )
        
        # Extract and clean hook
        hook = response.choices[0].message.content.strip()
        hook = sanitize_script_text(hook)
        hook = format_hook_sentence(hook, max_words=18)
        
        # Validate hook
        if validate_script_content(hook, script_type='hook'):
            return hook
        else:
            error_msg = f"Hook validation failed: {hook}"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
    except Exception as e:
        error_msg = f"Error generating hook script: {str(e)}"
        logger.error(f"❌ STRICT MODE: {error_msg}")
        raise RuntimeError(error_msg)


def generate_intro_script(genre: Optional[str] = None,
                         platform: Optional[str] = None,
                         content_type: Optional[str] = None,
                         api_config: Optional[Dict] = None) -> Optional[str]:
    """
    Generate an intro script for the video collection.
    
    Args:
        genre (str): Genre for context
        platform (str): Target platform
        content_type (str): Content type
        api_config (Dict): OpenAI API configuration
        
    Returns:
        str: Generated intro script or None if failed
    """
    try:
        client = _get_openai_client()
        if not client:
            return None
        
        # Get configuration
        if not api_config:
            api_config = get_api_config('openai')
        
        # Build prompt
        system_prompt, user_prompt = get_intro_prompt_template(genre, platform, content_type)
        
        logger.debug(f"🎬 Generating intro for: {genre} on {platform}")
        
        # Generate intro using OpenAI
        response = client.chat.completions.create(
            model=api_config.get('model', 'gpt-4'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=api_config.get('temperature', 0.8),
            max_tokens=api_config.get('intro_max_tokens', 60)
        )
        
        # Extract and clean intro
        intro = response.choices[0].message.content.strip()
        intro = sanitize_script_text(intro)
        intro = format_intro_text(intro, max_words=25)
        
        # Validate intro
        if validate_script_content(intro, script_type='intro'):
            return intro
        else:
            error_msg = f"Intro validation failed: {intro}"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
    except Exception as e:
        error_msg = f"Error generating intro script: {str(e)}"
        logger.error(f"❌ STRICT MODE: {error_msg}")
        raise RuntimeError(error_msg)

# =============================================================================
# BATCH PROCESSING FUNCTIONS
# =============================================================================

def generate_scripts_batch(movie_batches: List[List[Dict]], 
                          config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate scripts for multiple movie batches.
    
    Args:
        movie_batches (List[List[Dict]]): List of movie batches
        config (Dict): Configuration parameters
        
    Returns:
        Dict[str, Any]: Batch processing results
    """
    results = {
        'successful_batches': 0,
        'failed_batches': 0,
        'total_scripts': 0,
        'batch_results': {},
        'errors': []
    }
    
    try:
        logger.info(f"📦 BATCH SCRIPT GENERATION: {len(movie_batches)} batches")
        
        for i, movies in enumerate(movie_batches):
            batch_id = f"batch_{i+1}"
            logger.info(f"🎯 Processing {batch_id}: {len(movies)} movies")
            
            try:
                # Generate scripts for this batch
                batch_result = generate_video_scripts(
                    movies,
                    country=config.get('country', 'US'),
                    genre=config.get('genre'),
                    platform=config.get('platform'),
                    content_type=config.get('content_type')
                )
                
                if batch_result:
                    combined_script, script_path, individual_scripts = batch_result
                    
                    results['batch_results'][batch_id] = {
                        'status': 'success',
                        'combined_script': combined_script,
                        'script_path': script_path,
                        'individual_scripts': individual_scripts,
                        'script_count': len(individual_scripts)
                    }
                    
                    results['successful_batches'] += 1
                    results['total_scripts'] += len(individual_scripts)
                    
                    logger.info(f"✅ {batch_id} completed: {len(individual_scripts)} scripts")
                    
                else:
                    results['batch_results'][batch_id] = {
                        'status': 'failed',
                        'error': 'Script generation failed'
                    }
                    results['failed_batches'] += 1
                    results['errors'].append(f"{batch_id}: Script generation failed")
                    
                    logger.error(f"❌ {batch_id} failed")
                
            except Exception as e:
                error_msg = f"{batch_id}: {str(e)}"
                results['batch_results'][batch_id] = {
                    'status': 'error',
                    'error': error_msg
                }
                results['failed_batches'] += 1
                results['errors'].append(error_msg)
                
                logger.error(f"❌ {batch_id} error: {str(e)}")
        
        logger.info(f"🏁 BATCH PROCESSING COMPLETE:")
        logger.info(f"   ✅ Successful: {results['successful_batches']}")
        logger.info(f"   ❌ Failed: {results['failed_batches']}")
        logger.info(f"   📊 Total scripts: {results['total_scripts']}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in batch script generation: {str(e)}")
        results['errors'].append(f"Batch processing error: {str(e)}")
        return results

# =============================================================================
# SCRIPT OPTIMIZATION FUNCTIONS
# =============================================================================

def optimize_script_for_platform(script: str, platform: str = "TikTok") -> str:
    """
    Optimize script content for specific platform requirements.
    
    Args:
        script (str): Original script content
        platform (str): Target platform
        
    Returns:
        str: Optimized script
    """
    try:
        if not script:
            return script
        
        # Platform-specific optimizations
        if platform.lower() in ['tiktok', 'instagram', 'shorts']:
            # Ultra-short format optimization
            words = script.split()
            if len(words) > 15:
                # Truncate to most impactful words
                script = ' '.join(words[:15])
                if not script.endswith(('.', '!', '?')):
                    script += '!'
        
        elif platform.lower() in ['youtube', 'youtube_shorts']:
            # YouTube optimization (slightly longer allowed)
            words = script.split()
            if len(words) > 20:
                script = ' '.join(words[:20])
                if not script.endswith(('.', '!', '?')):
                    script += '!'
        
        return script
        
    except Exception as e:
        logger.error(f"❌ Error optimizing script for {platform}: {str(e)}")
        return script


def enhance_script_with_context(script: str, 
                               movie_data: Dict,
                               enhancement_type: str = "viral") -> str:
    """
    ADVANCED script enhancement with comprehensive viral optimization.
    
    Features:
    - Genre-specific viral starters and hooks
    - Dynamic emotional triggers based on movie data
    - Platform-optimized viral language patterns
    - Psychological engagement techniques
    - Trending phrase integration
    
    Args:
        script (str): Original script
        movie_data (Dict): Movie information for context
        enhancement_type (str): Type of enhancement (viral, suspense, emotional, trending)
        
    Returns:
        str: Enhanced script with advanced viral elements
    """
    try:
        if not script or not movie_data:
            return script
        
        genres = movie_data.get('genres', [])
        title = movie_data.get('title', '')
        imdb_score = movie_data.get('imdb_score', 0)
        
        if enhancement_type == "viral":
            return _apply_viral_enhancement(script, genres, title, imdb_score)
        elif enhancement_type == "suspense":
            return _apply_suspense_enhancement(script, genres, title)
        elif enhancement_type == "emotional":
            return _apply_emotional_enhancement(script, genres, imdb_score)
        elif enhancement_type == "trending":
            return _apply_trending_enhancement(script, genres)
        else:
            return _apply_viral_enhancement(script, genres, title, imdb_score)
        
    except Exception as e:
        logger.error(f"❌ Error in advanced script enhancement: {str(e)}")
        return script


def _apply_viral_enhancement(script: str, genres: List[str], title: str, imdb_score: float) -> str:
    """
    Apply viral enhancement with genre-specific optimization.
    """
    try:
        # Genre-specific viral starters
        viral_starters = {
            'Horror': ["This terrifying", "Why this scary", "The horror that", "You won't survive", "This nightmare"],
            'Horreur': ["Cette terreur", "Pourquoi cette horreur", "Ce cauchemar", "Vous ne survivrez pas"],
            'Comedy': ["This hilarious", "Why this funny", "The comedy that", "You'll die laughing", "This ridiculous"],
            'Comédie': ["Cette comédie", "Pourquoi ce drôle", "Vous allez mourir de rire"],
            'Action': ["This explosive", "Why this intense", "The action that", "You won't believe", "This insane"],
            'Drama': ["This emotional", "Why this powerful", "The story that", "You'll cry watching", "This moving"],
            'Thriller': ["This shocking", "Why this twisted", "The thriller that", "You won't see coming", "This mind-bending"]
        }
        
        # Get appropriate starters for the genre
        genre_starters = []
        for genre in genres:
            if genre in viral_starters:
                genre_starters.extend(viral_starters[genre])
        
        # Fallback to general viral starters
        if not genre_starters:
            genre_starters = ["This amazing", "Why this incredible", "The movie that", "You won't believe", "This epic"]
        
        # Check if script needs viral starter
        words = script.split()
        if len(words) > 0:
            first_two = ' '.join(words[:2]).lower()
            
            # If doesn't start with viral pattern, enhance it
            if not any(starter.lower().startswith(first_two) for starter_list in viral_starters.values() for starter in starter_list):
                if len(words) < 14:  # Room for enhancement
                    import random
                    chosen_starter = random.choice(genre_starters)
                    
                    # Smart integration based on script content
                    if script.lower().startswith(('the ', 'a ', 'an ')):
                        script = f"{chosen_starter} {script[script.find(' ')+1:].lower()}"
                    else:
                        script = f"{chosen_starter} {script.lower()}"
        
        # Add power endings if high IMDb score
        if imdb_score >= 8.0 and len(script.split()) < 16:
            if not script.endswith(('!', '?')):
                script += "!"
        
        return script
        
    except Exception as e:
        logger.debug(f"Viral enhancement error: {str(e)}")
        return script


def _apply_suspense_enhancement(script: str, genres: List[str], title: str) -> str:
    """
    Apply suspense enhancement with psychological triggers.
    """
    try:
        suspense_triggers = {
            'Horror': ['will haunt you', 'you dare watch', 'if you can handle it', 'will terrify you'],
            'Thriller': ['will shock you', 'you never see coming', 'will blow your mind', 'keeps you guessing'],
            'Mystery': ['the truth behind', 'what really happened', 'the secret that', 'you won\'t solve']
        }
        
        # Find matching genre triggers
        applicable_triggers = []
        for genre in genres:
            if genre in suspense_triggers:
                applicable_triggers.extend(suspense_triggers[genre])
        
        if applicable_triggers and len(script.split()) < 14:
            import random
            trigger = random.choice(applicable_triggers)
            
            # Smart integration
            if script.endswith('.'):
                script = script[:-1] + f" {trigger}!"
            elif not script.endswith(('!', '?')):
                script += f" {trigger}!"
        
        return script
        
    except Exception as e:
        logger.debug(f"Suspense enhancement error: {str(e)}")
        return script


def _apply_emotional_enhancement(script: str, genres: List[str], imdb_score: float) -> str:
    """
    Apply emotional enhancement based on genre and quality.
    """
    try:
        emotional_amplifiers = {
            'Drama': ['will make you cry', 'touches your heart', 'emotionally devastating', 'brings tears'],
            'Romance': ['will warm your heart', 'pure love story', 'romantically perfect', 'heart-melting'],
            'Family': ['the whole family loves', 'heartwarming story', 'brings families together']
        }
        
        # High IMDb score gets stronger emotional language
        if imdb_score >= 8.5:
            emotional_boosters = ['masterpiece', 'absolutely perfect', 'cinematic genius', 'unforgettable']
            
            words = script.split()
            if len(words) < 13:
                import random
                booster = random.choice(emotional_boosters)
                if not any(word in script.lower() for word in emotional_boosters):
                    script = f"{booster.title()} {script.lower()}"
        
        # Apply genre-specific emotional triggers
        for genre in genres:
            if genre in emotional_amplifiers and len(script.split()) < 15:
                import random
                amplifier = random.choice(emotional_amplifiers[genre])
                if not script.endswith(('!', '?')):
                    script += f" {amplifier}!"
                break
        
        return script
        
    except Exception as e:
        logger.debug(f"Emotional enhancement error: {str(e)}")
        return script


def _apply_trending_enhancement(script: str, genres: List[str]) -> str:
    """
    Apply current trending language patterns and phrases.
    """
    try:
        # Current trending phrases (update periodically)
        trending_patterns = {
            'viral_openings': ['POV:', 'Not me watching', 'Tell me why', 'The way I', 'When you realize'],
            'engagement_hooks': ['Wait for it', 'Watch till the end', 'You\'re not ready', 'This hits different'],
            'current_slang': ['no cap', 'hits different', 'absolutely unhinged', 'chef\'s kiss', 'main character energy']
        }
        
        words = script.split()
        if len(words) < 12:  # Room for trending elements
            import random
            
            # 30% chance to add viral opening
            if random.random() < 0.3:
                opener = random.choice(trending_patterns['viral_openings'])
                script = f"{opener} {script.lower()}"
            
            # 20% chance to add engagement hook
            elif random.random() < 0.2 and len(script.split()) < 10:
                hook = random.choice(trending_patterns['engagement_hooks'])
                script += f" {hook}!"
        
        return script
        
    except Exception as e:
        logger.debug(f"Trending enhancement error: {str(e)}")
        return script

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def save_scripts_to_files(scripts: Dict[str, str], combined_script: str) -> Optional[str]:
    """
    Save individual and combined scripts to files.
    
    Args:
        scripts (Dict): Individual scripts dictionary
        combined_script (str): Combined script content
        
    Returns:
        str: Path to combined script file or None if failed
    """
    try:
        # Ensure output directory exists
        from utils.file_utils import ensure_directory
        ensure_directory("videos")
        
        # Save individual scripts
        for name, script in scripts.items():
            script_path = f"videos/script_{name}.txt"
            try:
                with open(script_path, "w", encoding='utf-8') as f:
                    f.write(script)
                logger.debug(f"💾 Saved {name} script: {script_path}")
            except Exception as e:
                logger.error(f"❌ Failed to save {name} script: {str(e)}")
        
        # Save combined script
        combined_path = "videos/combined_script.txt"
        try:
            with open(combined_path, "w", encoding='utf-8') as f:
                f.write(combined_script)
            logger.info(f"💾 Combined script saved: {combined_path}")
            return combined_path
        except Exception as e:
            logger.error(f"❌ Failed to save combined script: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error saving scripts to files: {str(e)}")
        return None


def get_openai_usage_stats() -> Dict[str, Any]:
    """
    Get OpenAI API usage statistics and configuration info.
    
    Returns:
        Dict[str, Any]: Usage statistics and configuration
    """
    stats = {
        'api_key_configured': bool(os.getenv('OPENAI_API_KEY')),
        'client_available': False,
        'model_config': {},
        'rate_limits': {},
        'last_error': None
    }
    
    try:
        # Test client initialization
        client = _get_openai_client()
        if client:
            stats['client_available'] = True
            
            # Get API configuration
            api_config = get_api_config('openai')
            stats['model_config'] = {
                'model': api_config.get('model', 'gpt-4'),
                'temperature': api_config.get('temperature', 0.9),
                'hook_max_tokens': api_config.get('hook_max_tokens', 40),
                'intro_max_tokens': api_config.get('intro_max_tokens', 60)
            }
        
        return stats
        
    except Exception as e:
        stats['last_error'] = str(e)
        logger.error(f"Error getting OpenAI usage stats: {str(e)}")
        return stats


def test_openai_connection() -> Dict[str, Any]:
    """
    Test OpenAI API connection and functionality.
    
    Returns:
        Dict[str, Any]: Connection test results
    """
    test_result = {
        'connection_successful': False,
        'api_accessible': False,
        'test_generation': False,
        'response_time': None,
        'error': None
    }
    
    try:
        import time
        
        client = _get_openai_client()
        if not client:
            test_result['error'] = 'Client initialization failed'
            return test_result
        
        test_result['connection_successful'] = True
        
        # Test simple generation
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use cheaper model for testing
            messages=[
                {"role": "user", "content": "Say 'test successful' in exactly 2 words."}
            ],
            max_tokens=10,
            temperature=0
        )
        
        response_time = time.time() - start_time
        test_result['response_time'] = response_time
        test_result['api_accessible'] = True
        
        # Check response
        if response.choices and response.choices[0].message.content:
            test_result['test_generation'] = True
        
        logger.info(f"✅ OpenAI connection test successful ({response_time:.2f}s)")
        
        return test_result
        
    except Exception as e:
        test_result['error'] = str(e)
        logger.error(f"❌ OpenAI connection test failed: {str(e)}")
        return test_result


# =============================================================================
# ADVANCED SCRIPT GENERATION FUNCTIONS
# =============================================================================

def generate_dynamic_viral_hooks(movie_data: Dict, 
                                 genre: Optional[str] = None,
                                 platform: Optional[str] = None,
                                 num_variations: int = 3) -> List[str]:
    """
    Generate multiple viral hook variations with advanced optimization.
    
    Features:
    - Multiple viral starter patterns per genre
    - A/B testing variations for performance optimization
    - Platform-specific viral language adaptation
    - Psychological engagement triggers
    - Trending phrase integration
    
    Args:
        movie_data (Dict): Movie information
        genre (str): Genre for context-aware generation
        platform (str): Target platform for optimization
        num_variations (int): Number of hook variations to generate
        
    Returns:
        List[str]: List of optimized viral hook variations
    """
    try:
        logger.info(f"🔥 DYNAMIC VIRAL HOOK GENERATION: {num_variations} variations")
        logger.info(f"   Movie: {movie_data.get('title', 'Unknown')}")
        logger.info(f"   Genre: {genre} | Platform: {platform}")
        
        client = _get_openai_client()
        if not client:
            return []
        
        api_config = get_api_config('openai')
        viral_hooks = []
        
        # Generate multiple variations with different approaches
        for i in range(num_variations):
            variation_type = ['viral', 'suspense', 'emotional'][i % 3]
            
            logger.debug(f"🎯 Generating variation {i+1}: {variation_type} approach")
            
            # Get enhanced prompts for this variation
            system_prompt, user_prompt = _get_advanced_hook_prompts(
                movie_data, genre, platform, variation_type
            )
            
            try:
                response = client.chat.completions.create(
                    model=api_config.get('model', 'gpt-4'),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.9 + (i * 0.1),  # Increasing creativity for variations
                    max_tokens=api_config.get('hook_max_tokens', 40)
                )
                
                hook = response.choices[0].message.content.strip()
                hook = sanitize_script_text(hook)
                
                # Apply enhancement based on variation type
                enhanced_hook = enhance_script_with_context(
                    hook, movie_data, enhancement_type=variation_type
                )
                
                # Optimize for platform
                optimized_hook = optimize_script_for_platform(enhanced_hook, platform)
                
                if validate_script_content(optimized_hook, script_type='hook'):
                    viral_hooks.append(optimized_hook)
                    logger.debug(f"✅ Variation {i+1}: {optimized_hook}")
                else:
                    logger.warning(f"⚠️ Variation {i+1} failed validation")
                
            except Exception as e:
                logger.error(f"❌ Error generating variation {i+1}: {str(e)}")
                continue
        
        # Ensure we have at least one hook
        if not viral_hooks:
            logger.warning("⚠️ No variations generated, attempting fallback...")
            fallback_hook = _generate_fallback_hook(movie_data, genre)
            if fallback_hook:
                viral_hooks.append(fallback_hook)
        
        logger.info(f"✅ Generated {len(viral_hooks)}/{num_variations} viral hook variations")
        return viral_hooks
        
    except Exception as e:
        logger.error(f"❌ Error in dynamic viral hook generation: {str(e)}")
        return []


def _get_advanced_hook_prompts(movie_data: Dict, genre: str, platform: str, variation_type: str) -> Tuple[str, str]:
    """
    Generate advanced hook prompts with variation-specific optimization.
    """
    title = movie_data.get('title', 'Unknown Movie')
    imdb_score = movie_data.get('imdb_score', 0)
    year = movie_data.get('year', '')
    
    base_context = f"Movie: {title} | Genre: {genre} | IMDb: {imdb_score} | Year: {year}"
    
    if variation_type == "viral":
        system_prompt = f"""
You are a viral content creator specializing in {platform} hooks. Create ultra-engaging movie hooks that:
- Use psychological triggers and viral language patterns
- Start with proven viral openers for {genre} content
- Include trending phrases and current social media language
- Maximize click-through rates and engagement
- Stay within 10-18 words for optimal performance

Context: {base_context}
Platform: {platform} algorithm optimization
Objective: Maximum viral potential
"""
    
    elif variation_type == "suspense":
        system_prompt = f"""
You are a master of suspenseful content creation. Create hooks that:
- Build immediate tension and curiosity
- Use psychological suspense triggers
- Create fear of missing out (FOMO)
- Include cliffhanger elements
- Make viewers unable to scroll away

Context: {base_context}
Platform: {platform} engagement optimization
Objective: Maximum retention and curiosity
"""
    
    else:  # emotional
        system_prompt = f"""
You are an emotional storytelling expert. Create hooks that:
- Trigger strong emotional responses
- Connect with universal human experiences
- Use empathy and relatability
- Create emotional investment
- Drive sharing through emotional connection

Context: {base_context}
Platform: {platform} sharing optimization
Objective: Maximum emotional engagement
"""
    
    user_prompt = f"Create a {variation_type} hook for '{title}' ({genre}) optimized for {platform}. Focus on {variation_type} elements while staying concise and impactful."
    
    return system_prompt, user_prompt


def _generate_fallback_hook(movie_data: Dict, genre: str) -> Optional[str]:
    """
    Generate fallback hook using template-based approach.
    """
    try:
        title = movie_data.get('title', 'this movie')
        
        fallback_templates = {
            'Horror': f"This terrifying {title.lower()} will haunt you!",
            'Comedy': f"This hilarious {title.lower()} will make you laugh!",
            'Action': f"This explosive {title.lower()} will blow your mind!",
            'Drama': f"This powerful {title.lower()} will move you!",
            'Thriller': f"This shocking {title.lower()} will surprise you!"
        }
        
        return fallback_templates.get(genre, f"This amazing {title.lower()} is incredible!")
        
    except Exception:
        return "This incredible movie will amaze you!"

# =============================================================================
# PROFESSIONAL MULTI-MODEL FALLBACK SYSTEM
# =============================================================================

def generate_script_with_fallback(script_type: str, **kwargs) -> Optional[str]:
    """
    🚀 Professional Multi-Model Script Generation with Intelligent Fallback
    
    This function implements a robust fallback system:
    1. Try OpenAI first (primary, high-quality generation)
    2. If OpenAI fails, automatically fallback to Gemini
    3. If both fail, use template-based fallback
    
    Args:
        script_type: Type of script ('intro' or 'hook')
        **kwargs: Arguments specific to the script type
        
    Returns:
        Generated script string or None if all methods fail
    """
    logger.info(f"🤖 Starting {script_type} generation with multi-model fallback")
    
    # Try OpenAI first (primary model)
    openai_result = None
    try:
        logger.info("🔵 Attempting OpenAI generation...")
        
        if script_type == 'intro':
            openai_result = _generate_intro_openai(**kwargs)
        elif script_type == 'hook':
            openai_result = _generate_hook_openai(**kwargs)
        else:
            raise ValueError(f"Unknown script type: {script_type}")
            
        if openai_result:
            logger.info("✅ OpenAI generation successful!")
            return openai_result
            
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"⚠️ OpenAI failed: {error_msg}")
        
        # Check if it's a quota/API key issue that should trigger fallback
        should_fallback = any(keyword in error_msg.lower() for keyword in [
            'quota', 'insufficient_quota', 'rate_limit', 'invalid_api_key', 
            'incorrect api key', 'model_not_found', '401', '403', '429'
        ])
        
        if not should_fallback:
            logger.error("❌ OpenAI failed with non-recoverable error")
            return None
    
    # Fallback to Gemini if available
    if GEMINI_FALLBACK_AVAILABLE:
        try:
            logger.info("🟢 Falling back to Gemini generation...")
            gemini_client = GeminiClient()
            
            if gemini_client.is_available():
                gemini_result = None
                
                if script_type == 'intro':
                    gemini_result = gemini_client.generate_intro_script(**kwargs)
                elif script_type == 'hook':
                    gemini_result = gemini_client.generate_movie_hook(**kwargs)
                
                if gemini_result:
                    logger.info("✅ Gemini fallback successful!")
                    return gemini_result
                    
            else:
                # Get detailed configuration status
                status = gemini_client.get_configuration_status()
                logger.warning(f"⚠️ Gemini unavailable: {status['initialization_error']}")
                
                # Log configuration steps for user
                if not status['dependencies_installed']:
                    logger.info("💡 To enable Gemini fallback: pip install google-generativeai")
                elif not status['api_key_configured']:
                    logger.info("💡 To enable Gemini fallback: Add GEMINI_API_KEY to your .env file")
                    logger.info("💡 Get API key from: https://makersuite.google.com/app/apikey")
                
        except Exception as e:
            logger.error(f"❌ Gemini fallback failed: {e}")
    else:
        logger.warning("⚠️ Gemini fallback not available")
    
    # Final fallback to template-based generation
    logger.info("🔧 Using template-based fallback...")
    try:
        if script_type == 'intro':
            return _generate_intro_fallback(**kwargs)
        elif script_type == 'hook':
            return _generate_hook_fallback(**kwargs)
    except Exception as e:
        logger.error(f"❌ Template fallback failed: {e}")
    
    logger.error(f"❌ All fallback methods failed for {script_type} generation")
    return None

def _generate_intro_openai(genre: str, platform: str, content_type: str, 
                          movie_count: int, **kwargs) -> Optional[str]:
    """Generate intro using OpenAI API"""
    try:
        api_config = get_api_config('openai')
        client = OpenAI()
        
        content_name = "movie" if "film" in content_type.lower() else "series"
        
        system_msg = f"You create engaging intros for TikTok/YouTube videos that hook viewers immediately. You specialize in {genre} content recommendations."
        
        user_prompt = f"""Create a short, energetic intro that introduces this collection of {content_name}s from StreamGank.

Collection Details:
- Content: {content_name}s
- Genre: {genre}  
- Platform: {platform}
- Count: {movie_count} {content_name}s

Intro Requirements:
- 1-2 sentences maximum
- 15-25 words total
- Must be hooky and grab attention immediately
- Create excitement for what's coming
- Use viral language that makes viewers want to keep watching

PREFERRED STYLES (choose one that fits the genre):
- "Here are the top {movie_count} {genre} {content_name}s that will blow your mind!"
- "StreamGank's top {movie_count} {genre} {content_name}s that everyone's talking about!"
- "Get ready for the most incredible {genre} {content_name}s on {platform}!"
- "These {movie_count} {genre} {content_name}s from StreamGank are breaking the internet!"

Create something similar but more engaging and viral. Respond with ONLY the intro text."""

        response = client.chat.completions.create(
            model=api_config.get('model', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            temperature=api_config.get('temperature', 0.8),
            max_tokens=api_config.get('intro_max_tokens', 60)
        )
        
        intro_text = response.choices[0].message.content.strip()
        intro_text = intro_text.replace('"', '').replace("'", "").strip()
        if not intro_text.endswith(('.', '!', '?')):
            intro_text += "!"
            
        return intro_text
        
    except Exception as e:
        logger.error(f"❌ OpenAI intro generation failed: {e}")
        raise

def _generate_hook_openai(movie_data: Dict[str, Any], genre: str, platform: str, **kwargs) -> Optional[str]:
    """Generate movie hook using OpenAI API"""
    try:
        api_config = get_api_config('openai')
        client = OpenAI()
        
        title = movie_data.get('title', 'Unknown')
        year = movie_data.get('year', 'Unknown')
        genres = movie_data.get('genres', [])
        
        system_msg = f"You create viral TikTok/YouTube hook sentences that instantly stop scrollers. You specialize in {genre} content and making viewers think 'I NEED to watch this!'"
        
        hook_starters = '"This movie", "You won\'t believe", "Everyone\'s talking about", "This is why", "Get ready for", "The moment when"'
        if genre and genre.lower() == 'horror':
            hook_starters = '"This horror masterpiece", "You won\'t believe what lurks", "This movie proves that", "Everyone\'s too scared to watch", "This is why horror fans are obsessed with", "The moment you see this"'
        
        user_prompt = f"""Create ONE viral hook sentence for this movie that makes viewers instantly stop scrolling.

Movie: {title} ({year})
Genres: {', '.join(genres[:3]) if genres else genre}
Platform: {platform}

Hook Requirements:
- EXACTLY 1 sentence only
- 10-18 words maximum
- Use varied viral starters: {hook_starters}
- AVOID overusing "What happens when" - be more creative and varied
- Create instant curiosity and urgency
- Make viewers think "I MUST see this!"
- Use viral TikTok language that makes people want to watch immediately
- Focus on the movie's unique selling point or most shocking element

Respond with ONLY the hook sentence."""

        response = client.chat.completions.create(
            model=api_config.get('model', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,  # High creativity for viral hooks
            max_tokens=api_config.get('hook_max_tokens', 40)
        )
        
        hook = response.choices[0].message.content.strip()
        hook = hook.replace('"', '').replace("'", "").strip()
        if not hook.endswith(('.', '!', '?')):
            hook += "!"
            
        return hook
        
    except Exception as e:
        logger.error(f"❌ OpenAI hook generation failed: {e}")
        raise

def _generate_intro_fallback(genre: str, platform: str, content_type: str, movie_count: int, **kwargs) -> str:
    """Generate intro using template-based fallback"""
    content_name = "movie" if "film" in content_type.lower() else "series"
    
    templates = [
        f"Here are the top {movie_count} {genre} {content_name}s from StreamGank!",
        f"Get ready for {movie_count} incredible {genre} {content_name}s on {platform}!",
        f"StreamGank's best {movie_count} {genre} {content_name}s that everyone's watching!",
        f"These {movie_count} {genre} {content_name}s will blow your mind!"
    ]
    
    # Simple hash-based selection for consistency
    template_index = hash(f"{genre}{platform}{movie_count}") % len(templates)
    return templates[template_index]

def _generate_hook_fallback(movie_data: Dict[str, Any], genre: str, **kwargs) -> str:
    """Generate hook using template-based fallback"""
    title = movie_data.get('title', 'this movie')
    
    templates = {
        'Horror': f"This terrifying masterpiece will haunt your dreams!",
        'Action': f"The most intense action experience you'll ever see!",
        'Comedy': f"This hilarious gem will have you crying with laughter!",
        'Drama': f"This powerful story will change how you see everything!",
        'Thriller': f"This edge-of-your-seat thriller will leave you breathless!",
    }
    
    return templates.get(genre, f"This incredible {genre.lower()} movie is a must-watch!")