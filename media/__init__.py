"""
StreamGank Assets Module

This module handles all media asset creation and processing for the StreamGang 
video generation system, including enhanced posters and trailer clips.

Modules:
    - poster_generator: Enhanced movie poster creation with metadata overlays
    - clip_processor: Trailer downloading and highlight clip extraction
    - cloudinary_uploader: Media upload and transformation with Cloudinary
    - media_utils: Common media processing utilities and helpers
"""

from .poster_generator import *
from .clip_processor import *
from .cloudinary_uploader import *
from .media_utils import *

__all__ = [
    # Poster Generation
    'create_enhanced_movie_poster',
    'create_enhanced_movie_posters',
    'generate_poster_metadata',
    'apply_cinematic_effects',
    
    # Clip Processing
    'download_youtube_trailer',
    'extract_highlight_clip',
    'process_movie_trailers_to_clips',
    'extract_youtube_video_id',
    
    # Cloudinary Upload
    'upload_poster_to_cloudinary',
    'upload_clip_to_cloudinary',
    'get_cloudinary_transformation',
    'batch_upload_assets',
    
    # Media Utilities
    'validate_media_file',
    'get_video_duration',
    'get_image_dimensions',
    'clean_temp_files',
    'ensure_media_directories'
]