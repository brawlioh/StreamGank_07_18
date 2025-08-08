"""
StreamGank Cloudinary Uploader

This module handles media uploads to Cloudinary with optimized transformations
for social media platforms, particularly TikTok/YouTube Shorts format.

Features:
- Poster upload with metadata and optimization
- Video clip upload with aspect ratio transformations
- Batch upload capabilities
- Retry logic and error handling
- Transformation presets for different platforms
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any
import cloudinary
import cloudinary.uploader
import cloudinary.api
from pathlib import Path

from config.settings import get_api_config
from utils.formatters import clean_filename
from utils.file_utils import get_file_info
from utils.validators import validate_file_path

logger = logging.getLogger(__name__)

# =============================================================================
# CLOUDINARY CONFIGURATION
# =============================================================================

def _ensure_cloudinary_config() -> bool:
    """
    Ensure Cloudinary is properly configured with API credentials.
    
    Returns:
        bool: True if configuration is valid
    """
    try:
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
        
        if not all([cloud_name, api_key, api_secret]):
            logger.error("❌ Missing Cloudinary configuration (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)")
            return False
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        
        logger.debug("✅ Cloudinary configuration validated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error configuring Cloudinary: {str(e)}")
        return False

# =============================================================================
# POSTER UPLOAD FUNCTIONS
# =============================================================================

def upload_poster_to_cloudinary(poster_path: str, 
                               movie_title: str, 
                               movie_id: str = None,
                               folder: str = "enhanced_posters") -> Optional[str]:
    """
    Upload enhanced movie poster to Cloudinary with optimization.
    
    Args:
        poster_path (str): Path to the poster image file
        movie_title (str): Movie title for naming
        movie_id (str): Movie ID for unique identification
        folder (str): Cloudinary folder name
        
    Returns:
        str: Cloudinary URL of uploaded poster or None if failed
    """
    try:
        if not _ensure_cloudinary_config():
            return None
        
        # Validate file
        file_validation = validate_file_path(poster_path, must_exist=True)
        if not file_validation['is_valid']:
            logger.error(f"❌ Invalid poster file: {poster_path}")
            return None
        
        # Create clean public ID
        clean_title = clean_filename(movie_title)
        public_id = f"{folder}/{clean_title}_{movie_id}" if movie_id else f"{folder}/{clean_title}"
        
        logger.info(f"🖼️ Uploading poster to Cloudinary: {poster_path}")
        logger.info(f"   Movie: {movie_title}")
        logger.info(f"   Public ID: {public_id}")
        
        # Get file info for logging
        file_info = get_file_info(poster_path)
        logger.info(f"   File size: {file_info['size_mb']:.1f} MB")
        
        # Upload with poster-optimized settings
        upload_result = cloudinary.uploader.upload(
            poster_path,
            public_id=public_id,
            folder=folder,
            resource_type="image",
            format="jpg",  # Convert to JPG for better compression
            quality="auto:good",  # Automatic quality optimization
            fetch_format="auto",  # Automatic format selection
            width=1080,  # Standard width
            height=1920,  # Standard height (9:16)
            crop="fit",  # Maintain aspect ratio
            background="auto",  # Auto background if needed
            tags=["enhanced_poster", "movie", clean_title],
            context={
                "movie_title": movie_title,
                "movie_id": str(movie_id) if movie_id else "",
                "type": "enhanced_poster"
            },
            overwrite=True,  # Allow overwriting existing uploads
            invalidate=True  # Invalidate CDN cache
        )
        
        if upload_result and 'secure_url' in upload_result:
            cloudinary_url = upload_result['secure_url']
            logger.info(f"✅ Poster uploaded successfully: {cloudinary_url}")
            logger.info(f"   Cloudinary public ID: {upload_result.get('public_id', 'Unknown')}")
            logger.info(f"   Final size: {upload_result.get('width', 0)}x{upload_result.get('height', 0)}")
            
            return cloudinary_url
        else:
            logger.error(f"❌ Upload succeeded but no URL returned")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error uploading poster {poster_path} to Cloudinary: {str(e)}")
        return None

# =============================================================================
# VIDEO CLIP UPLOAD FUNCTIONS
# =============================================================================

def upload_clip_to_cloudinary(clip_path: str, 
                             movie_title: str, 
                             movie_id: str = None,
                             transform_mode: str = "youtube_shorts",
                             folder: str = "movie_clips") -> Optional[str]:
    """
    Upload video clip to Cloudinary with platform-specific transformations.
    
    Args:
        clip_path (str): Path to the video clip file
        movie_title (str): Movie title for naming
        movie_id (str): Movie ID for unique identification
        transform_mode (str): Transformation mode ("youtube_shorts", "tiktok", "instagram", "fit")
        folder (str): Cloudinary folder name
        
    Returns:
        str: Cloudinary URL of uploaded clip or None if failed
    """
    try:
        if not _ensure_cloudinary_config():
            return None
        
        # Validate file
        file_validation = validate_file_path(clip_path, must_exist=True)
        if not file_validation['is_valid']:
            logger.error(f"❌ Invalid clip file: {clip_path}")
            return None
        
        # Create clean public ID
        clean_title = clean_filename(movie_title)
        public_id = f"{folder}/{clean_title}_{movie_id}_clip" if movie_id else f"{folder}/{clean_title}_clip"
        
        logger.info(f"🎬 Uploading clip to Cloudinary: {clip_path}")
        logger.info(f"   Movie: {movie_title}")
        logger.info(f"   Public ID: {public_id}")
        logger.info(f"   Transform mode: {transform_mode}")
        
        # Get file info for logging
        file_info = get_file_info(clip_path)
        logger.info(f"   File size: {file_info['size_mb']:.1f} MB")
        
        # Get transformation parameters
        transformation = get_cloudinary_transformation(transform_mode)
        
        # Upload with video-optimized settings (match legacy exactly)
        upload_result = cloudinary.uploader.upload(
            clip_path,
            public_id=public_id,
            folder=folder,
            resource_type="video",
            format="mp4",  # Standard MP4 format
            video_codec="h264",  # H.264 codec for compatibility
            audio_codec="aac",  # AAC audio codec
            transformation=transformation,  # Apply platform-specific transformations (legacy format)
            tags=["movie_clip", "highlight", clean_title, transform_mode],
            context={
                "movie_title": movie_title,
                "movie_id": str(movie_id) if movie_id else "",
                "type": "highlight_clip",
                "transform_mode": transform_mode
            },
            overwrite=True,  # Allow overwriting existing uploads
            invalidate=True  # Invalidate CDN cache
        )
        
        if upload_result and 'secure_url' in upload_result:
            cloudinary_url = upload_result['secure_url']
            logger.info(f"✅ Clip uploaded successfully: {cloudinary_url}")
            logger.info(f"   Cloudinary public ID: {upload_result.get('public_id', 'Unknown')}")
            logger.info(f"   Duration: {upload_result.get('duration', 0):.1f}s")
            logger.info(f"   Final size: {upload_result.get('width', 0)}x{upload_result.get('height', 0)}")
            
            return cloudinary_url
        else:
            logger.error(f"❌ Upload succeeded but no URL returned")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error uploading clip {clip_path} to Cloudinary: {str(e)}")
        return None

# =============================================================================
# TRANSFORMATION CONFIGURATIONS
# =============================================================================

def get_cloudinary_transformation(transform_mode: str) -> Dict[str, Any]:
    """
    Get Cloudinary transformation parameters for different platforms - ADVANCED MODES.
    
    YouTube Shorts optimized transformation modes (9:16 portrait - 1080x1920)
    from legacy streamgank_helpers.py with premium quality settings.
    
    Args:
        transform_mode (str): Platform or transformation type
        
    Returns:
        dict: Cloudinary transformation parameters
    """
    transformations = {
        # Basic fit mode (preserve aspect ratio with black bars) - LEGACY FORMAT
        "fit": [
            {"width": 1080, "height": 1920, "crop": "fit", "background": "black"},
            {"quality": "auto:best"},
            {"format": "mp4"},
            {"video_codec": "h264"},
            {"bit_rate": "2000k"}
        ],
        
        # Smart fit mode (intelligent cropping with center focus) - LEGACY FORMAT
        "smart_fit": [
            {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},
            {"quality": "auto:best"},
            {"format": "mp4"},
            {"video_codec": "h264"},
            {"bit_rate": "2500k"},
            {"flags": "progressive"}
        ],
        
        # Pad mode (smart padding with auto background) - LEGACY FORMAT
        "pad": [
            {"width": 1080, "height": 1920, "crop": "pad", "background": "auto"},
            {"quality": "auto:best"},
            {"format": "mp4"},
            {"bit_rate": "2000k"}
        ],
        
        # Scale mode (scale to fit, may distort) - LEGACY FORMAT
        "scale": [
            {"width": 1080, "height": 1920, "crop": "scale"},
            {"quality": "auto:best"},
            {"format": "mp4"},
            {"bit_rate": "1800k"}
        ],
        
        # YouTube Shorts optimized (PREMIUM QUALITY) - LEGACY FORMAT
        "youtube_shorts": [
            {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},
            {"quality": "auto:best"},
            {"format": "mp4"},
            {"video_codec": "h264"},
            {"bit_rate": "3000k"},
            {"flags": "progressive"},
            {"audio_codec": "aac"},
            {"audio_frequency": 48000}
        ],
        
        # TikTok optimized - LEGACY FORMAT
        "tiktok": [
            {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},
            {"quality": "auto:good"},
            {"format": "mp4"},
            {"video_codec": "h264"},
            {"bit_rate": "2000k"},
            {"audio_codec": "aac"}
        ],
        
        # Instagram Reels optimized - LEGACY FORMAT
        "instagram": [
            {"width": 1080, "height": 1920, "crop": "fill", "gravity": "center"},
            {"quality": "auto:good"},
            {"format": "mp4"},
            {"video_codec": "h264"},
            {"bit_rate": "2200k"},
            {"audio_codec": "aac"}
        ],
        
        # Auto mode (smart automatic optimization) - LEGACY FORMAT
        "auto": [
            {"width": 1080, "height": 1920, "crop": "auto", "gravity": "auto"},
            {"quality": "auto:best"},
            {"format": "auto"},
            {"video_codec": "auto"},
            {"bit_rate": "auto"}
        ]
    }
    
    return transformations.get(transform_mode, transformations["youtube_shorts"])

# =============================================================================
# BATCH UPLOAD FUNCTIONS
# =============================================================================

def batch_upload_assets(file_paths: List[str], 
                       asset_type: str = "auto",
                       folder: str = "batch_upload") -> Dict[str, str]:
    """
    Batch upload multiple assets to Cloudinary.
    
    Args:
        file_paths (List[str]): List of file paths to upload
        asset_type (str): Asset type ("poster", "clip", "auto")
        folder (str): Cloudinary folder name
        
    Returns:
        Dict[str, str]: Mapping of file paths to Cloudinary URLs
    """
    results = {}
    
    try:
        if not _ensure_cloudinary_config():
            return results
        
        logger.info(f"☁️ BATCH UPLOAD TO CLOUDINARY")
        logger.info(f"📋 Uploading {len(file_paths)} files")
        logger.info(f"🎯 Asset type: {asset_type}")
        logger.info(f"📁 Folder: {folder}")
        
        for i, file_path in enumerate(file_paths):
            try:
                file_name = Path(file_path).name
                logger.info(f"📤 Uploading {i+1}/{len(file_paths)}: {file_name}")
                
                # Determine asset type if auto
                detected_type = _detect_asset_type(file_path) if asset_type == "auto" else asset_type
                
                # Upload based on type
                if detected_type == "poster" or detected_type == "image":
                    cloudinary_url = upload_poster_to_cloudinary(
                        file_path, 
                        Path(file_path).stem, 
                        folder=folder
                    )
                elif detected_type == "clip" or detected_type == "video":
                    cloudinary_url = upload_clip_to_cloudinary(
                        file_path,
                        Path(file_path).stem,
                        folder=folder
                    )
                else:
                    logger.warning(f"⚠️ Unknown asset type for {file_path}")
                    continue
                
                if cloudinary_url:
                    results[file_path] = cloudinary_url
                    logger.info(f"✅ Uploaded: {file_name}")
                else:
                    logger.error(f"❌ Failed to upload: {file_name}")
                    
            except Exception as e:
                logger.error(f"❌ Error uploading {file_path}: {str(e)}")
                continue
        
        logger.info(f"🏁 BATCH UPLOAD COMPLETE: {len(results)}/{len(file_paths)} files uploaded")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in batch upload: {str(e)}")
        return results

# =============================================================================
# CLOUDINARY MANAGEMENT FUNCTIONS
# =============================================================================

def list_cloudinary_assets(folder: str = None, resource_type: str = "image") -> List[Dict]:
    """
    List assets in Cloudinary folder.
    
    Args:
        folder (str): Folder name to list (None for all)
        resource_type (str): Resource type ("image", "video", "raw")
        
    Returns:
        List[Dict]: List of asset information
    """
    try:
        if not _ensure_cloudinary_config():
            return []
        
        # Build search parameters
        search_params = {"resource_type": resource_type}
        if folder:
            search_params["prefix"] = folder
        
        # Get assets
        result = cloudinary.api.resources(**search_params)
        
        assets = []
        for resource in result.get('resources', []):
            assets.append({
                'public_id': resource.get('public_id'),
                'url': resource.get('secure_url'),
                'format': resource.get('format'),
                'size': resource.get('bytes', 0),
                'created': resource.get('created_at'),
                'width': resource.get('width'),
                'height': resource.get('height')
            })
        
        logger.info(f"📋 Found {len(assets)} assets in folder: {folder or 'all'}")
        return assets
        
    except Exception as e:
        logger.error(f"❌ Error listing Cloudinary assets: {str(e)}")
        return []


def delete_cloudinary_asset(public_id: str, resource_type: str = "image") -> bool:
    """
    Delete an asset from Cloudinary.
    
    Args:
        public_id (str): Cloudinary public ID
        resource_type (str): Resource type ("image", "video", "raw")
        
    Returns:
        bool: True if deletion was successful
    """
    try:
        if not _ensure_cloudinary_config():
            return False
        
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        
        if result.get('result') == 'ok':
            logger.info(f"✅ Deleted Cloudinary asset: {public_id}")
            return True
        else:
            logger.warning(f"⚠️ Could not delete asset: {public_id} - {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error deleting Cloudinary asset {public_id}: {str(e)}")
        return False

# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _detect_asset_type(file_path: str) -> str:
    """Detect asset type based on file extension."""
    try:
        extension = Path(file_path).suffix.lower()
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        
        if extension in image_extensions:
            return "poster"
        elif extension in video_extensions:
            return "clip"
        else:
            return "unknown"
            
    except Exception:
        return "unknown"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_cloudinary_config_status() -> Dict[str, Any]:
    """
    Get Cloudinary configuration status and information.
    
    Returns:
        Dict[str, Any]: Configuration status and details
    """
    status = {
        'configured': False,
        'cloud_name': None,
        'api_key_set': False,
        'api_secret_set': False,
        'connection_test': False
    }
    
    try:
        # Check environment variables
        status['cloud_name'] = os.getenv('CLOUDINARY_CLOUD_NAME')
        status['api_key_set'] = bool(os.getenv('CLOUDINARY_API_KEY'))
        status['api_secret_set'] = bool(os.getenv('CLOUDINARY_API_SECRET'))
        
        # Check if configured
        status['configured'] = all([
            status['cloud_name'],
            status['api_key_set'],
            status['api_secret_set']
        ])
        
        # Test connection if configured
        if status['configured']:
            try:
                cloudinary.api.ping()
                status['connection_test'] = True
            except Exception as e:
                logger.debug(f"Cloudinary connection test failed: {str(e)}")
        
        return status
        
    except Exception as e:
        logger.error(f"Error checking Cloudinary config: {str(e)}")
        return status


def optimize_existing_asset(public_id: str, 
                          resource_type: str = "image",
                          transform_mode: str = "auto") -> Optional[str]:
    """
    Optimize an existing Cloudinary asset with new transformations.
    
    Args:
        public_id (str): Cloudinary public ID
        resource_type (str): Resource type
        transform_mode (str): New transformation mode
        
    Returns:
        str: New optimized URL or None if failed
    """
    try:
        if not _ensure_cloudinary_config():
            return None
        
        # Get transformation parameters
        if resource_type == "video":
            transformation = get_cloudinary_transformation(transform_mode)
        else:
            transformation = {"quality": "auto:good", "fetch_format": "auto"}
        
        # Build URL with transformations
        if resource_type == "video":
            url = cloudinary.CloudinaryVideo(public_id).build_url(**transformation)
        else:
            url = cloudinary.CloudinaryImage(public_id).build_url(**transformation)
        
        logger.info(f"✅ Optimized asset URL: {url}")
        return url
        
    except Exception as e:
        logger.error(f"❌ Error optimizing asset {public_id}: {str(e)}")
        return None


def upload_enhanced_poster_to_cloudinary(poster_path: str, movie_title: str, movie_id: str = None) -> Optional[str]:
    """
    Upload an enhanced movie poster to Cloudinary with optimized transformations.
    
    Args:
        poster_path (str): Path to the enhanced poster image
        movie_title (str): Movie title for naming
        movie_id (str): Movie ID for unique identification
        
    Returns:
        str: Cloudinary URL of uploaded poster
        
    Raises:
        RuntimeError: If upload fails in STRICT mode
    """
    try:
        # STRICT MODE: Validate file path first
        if not validate_file_path(poster_path):
            error_msg = f"Invalid poster file path: {poster_path}"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
        # Ensure Cloudinary is configured
        if not _ensure_cloudinary_config():
            error_msg = "Cloudinary not configured"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
        # Create clean filename from movie title
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', movie_title.lower())
        clean_title = re.sub(r'_+', '_', clean_title).strip('_')
        
        # Create unique public ID
        public_id = f"enhanced_posters/{clean_title}_{movie_id}" if movie_id else f"enhanced_posters/{clean_title}"
        
        logger.info(f"☁️ STRICT MODE: Uploading enhanced poster to Cloudinary")
        logger.info(f"   File: {poster_path}")
        logger.info(f"   Movie: {movie_title}")
        logger.info(f"   Public ID: {public_id}")
        
        # Get file info for logging
        file_info = get_file_info(poster_path)
        logger.info(f"   File size: {file_info['size_mb']:.2f} MB")
        
        # Upload to Cloudinary with enhanced poster optimization
        upload_result = cloudinary.uploader.upload(
            poster_path,
            resource_type="image",
            public_id=public_id,
            folder="enhanced_posters",
            overwrite=True,
            quality="auto:best",
            format="png",
            transformation=[
                {"width": 1080, "height": 1920, "crop": "fit"},  # Ensure exact 9:16 dimensions
                {"quality": "auto:best"},
                {"fetch_format": "auto"}  # Optimize format for device
            ],
            tags=["enhanced_poster", "movie", "tiktok", "instagram", "portrait"]
        )
        
        cloudinary_url = upload_result.get('secure_url')
        if not cloudinary_url:
            error_msg = "No URL returned from Cloudinary upload"
            logger.error(f"❌ STRICT MODE: {error_msg}")
            raise RuntimeError(error_msg)
        
        logger.info(f"✅ Enhanced poster uploaded successfully: {cloudinary_url}")
        logger.info(f"   Cloudinary Public ID: {upload_result.get('public_id')}")
        logger.info(f"   Dimensions: {upload_result.get('width')}x{upload_result.get('height')}")
        
        return cloudinary_url
        
    except Exception as e:
        error_msg = f"Error uploading enhanced poster {poster_path}: {str(e)}"
        logger.error(f"❌ STRICT MODE: {error_msg}")
        raise RuntimeError(error_msg)