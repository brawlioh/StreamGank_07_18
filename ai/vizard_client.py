"""
StreamGank Vizard.ai Integration Client

This module provides intelligent video clipping capabilities using Vizard.ai's API
to extract highlight clips from movie trailers. It replaces the traditional 
YouTube downloading and FFmpeg processing approach with AI-powered content extraction.

Features:
- AI-powered video clip extraction
- Intelligent highlight detection
- Multiple clip durations support
- Subtitle and headline generation
- High-quality output optimized for social media

Author: StreamGank Development Team
Version: 1.0.0 - Vizard.ai Integration
"""

import os
import logging
import time
import requests
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import configuration and utilities
from config.settings import get_api_config, get_video_settings
from utils.validators import is_valid_url
from utils.file_utils import ensure_directory, cleanup_temp_files

logger = logging.getLogger(__name__)

# =============================================================================
# VIZARD.AI CLIENT CONFIGURATION
# =============================================================================

class VizardClient:
    """
    Vizard.ai API client for intelligent video clipping.
    
    This class handles all interactions with Vizard.ai's API for processing
    movie trailers into optimized highlight clips using AI-powered analysis.
    """
    
    def __init__(self):
        """Initialize Vizard client with API configuration."""
        self.api_key = self._get_api_key()
        self.base_url = "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1"
        self.headers = {
            "Content-Type": "application/json",
            "VIZARDAI_API_KEY": self.api_key
        }
        
        # Get video settings for clip preferences
        video_settings = get_video_settings()
        self.preferred_duration = video_settings.get('clip_duration', 15)  # 15 seconds for highlights
        self.enable_subtitles = video_settings.get('enable_subtitles', True)
        self.enable_headlines = video_settings.get('enable_headlines', True)
        
        logger.info("🤖 Vizard.ai client initialized")
        logger.info(f"   Preferred clip duration: {self.preferred_duration}s")
        logger.info(f"   Subtitles: {'Enabled' if self.enable_subtitles else 'Disabled'}")
        logger.info(f"   Headlines: {'Enabled' if self.enable_headlines else 'Disabled'}")
    
    def _get_api_key(self) -> str:
        """
        Get Vizard.ai API key from environment or config.
        
        Returns:
            str: API key for Vizard.ai
            
        Raises:
            ValueError: If API key is not found
        """
        # Try environment variable first
        api_key = os.getenv('VIZARD_API_KEY')
        
        # Try config file as fallback
        if not api_key:
            api_config = get_api_config('vizard')
            if api_config:
                api_key = api_config.get('api_key')
        
        if not api_key:
            raise ValueError(
                "Vizard.ai API key not found. Please set VIZARD_API_KEY environment variable "
                "or configure it in your API settings."
            )
        
        return api_key
    
    def create_project(self, video_url: str, movie_title: str, template_id: Optional[str] = None, 
                      language: str = "auto") -> Optional[str]:
        """
        Submit a video to Vizard.ai for processing with optimized StreamGank settings.
        
        Uses advanced Vizard.ai configuration for high-quality social media clips:
        - 9:16 vertical format (ratioOfClip: 1) 
        - Automatic silence removal (removeSilenceSwitch: 1)
        - Highlight keywords in subtitles (highlightSwitch: 1)
        - 15-20 second preferred length (preferLength: 1)
        - Automatic language detection (lang: auto)
        
        Args:
            video_url (str): URL of the video to process (YouTube, direct video file, etc.)
            movie_title (str): Title of the movie for project naming
            template_id (Optional[str]): Custom template ID for branding (optional)
            language (str): Language code for video processing (default: "auto")
            
        Returns:
            str: Project ID if successful, None if failed
        """
        try:
            # Validate video URL
            if not is_valid_url(video_url):
                logger.error(f"❌ Invalid video URL: {video_url}")
                return None
            
            # Determine video file extension from URL
            video_ext = self._extract_video_extension(video_url)
            
            # Create project payload with StreamGank optimized settings
            payload = {
                "lang": language,                    # "auto" for automatic language detection
                "videoUrl": video_url,
                "ext": video_ext,
                "videoType": 1,                      # Video type 1 as specified
                "preferLength": [1],                 # Length code 1 for 15-20 second clips
                "ratioOfClip": 1,                   # 9:16 vertical format (TikTok/Instagram)
                "removeSilenceSwitch": 0,           # Remove silence and filler words
                "highlightSwitch": 1,               # Enable auto highlight keywords in subtitles
                "maxClipNumber": 1,                 # Return only the best clip (speeds up processing)
                "projectName": f"StreamGank - {movie_title}",
                "subtitleSwitch": 1 if self.enable_subtitles else 0,
                "headlineSwitch": 1 if self.enable_headlines else 0
            }
            
            # Add template ID if provided
            if template_id:
                payload["templateId"] = template_id
                logger.info(f"   Using custom template ID: {template_id}")
            
            logger.info(f"🎬 Submitting video to Vizard.ai with optimized settings: {movie_title}")
            logger.info(f"   Video URL: {video_url}")
            logger.info(f"   Language: {language} (auto-detect)")
            logger.info(f"   Extension: {video_ext}")
            logger.info(f"   📱 Format: 9:16 vertical (ratioOfClip: 1)")
            logger.info(f"   🎯 Length: 15-20 seconds (preferLength: 1)")
            logger.info(f"   🔇 Silence removal: Enabled")
            logger.info(f"   ✨ Highlight keywords: Enabled")
            logger.info(f"   🎬 Max clips: 1 (best clip only)")
            
            # Send request to Vizard.ai
            response = requests.post(
                f"{self.base_url}/project/create",
                json=payload,
                headers=self.headers,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract project ID
            project_id = result.get('data', {}).get('projectId')
            if project_id:
                logger.info(f"✅ Successfully created Vizard project: {project_id}")
                return project_id
            else:
                logger.error(f"❌ No project ID returned from Vizard.ai: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP error creating Vizard project: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error creating Vizard project for {movie_title}: {str(e)}")
            return None
    
    def get_project_clips(self, project_id: str, max_wait_time: int = 300) -> Optional[List[Dict]]:
        """
        Poll Vizard.ai project until clips are ready and retrieve them.
        
        Args:
            project_id (str): Project ID from create_project
            max_wait_time (int): Maximum wait time in seconds (default: 5 minutes)
            
        Returns:
            List[Dict]: List of clip data with download URLs, None if failed
        """
        try:
            logger.info(f"⏳ Waiting for Vizard.ai to process project: {project_id}")
            logger.info(f"   Max wait time: {max_wait_time}s")
            
            start_time = time.time()
            poll_interval = 30  # Poll every 30 seconds
            
            while time.time() - start_time < max_wait_time:
                # Query project status
                response = requests.get(
                    f"{self.base_url}/project/query/{project_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Check if processing is complete
                status = result.get('status', 'unknown')
                logger.info(f"   Project status: {status}")
                
                if status == 'completed' or result.get('data', {}).get('clips'):
                    clips = result.get('data', {}).get('clips', [])
                    if clips:
                        logger.info(f"🎉 Vizard.ai processing complete! Found {len(clips)} clips")
                        return clips
                
                elif status == 'failed' or status == 'error':
                    logger.error(f"❌ Vizard.ai processing failed for project: {project_id}")
                    return None
                
                # Wait before next poll
                logger.info(f"   Still processing... waiting {poll_interval}s before next check")
                time.sleep(poll_interval)
            
            logger.warning(f"⏰ Timeout waiting for Vizard.ai project: {project_id}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP error querying Vizard project: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error querying Vizard project {project_id}: {str(e)}")
            return None
    
    def download_clip(self, clip_url: str, output_path: str) -> bool:
        """
        Download a clip from Vizard.ai's generated URL.
        
        Args:
            clip_url (str): URL of the clip to download
            output_path (str): Local path to save the clip
            
        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            logger.info(f"📥 Downloading Vizard clip: {clip_url}")
            logger.info(f"   Output path: {output_path}")
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Download the clip with timeout and streaming
            response = requests.get(
                clip_url,
                headers={"User-Agent": "StreamGang/1.0"},
                stream=True,
                timeout=120
            )
            
            response.raise_for_status()
            
            # Write to file in chunks
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify download
            file_size = os.path.getsize(output_path)
            if file_size > 1000:  # At least 1KB
                logger.info(f"✅ Successfully downloaded clip ({file_size} bytes): {output_path}")
                return True
            else:
                logger.error(f"❌ Downloaded clip too small: {file_size} bytes")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP error downloading clip: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error downloading clip from {clip_url}: {str(e)}")
            return False
    
    def _extract_video_extension(self, video_url: str) -> str:
        """
        Extract video file extension from URL.
        
        Args:
            video_url (str): Video URL
            
        Returns:
            str: File extension (default: "mp4")
        """
        # Common video extensions
        extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        
        url_lower = video_url.lower()
        for ext in extensions:
            if ext in url_lower:
                return ext[1:]  # Return without the dot
        
        # Default to mp4 for YouTube and unknown formats
        return "mp4"


# =============================================================================
# MAIN INTEGRATION FUNCTIONS
# =============================================================================

def process_movie_trailers_with_vizard(movie_data: List[Dict], max_movies: int = 3, 
                                      transform_mode: str = "youtube_shorts",
                                      template_id: Optional[str] = None,
                                      use_intelligent_highlights: bool = True,
                                      review_mode: bool = False) -> Dict[str, str]:
    """
    Process movie trailers with intelligent pre-processing and optional Vizard.ai processing.
    
    Enhanced workflow with intelligent highlight extraction:
    1. Download high-quality video (1080p resolution)
    2. AI-powered analysis to find best 1:30 segment using multiple algorithms
    3. Extract intelligent highlight with optimal content
    4. Generate content-based keywords
    5. Process with Vizard.ai (OPTIONAL - can be skipped for review)
    
    Advanced Vizard.ai configuration features (when not in review mode):
    - 9:16 vertical format perfect for TikTok/Instagram
    - AI-powered silence removal and highlight detection  
    - Automatic language detection
    - 15-20 second optimal clip duration
    - Enhanced subtitle formatting with keyword highlights
    - Single best clip per video (maxClipNumber=1) for faster processing
    
    Args:
        movie_data (List[Dict]): List of movie data dictionaries with trailer_url
        max_movies (int): Maximum number of movies to process
        transform_mode (str): Transformation mode (maintained for compatibility)
        template_id (Optional[str]): Custom Vizard template ID for branding
        use_intelligent_highlights (bool): Enable intelligent highlight extraction (default: True)
        review_mode (bool): Skip Vizard.ai processing and save highlights locally (default: False)
        
    Returns:
        Dict[str, str]: Dictionary mapping movie titles to processed clip URLs or local paths
    """
    if review_mode:
        logger.info("📺 REVIEW MODE: Intelligent Highlights Only (Vizard.ai Skipped)")
        logger.info(f"📊 Processing {min(len(movie_data), max_movies)} movies for highlight review")
        logger.info(f"🧠 Intelligent highlight extraction: {'ENABLED' if use_intelligent_highlights else 'DISABLED'}")
        logger.info(f"🎯 Review workflow:")
        logger.info(f"   📥 1. Download 1080p video")
        logger.info(f"   🔍 2. Multi-algorithm content analysis") 
        logger.info(f"   ✂️  3. Extract best 1:30 segment")
        logger.info(f"   🏷️  4. Generate content keywords")
        logger.info(f"   💾 5. Save highlights locally")
        logger.info(f"   ⏸️  6. SKIP Vizard.ai processing")
    else:
        logger.info("🤖 Starting Enhanced Vizard.ai Processing with Intelligent Highlights")
        logger.info(f"📊 Processing {min(len(movie_data), max_movies)} movies")
        logger.info(f"🧠 Intelligent highlight extraction: {'ENABLED' if use_intelligent_highlights else 'DISABLED'}")
        
        if use_intelligent_highlights:
            logger.info(f"🎯 Enhanced workflow:")
            logger.info(f"   📥 1. Download 1080p video")
            logger.info(f"   🔍 2. Multi-algorithm content analysis") 
            logger.info(f"   ✂️  3. Extract best 1:30 segment")
            logger.info(f"   🏷️  4. Generate content keywords")
            logger.info(f"   🤖 5. Vizard.ai final processing")
        else:
            logger.info(f"🎯 Standard workflow: Direct Vizard.ai processing")
        
        logger.info(f"⚙️ Vizard.ai configuration:")
        logger.info(f"   📱 Format: 9:16 vertical (ratioOfClip: 1)")
        logger.info(f"   🎬 Length: 15-20s (preferLength: 1)")
        logger.info(f"   🎯 Max clips: 1 (best clip only)")
        logger.info(f"   🔇 Silence removal: Enabled")
        logger.info(f"   ✨ Keyword highlights: Enabled")
        logger.info(f"   🌍 Language: Auto-detect")
        if template_id:
            logger.info(f"   🎨 Custom template: {template_id}")
        else:
            logger.info(f"   🎨 Template: Default Vizard styling")
    
    clip_urls = {}
    temp_dir = "temp_vizard_clips"
    
    try:
        # Initialize Vizard client (skip in review mode)
        if not review_mode:
            vizard = VizardClient()
        else:
            vizard = None  # Skip Vizard initialization in review mode
        
        # Create temporary directory for clips
        ensure_directory(temp_dir)
        
        # Process each movie
        for i, movie in enumerate(movie_data[:max_movies]):
            try:
                title = movie.get('title', f'Movie_{i+1}')
                trailer_url = movie.get('trailer_url', '')
                
                logger.info(f"\n🎬 Processing Movie {i+1}/{min(len(movie_data), max_movies)}: {title}")
                
                if not trailer_url or not is_valid_url(trailer_url):
                    logger.warning(f"⚠️ No valid trailer URL for: {title}")
                    continue
                
                # Choose processing method based on intelligent highlights setting
                if use_intelligent_highlights:
                    # Use intelligent highlight extraction workflow
                    try:
                        from ai.intelligent_highlight_extractor import process_movie_with_intelligent_highlights
                        clip_url = process_movie_with_intelligent_highlights(
                            movie, transform_mode, template_id, review_mode
                        )
                    except ImportError as e:
                        logger.error(f"❌ Intelligent highlight extractor not available: {str(e)}")
                        logger.info(f"   Falling back to standard processing for: {title}")
                        # Fallback to standard processing (only if not in review mode)
                        if not review_mode:
                            clip_url = _process_movie_with_vizard(
                                vizard, movie, trailer_url, temp_dir, i+1, transform_mode, template_id
                            )
                        else:
                            logger.error(f"   Cannot fallback in review mode (no Vizard.ai available)")
                            clip_url = None
                else:
                    # Use standard Vizard processing (only if not in review mode)
                    if not review_mode:
                        clip_url = _process_movie_with_vizard(
                            vizard, movie, trailer_url, temp_dir, i+1, transform_mode, template_id
                        )
                    else:
                        logger.warning(f"   ⚠️ Review mode enabled but intelligent highlights disabled - skipping")
                        clip_url = None
                
                if clip_url:
                    clip_urls[title] = clip_url
                    logger.info(f"✅ Successfully processed {title}")
                else:
                    logger.error(f"❌ Failed to process {title}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing movie {i+1}: {str(e)}")
                continue
        
        # Cleanup temporary files
        cleanup_temp_files(temp_dir)
        
        # Report results
        successful_count = len(clip_urls)
        total_attempted = min(len(movie_data), max_movies)
        
        processing_method = "Intelligent Highlight Processing" if use_intelligent_highlights else "Standard Vizard Processing"
        
        if successful_count == total_attempted:
            logger.info(f"🎉 Perfect! {processing_method} completed successfully!")
            logger.info(f"   📊 Processed: {successful_count}/{total_attempted} movies")
            if use_intelligent_highlights:
                logger.info(f"   🧠 Each video analyzed with multi-algorithm intelligence")
                logger.info(f"   📥 1080p downloads and 1:30s optimal extractions")
                logger.info(f"   💾 Intelligent highlights saved for review")
                logger.info(f"")
                logger.info(f"   📁 CHECK YOUR INTELLIGENT HIGHLIGHTS:")
                logger.info(f"      📂 Location: intelligent_highlights_output/ folder")
                logger.info(f"      🎬 Files: INTELLIGENT_HIGHLIGHT_[movie]_[timerange].mp4")
                logger.info(f"      ⏰ Duration: 90 seconds (1:30) each")
                logger.info(f"      📺 Review these before enabling Vizard.ai processing")
        elif successful_count > 0:
            logger.warning(f"⚠️ Partial success: {successful_count}/{total_attempted} movies processed")
            if use_intelligent_highlights:
                logger.info("   Some videos may require different analysis parameters")
                logger.info(f"   📁 Check intelligent_highlights_output/ for successful extractions")
            else:
                logger.info("   Some videos may have processing limitations - this is normal")
        else:
            logger.error(f"❌ No movies could be processed ({successful_count}/{total_attempted})")
            if use_intelligent_highlights:
                logger.error("   Check video dependencies (FFmpeg, OpenCV, moviepy) and API access")
            else:
                logger.error("   Check API key and video URL accessibility")
        
        return clip_urls
        
    except Exception as e:
        logger.error(f"❌ Critical error in Vizard.ai processing: {str(e)}")
        cleanup_temp_files(temp_dir)
        return {}


def _process_movie_with_vizard(vizard: VizardClient, movie_data: Dict, trailer_url: str,
                              temp_dir: str, movie_num: int, transform_mode: str, 
                              template_id: Optional[str] = None) -> Optional[str]:
    """
    Process a single movie using Vizard.ai's intelligent clipping with optimized settings.
    
    Args:
        vizard (VizardClient): Initialized Vizard client
        movie_data (Dict): Movie information
        trailer_url (str): URL of the trailer video  
        temp_dir (str): Temporary directory for files
        movie_num (int): Movie number for naming
        transform_mode (str): Transformation mode
        template_id (Optional[str]): Custom template ID for branding
        
    Returns:
        str: Cloudinary URL of processed clip or None if failed
    """
    try:
        title = movie_data.get('title', f'Movie_{movie_num}')
        movie_id = str(movie_data.get('id', movie_num))
        
        logger.info(f"🎯 Processing with Vizard.ai: {title}")
        logger.info(f"   Trailer URL: {trailer_url}")
        
        # Step 1: Create Vizard project with optimized settings
        project_id = vizard.create_project(trailer_url, title, template_id)
        if not project_id:
            logger.error(f"❌ Failed to create Vizard project for: {title}")
            return None
        
        # Step 2: Wait for processing and get clips
        clips = vizard.get_project_clips(project_id)
        if not clips:
            logger.error(f"❌ No clips generated by Vizard for: {title}")
            return None
        
        # Step 3: Select best clip (first one, or by criteria)
        best_clip = _select_best_clip(clips, title)
        if not best_clip:
            logger.error(f"❌ No suitable clip found for: {title}")
            return None
        
        # Step 4: Download the selected clip
        clip_download_url = best_clip.get('downloadUrl', best_clip.get('videoUrl'))
        if not clip_download_url:
            logger.error(f"❌ No download URL in clip data for: {title}")
            return None
        
        # Create temporary file path for downloaded clip
        temp_clip_path = os.path.join(temp_dir, f"{movie_id}_{title.replace(' ', '_')}.mp4")
        
        # Download clip from Vizard
        if not vizard.download_clip(clip_download_url, temp_clip_path):
            logger.error(f"❌ Failed to download clip for: {title}")
            return None
        
        # Step 5: Upload to Cloudinary (reuse existing function)
        from video.clip_processor import _upload_clip_to_cloudinary
        
        cloudinary_url = _upload_clip_to_cloudinary(temp_clip_path, title, movie_id, transform_mode)
        
        if cloudinary_url:
            logger.info(f"✅ Vizard.ai processing complete for {title}: {cloudinary_url}")
            
            # Log clip metadata
            clip_title = best_clip.get('title', 'N/A')
            clip_duration = best_clip.get('duration', 'N/A')
            logger.info(f"   📊 Clip: '{clip_title}' ({clip_duration}s)")
            
            return cloudinary_url
        else:
            logger.error(f"❌ Failed to upload Vizard clip to Cloudinary: {title}")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error processing {title} with Vizard: {str(e)}")
        return None


def _select_best_clip(clips: List[Dict], movie_title: str) -> Optional[Dict]:
    """
    Select the best clip from Vizard.ai results.
    
    With maxClipNumber=1, we expect only one clip, but this function
    handles edge cases where multiple clips might be returned.
    
    Args:
        clips (List[Dict]): List of clips from Vizard.ai (should be 1 clip)
        movie_title (str): Movie title for logging
        
    Returns:
        Dict: Best clip data or None if no suitable clip
    """
    try:
        if not clips:
            return None
        
        # With maxClipNumber=1, we should only get one clip
        if len(clips) == 1:
            clip = clips[0]
            clip_title = clip.get('title', 'AI-Generated Clip')
            clip_duration = clip.get('duration', 'Unknown')
            logger.info(f"🎯 Using AI-selected best clip for {movie_title}")
            logger.info(f"   📺 Title: '{clip_title}' ({clip_duration}s)")
            return clip
        
        # Fallback: Multiple clips returned (shouldn't happen with maxClipNumber=1)
        logger.warning(f"⚠️ Expected 1 clip but got {len(clips)} for {movie_title}")
        
        # Select first clip as fallback
        best_clip = clips[0]
        selected_title = best_clip.get('title', 'Selected clip')
        selected_duration = best_clip.get('duration', 'Unknown')
        logger.info(f"✅ Using first clip: '{selected_title}' ({selected_duration}s)")
        
        return best_clip
        
    except Exception as e:
        logger.error(f"❌ Error selecting clip: {str(e)}")
        return clips[0] if clips else None


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def validate_vizard_requirements() -> Dict[str, Any]:
    """
    Validate that Vizard.ai integration requirements are met.
    
    Returns:
        Dict[str, Any]: Validation results
    """
    validation = {
        'ready': True,
        'missing_requirements': [],
        'warnings': []
    }
    
    try:
        # Check API key
        try:
            client = VizardClient()
            validation['api_key_found'] = True
        except ValueError as e:
            validation['ready'] = False
            validation['missing_requirements'].append(str(e))
            validation['api_key_found'] = False
        
        # Check internet connectivity (basic test)
        try:
            response = requests.get("https://www.google.com", timeout=5)
            validation['internet_available'] = True
        except:
            validation['warnings'].append('Internet connectivity may be limited')
            validation['internet_available'] = False
        
        # Check temp directory access
        try:
            ensure_directory("temp_vizard_clips")
            validation['temp_dir_writable'] = True
        except Exception as e:
            validation['ready'] = False
            validation['missing_requirements'].append(f'Cannot create temp directory: {str(e)}')
            validation['temp_dir_writable'] = False
        
        return validation
        
    except Exception as e:
        validation['ready'] = False
        validation['missing_requirements'].append(f'Validation error: {str(e)}')
        return validation


def get_vizard_processing_stats() -> Dict[str, Any]:
    """
    Get Vizard.ai processing statistics and configuration info.
    
    Returns:
        Dict[str, Any]: Statistics and configuration
    """
    try:
        stats = {
            'client_available': False,
            'api_configured': False,
            'last_error': None
        }
        
        # Try to initialize client
        try:
            client = VizardClient()
            stats['client_available'] = True
            stats['api_configured'] = True
            stats['preferred_duration'] = client.preferred_duration
            stats['subtitles_enabled'] = client.enable_subtitles
            stats['headlines_enabled'] = client.enable_headlines
        except Exception as e:
            stats['last_error'] = str(e)
        
        # Get video settings
        try:
            video_settings = get_video_settings()
            stats['video_settings'] = {
                'clip_duration': video_settings.get('clip_duration', 15),
                'enable_subtitles': video_settings.get('enable_subtitles', True),
                'enable_headlines': video_settings.get('enable_headlines', True)
            }
        except Exception as e:
            if not stats['last_error']:
                stats['last_error'] = f'Settings error: {str(e)}'
        
        return stats
        
    except Exception as e:
        return {
            'client_available': False,
            'api_configured': False,
            'last_error': str(e)
        }
