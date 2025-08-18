"""
StreamGank Movie Trailer Clip Processor

This module handles processing movie trailers into highlight clips for 
TikTok/Instagram Reels format.

Features:
- Trailer download and processing
- 15-second highlight clip extraction
- Portrait format conversion (9:16)
- Cloudinary upload and optimization
- Multiple transformation modes
- Batch processing support

Author: StreamGank Development Team
Version: 1.0.0 - Modular Implementation
"""

import os
import logging
import subprocess
import tempfile
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
import cloudinary
import cloudinary.uploader
import yt_dlp

from config.settings import get_video_settings, get_api_config
from utils.validators import is_valid_url
from utils.file_utils import ensure_directory, cleanup_temp_files

logger = logging.getLogger(__name__)

# =============================================================================
# TRAILER CLIP PROCESSING
# =============================================================================

def process_movie_trailers_to_clips(movie_data: List[Dict], max_movies: int = 3, 
                                   transform_mode: str = "youtube_shorts") -> Dict[str, str]:
    """
    Process movie trailers to create highlight clips and upload to Cloudinary.
    
    MODULAR VERSION - Replaces legacy function from streamgank_helpers.py
    
    Args:
        movie_data (List[Dict]): List of movie data dictionaries with trailer_url
        max_movies (int): Maximum number of movies to process
        transform_mode (str): Transformation mode - "fit", "pad", "scale", "youtube_shorts"
        
    Returns:
        Dict[str, str]: Dictionary mapping movie titles to Cloudinary clip URLs
    """
    logger.info(f"🎬 Processing movie trailers to clips for {min(len(movie_data), max_movies)} movies")
    logger.info(f"🎬 Transform mode: {transform_mode}")
    logger.info("📐 Output: 15-second highlights in 9:16 portrait format")
    
    clip_urls = {}
    temp_dirs = ["temp_trailers", "temp_clips"]
    
    try:
        # Create temporary directories
        for temp_dir in temp_dirs:
            ensure_directory(temp_dir)
        
        # Get video settings
        video_settings = get_video_settings()
        clip_duration = video_settings.get('clip_duration', 15)
        
        # Process up to max_movies
        for i, movie in enumerate(movie_data[:max_movies]):
            try:
                title = movie.get('title', f'Movie_{i+1}')
                trailer_url = movie.get('trailer_url', '')
                
                logger.info(f"🎥 Processing trailer {i+1}: {title}")
                
                if not trailer_url or not is_valid_url(trailer_url):
                    logger.warning(f"⚠️ No valid trailer URL for: {title}")
                    continue
                
                # Process single trailer
                clip_url = _process_single_trailer(
                    movie, trailer_url, transform_mode, clip_duration, i+1
                )
                
                if clip_url:
                    clip_urls[title] = clip_url
                    logger.info(f"✅ Clip created for: {title}")
                else:
                    logger.error(f"❌ Failed to create clip for: {title}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing trailer for movie {i+1}: {str(e)}")
                continue
        
        # Cleanup temporary files
        for temp_dir in temp_dirs:
            cleanup_temp_files(temp_dir)
        
        # Report results with emphasis on YouTube importance
        successful_count = len(clip_urls)
        total_attempted = len(movie_data[:max_movies])
        
        if successful_count == total_attempted:
            logger.info(f"🎉 Perfect! Successfully created {successful_count}/{total_attempted} trailer clips")
        elif successful_count > 0:
            logger.warning(f"⚠️ Partial success: {successful_count}/{total_attempted} trailer clips created")
            logger.info(f"   💡 Some YouTube videos may have restrictions - this is normal")
            logger.info(f"   🎬 Video generation will continue with available clips")
        else:
            logger.error(f"❌ No trailer clips could be downloaded ({successful_count}/{total_attempted})")
            logger.error(f"   This may indicate YouTube bot detection is too strong")
            logger.error(f"   💡 Try running locally first, or check YouTube URLs manually")
        
        return clip_urls
        
    except Exception as e:
        logger.error(f"❌ Critical error in process_movie_trailers_to_clips: {str(e)}")
        # Cleanup on error
        for temp_dir in temp_dirs:
            cleanup_temp_files(temp_dir)
        # Return empty dict but don't raise exception - let workflow decide
        return {}


def _process_single_trailer(movie_data: Dict, trailer_url: str, transform_mode: str,
                           clip_duration: int, movie_num: int) -> Optional[str]:
    """
    Process a single movie trailer into a highlight clip.
    
    MODULAR VERSION - Uses same approach as working legacy code
    
    Args:
        movie_data (Dict): Movie information
        trailer_url (str): URL of the trailer video
        transform_mode (str): Transformation mode
        clip_duration (int): Duration of clip in seconds
        movie_num (int): Movie number for file naming
        
    Returns:
        str: Cloudinary URL of processed clip or None if failed
    """
    try:
        title = movie_data.get('title', f'Movie_{movie_num}')
        movie_id = str(movie_data.get('id', movie_num))
        
        logger.info(f"🎯 Processing Movie {movie_num}: {title}")
        logger.info(f"   Movie ID: {movie_id}")
        logger.info(f"   Trailer URL: {trailer_url}")
        
        # Step 1: Download YouTube trailer (same as legacy)
        downloaded_trailer = _download_youtube_trailer(trailer_url)
        if not downloaded_trailer:
            logger.error(f"❌ Failed to download trailer for {title}")
            return None
        
        # Step 2: Extract highlight (same as legacy)
        highlight_clip = _extract_second_highlight(downloaded_trailer, start_time=30)
        if not highlight_clip:
            logger.error(f"❌ Failed to extract highlight for {title}")
            return None
        
        # Step 3: Upload to Cloudinary (same as legacy)
        cloudinary_url = _upload_clip_to_cloudinary(highlight_clip, title, movie_id, transform_mode)
        if cloudinary_url:
            logger.info(f"✅ Successfully processed {title}: {cloudinary_url}")
            return cloudinary_url
        else:
            logger.error(f"❌ Failed to upload clip for {title}")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error processing single trailer: {str(e)}")
        return None


def _download_youtube_trailer(trailer_url: str, output_dir: str = "temp_trailers") -> Optional[str]:
    """
    Download YouTube trailer video using yt-dlp with cloud server optimization.
    
    MODULAR VERSION - Enhanced with anti-bot detection for Railway/cloud deployment
    
    Args:
        trailer_url (str): YouTube trailer URL
        output_dir (str): Directory to save downloaded video
        
    Returns:
        str: Path to downloaded video file or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract video ID for consistent naming
        video_id = _extract_youtube_video_id(trailer_url)
        if not video_id:
            logger.error(f"Invalid YouTube URL: {trailer_url}")
            return None
        
        # Enhanced yt-dlp configuration for cloud servers (anti-bot detection)
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',  # Prefer 720p MP4
            'outtmpl': os.path.join(output_dir, f'{video_id}_trailer.%(ext)s'),
            'quiet': True,  # Reduce verbose output
            'no_warnings': True,
            # Anti-bot detection headers and options
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            # Additional anti-detection options
            'extractor_retries': 3,  # Retry on temporary failures
            'retries': 3,            # Retry downloads
            'sleep_interval': 2,     # Wait between requests
            'max_sleep_interval': 5, # Max wait time
            # Bypass age restrictions
            'age_limit': None,
            # Use extract_flat to reduce requests
            'extract_flat': False,
        }
        
        logger.info(f"🎬 Downloading YouTube trailer (cloud-optimized): {trailer_url}")
        logger.info(f"   Video ID: {video_id}")
        logger.info(f"   Output directory: {output_dir}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download the video with retries
            ydl.download([trailer_url])
            
            # Find the downloaded file
            for file in os.listdir(output_dir):
                if video_id in file and file.endswith(('.mp4', '.webm', '.mkv')):
                    downloaded_path = os.path.join(output_dir, file)
                    logger.info(f"✅ Successfully downloaded: {downloaded_path}")
                    return downloaded_path
        
        logger.error(f"❌ Could not find downloaded file for video ID: {video_id}")
        return None
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific YouTube errors with solutions
        if "Sign in to confirm you're not a bot" in error_msg:
            logger.error(f"🤖 YouTube bot detection for: {trailer_url}")
            logger.info(f"   Attempting fallback method...")
            
            # Try with different extraction method
            return _download_youtube_fallback(trailer_url, output_dir, video_id)
        
        elif "Video unavailable" in error_msg:
            logger.warning(f"📵 Video unavailable: {trailer_url}")
            return None
            
        elif "Private video" in error_msg:
            logger.warning(f"🔒 Private video: {trailer_url}")
            return None
            
        else:
            logger.error(f"❌ Error downloading YouTube trailer {trailer_url}: {str(e)}")
            return None


def _download_youtube_fallback(trailer_url: str, output_dir: str, video_id: str) -> Optional[str]:
    """
    Fallback method for downloading YouTube videos when bot detection is triggered.
    
    Uses alternative yt-dlp configuration with proxy-like behavior.
    
    Args:
        trailer_url (str): YouTube trailer URL
        output_dir (str): Directory to save downloaded video
        video_id (str): Extracted video ID
        
    Returns:
        str: Path to downloaded video file or None if failed
    """
    try:
        logger.info(f"🔄 Trying fallback download method for: {video_id}")
        
        # Ultra-conservative yt-dlp options to avoid detection
        fallback_opts = {
            'format': 'worst[height>=360][ext=mp4]/worst[ext=mp4]/worst',  # Lower quality to reduce suspicion
            'outtmpl': os.path.join(output_dir, f'{video_id}_trailer_fallback.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            # More aggressive anti-bot measures
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity',
                'Connection': 'close',  # Don't keep connections alive
            },
            'extractor_retries': 5,     # More retries
            'retries': 5,
            'sleep_interval': 5,        # Longer waits
            'max_sleep_interval': 15,
            'fragment_retries': 5,
            # Try to bypass geo-restrictions
            'geo_bypass': True,
            # Use slower extraction
            'extract_flat': True,
        }
        
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            logger.info(f"⏳ Fallback download starting (this may take longer)...")
            ydl.download([trailer_url])
            
            # Find the downloaded file
            for file in os.listdir(output_dir):
                if video_id in file and 'fallback' in file and file.endswith(('.mp4', '.webm', '.mkv')):
                    downloaded_path = os.path.join(output_dir, file)
                    logger.info(f"🎉 Fallback download successful: {downloaded_path}")
                    return downloaded_path
        
        logger.warning(f"⚠️ Fallback method could not find downloaded file for: {video_id}")
        return None
        
    except Exception as fallback_error:
        logger.error(f"❌ Fallback download also failed: {str(fallback_error)}")
        logger.info(f"💡 Suggestion: Try running locally first to test, then deploy")
        return None


def _extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various YouTube URL formats.
    
    MODULAR VERSION - Same as working legacy code
    
    Args:
        url (str): YouTube URL in various formats
        
    Returns:
        str: YouTube video ID or None if not found
    """
    # Various YouTube URL patterns
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    logger.warning(f"Could not extract YouTube video ID from URL: {url}")
    return None


def _extract_second_highlight(video_path: str, start_time: int = 30, output_dir: str = "temp_clips") -> Optional[str]:
    """
    Extract a highlight clip from a video and convert to CINEMATIC PORTRAIT format (9:16).
    
    MODULAR VERSION - Uses exact same approach as working legacy code
    
    This function converts landscape YouTube trailers to portrait format using advanced techniques:
    1. Creates a soft Gaussian-blurred background from the original video
    2. Centers the original frame on top of the blurred background
    3. Enhances contrast, clarity, and saturation for TikTok/Instagram Reels aesthetics
    4. Maintains HD quality (1080x1920) without black bars
    
    Args:
        video_path (str): Path to the source video file (typically landscape YouTube trailer)
        start_time (int): Start time in seconds (default: 30s to skip intros)
        output_dir (str): Directory to save the cinematic portrait highlight clip
        
    Returns:
        str: Path to the extracted CINEMATIC PORTRAIT highlight clip or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        video_name = Path(video_path).stem
        output_path = os.path.join(output_dir, f"{video_name}_10s_highlight.mp4")
        
        logger.info(f"🎞️ Extracting CINEMATIC PORTRAIT highlight from: {video_path}")
        logger.info(f"   Start time: {start_time}s")
        logger.info(f"   Technique: Gaussian blur background + centered frame")
        logger.info(f"   Enhancement: Contrast, clarity, and saturation boost")
        logger.info(f"   Output: {output_path}")
        
        # Use FFmpeg with Gaussian blur background for cinematic portrait conversion
        # Creates a soft blurred background instead of black bars for TikTok/Instagram Reels
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,           # Input file
            '-ss', str(start_time),     # Start time
            '-t', '15',                 # Duration
            '-c:v', 'libx264',         # Video codec
            '-c:a', 'aac',             # Audio codec
            '-crf', '15',              # Ultra-high quality for social media
            '-preset', 'slow',         # Better compression efficiency
            '-profile:v', 'high',      # H.264 high profile for better quality
            '-level:v', '4.0',         # H.264 level 4.0 for high resolution
            '-movflags', '+faststart', # Optimize for web streaming
            '-pix_fmt', 'yuv420p',     # Ensure compatibility
            # Complex filter for Gaussian blur background + centered original
            '-filter_complex', 
            '[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=20[blurred];'
            '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[scaled];'
            '[blurred][scaled]overlay=(W-w)/2:(H-h)/2,unsharp=5:5:1.0:5:5:0.3,eq=contrast=1.1:brightness=0.05:saturation=1.2',
            '-r', '30',                # 30 FPS for smooth playback
            '-maxrate', '4000k',       # Higher bitrate for premium quality
            '-bufsize', '8000k',       # Larger buffer size
            '-y',                       # Overwrite output file
            output_path
        ]
        
        # Run FFmpeg command
        result = subprocess.run(
            ffmpeg_cmd, 
            capture_output=True, 
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully created CINEMATIC PORTRAIT highlight: {output_path}")
            logger.info(f"   🎬 Format: 1080x1920 with Gaussian blur background")
            logger.info(f"   🎨 Enhanced for TikTok/Instagram Reels aesthetics")
            return output_path
        else:
            logger.error(f"❌ FFmpeg error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ FFmpeg timeout while processing: {video_path}")
        return None
    except Exception as e:
        logger.error(f"❌ Error extracting highlight from {video_path}: {str(e)}")
        return None


def _download_direct_video(video_url: str, output_path: str) -> bool:
    """
    Fallback method to download video directly.
    
    Args:
        video_url (str): Direct video URL
        output_path (str): Output file path
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(video_url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.debug(f"📥 Downloaded video directly: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in direct video download: {str(e)}")
        return False


def _extract_highlight_clip(input_path: str, output_path: str, duration: int, 
                           transform_mode: str) -> bool:
    """
    Extract highlight clip from trailer using FFmpeg.
    
    Args:
        input_path (str): Path to input trailer
        output_path (str): Path to output clip
        duration (int): Duration of clip in seconds
        transform_mode (str): Transformation mode
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get video settings
        video_settings = get_video_settings()
        target_resolution = video_settings.get('target_resolution', (1080, 1920))
        target_fps = video_settings.get('target_fps', 60)
        video_bitrate = video_settings.get('video_bitrate', '2M')
        
        # Calculate start time (skip first 30 seconds, take middle section)
        start_offset = video_settings.get('clip_start_offset', 30)
        
        # Build FFmpeg command based on transform mode
        if transform_mode == "youtube_shorts":
            # Optimized for YouTube Shorts (9:16 portrait)
            cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_offset),  # Start offset
                '-t', str(duration),       # Duration
                '-vf', f'scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease,pad={target_resolution[0]}:{target_resolution[1]}:(ow-iw)/2:(oh-ih)/2,fps={target_fps}',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-b:v', video_bitrate,
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',  # Overwrite output
                output_path
            ]
        elif transform_mode == "fit":
            # Fit video maintaining aspect ratio
            cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_offset),
                '-t', str(duration),
                '-vf', f'scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-y',
                output_path
            ]
        else:  # Default transformation
            cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_offset),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-y',
                output_path
            ]
        
        # Execute FFmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Verify output file size
            file_size = os.path.getsize(output_path)
            if file_size > 1000:  # At least 1KB
                logger.debug(f"🎬 Created clip: {output_path} ({file_size} bytes)")
                return True
            else:
                logger.error(f"❌ Output clip too small: {file_size} bytes")
                return False
        else:
            logger.error(f"❌ FFmpeg failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ FFmpeg timeout for {input_path}")
        return False
    except Exception as e:
        logger.error(f"❌ Error extracting highlight clip: {str(e)}")
        return False


def _upload_clip_to_cloudinary(clip_path: str, movie_title: str, movie_id: str, transform_mode: str = "youtube_shorts") -> Optional[str]:
    """
    Upload a video clip to Cloudinary with optimized settings.
    
    MODULAR VERSION - Uses exact same approach as working legacy code
    
    Args:
        clip_path (str): Path to the video clip file
        movie_title (str): Movie title for naming
        movie_id (str): Movie ID for unique identification
        transform_mode (str): Transformation mode - "fit", "pad", "scale", or "auto"
        
    Returns:
        str: Cloudinary URL of uploaded clip or None if failed
    """
    try:
        # Create a clean filename from movie title
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', movie_title.lower())
        clean_title = re.sub(r'_+', '_', clean_title).strip('_')
        
        # Create unique public ID
        public_id = f"movie_clips/{clean_title}_{movie_id}_10s" if movie_id else f"movie_clips/{clean_title}_10s"
        
        logger.info(f"☁️ Uploading clip to Cloudinary: {clip_path}")
        logger.info(f"   Movie: {movie_title}")
        logger.info(f"   Public ID: {public_id}")
        logger.info(f"   Transform mode: {transform_mode}")
        
        # YouTube Shorts optimized transformation modes (9:16 portrait - 1080x1920)
        transform_modes = {
            "fit": [
                {"width": 1080, "height": 1920, "crop": "fit", "background": "black"},  # YouTube Shorts standard resolution
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "2000k"}  # High bitrate for crisp quality
            ],
            "smart_fit": [
                {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},  # Smart crop with center focus
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "2500k"},  # Even higher bitrate
                {"flags": "progressive"}  # Progressive scan for smooth playbook
            ],
            "pad": [
                {"width": 1080, "height": 1920, "crop": "pad", "background": "auto"},   # Smart padding with auto background
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"bit_rate": "2000k"}
            ],
            "scale": [
                {"width": 1080, "height": 1920, "crop": "scale"},                      # Scale to fit (may distort)
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"bit_rate": "1800k"}
            ],
            "youtube_shorts": [
                {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},  # YouTube Shorts optimized
                {"quality": "auto:best"},
                {"format": "mp4"},
                {"video_codec": "h264"},
                {"bit_rate": "3000k"},  # Premium bitrate for YouTube Shorts quality
                {"flags": "progressive"},
                {"audio_codec": "aac"},
                {"audio_frequency": 48000}  # High quality audio
            ]
        }
        
        # Get the transformation based on mode
        transformation = transform_modes.get(transform_mode, transform_modes["youtube_shorts"])
        
        # Upload to Cloudinary with video optimization (using selected transformation)
        upload_result = cloudinary.uploader.upload(
            clip_path,
            resource_type="video",
            public_id=public_id,
            folder="movie_clips",
            overwrite=True,
            quality="auto",              # Automatic quality optimization
            format="mp4",               # Ensure MP4 format
            video_codec="h264",         # Use H.264 codec for compatibility
            audio_codec="aac",          # Use AAC audio codec
            transformation=transformation
        )
        
        cloudinary_url = upload_result.get('secure_url')
        logger.info(f"✅ Successfully uploaded to Cloudinary: {cloudinary_url}")
        
        return cloudinary_url
        
    except Exception as e:
        logger.error(f"❌ Error uploading {clip_path} to Cloudinary: {str(e)}")
        return None

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_clip_processing_stats() -> Dict[str, Any]:
    """
    Get clip processing statistics and configuration info.
    
    Returns:
        Dict[str, Any]: Statistics and configuration
    """
    stats = {
        'ffmpeg_available': _check_ffmpeg_available(),
        'yt_dlp_available': _check_ytdlp_available(),
        'cloudinary_configured': bool(os.getenv('CLOUDINARY_URL')),
        'temp_directories': ['temp_trailers', 'temp_clips'],
        'supported_formats': ['mp4', 'avi', 'mov', 'mkv'],
        'last_error': None
    }
    
    try:
        # Get video settings
        video_settings = get_video_settings()
        stats['processing_settings'] = {
            'clip_duration': video_settings.get('clip_duration', 15),
            'target_resolution': video_settings.get('target_resolution', (1080, 1920)),
            'target_fps': video_settings.get('target_fps', 60),
            'start_offset': video_settings.get('clip_start_offset', 30)
        }
        
        # Get Cloudinary settings
        cloudinary_config = get_api_config('cloudinary')
        if cloudinary_config:
            stats['cloudinary_settings'] = {
                'quality': cloudinary_config.get('quality', 'auto:good'),
                'timeout': cloudinary_config.get('timeout', 120),
                'chunk_size': cloudinary_config.get('chunk_size', 6000000)
            }
        
        return stats
        
    except Exception as e:
        stats['last_error'] = str(e)
        logger.error(f"Error getting clip processing stats: {str(e)}")
        return stats


def _check_ffmpeg_available() -> bool:
    """Check if FFmpeg is available."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def _check_ytdlp_available() -> bool:
    """Check if yt-dlp is available."""
    try:
        result = subprocess.run(['yt-dlp', '--version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def validate_processing_requirements() -> Dict[str, Any]:
    """
    Validate that all requirements for clip processing are met.
    
    Returns:
        Dict[str, Any]: Validation results
    """
    validation = {
        'ready': True,
        'missing_requirements': [],
        'warnings': []
    }
    
    # Check FFmpeg
    if not _check_ffmpeg_available():
        validation['ready'] = False
        validation['missing_requirements'].append('FFmpeg not available - required for video processing')
    
    # Check yt-dlp (optional but recommended)
    if not _check_ytdlp_available():
        validation['warnings'].append('yt-dlp not available - some trailer URLs may not work')
    
    # Check Cloudinary
    if not os.getenv('CLOUDINARY_URL'):
        validation['ready'] = False
        validation['missing_requirements'].append('Cloudinary not configured - required for video upload')
    
    # Check temp directories
    try:
        for temp_dir in ['temp_trailers', 'temp_clips']:
            ensure_directory(temp_dir)
    except Exception as e:
        validation['ready'] = False
        validation['missing_requirements'].append(f'Cannot create temp directories: {str(e)}')
    
    return validation