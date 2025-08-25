"""
StreamGank Media Module

This module handles media utilities, uploads, and screenshot capture for the 
StreamGank video generation system.

Modules:
    - cloudinary_uploader: Media upload and transformation with Cloudinary
    - media_utils: Common media processing utilities and helpers
    - screenshot_capture: Screenshot capture functionality
"""

from .cloudinary_uploader import *
from .media_utils import *
# from .screenshot_capture import *  # Commented out due to import issues - import directly when needed

__all__ = [
    # Cloudinary Upload
    'upload_poster_to_cloudinary',
    'upload_clip_to_cloudinary',
    'get_cloudinary_transformation',
    'batch_upload_assets',
    'upload_file_to_cloudinary',
    
    # Media Utilities
    'validate_image_url',
    'validate_video_file',
    'get_video_duration',
    'get_image_dimensions',
    'clean_temp_files',
    'detect_media_format',
    'is_portrait_format',
    'get_fallback_poster',
    
    # Screenshot Capture - import directly from media.screenshot_capture when needed
    # 'capture_streamgank_screenshots',
    # 'batch_capture_screenshots', 
    # 'validate_screenshots'
]