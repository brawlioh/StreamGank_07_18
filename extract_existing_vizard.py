#!/usr/bin/env python3
"""
Extract clips from existing Vizard AI projects
This utility script helps you download clips from already processed Vizard AI projects
that appear in your dashboard, without having to create new projects.
"""

import os
import argparse
import sys
from ai.vizard_client import VizardAIClient
from media.cloudinary_uploader import upload_clip_to_cloudinary
# Use environment variable directly
from dotenv import load_dotenv

def main():
    parser = argparse.ArgumentParser(description="Extract clips from existing Vizard AI projects")
    parser.add_argument("--project-id", required=True, help="Vizard AI project ID from dashboard (e.g., open-api-175586116364)")
    parser.add_argument("--movie-title", default="Movie", help="Movie title for file naming")
    parser.add_argument("--output-dir", default="temp_clips", help="Directory to save clips to")
    parser.add_argument("--upload-to-cloudinary", action="store_true", help="Upload clips to Cloudinary")
    parser.add_argument("--cloudinary-folder", default="vizard_ai_clips", help="Cloudinary folder name")
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key directly from environment
    vizard_api_key = os.environ.get('VIZARD_API_KEY')
    if not vizard_api_key:
        print("❌ Vizard AI API key not found in environment variables")
        print("Make sure VIZARD_API_KEY is set in your .env file or environment")
        return 1
    
    # Create Vizard AI client
    client = VizardAIClient(api_key=vizard_api_key)
    
    # Extract clips from existing project
    print(f"🔍 Extracting clips from existing project: {args.project_id}")
    clip_paths = client.extract_from_existing_project(
        project_id=args.project_id,
        movie_title=args.movie_title,
        output_dir=args.output_dir
    )
    
    if not clip_paths:
        print("❌ No clips extracted from project")
        return 1
    
    print(f"✅ Successfully extracted {len(clip_paths)} clips from project")
    
    # Upload clips to Cloudinary if requested
    cloudinary_urls = []
    if args.upload_to_cloudinary:
        print(f"🔄 Uploading {len(clip_paths)} clips to Cloudinary folder: {args.cloudinary_folder}")
        
        for clip_path in clip_paths:
            try:
                clip_name = os.path.basename(clip_path)
                print(f"   Uploading: {clip_name}")
                
                cloudinary_url = upload_clip_to_cloudinary(
                    clip_path=clip_path,
                    public_id=f"{args.cloudinary_folder}/{os.path.splitext(clip_name)[0]}",
                    resource_type="video"
                )
                
                if cloudinary_url:
                    print(f"   ✅ Uploaded to: {cloudinary_url}")
                    cloudinary_urls.append(cloudinary_url)
                else:
                    print(f"   ❌ Failed to upload {clip_name}")
                    
            except Exception as e:
                print(f"   ❌ Error uploading {clip_path}: {str(e)}")
        
        print(f"\n📋 Cloudinary URLs for Creatomate:")
        for i, url in enumerate(cloudinary_urls, 1):
            print(f"{i}. {url}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
