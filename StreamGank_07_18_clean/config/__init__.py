"""
StreamGank Configuration Module

This module contains all configuration settings, templates, and constants
used throughout the StreamGank video generation system.

Modules:
    - templates: HeyGen templates and video composition settings
    - settings: API configurations and system parameters
    - constants: Fixed values and mappings used across the system
"""

from .templates import *
from .settings import *
from .constants import *

__all__ = [
    # Templates
    'HEYGEN_TEMPLATES',
    'get_heygen_template_id',
    
    # Settings  
    'API_SETTINGS',
    'VIDEO_SETTINGS',
    'SCROLL_SETTINGS',
    
    # Constants
    'PLATFORM_COLORS',
    'GENRE_COLORS', 
    'CONTENT_TYPES',
    'SUPPORTED_COUNTRIES'
]