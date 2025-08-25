#!/usr/bin/env python3
"""
Vizard Clips Cloudinary Upload Script

This script uploads locally downloaded Vizard AI highlight clips to Cloudinary
and returns the URLs for integration into the StreamGank workflow.

Usage:
    python upload_vizard_clips.py --clip-dir ./test_vizard_clips
"""

import os
import sys
import argparse
import json
import logging
from typing import List, Dict, Any, Optional
import re
from pathlib import Path

# Import Cloudinary upload functionality
from media.cloudinary_uploader import upload_clip_to_cloudinary
from ai.extract_highlights import process_vizard_highlights_for_creatomate

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def find_vizard_clips(clip_dir: str, pattern: str = "*highlight*.mp4") -> List[str]:
    """
    Find Vizard highlight clips in the specified directory
    
    Args:
        clip_dir: Directory to search for clips
        pattern: Glob pattern to match clip files
        
    Returns:
        List of paths to clip files
    """
    clip_paths = []
    
    try:
        # Convert to Path for proper handling
        clip_dir_path = Path(clip_dir)
        
        if not clip_dir_path.exists():
            logger.error(f"❌ Clip directory does not exist: {clip_dir}")
            return []
            
        # Find all clips matching the pattern
        for clip_path in clip_dir_path.glob(pattern):
            if clip_path.is_file() and clip_path.stat().st_size > 0:  # Skip empty files
                clip_paths.append(str(clip_path))
                
        logger.info(f"📋 Found {len(clip_paths)} Vizard clips in {clip_dir}")
        
        return sorted(clip_paths)  # Return sorted list for consistent ordering
        
    except Exception as e:
        logger.error(f"❌ Error finding Vizard clips: {str(e)}")
        return []

def upload_vizard_clips(clip_paths: List[str], folder: str = "vizard_ai_clips") -> List[Dict[str, Any]]:
    """
    Upload Vizard clips to Cloudinary and return clip metadata
    
    Args:
        clip_paths: List of paths to clip files
        folder: Cloudinary folder name
        
    Returns:
        List of clip metadata dictionaries with local_path and url
    """
    if not clip_paths:
        logger.error("❌ No clip paths provided")
        return []
        
    logger.info(f"🚀 Uploading {len(clip_paths)} Vizard clips to Cloudinary...")
    
    uploaded_clips = []
    cloudinary_urls = process_vizard_highlights_for_creatomate(clip_paths, folder)
    
    # Match the URLs with local paths
    for i, local_path in enumerate(clip_paths):
        if i < len(cloudinary_urls):
            uploaded_clips.append({
                "local_path": local_path,
                "url": cloudinary_urls[i],
                "file_name": Path(local_path).name,
                "order": i + 1
            })
    
    logger.info(f"✅ Successfully uploaded {len(uploaded_clips)} Vizard clips to Cloudinary")
    return uploaded_clips

def save_clip_metadata(clip_data: List[Dict[str, Any]], output_file: str) -> bool:
    """
    Save clip metadata to JSON file
    
    Args:
        clip_data: List of clip metadata dictionaries
        output_file: Path to output JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(output_file, 'w') as f:
            json.dump({
                "vizard_clips": clip_data,
                "clip_count": len(clip_data),
                "cloudinary_urls": [clip["url"] for clip in clip_data],
                "timestamp": Path(output_file).stem
            }, f, indent=2)
            
        logger.info(f"✅ Saved clip metadata to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving clip metadata: {str(e)}")
        return False

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Upload locally downloaded Vizard clips to Cloudinary")
    parser.add_argument("--clip-dir", type=str, default="./test_vizard_clips", 
                        help="Directory containing Vizard clips (default: ./test_vizard_clips)")
    parser.add_argument("--pattern", type=str, default="*highlight*.mp4",
                        help="File pattern to match (default: *highlight*.mp4)")
    parser.add_argument("--folder", type=str, default="vizard_ai_clips",
                        help="Cloudinary folder name (default: vizard_ai_clips)")
    parser.add_argument("--output", type=str, default="vizard_clips_metadata.json",
                        help="Output JSON file for clip metadata (default: vizard_clips_metadata.json)")
    parser.add_argument("--max-clips", type=int, default=3,
                        help="Maximum number of clips to upload (default: 3)")
    args = parser.parse_args()
    
    # Logging already set up at module level
    
    # Print welcome message
    print("\n" + "=" * 80)
    print("🎬 VIZARD AI CLIPS CLOUDINARY UPLOADER")
    print("=" * 80)
    print(f"📂 Clip Directory: {args.clip_dir}")
    print(f"🔍 Search Pattern: {args.pattern}")
    print(f"☁️ Cloudinary Folder: {args.folder}")
    print(f"📄 Output File: {args.output}")
    print(f"🔢 Max Clips: {args.max_clips}")
    print("-" * 80 + "\n")
    
    # Find Vizard clips
    print("🔍 Searching for Vizard clips...")
    clip_paths = find_vizard_clips(args.clip_dir, args.pattern)
    
    if not clip_paths:
        print("❌ No Vizard clips found. Exiting.")
        return 1
    
    print(f"📋 Found {len(clip_paths)} Vizard clips:")
    for i, path in enumerate(clip_paths):
        print(f"   {i+1}. {Path(path).name}")
    
    # Limit to max_clips if needed
    if len(clip_paths) > args.max_clips:
        print(f"\n⚠️ Limiting to {args.max_clips} clips (out of {len(clip_paths)} found)")
        clip_paths = clip_paths[:args.max_clips]
    
    # Upload clips
    print("\n☁️ Uploading clips to Cloudinary...")
    uploaded_clips = upload_vizard_clips(clip_paths, args.folder)
    
    if not uploaded_clips:
        print("❌ Failed to upload any clips. Exiting.")
        return 1
    
    # Save metadata
    if save_clip_metadata(uploaded_clips, args.output):
        print(f"\n✅ Successfully uploaded {len(uploaded_clips)} Vizard clips to Cloudinary")
        print(f"📄 Metadata saved to {args.output}")
        
        # Print URLs for easy access
        print("\n🔗 Cloudinary URLs for Creatomate:")
        for i, clip in enumerate(uploaded_clips):
            print(f"   {i+1}. {clip['url']}")
            
        return 0
    else:
        print("\n⚠️ Clips were uploaded but metadata could not be saved")
        return 1

if __name__ == "__main__":
    sys.exit(main())
