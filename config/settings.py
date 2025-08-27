"""
StreamGank System Settings Configuration

This module contains DEFAULT VALUES for API configurations, system parameters, 
and operational settings used throughout the StreamGank video generation system.

IMPORTANT: These are DEFAULT VALUES that can be overridden at runtime:
- Command line parameters take highest priority
- Function parameters can override defaults  
- Settings provide fallback values when parameters are None/not provided
- Hardcoded fallbacks ensure system stability

Example Priority Order:
1. Runtime Parameter: --scroll-distance 2.0 (highest)
2. Settings Default: SCROLL_SETTINGS['scroll_distance_multiplier'] = 1.5
3. Hardcoded Fallback: get('scroll_distance_multiplier', 1.5) (lowest)
"""

import os
from typing import Dict, Any

# =============================================================================
# API CONFIGURATION SETTINGS
# =============================================================================

API_SETTINGS = {
    # OpenAI Configuration  
    'openai': {
        'model': 'gpt-4',  # Standard available model - change to 'gpt-4.1-mini' if you have access
        'temperature': 0.8,  # Creative but consistent
        'hook_max_tokens': 40,  # For short hooks (10-18 words)
        'intro_max_tokens': 60,  # For intro scripts (15-25 words)
        'timeout': 30,  # Request timeout in seconds
        'retry_attempts': 3
    },
    
    # Gemini configuration removed - using OpenAI + Template fallback only
    
    # HeyGen Configuration
    'heygen': {
        'base_url': 'https://api.heygen.com/v2',
        'template_endpoint': '/template/{}/generate',
        'video_endpoint': '/video/generate', 
        'status_endpoint': '/video_status/{video_id}',
        'default_template_id': 'cc6718c5363e42b282a123f99b94b335',
        'poll_interval': 15,  # Status check interval in seconds
        'max_poll_attempts': 40,  # Maximum status checks (10 minutes)
        'timeout': 60  # Request timeout in seconds
    },
    
    # Creatomate Configuration
    'creatomate': {
        'base_url': 'https://api.creatomate.com/v1',
        'timeout': 120,  # Request timeout in seconds
        'max_wait_time': 300,  # Maximum wait for completion
        'poll_interval': 30  # Status check interval
    },
    
    # Cloudinary Configuration
    'cloudinary': {
        'resource_type': 'auto',
        'quality': 'auto:good',
        'fetch_format': 'auto',
        'timeout': 120,  # Upload timeout
        'chunk_size': 6000000,  # 6MB chunks for large files
        'transformation': {
            'poster': 'w_1080,h_1920,c_fill,f_auto,q_auto:good',
            'clip': 'w_1080,h_1920,c_fill,f_auto,q_auto:good,vc_auto',
            'scroll': 'w_1080,h_1920,c_fill,f_auto,q_auto:good'
        }
    }
}

# =============================================================================
# VIDEO PROCESSING SETTINGS
# =============================================================================

VIDEO_SETTINGS = {
    # General Video Parameters
    'target_resolution': (1080, 1920),  # 9:16 portrait for TikTok/YouTube Shorts
    'target_fps': 60,  # High frame rate for smooth playback
    'video_codec': 'libx264',
    'audio_codec': 'aac',
    'video_bitrate': '2M',
    'audio_bitrate': '128k',
    
    # Clip Processing
    'clip_duration': 15,  # Seconds for movie trailer highlights
    'clip_start_offset': 30,  # Skip first 30 seconds of trailers
    'highlight_detection_threshold': 0.7,  # Audio energy threshold
    
    # Poster Generation
    'poster_resolution': (1080, 1920),
    'poster_quality': 95,
    'font_sizes': {
        'title': 70,         # REDUCED from 88px - More balanced title size for better readability
        'subtitle': 48,      # REDUCED from 60px - More proportional platform badge size  
        'metadata': 40,      # REDUCED from 50px - Better sized metadata values
        'rating': 44         # REDUCED from 54px - More balanced rating labels
    },
    'margins': {
        'top': 100,
        'bottom': 150,
        'left': 80,
        'right': 80
    },
    
    # FFmpeg Settings
    'ffmpeg_threads': 4,
    'ffmpeg_preset': 'medium',  # Balance between speed and quality
    'temp_dir': './temp_processing'
}

# =============================================================================
# SCROLL VIDEO SETTINGS
# =============================================================================

SCROLL_SETTINGS = {
    # Duration and Timing
    'target_duration': 4,  # Seconds (reduced from 6 for better pacing)
    'target_fps': 60,  # Ultra-smooth 60fps
    'total_frames': 240,  # 4 seconds * 60fps
    
    # Scrolling Behavior
    'scroll_distance_multiplier': 1.5,  # Viewport multiplier for scroll distance
    'min_scroll_height': 1.5,  # Minimum scroll relative to viewport
    'max_scroll_percentage': 0.7,  # Maximum 70% of page height
    'micro_scroll_enabled': True,  # Enable frame-by-frame micro-scrolling
    
    # Screenshot Settings
    'viewport_width': 1080,
    'viewport_height': 1920,
    'device_scale_factor': 1.0,
    'wait_time': 0.04,  # Ultra-fast capture timing
    
    # Browser Settings
    'browser_timeout': 60000,  # 60 second timeout
    'page_load_timeout': 30000,  # 30 second page load timeout
    'screenshot_quality': 100,  # Maximum quality
    'screenshot_format': 'png'
}

# =============================================================================
# WORKFLOW ORCHESTRATION SETTINGS
# =============================================================================

WORKFLOW_SETTINGS = {
    # Processing Limits
    'max_movies': 3,  # Always process exactly 3 movies
    'max_concurrent_processes': 2,  # Parallel processing limit
    'strict_mode': True,  # Terminate on critical failures
    
    # Retry Logic
    'max_retries': 3,
    'retry_delay': 5,  # Seconds between retries
    'exponential_backoff': True,
    
    # Asset Processing
    'asset_timeout': 300,  # 5 minutes for asset creation
    'cleanup_temp_files': True,
    'preserve_debug_files': False,
    
    # Timing Settings
    'poster_timing_modes': ['heygen_last3s', 'with_movie_clips'],
    'default_poster_timing': 'heygen_last3s',
    'min_poster_duration': 0.5,  # Minimum poster display time
    'max_poster_duration': 3.0   # Maximum poster display time
}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGGING_SETTINGS = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_logging': True,
    'log_file': 'streamgank.log',
    'max_log_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
    'console_logging': True
}

# =============================================================================
# ENVIRONMENT VARIABLE MAPPINGS
# =============================================================================

REQUIRED_ENV_VARS = {
    'OPENAI_API_KEY': 'OpenAI API key for script generation',
    'HEYGEN_API_KEY': 'HeyGen API key for avatar video creation',
    'CREATOMATE_API_KEY': 'Creatomate API key for video composition',
    'CLOUDINARY_CLOUD_NAME': 'Cloudinary cloud name for media storage',
    'CLOUDINARY_API_KEY': 'Cloudinary API key',
    'CLOUDINARY_API_SECRET': 'Cloudinary API secret'
}

OPTIONAL_ENV_VARS = {
    'SUPABASE_URL': 'Supabase database URL',
    'SUPABASE_KEY': 'Supabase API key',
    'DATABASE_URL': 'Direct database connection URL',
    'VIZARD_API_KEY': 'Vizard AI API key for viral clip generation'
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_api_config(service: str = None) -> Dict[str, Any]:
    """
    Get API configuration for a specific service or return environment variables.
    
    Args:
        service (str, optional): Service name ('openai', 'heygen', 'creatomate', 'cloudinary')
                               If None, returns dictionary with environment variables
        
    Returns:
        dict: API configuration for the service or environment variables
    """
    if service is None:
        # Return environment variables for API keys
        return {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'HEYGEN_API_KEY': os.getenv('HEYGEN_API_KEY'), 
            'CREATOMATE_API_KEY': os.getenv('CREATOMATE_API_KEY'),
            'CLOUDINARY_URL': os.getenv('CLOUDINARY_URL'),
            'VIZARD_API_KEY': os.getenv('VIZARD_API_KEY')  # Added Vizard API key
        }
    
    return API_SETTINGS.get(service, {})


def validate_environment() -> Dict[str, bool]:
    """
    Validate that all required environment variables are set.
    
    Returns:
        dict: Validation results for each required variable
    """
    validation_results = {}
    
    for env_var, description in REQUIRED_ENV_VARS.items():
        validation_results[env_var] = bool(os.getenv(env_var))
    
    return validation_results


def get_missing_env_vars() -> list:
    """
    Get list of missing required environment variables.
    
    Returns:
        list: Names of missing environment variables
    """
    missing = []
    
    for env_var in REQUIRED_ENV_VARS.keys():
        if not os.getenv(env_var):
            missing.append(env_var)
    
    return missing


def is_environment_ready() -> bool:
    """
    Check if all required environment variables are configured.
    
    Returns:
        bool: True if environment is ready for operation
    """
    return len(get_missing_env_vars()) == 0


def get_scroll_settings() -> Dict[str, Any]:
    """
    Get scroll video configuration settings.
    
    Returns:
        dict: Scroll video settings
    """
    return SCROLL_SETTINGS


def get_video_settings() -> Dict[str, Any]:
    """
    Get video processing configuration settings.
    
    Returns:
        dict: Video processing settings
    """
    return VIDEO_SETTINGS


def get_workflow_settings() -> Dict[str, Any]:
    """
    Get workflow configuration settings.
    
    Returns:
        dict: Workflow settings
    """
    return WORKFLOW_SETTINGS


def get_system_config() -> Dict[str, Any]:
    """
    Get complete system configuration.
    
    Returns:
        dict: Complete system configuration
    """
    return {
        'api': API_SETTINGS,
        'video': VIDEO_SETTINGS,
        'scroll': SCROLL_SETTINGS,
        'workflow': WORKFLOW_SETTINGS,
        'logging': LOGGING_SETTINGS,
        'environment': {
            'ready': is_environment_ready(),
            'missing_vars': get_missing_env_vars()
        }
    }