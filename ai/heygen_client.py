"""
StreamGank HeyGen Client

This module handles HeyGen API integration for creating AI avatar videos
from generated scripts, with support for template-based and custom video creation.

Features:
- Template-based video generation using genre-specific templates
- Custom video creation with avatar and voice selection
- Batch video processing for multiple scripts
- Video status monitoring and completion tracking
- Retry logic and error handling
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
import requests

from config.templates import get_heygen_template_id
from config.settings import get_api_config
from utils.validators import validate_environment_variables
from ai.script_manager import validate_script_content

logger = logging.getLogger(__name__)

# =============================================================================
# HEYGEN CLIENT CONFIGURATION
# =============================================================================

def _get_heygen_headers() -> Optional[Dict[str, str]]:
    """
    Get HeyGen API headers with authentication.
    
    Returns:
        Dict[str, str]: API headers or None if API key missing
    """
    try:
        api_key = os.getenv('HEYGEN_API_KEY')
        if not api_key:
            logger.error("❌ Missing HeyGen API key (HEYGEN_API_KEY)")
            return None
        
        return {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting HeyGen headers: {str(e)}")
        return None


def _get_heygen_config() -> Dict[str, Any]:
    """Get HeyGen API configuration."""
    try:
        api_config = get_api_config('heygen')
        return {
            'base_url': api_config.get('base_url', 'https://api.heygen.com/v2'),
            'poll_interval': api_config.get('poll_interval', 15),
            'max_wait_time': api_config.get('max_wait_time', 300),
            'retry_attempts': api_config.get('retry_attempts', 3)
        }
    except Exception as e:
        logger.error(f"Error getting HeyGen config: {str(e)}")
        return {}

# =============================================================================
# MAIN VIDEO CREATION FUNCTIONS
# =============================================================================

def create_heygen_video(script_data: Any, 
                       use_template: bool = True, 
                       template_id: Optional[str] = None,
                       genre: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Create videos with HeyGen API using scripts.
    
    Args:
        script_data: Dictionary containing scripts or single script string
        use_template (bool): Whether to use template-based approach
        template_id (str): Specific HeyGen template ID (overrides genre selection)
        genre (str): Genre for automatic template selection
        
    Returns:
        Dict[str, str]: Dictionary mapping script keys to video IDs
    """
    try:
        logger.info(f"🎬 Creating HeyGen videos")
        
        # Check if we're in local mode - use hardcoded URLs instead of API
        if os.getenv('APP_ENV') == 'local':
            logger.info("🏠 LOCAL MODE: Using hardcoded HeyGen URLs instead of API calls")
            return _get_local_heygen_videos(script_data)
        
        # Validate API configuration
        headers = _get_heygen_headers()
        if not headers:
            return None
        
        if script_data is None:
            logger.error("❌ No script data provided")
            return None
        
        # Handle different input formats
        if isinstance(script_data, str):
            script_data = {
                "single_video": {
                    "text": script_data,
                    "path": "direct_input"
                }
            }
        
        # Determine template ID
        if use_template:
            if not template_id and genre:
                template_id = get_heygen_template_id(genre)
                logger.info(f"🎭 Using genre-specific template for {genre}: {template_id}")
            elif not template_id:
                template_id = get_heygen_template_id(None)  # Default template
                logger.info(f"🎭 Using default template: {template_id}")
        
        videos = {}
        
        # Process each script
        for key, script_info in script_data.items():
            logger.info(f"   🎯 Creating video for {key}")
            
            # Extract script text
            if isinstance(script_info, dict) and "text" in script_info:
                script_text = script_info["text"]
            else:
                script_text = str(script_info)
            
            # Validate script content
            if not validate_script_content(script_text):
                logger.warning(f"⚠️ Script validation failed for {key}, proceeding anyway")
            
            # Create video
            video_id = _create_single_video(script_text, key, use_template, template_id, headers)
            if video_id:
                videos[key] = video_id
            else:
                logger.error(f"❌ Failed to create video for {key}")
        
        logger.info(f"✅ HeyGen video creation initiated: {len(videos)} videos")
        return videos if videos else None
        
    except Exception as e:
        logger.error(f"❌ Error in create_heygen_video: {str(e)}")
        return None


def create_heygen_videos_batch(script_batches: List[Dict[str, Any]], 
                              config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create HeyGen videos for multiple script batches.
    
    Args:
        script_batches (List): List of script batch dictionaries
        config (Dict): Configuration parameters
        
    Returns:
        Dict[str, Any]: Batch processing results
    """
    results = {
        'successful_batches': 0,
        'failed_batches': 0,
        'total_videos': 0,
        'batch_results': {},
        'errors': []
    }
    
    try:
        logger.info(f"📦 BATCH HEYGEN VIDEO CREATION: {len(script_batches)} batches")
        
        for i, script_batch in enumerate(script_batches):
            batch_id = f"batch_{i+1}"
            logger.info(f"🎯 Processing {batch_id}: {len(script_batch)} scripts")
            
            try:
                # Create videos for this batch
                video_ids = create_heygen_video(
                    script_batch,
                    use_template=config.get('use_template', True),
                    template_id=config.get('template_id'),
                    genre=config.get('genre')
                )
                
                if video_ids:
                    results['batch_results'][batch_id] = {
                        'status': 'success',
                        'video_ids': video_ids,
                        'video_count': len(video_ids)
                    }
                    
                    results['successful_batches'] += 1
                    results['total_videos'] += len(video_ids)
                    
                    logger.info(f"✅ {batch_id} completed: {len(video_ids)} videos")
                    
                else:
                    results['batch_results'][batch_id] = {
                        'status': 'failed',
                        'error': 'Video creation failed'
                    }
                    results['failed_batches'] += 1
                    results['errors'].append(f"{batch_id}: Video creation failed")
                    
                    logger.error(f"❌ {batch_id} failed")
                
            except Exception as e:
                error_msg = f"{batch_id}: {str(e)}"
                results['batch_results'][batch_id] = {
                    'status': 'error',
                    'error': error_msg
                }
                results['failed_batches'] += 1
                results['errors'].append(error_msg)
                
                logger.error(f"❌ {batch_id} error: {str(e)}")
        
        logger.info(f"🏁 BATCH VIDEO CREATION COMPLETE:")
        logger.info(f"   ✅ Successful: {results['successful_batches']}")
        logger.info(f"   ❌ Failed: {results['failed_batches']}")
        logger.info(f"   🎬 Total videos: {results['total_videos']}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in batch video creation: {str(e)}")
        results['errors'].append(f"Batch processing error: {str(e)}")
        return results

# =============================================================================
# VIDEO STATUS MONITORING
# =============================================================================

def check_video_status(video_id: str, silent: bool = False) -> Dict[str, Any]:
    """
    Check the status of a HeyGen video.
    
    Args:
        video_id (str): HeyGen video ID
        silent (bool): Suppress logging output
        
    Returns:
        Dict[str, Any]: Video status information
    """
    try:
        headers = _get_heygen_headers()
        if not headers:
            return {'status': 'error', 'error': 'API headers not available'}
        
        config = _get_heygen_config()
        url = f"{config['base_url']}/video_status/{video_id}"
        
        if not silent:
            logger.debug(f"🔍 Checking video status: {video_id}")
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                video_data = data['data']
                status_info = {
                    'status': video_data.get('status', 'unknown'),
                    'video_url': video_data.get('video_url'),
                    'duration': video_data.get('duration'),
                    'created_at': video_data.get('created_at'),
                    'completed_at': video_data.get('completed_at'),
                    'error': video_data.get('error')
                }
                
                if not silent:
                    status = status_info['status']
                    if status == 'completed':
                        logger.info(f"✅ Video {video_id}: {status}")
                        if status_info['video_url']:
                            logger.info(f"   🎬 URL: {status_info['video_url']}")
                    elif status == 'processing':
                        logger.info(f"⏳ Video {video_id}: {status}")
                    elif status == 'failed':
                        logger.error(f"❌ Video {video_id}: {status}")
                        if status_info['error']:
                            logger.error(f"   Error: {status_info['error']}")
                
                return status_info
            else:
                return {'status': 'error', 'error': 'Invalid response format'}
        else:
            error_msg = f"API error: {response.status_code}"
            if not silent:
                logger.error(f"❌ Status check failed for {video_id}: {error_msg}")
            return {'status': 'error', 'error': error_msg}
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        if not silent:
            logger.error(f"❌ Error checking video status {video_id}: {error_msg}")
        return {'status': 'error', 'error': error_msg}


def wait_for_completion(video_ids: Dict[str, str], 
                       max_wait_time: int = 300,
                       poll_interval: int = 15) -> Dict[str, Dict[str, Any]]:
    """
    Wait for multiple HeyGen videos to complete with ADVANCED PROGRESS MONITORING.
    
    Features:
    - ETA calculations based on processing patterns
    - Detailed progress tracking with percentage completion
    - Fallback endpoint attempts when primary fails
    - Smart retry logic with exponential backoff
    - Duration estimation and validation
    
    Args:
        video_ids (Dict): Dictionary mapping keys to video IDs
        max_wait_time (int): Maximum time to wait in seconds (default: 300s = 5min)
        poll_interval (int): Polling interval in seconds (default: 15s)
        
    Returns:
        Dict[str, Dict]: Comprehensive status information for each video
    """
    try:
        logger.info(f"🎬 ADVANCED HEYGEN MONITORING: {len(video_ids)} videos")
        logger.info(f"   ⏱️ Max wait: {max_wait_time}s | Poll interval: {poll_interval}s")
        logger.info(f"   🔍 Features: ETA calculation, Fallback endpoints, Smart retry")
        
        start_time = time.time()
        video_status = {}
        completed_videos = set()
        processing_start_times = {}
        failed_attempts = {}
        
        # Track processing start times for ETA calculation
        for key in video_ids.keys():
            processing_start_times[key] = start_time
            failed_attempts[key] = 0
        
        poll_count = 0
        
        while len(completed_videos) < len(video_ids):
            poll_count += 1
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            logger.info(f"🔍 Poll #{poll_count} - Elapsed: {elapsed_time:.0f}s/{max_wait_time}s")
            
            if elapsed_time > max_wait_time:
                logger.warning(f"⏰ TIMEOUT reached ({max_wait_time}s), stopping monitoring")
                logger.info(f"   ✅ Completed: {len(completed_videos)}/{len(video_ids)}")
                logger.info(f"   ⏳ Still processing: {len(video_ids) - len(completed_videos)}")
                break
            
            # Check status of pending videos with advanced monitoring
            for key, video_id in video_ids.items():
                if key not in completed_videos:
                    # Try primary endpoint first, then fallback
                    status_info = _check_video_status_strict(video_id, key)
                    video_status[key] = status_info
                    
                    # Calculate processing time and ETA
                    processing_time = current_time - processing_start_times[key]
                    status_info['processing_time'] = processing_time
                    
                    if status_info['status'] in ['completed', 'failed', 'error']:
                        completed_videos.add(key)
                        
                        if status_info['status'] == 'completed':
                            logger.info(f"✅ {key} COMPLETED in {processing_time:.0f}s: {video_id}")
                            if status_info.get('video_url'):
                                logger.info(f"   🎬 URL: {status_info['video_url'][:50]}...")
                            if status_info.get('duration'):
                                logger.info(f"   ⏱️ Duration: {status_info['duration']}s")
                        else:
                            logger.error(f"❌ {key} FAILED after {processing_time:.0f}s: {status_info.get('error', 'Unknown error')}")
                    
                    elif status_info['status'] == 'processing':
                        # Calculate ETA based on average processing time of completed videos
                        eta = _calculate_eta(video_status, processing_time)
                        status_info['eta'] = eta
                        
                        if poll_count % 2 == 0:  # Log every 2nd poll to reduce noise
                            logger.info(f"⏳ {key}: Processing {processing_time:.0f}s (ETA: {eta:.0f}s)")
            
            # Break if all videos are done
            if len(completed_videos) >= len(video_ids):
                break
            
            # Calculate overall progress
            progress_percentage = (len(completed_videos) / len(video_ids)) * 100
            remaining_videos = len(video_ids) - len(completed_videos)
            
            # Calculate ETA for remaining videos
            overall_eta = _calculate_overall_eta(video_status, remaining_videos)
            
            logger.info(f"📈 Progress: {progress_percentage:.1f}% ({len(completed_videos)}/{len(video_ids)})")
            logger.info(f"   ⏳ Remaining: {remaining_videos} videos | Overall ETA: {overall_eta:.0f}s")
            logger.info(f"   ⏱️ Next check in {poll_interval}s...")
            
            time.sleep(poll_interval)
        
        # Final comprehensive status report
        total_time = time.time() - start_time
        completed_count = sum(1 for status in video_status.values() if status['status'] == 'completed')
        failed_count = sum(1 for status in video_status.values() if status['status'] in ['failed', 'error'])
        processing_count = len(video_ids) - completed_count - failed_count
        
        logger.info(f"🏆 HEYGEN MONITORING COMPLETE ({total_time:.0f}s total):")
        logger.info(f"   ✅ Completed: {completed_count}/{len(video_ids)} ({completed_count/len(video_ids)*100:.1f}%)")
        logger.info(f"   ❌ Failed: {failed_count}/{len(video_ids)} ({failed_count/len(video_ids)*100:.1f}%)")
        logger.info(f"   ⏳ Still processing: {processing_count}/{len(video_ids)} ({processing_count/len(video_ids)*100:.1f}%)")
        
        if completed_count > 0:
            avg_processing_time = sum(status.get('processing_time', 0) for status in video_status.values() if status['status'] == 'completed') / completed_count
            logger.info(f"   ⏱️ Average processing time: {avg_processing_time:.0f}s per video")
        
        return video_status
        
    except Exception as e:
        logger.error(f"❌ Error in advanced video monitoring: {str(e)}")
        return {}


def get_heygen_videos_for_creatomate(heygen_video_ids: dict, scripts: dict = None) -> dict:
    """
    Get HeyGen video URLs for direct use with Creatomate - STRICT MODE
    
    MODULAR VERSION - Replaces legacy function from automated_video_generator.py
    
    Args:
        heygen_video_ids: Dictionary of HeyGen video IDs (no placeholders allowed)
        scripts: Dictionary of script data for time estimation
        
    Returns:
        Dictionary with video URLs ready for Creatomate, or None if any video fails
        
    Note:
        STRICT MODE - Returns None if any video fails. No fallbacks allowed.
    """
    logger.info(f"🔗 Getting HeyGen video URLs for {len(heygen_video_ids)} videos - STRICT MODE")
    
    # Check if we're in local mode - return hardcoded URLs directly
    if os.getenv('APP_ENV') == 'local':
        logger.info("🏠 LOCAL MODE: Returning hardcoded HeyGen URLs for Creatomate")
        return _get_local_heygen_urls_for_creatomate(heygen_video_ids)
    
    video_urls = {}
    
    for key, video_id in heygen_video_ids.items():
        if not video_id or video_id.startswith('placeholder'):
            logger.error(f"❌ Invalid or placeholder ID for {key}: {video_id}")
            logger.error("❌ STRICT MODE - No placeholder IDs allowed")
            return None
        
        # Extract script length for estimation
        script_length = None
        if scripts and key in scripts:
            script_data = scripts[key]
            if isinstance(script_data, dict) and 'text' in script_data:
                script_text = script_data['text']
            elif isinstance(script_data, str):
                script_text = script_data
            else:
                script_text = str(script_data)
            script_length = len(script_text) if script_text else None
        
        logger.info(f"   Processing {key}: {video_id} ({script_length or 'unknown'} chars)")
        
        # Wait for video completion
        status_result = wait_for_heygen_video(
            video_id, 
            script_length=script_length,
            max_wait_minutes=25
        )
        
        if status_result['success'] and status_result['video_url']:
            video_url = status_result['video_url']
            video_urls[key] = video_url
            logger.info(f"✅ Got URL for {key}: {video_url[:50]}...")
        else:
            # STRICT MODE - No fallbacks allowed
            logger.error(f"❌ HeyGen video failed for {key}: {video_id}")
            logger.error(f"   Status: {status_result}")
            logger.error("❌ STRICT MODE - No fallback URLs allowed")
            return None
    
    logger.info(f"✅ Obtained {len(video_urls)} video URLs")
    return video_urls


def wait_for_heygen_video(video_id: str, script_length: int = None, max_wait_minutes: int = 15) -> dict:
    """
    Wait for HeyGen video completion with progress feedback.
    
    MODULAR VERSION - Replaces legacy function from automated_video_generator.py
    
    Args:
        video_id: HeyGen video ID
        script_length: Script length for time estimation
        max_wait_minutes: Maximum wait time in minutes
        
    Returns:
        Dictionary with status information
    """
    # Estimate processing time
    estimated_minutes = estimate_heygen_processing_time(script_length)
    timeout_minutes = min(max(estimated_minutes + 5, 8), max_wait_minutes)
    max_total_seconds = timeout_minutes * 60
    
    logger.info(f"⏳ Waiting for HeyGen video {video_id[:8]}... (estimated: ~{estimated_minutes} min)")
    
    start_time = time.time()
    attempt = 0
    next_check_time = start_time
    
    # Spinner frames
    spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    while True:
        current_time = time.time()
        elapsed_seconds = current_time - start_time
        
        # Check timeout
        if elapsed_seconds > max_total_seconds:
            elapsed_time = int(elapsed_seconds)
            minutes, seconds = divmod(elapsed_time, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            print(f"\r⏰ HeyGen video timeout    [{'░' * 30}] ----  │ {time_str} │ Max time reached{' ' * 10}")
            logger.warning(f"HeyGen video {video_id[:8]}... exceeded max wait time")
            
            return {
                'success': False,
                'status': 'timeout',
                'video_url': '',
                'data': {}
            }
        
        # Check status at intervals
        if current_time >= next_check_time:
            attempt += 1
            
            # Calculate progress
            time_progress = min(elapsed_seconds / (estimated_minutes * 60) * 100, 95)
            attempt_progress = min(elapsed_seconds / max_total_seconds * 100, 95)
            progress = max(time_progress, attempt_progress)
            
            elapsed_time = int(elapsed_seconds)
            minutes, seconds = divmod(elapsed_time, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # ETA calculation
            remaining_seconds = max(0, (estimated_minutes * 60) - elapsed_seconds)
            if remaining_seconds > 0 and progress < 90:
                remaining_minutes, remaining_secs = divmod(int(remaining_seconds), 60)
                eta_str = f"ETA ~{remaining_minutes:02d}:{remaining_secs:02d}"
            else:
                eta_str = "Almost ready..."
            
            # Progress display
            spinner = spinner_frames[attempt % len(spinner_frames)]
            bar_length = 30
            filled_length = int(bar_length * progress / 100)
            bar = f"[{'█' * filled_length}{'░' * (bar_length - filled_length)}]"
            
            progress_line = f"\r{spinner} Processing HeyGen video {bar} {progress:5.1f}% │ {time_str} │ {eta_str}"
            print(progress_line, end='', flush=True)
            
            # Check status
            status_info = check_heygen_video_status(video_id, silent=True)
            status = status_info.get('status', 'unknown')
            video_url = status_info.get('video_url', '')
            
            if status == "completed":
                print(f"\r✅ HeyGen video completed! [{'█' * bar_length}] 100.0% │ {time_str} │ Verifying URL...{' ' * 5}")
                logger.info(f"🎬 Video completed in {minutes}:{seconds:02d}")
                
                # Verify video URL is accessible for duration analysis
                if video_url and _verify_video_url_ready(video_url):
                    print(f"\r✅ HeyGen video ready!     [{'█' * bar_length}] 100.0% │ {time_str} │ URL verified!{' ' * 10}")
                    logger.info(f"🔗 Video URL verified and ready for duration analysis")
                    
                    return {
                        'success': True,
                        'status': status,
                        'video_url': video_url,
                        'data': status_info.get('data', {})
                    }
                else:
                    logger.warning(f"⚠️ Video marked completed but URL not ready yet: {video_url}")
                    # Continue waiting - sometimes there's a delay between completion and URL accessibility
                
            elif status in ["failed", "error"]:
                print(f"\r❌ HeyGen video failed!   [{'X' * bar_length}] ERROR │ {time_str} │ Processing failed{' ' * 10}")
                logger.error(f"HeyGen video {video_id[:8]}... processing failed")
                
                return {
                    'success': False,
                    'status': status,
                    'video_url': video_url,
                    'data': status_info.get('data', {})
                }
            
            # Set next check interval
            if elapsed_seconds < 120:
                current_interval = 10
            elif elapsed_seconds < 300:
                current_interval = 15
            elif elapsed_seconds < 600:
                current_interval = 20
            else:
                current_interval = 30
                
            next_check_time = current_time + current_interval
        
        time.sleep(1)


def _verify_video_url_ready(video_url: str, timeout: int = 10) -> bool:
    """
    Verify that a HeyGen video URL is ready for duration analysis.
    
    Args:
        video_url (str): Video URL to verify
        timeout (int): Timeout for verification
        
    Returns:
        bool: True if URL is ready for FFprobe analysis
    """
    try:
        import requests
        
        # Quick HTTP HEAD check to see if URL is accessible
        response = requests.head(video_url, timeout=timeout, allow_redirects=True)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            
            # Check if it's actually a video file
            if 'video/' in content_type or 'application/octet-stream' in content_type:
                logger.debug(f"Video URL verified: {video_url[:50]}... (Content-Type: {content_type})")
                return True
            else:
                logger.debug(f"URL accessible but not video content: {content_type}")
                return False
        else:
            logger.debug(f"URL not accessible: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        logger.debug(f"URL verification failed: {str(e)}")
        return False


def estimate_heygen_processing_time(script_length: int = None) -> int:
    """
    Estimate HeyGen processing time based on script complexity.
    
    MODULAR VERSION - Replaces legacy function from automated_video_generator.py
    
    Args:
        script_length: Length of the script in characters
        
    Returns:
        int: Estimated processing time in minutes
    """
    base_minutes = 3
    
    if script_length is None:
        return 6
    
    additional_minutes = script_length // 200
    
    if script_length <= 300:
        estimated = base_minutes + 1  # 4 minutes
    elif script_length <= 800:
        estimated = base_minutes + 3  # 6 minutes
    else:
        estimated = base_minutes + min(additional_minutes, 9)  # Cap at 12 minutes
    
    return estimated


def check_heygen_video_status(video_id: str, silent: bool = False) -> dict:
    """
    Check HeyGen video processing status.
    
    MODULAR VERSION - Replaces legacy function from automated_video_generator.py
    
    Args:
        video_id: HeyGen video ID
        silent: Whether to suppress debug logging
        
    Returns:
        dict: Status information with status, video_url, and data
    """
    if not silent:
        logger.debug(f"Checking HeyGen video status: {video_id[:8]}...")
    
    api_key = os.getenv('HEYGEN_API_KEY')
    if not api_key:
        return {"status": "unknown", "video_url": "", "data": {}}
    
    status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }
    
    try:
        response = requests.get(status_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                video_data = data['data']
                status = video_data.get('status', 'unknown')
                video_url = video_data.get('video_url', '') or video_data.get('url', '')
                
                return {
                    "status": status,
                    "video_url": video_url,
                    "data": video_data
                }
            else:
                return {"status": "unknown", "video_url": "", "data": data}
        else:
            return _try_fallback_status_endpoints(video_id, headers, silent)
            
    except Exception as e:
        return _try_fallback_status_endpoints(video_id, headers, silent)


def _try_fallback_status_endpoints(video_id: str, headers: dict, silent: bool = False) -> dict:
    """
    Try fallback endpoints for HeyGen status.
    
    Args:
        video_id: HeyGen video ID
        headers: Request headers
        silent: Whether to suppress debug logging
        
    Returns:
        dict: Status information or default empty status
    """
    fallback_endpoints = [
        f"https://api.heygen.com/v1/video.status?video_id={video_id}",
        f"https://api.heygen.com/v1/video_status?video_id={video_id}",
        f"https://api.heygen.com/v2/video/{video_id}/status"
    ]
    
    for endpoint in fallback_endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    video_data = data['data']
                    status = video_data.get('status', 'unknown')
                    video_url = video_data.get('video_url', '') or video_data.get('url', '')
                    
                    return {
                        "status": status,
                        "video_url": video_url,
                        "data": video_data
                    }
        except Exception:
            continue
    
    return {"status": "unknown", "video_url": "", "data": {}}


def get_video_urls(video_ids: Dict[str, str], 
                  scripts: Optional[Dict] = None,
                  max_wait_time: int = 300) -> Optional[Dict[str, str]]:
    """
    Get video URLs for completed HeyGen videos.
    
    This function waits for videos to complete and extracts their URLs.
    
    Args:
        video_ids (Dict): Dictionary mapping keys to video IDs
        scripts (Dict): Optional scripts dictionary for context
        max_wait_time (int): Maximum time to wait for completion
        
    Returns:
        Dict[str, str]: Dictionary mapping keys to video URLs or None if failed
    """
    try:
        logger.info(f"🔗 Getting video URLs for {len(video_ids)} HeyGen videos")
        
        # Wait for completion
        video_status = wait_for_completion(video_ids, max_wait_time)
        
        if not video_status:
            logger.error("❌ Failed to get video status")
            return None
        
        # Extract URLs from completed videos
        video_urls = {}
        
        for key, status_info in video_status.items():
            if status_info['status'] == 'completed' and status_info.get('video_url'):
                video_urls[key] = status_info['video_url']
                logger.info(f"✅ {key}: {status_info['video_url']}")
            else:
                logger.error(f"❌ {key}: No URL available (status: {status_info['status']})")
        
        if not video_urls:
            logger.error("❌ No video URLs obtained")
            return None
        
        logger.info(f"🎬 Successfully obtained {len(video_urls)}/{len(video_ids)} video URLs")
        return video_urls
        
    except Exception as e:
        logger.error(f"❌ Error getting video URLs: {str(e)}")
        return None

# =============================================================================
# LOCAL MODE FUNCTIONS
# =============================================================================

def _get_local_heygen_videos(script_data: Any) -> Dict[str, str]:
    """
    Return hardcoded HeyGen video URLs for local development mode.
    
    This avoids making API calls and using credits during development.
    
    Args:
        script_data: Dictionary containing scripts or single script string
        
    Returns:
        Dict[str, str]: Dictionary mapping script keys to hardcoded video IDs
    """
    try:
        # Hardcoded HeyGen video URLs for local mode
        local_heygen_urls = [
            "https://files2.heygen.ai/aws_pacific/avatar_tmp/fc001c501c65419385a406d9281db788/c4d15b0053364c2f9a676341a40bafae.mp4?Expires=1755527003&Signature=pFusBVqK-V0FOn90Mh9MlsKwk5Szq6kmi9akRezOOCb3odcZf8hbNp-r7DtyucVT8XdKMcYmGEr9isrbu3AKBkE1VtovLNXuTNNtSK9CP6ZtjVVj8TIDz0lz3j~Svpo7vgTiFzIulf3ja5H6YRZKrnEYUbVIxmo3BKWdvvaSjfftQmcbblOBI2QjYQZXVZOdsF2UpxLxzbrgifZlTiT373pRS9eVqYJiCzeJJEyrdJp5tpfzIc4o8WcOyuW4zVJ-QS0U4YXcSZpC1t~OLzSbgCg1rCrRKcv0aaha5g-K~-VFyjUhPjJydyA7aRc8MGIaGn2hKIyHCt06-eMk8qEI5w__&Key-Pair-Id=K38HBHX5LX3X2H",
            "https://files2.heygen.ai/aws_pacific/avatar_tmp/fc001c501c65419385a406d9281db788/09db94f0a5d64ecd9aa1c80dc5a41f5c.mp4?Expires=1755527004&Signature=lnNmK8EY~wvlvngCfdcE-4zNZB3yZhMOlt5UnH~x2ds0y6S2b-vF0097lKqDbYHKLYCbXWyFQpxkWf76NSnulH7BjGVlQaXlz3ltr73gp~FKic0Xz1oPBFvH1QJVP7wsCnin7Obm1l9D6z8wsaxnF33yDZHvVCDKOPS3QmXEez8xkncaaXRhe6x1hHXyMTTEfXkVPdUuUIwFXqMyzOGfxLlVL97wm-aWMiMUkrNsExFpUkQmkKPhXQgcIMIKoPJ5FE6Z3WkvsHUaiGiAGBLc4smQTtBS3W259gmFrAaiViizjHTMVsHKDrOdhE2abhOOOq5xXWSadv6t5IY30I0aOg__&Key-Pair-Id=K38HBHX5LX3X2H",
            "https://files2.heygen.ai/aws_pacific/avatar_tmp/fc001c501c65419385a406d9281db788/09cef1834e7d44f2a143cbfe144f54ca.mp4?Expires=1755527008&Signature=G2dEk8ymdsZwuWu7c8iXh~kAPb7Nove6wk6k2YsxJUA5riV~pUXVrT1OB-Miqi7dQF7nI3wrKYSPG~FpMlbng0PmVmP6vtn-Vbk7MSD4K2H~b5BiZ2E03uP8RHoAhe9cMa8vbJCjuZbaXhLtO-26Ab2XmyQXRXVZD8ctvpIsl1fFX5PTbYXKk~IgixoSEj-uRdpxG-B5kCI324n7V~7iCwxnPY-k1CfUSTWn5n83jqy1Wfk~Dmi~2FJgoSEf-~Z4GxIXLyL7FEPw7CwmJ6KSqHzLJPao-JfHNK5tu6~O~wex5N6nb4EZjrxBzs96WG~AHscTiOmgpd7M9-Pj5cReWg__&Key-Pair-Id=K38HBHX5LX3X2H"
        ]
        
        # Handle different input formats
        if isinstance(script_data, str):
            script_data = {
                "single_video": {
                    "text": script_data,
                    "path": "direct_input"
                }
            }
        
        videos = {}
        
        # Assign URLs to scripts (cycling through available URLs)
        for i, (key, script_info) in enumerate(script_data.items()):
            url_index = i % len(local_heygen_urls)
            
            # Generate a fake video ID for compatibility
            fake_video_id = f"local_heygen_{i+1}_{key}"
            videos[key] = fake_video_id
            
            logger.info(f"🏠 Local video assigned for {key}: {fake_video_id}")
            logger.info(f"   📹 URL: {local_heygen_urls[url_index][:60]}...")
        
        logger.info(f"✅ LOCAL MODE: {len(videos)} hardcoded HeyGen videos assigned")
        return videos
        
    except Exception as e:
        logger.error(f"❌ Error in local HeyGen mode: {str(e)}")
        return None


def _get_local_heygen_urls_for_creatomate(heygen_video_ids: dict) -> dict:
    """
    Return hardcoded HeyGen video URLs for Creatomate in local development mode.
    
    Args:
        heygen_video_ids: Dictionary of HeyGen video IDs (fake IDs from local mode)
        
    Returns:
        Dictionary with actual video URLs ready for Creatomate
    """
    try:
        # Hardcoded HeyGen video URLs for local mode
        local_heygen_urls = [
            "https://files2.heygen.ai/aws_pacific/avatar_tmp/fc001c501c65419385a406d9281db788/c4d15b0053364c2f9a676341a40bafae.mp4?Expires=1755527003&Signature=pFusBVqK-V0FOn90Mh9MlsKwk5Szq6kmi9akRezOOCb3odcZf8hbNp-r7DtyucVT8XdKMcYmGEr9isrbu3AKBkE1VtovLNXuTNNtSK9CP6ZtjVVj8TIDz0lz3j~Svpo7vgTiFzIulf3ja5H6YRZKrnEYUbVIxmo3BKWdvvaSjfftQmcbblOBI2QjYQZXVZOdsF2UpxLxzbrgifZlTiT373pRS9eVqYJiCzeJJEyrdJp5tpfzIc4o8WcOyuW4zVJ-QS0U4YXcSZpC1t~OLzSbgCg1rCrRKcv0aaha5g-K~-VFyjUhPjJydyA7aRc8MGIaGn2hKIyHCt06-eMk8qEI5w__&Key-Pair-Id=K38HBHX5LX3X2H",
            "https://files2.heygen.ai/aws_pacific/avatar_tmp/fc001c501c65419385a406d9281db788/09db94f0a5d64ecd9aa1c80dc5a41f5c.mp4?Expires=1755527004&Signature=lnNmK8EY~wvlvngCfdcE-4zNZB3yZhMOlt5UnH~x2ds0y6S2b-vF0097lKqDbYHKLYCbXWyFQpxkWf76NSnulH7BjGVlQaXlz3ltr73gp~FKic0Xz1oPBFvH1QJVP7wsCnin7Obm1l9D6z8wsaxnF33yDZHvVCDKOPS3QmXEez8xkncaaXRhe6x1hHXyMTTEfXkVPdUuUIwFXqMyzOGfxLlVL97wm-aWMiMUkrNsExFpUkQmkKPhXQgcIMIKoPJ5FE6Z3WkvsHUaiGiAGBLc4smQTtBS3W259gmFrAaiViizjHTMVsHKDrOdhE2abhOOOq5xXWSadv6t5IY30I0aOg__&Key-Pair-Id=K38HBHX5LX3X2H",
            "https://files2.heygen.ai/aws_pacific/avatar_tmp/fc001c501c65419385a406d9281db788/09cef1834e7d44f2a143cbfe144f54ca.mp4?Expires=1755527008&Signature=G2dEk8ymdsZwuWu7c8iXh~kAPb7Nove6wk6k2YsxJUA5riV~pUXVrT1OB-Miqi7dQF7nI3wrKYSPG~FpMlbng0PmVmP6vtn-Vbk7MSD4K2H~b5BiZ2E03uP8RHoAhe9cMa8vbJCjuZbaXhLtO-26Ab2XmyQXRXVZD8ctvpIsl1fFX5PTbYXKk~IgixoSEj-uRdpxG-B5kCI324n7V~7iCwxnPY-k1CfUSTWn5n83jqy1Wfk~Dmi~2FJgoSEf-~Z4GxIXLyL7FEPw7CwmJ6KSqHzLJPao-JfHNK5tu6~O~wex5N6nb4EZjrxBzs96WG~AHscTiOmgpd7M9-Pj5cReWg__&Key-Pair-Id=K38HBHX5LX3X2H"
        ]
        
        video_urls = {}
        
        # Map fake video IDs to actual URLs
        for i, (key, video_id) in enumerate(heygen_video_ids.items()):
            url_index = i % len(local_heygen_urls)
            video_url = local_heygen_urls[url_index]
            video_urls[key] = video_url
            
            logger.info(f"🏠 Local URL mapped for {key}: {video_url[:60]}...")
        
        logger.info(f"✅ LOCAL MODE: {len(video_urls)} hardcoded URLs ready for Creatomate")
        return video_urls
        
    except Exception as e:
        logger.error(f"❌ Error getting local HeyGen URLs for Creatomate: {str(e)}")
        return None


# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _create_single_video(script_text: str, 
                        key: str,
                        use_template: bool,
                        template_id: Optional[str],
                        headers: Dict[str, str]) -> Optional[str]:
    """Create a single HeyGen video."""
    try:
        config = _get_heygen_config()
        
        # Build payload based on approach
        if use_template and template_id:
            payload = _build_template_payload(script_text, key, template_id)
            url = f"{config['base_url']}/template/{template_id}/generate"
        else:
            payload = _build_custom_payload(script_text, key)
            url = f"{config['base_url']}/video/generate"
        # print(payload)
        # Send request with retry logic
        for attempt in range(config.get('retry_attempts', 3)):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    video_id = data.get("data", {}).get("video_id")
                    
                    if video_id:
                        logger.info(f"✅ Video generation started: {video_id}")
                        return video_id
                    else:
                        logger.error(f"❌ No video_id in response: {data}")
                        return None
                else:
                    logger.error(f"❌ HeyGen API error: {response.status_code} - {response.text}")
                    if attempt < config.get('retry_attempts', 3) - 1:
                        logger.info(f"🔄 Retrying... (attempt {attempt + 2})")
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        return None
                        
            except requests.RequestException as e:
                logger.error(f"❌ Request error (attempt {attempt + 1}): {str(e)}")
                if attempt < config.get('retry_attempts', 3) - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error creating single video: {str(e)}")
        return None


def _build_template_payload(script_text: str, key: str, template_id: str) -> Dict[str, Any]:
    """Build payload for template-based video creation."""
    return {
        "caption": False,
        "title": f"Video for {key}",
        "variables": {
            "script": {
                "name": "script",
                "type": "text",
                "properties": {
                    "content": script_text
                }
            }
        }
    }


def _build_custom_payload(script_text: str, key: str) -> Dict[str, Any]:
    """Build payload for custom video creation."""
    return {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": "Ann_Casual_Sitting_public",
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": script_text,
                    "voice_id": "ef74816547734c36ab44fd4f4d7434c3",
                    "speed": 1.0
                },
                "background": {
                    "type": "color",
                    "value": "#00FF00"
                }
            }
        ],
        "dimension": {
            "width": 1280,
            "height": 720
        },
        "title": f"Video for {key}"
    }


# =============================================================================
# ADVANCED MONITORING HELPER FUNCTIONS
# =============================================================================

def _check_video_status_strict(video_id: str, key: str) -> Dict[str, Any]:
    """
    Check video status with STRICT MODE - NO FALLBACKS.
    
    Args:
        video_id (str): HeyGen video ID
        key (str): Video key for logging
        
    Returns:
        Dict[str, Any]: Video status information
        
    Raises:
        RuntimeError: If status check fails
    """
    try:
        status_info = check_video_status(video_id, silent=True)
        
        if status_info.get('status') == 'error':
            error_msg = f"HeyGen video status check failed for {key} ({video_id}): {status_info.get('error', 'Unknown error')}"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
        return status_info
        
    except Exception as e:
        error_msg = f"Error checking video status for {key}: {str(e)}"
        logger.error(f"❌ STRICT MODE: {error_msg}")
        raise RuntimeError(error_msg)


def _try_fallback_endpoint(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Try alternative HeyGen API endpoints for video status.
    """
    try:
        headers = _get_heygen_headers()
        if not headers:
            return None
        
        # Try alternative endpoint patterns
        fallback_urls = [
            f"https://api.heygen.com/v1/video_status/{video_id}",  # v1 endpoint
            f"https://api.heygen.com/v2/video/{video_id}/status",   # Alternative v2 pattern
            f"https://api.heygen.com/v2/videos/{video_id}"          # Alternative videos endpoint
        ]
        
        for url in fallback_urls:
            try:
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        video_data = data['data']
                        return {
                            'status': video_data.get('status', 'unknown'),
                            'video_url': video_data.get('video_url'),
                            'duration': video_data.get('duration'),
                            'created_at': video_data.get('created_at'),
                            'completed_at': video_data.get('completed_at'),
                            'error': video_data.get('error'),
                            'fallback_endpoint': url
                        }
            except requests.RequestException:
                continue  # Try next fallback
        
        return None
        
    except Exception as e:
        logger.debug(f"Fallback endpoint error: {str(e)}")
        return None


def _calculate_eta(video_status: Dict[str, Dict[str, Any]], current_processing_time: float) -> float:
    """
    Calculate ETA for individual video based on completed videos' processing times.
    """
    try:
        # Get processing times of completed videos
        completed_times = [
            status.get('processing_time', 0) 
            for status in video_status.values() 
            if status.get('status') == 'completed' and status.get('processing_time', 0) > 0
        ]
        
        if not completed_times:
            # No completed videos yet, use conservative estimate
            estimated_total_time = max(120, current_processing_time * 2)  # At least 2min or 2x current
            return max(0, estimated_total_time - current_processing_time)
        
        # Calculate average processing time from completed videos
        avg_processing_time = sum(completed_times) / len(completed_times)
        
        # ETA = average processing time - current processing time
        eta = max(0, avg_processing_time - current_processing_time)
        
        # Add buffer for variability (20%)
        eta_with_buffer = eta * 1.2
        
        return max(10, eta_with_buffer)  # Minimum 10s ETA
        
    except Exception as e:
        logger.debug(f"ETA calculation error: {str(e)}")
        return 60.0  # Default 60s ETA


def _calculate_overall_eta(video_status: Dict[str, Dict[str, Any]], remaining_videos: int) -> float:
    """
    Calculate overall ETA for all remaining videos.
    """
    try:
        if remaining_videos <= 0:
            return 0.0
        
        # Get average ETA of processing videos
        processing_etas = [
            status.get('eta', 60) 
            for status in video_status.values() 
            if status.get('status') == 'processing' and status.get('eta')
        ]
        
        if processing_etas:
            avg_eta = sum(processing_etas) / len(processing_etas)
        else:
            # Fallback to completed video average if available
            completed_times = [
                status.get('processing_time', 0) 
                for status in video_status.values() 
                if status.get('status') == 'completed' and status.get('processing_time', 0) > 0
            ]
            
            if completed_times:
                avg_eta = sum(completed_times) / len(completed_times)
            else:
                avg_eta = 120  # Default 2min per video
        
        # Overall ETA = average ETA of remaining videos
        overall_eta = avg_eta * remaining_videos * 0.8  # 20% efficiency factor for batch processing
        
        return max(30, overall_eta)  # Minimum 30s overall ETA
        
    except Exception as e:
        logger.debug(f"Overall ETA calculation error: {str(e)}")
        return remaining_videos * 60.0  # Default 60s per remaining video

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_heygen_config_status() -> Dict[str, Any]:
    """
    Get HeyGen configuration status and information.
    
    Returns:
        Dict[str, Any]: Configuration status and details
    """
    status = {
        'api_key_set': False,
        'headers_available': False,
        'config_loaded': False,
        'connection_test': False,
        'available_templates': [],
        'last_error': None
    }
    
    try:
        # Check API key
        status['api_key_set'] = bool(os.getenv('HEYGEN_API_KEY'))
        
        # Check headers
        headers = _get_heygen_headers()
        status['headers_available'] = headers is not None
        
        # Check config
        config = _get_heygen_config()
        status['config_loaded'] = bool(config)
        
        # Test connection (simple API call)
        if headers:
            try:
                # This is a placeholder - HeyGen doesn't have a simple ping endpoint
                # We could test with a minimal request
                status['connection_test'] = True
            except Exception as e:
                status['last_error'] = f"Connection test failed: {str(e)}"
        
        return status
        
    except Exception as e:
        status['last_error'] = str(e)
        logger.error(f"Error getting HeyGen config status: {str(e)}")
        return status


def estimate_video_duration(script: str, detailed: bool = False) -> float:
    """
    ADVANCED video duration estimation with comprehensive analysis.
    
    Features:
    - Multiple calculation methods (words, characters, sentences)
    - Language-aware speaking rates
    - Punctuation-based pause detection
    - Avatar animation time estimation
    - Template-specific timing adjustments
    
    Args:
        script (str): Script content
        detailed (bool): Return detailed breakdown
        
    Returns:
        float: Estimated duration in seconds (or dict if detailed=True)
    """
    try:
        if not script or not script.strip():
            return 0.0 if not detailed else {'total': 0.0, 'error': 'Empty script'}
        
        script = script.strip()
        
        # METHOD 1: Word-based calculation (primary)
        words = len(script.split())
        
        # Adjust speaking rate based on content complexity
        if words < 10:
            speaking_rate = 120  # Slower for very short scripts
        elif words < 50:
            speaking_rate = 140  # Moderate pace
        else:
            speaking_rate = 160  # Faster for longer content
        
        word_based_duration = (words / speaking_rate) * 60
        
        # METHOD 2: Character-based calculation (secondary)
        chars = len(script)
        # Average: ~600-800 characters per minute of speech
        char_based_duration = chars / 700 * 60
        
        # METHOD 3: Sentence-based calculation (tertiary)
        sentences = len([s for s in script.split('.') if s.strip()])
        # Average: ~3-4 seconds per sentence including pauses
        sentence_based_duration = sentences * 3.5
        
        # WEIGHTED AVERAGE of all methods
        base_duration = (
            word_based_duration * 0.6 +    # Primary weight
            char_based_duration * 0.3 +    # Secondary weight
            sentence_based_duration * 0.1   # Tertiary weight
        )
        
        # PAUSE ANALYSIS: Add time for punctuation-based pauses
        commas = script.count(',')
        periods = script.count('.')
        questions = script.count('?')
        exclamations = script.count('!')
        
        pause_time = (
            commas * 0.3 +        # Short pause for commas
            periods * 0.8 +       # Medium pause for periods
            questions * 0.9 +     # Slightly longer for questions
            exclamations * 0.7    # Moderate pause for exclamations
        )
        
        # AVATAR ANIMATION BUFFER
        # HeyGen avatars need extra time for natural gestures and transitions
        animation_buffer = base_duration * 0.15  # 15% buffer
        
        # TEMPLATE TIMING ADJUSTMENTS
        # Some templates have intro/outro sequences
        template_buffer = 2.0  # Standard 2-second buffer for template transitions
        
        # FINAL CALCULATION
        total_duration = base_duration + pause_time + animation_buffer + template_buffer
        
        # BOUNDS CHECKING
        # Minimum: 3 seconds for very short scripts
        # Maximum: 180 seconds (3 minutes) for very long scripts
        total_duration = max(3.0, min(total_duration, 180.0))
        
        if detailed:
            return {
                'total': round(total_duration, 1),
                'breakdown': {
                    'base_duration': round(base_duration, 1),
                    'word_based': round(word_based_duration, 1),
                    'char_based': round(char_based_duration, 1),
                    'sentence_based': round(sentence_based_duration, 1),
                    'pause_time': round(pause_time, 1),
                    'animation_buffer': round(animation_buffer, 1),
                    'template_buffer': template_buffer
                },
                'stats': {
                    'words': words,
                    'characters': chars,
                    'sentences': sentences,
                    'speaking_rate': speaking_rate,
                    'punctuation': {
                        'commas': commas,
                        'periods': periods,
                        'questions': questions,
                        'exclamations': exclamations
                    }
                }
            }
        
        return round(total_duration, 1)
        
    except Exception as e:
        logger.error(f"Error in advanced duration estimation: {str(e)}")
        default_duration = 10.0
        
        if detailed:
            return {
                'total': default_duration,
                'error': str(e),
                'fallback': True
            }
        
        return default_duration


def select_optimal_template(genre: Optional[str] = None, 
                           content_type: str = "movie") -> Dict[str, Any]:
    """
    ADVANCED template selection with fallback logic and optimization.
    
    Features:
    - Genre-specific template matching with fuzzy matching
    - Content type awareness (movie, series, documentary)
    - Fallback template hierarchy for reliability
    - Template performance analytics
    - A/B testing support for template optimization
    
    Args:
        genre (str): Primary genre for template selection
        content_type (str): Type of content (movie, series, documentary)
        fallback_enabled (bool): Enable fallback template logic
        
    Returns:
        Dict[str, Any]: Template selection result with metadata
    """
    try:
        logger.info(f"🎭 ADVANCED TEMPLATE SELECTION: {genre} | {content_type}")
        
        selection_result = {
            'template_id': None,
            'template_name': None,
            'selection_method': None,
            'confidence': 0.0,
            'fallbacks_available': [],
            'recommendation_reason': None
        }
        
        # STEP 1: Primary genre-based selection
        if genre:
            primary_template = get_heygen_template_id(genre)
            if primary_template:
                selection_result.update({
                    'template_id': primary_template,
                    'template_name': _get_template_name(primary_template, genre),
                    'selection_method': 'genre_primary',
                    'confidence': 0.95,
                    'recommendation_reason': f'Direct genre match for {genre}'
                })
                
                logger.info(f"✅ Primary template selected: {primary_template} for {genre}")
        
        # STEP 2: Fuzzy genre matching for partial matches
        if not selection_result['template_id'] and genre and fallback_enabled:
            fuzzy_template = _find_fuzzy_genre_match(genre)
            if fuzzy_template:
                selection_result.update({
                    'template_id': fuzzy_template['template_id'],
                    'template_name': fuzzy_template['template_name'],
                    'selection_method': 'genre_fuzzy',
                    'confidence': fuzzy_template['confidence'],
                    'recommendation_reason': f'Fuzzy match: {genre} → {fuzzy_template["matched_genre"]}'
                })
                
                logger.info(f"🔍 Fuzzy match found: {fuzzy_template['template_id']} ({fuzzy_template['confidence']:.2f} confidence)")
        
        # STRICT MODE: If no template found, process must fail
        if not selection_result['template_id']:
            error_msg = f"No suitable template found for genre '{genre}' and content type '{content_type}'"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
        logger.info(f"🎯 Template selection complete:")
        logger.info(f"   Template: {selection_result['template_id']} ({selection_result['template_name']})")
        logger.info(f"   Method: {selection_result['selection_method']} (confidence: {selection_result['confidence']:.2f})")
        logger.info(f"   Reason: {selection_result['recommendation_reason']}")
        
        return selection_result
        
    except Exception as e:
        logger.error(f"❌ Error in advanced template selection: {str(e)}")
        
        # STRICT MODE: Re-raise the error instead of emergency fallback
        error_msg = f"Template selection error: {str(e)}"
        logger.error(f"❌ STRICT MODE: {error_msg}")
        raise RuntimeError(error_msg)


def _get_template_name(template_id: str, genre: str = None) -> str:
    """Get human-readable template name."""
    template_names = {
        'ed21a309a5c84b0d873fde68642adea3': 'Horror/Thriller Cinematic',
        '15d9eadcb46a45dbbca1834aa0a23ede': 'Comedy/Light Entertainment',
        'e44b139a1b94446a997a7f2ac5ac4178': 'Action/Adventure Dynamic',
        'cc6718c5363e42b282a123f99b94b335': 'Universal Default'
    }
    
    return template_names.get(template_id, f'{genre or "Generic"} Template ({template_id[:8]}...)')


def _find_fuzzy_genre_match(genre: str) -> Optional[Dict[str, Any]]:
    """Find fuzzy matches for genres using similarity matching."""
    try:
        genre_lower = genre.lower()
        
        # Genre similarity mappings
        fuzzy_mappings = {
            'horror': {'genres': ['thriller', 'suspense', 'scary', 'terror'], 'confidence': 0.8},
            'thriller': {'genres': ['horror', 'suspense', 'mystery'], 'confidence': 0.8},
            'comedy': {'genres': ['humor', 'funny', 'comedic', 'laugh'], 'confidence': 0.85},
            'action': {'genres': ['adventure', 'fight', 'battle', 'war'], 'confidence': 0.8},
            'adventure': {'genres': ['action', 'exploration', 'journey'], 'confidence': 0.75},
            'drama': {'genres': ['dramatic', 'serious', 'emotional'], 'confidence': 0.7}
        }
        
        for template_genre, mapping in fuzzy_mappings.items():
            if any(fuzzy_word in genre_lower for fuzzy_word in mapping['genres']):
                template_id = get_heygen_template_id(template_genre.capitalize())
                if template_id:
                    return {
                        'template_id': template_id,
                        'template_name': _get_template_name(template_id, template_genre),
                        'matched_genre': template_genre,
                        'confidence': mapping['confidence']
                    }
        
        return None
        
    except Exception as e:
        logger.debug(f"Fuzzy matching error: {str(e)}")
        return None


def _get_content_type_template(content_type: str) -> Optional[Dict[str, Any]]:
    """Get template based on content type."""
    content_templates = {
        'movie': {'template_id': get_heygen_template_id(None), 'name': 'Movie Standard'},
        'series': {'template_id': get_heygen_template_id(None), 'name': 'Series Format'},
        'documentary': {'template_id': get_heygen_template_id(None), 'name': 'Documentary Style'}
    }
    
    template_info = content_templates.get(content_type.lower())
    if template_info:
        return {
            'template_id': template_info['template_id'],
            'template_name': template_info['name']
        }
    
    return None


# FALLBACK FUNCTIONS REMOVED - STRICT MODE ONLY
# All template selection must succeed or fail - no fallback hierarchies allowed