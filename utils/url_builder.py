"""
StreamGank URL Builder Utilities

This module provides functions for building StreamGank URLs with proper
country-specific mappings for genres, platforms, and content types.

The URL builder supports localized parameters and ensures proper formatting
for StreamGank's filtering system.
"""

import logging
from typing import Dict, Optional, List, Tuple
from config.constants import US_GENRE_MAPPING, PLATFORM_MAPPING, CONTENT_TYPES

logger = logging.getLogger(__name__)

# =============================================================================
# GENRE MAPPING FUNCTIONS
# =============================================================================

def get_genre_mapping_by_country(country_code: str) -> Dict[str, str]:
    """
    Get genre mapping dictionary (US-ONLY SIMPLIFIED)
    
    Args:
        country_code (str): Ignored - always returns US English genre mapping
        
    Returns:
        dict: US English genre mapping for StreamGank URLs
        
    Example:
        >>> mapping = get_genre_mapping_by_country('US')
        >>> mapping.get('Horror')   # Returns 'Horror' (no translation needed)
    """
    logger.debug(f"Getting genre mapping for country: {country_code}")
    
    # Always return US English mapping regardless of country_code
    # This is the simplified US-only workflow approach
    return US_GENRE_MAPPING.copy()


def get_available_genres_for_country(country_code: str) -> list:
    """
    Get list of available genres for a specific country.
    
    Args:
        country_code (str): Country code
        
    Returns:
        list: Available genre names
    """
    genre_mapping = get_genre_mapping_by_country(country_code)
    return list(genre_mapping.keys())

# =============================================================================
# PLATFORM MAPPING FUNCTIONS
# =============================================================================

def get_platform_mapping() -> Dict[str, str]:
    """
    Get platform mapping for StreamGank URL parameters.
    
    Returns:
        dict: Platform name to URL parameter mapping
    """
    # Base platform mapping (consistent across most countries)
    base_platforms = {
        'Netflix': 'netflix',
        'Prime Video': 'amazon',
        'Apple TV+': 'apple',
        'Disney+': 'disney',
        'Max': 'max',
        'Hulu': 'hulu',
        'Paramount+': 'paramount',
        'Free': 'free'
    }
    
    return base_platforms


def get_platform_mapping_by_country(country_code: str) -> Dict[str, str]:
    """
    Get platform mapping for a specific country.
    
    Args:
        country_code (str): Country code
        
    Returns:
        dict: Platform mapping dictionary
    """
    logger.debug(f"Getting platform mapping for country: {country_code}")
    
    # Platform mapping is consistent across countries
    return get_platform_mapping()

# =============================================================================
# CONTENT TYPE MAPPING FUNCTIONS
# =============================================================================

def get_content_type_mapping() -> Dict[str, str]:
    """
    Get content type mapping dictionary for StreamGank URL parameters.
    
    Note: Content types are consistent across all supported countries.
    
    Returns:
        dict: Mapping from database content types to StreamGank URL type parameters
        
    Example:
        >>> mapping = get_content_type_mapping()
        >>> mapping.get('Série')    # Returns 'Série' (with accent for URL encoding)
        >>> mapping.get('Émission') # Returns 'Série' (French TV show term)
    """
    # Universal content type mapping (supports both French and English terms)
    return {
        'Film': 'Film',
        'Movie': 'Film',
        'Série': 'Série',  # Keep French accent for proper URL encoding
        'Serie': 'Série',   # Map Serie input to Série for URL encoding
        'Series': 'Série',  # Map English Series to Série for URL encoding
        'TV Show': 'Série',
        'TV Series': 'Série',
        'Émission': 'Série'  # French TV show term
    }


def get_content_type_mapping_by_country(country_code: str) -> Dict[str, str]:
    """
    Get content type mapping for a specific country.
    
    Args:
        country_code (str): Country code
        
    Returns:
        dict: Content type mapping dictionary
    """
    logger.debug(f"Getting content type mapping for country: {country_code}")
    
    # Content type mapping is universal across countries
    return get_content_type_mapping()

# =============================================================================
# URL CONSTRUCTION
# =============================================================================

def build_streamgank_url(country: Optional[str] = None, 
                        genre: Optional[str] = None, 
                        platform: Optional[str] = None, 
                        content_type: Optional[str] = None) -> str:
    """
    Build a complete StreamGank URL with localized parameters based on country.
    
    Args:
        country (str): Country code for localization
        genre (str): Genre to filter by
        platform (str): Platform to filter by  
        content_type (str): Content type to filter by
        
    Returns:
        str: Complete StreamGank URL with properly encoded parameters
        
    Example:
        >>> url = build_streamgank_url('FR', 'Horror', 'Netflix', 'Série')
        >>> print(url)
        https://streamgank.com/?country=FR&genres=Horror&platforms=netflix&type=Serie
        
        >>> url = build_streamgank_url('US', 'Drama', 'Netflix', 'Film')
        >>> print(url)
        https://streamgank.com/?country=US&genres=Drama&platforms=netflix&type=Film
    """
    logger.info(f"Building StreamGank URL: country={country}, genre={genre}, platform={platform}, content_type={content_type}")
    
    base_url = "https://streamgank.com/?"
    url_params = []
    
    # Add country parameter
    if country:
        url_params.append(f"country={country}")
    
    # Add genre parameter with proper mapping
    if genre:
        # Use US-only genre mapping (restored for proper URL formatting)
        genre_mapping = get_genre_mapping_by_country(country)
        streamgank_genre = genre_mapping.get(genre, genre)
        url_params.append(f"genres={streamgank_genre}")
        logger.debug(f"Genre mapped: {genre} -> {streamgank_genre}")
    
    # Add platform parameter with proper mapping  
    if platform:
        # Use country-specific platform mapping
        platform_mapping = get_platform_mapping()
        streamgank_platform = platform_mapping.get(platform, platform.lower())
        url_params.append(f"platforms={streamgank_platform}")
        logger.debug(f"Platform mapped: {platform} -> {streamgank_platform}")
    
    # Add content type parameter with proper mapping
    if content_type:
        # Use universal content type mapping (same across all countries)
        type_mapping = get_content_type_mapping()
        streamgank_type = type_mapping.get(content_type, content_type)
        # URL encode to handle accents (e.g., "Série" -> "S%C3%A9rie")
        import urllib.parse
        encoded_type = urllib.parse.quote(streamgank_type)
        url_params.append(f"type={encoded_type}")
        logger.debug(f"Content type mapped: {content_type} -> {streamgank_type} -> {encoded_type}")
    
    # Construct final URL
    if url_params:
        final_url = base_url + "&".join(url_params)
    else:
        final_url = "https://streamgank.com/"  # Default homepage if no params
    
    logger.info(f"Generated StreamGank URL: {final_url}")
    return final_url

# =============================================================================
# COMPREHENSIVE MAPPING FUNCTIONS
# =============================================================================

def get_all_mappings_for_country(country_code: str) -> Dict[str, Dict[str, str]]:
    """
    Get all mapping dictionaries for a specific country.
    
    Args:
        country_code (str): Country code
        
    Returns:
        dict: Dictionary containing all mappings (genres, platforms, content_types)
    """
    logger.info(f"Getting all mappings for country: {country_code}")
    
    return {
        'genres': get_genre_mapping_by_country(country_code),
        'platforms': get_platform_mapping_by_country(country_code),
        'content_types': get_content_type_mapping_by_country(country_code)
    }

# =============================================================================
# VALIDATION FUNCTIONS  
# =============================================================================

def validate_genre(genre: str, country_code: str = 'US') -> bool:
    """
    Validate if a genre is supported for a specific country.
    
    Args:
        genre (str): Genre to validate
        country_code (str): Country code
        
    Returns:
        bool: True if genre is valid
    """
    genre_mapping = get_genre_mapping_by_country(country_code)
    return genre in genre_mapping


def validate_platform(platform: str, country_code: str = 'US') -> bool:
    """
    Validate if a platform is supported for a specific country.
    
    Args:
        platform (str): Platform to validate
        country_code (str): Country code
        
    Returns:
        bool: True if platform is valid
    """
    platform_mapping = get_platform_mapping_by_country(country_code)
    return platform in platform_mapping


def validate_content_type(content_type: str) -> bool:
    """
    Validate if a content type is supported.
    
    Args:
        content_type (str): Content type to validate
        
    Returns:
        bool: True if content type is valid
    """
    mapping = get_content_type_mapping()
    return content_type in mapping


def get_available_platforms_for_country(country_code: str) -> List[str]:
    """
    Get list of available platforms for a specific country.
    
    This function provides a list of streaming platforms available in the specified country.
    For the simplified US-only workflow, all platforms are available for all countries.
    
    Args:
        country_code (str): Country code (e.g., 'US', 'FR', 'DE')
        
    Returns:
        List[str]: List of available platform names
        
    Example:
        >>> platforms = get_available_platforms_for_country('US')
        >>> print(platforms)
        ['Netflix', 'Max', 'Prime Video', 'Disney+', 'Apple TV+', ...]
    """
    logger.debug(f"Getting available platforms for country: {country_code}")
    
    # Get platform mapping for the country
    platform_mapping = get_platform_mapping_by_country(country_code)
    available_platforms = list(platform_mapping.keys())
    
    logger.debug(f"Found {len(available_platforms)} platforms for {country_code}")
    return available_platforms


def get_supported_countries() -> list:
    """
    Get list of supported country codes.
    
    Returns:
        list: Supported country codes
    """
    # For now, we support US-only workflow, but keeping structure for future expansion
    return ['US', 'FR', 'DE', 'IT', 'ES', 'PT', 'GB', 'CA']


# =============================================================================
# ADVANCED URL BUILDING AND VALIDATION
# =============================================================================

def build_advanced_streamgank_url(filters: Dict[str, str], 
                                  validate_params: bool = True) -> Dict[str, str]:
    """
    Build advanced StreamGank URLs with STRICT validation - NO FALLBACKS.
    
    Features:
    - Primary URL with all filters
    - Parameter validation and correction
    - URL optimization for different scenarios
    - STRICT MODE: Process stops if any validation fails
    
    Args:
        filters (Dict): Filter parameters (country, genre, platform, content_type)
        validate_params (bool): Whether to validate parameters
        
    Returns:
        Dict[str, str]: Dictionary with primary URL and validation info
        
    Raises:
        ValueError: If parameter validation fails
        RuntimeError: If URL building fails
    """
    logger.info(f"🔗 STRICT URL BUILDING: {len(filters)} filters - NO FALLBACKS")
    
    result = {
        'primary_url': '',
        'validation_errors': [],
        'applied_corrections': []
    }
    
    # Validate and correct parameters if requested
    if validate_params:
        filters, corrections, errors = _validate_and_correct_params(filters)
        result['applied_corrections'] = corrections
        result['validation_errors'] = errors
        
        # STRICT MODE: Stop if validation errors exist
        if errors:
            error_msg = f"Parameter validation failed: {'; '.join(errors)}"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise ValueError(error_msg)
    
    # Build primary URL with all filters
    primary_url = build_streamgank_url(
        country=filters.get('country'),
        genre=filters.get('genre'),
        platform=filters.get('platform'),
        content_type=filters.get('content_type')
    )
    
    if not primary_url:
        raise RuntimeError("❌ CRITICAL: Failed to build StreamGank URL")
    
    result['primary_url'] = primary_url
    
    logger.info(f"✅ STRICT URL built successfully: {primary_url}")
    return result


def build_url_variations(base_filters: Dict[str, str], 
                        variation_type: str = "platform") -> List[str]:
    """
    Build URL variations for A/B testing or content discovery.
    
    Args:
        base_filters (Dict): Base filter parameters
        variation_type (str): Type of variation (platform, genre, content_type)
        
    Returns:
        List[str]: List of URL variations
    """
    try:
        variations = []
        
        if variation_type == "platform":
            # Generate variations with different platforms
            platforms = get_available_platforms_for_country(base_filters.get('country', 'US'))
            
            for platform in platforms[:5]:  # Limit to top 5 platforms
                if platform != base_filters.get('platform'):
                    variant_filters = base_filters.copy()
                    variant_filters['platform'] = platform
                    
                    url = build_streamgank_url(**variant_filters)
                    variations.append(url)
        
        elif variation_type == "genre":
            # Generate variations with different genres
            genres = get_available_genres_for_country(base_filters.get('country', 'US'))
            
            for genre in genres[:5]:  # Limit to top 5 genres
                if genre != base_filters.get('genre'):
                    variant_filters = base_filters.copy()
                    variant_filters['genre'] = genre
                    
                    url = build_streamgank_url(**variant_filters)
                    variations.append(url)
        
        elif variation_type == "content_type":
            # Generate variations with different content types
            content_types = ['Film', 'Serie']
            
            for content_type in content_types:
                if content_type != base_filters.get('content_type'):
                    variant_filters = base_filters.copy()
                    variant_filters['content_type'] = content_type
                    
                    url = build_streamgank_url(**variant_filters)
                    variations.append(url)
        
        logger.info(f"🔀 Generated {len(variations)} {variation_type} variations")
        return variations
        
    except Exception as e:
        logger.error(f"❌ Error generating URL variations: {str(e)}")
        return []


def optimize_url_for_content(url: str, optimization_type: str = "performance") -> str:
    """
    Optimize URL for specific use cases.
    
    Args:
        url (str): Original URL
        optimization_type (str): Type of optimization (performance, mobile, accessibility)
        
    Returns:
        str: Optimized URL
    """
    try:
        if optimization_type == "performance":
            # Add performance optimization parameters
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}cache=1&optimize=true"
        
        elif optimization_type == "mobile":
            # Add mobile optimization
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}mobile=1&touch=true"
        
        elif optimization_type == "accessibility":
            # Add accessibility features
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}a11y=1&contrast=high"
        
        return url
        
    except Exception as e:
        logger.error(f"❌ Error optimizing URL: {str(e)}")
        return url


def extract_filters_from_url(url: str) -> Dict[str, str]:
    """
    Extract filter parameters from a StreamGank URL.
    
    Args:
        url (str): StreamGank URL
        
    Returns:
        Dict[str, str]: Extracted filter parameters
    """
    try:
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        filters = {}
        
        # Extract standard parameters
        if 'country' in params:
            filters['country'] = params['country'][0]
        
        if 'genres' in params:
            filters['genre'] = params['genres'][0]
        
        if 'platforms' in params:
            filters['platform'] = params['platforms'][0]
            
            # Reverse map platform parameter to display name
            platform_mapping = get_platform_mapping()
            for display_name, url_param in platform_mapping.items():
                if url_param == filters['platform']:
                    filters['platform'] = display_name
                    break
        
        if 'type' in params:
            filters['content_type'] = params['type'][0]
            
            # Reverse map content type parameter
            content_mapping = get_content_type_mapping()
            for display_name, url_param in content_mapping.items():
                if url_param == filters['content_type']:
                    filters['content_type'] = display_name
                    break
        
        logger.debug(f"Extracted filters from URL: {filters}")
        return filters
        
    except Exception as e:
        logger.error(f"❌ Error extracting filters from URL: {str(e)}")
        return {}


def validate_streamgank_url(url: str) -> Dict[str, any]:
    """
    Validate a StreamGank URL and its parameters.
    
    Args:
        url (str): URL to validate
        
    Returns:
        Dict: Validation results with details
    """
    try:
        from urllib.parse import urlparse
        
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'extracted_filters': {},
            'recommendations': []
        }
        
        # Basic URL validation
        parsed = urlparse(url)
        if not parsed.netloc:
            validation['is_valid'] = False
            validation['errors'].append('Invalid URL format')
            return validation
        
        if 'streamgank.com' not in parsed.netloc:
            validation['warnings'].append('URL is not for StreamGank domain')
        
        # Extract and validate filters
        filters = extract_filters_from_url(url)
        validation['extracted_filters'] = filters
        
        # Validate individual parameters
        if 'genre' in filters:
            if not validate_genre(filters['genre']):
                validation['warnings'].append(f"Genre '{filters['genre']}' may not be supported")
        
        if 'platform' in filters:
            if not validate_platform(filters['platform']):
                validation['warnings'].append(f"Platform '{filters['platform']}' may not be supported")
        
        if 'content_type' in filters:
            if not validate_content_type(filters['content_type']):
                validation['warnings'].append(f"Content type '{filters['content_type']}' may not be supported")
        
        # Generate recommendations
        if not filters:
            validation['recommendations'].append('Consider adding filters for more targeted results')
        
        if len(filters) == 1:
            validation['recommendations'].append('Adding more filters can improve content relevance')
        
        return validation
        
    except Exception as e:
        return {
            'is_valid': False,
            'errors': [str(e)],
            'warnings': [],
            'extracted_filters': {},
            'recommendations': []
        }


# =============================================================================
# HELPER FUNCTIONS FOR ADVANCED URL BUILDING
# =============================================================================

def _validate_and_correct_params(filters: Dict[str, str]) -> Tuple[Dict[str, str], List[str], List[str]]:
    """
    Validate and correct filter parameters.
    """
    corrected_filters = filters.copy()
    corrections = []
    errors = []
    
    try:
        # Validate and correct genre
        if 'genre' in filters and filters['genre']:
            if not validate_genre(filters['genre']):
                # Try to find a close match
                available_genres = get_available_genres_for_country('US')
                for genre in available_genres:
                    if genre.lower() in filters['genre'].lower() or filters['genre'].lower() in genre.lower():
                        corrected_filters['genre'] = genre
                        corrections.append(f"Genre corrected: {filters['genre']} → {genre}")
                        break
                else:
                    errors.append(f"Genre '{filters['genre']}' not found")
        
        # Validate and correct platform
        if 'platform' in filters and filters['platform']:
            if not validate_platform(filters['platform']):
                # Try common platform name variations
                platform_corrections = {
                    'amazon': 'Prime Video',
                    'prime': 'Prime Video',
                    'disney': 'Disney+',
                    'hbo': 'Max',
                    'apple': 'Apple TV+'
                }
                
                platform_lower = filters['platform'].lower()
                if platform_lower in platform_corrections:
                    corrected_filters['platform'] = platform_corrections[platform_lower]
                    corrections.append(f"Platform corrected: {filters['platform']} → {platform_corrections[platform_lower]}")
                else:
                    errors.append(f"Platform '{filters['platform']}' not found")
        
        return corrected_filters, corrections, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return corrected_filters, corrections, errors


# FALLBACK FUNCTIONS REMOVED - STRICT MODE ONLY
# No fallbacks allowed - process must succeed or fail completely


def get_popular_filter_combinations(country: str = 'US') -> List[Dict[str, str]]:
    """
    Get popular filter combinations for a country.
    
    Args:
        country (str): Country code
        
    Returns:
        List[Dict]: Popular filter combinations
    """
    # Popular combinations based on typical user behavior
    popular_combinations = [
        {'genre': 'Action', 'platform': 'Netflix', 'content_type': 'Film'},
        {'genre': 'Horror', 'platform': 'Max', 'content_type': 'Film'},
        {'genre': 'Comedy', 'platform': 'Netflix', 'content_type': 'Serie'},
        {'genre': 'Drama', 'platform': 'Prime Video', 'content_type': 'Film'},
        {'genre': 'Thriller', 'platform': 'Netflix', 'content_type': 'Film'},
    ]
    
    # Add country to each combination
    for combo in popular_combinations:
        combo['country'] = country
    
    return popular_combinations