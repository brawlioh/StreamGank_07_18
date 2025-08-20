#!/usr/bin/env python3
"""
StreamGank Modular Video Generation System
Main Entry Point

MODULAR SYSTEM - NO LEGACY DEPENDENCIES

Usage:
    python main.py --country US --platform Netflix --genre Horror --content-type Film --heygen-template-id ed21a309a5c84b0d873fde68642adea3
    python main.py --country FR --platform Netflix --genre Horreur --content-type Film --heygen-template-id ed21a309a5c84b0d873fde68642adea3

    python main.py --check-env
    python main.py --check-creatomate <render_id>
    python main.py --wait-creatomate <render_id>
    python main.py --process-heygen <file_path>
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import MODULAR functions - Clean CLI interface
from video.creatomate_client import check_creatomate_render_status, wait_for_creatomate_completion
from core.workflow import process_existing_heygen_videos, run_full_workflow


def main():
    """Main entry point for the StreamGank video generation system"""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="StreamGank Video Generation System - MODULAR SYSTEM",
        epilog="By default, runs the complete end-to-end video generation workflow using modular functions."
    )
    
    # Workflow options
    parser.add_argument("--process-heygen", help="Process existing HeyGen video IDs from JSON file")
    parser.add_argument("--check-creatomate", help="Check Creatomate render status by ID")
    parser.add_argument("--wait-creatomate", help="Wait for Creatomate render completion by ID")
    
    # Parameters
    parser.add_argument("--num-movies", type=int, default=3, help="Number of movies to extract (default: 3)")
    parser.add_argument("--country", help="Country code for filtering")
    parser.add_argument("--genre", help="Genre to filter")
    parser.add_argument("--platform", help="Platform to filter")
    parser.add_argument("--content-type", help="Content type to filter")
    
    # HeyGen processing
    parser.add_argument("--heygen-ids", help="JSON string or file path with HeyGen video IDs")
    
    # HeyGen Id template
    parser.add_argument("--heygen-template-id", default="", help="HeyGen template ID to use for video generation")

    # HeyGen Id template
    parser.add_argument("--vizard-template-id", default="", help="Vizard template ID to use for video generation")

    # Output options
    parser.add_argument("--output", help="Output file path to save results")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--skip-scroll-video", action="store_true", help="Skip scroll video generation")
    parser.add_argument("--pause-after-extraction", action="store_true", help="Pause process after movie extraction for review")
    
    parser.add_argument("--scroll-distance", type=float, 
                       default=1.5, 
                       help="Scroll distance as viewport multiplier (default: 1.5)")
    
    args = parser.parse_args()
    
    # Handle different execution modes
    if args.check_creatomate:
        # Check Creatomate status
        print(f"\n🎬 StreamGank Video Generator - Creatomate Status Check")
        print(f"Checking status for render ID: {args.check_creatomate}")
        
        try:
            status_info = check_creatomate_render_status(args.check_creatomate)
            status = status_info.get("status", "unknown")
            
            print(f"\n📊 Render Status: {status}")
            if status_info.get("url"):
                print(f"📹 Video URL: {status_info['url']}")
            
            if status == "completed":
                print("✅ Video is ready for download!")
            elif status == "planned":
                print("⏳ Video is queued for rendering")
            elif status == "processing":
                print("🔄 Video is currently being rendered")
            elif status in ["failed", "error"]:
                print("❌ Video rendering failed")
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(status_info, f, indent=2, ensure_ascii=False)
                print(f"📁 Status saved to: {args.output}")
                
        except Exception as e:
            print(f"❌ Error checking status: {str(e)}")
            sys.exit(1)
            
    elif args.wait_creatomate:
        # Wait for Creatomate completion
        print(f"\n🎬 StreamGank Video Generator - Wait for Creatomate")
        print(f"Waiting for render ID: {args.wait_creatomate}")
        
        try:
            final_status = wait_for_creatomate_completion(args.wait_creatomate)
            status = final_status.get("status", "unknown")
            
            if status == "completed":
                print(f"✅ Video completed successfully!")
                print(f"📹 Download URL: {final_status.get('url', 'No URL')}")
            else:
                print(f"❌ Video rendering ended with status: {status}")
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(final_status, f, indent=2, ensure_ascii=False)
                print(f"📁 Final status saved to: {args.output}")
                
        except Exception as e:
            print(f"❌ Error waiting for completion: {str(e)}")
            sys.exit(1)
            
    elif args.process_heygen or args.heygen_ids:
        # Process existing HeyGen videos
        print(f"\n🎬 StreamGank Video Generator - HeyGen Processing Mode")
        
        heygen_video_ids = {}
        
        # Get video IDs
        if args.heygen_ids:
            try:
                if os.path.exists(args.heygen_ids):
                    with open(args.heygen_ids, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        heygen_video_ids = data.get('video_ids', data)
                else:
                    heygen_video_ids = json.loads(args.heygen_ids)
            except Exception as e:
                print(f"Error loading HeyGen video IDs: {str(e)}")
                sys.exit(1)
        elif args.process_heygen:
            try:
                with open(args.process_heygen, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    heygen_video_ids = data.get('video_ids', data)
            except Exception as e:
                print(f"Error loading HeyGen video IDs from {args.process_heygen}: {str(e)}")
                sys.exit(1)
        
        if not heygen_video_ids:
            print("No HeyGen video IDs provided")
            sys.exit(1)
        
        print(f"Processing HeyGen video IDs: {list(heygen_video_ids.keys())}")
        
        try:
            results = process_existing_heygen_videos(heygen_video_ids, args.output)
            print("\n✅ HeyGen processing completed!")
            
            if results.get('status') == 'success':
                print(f"🎬 Successfully submitted Creatomate video: {results.get('creatomate_id')}")
                print(f"📹 Status: {results.get('creatomate_status', 'submitted')}")
                if results.get('status_check_command'):
                    print(f"💡 Check status: {results['status_check_command']}")
            else:
                print(f"❌ Processing failed: {results.get('error')}")
            
            if args.output:
                print(f"📁 Results saved to: {args.output}")
                
        except Exception as e:
            print(f"❌ Error during HeyGen processing: {str(e)}")
            sys.exit(1)
            
    else:
        # Run full workflow
        print(f"\n🎬 StreamGank Video Generator - Full Workflow Mode")
        
        # Command line mode - use provided arguments
        country = args.country
        platform = args.platform
        genre = args.genre
        content_type = args.content_type

        # Validate required parameters
        if not country or not platform or not genre or not content_type:
            print("❌ Error: Country, platform, genre, and content type are required when not using interactive mode")
            sys.exit(1)
            
        # Confirm selections
        print("\n===== Your Selections =====")
        print(f"Country: {country}")
        print(f"Platform: {platform}")
        print(f"Genre: {genre}")
        print(f"Content Type: {content_type}")
        print(f"Number of Movies: {args.num_movies}")
        print(f"HeyGen Template ID: {args.heygen_template_id}")
        print(f"Vizard Template ID: {args.vizard_template_id}")
        print("===========================\n")
        
        # Start workflow execution
        print(f"Parameters: {args.num_movies} movies, {country}, {genre}, {platform}, {content_type}")
        print("Starting end-to-end workflow...\n")

        try:
            results = run_full_workflow(
                num_movies=args.num_movies,
                country=country,
                genre=genre,
                platform=platform,
                content_type=content_type,
                output=args.output,
                skip_scroll_video=args.skip_scroll_video,
                smooth_scroll=None,  # Use settings default
                scroll_distance=args.scroll_distance,
                heygen_template_id=args.heygen_template_id,
                vizard_template_id=args.vizard_template_id,
                pause_after_extraction=args.pause_after_extraction
            )
            print("\n✅ Workflow completed successfully!")
            
            # Print summary
            if results:
                print("\n📊 Results Summary:")
                print(f"📽️ Movies processed: 3 (simplified workflow)")
                
                if 'heygen_video_ids' in results:
                    print(f"🎥 HeyGen videos created: {len(results['heygen_video_ids'])}")
                
                if 'creatomate_id' in results:
                    print(f"🎞️ Final video submitted to Creatomate: {results['creatomate_id']}")
                    print(f"📹 Status: {results.get('creatomate_status', 'submitted')}")
                    print(f"💡 Check status: python main.py --check-creatomate {results['creatomate_id']}")
                
                if 'workflow_id' in results:
                    print(f"💾 Data stored with group ID: {results['workflow_id']}")
            
            if args.output:
                print(f"\n📁 Full results saved to: {args.output}")
                
        except Exception as e:
            print(f"\n❌ Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
if __name__ == "__main__":
    main()