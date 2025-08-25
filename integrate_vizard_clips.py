#!/usr/bin/env python3
"""
Vizard Clip Integration Utility

This script helps integrate manually downloaded Vizard AI highlight clips into the StreamGank workflow.
It processes clips from a local directory, optionally uploads them to Cloudinary, and outputs
clip metadata for use in the main workflow.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# Import necessary utilities
try:
    from media.cloudinary_uploader import CloudinaryUploader
except ImportError:
    print("⚠️ Cloudinary uploader module not found, upload functionality will be disabled")
    CloudinaryUploader = None

def setup_cloudinary() -> Optional[Any]:
    """Set up Cloudinary uploader if credentials are available"""
    if CloudinaryUploader is None:
        return None
        
    try:
        return CloudinaryUploader()
    except Exception as e:
        print(f"❌ Failed to initialize Cloudinary: {str(e)}")
        return None

def process_clip_files(
    clip_dir: str, 
    output_file: Optional[str] = None,
    movie_title: str = "Movie",
    upload_to_cloudinary: bool = False,
    cloudinary_folder: str = "vizard_clips"
) -> List[Dict[str, Any]]:
    """
    Process Vizard clip files from a directory
    
    Args:
        clip_dir: Directory containing downloaded clip files
        output_file: Optional JSON file to save clip metadata
        movie_title: Movie title for naming
        upload_to_cloudinary: Whether to upload clips to Cloudinary
        cloudinary_folder: Folder name in Cloudinary
        
    Returns:
        List of clip metadata dictionaries
    """
    # Verify directory exists
    if not os.path.isdir(clip_dir):
        print(f"❌ Directory not found: {clip_dir}")
        return []
        
    # Get all video files in the directory
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
    clip_files = []
    
    for ext in video_extensions:
        clip_files.extend(Path(clip_dir).glob(f"*{ext}"))
    
    if not clip_files:
        print(f"❌ No video files found in {clip_dir}")
        return []
    
    print(f"✅ Found {len(clip_files)} video clip(s) in {clip_dir}")
    
    # Set up Cloudinary if needed
    cloudinary_uploader = None
    if upload_to_cloudinary:
        cloudinary_uploader = setup_cloudinary()
        if cloudinary_uploader is None:
            print("⚠️ Cloudinary upload disabled due to initialization failure")
            upload_to_cloudinary = False
    
    # Process each clip file
    clip_data = []
    for i, clip_path in enumerate(sorted(clip_files)):
        clip_name = f"{movie_title}_highlight_{i+1}"
        
        print(f"🎬 Processing clip {i+1}/{len(clip_files)}: {clip_path.name}")
        
        # Clip metadata
        clip_info = {
            "path": str(clip_path),
            "name": clip_name,
            "local_path": str(clip_path),
            "index": i,
            "url": None
        }
        
        # Upload to Cloudinary if requested
        if upload_to_cloudinary and cloudinary_uploader:
            try:
                print(f"☁️ Uploading to Cloudinary: {clip_path.name}")
                upload_result = cloudinary_uploader.upload_video(
                    video_path=str(clip_path),
                    public_id=f"{cloudinary_folder}/{clip_name}",
                    overwrite=True
                )
                
                if upload_result and "url" in upload_result:
                    clip_info["url"] = upload_result["url"]
                    print(f"✅ Uploaded to: {clip_info['url']}")
                else:
                    print(f"⚠️ Upload succeeded but URL not found in response")
            except Exception as e:
                print(f"❌ Failed to upload {clip_path.name}: {str(e)}")
        
        clip_data.append(clip_info)
    
    # Save to output file if specified
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump({"clips": clip_data}, f, indent=2)
            print(f"✅ Saved clip metadata to {output_file}")
        except Exception as e:
            print(f"❌ Failed to save clip metadata: {str(e)}")
    
    return clip_data

def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description="Integrate manually downloaded Vizard AI clips")
    parser.add_argument("--clip-dir", required=True, help="Directory containing downloaded Vizard AI clips")
    parser.add_argument("--movie-title", default="Movie", help="Movie title for file naming")
    parser.add_argument("--output-file", default="vizard_clips_metadata.json", help="Output JSON file for clip metadata")
    parser.add_argument("--upload-to-cloudinary", action="store_true", help="Upload clips to Cloudinary")
    parser.add_argument("--cloudinary-folder", default="vizard_clips", help="Cloudinary folder name")
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Process the clips
    clip_data = process_clip_files(
        clip_dir=args.clip_dir,
        output_file=args.output_file,
        movie_title=args.movie_title,
        upload_to_cloudinary=args.upload_to_cloudinary,
        cloudinary_folder=args.cloudinary_folder
    )
    
    # Summary
    if clip_data:
        print(f"\n✨ Successfully processed {len(clip_data)} clip(s)")
        
        # Show Cloudinary upload stats
        uploaded_count = sum(1 for clip in clip_data if clip.get("url"))
        if uploaded_count:
            print(f"☁️ {uploaded_count}/{len(clip_data)} clip(s) uploaded to Cloudinary")
        
        print(f"\n📋 Metadata saved to: {args.output_file}")
        print("Use this metadata file in your workflow to integrate the clips")
    else:
        print("❌ No clips were processed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
