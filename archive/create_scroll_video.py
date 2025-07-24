#!/usr/bin/env python3
"""
Script to create a scrolling video of StreamGank in responsive (mobile) mode. 
The script captures a series of images during the scroll and assembles them into a video.
DYNAMICALLY CAPTURES CONTENT BASED ON QUERY FILTERS.
"""

import os
import time
import logging
import subprocess
from playwright.sync_api import sync_playwright
# Import StreamGank helper function for URL building
from streamgank_helpers import build_streamgank_url

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def detect_content_availability(page):
    """
    Detect if there's actual content available on the page
    
    Args:
        page: Playwright page object
        
    Returns:
        dict: Information about content availability
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

def create_scroll_video(
    country="FR",
    genre="Horreur", 
    platform="Netflix",
    content_type="Série",
    target_duration=6,  # FIXED: Always 6 seconds duration
    output_video=None,  # Will be auto-generated based on filters
    scroll_height=None,  # Will be calculated dynamically
    device_name="iPhone 12 Pro Max",
    smooth_scroll=True,  # Enable micro-scrolling (not CSS smooth)
    scroll_distance=1.5  # MUCH SHORTER: Readable micro-scrolling
):
    """
    Create a DYNAMIC scrolling video of StreamGank with MICRO-SCROLLING for readability.
    NO MORE DISTORTION - Uses tiny scroll increments for natural reading experience!
    
    Args:
        country: Country filter
        genre: Genre filter  
        platform: Platform filter
        content_type: Content type filter
        target_duration: Fixed video duration in seconds (default: 6)
        output_video: Output video filename
        scroll_height: Max scroll height (calculated dynamically if None)
        device_name: Mobile device to simulate
        smooth_scroll: Enable micro-scrolling animation (NOT CSS smooth)
        scroll_distance: Viewport height multiplier for scroll amount (default: 1.5 = minimal readable)
        
    Returns:
        str: Path to created video file, or None if failed
    """
    # Generate unique filename based on filter parameters (prevent duplicates!)
    if output_video is None:
        # Create unique filename based on all parameters
        safe_country = country.replace(" ", "").replace("/", "-")
        safe_genre = genre.replace(" ", "").replace("/", "-")
        safe_platform = platform.replace(" ", "").replace("/", "-")
        safe_content = content_type.replace(" ", "").replace("/", "-")
        
        output_video = f"scroll_{safe_country}_{safe_genre}_{safe_platform}_{safe_content}_{scroll_distance}x.mp4"
    
    logger.info(f"📝 Unique filename: {output_video}")
    logger.info(f"🎯 DYNAMIC SCROLL VIDEO GENERATION (SMOOTH: {smooth_scroll})")
    logger.info(f"   Parameters: {country} | {genre} | {platform} | {content_type}")
    logger.info(f"   Speed: Ultra | Distance: {scroll_distance}x")
    
    # Create unique frames directory per process to avoid conflicts
    import time
    import random
    unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
    frames_dir = f"scroll_frames_{unique_id}"
    os.makedirs(frames_dir, exist_ok=True)
    
    logger.info(f"📁 Using unique frames directory: {frames_dir}")
    logger.info(f"   🛡️ Multi-script safe - no frame conflicts!")
    
    # STEP 1: Try the ACTUAL FILTERED URL first (this is the key change!)
    filtered_url = build_streamgank_url(country, genre, platform, content_type)
    fallback_url = build_streamgank_url(country=country, genre=None, platform=None, content_type=None)
    
    logger.info(f"🎯 DYNAMIC SCROLL VIDEO GENERATION (SMOOTH: {smooth_scroll})")
    logger.info(f"   🎬 FIXED DURATION: {target_duration} seconds")
    logger.info(f"   Primary (filtered): {filtered_url}")
    logger.info(f"   Fallback (homepage): {fallback_url}")
    logger.info(f"   Scroll Speed: Ultra")
    
    # Clean old frames
    for file in os.listdir(frames_dir):
        if file.endswith(".png"):
            os.remove(os.path.join(frames_dir, file))
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
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
        
        # STEP 2: Try filtered URL first
        url_to_use = filtered_url
        use_fallback = False
        
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
            content_info = detect_content_availability(page)
            
            logger.info(f"📊 Content Analysis:")
            logger.info(f"   Has content: {content_info['has_content']}")
            logger.info(f"   Content count: {content_info['content_count']}")
            logger.info(f"   Page height: {content_info['page_height']}px")
            logger.info(f"   Needs scrolling: {content_info['needs_scrolling']}")
            
            # STEP 4: Decide if we need fallback
            if not content_info['has_content'] or content_info['has_no_results']:
                logger.warning("⚠️ No content found with filters, falling back to homepage")
                use_fallback = True
            else:
                logger.info("🎉 Using filtered results for scroll video!")
                # Calculate OPTIMAL scroll height for smooth 6-second scrolling
                if scroll_height is None:
                    viewport_height = content_info['viewport_height']
                    page_height = content_info['page_height']
                    
                    # OPTIMAL SCROLL CALCULATION FOR 6 SECONDS
                    # Rule: 2.5x viewport height for natural scrolling speed
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
                    logger.info(f"   Optimal scroll (2.5x viewport): {optimal_scroll:.0f}px")
                    logger.info(f"   Final scroll height: {scroll_height:.0f}px")
                    logger.info(f"   Scroll speed: {scroll_height/6:.0f}px/second (SMOOTH!)")
                    
                    if not content_info['needs_scrolling']:
                        # Very short page - use minimal scrolling
                        scroll_height = viewport_height * 1.2
                        logger.info(f"   ⚠️ Short page detected - using minimal scroll: {scroll_height:.0f}px")
                
        except Exception as e:
            logger.warning(f"⚠️ Error with filtered URL: {str(e)}")
            use_fallback = True
        
        # STEP 5: Use fallback if needed
        if use_fallback:
            try:
                logger.info(f"🔄 Falling back to homepage: {fallback_url}")
                page.goto(fallback_url)
                page.wait_for_selector("text=StreamGank", timeout=10000)
                url_to_use = fallback_url
                
                time.sleep(2)
                content_info = detect_content_availability(page)
                
                # Set OPTIMAL scroll parameters for homepage using same logic
                if scroll_height is None:
                    viewport_height = content_info['viewport_height']
                    page_height = content_info['page_height']
                    
                    # Use same optimal calculation as filtered page
                    optimal_scroll = viewport_height * scroll_distance
                    max_reasonable_scroll = min(page_height * 0.7, optimal_scroll * 1.2)
                    scroll_height = min(optimal_scroll, max_reasonable_scroll)
                    
                    # Ensure minimum scrolling
                    if scroll_height < viewport_height * 1.5:
                        scroll_height = viewport_height * 1.5
                    
                    logger.info(f"📏 FALLBACK SCROLL CALCULATION:")
                    logger.info(f"   Viewport height: {viewport_height}px")
                    logger.info(f"   Optimal scroll: {scroll_height:.0f}px")
                    logger.info(f"   Scroll speed: {scroll_height/6:.0f}px/second")
                
            except Exception as e:
                logger.error(f"❌ Even fallback failed: {str(e)}")
                browser.close()
                return None
        
        # STEP 6: Handle cookies
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
        
        # STEP 7: Configure ULTRA 60 FPS MICRO-SCROLLING (simplified - no speed options!)
        wait_time = 0.04  # Ultra-fast capture timing
        target_fps = 60   # 60 FPS ultra-smooth!
        
        # CALCULATE FRAMES FOR EXACTLY 6 SECONDS WITH 60 FPS MICRO-SCROLLING
        final_fps = target_fps  # NO motion interpolation - use native 60fps
        num_frames = target_duration * target_fps  # 6 * 60 = 360 frames for ultra-smoothness
        
        num_frames = int(num_frames)  # Ensure it's an integer
        
        logger.info(f"🎬 MICRO-SCROLLING CALCULATION:")
        logger.info(f"   Target duration: {target_duration} seconds")
        logger.info(f"   Micro-scroll FPS: {target_fps}")
        logger.info(f"   Total frames: {num_frames}")
        logger.info(f"   Pixels per frame: {scroll_height/num_frames:.1f}px (MICRO!)")
        logger.info(f"   Wait per frame: {wait_time:.2f}s (READABLE)")
        
        # STEP 8: Capture frames with MICRO-SCROLLING (no CSS smooth!)
        logger.info(f"📸 Capturing {num_frames} frames with MICRO-SCROLLING")
        logger.info(f"   Scroll height: {scroll_height:.0f}px (SHORT & READABLE)")
        logger.info(f"   URL being captured: {url_to_use}")
        
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
    
    # STEP 9: Create video with ffmpeg (MICRO-SCROLLING - NO interpolation)
    logger.info("🎬 Assembling frames into MICRO-SCROLLING 6-second video...")
    
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
        logger.info(f"   Frames captured: {num_frames}")
        logger.info(f"   Native FPS: {final_fps} (NO interpolation)")
        logger.info(f"   Quality: CRF 12 (maximum quality for readable text)")
        logger.info(f"   Scroll distance: {scroll_distance}x viewport (MINIMAL)")
        logger.info(f"   Pixels per frame: {scroll_height/num_frames:.1f}px (MICRO!)")
        logger.info(f"   Content: {'Filtered results' if not use_fallback else 'Homepage fallback'}")
        logger.info(f"   URL captured: {url_to_use}")
        
        # 🗑️ CLEANUP: Delete all screenshot frames after successful video creation
        try:
            import shutil
            shutil.rmtree(frames_dir)
            logger.info(f"🗑️ Cleaned up {num_frames} screenshot frames from {frames_dir}/")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup frames directory: {str(e)}")
        
        return output_video
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg error: {e.stderr.decode()}")
        return None
    except FileNotFoundError:
        logger.error("❌ FFmpeg not installed. Please install it:")
        logger.error("   macOS: brew install ffmpeg")
        logger.error("   Ubuntu: sudo apt-get install ffmpeg")
        logger.error("   Windows: Download from https://ffmpeg.org/")
        return None

def smooth_ease_in_out(t):
    """
    Smooth easing function for natural scroll animation
    
    Args:
        t: Progress from 0 to 1
        
    Returns:
        float: Eased progress from 0 to 1
    """
    # Cubic ease-in-out: starts slow, speeds up, then slows down
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2

def gentle_ease_in_out(t):
    """
    GENTLER easing function for natural scroll animation
    
    Args:
        t: Progress from 0 to 1
        
    Returns:
        float: Eased progress from 0 to 1
    """
    # Quadratic ease-in-out: starts slow, speeds up, then slows down
    if t < 0.5:
        return 2 * t * t
    else:
        return 1 - pow(-2 * t + 2, 2) / 2

if __name__ == "__main__":
    video_path = create_scroll_video()
    if video_path:
        logger.info(f"✅ Video generated successfully: {video_path}")
    else:
        logger.error("❌ Failed to create video")
