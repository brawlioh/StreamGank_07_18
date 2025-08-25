#!/usr/bin/env python3
"""
StreamGank Core Workflow Orchestration

This module contains the main workflow functions that orchestrate the complete
video generation process. It coordinates between all modules to maintain the
same output as the original system while providing clean, readable code for
senior engineers.

EXACT SAME APPROACH AS LEGACY SYSTEM - PROVEN TO WORK
"""

import sys
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import modular functions
from ai.robust_script_generator import generate_video_scripts
from ai.extract_highlights import extract_highlights_with_vizard, process_vizard_highlights_for_creatomate
from ai.heygen_client import create_heygen_video, get_heygen_videos_for_creatomate

from database.movie_extractor import extract_movie_data

from video.poster_generator import create_enhanced_movie_posters
from video.clip_processor import process_movie_trailers_to_clips
from video.composition_builder import build_video_composition

from media.cloudinary_uploader import upload_clip_to_cloudinary

# Function to load local Vizard clip metadata
def load_local_vizard_clips(metadata_file="vizard_workflow_data.json") -> List[Dict[str, Any]]:
    """
    Load local Vizard clip metadata from JSON file
    
    Args:
        metadata_file: Path to JSON metadata file with clip info
        
    Returns:
        List of clip metadata entries or empty list if file not found/invalid
    """
    try:
        if not os.path.isfile(metadata_file):
            logging.warning(f"Local Vizard clip metadata file not found: {metadata_file}")
            return []
            
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            
        if not data or 'highlight_clips' not in data:
            logging.warning(f"Invalid local Vizard clip metadata format in {metadata_file}")
            return []
            
        clips = data['highlight_clips']
        logging.info(f"Loaded {len(clips)} local Vizard clips from metadata file")
        return clips
        
    except Exception as e:
        logging.error(f"Error loading local Vizard clip metadata: {str(e)}")
        return []

# Import HeyGen functions
from ai.heygen_client import create_heygen_video, get_heygen_videos_for_creatomate

# Import video functions
from video.scroll_generator import generate_scroll_video
from video.creatomate_client import create_creatomate_video

# Import centralized settings
from config.settings import get_scroll_settings, get_video_settings

# Load test data helpers (for AppEnv=test mode)
from utils.file_utils import load_test_data, save_test_data, save_assets_result

# Configure logging
logger = logging.getLogger(__name__)

def run_full_workflow(
    num_movies: int = 3,
    country: str = "US",
    genre: str = None,
    platform: str = None,
    content_type: str = "movie",
    skip_heygen: bool = False,
    scroll_seconds: int = 5,
    scroll_duration: float = 5.0,
    poster_timing_mode: str = "fixed",
    use_vizard_ai: bool = True,
    smooth_scroll: bool = True,
    scroll_distance: float = 1.5,
    heygen_template_id: str = "",
    raw_movies: list = None
) -> dict:
    """
    Run the complete StreamGank video generation workflow.
    
    This function orchestrates all the necessary steps to generate a complete
    video for a StreamGank feed, including:
    
    1. Movie data extraction from Supabase
    2. Script generation for HeyGen videos
    3. Asset preparation (posters, clips, etc.)
    4. HeyGen video generation
    5. Scroll video generation
    6. Final video assembly with Creatomate
    
    It uses modular approach, delegating specific functionality to dedicated
    modules and functions.
    
    Args:
        raw_movies (list): List of raw movie data from Supabase
        country (str): Country code (e.g., US, UK, etc.)
        genre (str): Movie genre (e.g., Action, Comedy, etc.)
        platform (str): Streaming platform (e.g., Netflix, Hulu, etc.)
        content_type (str): Type of content (default: "movie")
        check_status (bool): Check Creatomate render status (default: False)
        process_heygen (bool): Process HeyGen videos (default: False)
        num_movies (int): Number of movies to process (default: 3)
        scroll_seconds (int): Scroll video duration in seconds (default: 5)
        scroll_duration (float): Scroll duration (default: 5.0)
        poster_timing_mode (str): Poster timing strategy (default: "fixed")
        use_vizard_ai (bool): Use Vizard AI for clip processing (default: True)
        
    Returns:
        Dict[str, Any]: Complete workflow results including all generated assets
    """
    print("\n" + "=" * 80)
    print("🎬 STREAMGANK VIDEO GENERATION WORKFLOW")
    print("=" * 80)
    
    # Initialize workflow results tracking
    workflow_results = {
        'start_time': time.time(),
        'country': country,
        'genre': genre,
        'platform': platform,
        'content_type': content_type,
        'steps_completed': [],
        'errors': []
    }
    
    try:
        # Step 1: Extract movies from database or use cached test data
        print("\n[STEP 1/7] Movie Extraction - Fetching movies matching criteria")
        step_start = time.time()
        
        # Check if we have test data we can use
        test_data = load_test_data('assets', country, genre, platform)
        
        if test_data and isinstance(test_data, dict) and test_data.get('movies'):
            # Use test data
            extracted_movies = test_data.get('movies', [])[:num_movies]
            print(f"   📂 Using {len(extracted_movies)} movies from cached test data")
        elif raw_movies is not None and len(raw_movies) > 0:
            # Use provided movies
            extracted_movies = raw_movies[:num_movies]
            print(f"   👌 Using {len(extracted_movies)} provided movies")
        else:
            # Extract fresh movies from database
            print(f"   🔍 Extracting movies for {country}, {platform}, {genre}, {content_type}...")
            db_movies = extract_movie_data(
                country=country,
                genre=genre,
                platform=platform,
                content_type=content_type,
                num_movies=num_movies
            )
            
            # If database extraction failed, exit with clear error
            if db_movies is None:
                error_message = "❌ ERROR: Database extraction failed. Cannot proceed with workflow."
                print(error_message)
                raise Exception(error_message)
            else:
                # Process the results
                print(f"   🎞️ Found {len(db_movies)} movies")
            
        # Save to workflow results
        workflow_results['movies'] = extracted_movies
        workflow_results['steps_completed'].append('movie_extraction')
        print(f"   ✅ Movie extraction completed in {time.time() - step_start:.2f}s")
        
        # Step 2: Generate scripts for each movie
        print("\n[STEP 2/7] Script Generation - Creating scripts for HeyGen videos")
        step_start = time.time()
        
        # Check if we have cached scripts
        movie_scripts = {}
        
        if test_data and isinstance(test_data, dict) and test_data.get('movie_scripts'):
            # Use cached scripts from test data
            movie_scripts = test_data.get('movie_scripts', {})
            print("   📂 Using cached script data from test output")
        else:
            # Generate fresh scripts
            print("   🔄 Generating fresh scripts...")
            # generate_video_scripts returns a tuple (combined_script, script_path, individual_scripts)
            script_result = generate_video_scripts(extracted_movies)
            
            if isinstance(script_result, tuple) and len(script_result) == 3:
                combined_script, script_path, individual_scripts = script_result
                movie_scripts = individual_scripts
            else:
                movie_scripts = script_result  # Handle legacy or different return format
        
        if movie_scripts:
            workflow_results['movie_scripts'] = movie_scripts
            workflow_results['movie_scripts_generated'] = True
            workflow_results['steps_completed'].append('script_generation')
            print(f"   ✅ Script generation completed in {time.time() - step_start:.2f}s")
        else:
            print("   ⚠️ No scripts generated - check for errors")
        
        # Save script results to test_output for future use
        if movie_scripts:
            scripts_data_to_save = {
                'scripts': movie_scripts,
                'parameters': {
                    'country': country,
                    'genre': genre,
                    'platform': platform,
                    'content_type': content_type,
                    'num_movies': len(extracted_movies)
                }
            }
            save_test_data(scripts_data_to_save, 'scripts', country, genre, platform)
        else:
            print("   ❌ Script generation failed")
    except Exception as e:
        error_message = f"Error during movie extraction or script generation: {str(e)}"
        print(f"\n❌ {error_message}")
        workflow_results['errors'].append(error_message)
        return workflow_results
    
    # Step 2: Process HeyGen videos (if requested)
    if process_heygen:
        print("\n[STEP 2/7] HeyGen Processing - Retrieving HeyGen video URLs for Creatomate")
        step_start = time.time()
        
        # Get HeyGen video URLs
        heygen_video_urls = get_heygen_videos_for_creatomate()
        
        if heygen_video_urls:
            workflow_results['heygen_videos'] = heygen_video_urls
            workflow_results['steps_completed'].append('heygen_processing')
            print(f"   ✅ Retrieved {len(heygen_video_urls)} HeyGen video URLs")
        else:
            print("   ❌ Failed to retrieve HeyGen video URLs")
            
        # Skip other steps
        return workflow_results
    
    # Step 3: Asset preparation (posters and clips)
    if not check_status:
        print("\n[STEP 3/7] Asset Preparation - Creating enhanced posters and movie clips")
        step_start = time.time()
        
        # Skip cached assets if Vizard AI is requested
        cached_assets_data = None if use_vizard_ai else load_test_data('assets', country, genre, platform)
        
        if cached_assets_data and not use_vizard_ai:
            print("   📂 Using cached asset data from test_output...")
            
            enhanced_posters = cached_assets_data.get('enhanced_posters', {})
            dynamic_clips = cached_assets_data.get('dynamic_clips', {})
            
            if enhanced_posters and dynamic_clips:
                workflow_results['enhanced_posters'] = enhanced_posters
                workflow_results['dynamic_clips'] = dynamic_clips
                print(f"   ✅ Loaded {len(enhanced_posters)} posters and {len(dynamic_clips)} clips from cache")
            else:
                print("   ⚠️ Cached asset data incomplete, generating fresh...")
                cached_assets_data = None
        
        if not cached_assets_data:
            # Generate enhanced posters
            print("   🖼️ Creating enhanced movie posters...")
            enhanced_posters = create_enhanced_movie_posters(extracted_movies, max_movies=3)
            
            if enhanced_posters:
                print(f"   ✅ Created {len(enhanced_posters)} enhanced posters")
                workflow_results['enhanced_posters'] = enhanced_posters
            else:
                print("   ❌ Failed to create enhanced posters")
            
            # Process movie trailers to clips
            trailer_movies = []
            highlight_clips = []
            
            # Vizard AI is the only option now
            print("   🎬 Using Vizard AI for highlight extraction from trailers")
            # Check for locally prepared Vizard clips first
            local_vizard_clips = load_local_vizard_clips()
            
            if local_vizard_clips:
                print(f"   📂 Using {len(local_vizard_clips)} pre-prepared local Vizard clips")
                highlight_clips = local_vizard_clips
                print("   ✅ Local Vizard clips loaded successfully, skipping API calls")
            else:
                # No local clips, use the API
                print("   ⚠️ No local Vizard clips found, will make fresh API calls to Vizard for each trailer")
                print("   🔄 Generating fresh highlights from movie trailers using Vizard AI")
                print("   🛠️ Using the fixed VizardAIClient implementation")
                
                # Initialize list for collecting highlight clips
                highlight_clips = []
                
                trailer_movies = []
                
                for i, movie_data in enumerate(raw_movies[:num_movies]):
                    movie_id = movie_data.get('id')
                    movie_name = movie_data.get('title', f"Movie {i+1}")
                    trailer_url = movie_data.get('trailer_url')
                    
                    if not trailer_url or not trailer_url.startswith("https://www.youtube.com"):
                        print(f"   ⚠️ No valid YouTube trailer URL for {movie_name}")
                        continue
                    
                    print(f"   📋 Processing trailer for {movie_name} with Vizard AI...")
                    print(f"   🛠️ Using improved VizardAIClient with fixed video URL extraction")
                    
                    try:
                        movie_clips = extract_highlights_with_vizard(
                            youtube_url=trailer_url,
                            movie_title=movie_name,
                            num_clips=1,
                            clip_length=1,  # Use short clips
                            output_dir="temp_clips",
                            max_wait_minutes=15  # Set reasonable timeout for API processing
                        )
                        
                        if movie_clips:
                            print(f"   ✅ Successfully extracted {len(movie_clips)} clips for {movie_name}")
                            
                            # Add these clips to our collection
                            for clip_path in movie_clips:
                                highlight_clips.append({
                                    'local_path': clip_path,
                                    'name': f"{movie_name}_highlight_{len(highlight_clips) + 1}",
                                    'url': None,
                                    'index': len(highlight_clips)
                                })
                            
                            # Track movie that has trailer processed
                            trailer_movies.append(movie_data)
                        else:
                            print(f"   ❌ No clips extracted for {movie_name}")
                    except Exception as e:
                        print(f"   ❌ Failed to extract highlights for {movie_name}: {str(e)}")
                
                # If we have highlights, process them for the workflow
                if highlight_clips:
                    print(f"\n🎬 Processing {len(highlight_clips)} Vizard AI highlights for Creatomate assembly...")
                    
                    # Check if we have pre-uploaded clips with URLs or local paths
                    has_pre_uploaded = any(clip.get('url') for clip in highlight_clips)
                    has_local_paths = any(clip.get('local_path') for clip in highlight_clips)
                    
                    if has_pre_uploaded:
                        # Use existing Cloudinary URLs
                        print(f"   💾 Using {len(highlight_clips)} pre-uploaded clips with existing URLs")
                        vizard_clip_urls = [clip['url'] for clip in highlight_clips if clip.get('url')]
                    elif has_local_paths and not os.environ.get('CLOUDINARY_CLOUD_NAME'):
                        # Use local paths if Cloudinary is not configured
                        print(f"   💾 Using {len(highlight_clips)} local clip paths (Cloudinary not configured)")
                        # Get absolute paths for local clips
                        vizard_clip_urls = []
                        for clip in highlight_clips:
                            if clip.get('local_path'):
                                # Make sure we use absolute paths
                                path = clip['local_path']
                                if not os.path.isabs(path):
                                    path = os.path.abspath(path)
                                vizard_clip_urls.append(path)
                        print(f"   ✅ Found {len(vizard_clip_urls)} local clips to use directly")
                    else:
                        # Need to upload the clips to Cloudinary
                        print(f"   💾 Processing clips for Cloudinary upload")
                        vizard_clip_paths = [clip['local_path'] for clip in highlight_clips if clip.get('local_path')]
                        
                        try:
                            vizard_clip_urls = process_vizard_highlights_for_creatomate(
                                highlight_clips=vizard_clip_paths,
                                folder="vizard_ai_clips"
                            )
                            print(f"   ✅ Successfully uploaded {len(vizard_clip_urls)} clips to Cloudinary")
                        except Exception as e:
                            print(f"   ⚠️ Failed to upload clips to Cloudinary: {str(e)}")
                            # Fallback to local paths if upload fails
                            print(f"   🔄 Falling back to local clip paths")
                            vizard_clip_urls = [os.path.abspath(path) for path in vizard_clip_paths]
                    
                    # Replace movie clips with Vizard AI clips if we have any
                    if len(vizard_clip_urls) >= num_movies:
                        # Replace all clips with Vizard AI ones
                        dynamic_clips = vizard_clip_urls[:num_movies]
                        print(f"   🔄 Replaced all {num_movies} original clips with Vizard AI highlight clips")
                    elif len(vizard_clip_urls) > 0:
                        # Replace as many clips as we have, keeping original clips for the rest
                        original_clip_count = len(dynamic_clips)
                        for i, url in enumerate(vizard_clip_urls):
                            if i < original_clip_count:
                                dynamic_clips[i] = url
                        
                        print(f"   🔄 Replaced {len(vizard_clip_urls)}/{original_clip_count} clips with Vizard AI clips")
                        print(f"   ℹ️ Keeping {original_clip_count - len(vizard_clip_urls)} original clips")
                    
                    # Update workflow results with the final clips
                    workflow_results['final_movie_clips'] = dynamic_clips
                    workflow_results['vizard_ai_clips'] = highlight_clips
                    workflow_results['trailer_movies'] = trailer_movies
                else:
                    error_message = "❌ ERROR: No Vizard AI highlights could be generated and use_vizard_ai=True was specified"
                    print(error_message)
                    raise Exception(error_message)
            
            # Save asset results to test_output for future use
            assets_data_to_save = {
                'enhanced_posters': enhanced_posters,
                'dynamic_clips': dynamic_clips,
                'parameters': {
                    'country': country,
                    'genre': genre,
                    'platform': platform,
                    'content_type': content_type,
                    'num_movies': len(raw_movies) if raw_movies is not None else len(extracted_movies) if extracted_movies is not None else num_movies
                }
            }
            
            save_assets_result(assets_data_to_save, country, genre, platform)
        
        # Extract URLs for Creatomate
        movie_covers = list(enhanced_posters.values())[:3]
        
        # Handle dynamic_clips (should always be a list from Vizard now)
        # Keep compatibility check for safety
        if isinstance(dynamic_clips, dict):
            movie_clips = list(dynamic_clips.values())[:3]
        else:
            # Already a list (from Vizard AI processing)
            movie_clips = dynamic_clips[:3]
        
        # Check if we have enough movie clips when Vizard AI is requested
        if use_vizard_ai and (not movie_clips or len(movie_clips) < num_movies):
            error_message = f"❌ ERROR: Insufficient Vizard AI clips generated. Got {len(movie_clips)} clips but need {num_movies}"
            print(error_message)
            raise Exception(error_message)
        
        workflow_results['movie_covers'] = movie_covers
        workflow_results['final_movie_clips'] = movie_clips
        workflow_results['enhanced_posters'] = enhanced_posters
        workflow_results['dynamic_clips'] = dynamic_clips
        workflow_results['steps_completed'].append('asset_preparation')
        
        print(f"   ✅ Asset preparation completed in {time.time() - step_start:.2f}s")
    
    # Step 4: HeyGen Video Generation (skip in check_status mode or if skip_heygen is True)
    if not check_status:
        print("\n[STEP 4/7] HeyGen Video Generation - Creating avatar videos with scripts")
        step_start = time.time()
        
        # Skip this step if specified, checking status, or scripts weren't generated
        if skip_heygen:
            print("   ⏭️ Skipping HeyGen video generation (skip_heygen=True)")
        elif not workflow_results.get('movie_scripts_generated', False):
            print("   ⏭️ Skipping HeyGen video generation (scripts not available)")
        else:
            # Generate HeyGen videos using the scripts
            movie_scripts = workflow_results.get('movie_scripts', {})
            
            if not movie_scripts:
                print("   ⚠️ No scripts available for HeyGen video generation")
            else:
                # Actually create HeyGen videos
                heygen_videos = {}
                
                for movie_id, script_data in movie_scripts.items():
                    movie_name = script_data.get('movie_name', f"Movie {movie_id}")
                    script_text = script_data.get('script_text', "")
                    
                    if not script_text:
                        print(f"   ⚠️ No script text for {movie_name}, skipping...")
                        continue
                    
                    print(f"   🎭 Creating HeyGen video for {movie_name}...")
                    heygen_result = create_heygen_video(
                        movie_name=movie_name,
                        script_text=script_text,
                        max_attempts=3
                    )
                    
                    if heygen_result and 'video_id' in heygen_result:
                        print(f"   ✅ Created HeyGen video: {heygen_result.get('video_id')}")
                        heygen_videos[movie_id] = heygen_result
                    else:
                        print(f"   ❌ Failed to create HeyGen video for {movie_name}")
                
                workflow_results['heygen_videos'] = heygen_videos
                workflow_results['steps_completed'].append('heygen_generation')
                
                print(f"   ✅ HeyGen video generation completed in {time.time() - step_start:.2f}s")
    
    # Step 5: Scroll Video Generation (skip in check_status mode)
    if not check_status:
        print("\n[STEP 5/7] Scroll Video Generation - Creating scroll videos for each movie")
        step_start = time.time()
        
        # Skip this step if we don't have enhanced posters
        if 'enhanced_posters' not in workflow_results:
            print("   ⏭️ Skipping scroll video generation (no enhanced posters)")
        else:
            # Get scroll settings
            scroll_settings = get_scroll_settings()
            
            # Generate scroll videos for each movie
            enhanced_posters = workflow_results.get('enhanced_posters', {})
            scroll_videos = {}
            
            for movie_id, poster_url in enhanced_posters.items():
                # Safely handle raw_movies if it's None
                if raw_movies is not None:
                    movie_data = next((m for m in raw_movies if str(m.get('id')) == str(movie_id)), {})
                else:
                    movie_data = {}
                movie_name = movie_data.get('title', f"Movie {movie_id}")
                
                print(f"   📱 Creating scroll video for {movie_name}...")
                # Get required parameters from context
                scroll_video = generate_scroll_video(
                    country=country,
                    genre=genre,
                    platform=platform,
                    content_type=content_type,
                    smooth=scroll_settings.get('smooth', True),
                    scroll_distance=scroll_settings.get('scroll_distance', 1.5),
                    duration=scroll_seconds or 4  # Default to 4 seconds if not specified
                )
                
                if scroll_video:
                    print(f"   ✅ Created scroll video for {movie_name}")
                    scroll_videos[movie_id] = scroll_video
                else:
                    print(f"   ❌ Failed to create scroll video for {movie_name}")
            
            workflow_results['scroll_videos'] = scroll_videos
            workflow_results['steps_completed'].append('scroll_generation')
            
            print(f"   ✅ Scroll video generation completed in {time.time() - step_start:.2f}s")
    
    # Step 6: Final Video Assembly with Creatomate
    print("\n[STEP 6/7] Final Video Assembly - Creating final video with Creatomate")
    step_start = time.time()
    
    if check_status:
        print("   🔍 Checking Creatomate render status...")
        # TODO: Implement Creatomate status check
        print("   ⚠️ Creatomate status check not implemented yet")
    else:
        # Skip this step if we don't have necessary assets
        if 'movie_covers' not in workflow_results or 'final_movie_clips' not in workflow_results:
            print("   ⏭️ Skipping final video assembly (missing required assets)")
        else:
            # Get video settings
            video_settings = get_video_settings()
            
            # Create final video with Creatomate
            movie_covers = workflow_results.get('movie_covers', [])
            movie_clips = workflow_results.get('final_movie_clips', [])
            heygen_videos = workflow_results.get('heygen_videos', {})
            scroll_videos = workflow_results.get('scroll_videos', {})
            
            # Check if we have HeyGen videos
            heygen_video_urls = [video.get('video_url') for video in heygen_videos.values() if video.get('video_url')]
            if not heygen_video_urls:
                error_message = "❌ ERROR: No HeyGen videos available. Cannot continue with video assembly."
                print(error_message)
                raise Exception(error_message)
            
            # Check if we have scroll videos
            scroll_video_urls = list(scroll_videos.values()) if scroll_videos else []
            if not scroll_video_urls:
                error_message = "❌ ERROR: No scroll videos available. Cannot continue with video assembly."
                print(error_message)
                raise Exception(error_message)
            # We've already added error handling above that will prevent us from reaching here
            # with empty scroll_video_urls, but keeping this check for clarity
            print(f"   📱 Using {len(scroll_video_urls)} generated scroll videos")
            
            print("   🎬 Creating final video composition with Creatomate...")
            final_composition = build_video_composition(
                heygen_video_urls=heygen_video_urls,
                movie_covers=movie_covers,
                movie_clips=movie_clips,
                scroll_video_url=scroll_video_urls
            )
            
            if final_composition:
                print(f"   ✅ Created final video composition: {final_composition.get('id')}")
                workflow_results['final_composition'] = final_composition
            
            if final_video:
                print(f"   ✅ Created final video: {final_video.get('id')}")
                workflow_results['final_composition'] = final_video
                workflow_results['steps_completed'].append('final_assembly')
            else:
                print("   ❌ Failed to create final video")
    
    print(f"   ✅ Final video assembly completed in {time.time() - step_start:.2f}s")
    
    # Step 7: Workflow Summary
    print("\n[STEP 7/7] Workflow Summary - Final results")
    print("-" * 80)
    
    # Print summary of completed steps
    completed_steps = workflow_results.get('steps_completed', [])
    print(f"✅ Completed {len(completed_steps)}/{7} workflow steps:")
    for step in completed_steps:
        print(f"   ✓ {step}")
    
    # Print final composition details if available
    final_composition = workflow_results.get('final_composition')
    if final_composition:
        print("\n🎬 Final Video:")
        print(f"   🆔 ID: {final_composition.get('id')}")
        print(f"   🔗 URL: {final_composition.get('url')}")
        print(f"   ⏱️ Duration: {final_composition.get('duration', 0):.2f}s")
    
    print("\n" + "=" * 80)
    print("✅ WORKFLOW COMPLETE")
    print("=" * 80)
    
    return workflow_results


def process_existing_heygen_videos(heygen_video_ids: Dict[str, str], output_file: str = None) -> Dict[str, Any]:
    """
    Process existing HeyGen videos to create the final video.
    
    Args:
        heygen_video_ids (dict): Dictionary of movie_id -> video_id mappings
        output_file (str): Output file path for results
        
    Returns:
        dict: Processing results
    """
    print("\n" + "=" * 80)
    print("🎭 PROCESSING EXISTING HEYGEN VIDEOS")
    print("=" * 80)
    print(f"📋 Processing {len(heygen_video_ids)} HeyGen videos")
    
    # Initialize results
    results = {
        'status': 'pending',
        'heygen_videos': {},
        'processed_count': 0,
        'error_count': 0
    }
    
    try:
        # Get HeyGen video URLs
        heygen_videos = get_heygen_videos_for_creatomate(video_ids=list(heygen_video_ids.values()))
        
        if heygen_videos:
            results['heygen_videos'] = heygen_videos
            results['processed_count'] = len(heygen_videos)
            results['status'] = 'success'
            print(f"✅ Successfully processed {len(heygen_videos)} HeyGen videos")
        else:
            results['status'] = 'error'
            results['error'] = 'No HeyGen videos processed'
            print("❌ Failed to process HeyGen videos")
    
    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)
        results['error_count'] += 1
        print(f"❌ Error processing HeyGen videos: {str(e)}")
    
    # Save results if output file specified
    if output_file and results.get('heygen_videos'):
        from utils.file_utils import safe_write_file
        safe_write_file(output_file, results)
        print(f"📄 Results saved to {output_file}")
    
    return results
