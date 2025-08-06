#!/usr/bin/env python3
"""
🤖 Gemini AI Client - Professional Google Gemini Integration
StreamGank Modular Video Generation System

This module provides a robust Gemini API client as a fallback for OpenAI script generation.
Implements professional error handling, retry logic, and safety settings.

Author: StreamGank Development Team
Version: 1.0.0
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from config.settings import get_api_config
from utils.validators import validate_environment_variables

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class GeminiResponse:
    """Data class for Gemini API responses"""
    content: str
    model: str
    tokens_used: int
    finish_reason: str
    safety_ratings: List[Dict[str, Any]]
    
class GeminiClient:
    """
    🤖 Professional Gemini API Client
    
    Handles all interactions with Google's Gemini AI API including:
    - Intelligent script generation with safety controls
    - Robust error handling and retry logic
    - Token usage monitoring and optimization
    - Professional logging and debugging
    """
    
    def __init__(self):
        """Initialize Gemini client with configuration and safety settings"""
        self.config = get_api_config('gemini')
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None
        self.initialization_error = None
        
        # Check dependencies first
        if not GEMINI_AVAILABLE:
            self.initialization_error = "Dependencies not installed. Run: pip install google-generativeai"
            logger.warning(f"⚠️ Gemini fallback unavailable: {self.initialization_error}")
            return
        
        # Check API key
        if not self.api_key:
            self.initialization_error = "GEMINI_API_KEY not found in environment variables"
            logger.warning(f"⚠️ Gemini fallback unavailable: {self.initialization_error}")
            return
        
        # Initialize client
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.config['model'])
            logger.info(f"✅ Gemini client initialized successfully: {self.config['model']}")
        except Exception as e:
            self.initialization_error = f"Failed to initialize Gemini client: {e}"
            logger.error(f"❌ {self.initialization_error}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Gemini client is available and properly configured"""
        return (
            GEMINI_AVAILABLE and 
            self.api_key is not None and 
            self.model is not None
        )
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get detailed configuration status for debugging"""
        return {
            'dependencies_installed': GEMINI_AVAILABLE,
            'api_key_configured': self.api_key is not None,
            'model_initialized': self.model is not None,
            'is_available': self.is_available(),
            'initialization_error': self.initialization_error,
            'configuration_steps': [
                "1. Install dependencies: pip install google-generativeai",
                "2. Get API key from: https://makersuite.google.com/app/apikey", 
                "3. Add to .env file: GEMINI_API_KEY=your_api_key_here",
                "4. Restart the application"
            ]
        }
    
    def _prepare_safety_settings(self) -> List[Any]:
        """Prepare safety settings for content generation"""
        if not GEMINI_AVAILABLE:
            return []
            
        safety_settings = []
        for setting in self.config.get('safety_settings', []):
            try:
                category = getattr(HarmCategory, setting['category'])
                threshold = getattr(HarmBlockThreshold, setting['threshold'])
                safety_settings.append({
                    'category': category,
                    'threshold': threshold
                })
            except (AttributeError, KeyError) as e:
                logger.warning(f"Invalid safety setting ignored: {setting} - {e}")
                
        return safety_settings
    
    def _generate_with_retry(self, prompt: str, max_retries: int = None) -> Optional[GeminiResponse]:
        """
        Generate content with intelligent retry logic
        
        Args:
            prompt: The input prompt for generation
            max_retries: Maximum number of retry attempts
            
        Returns:
            GeminiResponse object or None if failed
        """
        if not self.is_available():
            logger.error("❌ Gemini client not available")
            return None
            
        max_retries = max_retries or self.config.get('retry_attempts', 3)
        safety_settings = self._prepare_safety_settings()
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"🔄 Gemini generation attempt {attempt + 1}/{max_retries + 1}")
                
                # Configure generation parameters
                generation_config = {
                    'temperature': self.config.get('temperature', 0.8),
                    'max_output_tokens': self.config.get('max_output_tokens', 100),
                }
                
                # Generate content
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Check if response is valid and handle safety blocks
                if not hasattr(response, 'text') or not response.text:
                    # Check if content was blocked by safety filters
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 3:  # SAFETY
                            safety_info = getattr(candidate, 'safety_ratings', [])
                            blocked_categories = [rating.category for rating in safety_info if getattr(rating, 'blocked', False)]
                            raise ValueError(f"Content blocked by Gemini safety filters: {blocked_categories}")
                    
                    raise ValueError("Empty or invalid response from Gemini API")
                
                # Create response object
                usage_metadata = getattr(response, 'usage_metadata', None)
                tokens_used = 0
                if usage_metadata:
                    tokens_used = getattr(usage_metadata, 'total_token_count', 0)
                
                gemini_response = GeminiResponse(
                    content=response.text.strip(),
                    model=self.config['model'],
                    tokens_used=tokens_used,
                    finish_reason=str(getattr(response, 'finish_reason', 'STOP')),
                    safety_ratings=list(getattr(response, 'safety_ratings', []))
                )
                
                logger.info(f"✅ Gemini generation successful (attempt {attempt + 1})")
                return gemini_response
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Gemini attempt {attempt + 1} failed: {error_msg}")
                
                # Check if we should retry
                if attempt < max_retries:
                    # Exponential backoff
                    delay = 2 ** attempt
                    logger.info(f"🔄 Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ All Gemini attempts failed. Final error: {error_msg}")
                    
        return None
    
    def generate_intro_script(self, genre: str, platform: str, content_type: str, 
                            movie_count: int, context: Dict[str, Any] = None) -> Optional[str]:
        """
        🎬 Generate intro script using Gemini AI
        
        Args:
            genre: Movie genre (e.g., 'Horror', 'Action')
            platform: Streaming platform (e.g., 'Netflix', 'Hulu') 
            content_type: Type of content (e.g., 'Film', 'Series')
            movie_count: Number of movies being presented
            context: Additional context for generation
            
        Returns:
            Generated intro script or None if failed
        """
        logger.info(f"🎬 Generating Gemini intro script: {genre} {content_type} from {platform}")
        
        # Build context-aware prompt
        content_name = "movie" if "film" in content_type.lower() else "series"
        context_info = context or {}
        
        prompt = f"""Create a short, energetic intro for a TikTok/YouTube video about {genre} {content_name}s.

Collection Details:
- Content: {content_name}s
- Genre: {genre}  
- Platform: {platform}
- Count: {movie_count} {content_name}s

Requirements:
- 1-2 sentences maximum
- 15-25 words total
- Hook viewers immediately with excitement
- Use viral, engaging language
- Make viewers want to keep watching
- Sound natural and conversational

Examples of good intros:
- "Here are the top {movie_count} {genre.lower()} {content_name}s that will blow your mind!"
- "Get ready for the most incredible {genre.lower()} {content_name}s on {platform}!"
- "These {movie_count} {genre.lower()} {content_name}s from StreamGank are breaking the internet!"

Generate ONLY the intro text, nothing else:"""

        response = self._generate_with_retry(prompt)
        if response and response.content:
            # Clean and validate the response
            intro = response.content.strip().strip('"').strip("'")
            
            # Log success with metrics
            logger.info(f"✅ Gemini intro generated: {len(intro.split())} words")
            logger.debug(f"📝 Generated intro: '{intro}'")
            
            return intro
        
        logger.error("❌ Failed to generate intro script with Gemini")
        return None
    
    def generate_movie_hook(self, movie_data: Dict[str, Any], genre: str, 
                          platform: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        🎯 Generate movie hook script using Gemini AI
        
        Args:
            movie_data: Movie information dictionary
            genre: Movie genre for context
            platform: Streaming platform
            context: Additional context for generation
            
        Returns:
            Generated hook script or None if failed
        """
        title = movie_data.get('title', 'Unknown Movie')
        year = movie_data.get('year', 'N/A')
        rating = movie_data.get('imdb_score', 0)
        
        logger.info(f"🎯 Generating Gemini hook: {title} ({year})")
        
        prompt = f"""Create a viral hook sentence for this {genre} movie.

Movie Details:
- Title: {title}
- Year: {year}
- IMDB Rating: {rating}/10
- Genre: {genre}
- Platform: {platform}

Requirements:
- Single powerful sentence (10-18 words max)
- Create excitement and intrigue
- Use viral TikTok/YouTube language
- Hook viewers immediately
- Don't mention the title (it will be shown visually)
- Focus on impact and emotion

Examples of good hooks:
- "This {genre.lower()} movie will haunt your dreams for weeks!"
- "The most intense {genre.lower()} experience you'll ever watch!"
- "This {rating}/10 masterpiece changed {genre.lower()} movies forever!"

Generate ONLY the hook sentence, nothing else:"""

        response = self._generate_with_retry(prompt)
        if response and response.content:
            # Clean and validate the response
            hook = response.content.strip().strip('"').strip("'")
            
            # Log success with metrics
            logger.info(f"✅ Gemini hook generated for '{title}': {len(hook.split())} words")
            logger.debug(f"📝 Generated hook: '{hook}'")
            
            return hook
        
        logger.error(f"❌ Failed to generate hook for '{title}' with Gemini")
        return None

def test_gemini_availability() -> bool:
    """
    🧪 Test Gemini API availability and configuration
    
    Returns:
        True if Gemini is available and working, False otherwise
    """
    try:
        client = GeminiClient()
        if not client.is_available():
            return False
            
        # Test with a simple prompt
        test_response = client._generate_with_retry("Say 'test successful'", max_retries=1)
        return test_response is not None and 'test' in test_response.content.lower()
        
    except Exception as e:
        logger.error(f"❌ Gemini availability test failed: {e}")
        return False

# Professional logging for module initialization
if not GEMINI_AVAILABLE:
    logger.warning("⚠️ Gemini dependencies not installed. Install with: pip install google-generativeai")
else:
    logger.info("✅ Gemini client module loaded successfully")