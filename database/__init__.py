"""
StreamGank Database Module

This module handles all database operations for the StreamGang video generation system,
including movie data extraction, filtering, and validation.

Modules:
    - movie_extractor: Core movie data extraction from Supabase
    - connection: Database connection management and testing
    - filters: Query building and filtering utilities
    - validators: Database response validation
"""

from .movie_extractor import *
from .connection import *
from .filters import *
from .validators import *

__all__ = [
    # Movie Extraction
    'extract_movie_data',
    'extract_movies_by_filters',
    'get_movie_details',
    'simulate_movie_data',
    
    # Connection Management
    'test_supabase_connection',
    'get_supabase_client',
    'validate_database_config',
    
    # Query Filters
    'build_movie_query',
    'apply_content_filters',
    'apply_localization_filters',
    'apply_genre_filters',
    
    # Validators
    'validate_movie_response',
    'validate_extraction_params',
    'process_movie_data'
]