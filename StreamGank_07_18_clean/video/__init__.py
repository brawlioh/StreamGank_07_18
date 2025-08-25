"""
StreamGank Video Module

This module handles all video processing and assembly for the StreamGang 
video generation system, including Creatomate integration and scroll videos.

Modules:
    - creatomate_client: Creatomate API integration for video composition and rendering
    - scroll_generator: Browser-based scroll video generation with smooth animations
    - composition_builder: Video composition building and timing management
    - video_processor: Video processing utilities and duration analysis
"""

from .creatomate_client import *
from .scroll_generator import *
from .composition_builder import *
from .video_processor import *

__all__ = [
    # Creatomate Integration
    'create_creatomate_video',
    'check_render_status',
    'wait_for_completion',
    'send_creatomate_request',
    'get_creatomate_video_url',
    
    # Scroll Video Generation
    'generate_scroll_video',
    'create_scroll_video_from_url',
    'capture_scroll_screenshots',
    'convert_screenshots_to_video',
    
    # Composition Building
    'build_video_composition',
    'calculate_timing_strategy',
    'create_poster_timing',
    'build_composition_elements',
    
    # Video Processing
    'analyze_video_duration',
    'calculate_video_durations',
    'validate_video_urls',
    'process_video_metadata'
]