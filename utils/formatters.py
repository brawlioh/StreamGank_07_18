"""
StreamGank Text Formatting Utilities

This module provides text formatting, sanitization, and content processing
functions used throughout the StreamGank system.
"""

import re
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# SCRIPT TEXT FORMATTING
# =============================================================================

def sanitize_script_text(text: str) -> str:
    """
    Sanitize script text for AI avatar generation.
    
    Removes problematic characters and formatting that could cause issues
    with HeyGen or other AI services.
    
    Args:
        text (str): Raw script text
        
    Returns:
        str: Sanitized script text
    """
    if not isinstance(text, str):
        return ""
    
    # Remove or replace problematic characters
    sanitized = text.strip()
    
    # Remove various quote styles that could cause JSON issues
    sanitized = sanitized.replace('"', '').replace("'", "").replace('`', '')
    sanitized = sanitized.replace('"', '').replace('"', '')  # Smart quotes
    sanitized = sanitized.replace(''', '').replace(''', '')  # Smart apostrophes
    
    # Normalize whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = sanitized.strip()
    
    # Ensure proper sentence ending
    if sanitized and not sanitized.endswith(('.', '!', '?')):
        sanitized += "!"
    
    # Remove any remaining problematic patterns
    sanitized = re.sub(r'[^\w\s\.\!\?\,\-\:\;\&]', '', sanitized)
    
    logger.debug(f"Sanitized text: '{text}' -> '{sanitized}'")
    return sanitized


def format_hook_sentence(text: str, max_words: int = 18) -> str:
    """
    Format a hook sentence to meet specific requirements.
    
    Args:
        text (str): Raw hook text
        max_words (int): Maximum number of words allowed
        
    Returns:
        str: Formatted hook sentence
    """
    if not isinstance(text, str):
        return ""
    
    # Sanitize first
    formatted = sanitize_script_text(text)
    
    # Split into words and limit
    words = formatted.split()
    if len(words) > max_words:
        formatted = ' '.join(words[:max_words])
        logger.info(f"Hook truncated from {len(words)} to {max_words} words")
    
    # Ensure it ends with proper punctuation for excitement
    if formatted and not formatted.endswith(('!', '?')):
        if formatted.endswith('.'):
            formatted = formatted[:-1] + '!'
        else:
            formatted += '!'
    
    return formatted


def format_intro_text(text: str, max_words: int = 25) -> str:
    """
    Format intro text to meet specific requirements.
    
    Args:
        text (str): Raw intro text
        max_words (int): Maximum number of words allowed
        
    Returns:
        str: Formatted intro text
    """
    if not isinstance(text, str):
        return ""
    
    # Sanitize first
    formatted = sanitize_script_text(text)
    
    # Split into words and limit
    words = formatted.split()
    if len(words) > max_words:
        formatted = ' '.join(words[:max_words])
        logger.info(f"Intro truncated from {len(words)} to {max_words} words")
    
    # Ensure proper ending for energy
    if formatted and not formatted.endswith(('!', '?')):
        if formatted.endswith('.'):
            formatted = formatted[:-1] + '!'
        else:
            formatted += '!'
    
    return formatted

# =============================================================================
# MOVIE TITLE FORMATTING
# =============================================================================

def format_movie_title(title: str, max_length: int = 50) -> str:
    """
    Format movie title for display and processing.
    
    Args:
        title (str): Raw movie title
        max_length (int): Maximum length for title
        
    Returns:
        str: Formatted movie title
    """
    if not isinstance(title, str):
        return "Unknown Title"
    
    # Clean and normalize
    formatted = title.strip()
    
    # Remove excessive whitespace
    formatted = re.sub(r'\s+', ' ', formatted)
    
    # Remove problematic characters for file names
    formatted = re.sub(r'[<>:"/\\|?*]', '', formatted)
    
    # Truncate if too long
    if len(formatted) > max_length:
        formatted = formatted[:max_length-3] + "..."
        logger.debug(f"Title truncated: '{title}' -> '{formatted}'")
    
    # Ensure we have something
    if not formatted:
        formatted = "Unknown Title"
    
    return formatted


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format.
    
    Args:
        seconds (float): Duration in seconds
        
    Returns:
        str: Formatted duration (e.g., "2:34", "1:23:45")
    """
    if not isinstance(seconds, (int, float)) or seconds < 0:
        return "0:00"
    
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

# =============================================================================
# TEXT PROCESSING UTILITIES
# =============================================================================

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length with optional suffix.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length including suffix
        suffix (str): Suffix to add when truncating
        
    Returns:
        str: Truncated text
    """
    if not isinstance(text, str):
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Account for suffix length
    truncate_length = max_length - len(suffix)
    if truncate_length <= 0:
        return suffix[:max_length]
    
    return text[:truncate_length] + suffix


def clean_text_for_display(text: str) -> str:
    """
    Clean text for safe display in logs and UI.
    
    Args:
        text (str): Raw text
        
    Returns:
        str: Cleaned text safe for display
    """
    if not isinstance(text, str):
        return ""
    
    # Remove control characters
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove potentially problematic Unicode
    cleaned = cleaned.encode('ascii', 'ignore').decode('ascii')
    
    return cleaned.strip()


def extract_words(text: str, max_words: int = None) -> list:
    """
    Extract words from text with optional limit.
    
    Args:
        text (str): Text to process
        max_words (int): Maximum number of words to return
        
    Returns:
        list: List of words
    """
    if not isinstance(text, str):
        return []
    
    # Split into words, removing empty strings
    words = [word.strip() for word in text.split() if word.strip()]
    
    if max_words and len(words) > max_words:
        words = words[:max_words]
    
    return words


def count_words(text: str) -> int:
    """
    Count words in text.
    
    Args:
        text (str): Text to count
        
    Returns:
        int: Number of words
    """
    if not isinstance(text, str):
        return 0
    
    return len(extract_words(text))

# =============================================================================
# FILE NAME FORMATTING
# =============================================================================

def clean_filename(filename: str, max_length: int = 255) -> str:
    """
    Clean filename for safe file system usage.
    
    Args:
        filename (str): Raw filename
        max_length (int): Maximum filename length
        
    Returns:
        str: Safe filename
    """
    if not isinstance(filename, str):
        return "untitled"
    
    # Remove or replace problematic characters
    cleaned = filename.strip()
    
    # Replace problematic characters with underscores
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', cleaned)
    
    # Replace multiple underscores with single
    cleaned = re.sub(r'_+', '_', cleaned)
    
    # Remove leading/trailing dots and spaces (Windows issues)
    cleaned = cleaned.strip('. ')
    
    # Ensure reasonable length
    if len(cleaned) > max_length:
        name, ext = Path(cleaned).stem, Path(cleaned).suffix
        max_name_length = max_length - len(ext)
        cleaned = name[:max_name_length] + ext
    
    # Ensure we have something
    if not cleaned:
        cleaned = "untitled"
    
    return cleaned


def generate_unique_filename(base_name: str, extension: str = "", timestamp: bool = True) -> str:
    """
    Generate a unique filename with optional timestamp.
    
    Args:
        base_name (str): Base filename
        extension (str): File extension (with or without dot)
        timestamp (bool): Whether to add timestamp
        
    Returns:
        str: Unique filename
    """
    import time
    
    # Clean base name
    clean_base = clean_filename(base_name)
    
    # Ensure extension starts with dot
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    
    # Add timestamp if requested
    if timestamp:
        timestamp_str = str(int(time.time()))
        filename = f"{clean_base}_{timestamp_str}{extension}"
    else:
        filename = f"{clean_base}{extension}"
    
    return filename

# =============================================================================
# CONTENT FORMATTING
# =============================================================================

def format_genre_list(genres: list, max_display: int = 3) -> str:
    """
    Format list of genres for display.
    
    Args:
        genres (list): List of genre strings
        max_display (int): Maximum genres to display
        
    Returns:
        str: Formatted genre string
    """
    if not isinstance(genres, list) or not genres:
        return "Unknown"
    
    # Clean and deduplicate
    clean_genres = []
    for genre in genres:
        if isinstance(genre, str) and genre.strip():
            clean_genre = genre.strip()
            if clean_genre not in clean_genres:
                clean_genres.append(clean_genre)
    
    if not clean_genres:
        return "Unknown"
    
    # Limit display count
    if len(clean_genres) > max_display:
        displayed = clean_genres[:max_display]
        return ", ".join(displayed) + f" (+{len(clean_genres) - max_display} more)"
    
    return ", ".join(clean_genres)


def format_platform_name(platform: str) -> str:
    """
    Format platform name for consistent display.
    
    Args:
        platform (str): Raw platform name
        
    Returns:
        str: Formatted platform name
    """
    if not isinstance(platform, str):
        return "Unknown Platform"
    
    # Common platform name mappings
    platform_mappings = {
        'netflix': 'Netflix',
        'amazon': 'Prime Video',
        'prime video': 'Prime Video',
        'disney+': 'Disney+',
        'disneyplus': 'Disney+',
        'max': 'Max',
        'hbo max': 'Max',
        'apple tv+': 'Apple TV+',
        'appletv': 'Apple TV+',
        'hulu': 'Hulu',
        'paramount+': 'Paramount+',
        'paramount plus': 'Paramount+'
    }
    
    platform_lower = platform.strip().lower()
    return platform_mappings.get(platform_lower, platform.strip())


def format_content_type(content_type: str) -> str:
    """
    Format content type for consistent display.
    
    Args:
        content_type (str): Raw content type
        
    Returns:
        str: Formatted content type
    """
    if not isinstance(content_type, str):
        return "Unknown"
    
    # Common content type mappings
    type_mappings = {
        'film': 'Movie',
        'movie': 'Movie',
        'série': 'Series',
        'series': 'Series',
        'tv show': 'Series',
        'show': 'Series',
        'émission': 'Series'
    }
    
    type_lower = content_type.strip().lower()
    return type_mappings.get(type_lower, content_type.strip().title())


# =============================================================================
# ADVANCED NUMERIC AND MEDIA FORMATTING
# =============================================================================

def format_votes(votes: int) -> str:
    """
    🔧 COMPREHENSIVE VOTE FORMATTING - Support thousands AND millions with smart scaling.
    
    This is the advanced vote formatter used throughout StreamGank for consistent
    IMDb vote display with intelligent scaling and formatting.
    
    Args:
        votes (int): Number of votes to format
        
    Returns:
        str: Formatted vote count (e.g., "8.2k", "1.5M", "156M")
        
    Examples:
        >>> format_votes(800)      # "800"
        >>> format_votes(8240)     # "8.2k" 
        >>> format_votes(82400)    # "82k"
        >>> format_votes(1500000)  # "1.5M"
        >>> format_votes(15000000) # "15.0M"
        >>> format_votes(156000000)# "156M"
    """
    if not isinstance(votes, (int, float)):
        return str(votes)
    
    votes = int(votes)  # Ensure integer for proper formatting

    if votes < 1000:
        # Less than 1000: Show as-is (e.g., 800 → "800")
        return str(votes)
    elif votes < 10000:
        # 1000-9999: Show as X.Xk (e.g., 8240 → "8.2k")
        return f"{votes/1000:.1f}k"
    elif votes < 1000000:
        # 10000-999999: Show as XXXk (e.g., 82400 → "82k", 234567 → "235k")  
        return f"{int(votes/1000)}k"
    elif votes < 10000000:
        # 1M-9.9M: Show as X.XM (e.g., 1500000 → "1.5M", 8240000 → "8.2M")
        return f"{votes/1000000:.1f}M"
    elif votes < 100000000:
        # 10M-99.9M: Show as XX.XM (e.g., 15000000 → "15.0M", 25600000 → "25.6M")
        return f"{votes/1000000:.1f}M"
    else:
        # 100M+: Show as XXXM (e.g., 156000000 → "156M")
        return f"{int(votes/1000000)}M"


def format_rating(rating: float, max_rating: float = 10.0) -> str:
    """
    Format rating with consistent decimal places.
    
    Args:
        rating (float): Rating value
        max_rating (float): Maximum possible rating
        
    Returns:
        str: Formatted rating (e.g., "8.7/10", "4.2/5")
    """
    if not isinstance(rating, (int, float)):
        return "N/A"
    
    if rating <= 0:
        return "N/A"
    
    # Format with one decimal place
    formatted_rating = f"{rating:.1f}"
    
    # Include max rating for context
    if max_rating != 10.0:
        return f"{formatted_rating}/{max_rating:.0f}"
    else:
        return f"{formatted_rating}/10"


def format_runtime(minutes: int) -> str:
    """
    Format runtime minutes to human-readable format.
    
    Args:
        minutes (int): Runtime in minutes
        
    Returns:
        str: Formatted runtime (e.g., "125 min", "2h 5m")
    """
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        return "Unknown"
    
    minutes = int(minutes)
    
    if minutes < 60:
        return f"{minutes} min"
    else:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}m"


def format_year(year: any) -> str:
    """
    Format year for consistent display.
    
    Args:
        year: Year value (int, str, or other)
        
    Returns:
        str: Formatted year or "Unknown" if invalid
    """
    try:
        year_int = int(year)
        
        # Reasonable year range
        if 1900 <= year_int <= 2030:
            return str(year_int)
        else:
            return "Unknown"
    except (ValueError, TypeError):
        return "Unknown"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format percentage with specified decimal places.
    
    Args:
        value (float): Percentage value (0-100)
        decimal_places (int): Number of decimal places
        
    Returns:
        str: Formatted percentage (e.g., "85.7%")
    """
    if not isinstance(value, (int, float)):
        return "N/A"
    
    return f"{value:.{decimal_places}f}%"


def format_file_size(bytes_size: int) -> str:
    """
    Format file size in bytes to human-readable format.
    
    Args:
        bytes_size (int): Size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.5 MB", "2.3 GB")
    """
    if not isinstance(bytes_size, (int, float)) or bytes_size < 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(bytes_size)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:  # Bytes
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


# =============================================================================
# ADVANCED TEXT PROCESSING AND VIRAL CONTENT FORMATTING
# =============================================================================

def format_viral_text(text: str, platform: str = "TikTok") -> str:
    """
    Format text for viral social media content with platform-specific optimization.
    
    Args:
        text (str): Original text
        platform (str): Target platform (TikTok, Instagram, YouTube)
        
    Returns:
        str: Optimized viral text
    """
    if not isinstance(text, str):
        return ""
    
    formatted = text.strip()
    
    # Platform-specific optimizations
    if platform.lower() in ['tiktok', 'instagram']:
        # Ultra-short format for mobile-first platforms
        words = formatted.split()
        if len(words) > 12:
            formatted = ' '.join(words[:12]) + '!'
        
        # Ensure ends with excitement
        if not formatted.endswith(('!', '?')):
            formatted = formatted.rstrip('.') + '!'
    
    elif platform.lower() == 'youtube':
        # Slightly longer format for YouTube
        words = formatted.split()
        if len(words) > 18:
            formatted = ' '.join(words[:18]) + '!'
    
    return formatted


def add_viral_elements(text: str, enhancement_type: str = "engagement") -> str:
    """
    Add viral elements to text for increased engagement.
    
    Args:
        text (str): Original text
        enhancement_type (str): Type of enhancement (engagement, curiosity, emotion)
        
    Returns:
        str: Enhanced text with viral elements
    """
    if not isinstance(text, str) or not text.strip():
        return text
    
    enhanced = text.strip()
    
    if enhancement_type == "engagement":
        # Add engagement hooks
        engagement_starters = ["You won't believe", "This will shock you", "Wait until you see"]
        if not any(starter.lower() in enhanced.lower() for starter in engagement_starters):
            if len(enhanced.split()) < 12:
                import random
                starter = random.choice(engagement_starters)
                enhanced = f"{starter}: {enhanced.lower()}"
    
    elif enhancement_type == "curiosity":
        # Add curiosity gaps
        if not enhanced.endswith('?') and len(enhanced.split()) < 15:
            enhanced = enhanced.rstrip('.!') + "?"
    
    elif enhancement_type == "emotion":
        # Add emotional amplifiers
        if not enhanced.endswith('!') and len(enhanced.split()) < 15:
            enhanced = enhanced.rstrip('.') + "!"
    
    return enhanced


def smart_truncate(text: str, max_length: int, preserve_words: bool = True) -> str:
    """
    Smart text truncation that preserves word boundaries and meaning.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        preserve_words (bool): Whether to preserve word boundaries
        
    Returns:
        str: Smartly truncated text
    """
    if not isinstance(text, str) or len(text) <= max_length:
        return text
    
    if preserve_words:
        # Find the last complete word that fits
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.7:  # If we can preserve most of the text
            return truncated[:last_space] + "..."
    
    # Fallback to character truncation
    return text[:max_length-3] + "..."


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text.
    
    Args:
        text (str): Text containing hashtags
        
    Returns:
        List[str]: List of hashtags (without #)
    """
    if not isinstance(text, str):
        return []
    
    import re
    hashtags = re.findall(r'#(\w+)', text)
    return hashtags


def generate_hashtags(title: str, genres: List[str], platform: str = "TikTok") -> List[str]:
    """
    Generate relevant hashtags for movie content.
    
    Args:
        title (str): Movie title
        genres (List[str]): Movie genres
        platform (str): Target platform
        
    Returns:
        List[str]: Generated hashtags
    """
    hashtags = []
    
    # Platform-specific base tags
    platform_tags = {
        'TikTok': ['fyp', 'viral', 'trending', 'moviereview'],
        'Instagram': ['explore', 'reels', 'movies', 'entertainment'],
        'YouTube': ['shorts', 'movies', 'review', 'recommendation']
    }
    
    hashtags.extend(platform_tags.get(platform, platform_tags['TikTok']))
    
    # Genre-based tags
    if genres:
        for genre in genres[:2]:  # Max 2 genre tags
            hashtags.append(genre.lower().replace(' ', ''))
    
    # General movie tags
    hashtags.extend(['movies', 'film', 'cinema', 'mustwatch'])
    
    return hashtags[:10]  # Limit to 10 hashtags