"""
StreamGank Enhanced Movie Poster Generator - LEGACY MIGRATION COMPLETE

This module handles creating enhanced movie poster cards with metadata overlays
for TikTok/Instagram Reels format (9:16 portrait).

LEGACY MIGRATION COMPLETE - Uses the exact same sophisticated poster creation
as the original legacy system with all cinematic effects and advanced typography.

Features:
- Professional cinematic poster enhancement with advanced visual effects
- Blurred background that fills entire canvas with thematic overlays
- Cinematic vignette effects, dramatic shadows, and lighting effects
- Platform-specific badges with gradients and glows
- Sophisticated typography with multiple shadow layers
- Optimized for social media formats (9:16 portrait)
- Cloudinary upload and optimization
- Error handling and validation
- Configurable via settings

Author: StreamGank Development Team
Version: 2.0.0 - Legacy Migration Complete
"""

import os
import re
import math
import logging
import textwrap
import glob
from typing import Dict, List, Optional, Any
# Import platform module with specific alias to avoid conflicts
import platform as system_platform
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor
from pathlib import Path
import cloudinary
import cloudinary.uploader

from config.settings import get_video_settings, get_api_config
from utils.validators import is_valid_url
from utils.file_utils import ensure_directory, cleanup_temp_files

logger = logging.getLogger(__name__)

# =============================================================================
# CINEMATIC POSTER EFFECTS - LEGACY FUNCTIONS
# =============================================================================

def _get_thematic_colors(platform: str, genres: List[str], title: str) -> Dict[str, tuple]:
    """Get thematic colors based on platform, genres, and title"""
    # Platform-based base colors
    platform_themes = {
        'Netflix': {'primary': (229, 9, 20), 'secondary': (139, 0, 0)},
        'Max': {'primary': (0, 229, 255), 'secondary': (0, 100, 139)}, 
        'Prime Video': {'primary': (0, 168, 225), 'secondary': (0, 80, 120)},
        'Disney+': {'primary': (17, 60, 207), 'secondary': (10, 30, 100)},
        'Hulu': {'primary': (28, 231, 131), 'secondary': (10, 120, 60)},
        'Apple TV+': {'primary': (27, 27, 27), 'secondary': (60, 60, 60)}
    }
    
    # Genre-based mood colors
    genre_moods = {
        'Horror': {'primary': (139, 0, 0), 'secondary': (60, 0, 0)},
        'Horreur': {'primary': (139, 0, 0), 'secondary': (60, 0, 0)},
        'Thriller': {'primary': (75, 0, 130), 'secondary': (30, 0, 60)},
        'Drama': {'primary': (25, 25, 112), 'secondary': (10, 10, 50)},
        'Action': {'primary': (255, 69, 0), 'secondary': (180, 30, 0)},
        'Comedy': {'primary': (255, 165, 0), 'secondary': (200, 100, 0)},
        'Fantasy': {'primary': (148, 0, 211), 'secondary': (80, 0, 120)},
        'Fantastique': {'primary': (148, 0, 211), 'secondary': (80, 0, 120)}
    }
    
    # Title-specific themes
    title_themes = {
        'Wednesday': {'primary': (139, 0, 139), 'secondary': (70, 0, 70)},
        'Stranger Things': {'primary': (220, 20, 60), 'secondary': (120, 10, 30)},
        'The Last of Us': {'primary': (85, 107, 47), 'secondary': (40, 50, 20)}
    }
    
    # Priority: Title > Genre > Platform
    if title in title_themes:
        return title_themes[title]
    elif any(genre in genre_moods for genre in genres):
        matching_genre = next(genre for genre in genres if genre in genre_moods)
        return genre_moods[matching_genre]
    elif platform in platform_themes:
        return platform_themes[platform]
    else:
        return {'primary': (60, 60, 100), 'secondary': (30, 30, 50)}

def _add_thematic_gradient(canvas: Image.Image, colors: Dict[str, tuple]):
    """Add thematic gradient overlay to canvas"""
    width, height = canvas.size
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    primary = colors['primary']
    secondary = colors['secondary']
    
    # Create vertical gradient
    for y in range(height):
        # Gradient from top (secondary) to bottom (primary)
        ratio = y / height
        r = int(secondary[0] + (primary[0] - secondary[0]) * ratio)
        g = int(secondary[1] + (primary[1] - secondary[1]) * ratio)
        b = int(secondary[2] + (primary[2] - secondary[2]) * ratio)
        alpha = int(40 + 30 * ratio)  # Increasing opacity towards bottom
        
        draw.line([(0, y), (width, y)], fill=(r, g, b, alpha))
    
    canvas.paste(overlay, (0, 0), overlay)

def _add_vignette_effect(canvas: Image.Image):
    """Add cinematic vignette effect"""
    width, height = canvas.size
    vignette = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    
    # Create radial vignette
    center_x, center_y = width // 2, height // 2
    max_distance = ((width // 2) ** 2 + (height // 2) ** 2) ** 0.5
    
    for x in range(0, width, 10):  # Step by 10 for performance
        for y in range(0, height, 10):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            alpha = int((distance / max_distance) * 120)  # Max 120 alpha at edges
            if alpha > 0:
                draw.rectangle([x, y, x+10, y+10], fill=(0, 0, 0, min(alpha, 120)))
    
    canvas.paste(vignette, (0, 0), vignette)

def _add_light_rays(canvas: Image.Image, center_x: int, center_y: int):
    """Add subtle light rays effect"""
    width, height = canvas.size
    rays = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rays)
    
    # Create light rays emanating from center
    for angle in range(0, 360, 45):  # 8 rays
        rad = math.radians(angle)
        end_x = center_x + int(400 * math.cos(rad))
        end_y = center_y + int(400 * math.sin(rad))
        
        # Create gradient line (light ray)
        for i in range(20):  # Width of ray
            offset_x = int(i * math.cos(rad + math.pi/2) / 2)
            offset_y = int(i * math.sin(rad + math.pi/2) / 2)
            alpha = max(0, 30 - i)  # Fade towards edges
            
            draw.line([
                (center_x + offset_x, center_y + offset_y),
                (end_x + offset_x, end_y + offset_y)
            ], fill=(255, 255, 255, alpha), width=1)
    
    canvas.paste(rays, (0, 0), rays)

def format_votes(votes):
    """Format votes with proper k/M suffix based on magnitude"""

    if not isinstance(votes, (int, float)):
        return str(votes)
    
    votes = int(votes)  # Ensure integer for proper formatting

    if votes < 1000:
        # Less than 1000: Show as-is (e.g., 800 → "800")
        return str(votes)
    elif votes < 10000:
        # 1000-9999: Show as X.Xk (e.g., 8240 → "8.2k")
        return f"{votes/1000:.1f}k"
    elif votes < 1000000:
        # 10000-999999: Show as XXXk (e.g., 82400 → "82k", 234567 → "235k")  
        return f"{int(votes/1000)}k"
    elif votes < 10000000:
        # 1M-9.9M: Show as X.XM (e.g., 1500000 → "1.5M", 8240000 → "8.2M")
        return f"{votes/1000000:.1f}M"
    elif votes < 100000000:
        # 10M-99.9M: Show as XX.XM (e.g., 15000000 → "15.0M", 25600000 → "25.6M")
        return f"{votes/1000000:.1f}M"
    else:
        # 100M+: Show as XXXM (e.g., 156000000 → "156M")
        return f"{int(votes/1000000)}M"

# =============================================================================
# MAIN POSTER CREATION FUNCTIONS - LEGACY MIGRATED
# =============================================================================

def create_enhanced_movie_poster(movie_data: Dict, output_dir: str = "streamgank-reels/enhanced-poster-cover") -> Optional[str]:
    """
    Create an enhanced movie poster card with metadata overlay for TikTok/Instagram Reels
    
    LEGACY MIGRATION COMPLETE - This is the exact same function as the working legacy system
    
    This function creates a professional movie poster card that includes:
    1. Original poster with preserved aspect ratio (no distortion)
    2. Beautiful metadata display below the poster
    3. Platform badge, genres, IMDb score, runtime, year
    4. Optimized for 9:16 portrait format (1080x1920)
    
    Args:
        movie_data (Dict): Movie information including poster_url, title, platform, etc.
        output_dir (str): Directory to save the enhanced poster
        
    Returns:
        str: Path to the enhanced poster image or None if failed
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract movie information
        title = movie_data.get('title', 'Unknown Movie')
        year = str(movie_data.get('year', ''))
        platform = movie_data.get('platform', '')
        genres = movie_data.get('genres', [])
        imdb_score = movie_data.get('imdb_score', 0)
        runtime = movie_data.get('runtime', '0 min')
        imdb_votes = movie_data.get('imdb_votes', 0)
        poster_url = movie_data.get('poster_url') or movie_data.get('cloudinary_poster_url', '')
        
        logger.info(f"🎨 Creating enhanced poster card for: {title}")
        logger.info(f"   Platform: {platform} | IMDb: {imdb_score}/10 | Year: {year}")
        
        if not poster_url:
            logger.warning(f"⚠️ No poster URL for {title}")
            return None
        
        # Canvas dimensions (9:16 portrait for TikTok/Instagram Reels)
        canvas_width = 1080
        canvas_height = 1920
        
        # Create canvas with cinematic background
        canvas = Image.new('RGB', (canvas_width, canvas_height), color='#0f0f23')
        draw = ImageDraw.Draw(canvas)
        
        # 🎨 GODLIKE DESIGNER MODE: Create cinematic masterpiece
        poster_downloaded = False
        try:
            response = requests.get(poster_url, timeout=30)
            response.raise_for_status()
            
            poster_image = Image.open(BytesIO(response.content))
            poster_image = poster_image.convert('RGBA')
            poster_downloaded = True
            
            logger.info(f"   🎨 Creating CINEMATIC MASTERPIECE for: {title}")
            
            # Step 1: Create blurred background that fills entire canvas
            logger.info(f"   🌫️ Creating Gaussian blur background extension")
            
            # Create blurred background that COMPLETELY fills canvas (fix bottom gap)
            # Scale to cover entire canvas height AND width
            scale_w = canvas_width / poster_image.width
            scale_h = canvas_height / poster_image.height
            scale = max(scale_w, scale_h)  # Use larger scale to ensure full coverage
            
            new_bg_width = int(poster_image.width * scale)
            new_bg_height = int(poster_image.height * scale)
            bg_poster = poster_image.resize((new_bg_width, new_bg_height), Image.Resampling.LANCZOS)
            
            # Create blurred background
            blurred_bg = bg_poster.filter(ImageFilter.GaussianBlur(radius=25))
            
            # Apply dark overlay to blurred background
            dark_overlay = Image.new('RGBA', blurred_bg.size, (0, 0, 0, 160))
            blurred_bg = Image.alpha_composite(blurred_bg.convert('RGBA'), dark_overlay)
            
            # Center the blurred background to ensure full canvas coverage
            bg_x = (canvas_width - new_bg_width) // 2
            bg_y = (canvas_height - new_bg_height) // 2
            
            # Paste ensuring complete coverage (may overflow edges, which is fine)
            canvas.paste(blurred_bg, (bg_x, bg_y), blurred_bg)
            
            # Step 2: Add thematic gradient overlay based on movie theme
            logger.info(f"   🎭 Adding thematic overlays for {platform}")
            
            # Create thematic gradient based on platform and genre
            thematic_colors = _get_thematic_colors(platform, genres, title)
            _add_thematic_gradient(canvas, thematic_colors)
            
            # Step 3: Add cinematic vignette effect
            _add_vignette_effect(canvas)
            
            # Calculate main poster dimensions (preserve aspect ratio) 
            poster_max_width = int(canvas_width * 0.75)  # 75% width for main poster
            poster_max_height = int(canvas_height * 0.50)  # 50% height for main poster
            
            # Resize main poster while maintaining aspect ratio
            poster_ratio = poster_image.width / poster_image.height
            if poster_ratio > poster_max_width / poster_max_height:
                new_width = poster_max_width
                new_height = int(new_width / poster_ratio)
            else:
                new_height = poster_max_height
                new_width = int(new_height * poster_ratio)
            
            poster_image = poster_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Step 4: Add cinematic lighting effects to main poster
            logger.info(f"   ✨ Adding cinematic lighting effects")
            
            # Create dramatic shadow
            shadow = Image.new('RGBA', (new_width + 40, new_height + 40), (0, 0, 0, 140))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
            
            # Position main poster
            poster_x = int((canvas_width - new_width) / 2)
            poster_y = 60   # Higher positioning for better composition
            
            # Paste shadow and main poster
            canvas.paste(shadow, (poster_x - 20, poster_y + 20), shadow)
            canvas.paste(poster_image, (poster_x, poster_y), poster_image)
            
            # Step 5: Add subtle light rays effect
            _add_light_rays(canvas, poster_x + new_width//2, poster_y)
            
            logger.info(f"   📐 Main poster: {new_width}x{new_height} (cinematic composition)")
            
        except Exception as e:
            logger.error(f"❌ Failed to download/process poster: {str(e)}")
            poster_downloaded = False
            # Create cinematic placeholder
            new_width, new_height = 600, 900  # Larger placeholder
            poster_x = int((canvas_width - new_width) / 2)
            poster_y = 60
            
            # Create gradient placeholder background
            for y in range(canvas_height):
                alpha = int(100 * (1 - y / canvas_height))
                color = (40, 40, 60, alpha)
                draw.line([(0, y), (canvas_width, y)], fill=color[:3])
            
            draw.rectangle([poster_x, poster_y, poster_x + new_width, poster_y + new_height], 
                          fill='#2a2a3a', outline='#4a4a5a', width=3)
            draw.text((poster_x + new_width//2, poster_y + new_height//2), "CINEMATIC\\nPOSTER", 
                     fill='white', anchor='mm')
        
        # Get font sizes from settings configuration
        settings = get_video_settings()
        font_config = settings.get('font_sizes', {})
        
        # Use configured font sizes (with fallbacks)
        title_size = font_config.get('title', 72)        # Was 52, now 72 (40% larger)
        platform_size = font_config.get('subtitle', 48)  # Was 36, now 48 (33% larger)
        metadata_size = font_config.get('metadata', 36)  # Same as before
        small_size = font_config.get('rating', 32)       # Same as before
        
        # Load fonts with BOLD title font using CONFIGURED SIZES
        logger.info(f"   🔤 Loading fonts with sizes: Title={title_size}, Platform={platform_size}, Metadata={metadata_size}, Small={small_size}")
        
        try:
            # Try Windows fonts first
            title_font = ImageFont.truetype("arialbd.ttf", title_size)      # BOLD title font - LARGER
            platform_font = ImageFont.truetype("arial.ttf", platform_size) # Platform badge - LARGER
            metadata_font = ImageFont.truetype("arial.ttf", metadata_size) # Metadata values
            small_font = ImageFont.truetype("arial.ttf", small_size)       # Labels
            logger.info("   ✅ Successfully loaded Windows Arial fonts")
        except Exception as e1:
            logger.warning(f"   ⚠️ Windows Arial fonts not found: {e1}")
            try:
                # Try macOS fonts
                title_font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", title_size)  # BOLD
                platform_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", platform_size)
                metadata_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", metadata_size)
                small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", small_size)
                logger.info("   ✅ Successfully loaded macOS Arial fonts")
            except Exception as e2:
                logger.warning(f"   ⚠️ macOS Arial fonts not found: {e2}")
                try:
                    # Try common Linux fonts
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_size)
                    platform_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", platform_size)
                    metadata_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", metadata_size)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", small_size)
                    logger.info("   ✅ Successfully loaded Linux DejaVu fonts")
                except Exception as e3:
                    logger.warning(f"   ⚠️ Linux DejaVu fonts not found: {e3}")
                    try:
                        # Try Windows Calibri as alternative
                        title_font = ImageFont.truetype("calibrib.ttf", title_size)
                        platform_font = ImageFont.truetype("calibri.ttf", platform_size)
                        metadata_font = ImageFont.truetype("calibri.ttf", metadata_size)
                        small_font = ImageFont.truetype("calibri.ttf", small_size)
                        logger.info("   ✅ Successfully loaded Windows Calibri fonts")
                    except Exception as e4:
                        logger.warning(f"   ⚠️ Windows Calibri fonts not found: {e4}")
                        # Enhanced fallback - try to find ANY available system font
                        logger.error("   ❌ All common fonts failed, searching for any available system font...")
                        
                        # Try to find any available TrueType font on the system
                        font_found = False
                        try:
                            system_name = system_platform.system().lower()
                            logger.info(f"   🖥️ Detected system: {system_name}")
                        except Exception as e_platform:
                            logger.warning(f"   ⚠️ Could not detect system platform: {e_platform}")
                            # Default to generic paths if platform detection fails
                            system_name = 'unknown'
                        
                        # Common font search paths by OS
                        font_paths = []
                        if system_name == 'windows':
                            font_paths = [
                                "C:/Windows/Fonts/*.ttf",
                                "C:/Windows/Fonts/*.TTF"
                            ]
                        elif system_name == 'darwin':  # macOS
                            font_paths = [
                                "/System/Library/Fonts/*.ttf",
                                "/Library/Fonts/*.ttf"
                            ]
                        else:  # Linux/Docker/Unknown
                            font_paths = [
                                # Standard Linux paths
                                "/usr/share/fonts/*/*.ttf",
                                "/usr/share/fonts/*/*/*.ttf",
                                "/usr/local/share/fonts/*.ttf",
                                # Docker/Alpine specific paths
                                "/usr/share/fonts/truetype/*/*.ttf",
                                "/usr/share/fonts/TTF/*.ttf",
                                "/usr/share/fonts/truetype/dejavu/*.ttf",
                                # Additional common paths
                                "/usr/share/fonts/liberation/*.ttf",
                                "/usr/share/fonts/noto/*.ttf",
                                "/opt/fonts/*.ttf"
                            ]
                        
                        # Try to find any font
                        for pattern in font_paths:
                            try:
                                fonts = glob.glob(pattern)
                                logger.info(f"   🔍 Searching pattern: {pattern}, found {len(fonts) if fonts else 0} fonts")
                                
                                if fonts and len(fonts) > 0:
                                    try:
                                        # Use the first available font
                                        font_file = fonts[0]
                                        logger.info(f"   🔤 Attempting to load font: {font_file}")
                                        
                                        title_font = ImageFont.truetype(font_file, title_size)
                                        platform_font = ImageFont.truetype(font_file, platform_size)
                                        metadata_font = ImageFont.truetype(font_file, metadata_size)
                                        small_font = ImageFont.truetype(font_file, small_size)
                                        logger.info(f"   ✅ Found and loaded system font: {font_file}")
                                        font_found = True
                                        break
                                    except Exception as ef:
                                        logger.warning(f"   ⚠️ Failed to load found font {font_file}: {ef}")
                                        continue
                            except Exception as e_glob:
                                logger.warning(f"   ⚠️ Error searching pattern {pattern}: {e_glob}")
                                continue
                        
                        if not font_found:
                            # Last resort: Use PIL's built-in font rendering 
                            logger.error("   ❌ No system fonts found - using PIL default fonts")
                            try:
                                # Use PIL's default font (this should always work)
                                default_font = ImageFont.load_default()
                                title_font = default_font
                                platform_font = default_font
                                metadata_font = default_font
                                small_font = default_font
                                logger.warning("   ⚠️ Using default PIL font - text will be enhanced with multiple draws for visibility")
                                
                                # Log font details for debugging
                                logger.info(f"   🔤 Default font type: {type(default_font)}")
                                
                            except Exception as e_default:
                                logger.error(f"   ❌ Even default font failed: {e_default}")
                                # This should never happen, but create a minimal fallback
                                logger.error("   🆘 Creating emergency text fallback...")
                                # We'll handle this in the text drawing by skipping text if fonts fail completely
                                title_font = None
                                platform_font = None
                                metadata_font = None
                                small_font = None
                
        logger.info(f"   🔤 Font sizes: Title={title_size}, Platform={platform_size}, Metadata={metadata_size}, Small={small_size}")
        
        # Helper function to draw enhanced text (especially for default fonts)
        def draw_enhanced_text(draw, position, text, font, fill='#FFFFFF', shadow_color='#000000', bold_effect=False):
            """Draw text with enhanced visibility, shadows, and optional bold effect"""
            x, y = position
            
            # Handle case where font loading completely failed
            if font is None:
                logger.warning(f"   ⚠️ Skipping text '{text}' - no font available")
                return
            
            # Check if we're using default font (which is very small)
            try:
                is_default_font = (font == ImageFont.load_default() or 
                                 str(type(font)) == "<class 'PIL.ImageFont.DefaultFont'>" or
                                 getattr(font, 'path', None) is None)
            except:
                # If comparison fails, assume it's a proper font
                is_default_font = False
            
            # For default fonts, draw larger by using multiple overlapping draws
            if is_default_font:
                # Create a "larger" effect by drawing text in a pattern
                offsets = [(0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2), (2, 1), (1, 2), (2, 2)]
                
                # Draw shadow layers
                for offset in offsets:
                    draw.text((x + 3 + offset[0], y + 3 + offset[1]), text, fill=shadow_color, font=font)
                    draw.text((x + 1 + offset[0], y + 1 + offset[1]), text, fill='#333333', font=font)
                
                # Draw main text with pattern for size
                for offset in offsets:
                    draw.text((x + offset[0], y + offset[1]), text, fill=fill, font=font)
                
                # Additional bold effect for titles
                if bold_effect:
                    extra_offsets = [(3, 0), (0, 3), (3, 1), (1, 3), (3, 3)]
                    for offset in extra_offsets:
                        draw.text((x + offset[0], y + offset[1]), text, fill=fill, font=font)
            else:
                # Normal rendering for proper fonts
                # Draw shadow layers for depth
                draw.text((x + 3, y + 3), text, fill=shadow_color, font=font)  # Deep shadow
                draw.text((x + 1, y + 1), text, fill='#333333', font=font)     # Mid shadow
                
                # Main text
                draw.text((x, y), text, fill=fill, font=font)
                
                # Bold effect for titles (draw multiple times with slight offsets)
                if bold_effect:
                    draw.text((x + 1, y), text, fill=fill, font=font)     # Bold effect 1
                    draw.text((x, y + 1), text, fill=fill, font=font)     # Bold effect 2
                    draw.text((x + 1, y + 1), text, fill=fill, font=font) # Bold effect 3
                    draw.text((x, y - 1), text, fill='#F8F8F8', font=font) # Highlight
        
        # 🎨 CINEMATIC METADATA SECTION - PERFECT SPACING
        metadata_start_y = poster_y + new_height + 90  # Perfect breathing room from poster
        
        logger.info(f"   🎭 Creating cinematic text backgrounds")
        
        # Step 6: Draw BOLD title text WITHOUT background
        title_lines = textwrap.wrap(title, width=22)  # Wrap long titles
        current_y = metadata_start_y
        
        # Draw BOLD title text with cinematic effects (NO BACKGROUND)
        for line in title_lines[:2]:
            if title_font is not None:
                try:
                    bbox = draw.textbbox((0, 0), line, font=title_font)
                    text_width = bbox[2] - bbox[0]
                    text_x = int((canvas_width - text_width) / 2)
                    
                    # Use enhanced text drawing with bold effect
                    draw_enhanced_text(draw, (text_x, current_y), line, title_font, fill='#FFFFFF', bold_effect=True)
                except Exception as e_title:
                    logger.warning(f"   ⚠️ Failed to draw title text '{line}': {e_title}")
                    # Draw simple text without bbox calculation
                    text_x = int(canvas_width / 2) - len(line) * 10  # Rough centering
                    draw_enhanced_text(draw, (text_x, current_y), line, title_font, fill='#FFFFFF', bold_effect=True)
            else:
                logger.warning(f"   ⚠️ Skipping title line '{line}' - no font available")
            
            current_y += int(title_size * 1.2)  # Dynamic spacing based on title font size
        
        # Step 7: Create cinematic platform badge
        platform_y = current_y + 30  # More spacing after title
        if platform:
            platform_colors = {
                'Netflix': '#E50914', 'Max': '#00E5FF', 'Prime Video': '#00A8E1',
                'Disney+': '#113CCF', 'Hulu': '#1CE783', 'Apple TV+': '#1B1B1B'
            }
            
            platform_color = platform_colors.get(platform, '#FF6B35')
            display_platform = platform if len(platform) <= 12 else platform[:10] + "..."
            
            # Create cinematic platform badge with multiple effects
            if platform_font is not None:
                try:
                    platform_bbox = draw.textbbox((0, 0), display_platform, font=platform_font)
                    text_width = platform_bbox[2] - platform_bbox[0]
                except:
                    # Fallback text width calculation
                    text_width = len(display_platform) * platform_size * 0.6
            else:
                text_width = len(display_platform) * platform_size * 0.6
                
            platform_width = int(text_width) + 50
            platform_height = int(platform_size * 1.5)  # Dynamic height based on font size
            platform_x = int((canvas_width - platform_width) / 2)
            
            # Outer glow (multiple layers for cinema effect)
            for i in range(6, 0, -1):
                glow_alpha = max(20, 80 - i * 10)
                glow_color = ImageColor.getrgb(platform_color) + (glow_alpha,)
                draw.rounded_rectangle([
                    platform_x - i, platform_y - i, 
                    platform_x + platform_width + i, platform_y + platform_height + i
                ], radius=20 + i, fill=glow_color[:3])
            
            # Main badge with gradient effect
            badge_bg = Image.new('RGBA', (platform_width, platform_height), (0, 0, 0, 0))
            badge_draw = ImageDraw.Draw(badge_bg)
            
            # Create vertical gradient for badge
            base_color = ImageColor.getrgb(platform_color)
            for y in range(platform_height):
                ratio = y / platform_height
                # Darker at top, lighter at bottom
                r = int(base_color[0] * (0.7 + 0.3 * ratio))
                g = int(base_color[1] * (0.7 + 0.3 * ratio))
                b = int(base_color[2] * (0.7 + 0.3 * ratio))
                badge_draw.line([(0, y), (platform_width, y)], fill=(r, g, b))
            
            # Apply subtle blur and paste
            badge_bg = badge_bg.filter(ImageFilter.GaussianBlur(radius=1))
            
            # Create badge shape
            draw.rounded_rectangle([platform_x, platform_y, platform_x + platform_width, platform_y + platform_height], 
                                 radius=18, fill=platform_color)
            
            # Platform text with enhanced effects
            text_center_x = platform_x + platform_width // 2
            text_center_y = platform_y + platform_height // 2
            
            # Enhanced platform text (manually center since we can't use anchor with our function)
            if platform_font is not None:
                try:
                    platform_bbox = draw.textbbox((0, 0), display_platform, font=platform_font)
                    platform_text_width = platform_bbox[2] - platform_bbox[0]
                    platform_text_height = platform_bbox[3] - platform_bbox[1]
                    centered_x = text_center_x - platform_text_width // 2
                    centered_y = text_center_y - platform_text_height // 2
                except:
                    # Fallback positioning
                    centered_x = text_center_x - len(display_platform) * platform_size // 4
                    centered_y = text_center_y - platform_size // 2
                
                draw_enhanced_text(draw, (centered_x, centered_y), display_platform, platform_font, fill='white')
            else:
                logger.warning(f"   ⚠️ Skipping platform badge text - no font available")
            
            current_y = platform_y + platform_height + int(platform_size * 0.8)  # Dynamic spacing after platform
        
        # Step 8: Draw genres text WITHOUT background
        if genres and metadata_font is not None:
            genres_text = " • ".join(genres[:3])
            try:
                genres_bbox = draw.textbbox((0, 0), genres_text, font=metadata_font)
                genres_width = genres_bbox[2] - genres_bbox[0]
                text_x = int((canvas_width - genres_width) / 2)
            except:
                # Fallback positioning
                text_x = int(canvas_width / 2) - len(genres_text) * metadata_size // 4
            
            # Genres text with enhanced effects (NO BACKGROUND)
            draw_enhanced_text(draw, (text_x, current_y), genres_text, metadata_font, fill='#F5F5F5')
            
            current_y += int(metadata_size * 1.7)  # Dynamic spacing after genres
        elif genres:
            logger.warning(f"   ⚠️ Skipping genres text - no font available")
        
        # Step 9: Create ROUNDED and TRANSPARENT metadata panel
        metadata_y = current_y + 30  # More spacing before metadata
        
        formatted_votes = format_votes(imdb_votes)
        
        metadata_items = [
            ("Date:", str(year)),
            ("IMDb:", f"{imdb_score}/10"),
            ("Votes:", formatted_votes),  # ✅ FIXED: Proper vote formatting
            ("Time:", runtime)
        ]
        
        # Create ROUNDED metadata background panel
        panel_width = canvas_width - 120
        panel_height = len(metadata_items) * 50 + 30  # Adjusted for new spacing
        panel_x = 60
        panel_y = metadata_y - 15
        
        # Create ROUNDED metadata panel with TRANSPARENT background
        metadata_bg = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        metadata_draw = ImageDraw.Draw(metadata_bg)
        
        # Create ROUNDED background with MUCH MORE TRANSPARENCY
        if poster_downloaded:
            # Very subtle thematic color
            primary = thematic_colors['primary'][:3]
            bg_color = primary + (40,)  # Very low alpha for transparency
        else:
            bg_color = (20, 20, 30, 40)  # Very transparent dark
        
        # Draw rounded rectangle background
        metadata_draw.rounded_rectangle([0, 0, panel_width, panel_height], radius=20, fill=bg_color)
        
        # Apply minimal blur for glass effect
        metadata_bg = metadata_bg.filter(ImageFilter.GaussianBlur(radius=1))
        canvas.paste(metadata_bg, (panel_x, panel_y), metadata_bg)
        
        # Display metadata with cinematic typography using enhanced text
        for i, (label, value) in enumerate(metadata_items):
            item_y = metadata_y + (i * 50)  # Slightly tighter spacing
            
            # Left side - Labels with enhanced styling
            if small_font is not None:
                label_x = 140
                draw_enhanced_text(draw, (label_x, item_y), label, small_font, fill='#C0C0C0')
            
            # Right side - Values with enhanced effects
            if metadata_font is not None:
                try:
                    value_bbox = draw.textbbox((0, 0), value, font=metadata_font)
                    value_width = value_bbox[2] - value_bbox[0]
                    value_x = 940 - value_width
                except:
                    # Fallback positioning
                    value_x = 940 - len(value) * metadata_size // 2
                
                # Enhanced value text with extra highlight
                draw_enhanced_text(draw, (value_x, item_y), value, metadata_font, fill='#FFFFFF')
                # Extra highlight for values (only if font is available)
                try:
                    draw.text((value_x, item_y - 1), value, fill='#F8F8F8', font=metadata_font)
                except:
                    pass  # Skip highlight if it fails
        
        # Save enhanced poster
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title.lower()).strip('_')
        output_path = os.path.join(output_dir, f"enhanced_poster_{clean_title}_{year}.png")
        canvas.save(output_path, 'PNG', quality=95)
        
        logger.info(f"✅ Enhanced poster card created: {output_path}")
        logger.info(f"   🎨 Style: Professional TikTok/Reels format")
        logger.info(f"   📐 Dimensions: {canvas_width}x{canvas_height} (9:16 portrait)")
        logger.info(f"   🖼️ Poster: Aspect ratio preserved, no distortion")
        
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating enhanced poster for {title}: {str(e)}")
        return None 

def create_enhanced_movie_posters(movie_data: List[Dict], max_movies: int = 3) -> Dict[str, str]:
    """
    Create enhanced movie poster cards for all movies with metadata overlays.
    
    LEGACY MIGRATION COMPLETE - Uses sophisticated cinematic poster creation
    
    Args:
        movie_data (List[Dict]): List of movie data dictionaries
        max_movies (int): Maximum number of movies to process
        
    Returns:
        Dict[str, str]: Dictionary mapping movie titles to enhanced poster URLs
    """
    enhanced_poster_urls = {}
    temp_dir = "streamgank-reels/enhanced-poster-cover"  # Save to streamgank-reels folder structure
    
    logger.info(f"🎨 Creating enhanced movie posters for {min(len(movie_data), max_movies)} movies")
    logger.info("🎬 Style: Professional TikTok/Instagram Reels format")
    logger.info("📐 Dimensions: 1080x1920 (9:16 portrait)")
    logger.info(f"💾 Save Location: {temp_dir} (local) + streamgank-reels/enhanced-poster-cover/ (Cloudinary)")
    
    try:
        # Create temporary directory
        ensure_directory(temp_dir)
        
        # Process up to max_movies
        for i, movie in enumerate(movie_data[:max_movies]):
            try:
                title = movie.get('title', f'Movie_{i+1}')
                
                logger.info(f"🖼️ Processing poster {i+1}: {title}")
                
                # Generate enhanced poster using legacy function
                enhanced_path = create_enhanced_movie_poster(movie, temp_dir)
                
                if enhanced_path:
                    # Upload to Cloudinary
                    enhanced_url = _upload_poster_to_cloudinary(enhanced_path, title, i+1)
                    
                    if enhanced_url:
                        enhanced_poster_urls[title] = enhanced_url
                        logger.info(f"✅ Enhanced poster created for: {title}")
                    else:
                        logger.error(f"❌ Failed to upload enhanced poster for: {title}")
                else:
                    logger.error(f"❌ Failed to create enhanced poster for: {title}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing poster for movie {i+1}: {str(e)}")
                continue
        
        # Note: Not cleaning up files as they're saved to permanent streamgank-reels folder
        # cleanup_temp_files(temp_dir)  # Commented out - keeping enhanced posters permanently
        
        logger.info(f"🎨 Successfully created {len(enhanced_poster_urls)} enhanced posters")
        return enhanced_poster_urls
        
    except Exception as e:
        logger.error(f"❌ Error in create_enhanced_movie_posters: {str(e)}")
        # cleanup_temp_files(temp_dir)  # Not cleaning up - permanent storage folder
        return {}

# =============================================================================
# CLOUDINARY UPLOAD FUNCTIONS
# =============================================================================

def _upload_poster_to_cloudinary(poster_path: str, title: str, movie_num: int) -> Optional[str]:
    """
    Upload enhanced poster to Cloudinary.
    
    Args:
        poster_path (str): Path to enhanced poster file
        title (str): Movie title for naming
        movie_num (int): Movie number for unique naming
        
    Returns:
        str: Cloudinary URL or None if failed
    """
    try:
        # Configure Cloudinary
        cloudinary_config = get_api_config('cloudinary')
        
        if not cloudinary_config:
            logger.error("❌ Cloudinary configuration not available")
            return None
        
        # Generate unique public ID
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_').lower()[:30]  # Limit length
        
        public_id = f"enhanced_{safe_title}_{movie_num}"  # Clean public ID without folder path
        
        # Upload to Cloudinary (using folder parameter like movie clips)
        result = cloudinary.uploader.upload(
            poster_path,
            public_id=public_id,
            folder="streamgank-reels/enhanced-poster-cover",  # Separate folder parameter
            resource_type="image",
            format="jpg",
            overwrite=True,  # Allow overwrite like movie clips
            fetch_format="auto",
            transformation=[
                {'width': 1080, 'height': 1920, 'crop': 'fill'},
                {'quality': 'auto:good'}  # Quality only in transformation, not as parameter
            ],
            tags=["streamgank", "enhanced_poster", "movie"]
        )
        
        cloudinary_url = result.get('secure_url')
        actual_public_id = result.get('public_id')
        folder_used = result.get('folder')
        
        if cloudinary_url:
            logger.info(f"✅ Successfully uploaded enhanced poster to Cloudinary: {cloudinary_url}")
            logger.info(f"   📁 Actual folder: {folder_used}")
            logger.info(f"   🆔 Actual public_id: {actual_public_id}")
            logger.info(f"   🖼️ Enhanced poster available at: streamgank-reels/enhanced-poster-cover/{public_id}")
            return cloudinary_url
        else:
            logger.error(f"❌ Cloudinary upload failed for {poster_path}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error uploading enhanced poster {poster_path} to Cloudinary: {str(e)}")
        return None