"""
StreamGank Database Validators

This module provides validation functions for database operations,
including parameter validation, response validation, and data processing.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# PARAMETER VALIDATION
# =============================================================================

def validate_extraction_params(num_movies: int,
                              country: Optional[str] = None,
                              genre: Optional[str] = None,
                              platform: Optional[str] = None,
                              content_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate parameters for movie extraction.
    
    Args:
        num_movies (int): Number of movies to extract
        country (str): Country code filter
        genre (str): Genre filter
        platform (str): Platform filter
        content_type (str): Content type filter
        
    Returns:
        dict: Validation results with errors and warnings
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'corrected_params': {
            'num_movies': num_movies,
            'country': country,
            'genre': genre,
            'platform': platform,
            'content_type': content_type
        }
    }
    
    # Validate num_movies
    if not isinstance(num_movies, int):
        validation_result['errors'].append('num_movies must be an integer')
    elif num_movies <= 0:
        validation_result['errors'].append('num_movies must be positive')
    elif num_movies > 100:
        validation_result['warnings'].append('num_movies is very large, consider smaller values for performance')
        validation_result['corrected_params']['num_movies'] = min(num_movies, 100)
    
    # Validate country (if provided)
    if country is not None:
        if not isinstance(country, str):
            validation_result['errors'].append('country must be a string')
        elif len(country) != 2:
            validation_result['warnings'].append('country should be a 2-letter code (e.g., US, FR)')
        else:
            validation_result['corrected_params']['country'] = country.upper()
    
    # Validate genre (if provided)
    if genre is not None:
        if not isinstance(genre, str):
            validation_result['errors'].append('genre must be a string')
        elif len(genre.strip()) == 0:
            validation_result['warnings'].append('genre is empty, will be ignored')
            validation_result['corrected_params']['genre'] = None
    
    # Validate platform (if provided)
    if platform is not None:
        if not isinstance(platform, str):
            validation_result['errors'].append('platform must be a string')
        elif len(platform.strip()) == 0:
            validation_result['warnings'].append('platform is empty, will be ignored')
            validation_result['corrected_params']['platform'] = None
    
    # Validate content_type (if provided)
    if content_type is not None:
        if not isinstance(content_type, str):
            validation_result['errors'].append('content_type must be a string')
        elif len(content_type.strip()) == 0:
            validation_result['warnings'].append('content_type is empty, will be ignored')
            validation_result['corrected_params']['content_type'] = None
    
    validation_result['is_valid'] = len(validation_result['errors']) == 0
    
    if validation_result['warnings']:
        logger.debug(f"⚠️ Parameter validation warnings: {validation_result['warnings']}")
    
    if not validation_result['is_valid']:
        logger.error(f"❌ Parameter validation errors: {validation_result['errors']}")
    
    return validation_result

# =============================================================================
# RESPONSE VALIDATION
# =============================================================================

def validate_movie_response(response) -> Dict[str, Any]:
    """
    Validate database response structure and content.
    
    Args:
        response: Database response object
        
    Returns:
        dict: Validation results
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'data_count': 0,
        'valid_records': 0
    }
    
    # Check response structure
    if not hasattr(response, 'data'):
        validation_result['errors'].append('Response missing data attribute')
        validation_result['is_valid'] = False
        return validation_result
    
    if response.data is None:
        validation_result['errors'].append('Response data is None')
        validation_result['is_valid'] = False
        return validation_result
    
    if not isinstance(response.data, list):
        validation_result['errors'].append('Response data is not a list')
        validation_result['is_valid'] = False
        return validation_result
    
    validation_result['data_count'] = len(response.data)
    
    if validation_result['data_count'] == 0:
        validation_result['warnings'].append('No movies found matching criteria')
        return validation_result
    
    # Validate individual records
    for i, movie in enumerate(response.data):
        record_validation = validate_movie_record(movie, index=i)
        if record_validation['is_valid']:
            validation_result['valid_records'] += 1
        else:
            validation_result['warnings'].extend([
                f"Record {i}: {error}" for error in record_validation['errors']
            ])
    
    # Overall validation
    if validation_result['valid_records'] == 0:
        validation_result['errors'].append('No valid movie records found')
        validation_result['is_valid'] = False
    elif validation_result['valid_records'] < validation_result['data_count']:
        validation_result['warnings'].append(
            f"Only {validation_result['valid_records']}/{validation_result['data_count']} records are valid"
        )
    
    logger.debug(f"📊 Response validation: {validation_result['valid_records']}/{validation_result['data_count']} valid records")
    
    return validation_result


def validate_movie_record(movie: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    """
    Validate individual movie record structure.
    
    Args:
        movie (dict): Movie record from database
        index (int): Record index for error reporting
        
    Returns:
        dict: Validation results for the record
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'missing_fields': [],
        'invalid_fields': []
    }
    
    # Required fields
    required_fields = ['movie_id']
    
    # Optional but important fields
    important_fields = ['imdb_score', 'release_year', 'content_type']
    
    # Check required fields
    for field in required_fields:
        if field not in movie or movie[field] is None:
            validation_result['missing_fields'].append(field)
            validation_result['errors'].append(f"Missing required field: {field}")
    
    # Check important fields
    for field in important_fields:
        if field not in movie or movie[field] is None:
            validation_result['warnings'].append(f"Missing important field: {field}")
    
    # Validate localization data
    if 'movie_localizations' in movie:
        localization = movie['movie_localizations']
        if isinstance(localization, list):
            if len(localization) == 0:
                validation_result['warnings'].append("Empty localization data")
            else:
                # Validate first localization record
                loc_validation = validate_localization_record(localization[0])
                validation_result['warnings'].extend(loc_validation['warnings'])
                validation_result['errors'].extend(loc_validation['errors'])
        elif isinstance(localization, dict):
            loc_validation = validate_localization_record(localization)
            validation_result['warnings'].extend(loc_validation['warnings'])
            validation_result['errors'].extend(loc_validation['errors'])
        else:
            validation_result['errors'].append("Invalid localization data format")
    else:
        validation_result['errors'].append("Missing localization data")
    
    # Validate genre data
    if 'movie_genres' in movie:
        genres = movie['movie_genres']
        if isinstance(genres, list):
            if len(genres) == 0:
                validation_result['warnings'].append("No genres found")
        elif isinstance(genres, dict):
            if not genres.get('genre'):
                validation_result['warnings'].append("Empty genre data")
        else:
            validation_result['warnings'].append("Invalid genre data format")
    else:
        validation_result['warnings'].append("Missing genre data")
    
    # Validate numeric fields
    if 'imdb_score' in movie and movie['imdb_score'] is not None:
        try:
            score = float(movie['imdb_score'])
            if score < 0 or score > 10:
                validation_result['invalid_fields'].append('imdb_score out of range')
        except (ValueError, TypeError):
            validation_result['invalid_fields'].append('imdb_score not numeric')
    
    if 'imdb_votes' in movie and movie['imdb_votes'] is not None:
        try:
            votes = int(movie['imdb_votes'])
            if votes < 0:
                validation_result['invalid_fields'].append('imdb_votes negative')
        except (ValueError, TypeError):
            validation_result['invalid_fields'].append('imdb_votes not numeric')
    
    validation_result['is_valid'] = len(validation_result['errors']) == 0
    
    return validation_result


def validate_localization_record(localization: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate localization record structure.
    
    Args:
        localization (dict): Localization record
        
    Returns:
        dict: Validation results
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Important localization fields
    important_fields = ['title', 'country_code', 'platform_name']
    
    for field in important_fields:
        if field not in localization or not localization[field]:
            validation_result['warnings'].append(f"Missing localization field: {field}")
    
    # Validate URLs if present
    url_fields = ['poster_url', 'trailer_url', 'streaming_url']
    for field in url_fields:
        if field in localization and localization[field]:
            url = localization[field]
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                validation_result['warnings'].append(f"Invalid URL format for {field}")
    
    return validation_result

# =============================================================================
# DATA PROCESSING FUNCTIONS
# =============================================================================

def process_movie_data(raw_data: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
    """
    Process raw database response into standardized movie data format.
    
    Args:
        raw_data (list): Raw movie data from database
        debug (bool): Enable debug logging
        
    Returns:
        list: Processed movie data dictionaries
    """
    logger.debug(f"🔄 Processing {len(raw_data)} raw movie records")
    
    processed_movies = []
    
    for i, movie in enumerate(raw_data):
        try:
            processed_movie = process_single_movie(movie, debug=debug)
            if processed_movie:
                processed_movies.append(processed_movie)
            else:
                logger.warning(f"⚠️ Failed to process movie at index {i}")
        except Exception as e:
            logger.error(f"❌ Error processing movie {i}: {str(e)}")
            if debug:
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
            continue
    
    logger.info(f"✅ Successfully processed {len(processed_movies)}/{len(raw_data)} movies")
    return processed_movies


def process_single_movie(movie: Dict[str, Any], debug: bool = False) -> Optional[Dict[str, Any]]:
    """
    Process a single movie record into standardized format.
    
    Args:
        movie (dict): Raw movie record from database
        debug (bool): Enable debug logging
        
    Returns:
        dict: Processed movie data or None if processing failed
    """
    try:
        # Extract localization data
        localization = movie.get('movie_localizations', [])
        if isinstance(localization, list) and len(localization) > 0:
            localization = localization[0]
        elif not isinstance(localization, dict):
            logger.warning(f"Invalid localization data for movie {movie.get('movie_id', 'unknown')}")
            return None
        
        # Extract genre data
        genres_data = movie.get('movie_genres', [])
        if isinstance(genres_data, list):
            genres = [g.get('genre') for g in genres_data if g.get('genre')]
        elif isinstance(genres_data, dict) and genres_data.get('genre'):
            genres = [genres_data['genre']]
        else:
            genres = []
        
        # Build standardized movie info
        movie_info = {
            'id': movie.get('movie_id'),
            'title': localization.get('title', 'Unknown Title'),
            'year': movie.get('release_year', 'Unknown'),
            'imdb': format_imdb_display(movie.get('imdb_score', 0), movie.get('imdb_votes', 0)),
            'imdb_score': movie.get('imdb_score', 0),
            'imdb_votes': movie.get('imdb_votes', 0),
            'runtime': format_runtime_display(movie.get('runtime', 0)),
            'platform': localization.get('platform_name', 'Unknown'),
            'poster_url': localization.get('poster_url', ''),
            'cloudinary_poster_url': localization.get('cloudinary_poster_url', ''),
            'trailer_url': localization.get('trailer_url', ''),
            'streaming_url': localization.get('streaming_url', ''),
            'genres': genres,
            'content_type': movie.get('content_type', 'Unknown'),
            'country_code': localization.get('country_code', 'Unknown')
        }
        
        if debug:
            logger.debug(f"🎬 Processed: {movie_info['title']} ({movie_info['year']}) - {movie_info['imdb']}")
        
        return movie_info
        
    except Exception as e:
        logger.error(f"❌ Error processing movie {movie.get('movie_id', 'unknown')}: {str(e)}")
        return None

# =============================================================================
# FORMATTING UTILITIES
# =============================================================================

def format_imdb_display(score: float, votes: int) -> str:
    """
    Format IMDB score and votes for display.
    
    Args:
        score (float): IMDB score
        votes (int): Number of votes
        
    Returns:
        str: Formatted IMDB display string
    """
    try:
        score = float(score) if score is not None else 0.0
        votes = int(votes) if votes is not None else 0
        
        return f"{score:.1f}/10 ({votes:,} votes)"
    except (ValueError, TypeError):
        return "0.0/10 (0 votes)"


def format_runtime_display(runtime: int) -> str:
    """
    Format runtime for display.
    
    Args:
        runtime (int): Runtime in minutes
        
    Returns:
        str: Formatted runtime string
    """
    try:
        runtime = int(runtime) if runtime is not None else 0
        
        if runtime <= 0:
            return "Unknown"
        
        return f"{runtime} min"
    except (ValueError, TypeError):
        return "Unknown"


def extract_year_from_movie(movie: Dict[str, Any]) -> int:
    """
    Extract and validate year from movie data.
    
    Args:
        movie (dict): Movie data
        
    Returns:
        int: Release year or 0 if not available
    """
    try:
        year = movie.get('release_year')
        if year is not None:
            year = int(year)
            if 1900 <= year <= 2030:  # Reasonable year range
                return year
    except (ValueError, TypeError):
        pass
    
    return 0


def extract_score_from_movie(movie: Dict[str, Any]) -> float:
    """
    Extract and validate IMDB score from movie data.
    
    Args:
        movie (dict): Movie data
        
    Returns:
        float: IMDB score or 0.0 if not available
    """
    try:
        score = movie.get('imdb_score')
        if score is not None:
            score = float(score)
            if 0.0 <= score <= 10.0:  # Valid IMDB range
                return score
    except (ValueError, TypeError):
        pass
    
    return 0.0