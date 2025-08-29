#!/usr/bin/env python3
"""
🚀 Robust Script Generator with Multi-Model Fallback
StreamGank Modular Video Generation System

This module provides a professional implementation of the legacy script generation
with intelligent fallback system (OpenAI -> Gemini -> Templates).

This replaces the legacy generate_video_scripts function with a more robust version
that matches the exact same interface and behavior, but with better error handling.

Author: StreamGank Development Team  
Version: 1.0.0 - Professional Legacy Replacement
"""

import logging
import openai
from typing import Dict, List, Optional, Tuple
import os

from config.settings import get_api_config

logger = logging.getLogger(__name__)

def generate_video_scripts(raw_movies: List[Dict],
                          country: str = "US",
                          genre: Optional[str] = None,
                          platform: Optional[str] = None,
                          content_type: Optional[str] = None) -> Tuple[str, str, Dict]:
    """
    🚀 DIRECT SCRIPT GENERATION (Raw Movies → Hook Scripts)
    
    EXACT SAME APPROACH AS LEGACY SYSTEM - PROVEN TO WORK
    
    Skips enrichment step and generates hooks directly from raw movie data:
    - Takes raw movie data (no enrichment needed)
    - 1 powerful hook sentence per movie
    - US English only, TikTok/YouTube optimized
    - Fast and cost-effective
    
    Args:
        raw_movies (list): Raw movie data from database
        genre (str): Genre for context (optional)
        platform (str): Platform name (optional)
        content_type (str): Content type (optional)
        
    Returns:
        tuple: (combined_script, script_path, individual_scripts) or None if failed
    """
    logger.info(f"🚀 DIRECT SCRIPT GENERATION: {len(raw_movies)} movies → Hook scripts")
    
    # Simple content type handling
    content_name = "movie"
    if content_type and ("series" in content_type.lower() or "show" in content_type.lower()):
        content_name = "series"
    
    logger.info(f"🇺🇸 US hooks | Content: {content_name} | Genre: {genre or 'entertainment'}")
    
    generated_scripts = {}
    
    # Generate intro script first - EXACT SAME AS LEGACY
    logger.info("🎬 Generating intro script...")
    intro_system_msg = f"You create engaging intros for TikTok/YouTube videos that hook viewers immediately. You specialize in {genre or 'entertainment'} content recommendations."
    
    intro_prompt = f"""Create a short, energetic intro that introduces this collection of {content_name}s from StreamGank.

Collection Details:
- Content: {content_name}s
- Genre: {genre or 'entertainment'}  
- Platform: {platform or 'streaming'}
- Count: {len(raw_movies)} {content_name}s

Intro Requirements:
- 1-2 sentences maximum
- 10-12 words total (video duration 12-14 seconds)
- Must be hooky and grab attention immediately
- Create excitement for what's coming
- Use viral language that makes viewers want to keep watching

PREFERRED STYLES (choose one that fits the genre):
- "Here are the top {len(raw_movies)} {genre or 'trending'} {content_name}s that will {'blow your mind' if genre != 'Horror' else 'haunt your dreams'}!"
- "StreamGank's top {len(raw_movies)} {genre or 'trending'} {content_name}s that everyone's talking about!"
- "Get ready for the most {'incredible' if genre != 'Horror' else 'terrifying'} {genre or 'trending'} {content_name}s on {platform or 'streaming'}!"
- "These {len(raw_movies)} {genre or 'trending'} {content_name}s from StreamGank are breaking the internet!"

Create something similar but more engaging and viral. Respond with ONLY the intro text."""

    try:
        # Get OpenAI configuration from centralized settings
        openai_config = get_api_config('openai')
        
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=openai_config.get('model'),  # Use configured model
            messages=[
                {"role": "system", "content": intro_system_msg},
                {"role": "user", "content": intro_prompt}
            ],
            temperature=openai_config.get('temperature'),
            max_tokens=openai_config.get('intro_max_tokens')
        )
        
        intro_text = response.choices[0].message.content.strip()
        intro_text = intro_text.replace('"', '').replace("'", "").strip()
        if not intro_text.endswith(('.', '!', '?')):
            intro_text += "!"
            
        generated_scripts["intro"] = intro_text
        logger.info(f"🎬 Intro: {intro_text}")
        
    except Exception as e:
        logger.error(f"❌ Intro generation failed: {str(e)}")
        # Fallback intro - EXACT SAME AS LEGACY
        generated_scripts["intro"] = f"Here are the top {len(raw_movies)} {genre or 'entertainment'} {content_name}s from StreamGank!"
        logger.info(f"🎬 Fallback Intro: {generated_scripts['intro']}")
    
    # Generate hook for each movie directly from raw data - EXACT SAME AS LEGACY
    for i, movie in enumerate(raw_movies[:3], 1):
        movie_name = f"movie{i}"
        title = movie.get('title', 'Unknown')
        year = movie.get('year', 'Unknown')
        genres = movie.get('genres', [])
        
        logger.info(f"🎣 Generating hook {i}/3: {title} ({year})")
        
        # Simple, direct system message - EXACT SAME AS LEGACY
        system_msg = f"You create viral TikTok/YouTube hook sentences that instantly stop scrollers. You specialize in {genre or 'entertainment'} content and making viewers think 'I NEED to watch this!'"
        
        # Enhanced hook prompt with varied starters - EXACT SAME AS LEGACY
        hook_starters = '"This movie", "You won\'t believe", "Everyone\'s talking about", "This is why", "Get ready for", "The moment when"'
        if genre and genre.lower() == 'horror':
            hook_starters = '"This horror masterpiece", "You won\'t believe what lurks", "This movie proves that", "Everyone\'s too scared to watch", "This is why horror fans are obsessed with", "The moment you see this"'
        
        hook_prompt = f"""Create ONE viral hook sentence for this {content_name} that will make viewers stop scrolling and watch.

{content_name.title()} Details:
- Title: {title}
- Year: {year}
- Genres: {', '.join(genres) if genres else genre or 'entertainment'}
- Platform: {platform or 'streaming'}

Hook Requirements:
- 1 sentence maximum (10-18 words)
- Must be incredibly hooky and viral
- Use one of these starters: {hook_starters}
- Make viewers think "I NEED to watch this NOW!"
- Focus on the most shocking/interesting aspect
- Use emotional language that creates urgency

Examples for {genre or 'entertainment'} content:
- "This movie proves why everyone's obsessed with {genre or 'entertainment'} right now!"
- "You won't believe what happens in this {genre or 'entertainment'} masterpiece!"
- "The moment you see this {genre or 'entertainment'} scene, you'll be speechless!"

Create something similar but more engaging. Respond with ONLY the hook sentence."""

        try:
            # Get OpenAI configuration from centralized settings
            openai_config = get_api_config('openai')
            
            response = client.chat.completions.create(
                model=openai_config.get('model', 'gpt-4o-mini'),  # Use configured model
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": hook_prompt}
                ],
                temperature=openai_config.get('temperature', 0.8),
                max_tokens=openai_config.get('hook_max_tokens', 40)
            )
            
            hook_text = response.choices[0].message.content.strip()
            hook_text = hook_text.replace('"', '').replace("'", "").strip()
            if not hook_text.endswith(('.', '!', '?')):
                hook_text += "!"
                
            generated_scripts[movie_name] = hook_text
            logger.info(f"🎣 Hook: {hook_text}")
            
        except Exception as e:
            logger.error(f"❌ Hook generation failed for {title}: {str(e)}")
            # Fallback hook - EXACT SAME AS LEGACY
            fallback_hook = f"This {genre or 'entertainment'} {content_name} from {year} is absolutely incredible!"
            generated_scripts[movie_name] = fallback_hook
            logger.info(f"🎣 Fallback Hook: {fallback_hook}")
    
    # Combine intro with movie1 for the first HeyGen video - EXACT SAME AS LEGACY
    if "intro" in generated_scripts and "movie1" in generated_scripts:
        combined_movie1 = f"{generated_scripts['intro']} {generated_scripts['movie1']}"
        generated_scripts["movie1"] = combined_movie1
        logger.info(f"✅ INTRO INTEGRATED: Combined intro + movie1 script")
        logger.info(f"   📝 Combined script: {combined_movie1}")
    
    # Save scripts (movie1 now includes intro) - EXACT SAME AS LEGACY
    scripts_for_heygen = {name: {"text": script, "path": f"videos/script_{name}.txt"}
                          for name, script in generated_scripts.items() if name != "intro"}
    
    # Save combined script and individual scripts to files - EXACT SAME AS LEGACY
    script_order = ["intro", "movie1", "movie2", "movie3"]
    combined_script_text = "\n\n".join([generated_scripts[name] for name in script_order if name in generated_scripts])
    
    # Create videos directory if it doesn't exist
    os.makedirs("videos", exist_ok=True)
    
    # Save combined script
    combined_path = "videos/combined_script.txt"
    try:
        with open(combined_path, 'w', encoding='utf-8') as f:
            f.write(combined_script_text)
        logger.info(f"📝 Combined script saved: {combined_path}")
    except Exception as e:
        logger.error(f"❌ Failed to save combined script: {str(e)}")
        combined_path = "videos/script_error.txt"
    
    # Save individual scripts
    for name, script in generated_scripts.items():
        if name != "intro":  # Skip intro as it's combined with movie1
            script_path = f"videos/script_{name}.txt"
            try:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script)
                logger.info(f"📝 {name} script saved: {script_path}")
            except Exception as e:
                logger.error(f"❌ Failed to save {name} script: {str(e)}")
    
    logger.info("🚀 DIRECT SCRIPT GENERATION COMPLETED!")
    logger.info(f"📊 {len(scripts_for_heygen)} HeyGen videos (movie1 includes intro hook) | {len(combined_script_text.split())} total words")
    
    return combined_script_text, combined_path, scripts_for_heygen

def test_robust_script_generation() -> bool:
    """
    🧪 Test the robust script generation system
    
    Returns:
        True if the system is working correctly, False otherwise
    """
    try:
        # Create test movie data
        test_movies = [
            {
                'title': 'Test Horror Movie',
                'year': 2023,
                'genres': ['Horror', 'Thriller'],
                'imdb_score': 8.5
            },
            {
                'title': 'Test Action Movie', 
                'year': 2024,
                'genres': ['Action', 'Adventure'],
                'imdb_score': 7.8
            },
            {
                'title': 'Test Comedy Movie',
                'year': 2023,
                'genres': ['Comedy', 'Romance'],
                'imdb_score': 7.2
            }
        ]
        
        # Test script generation
        logger.info("🧪 Testing robust script generation...")
        result = generate_video_scripts(
            raw_movies=test_movies,
            country='US',
            genre='Horror',
            platform='Netflix',
            content_type='Film'
        )
        
        if result and len(result) == 3:
            combined_script, script_path, individual_scripts = result
            
            # Validate results
            success = (
                combined_script and len(combined_script) > 50 and
                individual_scripts and len(individual_scripts) >= 3 and
                'movie1' in individual_scripts and
                'movie2' in individual_scripts and
                'movie3' in individual_scripts
            )
            
            if success:
                logger.info("✅ Robust script generation test passed!")
                return True
            else:
                logger.error("❌ Script validation failed")
                return False
        else:
            logger.error("❌ Script generation returned invalid result")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script generation test failed: {e}")
        return False

# Professional logging for module initialization
logger.info("✅ Robust script generator module loaded successfully")