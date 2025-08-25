"""
Intelligent Video Highlight Extractor for StreamGank

This module provides AI-powered highlight detection from movie trailers using 
advanced algorithms to identify the most engaging 1:30 segments before sending 
to Vizard.ai for final processing.

Features:
- Smart video downloading at 1080p resolution
- Multi-algorithm highlight detection (audio peaks, visual changes, motion)
- Content-based keyword generation
- Intelligent scene boundary detection
- Quality optimization for Vizard.ai processing

Author: StreamGank Development Team
Version: 1.0.0 - Intelligent Pre-Processing
"""

import os
import logging
import subprocess
import tempfile
import json
import re
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import numpy as np
import cv2
import librosa
import yt_dlp
from moviepy.editor import VideoFileClip
import requests

from config.settings import get_video_settings
from utils.validators import is_valid_url
from utils.file_utils import ensure_directory, cleanup_temp_files
# Note: OpenAI integration can be added for advanced keyword generation

logger = logging.getLogger(__name__)

# =============================================================================
# INTELLIGENT VIDEO ANALYSIS
# =============================================================================

class IntelligentHighlightExtractor:
    """
    Advanced highlight extraction using multiple AI algorithms.
    
    Combines audio analysis, visual change detection, motion analysis,
    and content understanding to find the most engaging video segments.
    """
    
    def __init__(self):
        """Initialize the intelligent extractor with optimized settings."""
        video_settings = get_video_settings()
        
        self.target_duration = 90  # 1:30 seconds as requested
        self.analysis_window = 10   # Analyze in 10-second windows
        self.download_quality = "1080p"  # High quality as requested
        self.temp_dir = "temp_intelligent_highlights"
        
        # Algorithm weights for scoring
        self.weights = {
            'audio_energy': 0.25,    # High-energy audio (action, music)
            'visual_change': 0.25,   # Scene changes and cuts
            'motion_intensity': 0.20, # Movement and action
            'face_detection': 0.15,  # Human faces (dialogue, emotions)
            'color_variance': 0.10,  # Visual richness
            'temporal_position': 0.05 # Slight preference for middle sections
        }
        
        logger.info("🧠 Intelligent Highlight Extractor initialized")
        logger.info(f"   🎯 Target duration: {self.target_duration}s (1:30)")
        logger.info(f"   📺 HIGH QUALITY MODE: 1080p priority → 720p fallback")
        logger.info(f"   🔍 Analysis window: {self.analysis_window}s")
        logger.info(f"   ⚠️  Process will FAIL if neither 1080p nor 720p is available")
    
    def download_high_quality_video(self, video_url: str, movie_title: str) -> Optional[str]:
        """
        Download video at 1080p resolution with robust retry mechanism.
        
        Features:
        - Multiple download strategies with exponential backoff
        - Anti-bot detection with randomized delays and user agents
        - Fallback format selections for different scenarios
        - Comprehensive error handling and recovery
        
        Args:
            video_url (str): YouTube or direct video URL
            movie_title (str): Movie title for file naming
            
        Returns:
            str: Path to downloaded video file or None if failed
        """
        ensure_directory(self.temp_dir)
        
        # Clean title for filename
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', movie_title)
        clean_title = re.sub(r'_+', '_', clean_title).strip('_')
        
        logger.info(f"📥 Starting robust download with retry system: {movie_title}")
        logger.info(f"   URL: {video_url}")
        logger.info(f"   Quality: {self.download_quality} (1080p priority → 720p fallback)")
        logger.info(f"   🔄 Will use multiple strategies with exponential backoff")
        
        # Multiple download strategies - each with different approaches to avoid bot detection
        strategies = self._get_download_strategies(clean_title)
        
        max_attempts = len(strategies)
        base_delay = 2  # Base delay in seconds
        
        for attempt in range(max_attempts):
            strategy_name = strategies[attempt]['name']
            ydl_opts = strategies[attempt]['config']
            
            try:
                logger.info(f"🔄 ATTEMPT {attempt + 1}/{max_attempts}: Using {strategy_name} strategy")
                
                # Add randomized delay to avoid pattern detection (except first attempt)
                if attempt > 0:
                    # Exponential backoff with jitter: 2s, 5-7s, 12-16s, 25-35s
                    delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay * attempt)
                    logger.info(f"   ⏳ Anti-bot delay: {delay:.1f}s (exponential backoff + jitter)")
                    time.sleep(delay)
                
                # Attempt download with this strategy
                logger.info(f"   🎯 Format strategy: {ydl_opts.get('format', 'default')}")
                logger.info(f"   🕷️ User agent: {ydl_opts['http_headers']['User-Agent'][:50]}...")
                
                # Execute download
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                
                # Check for successful download
                downloaded_file = self._find_downloaded_file(clean_title)
                if downloaded_file:
                    # Validate the download
                    validation_result = self._validate_downloaded_video(downloaded_file, movie_title)
                    if validation_result:
                        logger.info(f"🎉 SUCCESS! Download completed with {strategy_name} strategy")
                        logger.info(f"   ⚡ Succeeded on attempt {attempt + 1}/{max_attempts}")
                        return validation_result
                    else:
                        logger.warning(f"   ⚠️ Downloaded file failed validation, trying next strategy...")
                        # Clean up failed file
                        try:
                            os.remove(downloaded_file)
                        except:
                            pass
                else:
                    logger.warning(f"   ❌ No file downloaded with {strategy_name} strategy")
                    
            except Exception as e:
                error_str = str(e).lower()
                logger.warning(f"   ❌ {strategy_name} strategy failed: {str(e)[:100]}...")
                
                # Analyze error for specific handling
                if "sign in to confirm" in error_str or "bot" in error_str:
                    logger.warning(f"   🤖 Bot detection encountered - will use more conservative approach")
                elif "403" in error_str or "forbidden" in error_str:
                    logger.warning(f"   🚫 HTTP 403 errors - formats may be geo-restricted or rate-limited")
                elif "not available" in error_str:
                    logger.warning(f"   📵 Video unavailable error - may be temporary")
                
                # Continue to next strategy unless it's the last attempt
                if attempt < max_attempts - 1:
                    logger.info(f"   🔄 Will try next strategy after delay...")
                else:
                    logger.error(f"   ❌ All {max_attempts} strategies exhausted")
        
        # All strategies failed
        logger.error(f"❌ DOWNLOAD FAILURE: All {max_attempts} download strategies failed for: {movie_title}")
        logger.error(f"   🚫 This indicates either:")
        logger.error(f"      • Strong bot detection measures active")
        logger.error(f"      • Video geo-restricted or temporarily unavailable") 
        logger.error(f"      • All high-quality formats (720p+) are blocked")
        logger.error(f"      • Network/connectivity issues")
        logger.error(f"")
        logger.error(f"   💡 SUGGESTIONS:")
        logger.error(f"      • Check video is publicly available in your region")
        logger.error(f"      • Verify network connectivity") 
        logger.error(f"      • Try again later (YouTube sometimes lifts restrictions)")
        logger.error(f"      • Set YOUTUBE_COOKIES environment variable for production")
        
        return None
    
    def _get_download_strategies(self, clean_title: str) -> List[Dict]:
        """
        Get multiple download strategies with different approaches to avoid bot detection.
        
        Each strategy uses different:
        - User agents (rotating between browsers/OS)
        - Format selection approaches 
        - Headers and request patterns
        - Retry and delay settings
        
        Args:
            clean_title (str): Cleaned movie title for filename
            
        Returns:
            List[Dict]: List of strategy configurations for yt-dlp
        """
        # Get YouTube cookies if available
        youtube_cookies = os.getenv('YOUTUBE_COOKIES', '')
        
        # Multiple user agents to rotate through (different browsers/OS combinations)
        user_agents = [
            # Chrome on Windows (primary)
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Firefox on Windows 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        strategies = []
        
        # Strategy 1: AGGRESSIVE HIGH QUALITY - Try for best possible quality first
        base_headers = {'User-Agent': user_agents[0]}
        if youtube_cookies:
            base_headers['Cookie'] = youtube_cookies
        
        strategies.append({
            'name': 'Aggressive High Quality',
            'config': {
                'format': 'bestvideo[height>=1080]+bestaudio/best[height>=1080]/bestvideo[height>=720]+bestaudio/best[height>=720]',
                'outtmpl': os.path.join(self.temp_dir, f'{clean_title}_high_quality.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
                'writeinfojson': False,
                'format_sort': ['res:1080', 'res:720', 'br', 'ext:mp4:webm', 'fps'],
                'http_headers': base_headers.copy(),
                'extractor_retries': 3,
                'retries': 3,
                'sleep_interval': 1,
                'max_sleep_interval': 4,
            }
        })
        
        # Strategy 2: CONSERVATIVE QUALITY - More compatible format selection
        conservative_headers = {'User-Agent': user_agents[1]}
        if youtube_cookies:
            conservative_headers['Cookie'] = youtube_cookies
            
        strategies.append({
            'name': 'Conservative Quality',
            'config': {
                'format': 'best[height>=720]/best[height>=480]',  # Broader quality range
                'outtmpl': os.path.join(self.temp_dir, f'{clean_title}_conservative.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
                'writeinfojson': False,
                'http_headers': conservative_headers.copy(),
                'extractor_retries': 2,  # Fewer retries to avoid detection
                'retries': 2,
                'sleep_interval': 2,     # Longer delays
                'max_sleep_interval': 6,
                'geo_bypass': True,      # Try to bypass geo-restrictions
            }
        })
        
        # Strategy 3: STEALTH MODE - Minimal footprint to avoid bot detection  
        stealth_headers = {
            'User-Agent': user_agents[2],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        if youtube_cookies:
            stealth_headers['Cookie'] = youtube_cookies
            
        strategies.append({
            'name': 'Stealth Mode',
            'config': {
                'format': 'worstvideo[height>=720]+worstaudio/worst[height>=720]',  # Less suspicious
                'outtmpl': os.path.join(self.temp_dir, f'{clean_title}_stealth.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
                'writeinfojson': False,
                'http_headers': stealth_headers.copy(),
                'extractor_retries': 1,  # Minimal retries
                'retries': 1,
                'sleep_interval': 3,     # Longer delays between requests
                'max_sleep_interval': 8,
                'extract_flat': False,   # Full extraction but conservative
            }
        })
        
        # Strategy 4: FALLBACK MODE - Last resort with maximum compatibility
        fallback_headers = {'User-Agent': user_agents[3]}
        if youtube_cookies:
            fallback_headers['Cookie'] = youtube_cookies
            
        strategies.append({
            'name': 'Fallback Mode',
            'config': {
                'format': 'best',  # Take whatever is available
                'outtmpl': os.path.join(self.temp_dir, f'{clean_title}_fallback.%(ext)s'),
                'quiet': False,  # Show more output for debugging
                'no_warnings': False,
                'merge_output_format': 'mp4',
                'writeinfojson': False,
                'http_headers': fallback_headers.copy(),
                'extractor_retries': 5,  # More aggressive retries as last resort
                'retries': 5,
                'sleep_interval': 4,
                'max_sleep_interval': 10,
                'ignore_errors': True,   # Continue despite errors
            }
        })
        
        # Randomize strategy order (except keep fallback last)
        main_strategies = strategies[:-1]
        random.shuffle(main_strategies)
        strategies = main_strategies + [strategies[-1]]  # Keep fallback last
        
        logger.info(f"   🔄 Prepared {len(strategies)} download strategies:")
        for i, strategy in enumerate(strategies, 1):
            logger.info(f"      {i}. {strategy['name']}")
        
        return strategies
    
    def _find_downloaded_file(self, clean_title: str) -> Optional[str]:
        """Find the downloaded video file in the temp directory."""
        try:
            for file in os.listdir(self.temp_dir):
                if clean_title in file and file.endswith(('.mp4', '.webm', '.mkv')):
                    return os.path.join(self.temp_dir, file)
            return None
        except Exception:
            return None
    
    def _validate_downloaded_video(self, downloaded_path: str, movie_title: str) -> Optional[str]:
        """
        Validate downloaded video meets quality requirements.
        
        Args:
            downloaded_path (str): Path to downloaded video
            movie_title (str): Movie title for logging
            
        Returns:
            str: Path to valid video file or None if validation failed
        """
        try:
            if not os.path.exists(downloaded_path):
                logger.error(f"   ❌ Downloaded file does not exist: {downloaded_path}")
                return None
                
            file_size = os.path.getsize(downloaded_path)
            if file_size < 1024 * 1024:  # Less than 1MB
                logger.error(f"   ❌ Downloaded file too small: {file_size / 1024:.1f} KB")
                return None
            
            # Validate video resolution using FFmpeg
            resolution_info = self._get_video_resolution(downloaded_path)
            
            logger.info(f"   ✅ Downloaded file validation:")
            logger.info(f"      📁 File: {os.path.basename(downloaded_path)}")
            logger.info(f"      📊 Size: {file_size / (1024*1024):.1f} MB")
            logger.info(f"      📺 Resolution: {resolution_info}")
            
            # HIGH QUALITY validation - Accept 1080p or 720p only
            if resolution_info and "x" in resolution_info:
                try:
                    width_str, height_str = resolution_info.split("x")
                    width_int = int(width_str)
                    height_int = int(height_str)
                    
                    # Check for acceptable resolutions: 1080p (priority) or 720p (fallback)
                    is_1080p = (width_int == 1920 and height_int == 1080)
                    is_720p = (width_int == 1280 and height_int == 720)
                    
                    if not (is_1080p or is_720p):
                        logger.error(f"   ❌ HIGH QUALITY MODE FAILURE: Downloaded video is {resolution_info}")
                        logger.error(f"      Required: 1920x1080 (1080p) OR 1280x720 (720p)")  
                        logger.error(f"      Actual: {width_int}x{height_int} ({height_int}p)")
                        logger.error(f"      This video does not meet minimum quality requirements")
                        return None
                    elif is_1080p:
                        logger.info(f"   🎉 EXCELLENT! Downloaded in 1080p quality (1920x1080)")
                    else:  # is_720p
                        logger.info(f"   ✅ GOOD! Downloaded in 720p quality (1280x720) - meets requirements")
                        
                except ValueError as e:
                    logger.error(f"   ❌ Could not parse resolution '{resolution_info}': {str(e)}")
                    return None
            else:
                logger.error(f"   ❌ Could not validate video resolution: {resolution_info}")
                logger.error(f"      HIGH QUALITY MODE requires resolution validation")
                return None
            
            return downloaded_path
            
        except Exception as e:
            logger.error(f"   ❌ Video validation error: {str(e)}")
            return None
    
    def _get_video_resolution(self, video_path: str) -> str:
        """
        Get video resolution using FFmpeg.
        
        Args:
            video_path (str): Path to video file
            
        Returns:
            str: Resolution string (e.g., "1920x1080") or "unknown"
        """
        try:
            # Use FFprobe to get video resolution
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                resolution = result.stdout.strip()
                return resolution
            else:
                logger.debug(f"Could not get resolution for {video_path}")
                return "unknown"
                
        except Exception as e:
            logger.debug(f"Error getting video resolution: {str(e)}")
            return "unknown"
    
    def analyze_video_content(self, video_path: str) -> Dict[str, List[float]]:
        """
        Perform comprehensive video analysis using multiple algorithms.
        
        Args:
            video_path (str): Path to the video file
            
        Returns:
            Dict[str, List[float]]: Analysis results per time window
        """
        try:
            logger.info(f"🔍 Starting intelligent video analysis: {os.path.basename(video_path)}")
            
            # Load video for analysis
            clip = VideoFileClip(video_path)
            duration = clip.duration
            
            logger.info(f"   📊 Video duration: {duration:.1f}s")
            logger.info(f"   🎯 Analyzing in {self.analysis_window}s windows")
            
            # Initialize analysis results
            num_windows = int(duration // self.analysis_window)
            analysis = {
                'audio_energy': [],
                'visual_change': [],
                'motion_intensity': [],
                'face_detection': [],
                'color_variance': [],
                'temporal_position': []
            }
            
            logger.info(f"   🔬 Processing {num_windows} analysis windows...")
            
            # Analyze each time window
            for i in range(num_windows):
                start_time = i * self.analysis_window
                end_time = min((i + 1) * self.analysis_window, duration)
                
                logger.info(f"   Analyzing window {i+1}/{num_windows}: {start_time:.1f}s - {end_time:.1f}s")
                
                # Extract segment for analysis
                segment = clip.subclip(start_time, end_time)
                
                # Perform multi-algorithm analysis
                window_analysis = self._analyze_segment(segment, start_time, duration)
                
                # Store results
                for key, value in window_analysis.items():
                    analysis[key].append(value)
                
                # Clean up segment
                segment.close()
                
                # Progress indicator
                if (i + 1) % 5 == 0:
                    progress = ((i + 1) / num_windows) * 100
                    logger.info(f"   📈 Analysis progress: {progress:.1f}%")
            
            clip.close()
            
            logger.info(f"✅ Video analysis complete!")
            logger.info(f"   📊 Analyzed {len(analysis['audio_energy'])} segments")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing video content: {str(e)}")
            return {}
    
    def _analyze_segment(self, segment: VideoFileClip, start_time: float, total_duration: float) -> Dict[str, float]:
        """
        Analyze a single video segment using multiple algorithms.
        
        Args:
            segment (VideoFileClip): Video segment to analyze
            start_time (float): Start time in original video
            total_duration (float): Total video duration
            
        Returns:
            Dict[str, float]: Analysis scores for this segment
        """
        try:
            scores = {}
            
            # 1. Audio Energy Analysis
            try:
                if segment.audio:
                    # Safe audio extraction with error handling
                    try:
                        # Get audio data with fallback options
                        audio_array = segment.audio.to_soundarray(fps=22050)
                        
                        # Ensure we have a valid array
                        if audio_array is None or len(audio_array) == 0:
                            scores['audio_energy'] = 0.0
                        else:
                            # Handle stereo to mono conversion safely
                            if len(audio_array.shape) == 2 and audio_array.shape[1] > 1:
                                audio_array = np.mean(audio_array, axis=1)
                            elif len(audio_array.shape) > 2:
                                # Flatten complex audio structures
                                audio_array = audio_array.flatten()
                            
                            # Ensure we have a 1D array
                            audio_array = np.atleast_1d(audio_array)
                            
                            # Calculate RMS energy safely
                            if len(audio_array) > 0:
                                rms_energy = np.sqrt(np.mean(np.square(audio_array)))
                                scores['audio_energy'] = float(rms_energy * 1000)  # Scale for better comparison
                            else:
                                scores['audio_energy'] = 0.0
                                
                    except Exception as audio_error:
                        logger.debug(f"Audio processing error: {str(audio_error)}")
                        scores['audio_energy'] = 0.0
                else:
                    scores['audio_energy'] = 0.0
            except Exception as e:
                logger.debug(f"Audio energy analysis failed: {str(e)}")
                scores['audio_energy'] = 0.0
            
            # 2. Visual Change Detection
            try:
                # Safe frame extraction with timeout and limits
                frames = []
                max_frames = 30  # Limit to prevent memory issues
                try:
                    frame_count = 0
                    for frame in segment.iter_frames():
                        if frame is not None and frame_count < max_frames:
                            frames.append(frame)
                            frame_count += 1
                        else:
                            break
                except Exception as frame_error:
                    logger.debug(f"Frame extraction error: {str(frame_error)}")
                    frames = []  # Fallback to empty frames
                
                if len(frames) > 1:
                    visual_changes = []
                    for i in range(1, min(len(frames), 15)):  # Limit frames for performance
                        try:
                            # Ensure frames are valid numpy arrays
                            if frames[i-1] is None or frames[i] is None:
                                continue
                            
                            # Convert to grayscale and calculate difference
                            gray1 = cv2.cvtColor(frames[i-1], cv2.COLOR_RGB2GRAY)
                            gray2 = cv2.cvtColor(frames[i], cv2.COLOR_RGB2GRAY)
                            
                            # Ensure consistent shape
                            if gray1.shape != gray2.shape:
                                min_h = min(gray1.shape[0], gray2.shape[0])
                                min_w = min(gray1.shape[1], gray2.shape[1])
                                gray1 = gray1[:min_h, :min_w]
                                gray2 = gray2[:min_h, :min_w]
                            
                            diff = cv2.absdiff(gray1, gray2)
                            change_score = np.mean(diff)
                            visual_changes.append(change_score)
                            
                        except Exception as e:
                            logger.debug(f"Visual change analysis error for frame {i}: {str(e)}")
                            continue
                    
                    scores['visual_change'] = float(np.mean(visual_changes)) if visual_changes else 0.0
                else:
                    scores['visual_change'] = 0.0
            except Exception as e:
                logger.debug(f"Visual change detection failed: {str(e)}")
                scores['visual_change'] = 0.0
            
            # 3. Motion Intensity Analysis
            try:
                # Ensure we have frames available (fallback if visual detection failed)
                if 'frames' not in locals():
                    frames = list(segment.iter_frames())
                    
                if len(frames) > 2:
                    motion_scores = []
                    for i in range(1, min(len(frames), 10)):  # Limit processing for performance
                        try:
                            # Ensure frames are valid
                            if frames[i-1] is None or frames[i] is None:
                                continue
                                
                            # Optical flow analysis using dense flow
                            gray1 = cv2.cvtColor(frames[i-1], cv2.COLOR_RGB2GRAY)
                            gray2 = cv2.cvtColor(frames[i], cv2.COLOR_RGB2GRAY)
                            
                            # Ensure consistent shape
                            if gray1.shape != gray2.shape:
                                min_h = min(gray1.shape[0], gray2.shape[0])
                                min_w = min(gray1.shape[1], gray2.shape[1])
                                gray1 = gray1[:min_h, :min_w]
                                gray2 = gray2[:min_h, :min_w]
                            
                            # Resize frames for faster processing
                            h, w = gray1.shape[:2]
                            if h > 240:  # Resize large frames for performance
                                scale = 240 / h
                                new_w = int(w * scale)
                                gray1 = cv2.resize(gray1, (new_w, 240))
                                gray2 = cv2.resize(gray2, (new_w, 240))
                            
                            # Calculate dense optical flow using Farneback method
                            flow = cv2.calcOpticalFlowFarneback(
                                gray1, gray2, None, 
                                pyr_scale=0.5, levels=3, winsize=15, 
                                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
                            )
                            
                            # Validate flow result and calculate magnitude safely
                            if flow is not None and len(flow.shape) == 3 and flow.shape[2] == 2:
                                # Calculate flow magnitude safely
                                magnitude = np.sqrt(np.square(flow[:, :, 0]) + np.square(flow[:, :, 1]))
                                if magnitude.size > 0:
                                    motion_scores.append(float(np.mean(magnitude)))
                                else:
                                    logger.debug("Empty magnitude array from optical flow")
                            else:
                                logger.debug(f"Invalid optical flow result: {flow.shape if flow is not None else 'None'}")
                            
                        except Exception as e:
                            logger.debug(f"Motion analysis error for frame {i}: {str(e)}")
                            continue  # Skip this frame instead of adding 0.0
                    
                    scores['motion_intensity'] = float(np.mean(motion_scores)) if motion_scores else 0.0
                else:
                    scores['motion_intensity'] = 0.0
            except Exception as e:
                logger.debug(f"Motion intensity analysis failed: {str(e)}")
                scores['motion_intensity'] = 0.0
            
            # 4. Face Detection (indicates dialogue/character focus)
            try:
                # Ensure we have frames available
                if 'frames' not in locals():
                    frames = list(segment.iter_frames())
                    
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                face_count = 0
                
                # Sample frames for performance (every 5th frame, max 10 frames)
                sample_frames = frames[::5][:10]
                for frame in sample_frames:
                    try:
                        if frame is None:
                            continue
                        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                        face_count += len(faces)
                    except Exception as e:
                        logger.debug(f"Face detection error: {str(e)}")
                        continue
                
                scores['face_detection'] = float(face_count)
            except Exception as e:
                logger.debug(f"Face detection failed: {str(e)}")
                scores['face_detection'] = 0.0
            
            # 5. Color Variance (visual richness)
            try:
                # Ensure we have frames available
                if 'frames' not in locals():
                    frames = list(segment.iter_frames())
                    
                color_variances = []
                # Sample frames for performance (every 3rd frame, max 15 frames)
                sample_frames = frames[::3][:15]
                for frame in sample_frames:
                    try:
                        if frame is None:
                            continue
                        # Calculate color variance across channels
                        variance = np.var(frame, axis=(0, 1))  # Variance per color channel
                        if isinstance(variance, np.ndarray) and len(variance) > 0:
                            color_variances.append(np.mean(variance))
                    except Exception as e:
                        logger.debug(f"Color variance error: {str(e)}")
                        continue
                
                scores['color_variance'] = float(np.mean(color_variances)) if color_variances else 0.0
            except Exception as e:
                logger.debug(f"Color variance analysis failed: {str(e)}")
                scores['color_variance'] = 0.0
            
            # 6. Temporal Position Score (slight preference for middle sections)
            position_ratio = start_time / total_duration
            # Bell curve: peak at 0.5 (middle), lower at extremes
            temporal_score = 1.0 - abs(position_ratio - 0.5) * 2
            scores['temporal_position'] = temporal_score
            
            return scores
            
        except Exception as e:
            logger.error(f"❌ Error in segment analysis: {str(e)}")
            # Return zero scores on error
            return {
                'audio_energy': 0.0,
                'visual_change': 0.0, 
                'motion_intensity': 0.0,
                'face_detection': 0.0,
                'color_variance': 0.0,
                'temporal_position': 0.0
            }
    
    def find_best_highlight_segment(self, analysis: Dict[str, List[float]]) -> Tuple[int, int]:
        """
        Find the best 1:30 segment using weighted scoring algorithm.
        
        Args:
            analysis (Dict[str, List[float]]): Analysis results from analyze_video_content
            
        Returns:
            Tuple[int, int]: (start_time, end_time) in seconds for best segment
        """
        try:
            if not analysis or not analysis['audio_energy']:
                logger.warning("⚠️ No analysis data available, using default segment")
                return (30, 120)  # Fallback to 30s-2:00 segment
            
            num_windows = len(analysis['audio_energy'])
            segments_needed = self.target_duration // self.analysis_window  # 9 segments for 90 seconds
            
            logger.info(f"🎯 Finding best {self.target_duration}s highlight from {num_windows} windows")
            logger.info(f"   📊 Need {segments_needed} consecutive segments")
            
            # Normalize all scores to 0-1 range
            normalized_analysis = {}
            for metric, scores in analysis.items():
                if scores:
                    max_score = max(scores) if max(scores) > 0 else 1
                    normalized_analysis[metric] = [score / max_score for score in scores]
                else:
                    normalized_analysis[metric] = [0.0] * num_windows
            
            # Calculate combined scores for each possible segment start
            best_score = -1
            best_start_window = 0
            
            for start_window in range(num_windows - segments_needed + 1):
                # Calculate weighted score for this segment
                segment_score = 0.0
                
                for i in range(segments_needed):
                    window_index = start_window + i
                    
                    # Combine all metrics with weights
                    window_score = 0.0
                    for metric, weight in self.weights.items():
                        if metric in normalized_analysis:
                            window_score += normalized_analysis[metric][window_index] * weight
                    
                    segment_score += window_score
                
                # Average score for this segment
                segment_score /= segments_needed
                
                logger.debug(f"   Segment {start_window}-{start_window + segments_needed}: score = {segment_score:.3f}")
                
                if segment_score > best_score:
                    best_score = segment_score
                    best_start_window = start_window
            
            # Convert window indices to time
            start_time = best_start_window * self.analysis_window
            end_time = start_time + self.target_duration
            
            logger.info(f"✅ Best highlight segment identified:")
            logger.info(f"   ⏰ Time range: {start_time}s - {end_time}s")
            logger.info(f"   📊 Composite score: {best_score:.3f}")
            logger.info(f"   🎯 Duration: {end_time - start_time}s")
            
            # Log the winning factors
            self._log_segment_analysis(normalized_analysis, best_start_window, segments_needed)
            
            return (start_time, end_time)
            
        except Exception as e:
            logger.error(f"❌ Error finding best segment: {str(e)}")
            # Fallback to middle section
            return (30, 120)
    
    def _log_segment_analysis(self, normalized_analysis: Dict[str, List[float]], 
                             start_window: int, segments_needed: int) -> None:
        """Log detailed analysis of the selected segment."""
        try:
            logger.info(f"   📈 Winning segment analysis breakdown:")
            
            # Calculate average scores for each metric in the winning segment
            segment_metrics = {}
            for metric, scores in normalized_analysis.items():
                segment_scores = scores[start_window:start_window + segments_needed]
                avg_score = sum(segment_scores) / len(segment_scores) if segment_scores else 0
                segment_metrics[metric] = avg_score
            
            # Sort by contribution (score * weight)
            contributions = []
            for metric, avg_score in segment_metrics.items():
                weight = self.weights.get(metric, 0)
                contribution = avg_score * weight
                contributions.append((metric, avg_score, weight, contribution))
            
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            for metric, avg_score, weight, contribution in contributions:
                logger.info(f"     {metric}: {avg_score:.3f} (weight: {weight:.2f}) = {contribution:.3f}")
            
        except Exception as e:
            logger.debug(f"Error logging segment analysis: {str(e)}")
    
    def extract_highlight_segment(self, video_path: str, start_time: int, end_time: int, 
                                 movie_title: str) -> Optional[str]:
        """
        Extract the identified highlight segment from the video.
        
        Args:
            video_path (str): Path to the source video
            start_time (int): Start time in seconds
            end_time (int): End time in seconds  
            movie_title (str): Movie title for file naming
            
        Returns:
            str: Path to extracted highlight file or None if failed
        """
        try:
            # Clean title for filename
            clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', movie_title)
            clean_title = re.sub(r'_+', '_', clean_title).strip('_')
            
            # Create output filename with timestamp
            timestamp = int(time.time())
            output_filename = f"{clean_title}_highlight_{start_time}-{end_time}s_{timestamp}.mp4"
            output_path = os.path.join(self.temp_dir, output_filename)
            
            logger.info(f"✂️ Extracting highlight segment: {movie_title}")
            logger.info(f"   ⏰ Time: {start_time}s - {end_time}s ({end_time - start_time}s duration)")
            logger.info(f"   📁 Output: {output_path}")
            
            # Get source video resolution for quality preservation
            source_resolution = self._get_video_resolution(video_path)
            
            # Use FFmpeg for high-quality extraction with resolution preservation
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', video_path,                    # Input file
                '-ss', str(start_time),              # Start time
                '-t', str(end_time - start_time),    # Duration
                '-c:v', 'libx264',                   # Video codec
                '-c:a', 'aac',                       # Audio codec
                '-crf', '18',                        # High quality (lower = better)
                '-preset', 'medium',                 # Encoding speed vs compression
                '-profile:v', 'high',                # H.264 high profile
                '-level:v', '4.1',                   # H.264 level for 1080p
                '-movflags', '+faststart',           # Optimize for web streaming
                '-pix_fmt', 'yuv420p',              # Ensure compatibility
                '-vf', 'scale=-2:ih',               # Preserve original resolution and aspect ratio
                '-maxrate', '8000k',                 # Higher max bitrate for quality
                '-bufsize', '16000k',               # Larger buffer size
                '-g', '30',                          # GOP size for better quality
                '-keyint_min', '30',                # Minimum GOP size
                '-sc_threshold', '0',               # Disable scene cut detection
                '-b:a', '192k',                     # Higher audio bitrate
                '-y',                                # Overwrite output file
                output_path
            ]
            
            logger.info(f"   📺 Source resolution: {source_resolution}")
            logger.info(f"   🎯 Output will preserve quality up to 1080p")
            
            # Execute FFmpeg command
            logger.info("   🎬 Starting FFmpeg extraction...")
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                
                # Validate output resolution
                output_resolution = self._get_video_resolution(output_path)
                
                logger.info(f"✅ Highlight extracted successfully!")
                logger.info(f"   📊 Output size: {file_size / (1024*1024):.1f} MB")
                logger.info(f"   📺 Final resolution: {output_resolution}")
                
                # HIGH QUALITY output validation - Accept 1080p or 720p
                if output_resolution and "x" in output_resolution:
                    width_str, height_str = output_resolution.split("x")
                    width_int = int(width_str)
                    height_int = int(height_str)
                    
                    # Check for acceptable output resolutions: 1080p or 720p
                    is_1080p = (width_int == 1920 and height_int == 1080)
                    is_720p = (width_int == 1280 and height_int == 720)
                    
                    if not (is_1080p or is_720p):
                        logger.error(f"❌ HIGH QUALITY MODE FAILURE: Output video is {output_resolution}")
                        logger.error(f"   Required: 1920x1080 (1080p) OR 1280x720 (720p)")
                        logger.error(f"   Actual: {width_int}x{height_int} ({height_int}p)")
                        logger.error(f"   FFmpeg processing failed to maintain high quality")
                        
                        # Clean up the failed output file
                        try:
                            os.remove(output_path)
                            logger.info(f"   🗑️ Cleaned up low-quality output file")
                        except:
                            pass
                        
                        return None  # Fail the extraction process
                    elif is_1080p:
                        logger.info(f"🎉 EXCELLENT! Output is 1080p (1920x1080)")
                    else:  # is_720p
                        logger.info(f"✅ GOOD! Output is 720p (1280x720)")
                else:
                    logger.error(f"❌ Could not validate output video resolution")
                    logger.error(f"   HIGH QUALITY MODE requires output resolution validation")
                    
                    # Clean up unverified output
                    try:
                        os.remove(output_path)
                        logger.info(f"   🗑️ Cleaned up unverified output file")
                    except:
                        pass
                    
                    return None
                
                logger.info(f"   🎯 Ready for Vizard.ai processing")
                
                return output_path
            else:
                logger.error(f"❌ FFmpeg extraction failed:")
                logger.error(f"   Return code: {result.returncode}")
                logger.error(f"   Error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ FFmpeg extraction timeout for {movie_title}")
            return None
        except Exception as e:
            logger.error(f"❌ Error extracting highlight: {str(e)}")
            return None
    
    def generate_content_keywords(self, video_path: str, movie_title: str, 
                                 start_time: int, end_time: int) -> List[str]:
        """
        Generate content-based keywords for the extracted highlight.
        
        Args:
            video_path (str): Path to the highlight video
            movie_title (str): Original movie title
            start_time (int): Start time of highlight in original video
            end_time (int): End time of highlight in original video
            
        Returns:
            List[str]: Generated keywords related to the video content
        """
        try:
            logger.info(f"🏷️ Generating content keywords for highlight: {movie_title}")
            logger.info(f"   📺 Segment: {start_time}s - {end_time}s")
            
            # Base keywords from movie title
            title_words = re.findall(r'\b[A-Za-z]{3,}\b', movie_title.lower())
            keywords = [word.capitalize() for word in title_words if len(word) > 3]
            
            # Analyze video characteristics to generate contextual keywords
            try:
                # Load video for basic analysis
                clip = VideoFileClip(video_path)
                duration = clip.duration
                
                # Genre/mood keywords based on analysis patterns
                contextual_keywords = []
                
                # Quick frame sampling for visual analysis
                mid_point = duration / 2
                frame = clip.get_frame(mid_point)
                
                # Analyze average brightness and color
                avg_brightness = np.mean(frame)
                color_std = np.std(frame)
                
                # Generate keywords based on visual characteristics
                if avg_brightness < 100:
                    contextual_keywords.extend(["dark", "intense", "dramatic"])
                elif avg_brightness > 180:
                    contextual_keywords.extend(["bright", "vibrant", "dynamic"])
                else:
                    contextual_keywords.extend(["balanced", "cinematic"])
                
                if color_std > 50:
                    contextual_keywords.extend(["colorful", "vivid", "rich"])
                else:
                    contextual_keywords.extend(["muted", "stylized"])
                
                # Audio-based keywords
                try:
                    if clip.audio:
                        # Safe audio analysis for keyword generation
                        try:
                            # Extract short audio segment safely
                            audio_duration = min(10, duration)
                            audio_segment = clip.audio.subclip(0, audio_duration)
                            audio_array = audio_segment.to_soundarray(fps=22050)
                            
                            # Ensure we have valid audio data
                            if audio_array is not None and len(audio_array) > 0:
                                # Handle stereo to mono conversion safely
                                if len(audio_array.shape) == 2 and audio_array.shape[1] > 1:
                                    audio_array = np.mean(audio_array, axis=1)
                                elif len(audio_array.shape) > 2:
                                    # Flatten complex audio structures
                                    audio_array = audio_array.flatten()
                                
                                # Ensure we have a 1D array
                                audio_array = np.atleast_1d(audio_array)
                                
                                # Calculate audio energy safely
                                if len(audio_array) > 0:
                                    audio_energy = np.sqrt(np.mean(np.square(audio_array)))
                                    
                                    if audio_energy > 0.1:
                                        contextual_keywords.extend(["action", "energetic", "powerful"])
                                    elif audio_energy > 0.05:
                                        contextual_keywords.extend(["moderate", "dialogue"])
                                    else:
                                        contextual_keywords.extend(["quiet", "atmospheric"])
                                else:
                                    contextual_keywords.extend(["silent", "no-audio"])
                            else:
                                contextual_keywords.extend(["no-audio", "silent"])
                                
                        except Exception as audio_error:
                            logger.debug(f"Audio analysis error in keywords: {str(audio_error)}")
                            contextual_keywords.extend(["audio-processing-failed"])
                            
                except Exception as e:
                    logger.debug(f"Audio keyword analysis failed: {str(e)}")
                    # Continue without audio-based keywords
                
                # Duration-based keywords
                if duration >= 60:
                    contextual_keywords.extend(["extended", "comprehensive"])
                else:
                    contextual_keywords.extend(["highlight", "snippet"])
                
                # Position-based keywords  
                video_position = start_time / 300  # Assume ~5 min average trailer
                if video_position < 0.3:
                    contextual_keywords.extend(["opening", "introduction"])
                elif video_position > 0.7:
                    contextual_keywords.extend(["climax", "finale"])
                else:
                    contextual_keywords.extend(["middle", "development"])
                
                keywords.extend(contextual_keywords)
                clip.close()
                
            except Exception as e:
                logger.warning(f"⚠️ Advanced keyword analysis failed: {str(e)}")
                # Fallback to basic keywords
                contextual_keywords = ["trailer", "highlight", "cinema", "movie", "film"]
                keywords.extend(contextual_keywords)
            
            # Add universal movie/trailer keywords
            universal_keywords = [
                "trailer", "movie", "film", "cinema", "highlight", "preview",
                "entertainment", "Hollywood", "blockbuster", "exclusive"
            ]
            keywords.extend(universal_keywords)
            
            # Remove duplicates and limit to reasonable number
            unique_keywords = list(set(keywords))
            final_keywords = unique_keywords[:10]  # Limit to top 10 keywords
            
            logger.info(f"✅ Generated {len(final_keywords)} content keywords:")
            for i, keyword in enumerate(final_keywords, 1):
                logger.info(f"   {i}. {keyword}")
            
            return final_keywords
            
        except Exception as e:
            logger.error(f"❌ Error generating keywords: {str(e)}")
            # Return basic fallback keywords
            return ["movie", "trailer", "highlight", "cinema", "entertainment"]


# =============================================================================
# MAIN INTEGRATION FUNCTION
# =============================================================================

def process_movie_with_intelligent_highlights(movie_data: Dict, transform_mode: str = "youtube_shorts",
                                            template_id: Optional[str] = None, 
                                            review_mode: bool = False) -> Optional[str]:
    """
    Complete intelligent highlight processing workflow.
    
    This function implements the full pipeline:
    1. Download high-quality video (1080p)
    2. Intelligent analysis to find best 1:30 segment
    3. Extract the highlight segment  
    4. Generate content-based keywords
    5. Save locally for review OR process with Vizard.ai
    
    Args:
        movie_data (Dict): Movie information including trailer_url
        transform_mode (str): Transformation mode for final processing
        template_id (Optional[str]): Custom Vizard template ID
        review_mode (bool): If True, save highlights locally; if False, process with Vizard.ai
        
    Returns:
        str: Local file path (review mode) or Cloudinary URL (normal mode), None if failed
    """
    try:
        title = movie_data.get('title', 'Unknown Movie')
        trailer_url = movie_data.get('trailer_url', '')
        movie_id = str(movie_data.get('id', 'unknown'))
        
        if not trailer_url or not is_valid_url(trailer_url):
            logger.error(f"❌ Invalid trailer URL for: {title}")
            return None
        
        logger.info(f"🎬 Starting intelligent highlight processing: {title}")
        logger.info(f"   📺 Original trailer: {trailer_url}")
        
        # Initialize the intelligent extractor
        extractor = IntelligentHighlightExtractor()
        
        # Step 1: Download high-quality video (1080p priority, 720p fallback)
        logger.info("📥 STEP 1: Downloading high-quality video (1080p priority, 720p fallback)...")
        downloaded_video = extractor.download_high_quality_video(trailer_url, title)
        if not downloaded_video:
            logger.error(f"❌ HIGH QUALITY MODE FAILURE: Could not download high-quality video for: {title}")
            logger.error(f"   Possible reasons:")
            logger.error(f"   • Video is not available in 1080p OR 720p resolution")
            logger.error(f"   • High quality formats may be geo-restricted")
            logger.error(f"   • Video source may only have 480p or lower quality versions")
            logger.error(f"   ℹ️ HIGH QUALITY MODE requires minimum 720p (1280x720)")
            return None
        
        # Step 2: Intelligent content analysis
        logger.info("🧠 STEP 2: Performing intelligent content analysis...")
        analysis = extractor.analyze_video_content(downloaded_video)
        if not analysis:
            logger.error(f"❌ Failed to analyze video content for: {title}")
            return None
        
        # Step 3: Find best highlight segment
        logger.info("🎯 STEP 3: Finding best 1:30 highlight segment...")
        start_time, end_time = extractor.find_best_highlight_segment(analysis)
        
        # Step 4: Extract the highlight (HIGH QUALITY OUTPUT)
        logger.info("✂️ STEP 4: Extracting high-quality intelligent highlight segment...")
        highlight_path = extractor.extract_highlight_segment(
            downloaded_video, start_time, end_time, title
        )
        if not highlight_path:
            logger.error(f"❌ HIGH QUALITY MODE FAILURE: Could not extract high-quality highlight for: {title}")
            logger.error(f"   FFmpeg processing failed to maintain high quality (1080p/720p)")
            logger.error(f"   ℹ️ HIGH QUALITY MODE requires output to be 1080p or 720p minimum")
            return None
        
        # Step 5: Generate content keywords
        logger.info("🏷️ STEP 5: Generating content-based keywords...")
        keywords = extractor.generate_content_keywords(
            highlight_path, title, start_time, end_time
        )
        
        # Step 6: Process final output (review mode or Vizard.ai)
        if review_mode:
            # REVIEW MODE: Save intelligent highlight locally for review
            logger.info("💾 STEP 6: Saving intelligent highlight for review (Vizard.ai SKIPPED)...")
            
            # Create dedicated output folder for intelligent highlights
            output_dir = "intelligent_highlights_output"
            try:
                ensure_directory(output_dir)
            except Exception as e:
                logger.warning(f"⚠️ Could not create output directory: {str(e)}")
                output_dir = extractor.temp_dir
            
            # Create a descriptive filename for the output
            timestamp = int(time.time())
            clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
            clean_title = re.sub(r'_+', '_', clean_title).strip('_')
            
            final_output_name = f"INTELLIGENT_HIGHLIGHT_{clean_title}_{start_time}-{end_time}s_{timestamp}.mp4"
            final_output_path = os.path.join(output_dir, final_output_name)
            
            # Copy the highlight to the output directory
            try:
                import shutil
                shutil.copy2(highlight_path, final_output_path)
                
                logger.info(f"✅ Intelligent highlight saved for review!")
                logger.info(f"   📁 Location: {final_output_path}")
                logger.info(f"   ⏰ Segment: {start_time}s - {end_time}s (90s duration)")
                logger.info(f"   🏷️ Keywords: {', '.join(keywords[:5])}...")
                logger.info(f"   📊 File size: {os.path.getsize(final_output_path) / (1024*1024):.1f} MB")
                
                # Log the analysis results summary
                logger.info(f"   🧠 AI Analysis Summary:")
                logger.info(f"      📈 This segment was selected as the most engaging 1:30 from the trailer")
                logger.info(f"      🎬 Ready for manual review - Vizard.ai processing SKIPPED")
                
                result = final_output_path  # Return local path for review
                
            except Exception as e:
                logger.error(f"❌ Failed to copy highlight to output directory: {str(e)}")
                logger.info(f"   📁 Highlight available at: {highlight_path}")
                result = highlight_path
                
        else:
            # NORMAL MODE: Process with Vizard.ai after intelligent extraction
            logger.info("🤖 STEP 6: Processing extracted highlight with Vizard.ai...")
            
            # Import Vizard functions (only when needed)
            from ai.vizard_client import _process_movie_with_vizard, VizardClient
            
            # Create enhanced movie data with intelligent highlight info
            highlight_movie_data = movie_data.copy()
            highlight_movie_data['trailer_url'] = trailer_url
            highlight_movie_data['intelligent_highlight_path'] = highlight_path
            highlight_movie_data['content_keywords'] = keywords
            highlight_movie_data['highlight_timerange'] = f"{start_time}-{end_time}s"
            
            # Initialize Vizard client and process
            vizard_client = VizardClient()
            result = _process_movie_with_vizard(
                vizard_client, 
                highlight_movie_data, 
                trailer_url,
                extractor.temp_dir, 
                1, 
                transform_mode, 
                template_id
            )
        
        # Clean up temporary files
        try:
            if os.path.exists(downloaded_video):
                os.remove(downloaded_video)
            if os.path.exists(highlight_path):
                pass  # Keep highlight for potential future use
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Cleanup warning: {str(cleanup_error)}")
        
        if result:
            if review_mode:
                logger.info(f"🎉 Intelligent highlight extraction completed successfully!")
                logger.info(f"   🎯 Best segment: {start_time}s - {end_time}s")
                logger.info(f"   🏷️ Keywords: {', '.join(keywords[:5])}...")
                logger.info(f"   📁 Saved to: {result}")
                logger.info(f"")
                logger.info(f"   📺 REVIEW MODE - NEXT STEPS:")
                logger.info(f"      1. Review the extracted highlight video")
                logger.info(f"      2. Check the AI-selected segment quality")
                logger.info(f"      3. Verify the 1:30 duration and content")
                logger.info(f"      4. When satisfied, disable review_mode for Vizard.ai processing")
            else:
                logger.info(f"🎉 Complete intelligent highlight processing finished!")
                logger.info(f"   🎯 Best segment: {start_time}s - {end_time}s")
                logger.info(f"   🏷️ Keywords: {', '.join(keywords[:5])}...")
                logger.info(f"   ☁️ Final URL: {result}")
                logger.info(f"   🤖 Processed through Vizard.ai pipeline")
            
            return result
        else:
            error_msg = "Intelligent highlight extraction failed" if review_mode else "Complete intelligent processing failed"
            logger.error(f"❌ {error_msg} for: {title}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Critical error in intelligent highlight processing: {str(e)}")
        return None


# =============================================================================
# UTILITY FUNCTIONS  
# =============================================================================

def validate_intelligent_processing_requirements() -> Dict[str, Any]:
    """
    Validate requirements for intelligent highlight processing.
    
    Returns:
        Dict[str, Any]: Validation results
    """
    validation = {
        'ready': True,
        'missing_requirements': [],
        'warnings': []
    }
    
    try:
        # Check FFmpeg availability
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        if result.returncode != 0:
            validation['ready'] = False
            validation['missing_requirements'].append('FFmpeg not available - required for video processing')
        
        # Check Python dependencies
        required_packages = ['cv2', 'librosa', 'moviepy', 'numpy']
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                validation['missing_requirements'].append(f'Missing Python package: {package}')
                validation['ready'] = False
        
        # Check temp directory access
        try:
            ensure_directory("temp_intelligent_highlights")
        except Exception as e:
            validation['missing_requirements'].append(f'Cannot create temp directory: {str(e)}')
            validation['ready'] = False
        
        return validation
        
    except Exception as e:
        validation['ready'] = False
        validation['missing_requirements'].append(f'Validation error: {str(e)}')
        return validation
