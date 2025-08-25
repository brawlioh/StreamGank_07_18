"""
StreamGank Video Processor

This module provides video processing utilities including duration analysis,
URL validation, and metadata extraction for video assets.

Features:
- Video duration analysis using FFprobe
- URL validation and accessibility checks
- Metadata extraction from video files
- Duration estimation for various content types
- Video quality assessment utilities
"""

import logging
import subprocess
import json
from typing import Dict, List, Optional, Any, Tuple
import requests

from utils.validators import is_valid_url
from ai.heygen_client import estimate_video_duration

logger = logging.getLogger(__name__)

# =============================================================================
# VIDEO DURATION ANALYSIS
# =============================================================================

def calculate_video_durations(video_urls: Dict[str, str], 
                             scripts: Optional[Dict] = None) -> Dict[str, float]:
    """
    Calculate EXACT video durations using FFprobe for precise Creatomate composition.
    
    STRICT MODE: Only accepts actual durations from video file analysis.
    NO FALLBACKS OR ESTIMATES - if FFprobe fails, the video is not ready/accessible.
    
    Args:
        video_urls (Dict): Dictionary mapping keys to video URLs (REQUIRED)
        scripts (Dict): Script data (not used - for compatibility only)
        
    Returns:
        Dict[str, float]: EXACT video durations in seconds with 2-decimal precision
        
    Raises:
        ValueError: If video URLs are invalid
        RuntimeError: If exact duration extraction fails for any video
    """
    logger.info(f"📏 STRICT MODE: Getting EXACT durations for {len(video_urls)} videos")
    logger.info("🎯 Purpose: Precise Creatomate composition timing (FFprobe ONLY - NO ESTIMATES)")
    
    if not video_urls:
        raise ValueError("❌ CRITICAL: No video URLs provided for duration calculation")
    
    durations = {}
    failed_extractions = []
    
    for key, url in video_urls.items():
        logger.info(f"🔍 Extracting EXACT duration: {key}")
        logger.debug(f"   URL: {url}")
        
        # Get EXACT duration using FFprobe ONLY (no fallbacks)
        duration = get_video_duration_from_url(url)
        
        if duration and duration > 0:
            # Map keys to match legacy format: movie1 -> heygen1, movie2 -> heygen2, movie3 -> heygen3
            if key.startswith('movie'):
                heygen_key = key.replace('movie', 'heygen')
                durations[heygen_key] = duration
                logger.info(f"✅ {key} → {heygen_key}: {duration:.2f}s (EXACT - ready for Creatomate)")
            else:
                # Keep original key if not movie format
                durations[key] = duration
                logger.info(f"✅ {key}: {duration:.2f}s (EXACT - ready for Creatomate)")
        else:
            # FFprobe failed - video not ready or URL invalid
            failed_extractions.append(f"{key} -> {url}")
            logger.error(f"❌ FAILED to get EXACT duration for {key}")
            logger.error(f"   This means the video is not ready or URL is invalid")
    
    # STRICT: All durations must be successfully extracted with FFprobe
    if failed_extractions:
        error_details = "\n".join([f"   • {item}" for item in failed_extractions])
        error_message = f"❌ CRITICAL: Failed to get EXACT durations:\n{error_details}"
        logger.error(error_message)
        logger.error("🚫 STRICT MODE: Videos must be ready and accessible for FFprobe analysis")
        logger.error("💡 Possible causes:")
        logger.error("   - HeyGen videos are still processing")
        logger.error("   - Video URLs are invalid or expired")
        logger.error("   - Network connectivity issues")
        logger.error("   - FFmpeg/FFprobe not installed")
        raise RuntimeError(error_message)
    
    # Validate duration quality for Creatomate
    for key, duration in durations.items():
        if duration < 0.5:  # Minimum reasonable duration
            raise ValueError(f"❌ CRITICAL: {key} duration too short: {duration}s (minimum 0.5s)")
        if duration > 600.0:  # Maximum 10 minutes (very generous)
            logger.warning(f"⚠️ {key} duration very long: {duration}s (over 10 minutes)")
    
    # Log detailed timing information for Creatomate debugging
    logger.info("📊 EXACT DURATIONS EXTRACTED FOR CREATOMATE:")
    total_content_duration = 0
    for key, duration in durations.items():
        logger.info(f"   🎬 {key}: {duration:.2f}s (FFprobe verified)")
        total_content_duration += duration
    
    logger.info(f"📈 Total video content: {total_content_duration:.2f}s")
    logger.info(f"📈 Estimated final video: ~{total_content_duration + 4:.2f}s (+ intro/outro)")
    logger.info("✅ All EXACT durations ready for precise Creatomate composition")
    
    return durations


def get_video_duration_from_url(video_url: str, timeout: int = 30) -> Optional[float]:
    """
    Get EXACT video duration from URL using FFprobe - NO FALLBACKS OR ESTIMATES.
    
    STRICT MODE: Only returns actual duration from video file analysis.
    If FFprobe fails, returns None to indicate the video is not accessible/ready.
    
    Args:
        video_url (str): Video URL to analyze
        timeout (int): Timeout in seconds
        
    Returns:
        float: EXACT video duration in seconds or None if FFprobe fails
        
    Raises:
        None - Returns None instead of raising to allow caller to handle failure
    """
    if not video_url or video_url == "":
        logger.error("❌ No video URL provided - cannot get exact duration")
        return None
    
    try:
        if not is_valid_url(video_url):
            logger.error(f"❌ Invalid video URL format: {video_url}")
            return None
        
        logger.info(f"🔍 Getting EXACT duration from video: {video_url[:50]}...")
        
        # Use FFprobe to get EXACT video duration (ONLY method - no fallbacks)
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_url
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        if result.returncode == 0:
            probe_data = json.loads(result.stdout)
            format_info = probe_data.get('format', {})
            duration = float(format_info.get('duration', 0))
            
            if duration > 0:
                logger.info(f"✅ EXACT video duration: {duration:.2f}s (FFprobe verified)")
                return round(duration, 2)  # 2 decimal precision for Creatomate
            else:
                logger.error(f"❌ FFprobe returned zero duration for: {video_url}")
                return None
        else:
            logger.error(f"❌ FFprobe failed with return code {result.returncode}")
            logger.error(f"   FFprobe stderr: {result.stderr}")
            logger.error(f"   Video URL: {video_url}")
            return None
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ FFprobe timeout after {timeout}s - video may not be ready")
        logger.error(f"   Video URL: {video_url}")
        return None
    except FileNotFoundError:
        logger.error("❌ FFprobe not found on system - install FFmpeg")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ FFprobe returned invalid JSON: {str(e)}")
        logger.error(f"   Video URL: {video_url}")
        return None
    except Exception as e:
        logger.error(f"❌ FFprobe error: {str(e)}")
        logger.error(f"   Video URL: {video_url}")
        return None


def estimate_clip_durations(clip_urls: Optional[List[str]]) -> Dict[str, float]:
    """
    Get ACTUAL durations for movie clips for precise Creatomate composition.
    
    STRICT MODE: All clip durations must be obtained from actual video files.
    This ensures accurate timing for Creatomate composition, making it easy to combine,
    adjust, and debug video elements with movie clips.
    
    Args:
        clip_urls (List): List of movie clip URLs (REQUIRED - exactly 3 clips)
        
    Returns:
        Dict[str, float]: ACTUAL clip durations in seconds with 2-decimal precision
        
    Raises:
        ValueError: If clip URLs are missing or invalid
        RuntimeError: If duration extraction fails for any clip
    """
    logger.info("📹 STRICT MODE: Getting ACTUAL durations for movie clips")
    logger.info("🎯 Purpose: Precise Creatomate composition timing for movie clips")
    
    if not clip_urls or len(clip_urls) != 3:
        raise ValueError("❌ CRITICAL: Exactly 3 movie clip URLs required for duration calculation")
    
    durations = {}
    failed_extractions = []
    
    for i, clip_url in enumerate(clip_urls[:3]):
        clip_key = f"clip{i+1}"
        
        if not clip_url or not clip_url.strip():
            failed_extractions.append(f"{clip_key}: empty/missing URL")
            continue
        
        logger.info(f"🔍 Extracting ACTUAL duration: {clip_key}")
        logger.debug(f"   URL: {clip_url}")
        
        # STRICT: Get actual duration from movie clip file (no fallbacks)
        duration = get_video_duration_from_url(clip_url)
        
        if duration and duration > 0:
            # Round to 2 decimal places for precise Creatomate timing
            precise_duration = round(duration, 2)
            durations[clip_key] = precise_duration
            logger.info(f"✅ {clip_key}: {precise_duration:.2f}s (ACTUAL - ready for Creatomate)")
        else:
            failed_extractions.append(f"{clip_key} -> {clip_url}")
            logger.error(f"❌ FAILED to extract ACTUAL duration for {clip_key}")
    
    # STRICT: All clip durations must be successfully extracted
    if failed_extractions:
        error_details = "\n".join([f"   • {item}" for item in failed_extractions])
        error_message = f"❌ CRITICAL: Failed to extract ACTUAL clip durations:\n{error_details}"
        logger.error(error_message)
        logger.error("🚫 STRICT MODE: Cannot use estimates - Creatomate needs precise timing")
        raise RuntimeError(error_message)
    
    # Validate clip duration quality for Creatomate
    for clip_key, duration in durations.items():
        if duration < 1.0:  # Minimum reasonable clip duration
            raise ValueError(f"❌ CRITICAL: {clip_key} duration too short: {duration}s (minimum 1.0s)")
        if duration > 30.0:  # Maximum reasonable clip duration for highlights
            logger.warning(f"⚠️ {clip_key} duration very long: {duration}s (over 30s for highlight)")
    
    # Log detailed timing information for Creatomate debugging
    logger.info("📊 ACTUAL CLIP DURATIONS EXTRACTED FOR CREATOMATE:")
    total_clip_duration = 0
    for clip_key, duration in durations.items():
        logger.info(f"   🎬 {clip_key}: {duration:.2f}s")
        total_clip_duration += duration
    
    logger.info(f"📈 Total movie clips content: {total_clip_duration:.2f}s")
    logger.info("✅ All clip durations ready for precise Creatomate composition")
    
    return durations

def validate_duration_consistency(heygen_durations: Dict[str, float], 
                                clip_durations: Dict[str, float]) -> None:
    """
    Validate duration consistency for Creatomate composition debugging.
    
    STRICT MODE: Ensures all durations are consistent and reasonable for Creatomate.
    Logs detailed information to make it easy to combine, adjust, and debug.
    
    Args:
        heygen_durations: Dictionary of HeyGen video durations
        clip_durations: Dictionary of movie clip durations
        
    Raises:
        ValueError: If durations are inconsistent or unreasonable
    """
    logger.info("🔍 VALIDATING DURATION CONSISTENCY FOR CREATOMATE:")
    
    # Validate HeyGen durations
    required_heygen = {"heygen1", "heygen2", "heygen3"}
    missing_heygen = required_heygen - set(heygen_durations.keys())
    if missing_heygen:
        raise ValueError(f"❌ CRITICAL: Missing HeyGen durations: {missing_heygen}")
    
    # Validate clip durations
    required_clips = {"clip1", "clip2", "clip3"}
    missing_clips = required_clips - set(clip_durations.keys())
    if missing_clips:
        raise ValueError(f"❌ CRITICAL: Missing clip durations: {missing_clips}")
    
    # Check duration ranges
    for key, duration in heygen_durations.items():
        if duration < 3.0 or duration > 60.0:  # Reasonable range for HeyGen videos
            logger.warning(f"⚠️ {key} duration unusual: {duration:.2f}s (expected 3-60s)")
    
    for key, duration in clip_durations.items():
        if duration < 5.0 or duration > 30.0:  # Reasonable range for movie clips
            logger.warning(f"⚠️ {key} duration unusual: {duration:.2f}s (expected 5-30s)")
    
    # Calculate total content
    total_heygen = sum(heygen_durations.values())
    total_clips = sum(clip_durations.values())
    total_content = total_heygen + total_clips
    estimated_final = total_content + 4  # + intro/outro
    
    logger.info(f"   🎤 Total HeyGen content: {total_heygen:.2f}s")
    logger.info(f"   🎬 Total clip content: {total_clips:.2f}s")
    logger.info(f"   📊 Total video content: {total_content:.2f}s")
    logger.info(f"   🎯 Estimated final video: ~{estimated_final:.2f}s")
    
    # Duration balance check
    heygen_percentage = (total_heygen / total_content) * 100
    clips_percentage = (total_clips / total_content) * 100
    
    logger.info(f"   📈 HeyGen: {heygen_percentage:.1f}% | Clips: {clips_percentage:.1f}%")
    
    if heygen_percentage < 20 or heygen_percentage > 80:
        logger.warning(f"⚠️ Unusual HeyGen/Clip balance: {heygen_percentage:.1f}% HeyGen")
    
    logger.info("✅ Duration consistency validated - ready for Creatomate timing")


# =============================================================================
# URL VALIDATION FUNCTIONS
# =============================================================================

def validate_video_urls(heygen_urls: Dict[str, str],
                       movie_covers: Optional[List[str]] = None,
                       movie_clips: Optional[List[str]] = None,
                       scroll_video_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate all video and image URLs for accessibility.
    
    Args:
        heygen_urls (Dict): HeyGen video URLs
        movie_covers (List): Movie poster URLs
        movie_clips (List): Movie clip URLs
        scroll_video_url (str): Scroll video URL
        
    Returns:
        Dict[str, Any]: Validation results
    """
    validation = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'heygen_status': {},
        'covers_status': [],
        'clips_status': [],
        'scroll_status': None
    }
    
    try:
        # Validate HeyGen URLs
        logger.debug("🔍 Validating HeyGen URLs...")
        for key, url in heygen_urls.items():
            status = check_url_accessibility(url)
            validation['heygen_status'][key] = status
            
            if not status['accessible']:
                validation['is_valid'] = False
                validation['errors'].append(f"HeyGen {key}: {status['error']}")
        
        # Validate movie covers
        if movie_covers:
            logger.debug("🔍 Validating movie cover URLs...")
            for i, url in enumerate(movie_covers):
                status = check_url_accessibility(url)
                validation['covers_status'].append(status)
                
                if not status['accessible']:
                    validation['warnings'].append(f"Cover {i+1}: {status['error']}")
        
        # Validate movie clips
        if movie_clips:
            logger.debug("🔍 Validating movie clip URLs...")
            for i, url in enumerate(movie_clips):
                status = check_url_accessibility(url)
                validation['clips_status'].append(status)
                
                if not status['accessible']:
                    validation['warnings'].append(f"Clip {i+1}: {status['error']}")
        
        # Validate scroll video
        if scroll_video_url:
            logger.debug("🔍 Validating scroll video URL...")
            status = check_url_accessibility(scroll_video_url)
            validation['scroll_status'] = status
            
            if not status['accessible']:
                validation['warnings'].append(f"Scroll video: {status['error']}")
        
        # Summary
        total_errors = len(validation['errors'])
        total_warnings = len(validation['warnings'])
        
        if total_errors > 0:
            logger.error(f"❌ URL validation failed: {total_errors} errors")
        elif total_warnings > 0:
            logger.warning(f"⚠️ URL validation warnings: {total_warnings} warnings")
        else:
            logger.info("✅ All URLs validated successfully")
        
        return validation
        
    except Exception as e:
        logger.error(f"❌ Error validating URLs: {str(e)}")
        validation['is_valid'] = False
        validation['errors'].append(f"Validation error: {str(e)}")
        return validation


def check_url_accessibility(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Check if a URL is accessible.
    
    Args:
        url (str): URL to check
        timeout (int): Request timeout in seconds
        
    Returns:
        Dict[str, Any]: Accessibility status
    """
    status = {
        'url': url,
        'accessible': False,
        'status_code': None,
        'content_type': None,
        'content_length': None,
        'error': None
    }
    
    try:
        if not is_valid_url(url):
            status['error'] = 'Invalid URL format'
            return status
        
        # Make HEAD request to check accessibility
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        
        status['status_code'] = response.status_code
        status['content_type'] = response.headers.get('content-type', '')
        status['content_length'] = response.headers.get('content-length')
        
        if response.status_code == 200:
            status['accessible'] = True
        else:
            status['error'] = f'HTTP {response.status_code}'
        
        return status
        
    except requests.RequestException as e:
        status['error'] = f'Request failed: {str(e)}'
        return status
    except Exception as e:
        status['error'] = f'Unexpected error: {str(e)}'
        return status

# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def extract_video_metadata(video_url: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Extract comprehensive metadata from video URL.
    
    Args:
        video_url (str): Video URL to analyze
        timeout (int): Analysis timeout in seconds
        
    Returns:
        Dict[str, Any]: Video metadata or None if failed
    """
    try:
        if not is_valid_url(video_url):
            return None
        
        # Use FFprobe to get comprehensive video info
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            video_url
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        if result.returncode == 0:
            probe_data = json.loads(result.stdout)
            
            # Extract format info
            format_info = probe_data.get('format', {})
            streams = probe_data.get('streams', [])
            
            # Find video and audio streams
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            
            metadata = {
                'url': video_url,
                'duration': float(format_info.get('duration', 0)),
                'size_bytes': int(format_info.get('size', 0)),
                'format_name': format_info.get('format_name', 'unknown'),
                'bit_rate': int(format_info.get('bit_rate', 0))
            }
            
            # Video stream info
            if video_stream:
                metadata.update({
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'video_codec': video_stream.get('codec_name', 'unknown'),
                    'pixel_format': video_stream.get('pix_fmt', 'unknown'),
                    'frame_rate': _parse_frame_rate(video_stream.get('r_frame_rate', '0/1'))
                })
            
            # Audio stream info
            if audio_stream:
                metadata.update({
                    'audio_codec': audio_stream.get('codec_name', 'unknown'),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0))
                })
            
            return metadata
        
        return None
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Metadata extraction timeout: {video_url}")
        return None
    except Exception as e:
        logger.debug(f"Error extracting metadata from {video_url}: {str(e)}")
        return None


def analyze_video_quality(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze video quality based on metadata.
    
    Args:
        metadata (Dict): Video metadata
        
    Returns:
        Dict[str, Any]: Quality analysis results
    """
    quality = {
        'resolution_quality': 'unknown',
        'aspect_ratio': 'unknown',
        'bitrate_quality': 'unknown',
        'overall_quality': 'unknown',
        'recommendations': []
    }
    
    try:
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)
        bit_rate = metadata.get('bit_rate', 0)
        duration = metadata.get('duration', 0)
        
        # Resolution quality
        if width >= 1920 and height >= 1080:
            quality['resolution_quality'] = 'high'
        elif width >= 1280 and height >= 720:
            quality['resolution_quality'] = 'medium'
        else:
            quality['resolution_quality'] = 'low'
        
        # Aspect ratio
        if width > 0 and height > 0:
            ratio = width / height
            if 0.5 < ratio < 0.6:  # Portrait (9:16)
                quality['aspect_ratio'] = 'portrait'
            elif 1.7 < ratio < 1.8:  # Landscape (16:9)
                quality['aspect_ratio'] = 'landscape'
            elif 0.9 < ratio < 1.1:  # Square
                quality['aspect_ratio'] = 'square'
            else:
                quality['aspect_ratio'] = 'custom'
        
        # Bitrate quality (very rough estimates)
        if bit_rate > 0 and duration > 0:
            bitrate_mbps = bit_rate / 1000000  # Convert to Mbps
            if bitrate_mbps > 5:
                quality['bitrate_quality'] = 'high'
            elif bitrate_mbps > 2:
                quality['bitrate_quality'] = 'medium'
            else:
                quality['bitrate_quality'] = 'low'
        
        # Overall quality
        quality_scores = []
        if quality['resolution_quality'] == 'high':
            quality_scores.append(3)
        elif quality['resolution_quality'] == 'medium':
            quality_scores.append(2)
        else:
            quality_scores.append(1)
        
        if quality['bitrate_quality'] == 'high':
            quality_scores.append(3)
        elif quality['bitrate_quality'] == 'medium':
            quality_scores.append(2)
        else:
            quality_scores.append(1)
        
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 1
        
        if avg_score >= 2.5:
            quality['overall_quality'] = 'high'
        elif avg_score >= 1.5:
            quality['overall_quality'] = 'medium'
        else:
            quality['overall_quality'] = 'low'
        
        # Recommendations
        if quality['resolution_quality'] == 'low':
            quality['recommendations'].append('Consider higher resolution source')
        
        if quality['aspect_ratio'] not in ['portrait', 'landscape']:
            quality['recommendations'].append('Non-standard aspect ratio detected')
        
        if quality['bitrate_quality'] == 'low':
            quality['recommendations'].append('Low bitrate may affect quality')
        
        return quality
        
    except Exception as e:
        logger.error(f"Error analyzing video quality: {str(e)}")
        return quality

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _parse_frame_rate(frame_rate_str: str) -> float:
    """Parse frame rate from FFprobe format (e.g., '30/1')."""
    try:
        if '/' in frame_rate_str:
            numerator, denominator = frame_rate_str.split('/')
            return float(numerator) / float(denominator)
        else:
            return float(frame_rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def batch_analyze_videos(video_urls: List[str], 
                        max_concurrent: int = 3) -> Dict[str, Dict[str, Any]]:
    """
    Analyze multiple videos in batch with concurrency control.
    
    Args:
        video_urls (List): List of video URLs to analyze
        max_concurrent (int): Maximum concurrent analyses
        
    Returns:
        Dict[str, Dict]: Analysis results for each URL
    """
    results = {}
    
    try:
        logger.info(f"📊 Batch analyzing {len(video_urls)} videos")
        
        # For now, process sequentially (can be optimized with threading)
        for i, url in enumerate(video_urls):
            logger.info(f"🔍 Analyzing video {i+1}/{len(video_urls)}")
            
            metadata = extract_video_metadata(url)
            if metadata:
                quality = analyze_video_quality(metadata)
                results[url] = {
                    'metadata': metadata,
                    'quality': quality
                }
            else:
                results[url] = {
                    'error': 'Failed to extract metadata'
                }
        
        logger.info(f"✅ Batch analysis complete: {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in batch video analysis: {str(e)}")
        return results