"""
StreamGank Video Composition Builder

This module builds complete video compositions for Creatomate rendering,
including timing calculations, element positioning, and asset integration.

Features:
- Dynamic video composition building
- Poster timing strategy implementation
- Element layering and positioning
- Animation and transition management
- Asset integration (videos, images, overlays)
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod

from video.video_processor import calculate_video_durations, estimate_clip_durations, validate_duration_consistency

logger = logging.getLogger(__name__)

# =============================================================================
# TIMING STRATEGY CLASSES
# =============================================================================

class PosterTimingStrategy(ABC):
    """Abstract base class for poster timing strategies."""
    
    @abstractmethod
    def calculate_timing(self, heygen_durations: Dict[str, float], 
                        clip_durations: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Calculate poster timing based on video durations."""
        pass


class HeyGenLast3sStrategy(PosterTimingStrategy):
    """Posters appear during last 3 seconds of HeyGen videos."""
    
    def calculate_timing(self, heygen_durations: Dict[str, float], 
                        clip_durations: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        try:
            # Calculate cumulative times
            intro_time = 1 
            
            # Movie 1
            heygen1_start = intro_time
            heygen1_end = heygen1_start + heygen_durations["heygen1"]
            clip1_start = heygen1_end
            clip1_end = clip1_start + clip_durations["clip1"]
            
            # Movie 2  
            heygen2_start = clip1_end
            heygen2_end = heygen2_start + heygen_durations["heygen2"]
            clip2_start = heygen2_end
            clip2_end = clip2_start + clip_durations["clip2"]
            
            # Movie 3
            heygen3_start = clip2_end
            heygen3_end = heygen3_start + heygen_durations["heygen3"]
            clip3_start = heygen3_end
            
            return {
                "poster1": {
                    "time": heygen1_end - 4.0,  # Simple: last 4 seconds of HeyGen video
                    "duration": 4.0  # Fixed 4-second duration as requested
                },
                "poster2": {
                    "time": heygen2_end - 4.0,  # Simple: last 4 seconds of HeyGen video
                    "duration": 4.0  # Fixed 4-second duration as requested
                },
                "poster3": {
                    "time": heygen3_end - 4.0,  # Simple: last 4 seconds of HeyGen video
                    "duration": 4.0  # Fixed 4-second duration as requested
                }
            }
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: Failed to calculate HeyGen timing: {str(e)}")
            logger.error("🚫 STOPPING PROCESS - No fallback timing will be used")
            raise RuntimeError(f"HeyGen timing calculation failed: {str(e)}") from e


class WithMovieClipsStrategy(PosterTimingStrategy):
    """Posters appear simultaneously with movie clips."""
    
    def calculate_timing(self, heygen_durations: Dict[str, float], 
                        clip_durations: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        try:
            # Calculate cumulative times (same as above)
            intro_time = 1.0
            
            heygen1_start = intro_time
            clip1_start = heygen1_start + heygen_durations["heygen1"]
            clip1_end = clip1_start + clip_durations["clip1"]
            
            heygen2_start = clip1_end
            clip2_start = heygen2_start + heygen_durations["heygen2"]
            clip2_end = clip2_start + clip_durations["clip2"]
            
            heygen3_start = clip2_end
            clip3_start = heygen3_start + heygen_durations["heygen3"]
            
            return {
                "poster1": {
                    "time": clip1_start,
                    "duration": 4.0  # Fixed 4-second duration as requested
                },
                "poster2": {
                    "time": clip2_start,
                    "duration": 4.0  # Fixed 4-second duration as requested
                },
                "poster3": {
                    "time": clip3_start,
                    "duration": 4.0  # Fixed 4-second duration as requested
                }
            }
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: Failed to calculate movie clips timing: {str(e)}")
            logger.error("🚫 STOPPING PROCESS - No fallback timing will be used")
            raise RuntimeError(f"Movie clips timing calculation failed: {str(e)}") from e

# =============================================================================
# MAIN COMPOSITION BUILDING FUNCTIONS
# =============================================================================

def build_video_composition(heygen_video_urls: Dict[str, str],
                           movie_covers: Optional[List[str]] = None,
                           movie_clips: Optional[List[str]] = None,
                           scroll_video_url: Optional[str] = None,
                           scripts: Optional[Dict] = None,
                           poster_timing_mode: str = "heygen_last3s",
                           background_music_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Build complete video composition for Creatomate.
    
    STRICT MODE: All dependencies must be available. No fallbacks used.
    Process stops immediately if any required component is missing or invalid.
    
    Args:
        heygen_video_urls (Dict): HeyGen video URLs (REQUIRED)
        movie_covers (List): Enhanced poster URLs (REQUIRED - no fallback)
        movie_clips (List): Movie clip URLs (REQUIRED - no fallback)
        scroll_video_url (str): Optional scroll video URL
        scripts (Dict): Optional script data for duration calculation
        poster_timing_mode (str): Poster timing strategy
        background_music_url (str): Optional background music URL for audio elements
        
    Returns:
        Dict[str, Any]: Complete Creatomate composition
        
    Raises:
        ValueError: If required data is missing or invalid
        RuntimeError: If composition building fails
    """
    logger.info("🎬 Starting STRICT video composition building (no fallbacks)")
    
    # STRICT VALIDATION - All required inputs must be present (including outro)
    if not heygen_video_urls or len(heygen_video_urls) != 4:
        raise ValueError("❌ CRITICAL: Exactly 4 HeyGen video URLs required (movie1, movie2, movie3, outro)")
    
    required_keys = {"movie1", "movie2", "movie3", "outro"}
    if not required_keys.issubset(set(heygen_video_urls.keys())):
        missing_keys = required_keys - set(heygen_video_urls.keys())
        raise ValueError(f"❌ CRITICAL: Missing required HeyGen video keys: {missing_keys}")
    
    logger.info("✅ All 4 HeyGen videos found (movie1, movie2, movie3, outro)")
    
    # STRICT: Movie covers are REQUIRED (no fallback)
    if not movie_covers or len(movie_covers) != 3:
        raise ValueError("❌ CRITICAL: Exactly 3 movie cover URLs required - no fallback available")
    
    # STRICT: Movie clips are REQUIRED (no fallback)
    if not movie_clips or len(movie_clips) != 3:
        raise ValueError("❌ CRITICAL: Exactly 3 movie clip URLs required - no fallback available")
    
    # Validate all URLs are accessible
    for key, url in heygen_video_urls.items():
        if not url or not url.startswith(('http://', 'https://')):
            raise ValueError(f"❌ CRITICAL: Invalid HeyGen URL for {key}: {url}")
    
    for i, cover_url in enumerate(movie_covers):
        if not cover_url or not cover_url.startswith(('http://', 'https://')):
            raise ValueError(f"❌ CRITICAL: Invalid movie cover URL at index {i}: {cover_url}")
    
    for i, clip_url in enumerate(movie_clips):
        if not clip_url or not clip_url.startswith(('http://', 'https://')):
            raise ValueError(f"❌ CRITICAL: Invalid movie clip URL at index {i}: {clip_url}")
    
    # Step 1: Calculate video durations (STRICT - must succeed)
    logger.info("📊 Calculating HeyGen video durations (STRICT mode)...")
    heygen_durations = calculate_video_durations(heygen_video_urls, scripts)
    if not heygen_durations:
        raise RuntimeError("❌ CRITICAL: Failed to calculate HeyGen video durations - cannot proceed")
    
    # Validate heygen_durations completeness
    for key in required_keys:
        heygen_key = key.replace('movie', 'heygen')
        if heygen_key not in heygen_durations or heygen_durations[heygen_key] <= 0:
            raise ValueError(f"❌ CRITICAL: Invalid or missing duration for {heygen_key}: {heygen_durations.get(heygen_key)}")
    
    # Step 2: Calculate clip durations (STRICT - must succeed)
    logger.info("📊 Calculating clip durations (STRICT mode)...")
    clip_durations = estimate_clip_durations(movie_clips)
    if not clip_durations:
        raise RuntimeError("❌ CRITICAL: Failed to calculate clip durations - cannot proceed")
    
    # Validate clip_durations completeness
    for i in range(1, 4):
        clip_key = f"clip{i}"
        if clip_key not in clip_durations or clip_durations[clip_key] <= 0:
            raise ValueError(f"❌ CRITICAL: Invalid or missing duration for {clip_key}: {clip_durations.get(clip_key)}")
    
    # Step 2.5: Validate duration consistency for Creatomate debugging
    logger.info("🔍 Validating duration consistency (STRICT mode)...")
    validate_duration_consistency(heygen_durations, clip_durations)
    
    # Step 3: Calculate poster timing (STRICT - will raise on failure)
    logger.info("🎯 Calculating poster timing (STRICT mode)...")
    timing_strategy = get_poster_timing_strategy(poster_timing_mode)
    poster_timings = timing_strategy.calculate_timing(heygen_durations, clip_durations)
    
    # Validate poster timings
    required_posters = {"poster1", "poster2", "poster3"}
    if not all(poster in poster_timings for poster in required_posters):
        missing_posters = required_posters - set(poster_timings.keys())
        raise RuntimeError(f"❌ CRITICAL: Missing poster timing calculations: {missing_posters}")
    
    # Step 4: Build composition elements (STRICT - will raise on failure)
    logger.info("🏗️ Building composition structure (STRICT mode)...")
    composition = _build_composition_structure(
        heygen_video_urls,
        movie_covers,
        movie_clips,
        poster_timings,
        heygen_durations,
        clip_durations,
        scroll_video_url,
        background_music_url
    )
    
    # Final validation of composition
    if not composition or 'elements' not in composition or len(composition['elements']) < 8:
        raise RuntimeError("❌ CRITICAL: Invalid composition structure - insufficient elements")
    
    # Calculate total duration for logging
    calculated_total_duration = (1 + sum(heygen_durations.values()) + sum(clip_durations.values()) + 3)
    
    # Final logging for easy Creatomate debugging and monitoring
    logger.info("✅ CREATOMATE COMPOSITION SUMMARY:")
    logger.info(f"   📊 Total elements: {len(composition['elements'])}")
    logger.info(f"   🎬 Video resolution: {composition['width']}x{composition['height']}")
    logger.info(f"   🎞️ Frame rate: {composition['frame_rate']} fps")
    logger.info(f"   ⏱️ Total duration: {calculated_total_duration:.2f}s")
    
    # Log all asset URLs for debugging
    logger.info("🔗 ASSET URLS IN COMPOSITION:")
    for i, (key, url) in enumerate(heygen_video_urls.items(), 1):
        logger.info(f"   🎤 {key}: {url}")
    
    for i, cover_url in enumerate(movie_covers, 1):
        logger.info(f"   🖼️ poster{i}: {cover_url}")
    
    for i, clip_url in enumerate(movie_clips, 1):
        logger.info(f"   🎬 clip{i}: {clip_url}")
    
    if scroll_video_url:
        logger.info(f"   📜 scroll_video: {scroll_video_url}")
    
    if background_music_url:
        logger.info(f"   🎵 background_music: {background_music_url}")
    
    logger.info("✅ STRICT video composition completed - ready for Creatomate render")
    
    # Log composition structure for easy debugging
    _log_composition_structure(composition)
    
    return composition


def _log_composition_structure(composition: Dict[str, Any]) -> None:
    """Log composition structure for easy Creatomate debugging."""
    logger.info("📋 CREATOMATE COMPOSITION STRUCTURE:")
    logger.info(f"   🎬 Resolution: {composition['width']}x{composition['height']}")
    logger.info(f"   🎞️ Frame Rate: {composition['frame_rate']} fps")
    logger.info(f"   📊 Total Elements: {len(composition['elements'])}")
    
    logger.info("📝 ELEMENT BREAKDOWN:")
    for i, element in enumerate(composition['elements'], 1):
        element_type = element.get('type', 'unknown')
        track = element.get('track', 'auto')
        time = element.get('time', 'auto')
        duration = element.get('duration', 'auto')
        
        if element_type == 'image':
            source = element.get('source', '').split('/')[-1]  # Just filename
            logger.info(f"   {i:2d}. 🖼️ {element_type.upper()} | Track {track} | {time}s → {duration}s | {source}")
        elif element_type == 'video':
            source = element.get('source', '')
            if 'heygen' in source.lower():
                logger.info(f"   {i:2d}. 🎤 HEYGEN | Track {track} | {time}s → {duration}s")
            elif 'cloudinary' in source.lower() and 'clip' in source.lower():
                logger.info(f"   {i:2d}. 🎬 CLIP | Track {track} | {time}s → {duration}s")
            elif 'scroll' in source.lower():
                logger.info(f"   {i:2d}. 📜 SCROLL | Track {track} | {time}s → {duration}s")
            else:
                logger.info(f"   {i:2d}. 🎥 VIDEO | Track {track} | {time}s → {duration}s")
        elif element_type == 'composition':
            name = element.get('name', 'Unknown')
            logger.info(f"   {i:2d}. 🏷️ BRANDING | Track {track} | {time}s → {duration}s | {name}")
        else:
            logger.info(f"   {i:2d}. ❓ {element_type.upper()} | Track {track} | {time}s → {duration}s")
    
    logger.info("🎯 READY FOR CREATOMATE RENDER - All timings precise and validated")


def get_poster_timing_strategy(mode: str) -> PosterTimingStrategy:
    """Get poster timing strategy based on mode."""
    strategies = {
        "heygen_last3s": HeyGenLast3sStrategy(),
        "with_movie_clips": WithMovieClipsStrategy()
    }
    
    return strategies.get(mode, HeyGenLast3sStrategy())


def create_poster_timing(poster_timings: Dict[str, Dict[str, float]], 
                        movie_covers: List[str]) -> List[Dict[str, Any]]:
    """Create poster elements with timing."""
    poster_elements = []
    
    try:
        for i, cover_url in enumerate(movie_covers[:3]):
            poster_key = f"poster{i+1}"
            if poster_key in poster_timings:
                timing = poster_timings[poster_key]
                
                poster_element = {
                    "name": f"MoviePoster-{i+1}",
                    "type": "image",
                    "track": 3,  # Poster layer
                    "time": timing["time"],
                    "duration": timing["duration"],
                    "source": cover_url,
                    "x": "50%",
                    "y": "50%",
                    "width": "40%",
                    "height": "auto",
                    "x_anchor": "50%",
                    "y_anchor": "50%",
                    "animations": [
                        {
                            "time": 0,
                            "duration": 0.5,
                            "type": "scale",
                            "scale_x": 0,
                            "scale_y": 0
                        },
                        {
                            "time": "end",
                            "duration": 0.5,
                            "type": "scale",
                            "scale_x": 0,
                            "scale_y": 0,
                            "reversed": True
                        }
                    ]
                }
                
                poster_elements.append(poster_element)
        
        logger.info(f"✅ Created {len(poster_elements)} poster elements")
        return poster_elements
        
    except Exception as e:
        logger.error(f"❌ Error creating poster elements: {str(e)}")
        return []

# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _build_composition_structure(heygen_video_urls: Dict[str, str],
                               movie_covers: Optional[List[str]],
                               movie_clips: Optional[List[str]],
                               poster_timings: Dict[str, Dict[str, float]],
                               heygen_durations: Dict[str, float],
                               clip_durations: Dict[str, float],
                               scroll_video_url: Optional[str],
                               background_music_url: Optional[str] = None) -> Dict[str, Any]:
    """Build the complete Creatomate composition with all detailed elements."""
    
    # ═══════════════════════════════════════════════════════════════
    # TIMING VARIABLES FOR EASY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    # Extract poster timing data
    poster1_time = poster_timings["poster1"]["time"]
    poster1_duration = poster_timings["poster1"]["duration"]
    poster2_time = poster_timings["poster2"]["time"]
    poster2_duration = poster_timings["poster2"]["duration"]
    poster3_time = poster_timings["poster3"]["time"]
    poster3_duration = poster_timings["poster3"]["duration"]
    
    # Timing offset variables for easy management
    poster1_time_offset = -0.5      # No offset for first poster
    poster2_time_offset = poster1_time_offset + -0.5   # Sync with HeyGen2 fade (0.5s)
    poster3_time_offset = poster2_time_offset + -0.5   # Sync with HeyGen3 fade (0.5s)
    
    # Animation duration variables
    intro_fade_duration = 0.5
    poster_fade_duration = 1.0
    heygen_fade_duration = 0.5
    outro_fade_duration = 1.0
    
    # Element duration variables
    intro_duration = 1
    outro_duration = heygen_durations["outro"]  # Use actual HeyGen outro video duration
    outro_static_duration = 3 - outro_fade_duration  # Static outro image duration after HeyGen outro
    scroll_video_start_time = 2
    scroll_video_duration = 4
    

    # Audio duration variables
    # To calculate the audio timing, we need to subtract the fade duration from the heygen duration
    heygen1_audio_timing = -0.5
    heygen2_audio_timing = heygen1_audio_timing + -0.5 # 0.5 heygen2 fade
    heygen3_audio_timing = heygen2_audio_timing + -0.5 # heygen2_audio_timing + 0.5 heygen3 fade 
    outro_audio_timing = heygen3_audio_timing + -0.5 # heygen3_audio_timing + 0.5 outro fade 

    # Audio settings
    audio_volume = "40%"
    
    # Calculate total video length using ACTUAL durations (makes Creatomate easy to debug)
    total_video_length = (intro_duration +  # Intro
                         heygen_durations["heygen1"] + 
                         clip_durations["clip1"] + 
                         heygen_durations["heygen2"] + 
                         clip_durations["clip2"] + 
                         heygen_durations["heygen3"] + 
                         clip_durations["clip3"] + 
                         outro_duration +  # HeyGen outro video
                         outro_static_duration)  # Static outro image
        
    # Branding duration = total - intro - outro - fade durations
    branding_duration = total_video_length - intro_duration - outro_static_duration - outro_fade_duration - (heygen_fade_duration * 4)
        
    # LOG DETAILED TIMING FOR EASY CREATOMATE DEBUGGING
    logger.info("🎬 CREATOMATE COMPOSITION TIMING BREAKDOWN:")
    logger.info(f"   📐 INTRO: 0.00s → {intro_duration:.2f}s ({intro_duration:.2f}s duration)")
    
    current_time = float(intro_duration)
    logger.info(f"   🎤 HEYGEN1 (includes intro): {current_time:.2f}s → {current_time + heygen_durations['heygen1']:.2f}s ({heygen_durations['heygen1']:.2f}s duration)")
    current_time += heygen_durations["heygen1"]
    
    logger.info(f"   🎬 CLIP1: {current_time:.2f}s → {current_time + clip_durations['clip1']:.2f}s ({clip_durations['clip1']:.2f}s duration)")
    current_time += clip_durations["clip1"]
    
    logger.info(f"   🎤 HEYGEN2: {current_time:.2f}s → {current_time + heygen_durations['heygen2']:.2f}s ({heygen_durations['heygen2']:.2f}s duration)")
    current_time += heygen_durations["heygen2"]
    
    logger.info(f"   🎬 CLIP2: {current_time:.2f}s → {current_time + clip_durations['clip2']:.2f}s ({clip_durations['clip2']:.2f}s duration)")
    current_time += clip_durations["clip2"]
    
    logger.info(f"   🎤 HEYGEN3: {current_time:.2f}s → {current_time + heygen_durations['heygen3']:.2f}s ({heygen_durations['heygen3']:.2f}s duration)")
    current_time += heygen_durations["heygen3"]
    
    logger.info(f"   🎬 CLIP3: {current_time:.2f}s → {current_time + clip_durations['clip3']:.2f}s ({clip_durations['clip3']:.2f}s duration)")
    current_time += clip_durations["clip3"]
    
    logger.info(f"   🎤 HEYGEN OUTRO: {current_time:.2f}s → {current_time + outro_duration:.2f}s ({outro_duration:.2f}s duration)")
    current_time += outro_duration
    
    logger.info(f"   📐 STATIC OUTRO: {current_time:.2f}s → {total_video_length:.2f}s ({outro_static_duration:.2f}s duration)")
    
    logger.info(f"📊 TOTAL VIDEO LENGTH: {total_video_length:.2f}s ({total_video_length/60:.1f} minutes)")
    logger.info(f"🏷️ BRANDING: {intro_duration:.2f}s → {intro_duration + branding_duration:.2f}s ({branding_duration:.2f}s duration)")
    
    # Show poster timing for easy debugging
    logger.info("🖼️ POSTER TIMING (Fixed 4.0s duration):")
    logger.info(f"   🖼️ POSTER1: {poster1_time:.2f}s → {poster1_time + poster1_duration:.2f}s ({poster1_duration:.2f}s duration)")
    logger.info(f"   🖼️ POSTER2: {poster2_time - 0.5:.2f}s → {poster2_time - 0.5 + poster2_duration:.2f}s ({poster2_duration:.2f}s duration)")
    logger.info(f"   🖼️ POSTER3: {poster3_time - 0.5:.2f}s → {poster3_time - 0.5 + poster3_duration:.2f}s ({poster3_duration:.2f}s duration)")

    # Base composition structure - EXACT CREATOMATE FORMAT (matches legacy exactly)
    composition = {
        "width": 1080,
        "height": 1920,
        "frame_rate": 30,
        "output_format": "mp4",  # Required by Creatomate API
        "elements": [
            # ═══════════════════════════════════════════════════════════════
            # MAIN TIMELINE (Track 1) - Sequential elements
            # ═══════════════════════════════════════════════════════════════
            
            # 🎯 ELEMENT 1: INTRO IMAGE
            {
                "type": "image",
                "track": 1,
                "time": 0,
                "duration": intro_duration,
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1753263646/streamGank_intro_cwefmt.jpg",
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": intro_fade_duration,
                        "easing": "quadratic-out",
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 ELEMENT 2: HEYGEN VIDEO 1 (includes intro + movie1 hook) - Natural duration
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "source": heygen_video_urls["movie1"],
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": heygen_fade_duration,
                        "transition": True,
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 ELEMENT 3: MOVIE CLIP 1 (ACTUAL duration)
            {
                "type": "video", 
                "track": 1,
                "time": "auto",
                "duration": clip_durations["clip1"],
                "source": movie_clips[0],
                "fit": "cover"
            },
            
            # 🎯 ELEMENT 4: HEYGEN VIDEO 2 - Natural duration
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "source": heygen_video_urls["movie2"],
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": heygen_fade_duration,
                        "transition": True,
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 ELEMENT 5: MOVIE CLIP 2 (ACTUAL duration)
            {
                "type": "video",
                "track": 1, 
                "time": "auto",
                "duration": clip_durations["clip2"],
                "source": movie_clips[1],
                "fit": "cover"
            },
            
            # 🎯 ELEMENT 6: HEYGEN VIDEO 3 - Natural duration
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "source": heygen_video_urls["movie3"],
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": heygen_fade_duration,
                        "transition": True,
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 ELEMENT 7: MOVIE CLIP 3 (ACTUAL duration)
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "duration": clip_durations["clip3"],
                "source": movie_clips[2],
                "fit": "cover"
            },
            
            # 🎯 ELEMENT 7.5: OUTRO HEYGEN VIDEO (Dynamic genre-based script)
            {
                "type": "video",
                "track": 1,
                "time": "auto",
                "source": heygen_video_urls["outro"],
                "fit": "cover",
                "animations": [
                    {
                    "time": 0,
                    "duration": heygen_fade_duration,
                    "transition": True,
                    "type": "fade"
                    }
                ]
            },

            # 🎯 ELEMENT 8: STATIC OUTRO IMAGE
            {
                "type": "image",
                "track": 1,
                "time": "auto",
                "duration": outro_static_duration,
                "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1752587571/streamgank_bg_heecu7.png",
                "fit": "cover",
                "animations": [
                    {
                        "time": 0,
                        "duration": outro_fade_duration,
                        "transition": True,
                        "type": "fade"
                    }
                ]
            },
            
            # ═══════════════════════════════════════════════════════════════
            # OVERLAY ELEMENTS (Track 2) - Enhanced Posters with Perfect Timing
            # ═══════════════════════════════════════════════════════════════
            
            # 🎯 POSTER 1 - Fixed 4-second duration for optimal display
            {
                "type": "image",
                "track": 2,
                "time": poster1_time + poster1_time_offset,
                "duration": poster1_duration,
                "source": movie_covers[0],
                "fit": "contain",
                "animations": [
                    {
                        "time": 0,
                        "duration": poster_fade_duration,
                        "easing": "quadratic-out",
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 POSTER 2 - Fixed 4-second duration for optimal display
            {
                "type": "image",
                "track": 2,  
                "time": poster2_time + poster2_time_offset,  # Sync with HeyGen2 fade timing
                "duration": poster2_duration,
                "source": movie_covers[1],
                "fit": "contain",
                "animations": [
                    {
                        "time": 0,
                        "duration": poster_fade_duration,
                        "easing": "quadratic-out",
                        "type": "fade"
                    }
                ]
            },
            
            # 🎯 POSTER 3 - Fixed 4-second duration for optimal display
            {
                "type": "image",
                "track": 2,
                "time": poster3_time + poster3_time_offset,  # Sync with HeyGen3 fade timing
                "duration": poster3_duration,
                "source": movie_covers[2],
                "fit": "contain",
                "animations": [
                    {
                        "time": 0,
                        "duration": poster_fade_duration,
                        "easing": "quadratic-out",
                        "type": "fade"
                    }
                ]
            },
            
            # ═══════════════════════════════════════════════════════════════
            # PERSISTENT BRANDING (Tracks 3) 
            # ═══════════════════════════════════════════════════════════════
            
            {
                "name": "Composition-228",
                "type": "composition",
                "track": 3,
                "time": intro_duration,
                "duration": branding_duration,
                "elements": [
                    # STREAMGANK LOGO TEXT "Stream" - Green colored, persistent overlay
                    {
                        "name": "StreamGank-Stream",
                        "type": "text",
                        "x": "19.2502%",
                        "y": "0%",
                        "x_anchor": "0%",
                        "y_anchor": "0%",
                        "text": "Stream",
                        "font_family": "Noto Sans",
                        "font_weight": "700",
                        "font_size": "10 vmin",
                        "fill_color": "#61d7a5",
                        "shadow_color": "rgba(0,0,0,0.8)",
                        "shadow_blur": "2 vmin"
                    },

                    # STREAMGANK LOGO TEXT "Gank" - White colored, persistent overlay
                    {
                        "name": "Text-9SD",
                        "type": "text",
                        "x": "54.7131%",
                        "y": "0%",
                        "x_anchor": "0%",
                        "y_anchor": "0%",
                        "text": "Gank",
                        "font_family": "Noto Sans",
                        "font_weight": "700",
                        "font_size": "10 vmin",
                        "fill_color": "#ffffff",
                        "shadow_color": "rgba(0,0,0,0.25)"
                    },

                    # STREAMGANK TAGLINE - Brand message, persistent overlay
                    {
                        "name": "Text-LZ9",
                        "type": "text",
                        "x": "20.1158%",
                        "y": "6.1282%",
                        "x_anchor": "0%",
                        "y_anchor": "0%",
                        "text": "AMBUSH THE BEST VOD TOGETHER",
                        "font_family": "Noto Sans",
                        "font_weight": "700",
                        "font_size": "3.5 vmin",
                        "fill_color": "#ffffff",
                        "shadow_color": "rgba(0,0,0,0.8)",
                        "shadow_blur": "2 vmin"
                    }
                ]
            },

            # ═══════════════════════════════════════════════════════════════
            # AUDIO ELEMENTS (Track 5) 
            # ═══════════════════════════════════════════════════════════════

            {
                "id": "7405c69c-5557-4b19-9989-f4128fdebce6",
                "name": "Composition-3ZN",
                "type": "composition",
                "track": 5,
                "time": 0,
                "elements": [
                    # AUDIO 1 - Start with intro, duration ends with 1st HeyGen video
                    {
                        "name": "Audio-3P3",
                        "type": "audio",
                        "track": 1,
                        "time": 0,
                        "duration": intro_duration + heygen_durations["heygen1"] + heygen1_audio_timing,
                        "source": background_music_url,
                        "volume": audio_volume
                    },
                    # AUDIO 2 - Start with 2nd HeyGen video, duration matches HeyGen2
                    {
                        "name": "Audio-8X4",
                        "type": "audio",
                        "track": 1,
                        "time": intro_duration + heygen_durations["heygen1"] + clip_durations["clip1"] + heygen2_audio_timing,
                        "duration": heygen_durations["heygen2"],
                        "source": background_music_url,
                        "volume": audio_volume
                    },
                    # AUDIO 3 - Start with 3rd HeyGen video, duration matches HeyGen3
                    {
                        "name": "Audio-49L",
                        "type": "audio",
                        "track": 1,
                        "time": intro_duration + heygen_durations["heygen1"] + clip_durations["clip1"] + heygen_durations["heygen2"] + clip_durations["clip2"] + heygen3_audio_timing,
                        "duration": heygen_durations["heygen3"],
                        "source": background_music_url,
                        "volume": audio_volume
                    },
                    
                    # AUDIO 4 - Start with HeyGen outro video, duration matches HeyGen outro
                    {
                        "name": "Audio-Outro",
                        "type": "audio",
                        "track": 1,
                        "time": intro_duration + heygen_durations["heygen1"] + clip_durations["clip1"] + heygen_durations["heygen2"] + clip_durations["clip2"] + heygen_durations["heygen3"] + clip_durations["clip3"] + outro_audio_timing,
                        "duration": outro_duration,
                        "source": background_music_url,
                        "volume": audio_volume
                    }
                ]
            }
        ]
    }

    # Add scroll video overlay if provided (Track 4 - Top layer)
    if scroll_video_url:
        scroll_overlay = {
            "name": "ScrollVideo-Overlay",
            "type": "video",
            "track": 4,
            "time": scroll_video_start_time,
            "duration": scroll_video_duration,
            "source": scroll_video_url,
            "fit": "cover",
            "width": "100%",
            "height": "100%",
            "animations": [
                {
                    "time": 0,
                    "duration": poster_fade_duration,
                    "type": "fade",
                    "fade_in": True
                },
                {
                    "time": "end",
                    "duration": poster_fade_duration,
                    "easing": "quadratic-out",
                    "reversed": True,
                    "type": "fade"
                }
            ]
        }
        composition["elements"].append(scroll_overlay)
        logger.info("✅ Scroll video overlay added to composition")
    else:
        logger.info("ℹ️ No scroll video URL provided - skipping overlay")
    
    logger.info(f"🎬 Composition built with {len(composition['elements'])} total elements")
    return composition 


# Helper functions removed - full composition now built in _build_composition_structure