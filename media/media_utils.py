"""
StreamGank Media Utilities

Common utilities for media processing, validation, and file management
used across the assets module.

Features:
- Media file validation and analysis
- Fallback asset generation
- Temporary file management
- Media format detection and conversion helpers
- Performance monitoring for media operations
"""

import os
import logging
import subprocess
import json
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests

from utils.file_utils import ensure_directory, safe_delete_file
from utils.validators import is_valid_url

logger = logging.getLogger(__name__)

# =============================================================================
# MEDIA FILE VALIDATION
# =============================================================================

def validate_image_url(url: str) -> bool:
    """
    Validate that a URL points to a valid image.
    
    Args:
        url (str): Image URL to validate
        
    Returns:
        bool: True if URL is valid and points to an image
    """
    try:
        if not is_valid_url(url):
            return False
        
        # Check if URL looks like an image
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        url_lower = url.lower()
        
        # Check extension in URL
        for ext in image_extensions:
            if ext in url_lower:
                return True
        
        # If no extension found, try a HEAD request to check content type
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            content_type = response.headers.get('content-type', '').lower()
            return content_type.startswith('image/')
        except:
            # If HEAD request fails, assume it might be valid
            return True
        
    except Exception as e:
        logger.debug(f"Error validating image URL {url}: {str(e)}")
        return False


def validate_video_file(file_path: str) -> bool:
    """
    Validate that a file is a valid video using FFprobe.
    
    Args:
        file_path (str): Path to video file
        
    Returns:
        bool: True if file is a valid video
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        # Use FFprobe to check if file is valid video
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return False
        
        # Parse FFprobe output
        probe_data = json.loads(result.stdout)
        
        # Check if there's at least one video stream
        streams = probe_data.get('streams', [])
        has_video = any(stream.get('codec_type') == 'video' for stream in streams)
        
        # Check if file has valid format
        format_info = probe_data.get('format', {})
        duration = float(format_info.get('duration', 0))
        
        return has_video and duration > 0
        
    except Exception as e:
        logger.debug(f"Error validating video file {file_path}: {str(e)}")
        return False


def get_video_duration(file_path: str) -> Optional[float]:
    """
    Get video duration in seconds using FFprobe.
    
    Args:
        file_path (str): Path to video file
        
    Returns:
        float: Duration in seconds or None if failed
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None
        
        probe_data = json.loads(result.stdout)
        format_info = probe_data.get('format', {})
        duration = float(format_info.get('duration', 0))
        
        return duration if duration > 0 else None
        
    except Exception as e:
        logger.debug(f"Error getting video duration for {file_path}: {str(e)}")
        return None


def get_image_dimensions(file_path: str) -> Optional[Tuple[int, int]]:
    """
    Get image dimensions using PIL.
    
    Args:
        file_path (str): Path to image file
        
    Returns:
        Tuple[int, int]: (width, height) or None if failed
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        with Image.open(file_path) as img:
            return img.size
        
    except Exception as e:
        logger.debug(f"Error getting image dimensions for {file_path}: {str(e)}")
        return None


def get_video_info(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive video information using FFprobe.
    
    Args:
        file_path (str): Path to video file
        
    Returns:
        Dict[str, Any]: Video information or None if failed
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None
        
        probe_data = json.loads(result.stdout)
        
        # Extract relevant information
        format_info = probe_data.get('format', {})
        streams = probe_data.get('streams', [])
        
        # Find video stream
        video_stream = None
        audio_stream = None
        
        for stream in streams:
            if stream.get('codec_type') == 'video' and not video_stream:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and not audio_stream:
                audio_stream = stream
        
        # Build info dictionary
        info = {
            'duration': float(format_info.get('duration', 0)),
            'size_bytes': int(format_info.get('size', 0)),
            'format_name': format_info.get('format_name', 'unknown'),
            'bit_rate': int(format_info.get('bit_rate', 0))
        }
        
        if video_stream:
            info.update({
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'fps': eval(video_stream.get('r_frame_rate', '0/1')) if '/' in str(video_stream.get('r_frame_rate', '')) else 0,
                'pixel_format': video_stream.get('pix_fmt', 'unknown')
            })
        
        if audio_stream:
            info.update({
                'audio_codec': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0))
            })
        
        return info
        
    except Exception as e:
        logger.debug(f"Error getting video info for {file_path}: {str(e)}")
        return None

# =============================================================================
# FALLBACK ASSET GENERATION
# =============================================================================

def get_fallback_poster(title: str = "Movie Poster", 
                       width: int = 600, 
                       height: int = 900) -> Image.Image:
    """
    Generate a fallback poster image when original poster is unavailable.
    
    Args:
        title (str): Movie title to display
        width (int): Poster width
        height (int): Poster height
        
    Returns:
        Image.Image: Generated fallback poster
    """
    try:
        # Create canvas with gradient background
        poster = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(poster)
        
        # Create gradient background
        for y in range(height):
            ratio = y / height
            r = int(26 * (1 - ratio) + 56 * ratio)  # 1a -> 38
            g = int(26 * (1 - ratio) + 26 * ratio)  # 1a -> 1a
            b = int(46 * (1 - ratio) + 78 * ratio)  # 2e -> 4e
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Load font (with fallback)
        try:
            title_font = ImageFont.truetype("arial.ttf", width // 15)
            subtitle_font = ImageFont.truetype("arial.ttf", width // 25)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Draw movie camera icon (simple)
        icon_size = width // 6
        icon_x = (width - icon_size) // 2
        icon_y = height // 3
        
        # Camera body
        draw.rectangle([
            (icon_x, icon_y),
            (icon_x + icon_size, icon_y + icon_size // 2)
        ], fill='#ffffff', outline='#cccccc', width=2)
        
        # Camera lens
        lens_size = icon_size // 3
        lens_x = icon_x + (icon_size - lens_size) // 2
        lens_y = icon_y + icon_size // 8
        draw.ellipse([
            (lens_x, lens_y),
            (lens_x + lens_size, lens_y + lens_size)
        ], fill='#333333', outline='#cccccc', width=2)
        
        # Title text
        title_y = icon_y + icon_size // 2 + 40
        
        # Wrap title text
        words = title.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= width - 40:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw title lines
        for i, line in enumerate(lines[:3]):  # Max 3 lines
            line_bbox = draw.textbbox((0, 0), line, font=title_font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (width - line_width) // 2
            line_y = title_y + (i * 50)
            
            # Text shadow
            draw.text((line_x + 2, line_y + 2), line, fill='#000000', font=title_font)
            # Main text
            draw.text((line_x, line_y), line, fill='#ffffff', font=title_font)
        
        # Subtitle
        subtitle = "Poster Not Available"
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (width - subtitle_width) // 2
        subtitle_y = title_y + len(lines) * 50 + 30
        
        draw.text((subtitle_x + 1, subtitle_y + 1), subtitle, fill='#000000', font=subtitle_font)
        draw.text((subtitle_x, subtitle_y), subtitle, fill='#cccccc', font=subtitle_font)
        
        logger.debug(f"Generated fallback poster: {width}x{height}")
        return poster
        
    except Exception as e:
        logger.error(f"Error generating fallback poster: {str(e)}")
        # Return basic solid color image as last resort
        return Image.new('RGB', (width, height), color='#333333')

# =============================================================================
# TEMPORARY FILE MANAGEMENT
# =============================================================================

def clean_temp_files(*directories: str) -> Dict[str, Any]:
    """
    Clean up temporary files in specified directories.
    
    Args:
        *directories: Directory paths to clean
        
    Returns:
        Dict[str, Any]: Cleanup results
    """
    results = {
        'directories_cleaned': 0,
        'files_deleted': 0,
        'bytes_freed': 0,
        'errors': []
    }
    
    try:
        import shutil
        
        for directory in directories:
            try:
                if os.path.exists(directory):
                    # Calculate directory size before deletion
                    dir_size = _get_directory_size(directory)
                    
                    # Delete directory
                    shutil.rmtree(directory)
                    
                    # Update results
                    results['directories_cleaned'] += 1
                    results['bytes_freed'] += dir_size
                    
                    logger.debug(f"Cleaned temporary directory: {directory} ({dir_size / 1024 / 1024:.1f} MB)")
                
            except Exception as e:
                error_msg = f"Error cleaning {directory}: {str(e)}"
                results['errors'].append(error_msg)
                logger.warning(error_msg)
        
        logger.info(f"🧹 Cleanup complete: {results['directories_cleaned']} directories, {results['bytes_freed'] / 1024 / 1024:.1f} MB freed")
        
        return results
        
    except Exception as e:
        results['errors'].append(f"Cleanup error: {str(e)}")
        logger.error(f"Error in cleanup: {str(e)}")
        return results


def ensure_media_directories(*directory_names: str) -> List[str]:
    """
    Ensure media directories exist and return their paths.
    
    Args:
        *directory_names: Directory names to create
        
    Returns:
        List[str]: List of created directory paths
    """
    created_dirs = []
    
    try:
        for dir_name in directory_names:
            if ensure_directory(dir_name):
                created_dirs.append(dir_name)
                logger.debug(f"Ensured directory exists: {dir_name}")
            else:
                logger.warning(f"Could not create directory: {dir_name}")
        
        return created_dirs
        
    except Exception as e:
        logger.error(f"Error ensuring media directories: {str(e)}")
        return created_dirs

# =============================================================================
# FORMAT DETECTION AND CONVERSION
# =============================================================================

def detect_media_format(file_path: str) -> Dict[str, Any]:
    """
    Detect media format and basic properties.
    
    Args:
        file_path (str): Path to media file
        
    Returns:
        Dict[str, Any]: Format detection results
    """
    result = {
        'exists': False,
        'type': 'unknown',
        'format': 'unknown',
        'size_bytes': 0,
        'valid': False
    }
    
    try:
        if not os.path.exists(file_path):
            return result
        
        result['exists'] = True
        result['size_bytes'] = os.path.getsize(file_path)
        
        # Get file extension
        extension = Path(file_path).suffix.lower()
        
        # Detect type based on extension
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
        
        if extension in image_extensions:
            result['type'] = 'image'
            result['format'] = extension[1:]  # Remove dot
            
            # Validate image
            try:
                dimensions = get_image_dimensions(file_path)
                if dimensions:
                    result['valid'] = True
                    result['width'], result['height'] = dimensions
            except:
                pass
                
        elif extension in video_extensions:
            result['type'] = 'video'
            result['format'] = extension[1:]  # Remove dot
            
            # Validate video
            if validate_video_file(file_path):
                result['valid'] = True
                
                # Get additional video info
                video_info = get_video_info(file_path)
                if video_info:
                    result.update(video_info)
        
        return result
        
    except Exception as e:
        logger.debug(f"Error detecting media format for {file_path}: {str(e)}")
        return result


def is_portrait_format(file_path: str) -> Optional[bool]:
    """
    Check if media file is in portrait format (height > width).
    
    Args:
        file_path (str): Path to media file
        
    Returns:
        bool: True if portrait, False if landscape, None if unknown
    """
    try:
        format_info = detect_media_format(file_path)
        
        if format_info.get('valid') and 'width' in format_info and 'height' in format_info:
            return format_info['height'] > format_info['width']
        
        return None
        
    except Exception as e:
        logger.debug(f"Error checking portrait format for {file_path}: {str(e)}")
        return None

# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

def monitor_media_operation(operation_name: str):
    """
    Decorator for monitoring media operation performance.
    
    Args:
        operation_name (str): Name of the operation being monitored
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            
            start_time = time.time()
            logger.debug(f"🔄 Starting {operation_name}...")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"✅ {operation_name} completed in {execution_time:.2f}s")
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"❌ {operation_name} failed after {execution_time:.2f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator

# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _get_directory_size(directory: str) -> int:
    """Get total size of directory in bytes."""
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except:
                    pass
        return total_size
    except:
        return 0

# =============================================================================
# BACKGROUND MUSIC SELECTION
# =============================================================================

def select_background_music(genre: str) -> str:
    """
    Select appropriate background music URL based on the genre.
    
    Uses genre-specific background music to enhance the video experience.
    Supports both English and French genres with case-insensitive matching.
    
    Args:
        genre (str): Content genre (e.g., 'Horror', 'Comedy', 'Action')
        
    Returns:
        str: Cloudinary URL for the appropriate background music
        
    Examples:
        >>> select_background_music('Horror')
        'https://res.cloudinary.com/dodod8s0v/video/upload/v1754637489/horror_bg_rbvweq.mp3'
        
        >>> select_background_music('comedy')  # Case insensitive
        'https://res.cloudinary.com/dodod8s0v/video/upload/v1756218702/comedy_uju3dv.mp3'
        
        >>> select_background_music('Drama')   # Uses default horror for unknown genres
        'https://res.cloudinary.com/dodod8s0v/video/upload/v1754637489/horror_bg_rbvweq.mp3'
    """
    logger.info(f"🎵 Selecting background music for genre: {genre}")
    
    # Background music URLs by genre - ALL LOWERCASE for easy matching
    BACKGROUND_MUSIC_URLS = {
        # Comedy genres
        'comedy': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1756218702/comedy_uju3dv.mp3',
        
        # Action & Adventure genres  
        'action': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1756218054/action_y1zm5x.mp3',
        'action & adventure': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1756218054/action_y1zm5x.mp3',
        'action & aventure': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1756218054/action_y1zm5x.mp3',
        
        # Horror genres
        'horror': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1754637489/horror_bg_rbvweq.mp3',
        'horreur': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1754637489/horror_bg_rbvweq.mp3',
        'thriller': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1754637489/horror_bg_rbvweq.mp3',
        'mystery & thriller': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1754637489/horror_bg_rbvweq.mp3',
        
        # Default fallback (using Action as default)
        'default': 'https://res.cloudinary.com/dodod8s0v/video/upload/v1754637489/action_y1zm5x.mp3'
    }
    
    if not genre:
        logger.info("🎵 No genre provided, using default background music")
        return BACKGROUND_MUSIC_URLS['default']
    
    # Normalize genre for comparison (lowercase, stripped)
    genre_normalized = genre.strip().lower()
    
    # Check for exact match first
    if genre_normalized in BACKGROUND_MUSIC_URLS:
        selected_url = BACKGROUND_MUSIC_URLS[genre_normalized]
        logger.info(f"🎵 Genre '{genre}' matched background music: {selected_url}")
        return selected_url
    
    # No match found, use default
    logger.info(f"🎵 Genre '{genre}' not specifically mapped, using default background music")
    return BACKGROUND_MUSIC_URLS['default']


def get_background_music_info(genre: str) -> Dict[str, str]:
    """
    Get background music information including URL and metadata.
    
    Args:
        genre (str): Content genre
        
    Returns:
        Dict[str, str]: Background music information
    """
    music_url = select_background_music(genre)
    
    # Extract music type from URL for metadata
    music_type = 'horror'  # default
    if 'comedy' in music_url:
        music_type = 'comedy'
    elif 'action' in music_url:
        music_type = 'action'
    elif 'horror' in music_url:
        music_type = 'horror'
    
    return {
        'url': music_url,
        'type': music_type,
        'genre': genre,
        'description': f'{music_type.title()} background music for {genre} content'
    }

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_media_stats(directory: str) -> Dict[str, Any]:
    """
    Get statistics about media files in a directory.
    
    Args:
        directory (str): Directory path to analyze
        
    Returns:
        Dict[str, Any]: Media statistics
    """
    stats = {
        'total_files': 0,
        'images': 0,
        'videos': 0,
        'other': 0,
        'total_size_mb': 0,
        'largest_file': {'path': '', 'size_mb': 0},
        'formats': {}
    }
    
    try:
        if not os.path.exists(directory):
            return stats
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    format_info = detect_media_format(file_path)
                    file_size_mb = format_info['size_bytes'] / 1024 / 1024
                    
                    stats['total_files'] += 1
                    stats['total_size_mb'] += file_size_mb
                    
                    # Track file types
                    if format_info['type'] == 'image':
                        stats['images'] += 1
                    elif format_info['type'] == 'video':
                        stats['videos'] += 1
                    else:
                        stats['other'] += 1
                    
                    # Track formats
                    format_name = format_info['format']
                    stats['formats'][format_name] = stats['formats'].get(format_name, 0) + 1
                    
                    # Track largest file
                    if file_size_mb > stats['largest_file']['size_mb']:
                        stats['largest_file'] = {
                            'path': file_path,
                            'size_mb': file_size_mb
                        }
                
                except Exception as e:
                    logger.debug(f"Error analyzing file {file_path}: {str(e)}")
                    continue
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting media stats for {directory}: {str(e)}")
        return stats