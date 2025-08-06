#!/usr/bin/env python3
"""
StreamGank Modular Video Generation System
Main Entry Point

MODULAR SYSTEM - NO LEGACY DEPENDENCIES

Usage:
    python main.py --country US --platform Netflix --genre Horror --content-type Film --heygen-template-id cc6718c5363e42b282a123f99b94b335
    python main.py --country FR --platform Netflix --genre Horreur --content-type Film --heygen-template-id cc6718c5363e42b282a123f99b94b335

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

# Import MODULAR functions (partial migration - some legacy functions still needed)
from ai.robust_script_generator import generate_video_scripts
from ai.heygen_client import create_heygen_video, get_heygen_videos_for_creatomate
from video.scroll_generator import generate_scroll_video
from video.creatomate_client import create_creatomate_video
from automated_video_generator import check_creatomate_render_status, wait_for_creatomate_completion
from core.workflow import process_existing_heygen_videos
from database.movie_extractor import extract_movie_data

# Import asset creation functions from modular structure
from video.poster_generator import create_enhanced_movie_posters
from video.clip_processor import process_movie_trailers_to_clips

# Import centralized settings
from config.settings import get_scroll_settings, get_video_settings

# Import test data caching utilities
from utils.test_data_cache import load_test_data, save_script_result, save_assets_result, get_app_env, should_use_cache


def run_full_workflow(num_movies: int = 3,
                     country: str = "US", 
                     genre: str = "Horror",
                     platform: str = "Netflix",
                     content_type: str = "Movies",
                     output: str = None,
                     skip_scroll_video: bool = False,
                     smooth_scroll: bool = None,
                     scroll_distance: float = None,
                     poster_timing_mode: str = "heygen_last3s",
                     heygen_template_id: str = None) -> dict:
    """
    Run the complete StreamGank video generation workflow.
    
    PARTIALLY MODULAR SYSTEM - SOME LEGACY FUNCTIONS STILL NEEDED
    
    This function orchestrates the entire process from database extraction to final
    video creation, using mostly modular functions with some legacy functions where needed.
    
    Workflow Steps:
    1. Database Extraction - Get top movies by IMDB score
    2. Script Generation - Create AI-powered hooks and intro (MODULAR FUNCTION)
    3. Asset Preparation - Generate posters and process clips (MODULAR FUNCTIONS)
    4. HeyGen Video Creation - Generate AI avatar videos  
    5. Scroll Video Generation - Create scroll overlay (optional)
    6. Creatomate Assembly - Combine all elements into final video
    7. Status Monitoring - Wait for completion and return results
    
    Args:
        num_movies (int): Number of movies to process (default: 3)
        country (str): Country code for localization (default: "US")
        genre (str): Genre filter (default: "Horror") 
        platform (str): Streaming platform (default: "Netflix")
        content_type (str): Content type (default: "Movies")
        output (str): Output file path (optional)
        skip_scroll_video (bool): Skip scroll video generation (default: False)
        smooth_scroll (bool): Use smooth scrolling (default: True)
        scroll_distance (float): Scroll distance factor (default: 1.5)
        poster_timing_mode (str): Poster timing strategy (default: "heygen_last3s")
        
    Returns:
        Dict[str, Any]: Complete workflow results including all generated assets
    """
    # Log environment information
    app_env = get_app_env()
    cache_enabled = should_use_cache()
    
    print("🚀 Starting StreamGank video generation workflow")
    print(f"🌍 Environment: APP_ENV='{app_env}' (Cache: {'ENABLED' if cache_enabled else 'DISABLED'})")
    print(f"Parameters: {num_movies} movies, {country}, {genre}, {platform}, {content_type}")
    
    # Load settings from centralized configuration
    scroll_settings = get_scroll_settings()
    video_settings = get_video_settings()
    
    # Use settings defaults if parameters not provided
    if smooth_scroll is None:
        smooth_scroll = scroll_settings.get('micro_scroll_enabled', True)
    if scroll_distance is None:
        scroll_distance = scroll_settings.get('scroll_distance_multiplier', 1.5)
    
    print(f"🎛️ Using settings: smooth_scroll={smooth_scroll}, scroll_distance={scroll_distance}")
    
    workflow_results = {
        'workflow_id': f"workflow_{int(time.time())}",
        'parameters': {
            'num_movies': num_movies,
            'country': country,
            'genre': genre,
            'platform': platform,
            'content_type': content_type
        },
        'steps_completed': [],
        'start_time': time.time()
    }
    
    try:
        # =============================================================================
        # STEP 1: DATABASE EXTRACTION
        # =============================================================================
        print(f"\n[STEP 1/7] Database Extraction - Extracting {num_movies} movies from database")
        step_start = time.time()
        print(f"   Filters: {country}, {genre}, {platform}, {content_type}")
        
        raw_movies = extract_movie_data(
            num_movies=num_movies,
            country=country,
            genre=genre,
            platform=platform,
            content_type=content_type
        )
        
        if not raw_movies:
            raise Exception("Database extraction failed - no movies found")
        
        workflow_results['raw_movies'] = raw_movies
        workflow_results['steps_completed'].append('database_extraction')
        
        print(f"✅ STEP 1 COMPLETED - Found {len(raw_movies)} movies in {time.time() - step_start:.1f}s")
        
        # =============================================================================
        # STEP 2: SCRIPT GENERATION (MODULAR FUNCTION WITH TEST DATA CACHING)
        # =============================================================================
        print(f"\n[STEP 2/7] Script Generation - Generating scripts for {genre} content on {platform}")
        step_start = time.time()
        
        # Try to load existing script data from test_output
        cached_script_data = load_test_data('script_result', country, genre, platform)
        
        if cached_script_data and should_use_cache():
            print("   📂 Using cached script data from test_output...")
            
            # Extract data from cached result
            combined_script = cached_script_data.get('combined_script', '')
            script_file_path = cached_script_data.get('script_file_path', '')
            individual_scripts = cached_script_data.get('individual_scripts', {})
            
            script_result = (combined_script, script_file_path, individual_scripts)
            
            print(f"   📋 Loaded {len(individual_scripts)} cached scripts")
            
        else:
            print("   🔄 No cached data found, generating new scripts...")
            print("   Using modular script generation...")
            
            script_result = generate_video_scripts(
                raw_movies=raw_movies,
                country=country,
                genre=genre,
                platform=platform,
                content_type=content_type
            )
            
            if not script_result:
                raise Exception("Script generation failed - no scripts were generated")
            
            combined_script, script_file_path, individual_scripts = script_result
            
            # Save script result to test_output for future use
            script_data_to_save = {
                'combined_script': combined_script,
                'script_file_path': script_file_path,
                'individual_scripts': individual_scripts,
                'raw_movies': raw_movies,  # Also save movie data for reference
                'parameters': {
                    'country': country,
                    'genre': genre,
                    'platform': platform,
                    'content_type': content_type,
                    'num_movies': len(raw_movies)
                }
            }
            
            save_script_result(script_data_to_save, country, genre, platform)
        
        workflow_results['combined_script'] = combined_script
        workflow_results['script_file_path'] = script_file_path
        workflow_results['individual_scripts'] = individual_scripts
        workflow_results['steps_completed'].append('script_generation')
        
        print(f"✅ STEP 2 COMPLETED - Using {len(individual_scripts)} scripts in {time.time() - step_start:.1f}s")
        
        # =============================================================================
        # STEP 3: ASSET PREPARATION (MODULAR FUNCTIONS WITH TEST DATA CACHING)
        # =============================================================================
        print(f"\n[STEP 3/7] Asset Preparation - Creating enhanced posters and movie clips")
        step_start = time.time()
        
        # Try to load existing asset data from test_output
        cached_assets_data = load_test_data('assets', country, genre, platform)
        
        if cached_assets_data:
            print("   📂 Using cached asset data from test_output...")
            
            enhanced_posters = cached_assets_data.get('enhanced_posters', {})
            dynamic_clips = cached_assets_data.get('dynamic_clips', {})
            
            print(f"   📋 Loaded {len(enhanced_posters)} cached posters and {len(dynamic_clips)} cached clips")
            
        else:
            print("   🔄 No cached assets found, generating new assets...")
            
            # Create enhanced posters (MODULAR FUNCTION)
            print("   Creating enhanced movie posters with metadata overlays...")
            enhanced_posters = create_enhanced_movie_posters(raw_movies, max_movies=3)
            
            if not enhanced_posters or len(enhanced_posters) < 3:
                raise Exception(f"Failed to create enhanced posters - got {len(enhanced_posters) if enhanced_posters else 0}, need 3")
            
            # Process movie clips (MODULAR FUNCTION)
            print("   Processing dynamic cinematic portrait clips from trailers...")
            dynamic_clips = process_movie_trailers_to_clips(raw_movies, max_movies=3, transform_mode="youtube_shorts")
            
            if not dynamic_clips or len(dynamic_clips) < 3:
                raise Exception(f"Failed to create movie clips - got {len(dynamic_clips) if dynamic_clips else 0}, need 3")
            
            # Save asset results to test_output for future use
            assets_data_to_save = {
                'enhanced_posters': enhanced_posters,
                'dynamic_clips': dynamic_clips,
                'parameters': {
                    'country': country,
                    'genre': genre,
                    'platform': platform,
                    'content_type': content_type,
                    'num_movies': len(raw_movies)
                }
            }
            
            save_assets_result(assets_data_to_save, country, genre, platform)
        
        # Extract URLs for Creatomate
        movie_covers = list(enhanced_posters.values())[:3]
        movie_clips = list(dynamic_clips.values())[:3]
        
        workflow_results['movie_covers'] = movie_covers
        workflow_results['movie_clips'] = movie_clips
        workflow_results['enhanced_posters'] = enhanced_posters
        workflow_results['dynamic_clips'] = dynamic_clips
        workflow_results['steps_completed'].append('asset_preparation')
        
        print(f"✅ STEP 3 COMPLETED - Created {len(movie_covers)} posters and {len(movie_clips)} clips in {time.time() - step_start:.1f}s")
        
        # =============================================================================
        # STEP 4: HEYGEN VIDEO CREATION
        # =============================================================================
        print(f"\n[STEP 4/7] HeyGen Video Creation - Generating AI avatar videos")
        step_start = time.time()
        
        heygen_video_ids = create_heygen_video(individual_scripts, True, heygen_template_id)
        
        if not heygen_video_ids:
            raise Exception("HeyGen video creation failed")
        
        workflow_results['heygen_video_ids'] = heygen_video_ids
        workflow_results['steps_completed'].append('heygen_creation')
        
        print(f"✅ STEP 4 COMPLETED - Created {len(heygen_video_ids)} HeyGen videos in {time.time() - step_start:.1f}s")
        
        # =============================================================================
        # STEP 5: GET HEYGEN VIDEO URLS
        # =============================================================================
        print(f"\n[STEP 5/7] HeyGen Video Processing - Waiting for video completion")
        step_start = time.time()
        
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids, individual_scripts)
        
        if not heygen_video_urls:
            raise Exception("HeyGen video URL retrieval failed")
        
        workflow_results['heygen_video_urls'] = heygen_video_urls
        workflow_results['steps_completed'].append('heygen_processing')
        
        print(f"✅ STEP 5 COMPLETED - Got {len(heygen_video_urls)} video URLs in {time.time() - step_start:.1f}s")
        
        # =============================================================================
        # STEP 6: SCROLL VIDEO GENERATION (OPTIONAL)
        # =============================================================================
        scroll_video_url = None
        if not skip_scroll_video:
            print(f"\n[STEP 6/7] Scroll Video Generation - Creating StreamGank scroll overlay")
            step_start = time.time()
            
            scroll_video_url = generate_scroll_video(
                country=country,
                genre=genre,
                platform=platform,
                content_type=content_type,
                smooth=smooth_scroll,
                scroll_distance=scroll_distance,
                duration=scroll_settings.get('target_duration', 4)
            )
            
            if scroll_video_url:
                workflow_results['scroll_video_url'] = scroll_video_url
                print(f"✅ STEP 6 COMPLETED - Scroll video created in {time.time() - step_start:.1f}s")
            else:
                print(f"⚠️ STEP 6 SKIPPED - Scroll video generation failed, continuing without it")
        else:
            print(f"\n[STEP 6/7] Scroll Video Generation - SKIPPED (user requested)")
        
        workflow_results['steps_completed'].append('scroll_generation')
        
        # =============================================================================
        # STEP 7: CREATOMATE FINAL ASSEMBLY
        # =============================================================================
        print(f"\n[STEP 7/7] Creatomate Assembly - Creating final video")
        step_start = time.time()
        
        creatomate_id = create_creatomate_video(
            heygen_video_urls=heygen_video_urls,
            movie_covers=movie_covers,
            movie_clips=movie_clips,
            scroll_video_url=scroll_video_url,
            scripts=individual_scripts,
            poster_timing_mode=poster_timing_mode
        )
        
        if not creatomate_id or creatomate_id.startswith('error'):
            raise Exception(f"Creatomate video creation failed: {creatomate_id}")
        
        workflow_results['creatomate_id'] = creatomate_id
        workflow_results['steps_completed'].append('creatomate_assembly')
        
        print(f"✅ STEP 7 COMPLETED - Final video submitted in {time.time() - step_start:.1f}s")
        
        # =============================================================================
        # WORKFLOW COMPLETION
        # =============================================================================
        total_duration = time.time() - workflow_results['start_time']
        workflow_results['status'] = 'completed'
        workflow_results['total_duration'] = total_duration
        workflow_results['end_time'] = time.time()
        
        print(f"\n🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
        print(f"   ⏱️ Total duration: {total_duration:.1f}s")
        print(f"   📊 Steps completed: {len(workflow_results['steps_completed'])}/7")
        print(f"   🎬 Creatomate ID: {creatomate_id}")
        print(f"   💡 Check status: python main.py --check-creatomate {creatomate_id}")
        
        # Save results if output file specified
        if output:
            try:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(workflow_results, f, indent=2, ensure_ascii=False)
                print(f"   📁 Results saved to: {output}")
            except Exception as e:
                print(f"   ⚠️ Failed to save results: {str(e)}")
        
        return workflow_results
        
    except Exception as e:
        # Handle workflow failure
        total_duration = time.time() - workflow_results['start_time']
        workflow_results['status'] = 'failed'
        workflow_results['error'] = str(e)
        workflow_results['total_duration'] = total_duration
        workflow_results['end_time'] = time.time()
        
        print(f"\n❌ WORKFLOW FAILED at step {len(workflow_results['steps_completed']) + 1}")
        print(f"   Error: {str(e)}")
        print(f"   Duration before failure: {total_duration:.1f}s")
        
        # Save partial results if output file specified
        if output:
            try:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(workflow_results, f, indent=2, ensure_ascii=False)
                print(f"   📁 Partial results saved to: {output}")
            except Exception as save_error:
                print(f"   ⚠️ Failed to save partial results: {str(save_error)}")
        
        raise RuntimeError(f"❌ CRITICAL: Failed to process exactly {num_movies} movie clips")

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

    # Output options
    parser.add_argument("--output", help="Output file path to save results")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--skip-scroll-video", action="store_true", help="Skip scroll video generation")
    
    # Load default settings for argument parser
    scroll_settings = get_scroll_settings()
    
    parser.add_argument("--scroll-distance", type=float, 
                       default=scroll_settings.get('scroll_distance_multiplier', 1.5), 
                       help="Scroll distance as viewport multiplier (default from settings)")
    
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
                heygen_template_id=args.heygen_template_id
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