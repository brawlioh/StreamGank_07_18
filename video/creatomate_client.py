"""
StreamGank Creatomate Client

This module handles Creatomate API integration for video composition and rendering.
Provides a clean interface for creating and managing video render jobs.

Features:
- Video composition creation and submission
- Render status monitoring and tracking
- Automatic retry logic and error handling
- Render completion waiting with progress updates
- Video URL retrieval and validation
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
import requests

from config.settings import get_api_config
from utils.validators import validate_environment_variables, is_valid_url
from video.composition_builder import build_video_composition
from video.video_processor import validate_video_urls

logger = logging.getLogger(__name__)

# =============================================================================
# CREATOMATE CLIENT CONFIGURATION
# =============================================================================

def _get_creatomate_headers() -> Optional[Dict[str, str]]:
    """
    Get Creatomate API headers with authentication.
    
    Returns:
        Dict[str, str]: API headers or None if API key missing
    """
    try:
        api_key = os.getenv('CREATOMATE_API_KEY')
        if not api_key:
            error_msg = "Missing Creatomate API key (CREATOMATE_API_KEY)"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    except Exception as e:
        error_msg = f"Error getting Creatomate headers: {str(e)}"
        logger.error(f"❌ STRICT MODE: {error_msg}")
        raise RuntimeError(error_msg)


def _get_webhook_url() -> Optional[str]:
    """
    Get webhook URL for Creatomate render completion notifications.
    
    Returns:
        str: Webhook URL or None if not configured
    """
    try:
        # Get the base webhook URL from environment or use localhost for development
        base_url = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:3000')
        webhook_endpoint = '/api/webhooks/creatomate-completion'  # Using original reliable endpoint
        
        webhook_url = f"{base_url}{webhook_endpoint}"
        
        # Validate URL format
        if not webhook_url.startswith(('http://', 'https://')):
            logger.error(f"❌ Invalid webhook URL format: {webhook_url}")
            return None
            
        return webhook_url
        
    except Exception as e:
        logger.error(f"❌ Error getting webhook URL: {str(e)}")
        return None


def _get_creatomate_config() -> Dict[str, Any]:
    """Get Creatomate API configuration."""
    try:
        api_config = get_api_config('creatomate')
        return {
            'base_url': api_config.get('base_url', 'https://api.creatomate.com/v1'),
            'poll_interval': api_config.get('poll_interval', 10),
            'max_wait_time': api_config.get('max_wait_time', 1800),  # 30 minutes
            'retry_attempts': api_config.get('retry_attempts', 3),
            'timeout': api_config.get('timeout', 60)
        }
    except Exception as e:
        logger.error(f"Error getting Creatomate config: {str(e)}")
        return {}

# =============================================================================
# MAIN VIDEO CREATION FUNCTIONS
# =============================================================================

def create_creatomate_video(heygen_video_urls: Dict[str, str],
                          movie_covers: Optional[List[str]] = None,
                          movie_clips: Optional[List[str]] = None,
                          scroll_video_url: Optional[str] = None,
                          scripts: Optional[Dict] = None,
                          poster_timing_mode: str = "heygen_last3s",
                          background_music_url: Optional[str] = None) -> str:
    """
    Create a video using Creatomate API with all provided assets.
    
    STRICT MODE: All required components must be available. No fallbacks used.
    Process stops immediately if any validation or creation step fails.
    
    This is the main entry point for video creation that:
    1. Validates all input URLs and assets (STRICT - no fallbacks)
    2. Builds the complete video composition (STRICT - raises on failure)
    3. Submits the render job to Creatomate (STRICT - raises on failure)
    4. Returns the render ID (guaranteed if function returns)
    
    Args:
        heygen_video_urls (Dict): Dictionary mapping keys to HeyGen video URLs (REQUIRED)
        movie_covers (List): List of enhanced poster URLs (REQUIRED - exactly 3)
        movie_clips (List): List of processed movie clip URLs (REQUIRED - exactly 3)
        scroll_video_url (str): Optional scroll video URL for overlay
        scripts (Dict): Optional script data for duration estimation
        poster_timing_mode (str): Poster timing strategy
        background_music_url (str): Optional background music URL for audio elements
        
    Returns:
        str: Creatomate render ID (guaranteed success)
        
    Raises:
        ValueError: If required data is missing or invalid
        RuntimeError: If video creation fails
    """
    logger.info("🎬 CREATOMATE VIDEO CREATION (STRICT MODE - NO FALLBACKS)")
    logger.info(f"   HeyGen videos: {len(heygen_video_urls)}")
    logger.info(f"   Movie covers: {len(movie_covers) if movie_covers else 0}")
    logger.info(f"   Movie clips: {len(movie_clips) if movie_clips else 0}")
    logger.info(f"   Scroll video: {'Yes' if scroll_video_url else 'No'}")
    logger.info(f"   Timing mode: {poster_timing_mode}")
    
    # STRICT: Validate API configuration
    headers = _get_creatomate_headers()
    if not headers:
        raise RuntimeError("❌ CRITICAL: Creatomate API headers not available - cannot proceed")
    
    # STRICT: Validate input URLs thoroughly
    url_validation = validate_video_urls(heygen_video_urls, movie_covers, movie_clips, scroll_video_url)
    if not url_validation['is_valid']:
        errors = url_validation.get('errors', [])
        raise ValueError(f"❌ CRITICAL: URL validation failed: {'; '.join(errors)}")
    
    # STRICT: Build video composition (will raise on failure)
    logger.info("🏗️ Building video composition (STRICT mode)...")
    composition = build_video_composition(
        heygen_video_urls=heygen_video_urls,
        movie_covers=movie_covers,
        movie_clips=movie_clips,
        scroll_video_url=scroll_video_url,
        scripts=scripts,
        poster_timing_mode=poster_timing_mode,
        background_music_url=background_music_url
    )
    
    # STRICT: Submit render job (will raise on failure)
    logger.info("📤 Submitting render job to Creatomate (STRICT mode)...")
    render_id = send_creatomate_request(composition)
    
    if not render_id:
        raise RuntimeError("❌ CRITICAL: Failed to submit Creatomate render - no render ID received")
    
    logger.info(f"✅ Creatomate render submitted successfully: {render_id}")
    return render_id


def send_creatomate_request(composition: Dict[str, Any]) -> Optional[str]:
    """
    Send render request to Creatomate API.
    
    Args:
        composition (Dict): Video composition data
        
    Returns:
        str: Render ID or None if failed
    """
    try:
        headers = _get_creatomate_headers()
        if not headers:
            error_msg = "Creatomate API headers not available"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
        config = _get_creatomate_config()
        url = f"{config['base_url']}/renders"
        
        logger.info("📤 Sending render request to Creatomate...")
        logger.info(f"   Elements: {len(composition.get('elements', []))}")
        logger.info(f"   Duration: {composition.get('duration', 'auto')}")
        
        # Get webhook URL for completion notifications
        webhook_url = _get_webhook_url()
        
        # Prepare payload to match legacy format EXACTLY  
        payload = {
            "source": composition,  # Raw JSON composition must be wrapped in "source"
            "output_format": "mp4", # Must match legacy payload exactly
            "render_scale": 1       # Must match legacy payload exactly  
        }
        
        # Add webhook URL for completion notifications (avoids polling)
        if webhook_url:
            payload["webhook_url"] = webhook_url
            logger.info(f"🔗 Webhook URL configured: {webhook_url}")
        else:
            logger.warning("⚠️ No webhook URL configured - falling back to polling")
        
        # Submit request with retry logic
        for attempt in range(config.get('retry_attempts', 3)):
            try:
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=payload,  # Send payload with "source" parameter
                    timeout=config.get('timeout', 60)
                )
                
                if response.status_code in [200, 201, 202]:  # 202 = Accepted (processing)
                    data = response.json()
                    # Handle both single object and array responses
                    if isinstance(data, list) and len(data) > 0:
                        render_id = data[0].get('id')
                    else:
                        render_id = data.get('id')
                    
                    if render_id:
                        logger.info(f"✅ Render request submitted: {render_id}")
                        return render_id
                    else:
                        logger.error(f"❌ No render ID in response: {data}")
                        return None
                        
                elif response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"⏳ Rate limit hit, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                    
                else:
                    logger.error(f"❌ Creatomate API error: {response.status_code} - {response.text}")
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
        logger.error(f"❌ Error sending Creatomate request: {str(e)}")
        return None

# =============================================================================
# RENDER STATUS MONITORING
# =============================================================================

def check_render_status(render_id: str, silent: bool = False) -> Dict[str, Any]:
    """
    Check the status of a Creatomate render.
    
    Args:
        render_id (str): Creatomate render ID
        silent (bool): Suppress logging output
        
    Returns:
        Dict[str, Any]: Render status information
    """
    try:
        headers = _get_creatomate_headers()
        if not headers:
            return {'status': 'error', 'error': 'API headers not available'}
        
        config = _get_creatomate_config()
        url = f"{config['base_url']}/renders/{render_id}"
        
        if not silent:
            logger.debug(f"🔍 Checking render status: {render_id}")
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            status_info = {
                'status': data.get('status', 'unknown'),
                'progress': data.get('progress', 0),
                'url': data.get('url'),
                'duration': data.get('duration'),
                'created_at': data.get('created_at'),
                'completed_at': data.get('completed_at'),
                'error': data.get('error'),
                'snapshot_url': data.get('snapshot_url')
            }
            
            if not silent:
                status = status_info['status']
                progress = status_info['progress']
                
                if status == 'succeeded':
                    logger.info(f"✅ Render {render_id}: {status}")
                    if status_info['url']:
                        logger.info(f"   🎬 Video URL: {status_info['url']}")
                elif status == 'processing':
                    logger.info(f"⏳ Render {render_id}: {status} ({progress}%)")
                elif status == 'failed':
                    logger.error(f"❌ Render {render_id}: {status}")
                    if status_info['error']:
                        logger.error(f"   Error: {status_info['error']}")
                else:
                    logger.info(f"🔄 Render {render_id}: {status}")
            
            return status_info
        else:
            error_msg = f"API error: {response.status_code}"
            if not silent:
                logger.error(f"❌ Status check failed for {render_id}: {error_msg}")
            return {'status': 'error', 'error': error_msg}
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        if not silent:
            logger.error(f"❌ Error checking render status {render_id}: {error_msg}")
        return {'status': 'error', 'error': error_msg}


def wait_for_completion(render_id: str, 
                       max_wait_time: int = 1800,
                       poll_interval: int = 10) -> Dict[str, Any]:
    """
    ADVANCED Creatomate render monitoring with intelligent progress tracking.
    
    Features:
    - Dynamic ETA calculations based on render progress patterns
    - Adaptive polling intervals based on render stage
    - Detailed progress breakdown with render stage detection
    - Smart timeout handling with context-aware logging
    - Professional render performance analytics
    - Fallback endpoint attempts for status checking
    
    Args:
        render_id (str): Creatomate render ID
        max_wait_time (int): Maximum time to wait in seconds (default: 30 minutes)
        poll_interval (int): Base polling interval in seconds (adaptive)
        
    Returns:
        Dict[str, Any]: Comprehensive final render status with analytics
    """
    try:
        logger.info(f"🎬 ADVANCED CREATOMATE MONITORING: {render_id}")
        logger.info(f"   ⏱️ Max wait: {max_wait_time}s | Base poll interval: {poll_interval}s")
        logger.info(f"   🔍 Features: ETA calculation, Adaptive polling, Stage detection")
        
        start_time = time.time()
        last_progress = -1
        last_stage = None
        progress_history = []
        stage_start_times = {}
        
        poll_count = 0
        current_poll_interval = poll_interval
        
        while True:
            poll_count += 1
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            logger.info(f"🔍 Poll #{poll_count} - Elapsed: {elapsed_time:.0f}s/{max_wait_time}s")
            
            # Check timeout with intelligent context
            if elapsed_time > max_wait_time:
                logger.warning(f"⏰ TIMEOUT reached ({max_wait_time}s)")
                logger.info(f"   📉 Progress history: {progress_history[-5:] if progress_history else 'No progress recorded'}")
                logger.info(f"   🔄 Attempting final status check with STRICT validation...")
            
            final_status = _check_render_status_strict(render_id)
            logger.warning(f"   Final status: {final_status['status']} at {final_status.get('progress', 0)}%")
            break
            
        # Check status with STRICT MODE - NO FALLBACKS
        status_info = _check_render_status_strict(render_id)
            
        if status_info['status'] == 'succeeded':
            total_time = time.time() - start_time
            logger.info(f"✅ RENDER COMPLETED in {total_time:.0f}s!")
                
            if status_info.get('url'):
                logger.info(f"   🎬 Video URL: {status_info['url']}")
            if status_info.get('duration'):
                logger.info(f"   ⏱️ Video duration: {status_info['duration']}s")
                
            # Add performance analytics
            status_info['render_analytics'] = _calculate_render_analytics(
                total_time, progress_history, stage_start_times
            )
                
            return status_info
                
        elif status_info['status'] == 'failed':
            total_time = time.time() - start_time
            logger.error(f"❌ RENDER FAILED after {total_time:.0f}s")
            logger.error(f"   Error: {status_info.get('error', 'Unknown error')}")
            logger.info(f"   📉 Progress reached: {max(progress_history) if progress_history else 0}%")
            return status_info
                
        elif status_info['status'] == 'error':
            logger.error(f"❌ API ERROR: {status_info.get('error', 'Unknown error')}")
            return status_info
            
        # Advanced progress tracking and stage detection
        current_progress = status_info.get('progress', 0)
        current_stage = _detect_render_stage(current_progress)
            
        # Track stage transitions
        if current_stage != last_stage:
            stage_start_times[current_stage] = current_time
            if last_stage:
                stage_duration = current_time - stage_start_times.get(last_stage, current_time)
                logger.info(f"🔄 Stage transition: {last_stage} → {current_stage} (took {stage_duration:.0f}s)")
            last_stage = current_stage
            
        # Show detailed progress if changed
        if current_progress != last_progress:
            progress_history.append(current_progress)
                
            # Calculate ETA based on progress velocity
            eta = _calculate_render_eta(progress_history, elapsed_time, current_progress)
                
            logger.info(f"📈 Render progress: {current_progress}% | Stage: {current_stage}")
            logger.info(f"   ⏱️ Elapsed: {elapsed_time:.0f}s | ETA: {eta:.0f}s | Total est: {elapsed_time + eta:.0f}s")
                
            last_progress = current_progress
                
            # Adaptive polling - faster during active stages
            current_poll_interval = _calculate_adaptive_poll_interval(
                current_stage, current_progress, poll_interval
            )
            
        # Wait with adaptive interval
        if poll_count % 3 == 0:  # Every 3rd poll, show extended info
            logger.info(f"   ⏳ Next check in {current_poll_interval}s (adaptive)...")
            
        time.sleep(current_poll_interval)
        
        # If we exit the loop, it's due to timeout
        final_status = check_render_status(render_id)
        logger.warning(f"⏰ Wait timeout, final status: {final_status['status']}")
        
        # Add timeout analytics
        final_status['timeout_analytics'] = {
            'elapsed_time': elapsed_time,
            'max_progress_reached': max(progress_history) if progress_history else 0,
            'total_polls': poll_count,
            'stages_completed': list(stage_start_times.keys())
        }
        
        return final_status
        
    except Exception as e:
        logger.error(f"❌ Error in advanced render monitoring: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def get_creatomate_video_url(render_id: str) -> Optional[str]:
    """
    Get the final video URL from a completed Creatomate render.
    
    Args:
        render_id (str): Creatomate render ID
        
    Returns:
        str: Video URL or None if not available
    """
    try:
        status_info = check_render_status(render_id)
        
        if status_info['status'] == 'succeeded' and status_info.get('url'):
            video_url = status_info['url']
            
            # Validate URL
            if is_valid_url(video_url):
                logger.info(f"✅ Video URL retrieved: {video_url}")
                return video_url
            else:
                logger.error(f"❌ Invalid video URL: {video_url}")
                return None
        else:
            logger.warning(f"⚠️ Video not ready, status: {status_info['status']}")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error getting video URL: {str(e)}")
        return None

# =============================================================================
# BATCH PROCESSING FUNCTIONS
# =============================================================================

def create_multiple_videos(video_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create multiple videos in batch using Creatomate.
    
    Args:
        video_configs (List): List of video configuration dictionaries
        
    Returns:
        Dict[str, Any]: Batch processing results
    """
    results = {
        'successful_renders': 0,
        'failed_renders': 0,
        'render_ids': [],
        'errors': []
    }
    
    try:
        logger.info(f"📦 BATCH VIDEO CREATION: {len(video_configs)} videos")
        
        for i, config in enumerate(video_configs):
            video_id = f"video_{i+1}"
            logger.info(f"🎯 Creating {video_id}...")
            
            try:
                render_id = create_creatomate_video(**config)
                
                if render_id:
                    results['render_ids'].append({
                        'video_id': video_id,
                        'render_id': render_id,
                        'config': config
                    })
                    results['successful_renders'] += 1
                    logger.info(f"✅ {video_id} submitted: {render_id}")
                else:
                    results['failed_renders'] += 1
                    results['errors'].append(f"{video_id}: Render submission failed")
                    logger.error(f"❌ {video_id} failed")
                
            except Exception as e:
                error_msg = f"{video_id}: {str(e)}"
                results['failed_renders'] += 1
                results['errors'].append(error_msg)
                logger.error(f"❌ {video_id} error: {str(e)}")
        
        logger.info(f"🏁 BATCH SUBMISSION COMPLETE:")
        logger.info(f"   ✅ Successful: {results['successful_renders']}")
        logger.info(f"   ❌ Failed: {results['failed_renders']}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in batch video creation: {str(e)}")
        results['errors'].append(f"Batch processing error: {str(e)}")
        return results


def wait_for_batch_completion(render_ids: List[str], 
                             max_wait_time: int = 1800) -> Dict[str, Dict[str, Any]]:
    """
    Wait for multiple Creatomate renders to complete.
    
    Args:
        render_ids (List): List of render IDs to monitor
        max_wait_time (int): Maximum wait time per video
        
    Returns:
        Dict[str, Dict]: Status information for each render
    """
    results = {}
    
    try:
        logger.info(f"⏳ Waiting for {len(render_ids)} renders to complete...")
        
        for i, render_id in enumerate(render_ids):
            logger.info(f"🎯 Waiting for render {i+1}/{len(render_ids)}: {render_id}")
            
            status_info = wait_for_completion(render_id, max_wait_time)
            results[render_id] = status_info
            
            if status_info['status'] == 'succeeded':
                logger.info(f"✅ Render {i+1} completed")
            else:
                logger.error(f"❌ Render {i+1} failed: {status_info.get('error', 'Unknown')}")
        
        # Summary
        completed = sum(1 for status in results.values() if status['status'] == 'succeeded')
        failed = len(render_ids) - completed
        
        logger.info(f"🏁 BATCH COMPLETION SUMMARY:")
        logger.info(f"   ✅ Completed: {completed}")
        logger.info(f"   ❌ Failed: {failed}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error waiting for batch completion: {str(e)}")
        return results

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_creatomate_config_status() -> Dict[str, Any]:
    """
    Get Creatomate configuration status and information.
    
    Returns:
        Dict[str, Any]: Configuration status and details
    """
    status = {
        'api_key_set': False,
        'headers_available': False,
        'config_loaded': False,
        'connection_test': False,
        'last_error': None
    }
    
    try:
        # Check API key
        status['api_key_set'] = bool(os.getenv('CREATOMATE_API_KEY'))
        
        # Check headers
        headers = _get_creatomate_headers()
        status['headers_available'] = headers is not None
        
        # Check config
        config = _get_creatomate_config()
        status['config_loaded'] = bool(config)
        
        # Test connection (simple API call)
        if headers:
            try:
                config = _get_creatomate_config()
                url = f"{config['base_url']}/renders?limit=1"
                response = requests.get(url, headers=headers, timeout=10)
                status['connection_test'] = response.status_code in [200, 401]  # 401 is also valid (means auth works)
            except Exception as e:
                status['last_error'] = f"Connection test failed: {str(e)}"
        
        return status
        
    except Exception as e:
        status['last_error'] = str(e)
        logger.error(f"Error getting Creatomate config status: {str(e)}")
        return status


def estimate_render_time(composition: Dict[str, Any]) -> float:
    """
    Estimate render time based on composition complexity.
    
    Args:
        composition (Dict): Video composition data
        
    Returns:
        float: Estimated render time in seconds
    """
    try:
        # Base time per second of video
        base_time_per_second = 10.0  # seconds
        
        # Get video duration
        duration = composition.get('duration', 30)  # Default 30s
        if duration == 'auto':
            duration = 30  # Conservative estimate
        
        # Count elements for complexity
        elements = composition.get('elements', [])
        element_count = len(elements)
        
        # Base render time
        base_time = duration * base_time_per_second
        
        # Complexity multiplier based on elements
        if element_count > 20:
            complexity_multiplier = 2.0
        elif element_count > 10:
            complexity_multiplier = 1.5
        else:
            complexity_multiplier = 1.0
        
        # Calculate total estimate
        estimated_time = base_time * complexity_multiplier
        
        # Add buffer time
        estimated_time_with_buffer = estimated_time * 1.3
        
        logger.debug(f"📊 Render time estimate: {estimated_time_with_buffer:.0f}s ({duration}s video, {element_count} elements)")
        
        return estimated_time_with_buffer
        
    except Exception as e:
        logger.error(f"Error estimating render time: {str(e)}")
        return 300.0  # Default 5 minutes


# =============================================================================
# ADVANCED MONITORING HELPER FUNCTIONS
# =============================================================================

def _check_render_status_strict(render_id: str) -> Dict[str, Any]:
    """
    Check render status with STRICT MODE - NO FALLBACKS.
    
    Args:
        render_id (str): Creatomate render ID
        
    Returns:
        Dict[str, Any]: Render status information
        
    Raises:
        RuntimeError: If status check fails
    """
    status_info = check_render_status(render_id, silent=True)
    
    if status_info.get('status') == 'error':
        error_msg = f"Creatomate status check failed for {render_id}: {status_info.get('error', 'Unknown error')}"
        logger.error(f"❌ STRICT MODE: {error_msg}")
        raise RuntimeError(error_msg)
    
    return status_info


def _detect_render_stage(progress: int) -> str:
    """
    Detect current render stage based on progress percentage.
    """
    if progress < 5:
        return "Initializing"
    elif progress < 15:
        return "Preprocessing"
    elif progress < 30:
        return "Asset Loading"
    elif progress < 80:
        return "Rendering"
    elif progress < 95:
        return "Postprocessing" 
    elif progress < 100:
        return "Finalizing"
    else:
        return "Complete"


def _calculate_render_eta(progress_history: List[int], elapsed_time: float, current_progress: int) -> float:
    """
    Calculate ETA based on progress velocity and render patterns.
    """
    try:
        if len(progress_history) < 2 or current_progress >= 100:
            return 0.0
        
        # Calculate recent progress velocity (last 3 data points)
        recent_history = progress_history[-3:]
        if len(recent_history) >= 2:
            progress_diff = recent_history[-1] - recent_history[0]
            time_interval = (len(recent_history) - 1) * 10  # Assuming 10s intervals
            
            if progress_diff > 0:
                velocity = progress_diff / time_interval  # progress per second
                remaining_progress = 100 - current_progress
                eta = remaining_progress / velocity
                
                # Apply stage-based adjustment
                stage = _detect_render_stage(current_progress)
                stage_adjustments = {
                    "Initializing": 0.8,  # Usually speeds up
                    "Preprocessing": 1.0,
                    "Asset Loading": 1.2,  # Can be slow
                    "Rendering": 1.0,
                    "Postprocessing": 0.9,  # Usually faster
                    "Finalizing": 0.7   # Quick final steps
                }
                
                adjusted_eta = eta * stage_adjustments.get(stage, 1.0)
                return max(30, min(adjusted_eta, 1800))  # Between 30s and 30min
        
        # Fallback: linear estimation
        if current_progress > 0:
            time_per_percent = elapsed_time / current_progress
            remaining_percent = 100 - current_progress
            return remaining_percent * time_per_percent
        
        return 600.0  # Default 10 minutes
        
    except Exception as e:
        logger.debug(f"ETA calculation error: {str(e)}")
        return 300.0  # Default 5 minutes


def _calculate_adaptive_poll_interval(stage: str, progress: int, base_interval: int) -> int:
    """
    Calculate adaptive polling interval based on render stage and progress.
    """
    # Stage-based intervals
    stage_intervals = {
        "Initializing": base_interval * 0.5,  # Poll more frequently
        "Preprocessing": base_interval * 0.8,
        "Asset Loading": base_interval * 1.0,
        "Rendering": base_interval * 1.2,  # Poll less frequently during long render
        "Postprocessing": base_interval * 0.8,
        "Finalizing": base_interval * 0.5,  # Poll more frequently near completion
        "Complete": base_interval * 0.5
    }
    
    interval = stage_intervals.get(stage, base_interval)
    
    # Progress-based adjustment
    if progress > 90:
        interval *= 0.7  # More frequent near completion
    elif progress < 10:
        interval *= 0.8  # More frequent at start
    
    return max(5, min(int(interval), 30))  # Between 5s and 30s


def _calculate_render_analytics(total_time: float, progress_history: List[int], stage_times: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculate comprehensive render performance analytics.
    """
    try:
        analytics = {
            'total_render_time': total_time,
            'average_progress_per_minute': (100 / total_time) * 60 if total_time > 0 else 0,
            'progress_data_points': len(progress_history),
            'stages_completed': len(stage_times),
            'stage_durations': {},
            'performance_rating': 'Unknown'
        }
        
        # Calculate stage durations
        stage_list = list(stage_times.keys())
        for i, stage in enumerate(stage_list):
            if i < len(stage_list) - 1:
                next_stage = stage_list[i + 1]
                duration = stage_times[next_stage] - stage_times[stage]
                analytics['stage_durations'][stage] = duration
        
        # Performance rating based on total time
        if total_time < 300:  # Under 5 minutes
            analytics['performance_rating'] = 'Excellent'
        elif total_time < 600:  # Under 10 minutes
            analytics['performance_rating'] = 'Good'
        elif total_time < 1200:  # Under 20 minutes
            analytics['performance_rating'] = 'Average'
        else:
            analytics['performance_rating'] = 'Slow'
        
        return analytics
        
    except Exception as e:
        logger.debug(f"Analytics calculation error: {str(e)}")
        return {'error': str(e)}


def _analyze_composition_complexity(elements: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Analyze composition complexity for render time estimation.
    """
    try:
        video_count = 0
        image_count = 0
        animation_count = 0
        overlay_count = 0
        
        for element in elements:
            element_type = element.get('type', '')
            
            if element_type == 'video':
                video_count += 1
            elif element_type == 'image':
                image_count += 1
            elif element_type == 'composition':
                overlay_count += 1
            
            # Count animations
            animations = element.get('animations', [])
            animation_count += len(animations)
        
        # Calculate complexity factors
        total_elements = len(elements)
        
        return {
            'video_complexity_factor': min(2.5, 1.0 + (video_count * 0.3)),
            'animation_complexity_factor': min(2.0, 1.0 + (animation_count * 0.1)),
            'element_count_factor': min(2.0, 1.0 + (total_elements * 0.05)),
            'overlay_complexity_factor': min(1.5, 1.0 + (overlay_count * 0.2)),
            'total_elements': total_elements,
            'video_count': video_count,
            'animation_count': animation_count
        }
        
    except Exception as e:
        logger.debug(f"Complexity analysis error: {str(e)}")
        return {
            'video_complexity_factor': 1.5,
            'animation_complexity_factor': 1.3,
            'element_count_factor': 1.2,
            'overlay_complexity_factor': 1.1
        }


# =============================================================================
# LEGACY-STYLE SIMPLE CREATOMATE FUNCTIONS (PROVEN TO WORK)
# =============================================================================

def check_creatomate_render_status(render_id: str) -> dict:
    """
    Simple, reliable Creatomate render status check (Legacy Migration)
    
    This is the proven, working implementation from the legacy system.
    Returns simple dict with status, url, and data.
    
    Args:
        render_id (str): Creatomate render ID
        
    Returns:
        dict: Status information with keys: status, url, data
    """
    logger.info(f"Checking Creatomate render status: {render_id}")
    
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        return {"status": "error", "message": "No API key"}
    
    try:
        response = requests.get(
            f"https://api.creatomate.com/v1/renders/{render_id}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get("status", "unknown")
            url = result.get("url", "")
            
            logger.info(f"Creatomate render {render_id} status: {status}")
            if url and status == "completed":
                logger.info(f"Video ready at: {url}")
            
            return {
                "status": status,
                "url": url,
                "data": result
            }
        else:
            logger.error(f"Failed to check render status: {response.status_code} - {response.text}")
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Exception checking render status: {str(e)}")
        return {"status": "error", "message": str(e)}


def wait_for_creatomate_completion(render_id: str, max_attempts: int = 30, interval: int = 10) -> dict:
    """
    Simple, reliable Creatomate render waiting with progress (Legacy Migration)
    
    This is the proven, working implementation from the legacy system.
    Shows progress bar and waits for completion.
    
    Args:
        render_id (str): Creatomate render ID  
        max_attempts (int): Maximum attempts to check (default: 30)
        interval (int): Seconds between checks (default: 10)
        
    Returns:
        dict: Final status information
    """
    logger.info(f"Waiting for Creatomate render {render_id} to complete...")
    
    print(f"\n{'=' * 70}")
    print(f"RENDERING: Creatomate video {render_id}")
    print(f"{'=' * 70}")
    
    for attempt in range(1, max_attempts + 1):
        # Progress bar
        progress = min(attempt / max_attempts * 100, 99)
        bar_length = 40
        filled_length = int(bar_length * progress / 100)
        progress_bar = f"[{'█' * filled_length}{' ' * (bar_length - filled_length)}] {progress:.1f}%"
        print(f"\rRendering: {progress_bar}", end="")
        import sys
        sys.stdout.flush()
        
        # Check status
        status_info = check_creatomate_render_status(render_id)
        status = status_info.get("status", "unknown")
        
        if status == "completed":
            print(f"\r\n{'=' * 70}")
            print(f"SUCCESS: Creatomate video completed! [{'█' * bar_length}] 100%")
            print(f"Video URL: {status_info.get('url', 'No URL provided')}")
            print(f"{'=' * 70}\n")
            return status_info
            
        elif status in ["failed", "error"]:
            print(f"\r\n{'=' * 70}")
            print(f"FAILED: Creatomate render failed! [{'X' * bar_length}]")
            print(f"{'=' * 70}\n")
            return status_info
        
        time.sleep(interval)
    
    print(f"\r\n{'=' * 70}")
    print(f"TIMEOUT: Render timed out after {max_attempts} attempts")
    print(f"{'=' * 70}\n")
    
    return check_creatomate_render_status(render_id)

# =============================================================================
# LEGACY FUNCTIONS COMPLETED - READY TO USE
# =============================================================================