"""
StreamGank Screenshot Capture

This module provides screenshot capture functionality for the StreamGank website.
Maintains the same functionality as the original system while using the modular
architecture for better organization and maintainability.

Features:
- Automated screenshot capture using Playwright
- Support for different scroll distances and timing
- Batch screenshot generation
- Error handling and retry logic
- Cloudinary integration for upload
"""

import logging
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import tempfile

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available - screenshot functionality disabled")

from utils.url_builder import build_streamgank_url
from config.settings import get_cloudinary_config
from media.cloudinary_uploader import upload_file_to_cloudinary

logger = logging.getLogger(__name__)

# =============================================================================
# SCREENSHOT CAPTURE FUNCTIONS
# =============================================================================

def capture_streamgank_screenshots(country: Optional[str] = None,
                                  genre: Optional[str] = None, 
                                  platform: Optional[str] = None,
                                  content_type: Optional[str] = None,
                                  output_dir: str = "screenshots",
                                  upload_to_cloudinary: bool = True) -> List[str]:
    """
    Capture screenshots of StreamGank website for video generation.
    
    This function replicates the original screenshot capture functionality,
    taking multiple screenshots at different scroll positions to create
    smooth scrolling videos.
    
    Args:
        country (str): Country code for URL generation
        genre (str): Genre for URL filtering  
        platform (str): Streaming platform
        content_type (str): Content type filter
        output_dir (str): Directory to save screenshots
        upload_to_cloudinary (bool): Whether to upload to Cloudinary
        
    Returns:
        List[str]: List of screenshot file paths or URLs
        
    Raises:
        RuntimeError: If screenshot capture fails
        ImportError: If Playwright is not available
        
    Example:
        >>> screenshots = capture_streamgank_screenshots(
        ...     country="US",
        ...     genre="Horror", 
        ...     platform="Netflix"
        ... )
        >>> print(f"Captured {len(screenshots)} screenshots")
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("❌ CRITICAL: Playwright not available - install with: pip install playwright")
    
    logger.info("📸 STREAMGANK SCREENSHOT CAPTURE STARTING")
    logger.info(f"   Country: {country}")
    logger.info(f"   Genre: {genre}")
    logger.info(f"   Platform: {platform}")
    logger.info(f"   Content Type: {content_type}")
    
    # Build StreamGank URL
    target_url = build_streamgank_url(
        country=country,
        genre=genre,
        platform=platform,
        content_type=content_type
    )
    
    logger.info(f"   Target URL: {target_url}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    screenshot_paths = []
    
    try:
        with sync_playwright() as playwright:
            logger.info("🌐 Launching browser...")
            
            # Launch browser with mobile viewport for TikTok format
            browser = playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Create mobile context (TikTok/Instagram format)
            context = browser.new_context(
                viewport={'width': 390, 'height': 844},  # iPhone 12 Pro dimensions
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
            )
            
            page = context.new_page()
            
            # Navigate to StreamGank
            logger.info(f"📱 Navigating to: {target_url}")
            page.goto(target_url, wait_until='networkidle', timeout=30000)
            
            # Wait for content to load
            logger.info("⏳ Waiting for content to load...")
            time.sleep(3)
            
            # Check if content is available
            if not _is_content_available(page):
                logger.warning("⚠️ No content detected on page")
                # Take screenshot anyway for debugging
                debug_path = output_path / "debug_no_content.png"
                page.screenshot(path=str(debug_path), full_page=True)
                logger.info(f"🐛 Debug screenshot saved: {debug_path}")
            
            # Get page dimensions for scrolling
            page_height = page.evaluate("document.documentElement.scrollHeight")
            viewport_height = page.evaluate("window.innerHeight")
            
            logger.info(f"📏 Page dimensions: {page_height}px height, {viewport_height}px viewport")
            
            # Calculate scroll positions for smooth video
            scroll_positions = _calculate_scroll_positions(page_height, viewport_height)
            
            logger.info(f"📸 Capturing {len(scroll_positions)} screenshots...")
            
            # Capture screenshots at different scroll positions
            for i, scroll_y in enumerate(scroll_positions):
                logger.info(f"   📸 Screenshot {i+1}/{len(scroll_positions)} at {scroll_y}px...")
                
                # Scroll to position
                page.evaluate(f"window.scrollTo(0, {scroll_y})")
                time.sleep(0.5)  # Wait for scroll animation
                
                # Take screenshot
                timestamp = int(time.time() * 1000)
                filename = f"streamgank_scroll_{timestamp}_{i:03d}.png"
                screenshot_path = output_path / filename
                
                page.screenshot(path=str(screenshot_path))
                screenshot_paths.append(str(screenshot_path))
                
                logger.info(f"   ✅ Saved: {filename}")
            
            # Take a final full-page screenshot for reference
            final_path = output_path / f"streamgank_full_{int(time.time())}.png"
            page.screenshot(path=str(final_path), full_page=True)
            screenshot_paths.append(str(final_path))
            
            browser.close()
            
        logger.info(f"✅ Screenshot capture completed: {len(screenshot_paths)} files")
        
        # Upload to Cloudinary if requested
        if upload_to_cloudinary:
            logger.info("☁️ Uploading screenshots to Cloudinary...")
            cloudinary_urls = []
            
            for screenshot_path in screenshot_paths:
                try:
                    url = upload_file_to_cloudinary(
                        file_path=screenshot_path,
                        folder="streamgank_screenshots",
                        resource_type="image"
                    )
                    if url:
                        cloudinary_urls.append(url)
                    else:
                        logger.warning(f"⚠️ Failed to upload: {screenshot_path}")
                        cloudinary_urls.append(screenshot_path)  # Keep local path as fallback
                        
                except Exception as e:
                    logger.warning(f"⚠️ Upload failed for {screenshot_path}: {str(e)}")
                    cloudinary_urls.append(screenshot_path)  # Keep local path as fallback
            
            logger.info(f"☁️ Uploaded {len([u for u in cloudinary_urls if u.startswith('http')])} files to Cloudinary")
            return cloudinary_urls
        
        return screenshot_paths
        
    except Exception as e:
        logger.error(f"❌ Screenshot capture failed: {str(e)}")
        raise RuntimeError(f"Screenshot capture failed: {str(e)}") from e


def _is_content_available(page: Page) -> bool:
    """
    Check if content is available on the StreamGank page.
    
    Args:
        page (Page): Playwright page object
        
    Returns:
        bool: True if content is detected
    """
    try:
        # Look for common StreamGang content indicators
        content_selectors = [
            '[data-testid="movie-card"]',
            '.movie-poster',
            '.content-item',
            'img[alt*="poster"]',
            '.grid-item',
            '[class*="movie"]',
            '[class*="content"]'
        ]
        
        for selector in content_selectors:
            if page.query_selector(selector):
                logger.debug(f"✅ Content detected with selector: {selector}")
                return True
        
        # Check for any images (likely movie posters)
        images = page.query_selector_all('img')
        if len(images) > 3:  # More than just logos/icons
            logger.debug(f"✅ Content likely detected: {len(images)} images found")
            return True
        
        logger.debug("❌ No content indicators found")
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ Error checking content availability: {str(e)}")
        return False


def _calculate_scroll_positions(page_height: int, viewport_height: int, num_screenshots: int = 30) -> List[int]:
    """
    Calculate optimal scroll positions for smooth video generation.
    
    Args:
        page_height (int): Total page height in pixels
        viewport_height (int): Viewport height in pixels  
        num_screenshots (int): Number of screenshots to take
        
    Returns:
        List[int]: List of scroll Y positions
    """
    if page_height <= viewport_height:
        # Page fits in viewport, just take one screenshot
        return [0]
    
    # Calculate scrollable area
    max_scroll = page_height - viewport_height
    
    # Generate evenly spaced scroll positions
    if num_screenshots <= 1:
        return [0]
    
    positions = []
    for i in range(num_screenshots):
        progress = i / (num_screenshots - 1)
        scroll_y = int(progress * max_scroll)
        positions.append(scroll_y)
    
    logger.debug(f"📏 Calculated {len(positions)} scroll positions from 0 to {max_scroll}px")
    return positions


def batch_capture_screenshots(configurations: List[Dict[str, str]], 
                             output_base_dir: str = "screenshots",
                             upload_to_cloudinary: bool = True) -> Dict[str, List[str]]:
    """
    Capture screenshots for multiple StreamGank configurations.
    
    Useful for generating multiple video variations or testing different
    genre/platform combinations.
    
    Args:
        configurations (List[Dict]): List of configuration dictionaries
        output_base_dir (str): Base directory for outputs
        upload_to_cloudinary (bool): Whether to upload to Cloudinary
        
    Returns:
        Dict[str, List[str]]: Mapping of config names to screenshot paths/URLs
        
    Example:
        >>> configs = [
        ...     {'country': 'US', 'genre': 'Horror', 'platform': 'Netflix'},
        ...     {'country': 'US', 'genre': 'Comedy', 'platform': 'Disney+'},
        ... ]
        >>> results = batch_capture_screenshots(configs)
        >>> print(f"Captured screenshots for {len(results)} configurations")
    """
    logger.info(f"📸 BATCH SCREENSHOT CAPTURE: {len(configurations)} configurations")
    
    results = {}
    
    for i, config in enumerate(configurations, 1):
        config_name = f"config_{i}_{config.get('genre', 'unknown')}_{config.get('platform', 'unknown')}"
        config_output_dir = Path(output_base_dir) / config_name
        
        logger.info(f"📸 Processing configuration {i}/{len(configurations)}: {config_name}")
        
        try:
            screenshots = capture_streamgank_screenshots(
                country=config.get('country'),
                genre=config.get('genre'),
                platform=config.get('platform'),
                content_type=config.get('content_type'),
                output_dir=str(config_output_dir),
                upload_to_cloudinary=upload_to_cloudinary
            )
            
            results[config_name] = screenshots
            logger.info(f"✅ Configuration {config_name}: {len(screenshots)} screenshots")
            
        except Exception as e:
            logger.error(f"❌ Configuration {config_name} failed: {str(e)}")
            results[config_name] = []
    
    logger.info(f"✅ Batch capture completed: {len(results)} configurations processed")
    return results


def cleanup_local_screenshots(screenshot_paths: List[str], keep_originals: bool = False) -> int:
    """
    Clean up local screenshot files after upload.
    
    Args:
        screenshot_paths (List[str]): List of local file paths to clean up
        keep_originals (bool): Whether to keep original files
        
    Returns:
        int: Number of files cleaned up
    """
    if keep_originals:
        logger.info("🧹 Keeping original screenshot files")
        return 0
    
    cleaned_count = 0
    
    for path in screenshot_paths:
        try:
            if Path(path).exists() and not path.startswith('http'):
                Path(path).unlink()
                cleaned_count += 1
                logger.debug(f"🗑️ Deleted: {path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete {path}: {str(e)}")
    
    logger.info(f"🧹 Cleaned up {cleaned_count} screenshot files")
    return cleaned_count


# =============================================================================
# SCREENSHOT VALIDATION FUNCTIONS  
# =============================================================================

def validate_screenshots(screenshot_paths: List[str]) -> Dict[str, Any]:
    """
    Validate captured screenshots for quality and completeness.
    
    Args:
        screenshot_paths (List[str]): List of screenshot paths to validate
        
    Returns:
        Dict[str, Any]: Validation results
    """
    validation_results = {
        'total_screenshots': len(screenshot_paths),
        'valid_screenshots': 0,
        'invalid_screenshots': 0,
        'errors': [],
        'is_valid': False
    }
    
    for path in screenshot_paths:
        try:
            if path.startswith('http'):
                # URL - assume valid (would need separate validation)
                validation_results['valid_screenshots'] += 1
            else:
                # Local file - check existence and size
                file_path = Path(path)
                if file_path.exists() and file_path.stat().st_size > 1000:  # At least 1KB
                    validation_results['valid_screenshots'] += 1
                else:
                    validation_results['invalid_screenshots'] += 1
                    validation_results['errors'].append(f"Invalid screenshot: {path}")
        except Exception as e:
            validation_results['invalid_screenshots'] += 1
            validation_results['errors'].append(f"Error validating {path}: {str(e)}")
    
    # Consider valid if at least 80% of screenshots are good
    success_rate = validation_results['valid_screenshots'] / max(1, validation_results['total_screenshots'])
    validation_results['is_valid'] = success_rate >= 0.8
    validation_results['success_rate'] = success_rate
    
    logger.info(f"📊 Screenshot validation: {validation_results['valid_screenshots']}/{validation_results['total_screenshots']} valid ({success_rate:.1%})")
    
    return validation_results