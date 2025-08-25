"""
StreamGank Database Query Filters

This module provides query building and filtering utilities for the Supabase
database operations, handling complex joins and parameter filtering.
"""

import logging
from typing import Optional, Any
from supabase import Client

logger = logging.getLogger(__name__)

# =============================================================================
# QUERY BUILDING FUNCTIONS
# =============================================================================

def build_movie_query(supabase_client: Client):
    """
    Build the base movie query with all necessary joins.
    
    This creates the foundation query that includes:
    - Main movie data (ID, scores, runtime, etc.)
    - Localization data (titles, URLs, platform info)
    - Genre information
    
    Args:
        supabase_client (Client): Supabase client instance
        
    Returns:
        Query: Base query object ready for filtering and execution
    """
    logger.debug("🔨 Building base movie query with joins")
    
    # Build comprehensive query with all needed fields
    query = supabase_client.from_("movies").select("""
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
    
    logger.debug("✅ Base query built with movies, localizations, and genres joins")
    return query


def apply_filters(query, 
                 content_type: Optional[str] = None,
                 country: Optional[str] = None,
                 platform: Optional[str] = None,
                 genre: Optional[str] = None):
    """
    Apply filtering conditions to the movie query.
    
    Args:
        query: Base query object to filter
        content_type (str): Filter by content type (Film, Série, etc.)
        country (str): Filter by country code (US, FR, etc.)
        platform (str): Filter by platform name (Netflix, Max, etc.)
        genre (str): Filter by genre (Horror, Comedy, etc.)
        
    Returns:
        Query: Filtered query object
    """
    logger.debug(f"🔍 Applying filters: content_type={content_type}, country={country}, platform={platform}, genre={genre}")
    
    filters_applied = []
    
    # Apply content type filter
    if content_type:
        query = query.eq("content_type", content_type)
        filters_applied.append(f"content_type={content_type}")
    
    # Apply country filter (via localization join)
    if country:
        query = query.eq("movie_localizations.country_code", country)
        filters_applied.append(f"country={country}")
    
    # Apply platform filter (via localization join)
    if platform:
        query = query.eq("movie_localizations.platform_name", platform)
        filters_applied.append(f"platform={platform}")
    
    # Apply genre filter (via genre join)
    if genre:
        query = query.eq("movie_genres.genre", genre)
        filters_applied.append(f"genre={genre}")
    
    if filters_applied:
        logger.debug(f"✅ Applied filters: {', '.join(filters_applied)}")
    else:
        logger.debug("ℹ️ No filters applied - returning all movies")
    
    return query


def apply_content_filters(query, content_type: Optional[str] = None):
    """
    Apply content type specific filters.
    
    Args:
        query: Query object to filter
        content_type (str): Content type to filter by
        
    Returns:
        Query: Filtered query object
    """
    if not content_type:
        return query
    
    logger.debug(f"🎬 Applying content type filter: {content_type}")
    
    # Normalize content type variations
    content_type_mapping = {
        'Movie': 'Film',
        'Series': 'Série',
        'TV Show': 'Série',
        'Show': 'Série'
    }
    
    normalized_type = content_type_mapping.get(content_type, content_type)
    
    if normalized_type != content_type:
        logger.debug(f"📝 Content type normalized: {content_type} -> {normalized_type}")
    
    return query.eq("content_type", normalized_type)


def apply_localization_filters(query, 
                             country: Optional[str] = None,
                             platform: Optional[str] = None):
    """
    Apply localization-related filters (country and platform).
    
    Args:
        query: Query object to filter
        country (str): Country code filter
        platform (str): Platform name filter
        
    Returns:
        Query: Filtered query object
    """
    filters_applied = []
    
    if country:
        query = query.eq("movie_localizations.country_code", country)
        filters_applied.append(f"country={country}")
        logger.debug(f"🌍 Applied country filter: {country}")
    
    if platform:
        query = query.eq("movie_localizations.platform_name", platform)
        filters_applied.append(f"platform={platform}")
        logger.debug(f"📺 Applied platform filter: {platform}")
    
    if filters_applied:
        logger.debug(f"✅ Applied localization filters: {', '.join(filters_applied)}")
    
    return query


def apply_genre_filters(query, genre: Optional[str] = None):
    """
    Apply genre-specific filters.
    
    Args:
        query: Query object to filter
        genre (str): Genre to filter by
        
    Returns:
        Query: Filtered query object
    """
    if not genre:
        return query
    
    logger.debug(f"🎭 Applying genre filter: {genre}")
    
    # Handle genre variations and mappings
    genre_mapping = {
        'Sci-Fi': 'Science-Fiction',
        'SciFi': 'Science-Fiction',
        'Thriller': 'Mystery & Thriller',
        'Family': 'Kids & Family',
        'Musical': 'Music & Musical'
    }
    
    normalized_genre = genre_mapping.get(genre, genre)
    
    if normalized_genre != genre:
        logger.debug(f"📝 Genre normalized: {genre} -> {normalized_genre}")
    
    return query.eq("movie_genres.genre", normalized_genre)

# =============================================================================
# ADVANCED FILTERING FUNCTIONS
# =============================================================================

def apply_quality_filters(query, 
                         min_imdb_score: float = 0.0,
                         min_votes: int = 0,
                         max_runtime: int = None):
    """
    Apply quality-based filters (IMDB score, votes, runtime).
    
    Args:
        query: Query object to filter
        min_imdb_score (float): Minimum IMDB score
        min_votes (int): Minimum number of IMDB votes
        max_runtime (int): Maximum runtime in minutes
        
    Returns:
        Query: Filtered query object
    """
    filters_applied = []
    
    if min_imdb_score > 0:
        query = query.gte("imdb_score", min_imdb_score)
        filters_applied.append(f"imdb_score>={min_imdb_score}")
    
    if min_votes > 0:
        query = query.gte("imdb_votes", min_votes)
        filters_applied.append(f"votes>={min_votes}")
    
    if max_runtime:
        query = query.lte("runtime", max_runtime)
        filters_applied.append(f"runtime<={max_runtime}")
    
    if filters_applied:
        logger.debug(f"⭐ Applied quality filters: {', '.join(filters_applied)}")
    
    return query


def apply_date_filters(query,
                      min_year: int = None,
                      max_year: int = None):
    """
    Apply date-based filters (release year).
    
    Args:
        query: Query object to filter
        min_year (int): Minimum release year
        max_year (int): Maximum release year
        
    Returns:
        Query: Filtered query object
    """
    filters_applied = []
    
    if min_year:
        query = query.gte("release_year", min_year)
        filters_applied.append(f"year>={min_year}")
    
    if max_year:
        query = query.lte("release_year", max_year)
        filters_applied.append(f"year<={max_year}")
    
    if filters_applied:
        logger.debug(f"📅 Applied date filters: {', '.join(filters_applied)}")
    
    return query


def apply_availability_filters(query, require_trailer: bool = True, require_poster: bool = True):
    """
    Apply availability filters (require certain assets).
    
    Args:
        query: Query object to filter
        require_trailer (bool): Require trailer URL to be present
        require_poster (bool): Require poster URL to be present
        
    Returns:
        Query: Filtered query object
    """
    filters_applied = []
    
    if require_trailer:
        # Filter out movies without trailer URLs
        query = query.neq("movie_localizations.trailer_url", "")
        query = query.not_.is_("movie_localizations.trailer_url", "null")
        filters_applied.append("has_trailer")
    
    if require_poster:
        # Filter out movies without poster URLs
        query = query.neq("movie_localizations.poster_url", "")
        query = query.not_.is_("movie_localizations.poster_url", "null")
        filters_applied.append("has_poster")
    
    if filters_applied:
        logger.debug(f"🎯 Applied availability filters: {', '.join(filters_applied)}")
    
    return query

# =============================================================================
# FILTER VALIDATION AND HELPERS
# =============================================================================

def validate_filter_values(filters: dict) -> dict:
    """
    Validate filter values and provide corrections.
    
    Args:
        filters (dict): Dictionary of filter parameters
        
    Returns:
        dict: Validation results with corrected values
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'corrected_filters': filters.copy()
    }
    
    # Validate content type
    if 'content_type' in filters and filters['content_type']:
        valid_content_types = ['Film', 'Série', 'Movie', 'Series', 'TV Show']
        if filters['content_type'] not in valid_content_types:
            validation_result['warnings'].append(f"Unknown content type: {filters['content_type']}")
    
    # Validate country code
    if 'country' in filters and filters['country']:
        valid_countries = ['US', 'FR', 'DE', 'IT', 'ES', 'PT', 'GB', 'CA']
        if filters['country'] not in valid_countries:
            validation_result['warnings'].append(f"Uncommon country code: {filters['country']}")
    
    # Validate platform
    if 'platform' in filters and filters['platform']:
        common_platforms = ['Netflix', 'Max', 'Prime Video', 'Disney+', 'Hulu', 'Apple TV+']
        if filters['platform'] not in common_platforms:
            validation_result['warnings'].append(f"Uncommon platform: {filters['platform']}")
    
    # Validate numeric filters
    numeric_filters = ['min_imdb_score', 'min_votes', 'max_runtime', 'min_year', 'max_year']
    for filter_name in numeric_filters:
        if filter_name in filters and filters[filter_name] is not None:
            try:
                if filter_name.startswith('min_imdb_score'):
                    value = float(filters[filter_name])
                    if value < 0 or value > 10:
                        validation_result['errors'].append(f"{filter_name} must be between 0 and 10")
                else:
                    value = int(filters[filter_name])
                    if value < 0:
                        validation_result['errors'].append(f"{filter_name} must be positive")
                
                validation_result['corrected_filters'][filter_name] = value
            except (ValueError, TypeError):
                validation_result['errors'].append(f"Invalid numeric value for {filter_name}")
    
    validation_result['is_valid'] = len(validation_result['errors']) == 0
    
    return validation_result


def get_popular_filter_combinations() -> list:
    """
    Get list of popular filter combinations for testing and suggestions.
    
    Returns:
        list: List of filter combination dictionaries
    """
    return [
        {
            'name': 'US Horror Movies',
            'filters': {'country': 'US', 'genre': 'Horror', 'content_type': 'Film'},
            'description': 'Horror movies available in the US'
        },
        {
            'name': 'Netflix Original Series',
            'filters': {'platform': 'Netflix', 'content_type': 'Série'},
            'description': 'Netflix series content'
        },
        {
            'name': 'High-Rated Action',
            'filters': {'genre': 'Action', 'min_imdb_score': 7.0, 'min_votes': 100000},
            'description': 'Well-rated action content'
        },
        {
            'name': 'Recent Releases',
            'filters': {'min_year': 2020, 'require_trailer': True},
            'description': 'Recent movies and shows with trailers'
        },
        {
            'name': 'French Comedy',
            'filters': {'country': 'FR', 'genre': 'Comedy', 'platform': 'Netflix'},
            'description': 'French comedy content on Netflix' 
        }
    ]