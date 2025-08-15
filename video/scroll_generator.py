"""
StreamGank Scroll Video Generator

This module generates smooth scrolling videos of StreamGank website pages
using browser automation and screen capture.

Features:
- Browser automation with Playwright
- Smooth scroll animations (60 FPS)
- Dynamic URL building with filters
- Screenshot capture and video assembly
- Cloudinary upload integration
"""

import os
import time
import logging
import subprocess
import random
import math
from typing import Optional, Dict, Any
from pathlib import Path
from playwright.sync_api import sync_playwright

from utils.url_builder import build_streamgank_url
from media.cloudinary_uploader import upload_clip_to_cloudinary
from utils.file_utils import ensure_directory

logger = logging.getLogger(__name__)

# =============================================================================
# MAIN SCROLL VIDEO FUNCTIONS
# =============================================================================

def generate_scroll_video(country: str, 
                         genre: str, 
                         platform: str, 
                         content_type: str,
                         smooth: bool = True,
                         scroll_distance: float = 1.5,
                         duration: int = 4,
                         device_name: str = "iPhone 12 Pro Max") -> Optional[str]:
    """
    Create a DYNAMIC scrolling video of StreamGank with MICRO-SCROLLING for readability.
    NO MORE DISTORTION - Uses tiny scroll increments for natural reading experience!
    
    Args:
        country (str): Country filter
        genre (str): Genre filter
        platform (str): Platform filter  
        content_type (str): Content type filter
        smooth (bool): Enable micro-scrolling animation (NOT CSS smooth)
        scroll_distance (float): Viewport height multiplier for scroll amount (default: 1.5 = minimal readable)
        duration (int): Fixed video duration in seconds (default: 4)
        device_name (str): Mobile device to simulate
        
    Returns:
        str: Cloudinary URL of uploaded scroll video or None if failed
    """
    try:
        # Generate unique filename based on filter parameters (prevent duplicates!)
        safe_country = country.replace(" ", "").replace("/", "-")
        safe_genre = genre.replace(" ", "").replace("/", "-")
        safe_platform = platform.replace(" ", "").replace("/", "-")
        safe_content = content_type.replace(" ", "").replace("/", "-")
        
        # Fix filename: replace dots with underscores to avoid file extension issues
        scroll_distance_safe = str(scroll_distance).replace('.', '_')
        output_video = f"scroll_{safe_country}_{safe_genre}_{safe_platform}_{safe_content}_{scroll_distance_safe}x.mp4"
        
        logger.info(f"📏 Unique filename: {output_video}")
        logger.info(f"🎯 DYNAMIC SCROLL VIDEO GENERATION (SMOOTH: {smooth})")
        logger.info(f"   Parameters: {country} | {genre} | {platform} | {content_type}")
        logger.info(f"   Speed: Ultra | Distance: {scroll_distance}x")
        
        # Create unique frames directory per process to avoid conflicts
        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        frames_dir = f"scroll_frames_{unique_id}"
        ensure_directory(frames_dir)
        
        logger.info(f"📁 Using unique frames directory: {frames_dir}")
        logger.info(f"   🛡️ Multi-script safe - no frame conflicts!")
        
        # STRICT MODE: Only use filtered URL - NO FALLBACKS
        filtered_url = build_streamgank_url(country, genre, platform, content_type)
        
        logger.info(f"🎯 DYNAMIC SCROLL VIDEO GENERATION - STRICT MODE (NO FALLBACKS)")
        logger.info(f"   🎬 FIXED DURATION: {duration} seconds")
        logger.info(f"   Target URL (filtered): {filtered_url}")
        logger.info(f"   Scroll Speed: Ultra - Smooth: {smooth}")
        
        # Generate scroll video using advanced browser automation
        video_path = _create_advanced_scroll_video(
            filtered_url=filtered_url,
            output_video=output_video,
            frames_dir=frames_dir,
            target_duration=duration,
            smooth_scroll=smooth,
            scroll_distance=scroll_distance,
            device_name=device_name
        )
        
        if video_path:
            logger.info(f"✅ Scroll video generated: {video_path}")
            
            # Upload to Cloudinary
            try:
                cloudinary_url = upload_clip_to_cloudinary(
                    video_path, 
                    f"scroll_{genre}_{platform}",
                    folder="streamgank_scroll_videos",
                    transform_mode="fit"
                )
                
                if cloudinary_url:
                    logger.info(f"☁️ Scroll video uploaded: {cloudinary_url}")
                    
                    # Clean up local files
                    try:
                        os.remove(video_path)
                        logger.debug(f"🧹 Cleaned up local file: {video_path}")
                    except Exception as e:
                        logger.warning(f"Could not clean up local file: {str(e)}")
                    
                    return cloudinary_url
                else:
                    logger.warning("Failed to upload to Cloudinary, returning local path")
                    return video_path
                    
            except Exception as e:
                logger.warning(f"Upload error: {str(e)}, returning local path")
                return video_path
        else:
            logger.error("❌ Failed to generate scroll video")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error generating scroll video: {str(e)}")
        return None


def create_scroll_video_from_url(url: str,
                                output_path: Optional[str] = None,
                                duration: int = 4,
                                smooth_scroll: bool = True) -> Optional[str]:
    """
    Create scroll video from a specific URL using advanced browser automation.
    
    Args:
        url (str): URL to scroll and capture
        output_path (str): Output video path (optional)
        duration (int): Video duration in seconds
        smooth_scroll (bool): Enable smooth scrolling
        
    Returns:
        str: Path to generated video or None if failed
    """
    try:
        logger.info(f"🎬 Creating scroll video from URL: {url}")
        
        # Generate output path if not provided
        if not output_path:
            output_path = f"scroll_custom_{int(time.time())}.mp4"
        
        # Create unique frames directory
        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        frames_dir = f"scroll_frames_{unique_id}"
        ensure_directory(frames_dir)
        
        # Use advanced scroll video creation
        video_path = _create_advanced_scroll_video(
            filtered_url=url,
            output_video=output_path,
            frames_dir=frames_dir,
            target_duration=duration,
            smooth_scroll=smooth_scroll,
            scroll_distance=1.5  # Default scroll distance
        )
        
        if video_path:
            logger.info(f"✅ Scroll video created: {video_path}")
            return video_path
        else:
            logger.error("❌ Failed to create scroll video from URL")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error creating scroll video from URL: {str(e)}")
        return None

# =============================================================================
# UTILITY FUNCTIONS  
# =============================================================================

def get_scroll_video_url(country: str, genre: str, platform: str, content_type: str) -> str:
    """
    Build StreamGank URL for scroll video capture.
    
    Args:
        country (str): Country filter
        genre (str): Genre filter
        platform (str): Platform filter
        content_type (str): Content type filter
        
    Returns:
        str: Complete StreamGank URL
    """
    return build_streamgank_url(country, genre, platform, content_type)


def validate_scroll_parameters(duration: int, scroll_distance: float) -> Dict[str, Any]:
    """
    Validate scroll video parameters.
    
    Args:
        duration (int): Video duration in seconds
        scroll_distance (float): Scroll distance multiplier
        
    Returns:
        Dict[str, Any]: Validation results
    """
    validation = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Duration validation
    if duration < 1:
        validation['is_valid'] = False
        validation['errors'].append('Duration must be at least 1 second')
    elif duration > 10:
        validation['warnings'].append('Duration longer than 10 seconds may be too slow')
    
    # Scroll distance validation
    if scroll_distance < 0.5:
        validation['warnings'].append('Very short scroll distance may not show enough content')
    elif scroll_distance > 3.0:
        validation['warnings'].append('Very long scroll distance may be too fast to read')
    
    return validation


# =============================================================================
# ADVANCED SCROLL VIDEO CREATION FUNCTIONS
# =============================================================================

def _create_advanced_scroll_video(filtered_url: str,
                                 output_video: str,
                                 frames_dir: str,
                                 target_duration: int = 4,
                                 smooth_scroll: bool = True,
                                 scroll_distance: float = 1.5,
                                 device_name: str = "iPhone 12 Pro Max") -> Optional[str]:
    """
    Create scroll video using advanced browser automation with dynamic content detection.
    """
    try:
        # Clean old frames
        for file in os.listdir(frames_dir):
            if file.endswith(".png"):
                os.remove(os.path.join(frames_dir, file))
        
        with sync_playwright() as p:
            # Always use headless mode in Docker containers (detect by checking if we're in a container)
            # This is separate from APP_ENV which controls HeyGen API vs local URLs
            is_in_container = os.path.exists('/.dockerenv') or os.getenv('PYTHONPATH') == '/app'
            browser = p.chromium.launch(headless=is_in_container)
            
            # Use mobile device simulation
            device = p.devices[device_name]
            context = browser.new_context(
                **device,
                locale='fr-FR',
                timezone_id='Europe/Paris',
            )
            
            page = context.new_page()
            
            # STEP 1.5: DISABLE CSS smooth scrolling - use instant micro-scrolling instead
            page.add_init_script("""() => {
                // DISABLE all smooth scrolling for instant micro-movements
                document.documentElement.style.scrollBehavior = 'auto';
                document.body.style.scrollBehavior = 'auto';
                
                // Override any existing scroll behavior to instant
                const style = document.createElement('style');
                style.textContent = `
                    * {
                        scroll-behavior: auto !important;
                    }
                    html, body {
                        scroll-behavior: auto !important;
                    }
                `;
                document.head.appendChild(style);
            }""")
            
            # STEP 2: Use filtered URL only - STRICT MODE
            try:
                logger.info(f"🌐 Trying filtered URL: {filtered_url}")
                page.goto(filtered_url)
                
                # Wait for page load with multiple possible indicators
                try:
                    # Try to find RESULTS indicator (filtered page)
                    page.wait_for_selector("text=RESULTS", timeout=8000)
                    logger.info("✅ Filtered page loaded successfully")
                except:
                    try:
                        # Try to find any content
                        page.wait_for_selector("[class*='card'], [class*='movie'], [class*='item']", timeout=5000)
                        logger.info("✅ Content found on filtered page")
                    except:
                        # If no content selectors, wait for general page load
                        page.wait_for_selector("body", timeout=3000)
                        logger.info("⚠️ Page loaded but no specific content indicators")
                
                # STEP 3: Detect content availability
                time.sleep(3)  # Let content load
                content_info = _detect_content_availability(page)
                
                logger.info(f"📆 Content Analysis:")
                logger.info(f"   Has content: {content_info['has_content']}")
                logger.info(f"   Content count: {content_info['content_count']}")
                logger.info(f"   Page height: {content_info['page_height']}px")
                logger.info(f"   Needs scrolling: {content_info['needs_scrolling']}")
                
                # STEP 4: STRICT VALIDATION - No fallbacks allowed
                if not content_info['has_content'] or content_info['has_no_results']:
                    logger.error("❌ No content found with filters - NO FALLBACK ALLOWED")
                    logger.error(f"   Content details: has_content={content_info['has_content']}, has_no_results={content_info['has_no_results']}")
                    browser.close()
                    return None
                
                logger.info("✅ Content found - proceeding with scroll video generation!")
                
                # Calculate optimal scroll height
                scroll_height = _calculate_optimal_scroll_height(
                    content_info['viewport_height'],
                    content_info['page_height'],
                    scroll_distance
                )
                
            except Exception as e:
                logger.error(f"❌ Error with filtered URL: {str(e)}")
                logger.error("❌ STRICT MODE - No fallback allowed, returning None")
                browser.close()
                return None
            
            # STEP 5: Handle cookies
            _handle_cookies(page)
            
            # STEP 6: Configure ULTRA 60 FPS MICRO-SCROLLING
            wait_time = 0.04  # Ultra-fast capture timing
            target_fps = 60   # 60 FPS ultra-smooth!
            
            # Calculate frames for exactly target_duration seconds with 60 FPS micro-scrolling
            num_frames = target_duration * target_fps
            num_frames = int(num_frames)
            
            logger.info(f"🎬 MICRO-SCROLLING CALCULATION:")
            logger.info(f"   Target duration: {target_duration} seconds")
            logger.info(f"   Micro-scroll FPS: {target_fps}")
            logger.info(f"   Total frames: {num_frames}")
            logger.info(f"   Pixels per frame: {scroll_height/num_frames:.1f}px (MICRO!)")
            logger.info(f"   Wait per frame: {wait_time:.2f}s (READABLE)")
            
            # STEP 7: Capture frames with MICRO-SCROLLING
            unique_id = frames_dir.split('_')[-1]  # Extract unique ID from frames dir
            
            logger.info(f"📷 Capturing {num_frames} frames with MICRO-SCROLLING")
            logger.info(f"   Scroll height: {scroll_height:.0f}px (SHORT & READABLE)")
            logger.info(f"   URL being captured: {filtered_url}")
            
            for i in range(num_frames):
                # Calculate tiny scroll increments - perfectly linear for readability
                scroll_position = int((i * scroll_height) / max(1, (num_frames - 1)))
                
                # INSTANT scroll to exact position (no CSS smooth behavior)
                page.evaluate(f"window.scrollTo(0, {scroll_position})")
                
                # SHORT wait for content to render (no need for scroll animation delay)
                time.sleep(wait_time)
                
                # Take screenshot with unique filename to prevent conflicts
                frame_path = os.path.join(frames_dir, f"{unique_id}_frame_{i:03d}.png")
                page.screenshot(path=frame_path, full_page=False)
                
                if i % 10 == 0:  # Log every 10th frame
                    logger.info(f"   Frame {i+1}/{num_frames} at {scroll_position:.0f}px (MICRO: {scroll_height/num_frames:.1f}px/frame)")
            
            browser.close()
        
        # STEP 8: Create video with ffmpeg (MICRO-SCROLLING - NO interpolation)
        logger.info("🎬 Assembling frames into MICRO-SCROLLING video...")
        
        success = _assemble_frames_to_video(
            frames_dir, unique_id, output_video, target_fps, target_duration
        )
        
        if success:
            # Cleanup frames
            _cleanup_scroll_temp_files(frames_dir)
            return output_video
        else:
            return None
            
    except Exception as e:
        logger.error(f"❌ Error creating advanced scroll video: {str(e)}")
        return None


def _detect_content_availability(page):
    """
    Detect if there's actual content available on the page
    """
    try:
        # Check for "No results" or similar indicators
        no_results_selectors = [
            "text=No results found",
            "text=Aucun résultat",
            "text=No content available",
            "text=Nothing found",
            "[data-testid='no-results']",
            ".no-results",
            ".empty-state"
        ]
        
        has_no_results = False
        for selector in no_results_selectors:
            try:
                element = page.wait_for_selector(selector, timeout=2000)
                if element and element.is_visible():
                    has_no_results = True
                    break
            except:
                continue
        
        # Check for actual movie/content cards
        content_selectors = [
            "[data-testid='movie-card']",
            ".movie-card",
            ".content-card", 
            "[class*='card']",
            "[class*='movie']",
            "[class*='item']"
        ]
        
        content_count = 0
        for selector in content_selectors:
            try:
                elements = page.query_selector_all(selector)
                content_count += len(elements)
            except:
                continue
        
        # Get total page height to determine scroll requirements
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        
        return {
            "has_content": not has_no_results and content_count > 0,
            "content_count": content_count,
            "has_no_results": has_no_results,
            "page_height": page_height,
            "viewport_height": viewport_height,
            "needs_scrolling": page_height > viewport_height * 1.5
        }
        
    except Exception as e:
        logger.warning(f"Content detection failed: {str(e)}")
        return {
            "has_content": True,  # Assume content exists
            "content_count": 0,
            "has_no_results": False,
            "page_height": 3000,
            "viewport_height": 800,
            "needs_scrolling": True
        }


def _calculate_optimal_scroll_height(viewport_height: int, page_height: int, scroll_distance: float) -> int:
    """
    Calculate OPTIMAL scroll height for smooth scrolling
    """
    # OPTIMAL SCROLL CALCULATION
    # Rule: scroll_distance * viewport height for natural scrolling speed
    optimal_scroll = viewport_height * scroll_distance
    
    # Cap based on actual page content, but prioritize smooth speed
    max_reasonable_scroll = min(page_height * 0.7, optimal_scroll * 1.2)  # Don't exceed 70% of page or 1.2x optimal
    
    scroll_height = min(optimal_scroll, max_reasonable_scroll)
    
    # Ensure minimum scrolling for very short pages
    if scroll_height < viewport_height * 1.5:
        scroll_height = viewport_height * 1.5
    
    logger.info(f"📏 OPTIMAL SCROLL CALCULATION:")
    logger.info(f"   Viewport height: {viewport_height}px")
    logger.info(f"   Page height: {page_height}px")
    logger.info(f"   Optimal scroll ({scroll_distance}x viewport): {optimal_scroll:.0f}px")
    logger.info(f"   Final scroll height: {scroll_height:.0f}px")
    logger.info(f"   Scroll speed: {scroll_height/4:.0f}px/second (SMOOTH!)")
    
    return int(scroll_height)


def _handle_cookies(page):
    """Handle cookie banners"""
    try:
        cookie_banner = page.wait_for_selector("text=We use cookies", timeout=5000)
        if cookie_banner:
            logger.info("🍪 Handling cookie banner")
            essential_button = page.wait_for_selector("button:has-text('Essential Only')", timeout=3000)
            if essential_button:
                essential_button.click()
                time.sleep(2)
    except:
        pass  # No cookies banner
    
    # Remove cookie elements
    page.evaluate("""() => {
        const elements = document.querySelectorAll('*');
        for (const el of elements) {
            if (el.textContent && el.textContent.includes('cookies') && 
                (el.style.position === 'fixed' || el.style.position === 'absolute' || 
                 getComputedStyle(el).position === 'fixed' || getComputedStyle(el).position === 'absolute')) {
                el.style.display = 'none';
            }
        }
    }""")
    
    time.sleep(1)


def _assemble_frames_to_video(frames_dir: str, unique_id: str, output_video: str, target_fps: int, target_duration: int) -> bool:
    """Assemble frames into video using FFmpeg"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(target_fps),
            "-i", f"{frames_dir}/{unique_id}_frame_%03d.png",
            "-c:v", "libx264",
            "-profile:v", "high",
            "-crf", "12",  # HIGHEST quality for readable text
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1080:1920",  # Simple scaling only - NO interpolation
            "-t", str(target_duration),  # Force exact duration
            "-preset", "slow",  # Best quality encoding
            output_video
        ]
        
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Get actual video info to verify duration
        video_info = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", output_video],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        actual_duration = float(video_info.stdout.decode().strip())
        
        logger.info(f"✅ MICRO-SCROLLING VIDEO CREATED!")
        logger.info(f"   File: {output_video}")
        logger.info(f"   Target duration: {target_duration} seconds")
        logger.info(f"   Actual duration: {actual_duration:.2f} seconds")
        logger.info(f"   Native FPS: {target_fps} (NO interpolation)")
        logger.info(f"   Quality: CRF 12 (maximum quality for readable text)")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg error: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        logger.error("❌ FFmpeg not installed. Please install it:")
        logger.error("   macOS: brew install ffmpeg")
        logger.error("   Ubuntu: sudo apt-get install ffmpeg")
        logger.error("   Windows: Download from https://ffmpeg.org/")
        return False


def _cleanup_scroll_temp_files(frames_dir: str):
    """Clean up temporary scroll files"""
    try:
        import shutil
        shutil.rmtree(frames_dir)
        logger.info(f"🗑️ Cleaned up frames directory: {frames_dir}/")
    except Exception as e:
        logger.warning(f"⚠️ Failed to cleanup frames directory: {str(e)}")