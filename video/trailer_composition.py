"""
StreamGank Trailer Composition Builder

This module provides simplified composition functions for trailer-only videos
without requiring HeyGen integration.
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional

from video.creatomate_client import send_creatomate_request

logger = logging.getLogger(__name__)

def create_trailer_composition(
    clips: List[Dict[str, Any]],
    output_name: str = None,
    with_subtitles: bool = True
) -> Dict[str, Any]:
    """
    Create a trailer-only composition for Creatomate rendering.
    
    Args:
        clips: List of movie clip data with URLs and metadata
        output_name: Name for the output file
        with_subtitles: Whether to include subtitles
        
    Returns:
        Dict containing render ID and status information
    """
    if not clips:
        logger.error("❌ No clips provided for trailer composition")
        return {"status": "error", "error": "No clips provided"}
        
    if not output_name:
        output_name = f"trailer_composition_{int(time.time())}"
    
    logger.info(f"🎬 Creating trailer-only composition: {output_name}")
    logger.info(f"   🎬 Clips: {len(clips)}")
    
    # Basic composition structure
    composition = {
        "width": 1080,
        "height": 1920,
        "frame_rate": 30,
        "elements": []
    }
    
    # Create intro element
    composition["elements"].append({
        "type": "image",
        "track": 1,
        "time": 0,
        "duration": 2,
        "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1753263646/streamGank_intro_cwefmt.jpg",
        "fit": "cover",
        "animations": [
            {
                "time": 0,
                "duration": 0.5,
                "easing": "quadratic-out",
                "type": "fade"
            }
        ]
    })
    
    # Current position tracker
    current_time = 2  # After intro
    
    # Add movie clips
    for i, clip_data in enumerate(clips):
        # Get clip data
        clip_url = clip_data.get("clip_url")
        movie_title = clip_data.get("title", f"Movie {i+1}")
        platform = clip_data.get("platform", "")
        year = clip_data.get("year", "")
        imdb = clip_data.get("imdb_rating", "")
        
        logger.info(f"   📽️ Adding clip for: {movie_title} ({year})")
        
        # Clip duration estimate - for test purposes we'll use fixed durations
        clip_duration = 10  # Fixed duration for testing
        
        # Add clip element
        composition["elements"].append({
            "type": "video",
            "track": 1,
            "time": current_time,
            "duration": clip_duration,
            "source": clip_url,
            "fit": "cover",
            "animations": [
                {
                    "time": 0,
                    "duration": 0.5,
                    "easing": "quadratic-out",
                    "type": "fade"
                }
            ]
        })
        
        # Add movie title text overlay
        composition["elements"].append({
            "type": "text",
            "track": 2,
            "time": current_time,
            "duration": clip_duration,
            "x": "50%",
            "y": "85%", 
            "text": f"{movie_title} ({year}) - {platform}",
            "font_family": "Roboto",
            "font_weight": "700",
            "font_size": "6vmin",
            "fill_color": "#ffffff",
            "shadow_color": "rgba(0,0,0,0.8)",
            "shadow_blur": "2vmin"
        })
        
        # Add rating info
        if imdb:
            composition["elements"].append({
                "type": "text",
                "track": 2,
                "time": current_time,
                "duration": clip_duration,
                "x": "50%", 
                "y": "90%",
                "text": f"IMDb: {imdb}",
                "font_family": "Roboto",
                "font_weight": "700", 
                "font_size": "5vmin",
                "fill_color": "#61d7a5",
                "shadow_color": "rgba(0,0,0,0.8)",
                "shadow_blur": "1vmin"
            })
            
        # Update current time
        current_time += clip_duration
    
    # Add outro
    composition["elements"].append({
        "type": "image",
        "track": 1,
        "time": current_time,
        "duration": 3,
        "source": "https://res.cloudinary.com/dodod8s0v/image/upload/v1752587571/streamgank_bg_heecu7.png",
        "fit": "cover",
        "animations": [
            {
                "time": 0,
                "duration": 0.5,
                "transition": True,
                "type": "fade"
            }
        ]
    })
    
    # Add StreamGank branding
    composition["elements"].append({
        "name": "Branding",
        "type": "composition",
        "track": 3,
        "time": 0,
        "duration": current_time + 3,  # Full duration
        "elements": [
            # Logo - "Stream" (green)
            {
                "type": "text",
                "x": "19%",
                "y": "2%", 
                "x_anchor": "0%",
                "y_anchor": "0%",
                "text": "Stream",
                "font_family": "Noto Sans",
                "font_weight": "700",
                "font_size": "8vmin",
                "fill_color": "#61d7a5",
                "shadow_color": "rgba(0,0,0,0.8)",
                "shadow_blur": "2vmin"
            },
            # Logo - "Gank" (white)
            {
                "type": "text",
                "x": "55%",
                "y": "2%",
                "x_anchor": "0%",
                "y_anchor": "0%", 
                "text": "Gank",
                "font_family": "Noto Sans",
                "font_weight": "700",
                "font_size": "8vmin",
                "fill_color": "#ffffff",
                "shadow_color": "rgba(0,0,0,0.25)"
            },
            # Tagline
            {
                "type": "text",
                "x": "20%",
                "y": "8%",
                "x_anchor": "0%",
                "y_anchor": "0%",
                "text": "AMBUSH THE BEST VOD TOGETHER",
                "font_family": "Noto Sans",
                "font_weight": "700",
                "font_size": "3vmin",
                "fill_color": "#ffffff",
                "shadow_color": "rgba(0,0,0,0.8)",
                "shadow_blur": "2vmin"
            }
        ]
    })
    
    # Log composition
    logger.info(f"📋 Composition created with {len(composition['elements'])} elements")
    logger.info(f"   ⏱️ Total duration: {current_time + 3}s")
    
    # Submit to Creatomate
    try:
        logger.info("📤 Submitting trailer composition to Creatomate...")
        render_id = send_creatomate_request(composition)
        
        if render_id:
            logger.info(f"✅ Composition submitted successfully: {render_id}")
            return {
                "status": "success",
                "render_id": render_id,
                "clip_count": len(clips),
                "duration": current_time + 3
            }
        else:
            logger.error("❌ Failed to submit composition to Creatomate")
            return {"status": "error", "error": "Failed to submit to Creatomate"}
            
    except Exception as e:
        logger.error(f"❌ Error submitting composition: {str(e)}")
        return {"status": "error", "error": str(e)}

def create_composition_with_avatar(
    clips: List[Dict[str, Any]], 
    heygen_videos: Dict[str, str] = None,
    output_name: str = None
) -> Dict[str, Any]:
    """
    Create a composition with both avatar and trailer clips.
    If heygen_videos is not provided, falls back to trailer-only composition.
    
    Args:
        clips: List of movie clip data with URLs and metadata
        heygen_videos: Dictionary mapping movie keys to HeyGen video URLs
        output_name: Name for the output file
        
    Returns:
        Dict containing render ID and status information
    """
    if not heygen_videos:
        logger.warning("⚠️ No HeyGen videos provided, falling back to trailer-only composition")
        return create_trailer_composition(clips, output_name)
    
    logger.error("❌ Full avatar composition not implemented in this test version")
    return create_trailer_composition(clips, output_name)
