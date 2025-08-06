"""
StreamGank Validation Utilities

This module provides validation functions for input data, API responses,
and system configurations used throughout the StreamGank system.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# =============================================================================
# MOVIE DATA VALIDATION
# =============================================================================

def validate_movie_data(movie_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate movie data structure and required fields.
    
    Args:
        movie_data (dict): Movie data dictionary
        
    Returns:
        dict: Validation result with status and details
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'missing_fields': [],
        'invalid_fields': {}
    }
    
    # Required fields for movie processing
    required_fields = ['title', 'id']
    optional_fields = ['trailer_url', 'poster_url', 'genre', 'platform', 'rating', 'year']
    
    # Check required fields
    for field in required_fields:
        if field not in movie_data or not movie_data[field]:
            validation_result['missing_fields'].append(field)
            validation_result['errors'].append(f"Missing required field: {field}")
    
    # Validate field types and formats
    if 'title' in movie_data:
        if not isinstance(movie_data['title'], str) or len(movie_data['title'].strip()) == 0:
            validation_result['invalid_fields']['title'] = 'Title must be a non-empty string'
            validation_result['errors'].append('Invalid title format')
    
    if 'id' in movie_data:
        if not (isinstance(movie_data['id'], (int, str)) and str(movie_data['id']).strip()):
            validation_result['invalid_fields']['id'] = 'ID must be a valid number or string'
            validation_result['errors'].append('Invalid ID format')
    
    if 'trailer_url' in movie_data and movie_data['trailer_url']:
        if not is_valid_url(movie_data['trailer_url']):
            validation_result['invalid_fields']['trailer_url'] = 'Invalid URL format'
            validation_result['warnings'].append('Invalid trailer URL format')
    
    if 'year' in movie_data and movie_data['year']:
        try:
            year = int(movie_data['year'])
            if year < 1900 or year > 2030:
                validation_result['invalid_fields']['year'] = 'Year should be between 1900 and 2030'
                validation_result['warnings'].append('Unusual year value')
        except (ValueError, TypeError):
            validation_result['invalid_fields']['year'] = 'Year must be a valid number'
            validation_result['warnings'].append('Invalid year format')
    
    # Check for missing optional but important fields
    for field in optional_fields:
        if field not in movie_data or not movie_data[field]:
            validation_result['warnings'].append(f"Missing optional field: {field}")
    
    # Overall validation status
    validation_result['is_valid'] = len(validation_result['errors']) == 0
    
    logger.debug(f"Movie validation result: {validation_result}")
    return validation_result


def validate_movie_list(movies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a list of movie data dictionaries.
    
    Args:
        movies (list): List of movie data dictionaries
        
    Returns:
        dict: Validation summary for the entire list
    """
    if not isinstance(movies, list):
        return {
            'is_valid': False,
            'error': 'Movies data must be a list',
            'valid_count': 0,
            'total_count': 0
        }
    
    if len(movies) == 0:
        return {
            'is_valid': False,
            'error': 'Movies list is empty',
            'valid_count': 0,
            'total_count': 0 
        }
    
    validation_summary = {
        'is_valid': True,
        'total_count': len(movies),
        'valid_count': 0,
        'invalid_count': 0,
        'movie_validations': [],
        'overall_errors': []
    }
    
    for i, movie in enumerate(movies):
        movie_validation = validate_movie_data(movie)
        validation_summary['movie_validations'].append({
            'index': i,
            'title': movie.get('title', f'Movie_{i+1}'),
            'validation': movie_validation
        })
        
        if movie_validation['is_valid']:
            validation_summary['valid_count'] += 1
        else:
            validation_summary['invalid_count'] += 1
    
    # Overall validation fails if less than minimum viable movies
    if validation_summary['valid_count'] < 1:
        validation_summary['is_valid'] = False
        validation_summary['overall_errors'].append('No valid movies found')
    
    logger.info(f"Movie list validation: {validation_summary['valid_count']}/{validation_summary['total_count']} valid")
    return validation_summary

# =============================================================================
# SCRIPT DATA VALIDATION
# =============================================================================

def validate_script_data(script_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate script data structure for video generation.
    
    Args:
        script_data (dict): Script data dictionary
        
    Returns:
        dict: Validation result
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'script_count': 0
    }
    
    if not isinstance(script_data, dict):
        validation_result['is_valid'] = False
        validation_result['errors'].append('Script data must be a dictionary')
        return validation_result
    
    if len(script_data) == 0:
        validation_result['is_valid'] = False
        validation_result['errors'].append('Script data is empty')
        return validation_result
    
    # Check each script entry
    for key, script_info in script_data.items():
        if isinstance(script_info, dict):
            if 'text' not in script_info or not script_info['text']:
                validation_result['errors'].append(f"Script '{key}' missing text content")
            else:
                # Validate script text
                text = script_info['text'].strip()
                if len(text) == 0:
                    validation_result['errors'].append(f"Script '{key}' has empty text")
                elif len(text) > 1000:  # Reasonable limit for HeyGen
                    validation_result['warnings'].append(f"Script '{key}' is very long ({len(text)} chars)")
                
                validation_result['script_count'] += 1
        
        elif isinstance(script_info, str):
            text = script_info.strip()
            if len(text) == 0:
                validation_result['errors'].append(f"Script '{key}' is empty")
            else:
                validation_result['script_count'] += 1
        
        else:
            validation_result['errors'].append(f"Script '{key}' has invalid format")
    
    # Overall validation
    validation_result['is_valid'] = len(validation_result['errors']) == 0 and validation_result['script_count'] > 0
    
    logger.debug(f"Script validation result: {validation_result}")
    return validation_result

# =============================================================================
# API RESPONSE VALIDATION
# =============================================================================

def validate_api_response(response_data: Any, expected_fields: List[str] = None) -> Dict[str, Any]:
    """
    Validate API response structure and content.
    
    Args:
        response_data: API response data
        expected_fields (list): List of expected fields in response
        
    Returns:
        dict: Validation result
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'missing_fields': []
    }
    
    if response_data is None:
        validation_result['is_valid'] = False
        validation_result['errors'].append('Response data is None')
        return validation_result
    
    if expected_fields:
        if not isinstance(response_data, dict):
            validation_result['is_valid'] = False
            validation_result['errors'].append('Response is not a dictionary')
            return validation_result
        
        for field in expected_fields:
            if field not in response_data:
                validation_result['missing_fields'].append(field)
                validation_result['errors'].append(f"Missing expected field: {field}")
    
    # Check for common error indicators in API responses
    if isinstance(response_data, dict):
        if 'error' in response_data:
            validation_result['warnings'].append(f"API returned error: {response_data['error']}")
        
        if 'status' in response_data and response_data['status'] in ['error', 'failed', 'failure']:
            validation_result['warnings'].append(f"API status indicates failure: {response_data['status']}")
    
    validation_result['is_valid'] = len(validation_result['errors']) == 0
    
    logger.debug(f"API response validation result: {validation_result}")
    return validation_result

# =============================================================================
# URL AND TEXT VALIDATION
# =============================================================================

def is_valid_url(url: str) -> bool:
    """
    Validate if a string is a valid URL.
    
    Args:
        url (str): URL string to validate
        
    Returns:
        bool: True if URL is valid
    """
    if not isinstance(url, str) or not url.strip():
        return False
    
    try:
        parsed = urlparse(url.strip())
        return bool(parsed.netloc) and bool(parsed.scheme)
    except Exception:
        return False


def is_valid_youtube_url(url: str) -> bool:
    """
    Validate if a URL is a valid YouTube URL.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if it's a valid YouTube URL
    """
    if not is_valid_url(url):
        return False
    
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+'
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url.strip()):
            return True
    
    return False


def is_valid_genre(genre: str, supported_genres: List[str] = None) -> bool:
    """
    Validate if a genre is supported.
    
    Args:
        genre (str): Genre to validate
        supported_genres (list): List of supported genres
        
    Returns:
        bool: True if genre is valid
    """
    if not isinstance(genre, str) or not genre.strip():
        return False
    
    if supported_genres:
        return genre.strip() in supported_genres
    
    # Default genres if no list provided
    from config.constants import US_GENRE_MAPPING
    return genre.strip() in US_GENRE_MAPPING
    

def is_valid_platform(platform: str, supported_platforms: List[str] = None) -> bool:
    """
    Validate if a platform is supported.
    
    Args:
        platform (str): Platform to validate
        supported_platforms (list): List of supported platforms
        
    Returns:
        bool: True if platform is valid
    """
    if not isinstance(platform, str) or not platform.strip():
        return False
    
    if supported_platforms:
        return platform.strip() in supported_platforms
    
    # Default platforms if no list provided
    from config.constants import PLATFORM_MAPPING
    return platform.strip() in PLATFORM_MAPPING

# =============================================================================
# SYSTEM VALIDATION
# =============================================================================

def validate_environment_variables(required_vars: List[str]) -> Dict[str, Any]:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars (list): List of required environment variable names
        
    Returns:
        dict: Validation result with missing variables
    """
    import os
    
    validation_result = {
        'is_valid': True,
        'missing_vars': [],
        'empty_vars': [],
        'valid_vars': []
    }
    
    for var_name in required_vars:
        var_value = os.getenv(var_name)
        
        if var_value is None:
            validation_result['missing_vars'].append(var_name)
        elif not var_value.strip():
            validation_result['empty_vars'].append(var_name)
        else:
            validation_result['valid_vars'].append(var_name)
    
    validation_result['is_valid'] = (
        len(validation_result['missing_vars']) == 0 and 
        len(validation_result['empty_vars']) == 0
    )
    
    if not validation_result['is_valid']:
        logger.warning(f"Environment validation failed: missing={validation_result['missing_vars']}, empty={validation_result['empty_vars']}")
    
    return validation_result


def validate_file_path(file_path: str, must_exist: bool = False) -> Dict[str, Any]:
    """
    Validate file path format and existence.
    
    Args:
        file_path (str): File path to validate
        must_exist (bool): Whether file must exist
        
    Returns:
        dict: Validation result
    """
    import os
    from pathlib import Path
    
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'exists': False,
        'is_file': False,
        'is_directory': False
    }
    
    if not isinstance(file_path, str) or not file_path.strip():
        validation_result['is_valid'] = False
        validation_result['errors'].append('File path must be a non-empty string')
        return validation_result
    
    try:
        path = Path(file_path)
        validation_result['exists'] = path.exists()
        validation_result['is_file'] = path.is_file()
        validation_result['is_directory'] = path.is_dir()
        
        if must_exist and not validation_result['exists']:
            validation_result['is_valid'] = False
            validation_result['errors'].append('File does not exist')
        
        # Check for potential issues
        if validation_result['exists'] and validation_result['is_directory']:
            validation_result['warnings'].append('Path points to a directory, not a file')
            
    except Exception as e:
        validation_result['is_valid'] = False
        validation_result['errors'].append(f'Invalid file path: {str(e)}')
    
    return validation_result