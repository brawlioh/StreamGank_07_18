import os
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

from ai.vizard_client import VizardAIClient
from media.cloudinary_uploader import upload_clip_to_cloudinary

def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from a YouTube URL
    
    Args:
        url: YouTube URL in any format
        
    Returns:
        YouTube video ID if found, None otherwise
    """
    if not url:
        return None
        
    # Parse the URL
    parsed_url = urlparse(url)
    
    # youtube.com/watch?v=VIDEO_ID format
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            query = parse_qs(parsed_url.query)
            return query.get('v', [None])[0]
    
    # youtu.be/VIDEO_ID format
    elif parsed_url.hostname in ('youtu.be'):
        return parsed_url.path[1:]
    
    # Try regex as fallback
    youtube_regex = r"(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
    match = re.search(youtube_regex, url)
    if match:
        return match.group(1)
    
    return None

def extract_highlights_with_vizard(
    youtube_url: str, 
    movie_title: str = "Unknown Movie",
    num_clips: int = 1, 
    clip_length: int = 1, 
    output_dir: str = "temp_clips",
    max_wait_minutes: int = 15
) -> List[str]:
    """
    Extract highlights from a YouTube video using Vizard AI
    
    Args:
        youtube_url: YouTube video URL
        movie_title: Title of the movie for labeling
        num_clips: Number of highlight clips to generate
        clip_length: Preferred length of clips (1=short, 2=medium, 3=long)
        output_dir: Directory to save downloaded clips
        max_wait_minutes: Maximum time to wait for processing completion in minutes
        
    Returns:
        List of paths to downloaded highlight clips
    """
    print(f"🎬 Extracting {num_clips} highlights from video for '{movie_title}'...")
    
    # Validate YouTube URL
    video_id = extract_youtube_video_id(youtube_url)
    if not video_id:
        print(f"❌ Invalid YouTube URL: {youtube_url}")
        return []
    
    print(f"📋 Processing YouTube video ID: {video_id}")
    
    try:
        # Initialize the Vizard AI client
        vizard = VizardAIClient()
        
        # Extract highlights
        clip_paths = vizard.extract_highlights(
            youtube_url=youtube_url,
            num_clips=num_clips,
            clip_length=clip_length,
            output_dir=output_dir,
            max_wait_minutes=max_wait_minutes,
            force_download=True  # Force download even if project status is UNKNOWN
        )
        
        if not clip_paths:
            print(f"❌ No highlights generated for {movie_title}")
            return []
            
        print(f"✅ Successfully extracted {len(clip_paths)} highlights for '{movie_title}'")
        
        # Rename files to include video ID and movie title
        renamed_paths = []
        for i, path in enumerate(clip_paths):
            # Get directory and base filename
            directory = os.path.dirname(path)
            # Create new filename with movie info
            safe_title = movie_title.replace(' ', '_').replace(':', '').replace('/', '_')
            new_filename = f"vizard_{video_id}_{safe_title}_{i+1}.mp4"
            new_path = os.path.join(directory, new_filename)
            
            # Rename the file
            try:
                os.rename(path, new_path)
                renamed_paths.append(new_path)
                print(f"   📝 Renamed highlight to: {new_filename}")
            except Exception as e:
                print(f"   ⚠️ Could not rename file: {str(e)}")
                renamed_paths.append(path)  # Use original path
        
        return renamed_paths
        
    except Exception as e:
        print(f"❌ Error extracting highlights with Vizard AI: {str(e)}")
        return []

def process_vizard_highlights_for_creatomate(highlight_clips: List[str], folder: str = "vizard_ai_clips") -> List[str]:
    """
    Process Vizard AI highlight clips for use with Creatomate
    
    Args:
        highlight_clips: List of paths to downloaded highlight clips
        folder: Cloudinary folder name
        
    Returns:
        List of Cloudinary URLs for the uploaded clips
    """
    print(f"📤 Processing {len(highlight_clips)} Vizard AI highlights for Creatomate...")
    
    cloudinary_urls = []
    
    for i, clip_path in enumerate(highlight_clips):
        # Extract movie title from filename if possible
        filename = os.path.basename(clip_path)
        title_match = re.search(r"vizard_[^_]+_(.+)_\d+\.mp4$", filename)
        movie_title = title_match.group(1).replace('_', ' ') if title_match else f"Vizard Clip {i+1}"
        
        print(f"   📤 Uploading highlight {i+1}/{len(highlight_clips)}: {filename}")
        cloudinary_url = upload_clip_to_cloudinary(
            clip_path=clip_path,
            movie_title=f"Vizard: {movie_title}",
            transform_mode="youtube_shorts",  # Use standard shorts format
            folder=folder
        )
        
        if cloudinary_url:
            cloudinary_urls.append(cloudinary_url)
            print(f"   ✅ Successfully uploaded: {filename}")
            print(f"   🌐 Cloudinary URL: {cloudinary_url}")
        else:
            print(f"   ❌ Failed to upload {filename}")
    
    print(f"📊 Uploaded {len(cloudinary_urls)}/{len(highlight_clips)} clips to Cloudinary")
    return cloudinary_urls
