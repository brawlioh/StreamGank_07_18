"""
StreamGank Prompt Templates

This module provides reusable prompt templates and configurations for
OpenAI script generation, with customization for different genres and platforms.

Features:
- Genre-specific prompt templates
- Platform-optimized prompt variations
- Dynamic context building
- Viral content optimization prompts
- Customizable template parameters
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from config.constants import get_supported_genres, get_supported_platforms

logger = logging.getLogger(__name__)

# =============================================================================
# PROMPT TEMPLATE CONSTANTS
# =============================================================================

# Base system prompts
BASE_SYSTEM_PROMPTS = {
    'hook': """You are a viral content creator specialized in creating TikTok/YouTube Shorts hooks.
Your goal is to create hook sentences that make viewers instantly curious and unable to scroll away.
You understand viral psychology and create content that gets maximum engagement.""",
    
    'intro': """You are a professional video content creator specialized in creating engaging introductions.
Your goal is to create compelling intro scripts that set up the content perfectly and keep viewers watching.
You understand audience retention and create intros that hook viewers immediately."""
}

# Viral elements and power words
VIRAL_ELEMENTS = {
    'power_starters': [
        'This', 'Why', 'The reason', 'You won\'t believe', 'The truth about', 
        'Nobody tells you', 'The secret', 'Here\'s why', 'This is the',
        'The moment when', 'Everyone\'s talking about', 'This movie will',
        'Get ready for', 'You\'ve never seen', 'This is why'
    ],
    'engagement_words': [
        'shocking', 'terrifying', 'unbelievable', 'hidden', 'secret', 'revealed',
        'amazing', 'incredible', 'mind-blowing', 'game-changing', 'life-changing'
    ],
    'curiosity_gaps': [
        'but what happens next will shock you',
        'and the ending changes everything',
        'but there\'s a twist you won\'t see coming',
        'and the truth is darker than you think'
    ]
}

# Genre-specific customizations
GENRE_CUSTOMIZATIONS = {
    'Horror': {
        'mood_words': ['terrifying', 'spine-chilling', 'nightmare-inducing', 'haunting', 'disturbing', 'bone-chilling'],
        'viral_angles': ['psychological terror', 'jump scares', 'true horror stories', 'cursed', 'supernatural forces', 'survival horror'],
        'engagement_hooks': ['will haunt your dreams', 'too scary to watch alone', 'banned for being too frightening', 'will make you sleep with the lights on', 'you\'ll never see it coming'],
        'hook_starters': ['This horror masterpiece', 'You won\'t believe what lurks', 'This movie proves that', 'Everyone\'s too scared to watch', 'This is why horror fans are obsessed with', 'The moment you see this']
    },
    'Comedy': {
        'mood_words': ['hilarious', 'laugh-out-loud', 'side-splitting', 'comedy gold'],
        'viral_angles': ['plot twists', 'unexpected moments', 'comedy genius', 'viral scenes'],
        'engagement_hooks': ['will make you cry laughing', 'comedy perfection', 'meme-worthy moments']
    },
    'Action': {
        'mood_words': ['explosive', 'adrenaline-pumping', 'action-packed', 'intense'],
        'viral_angles': ['epic stunts', 'mind-blowing action', 'intense sequences', 'legendary scenes'],
        'engagement_hooks': ['non-stop action', 'edge-of-your-seat', 'action at its finest']
    },
    'Drama': {
        'mood_words': ['emotional', 'powerful', 'moving', 'compelling'],
        'viral_angles': ['plot twists', 'emotional moments', 'character development', 'deep stories'],
        'engagement_hooks': ['will move you to tears', 'emotionally devastating', 'award-worthy performances']
    }
}

# Platform-specific optimizations
PLATFORM_OPTIMIZATIONS = {
    'TikTok': {
        'max_words': 15,
        'style': 'ultra-casual',
        'pace': 'rapid-fire',
        'hooks': ['POV:', 'Tell me why', 'This is why']
    },
    'YouTube Shorts': {
        'max_words': 18,
        'style': 'casual-informative',
        'pace': 'fast-paced',
        'hooks': ['Here\'s why', 'The reason', 'What if I told you']
    },
    'Instagram Reels': {
        'max_words': 16,
        'style': 'aesthetic-casual',
        'pace': 'smooth-flow',
        'hooks': ['This is why', 'The truth about', 'You need to see']
    }
}

# =============================================================================
# HOOK PROMPT TEMPLATES
# =============================================================================

def get_hook_prompt_template(movie_data: Dict, 
                           genre: Optional[str] = None,
                           platform: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate hook prompt template for a specific movie.
    
    Args:
        movie_data (Dict): Movie information
        genre (str): Genre for customization
        platform (str): Target platform
        
    Returns:
        Tuple[str, str]: (system_prompt, user_prompt)
    """
    try:
        # Build system prompt
        system_prompt = BASE_SYSTEM_PROMPTS['hook']
        
        # Add genre-specific instructions
        if genre and genre in GENRE_CUSTOMIZATIONS:
            genre_info = GENRE_CUSTOMIZATIONS[genre]
            system_prompt += f"""

GENRE SPECIALIZATION - {genre.upper()}:
- Use mood words: {', '.join(genre_info['mood_words'])}
- Focus on: {', '.join(genre_info['viral_angles'])}
- Engagement style: {', '.join(genre_info['engagement_hooks'])}"""
        
        # Add platform-specific instructions
        if platform and platform in PLATFORM_OPTIMIZATIONS:
            platform_info = PLATFORM_OPTIMIZATIONS[platform]
            system_prompt += f"""

PLATFORM OPTIMIZATION - {platform.upper()}:
- Maximum words: {platform_info['max_words']}
- Style: {platform_info['style']}
- Pace: {platform_info['pace']}
- Platform hooks: {', '.join(platform_info['hooks'])}"""
        
        # Build user prompt with movie context
        user_prompt = _build_movie_context_prompt(movie_data, genre, platform)
        
        return system_prompt, user_prompt
        
    except Exception as e:
        logger.error(f"Error building hook prompt template: {str(e)}")
        return BASE_SYSTEM_PROMPTS['hook'], f"Create a hook for: {movie_data.get('title', 'Unknown Movie')}"


def get_intro_prompt_template(genre: Optional[str] = None,
                            platform: Optional[str] = None,
                            content_type: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate intro prompt template for video collection.
    
    Args:
        genre (str): Genre for customization
        platform (str): Target platform
        content_type (str): Content type
        
    Returns:
        Tuple[str, str]: (system_prompt, user_prompt)
    """
    try:
        # Build system prompt
        system_prompt = BASE_SYSTEM_PROMPTS['intro']
        
        # Add genre-specific instructions
        if genre and genre in GENRE_CUSTOMIZATIONS:
            genre_info = GENRE_CUSTOMIZATIONS[genre]
            system_prompt += f"""

GENRE FOCUS - {genre.upper()}:
Create an intro that captures the essence of {genre.lower()} content.
Use tone and language that appeals to {genre.lower()} fans."""
        
        # Build user prompt
        content_desc = content_type if content_type else "movies"
        platform_name = platform if platform else "streaming"
        
        user_prompt = f"""Create a short, engaging introduction for a video showcasing top {genre or 'trending'} {content_desc} from {platform_name}.

Requirements:
- 15-25 words maximum
- 1-2 sentences only
- Must be hooky and grab attention immediately
- Create excitement for what's coming
- Use viral language that makes viewers want to keep watching

Context:
Genre: {genre or 'Mixed'}
Platform: {platform or 'Multiple streaming platforms'}
Content Type: {content_type or 'Movies'}

PREFERRED STYLES (choose one):
- "Here are the top 3 {genre or 'trending'} {content_desc} that will {['blow your mind', 'haunt your dreams', 'keep you on edge'][0] if genre == 'Horror' else 'blow your mind'}!"
- "StreamGank's top 3 {genre or 'trending'} {content_desc} that everyone's talking about!"
- "Get ready for the most {['terrifying', 'incredible', 'amazing'][0] if genre == 'Horror' else 'incredible'} {genre or 'trending'} {content_desc} on {platform_name}!"
- "These 3 {genre or 'trending'} {content_desc} from StreamGank are breaking the internet!"

Create something similar but more engaging and viral."""
        
        return system_prompt, user_prompt
        
    except Exception as e:
        logger.error(f"Error building intro prompt template: {str(e)}")
        return BASE_SYSTEM_PROMPTS['intro'], "Create an engaging intro for a movie collection video."

# =============================================================================
# CONTEXT BUILDING FUNCTIONS
# =============================================================================

def build_context_prompt(context_data: Dict[str, Any]) -> str:
    """
    Build context prompt from various data sources.
    
    Args:
        context_data (Dict): Context information
        
    Returns:
        str: Formatted context prompt
    """
    try:
        context_parts = []
        
        # Add movie information
        if 'movies' in context_data:
            movies = context_data['movies']
            context_parts.append(f"Movies ({len(movies)} total):")
            for i, movie in enumerate(movies[:3]):  # Show first 3
                title = movie.get('title', f'Movie {i+1}')
                year = movie.get('year', 'Unknown')
                imdb = movie.get('imdb_score', 'N/A')
                context_parts.append(f"  {i+1}. {title} ({year}) - IMDb: {imdb}")
        
        # Add genre information
        if 'genre' in context_data and context_data['genre']:
            context_parts.append(f"Genre: {context_data['genre']}")
        
        # Add platform information
        if 'platform' in context_data and context_data['platform']:
            context_parts.append(f"Platform: {context_data['platform']}")
        
        # Add content type
        if 'content_type' in context_data and context_data['content_type']:
            context_parts.append(f"Content Type: {context_data['content_type']}")
        
        # Add target audience
        if 'audience' in context_data and context_data['audience']:
            context_parts.append(f"Target Audience: {context_data['audience']}")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error building context prompt: {str(e)}")
        return "Context information unavailable"


def customize_prompt_for_genre(base_prompt: str, genre: str) -> str:
    """
    Customize a base prompt for a specific genre.
    
    Args:
        base_prompt (str): Base prompt template
        genre (str): Genre for customization
        
    Returns:
        str: Customized prompt
    """
    try:
        if not genre or genre not in GENRE_CUSTOMIZATIONS:
            return base_prompt
        
        genre_info = GENRE_CUSTOMIZATIONS[genre]
        
        # Add genre-specific elements
        customizations = f"""

GENRE-SPECIFIC REQUIREMENTS:
- Tone: {genre.lower()}-focused
- Mood words to consider: {', '.join(genre_info['mood_words'])}
- Viral angles: {', '.join(genre_info['viral_angles'])}
- Engagement style: {', '.join(genre_info['engagement_hooks'])}"""
        
        return base_prompt + customizations
        
    except Exception as e:
        logger.error(f"Error customizing prompt for genre {genre}: {str(e)}")
        return base_prompt

# =============================================================================
# ADVANCED PROMPT FUNCTIONS
# =============================================================================

def get_viral_optimization_prompt(script_type: str = "hook") -> str:
    """
    Get prompt for viral content optimization.
    
    Args:
        script_type (str): Type of script to optimize
        
    Returns:
        str: Viral optimization prompt
    """
    try:
        base_prompt = f"""VIRAL CONTENT OPTIMIZATION FOR {script_type.upper()}:

Your goal is to create content that goes viral on social media platforms.

VIRAL PSYCHOLOGY PRINCIPLES:
1. Curiosity Gap: Create information gaps that viewers MUST fill
2. Pattern Interrupt: Break expected patterns to capture attention
3. Social Proof: Imply popularity or exclusivity
4. Emotional Triggers: Target strong emotional responses
5. Immediate Value: Promise instant gratification

VIRAL LANGUAGE TECHNIQUES:"""
        
        if script_type == "hook":
            base_prompt += """
- Start with power words: {', '.join(VIRAL_ELEMENTS['power_starters'])}
- Use engagement words: {', '.join(VIRAL_ELEMENTS['engagement_words'][:5])}
- Create curiosity gaps that demand completion
- Keep under 18 words for attention span
- End with emotional punch or cliffhanger"""
        
        elif script_type == "intro":
            base_prompt += """
- Open with immediate value proposition
- Build anticipation for what's coming
- Use inclusive language ("we", "you", "together")
- Set clear expectations
- Transition smoothly to main content"""
        
        base_prompt += f"""

AVOID:
- Generic language
- Slow starts
- Over-explanation
- Boring descriptions
- Weak endings

Create {script_type} content that viewers can't scroll past."""
        
        return base_prompt
        
    except Exception as e:
        logger.error(f"Error getting viral optimization prompt: {str(e)}")
        return f"Create viral {script_type} content."


def get_a_b_test_prompts(base_prompt: str, variations: int = 3) -> List[str]:
    """
    Generate multiple prompt variations for A/B testing.
    
    Args:
        base_prompt (str): Base prompt template
        variations (int): Number of variations to generate
        
    Returns:
        List[str]: List of prompt variations
    """
    try:
        variations_list = [base_prompt]  # Include original
        
        # Variation strategies
        strategies = [
            "Focus on emotional impact",
            "Emphasize urgency and scarcity",
            "Use more casual, conversational tone",
            "Add mystery and intrigue elements",
            "Include social proof elements"
        ]
        
        for i in range(min(variations - 1, len(strategies))):
            strategy = strategies[i]
            variation = base_prompt + f"""

ADDITIONAL FOCUS: {strategy}
Incorporate this element while maintaining all other requirements."""
            
            variations_list.append(variation)
        
        return variations_list[:variations]
        
    except Exception as e:
        logger.error(f"Error generating A/B test prompts: {str(e)}")
        return [base_prompt]

# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _build_movie_context_prompt(movie_data: Dict, genre: Optional[str], platform: Optional[str]) -> str:
    """Build detailed movie context for prompts."""
    try:
        # Extract movie information
        title = movie_data.get('title', 'Unknown Movie')
        year = movie_data.get('year', '')
        imdb_score = movie_data.get('imdb_score', 0)
        genres = movie_data.get('genres', [])
        platform_name = movie_data.get('platform', platform or 'streaming')
        
        # Build context
        context_prompt = f"""Create a viral hook sentence for this movie:

Movie: {title}"""
        
        if year:
            context_prompt += f"\nYear: {year}"
        
        if imdb_score and imdb_score > 0:
            context_prompt += f"\nIMDb Score: {imdb_score}/10"
        
        if genres:
            context_prompt += f"\nGenres: {', '.join(genres)}"
        
        context_prompt += f"\nPlatform: {platform_name}"
        
        # Add genre-specific hook starters if available
        hook_starters = "This movie", "You won't believe", "Everyone's talking about", "This is why", "Get ready for", "The moment when"
        if genre and genre in GENRE_CUSTOMIZATIONS and 'hook_starters' in GENRE_CUSTOMIZATIONS[genre]:
            genre_starters = GENRE_CUSTOMIZATIONS[genre]['hook_starters']
            hook_starters = ', '.join([f'"{starter}"' for starter in genre_starters])
        else:
            hook_starters = '"This movie", "You won\'t believe", "Everyone\'s talking about", "This is why", "Get ready for", "The moment when"'
        
        # Add requirements
        context_prompt += f"""

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
        
        return context_prompt
        
    except Exception as e:
        logger.error(f"Error building movie context prompt: {str(e)}")
        return f"Create a hook for: {movie_data.get('title', 'Unknown Movie')}"

# =============================================================================
# TEMPLATE MANAGEMENT FUNCTIONS
# =============================================================================

def get_available_templates() -> Dict[str, List[str]]:
    """
    Get list of available prompt templates.
    
    Returns:
        Dict[str, List[str]]: Available templates by category
    """
    return {
        'hook_templates': ['movie_hook', 'generic_hook', 'viral_hook'],
        'intro_templates': ['collection_intro', 'genre_intro', 'platform_intro'],
        'optimization_templates': ['viral_optimization', 'platform_optimization', 'genre_optimization'],
        'context_templates': ['movie_context', 'batch_context', 'platform_context']
    }


def validate_prompt_template(template: str) -> Dict[str, Any]:
    """
    Validate a prompt template for completeness and quality.
    
    Args:
        template (str): Prompt template to validate
        
    Returns:
        Dict[str, Any]: Validation results
    """
    validation = {
        'is_valid': True,
        'issues': [],
        'suggestions': [],
        'word_count': len(template.split()),
        'has_instructions': False,
        'has_examples': False
    }
    
    try:
        if not template or len(template.strip()) < 50:
            validation['is_valid'] = False
            validation['issues'].append("Template too short")
        
        # Check for instruction words
        instruction_words = ['create', 'generate', 'write', 'make', 'requirements', 'must']
        validation['has_instructions'] = any(word in template.lower() for word in instruction_words)
        
        if not validation['has_instructions']:
            validation['issues'].append("No clear instructions found")
        
        # Check for examples
        example_indicators = ['example:', 'for instance:', 'such as:', 'like:']
        validation['has_examples'] = any(indicator in template.lower() for indicator in example_indicators)
        
        if not validation['has_examples']:
            validation['suggestions'].append("Consider adding examples for clarity")
        
        # Check length
        if validation['word_count'] > 500:
            validation['suggestions'].append("Template might be too long, consider shortening")
        
        return validation
        
    except Exception as e:
        logger.error(f"Error validating prompt template: {str(e)}")
        validation['is_valid'] = False
        validation['issues'].append(f"Validation error: {str(e)}")
        return validation