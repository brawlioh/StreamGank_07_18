"""
StreamGank Utilities Module

This module contains helper functions, URL builders, validation utilities,
and other common functionality used throughout the StreamGank system.

Modules:
    - url_builder: StreamGank URL construction and country mappings
    - validators: Input validation and data verification
    - formatters: Text formatting and content processing
    - file_utils: File operations and cleanup utilities
"""

from .url_builder import *
from .validators import *
# formatters module removed - functions were bloated 1-liner utilities
from .file_utils import *

__all__ = [
    # URL Builder
    'build_streamgank_url',
    'get_genre_mapping_by_country',
    'get_platform_mapping_by_country',
    'get_available_genres_for_country',
    'get_all_mappings_for_country',
    
    # Validators
    'validate_movie_data',
    'validate_script_data',
    'validate_api_response',
    'is_valid_url',
    'is_valid_genre',
    'is_valid_platform',
    
    # Formatters removed - were bloated 1-liner functions
    
    # File Utils
    'ensure_directory',
    'cleanup_temp_files',
    'get_temp_filename',
    'safe_file_operation'
]