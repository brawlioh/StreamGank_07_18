"""
StreamGank HeyGen Templates Configuration

This module contains HeyGen template IDs and template selection logic 
based on genre and language preferences.

Template Selection Rules:
- Horror/Horreur genres use specialized horror template
- Comedy/Comédie genres use comedy-optimized template  
- Action/Action & Aventure genres use action template
- All other genres use the default template
"""

import logging

logger = logging.getLogger(__name__)

# =============================================================================
# HEYGEN TEMPLATE CONFIGURATIONS
# =============================================================================

HEYGEN_TEMPLATES = {
    # Horror/Thriller Templates
    'horror': {
        'id': 'ed21a309a5c84b0d873fde68642adea3',
        'name': 'Horror Template',
        'description': 'Specialized template for horror and thriller content',
        'genres': ['Horror', 'Horreur', 'Thriller', 'Mystery & Thriller']
    },
    
    # Comedy Templates  
    'comedy': {
        'id': '15d9eadcb46a45dbbca1834aa0a23ede',
        'name': 'Comedy Template', 
        'description': 'Optimized template for comedy and humorous content',
        'genres': ['Comedy', 'Comédie']
    },
    
    # Action Templates
    'action': {
        'id': '9186cef35dde4505bdccb1ec5c312339',  # Old ID: e44b139a1b94446a997a7f2ac5ac4178
        'name': 'Action Template',
        'description': 'High-energy template for action and adventure content',
        'genres': ['Action', 'Action & Adventure', 'Action & Aventure']
    },
    
    # Default Template
    'default': {
        'id': 'cc6718c5363e42b282a123f99b94b335',
        'name': 'Default Template',
        'description': 'General-purpose template for all other content types',
        'genres': ['*']  # Wildcard for all other genres
    }
}

# =============================================================================
# TEMPLATE SELECTION FUNCTIONS  
# =============================================================================

def get_heygen_template_id(genre: str = None) -> str:
    """
    Get the appropriate HeyGen template ID based on genre.
    
    Supports both English and French genres with case-insensitive matching
    for both UI and CLI workflows.
    
    Args:
        genre (str): Content genre (e.g., 'Horror', 'Comedy', 'Action')
        
    Returns:
        str: HeyGen template ID
        
    Examples:
        >>> get_heygen_template_id('Horror')
        'e2ad0e5c7e71483991536f5c93594e42'
        
        >>> get_heygen_template_id('comedy')  # Case insensitive
        '15d9eadcb46a45dbbca1834aa0a23ede'
        
        >>> get_heygen_template_id('Drama')   # Uses default
        'cc6718c5363e42b282a123f99b94b335'
    """
    logger.info(f"🎭 Selecting HeyGen template for genre: {genre}")
    
    if not genre:
        logger.info("🎭 No genre provided, using default template")
        return HEYGEN_TEMPLATES['default']['id']
    
    # Normalize genre for comparison
    genre_normalized = genre.strip()
    
    # Check each template category
    for template_key, template_info in HEYGEN_TEMPLATES.items():
        if template_key == 'default':
            continue  # Skip default, it's the fallback
            
        # Case-insensitive genre matching
        matching_genres = template_info['genres']
        for template_genre in matching_genres:
            if genre_normalized.lower() == template_genre.lower():
                logger.info(f"🎭 Genre '{genre}' matched template: {template_info['name']} ({template_info['id']})")
                return template_info['id']
    
    # No specific match found, use default
    logger.info(f"🎭 Genre '{genre}' not specifically mapped, using default template")
    return HEYGEN_TEMPLATES['default']['id']


def get_template_info(template_id: str) -> dict:
    """
    Get template information by template ID.
    
    Args:
        template_id (str): HeyGen template ID
        
    Returns:
        dict: Template information or None if not found
    """
    for template_key, template_info in HEYGEN_TEMPLATES.items():
        if template_info['id'] == template_id:
            return template_info
    return None


def list_available_templates() -> dict:
    """
    Get all available HeyGen templates.
    
    Returns:
        dict: All template configurations
    """
    return HEYGEN_TEMPLATES.copy()


def get_templates_by_genre() -> dict:
    """
    Get template mapping organized by genre.
    
    Returns:
        dict: Genre to template ID mapping
    """
    genre_mapping = {}
    
    for template_key, template_info in HEYGEN_TEMPLATES.items():
        template_id = template_info['id']
        
        for genre in template_info['genres']:
            if genre != '*':  # Skip wildcard
                genre_mapping[genre] = template_id
    
    return genre_mapping

# =============================================================================
# TEMPLATE VALIDATION
# =============================================================================

def validate_template_id(template_id: str) -> bool:
    """
    Validate if a template ID exists in our configuration.
    
    Args:
        template_id (str): HeyGen template ID to validate
        
    Returns:
        bool: True if template ID is valid
    """
    valid_ids = [template['id'] for template in HEYGEN_TEMPLATES.values()]
    return template_id in valid_ids


def get_template_for_content(genre: str = None, content_type: str = None, platform: str = None) -> dict:
    """
    Get the best template configuration for specific content parameters.
    
    Args:
        genre (str): Content genre
        content_type (str): Type of content (movie, series, etc.)
        platform (str): Streaming platform
        
    Returns:
        dict: Complete template configuration with metadata
    """
    template_id = get_heygen_template_id(genre)
    template_info = get_template_info(template_id)
    
    if template_info:
        # Add context information
        return {
            'template_id': template_id,
            'template_name': template_info['name'],
            'description': template_info['description'], 
            'selected_for': {
                'genre': genre,
                'content_type': content_type,
                'platform': platform
            }
        }
    
    return {
        'template_id': HEYGEN_TEMPLATES['default']['id'],
        'template_name': 'Default Template',
        'description': 'Fallback template',
        'selected_for': {
            'genre': genre,
            'content_type': content_type,
            'platform': platform
        }
    }