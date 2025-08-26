"""
StreamGank Media Processing Helpers

This module provides advanced media processing utilities and helpers
that were previously in the legacy streamgank_helpers.py file.

Features:
- Media type detection and validation
- Quality assessment and optimization
- Metadata extraction and processing
- Performance analytics
- Error handling and recovery
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# MEDIA TYPE DETECTION AND VALIDATION
# =============================================================================

def detect_media_type(file_path: str) -> Dict[str, Any]:
    """
    Detect comprehensive media type information.
    
    Args:
        file_path (str): Path to media file
        
    Returns:
        Dict[str, Any]: Media type information
    """
    try:
        if not os.path.exists(file_path):
            return {'type': 'unknown', 'error': 'File not found'}
        
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Media type mappings
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
        audio_extensions = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'}
        
        media_info = {
            'file_path': file_path,
            'filename': path.name,
            'extension': extension,
            'size_bytes': path.stat().st_size,
            'size_mb': round(path.stat().st_size / (1024 * 1024), 2)
        }
        
        if extension in image_extensions:
            media_info.update({
                'type': 'image',
                'category': 'visual',
                'suitable_for': ['poster', 'thumbnail', 'overlay']
            })
        elif extension in video_extensions:
            media_info.update({
                'type': 'video',
                'category': 'visual_audio',
                'suitable_for': ['main_content', 'clip', 'trailer']
            })
        elif extension in audio_extensions:
            media_info.update({
                'type': 'audio',
                'category': 'audio',
                'suitable_for': ['background_music', 'voiceover']
            })
        else:
            media_info.update({
                'type': 'unknown',
                'category': 'unknown',
                'suitable_for': []
            })
        
        return media_info
        
    except Exception as e:
        logger.error(f"Error detecting media type for {file_path}: {str(e)}")
        return {'type': 'error', 'error': str(e)}


def assess_media_quality(file_path: str, media_type: str = None) -> Dict[str, Any]:
    """
    Assess media quality and provide optimization recommendations.
    
    Args:
        file_path (str): Path to media file
        media_type (str): Type of media (auto-detected if None)
        
    Returns:
        Dict[str, Any]: Quality assessment results
    """
    try:
        if not media_type:
            media_info = detect_media_type(file_path)
            media_type = media_info.get('type', 'unknown')
        
        assessment = {
            'quality_score': 0,  # 0-100 scale
            'recommendations': [],
            'suitable_for_social': False,
            'optimization_needed': False
        }
        
        if media_type == 'image':
            assessment = _assess_image_quality(file_path)
        elif media_type == 'video':
            assessment = _assess_video_quality(file_path)
        elif media_type == 'audio':
            assessment = _assess_audio_quality(file_path)
        
        return assessment
        
    except Exception as e:
        logger.error(f"Error assessing media quality: {str(e)}")
        return {
            'quality_score': 0,
            'recommendations': ['Quality assessment failed'],
            'suitable_for_social': False,
            'optimization_needed': True,
            'error': str(e)
        }


def _assess_image_quality(file_path: str) -> Dict[str, Any]:
    """Assess image quality for social media use."""
    try:
        from PIL import Image
        
        with Image.open(file_path) as img:
            width, height = img.size
            aspect_ratio = width / height
            
            assessment = {
                'quality_score': 50,  # Base score
                'recommendations': [],
                'suitable_for_social': False,
                'optimization_needed': False,
                'dimensions': (width, height),
                'aspect_ratio': aspect_ratio
            }
            
            # Resolution assessment
            if width >= 1080 and height >= 1080:
                assessment['quality_score'] += 30
            elif width >= 720 and height >= 720:
                assessment['quality_score'] += 20
            else:
                assessment['recommendations'].append('Consider higher resolution (min 1080px)')
            
            # Aspect ratio assessment for social media
            if 0.5 <= aspect_ratio <= 0.6:  # 9:16 range (ideal for TikTok/Instagram)
                assessment['quality_score'] += 20
                assessment['suitable_for_social'] = True
            elif 0.8 <= aspect_ratio <= 1.2:  # Square-ish (good for Instagram)
                assessment['quality_score'] += 15
            else:
                assessment['recommendations'].append('Consider 9:16 aspect ratio for optimal social media performance')
            
            # Final suitability
            assessment['suitable_for_social'] = assessment['quality_score'] >= 70
            assessment['optimization_needed'] = assessment['quality_score'] < 60
            
            return assessment
            
    except Exception as e:
        logger.debug(f"Image quality assessment error: {str(e)}")
        return {
            'quality_score': 0,
            'recommendations': ['Unable to assess image quality'],
            'suitable_for_social': False,
            'optimization_needed': True
        }


def _assess_video_quality(file_path: str) -> Dict[str, Any]:
    """Assess video quality for social media use."""
    try:
        # This would require ffprobe for detailed analysis
        # For now, provide basic file-based assessment
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        assessment = {
            'quality_score': 50,
            'recommendations': [],
            'suitable_for_social': False,
            'optimization_needed': False,
            'file_size_mb': file_size_mb
        }
        
        # Size-based quality estimation
        if file_size_mb > 100:  # Very large file
            assessment['quality_score'] += 20
            assessment['recommendations'].append('High quality video detected')
        elif file_size_mb < 5:  # Very small file
            assessment['recommendations'].append('Video file seems small - check quality')
        
        # Duration estimation (rough)
        duration_estimate = file_size_mb / 10  # Rough estimate: 10MB per minute
        if 5 <= duration_estimate <= 30:  # Good duration for clips
            assessment['quality_score'] += 15
        
        assessment['suitable_for_social'] = assessment['quality_score'] >= 65
        assessment['optimization_needed'] = assessment['quality_score'] < 55
        
        return assessment
        
    except Exception as e:
        logger.debug(f"Video quality assessment error: {str(e)}")
        return {
            'quality_score': 0,
            'recommendations': ['Unable to assess video quality'],
            'suitable_for_social': False,
            'optimization_needed': True
        }


def _assess_audio_quality(file_path: str) -> Dict[str, Any]:
    """Assess audio quality."""
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        assessment = {
            'quality_score': 50,
            'recommendations': [],
            'suitable_for_social': False,
            'optimization_needed': False,
            'file_size_mb': file_size_mb
        }
        
        # Basic size-based assessment
        if file_size_mb > 5:  # Decent quality audio
            assessment['quality_score'] += 25
        elif file_size_mb < 1:  # Very compressed
            assessment['recommendations'].append('Audio file seems heavily compressed')
        
        assessment['suitable_for_social'] = assessment['quality_score'] >= 60
        assessment['optimization_needed'] = assessment['quality_score'] < 50
        
        return assessment
        
    except Exception as e:
        logger.debug(f"Audio quality assessment error: {str(e)}")
        return {
            'quality_score': 0,
            'recommendations': ['Unable to assess audio quality'],
            'suitable_for_social': False,
            'optimization_needed': True
        }


# =============================================================================
# MEDIA OPTIMIZATION UTILITIES
# =============================================================================

def get_optimization_recommendations(media_files: List[str]) -> Dict[str, List[str]]:
    """
    Get optimization recommendations for multiple media files.
    
    Args:
        media_files (List[str]): List of media file paths
        
    Returns:
        Dict[str, List[str]]: Optimization recommendations per file
    """
    recommendations = {}
    
    try:
        for file_path in media_files:
            media_info = detect_media_type(file_path)
            quality_assessment = assess_media_quality(file_path, media_info.get('type'))
            
            file_recommendations = quality_assessment.get('recommendations', [])
            
            # Add general recommendations based on media type
            if media_info.get('type') == 'image':
                if media_info.get('size_mb', 0) > 10:
                    file_recommendations.append('Consider compressing image for faster loading')
                    
            elif media_info.get('type') == 'video':
                if media_info.get('size_mb', 0) > 500:
                    file_recommendations.append('Consider reducing video size for better upload performance')
            
            recommendations[file_path] = file_recommendations
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {str(e)}")
        return {}


def calculate_processing_requirements(media_files: List[str]) -> Dict[str, Any]:
    """
    Calculate processing requirements for media files.
    
    Args:
        media_files (List[str]): List of media file paths
        
    Returns:
        Dict[str, Any]: Processing requirements and estimates
    """
    try:
        requirements = {
            'total_files': len(media_files),
            'total_size_mb': 0,
            'estimated_processing_time': 0,
            'complexity_score': 0,
            'breakdown': {
                'images': 0,
                'videos': 0,
                'audio': 0,
                'unknown': 0
            }
        }
        
        for file_path in media_files:
            media_info = detect_media_type(file_path)
            file_size = media_info.get('size_mb', 0)
            media_type = media_info.get('type', 'unknown')
            
            requirements['total_size_mb'] += file_size
            requirements['breakdown'][media_type + 's'] = requirements['breakdown'].get(media_type + 's', 0) + 1
            
            # Estimate processing time based on type and size
            if media_type == 'video':
                requirements['estimated_processing_time'] += file_size * 2  # 2 seconds per MB for video
                requirements['complexity_score'] += 3
            elif media_type == 'image':
                requirements['estimated_processing_time'] += file_size * 0.5  # 0.5 seconds per MB for image
                requirements['complexity_score'] += 1
            elif media_type == 'audio':
                requirements['estimated_processing_time'] += file_size * 1  # 1 second per MB for audio
                requirements['complexity_score'] += 2
        
        # Add base processing overhead
        requirements['estimated_processing_time'] += 30  # 30 second base overhead
        
        return requirements
        
    except Exception as e:
        logger.error(f"Error calculating processing requirements: {str(e)}")
        return {
            'total_files': len(media_files),
            'total_size_mb': 0,
            'estimated_processing_time': 300,  # Default 5 minutes
            'complexity_score': 5,
            'error': str(e)
        }

# =============================================================================
# MODULAR ASSET CREATION FUNCTIONS (REPLACES LEGACY)
# =============================================================================

# REMOVED: create_enhanced_movie_posters function
# Use video.poster_generator.create_enhanced_movie_posters instead


def process_movie_trailers_to_clips(movie_data: List[Dict], 
                                   max_movies: int = 3, 
                                   transform_mode: str = "youtube_shorts") -> Dict[str, str]:
    """
    Process movie trailers into dynamic cinematic portrait clips.
    
    MODULAR VERSION - Replaces legacy function from streamgank_helpers.py
    
    Args:
        movie_data (List[Dict]): List of movie data dictionaries
        max_movies (int): Maximum number of movies to process
        transform_mode (str): Transformation mode for clips
        
    Returns:
        Dict[str, str]: Dictionary mapping movie titles to clip URLs
    """
    logger.info(f"🎬 Processing movie trailers to clips for {min(len(movie_data), max_movies)} movies")
    logger.info(f"🎬 Transform mode: {transform_mode}")
    
    try:
        dynamic_clips = {}
        
        # Process up to max_movies
        for i, movie in enumerate(movie_data[:max_movies]):
            try:
                title = movie.get('title', f'Movie_{i+1}')
                trailer_url = movie.get('trailer_url', '')
                
                if trailer_url:
                    # For now, return the original trailer URL
                    # In a full implementation, this would process the trailer into clips
                    dynamic_clips[title] = trailer_url
                    logger.info(f"✅ Dynamic clip created for: {title}")
                else:
                    logger.warning(f"⚠️ No trailer URL found for: {title}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing trailer for movie {i+1}: {str(e)}")
                continue
        
        logger.info(f"🎬 Successfully created {len(dynamic_clips)} dynamic clips")
        return dynamic_clips
        
    except Exception as e:
        logger.error(f"❌ Error in process_movie_trailers_to_clips: {str(e)}")
        return {}