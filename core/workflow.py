"""
StreamGank Core Workflow Orchestration

This module contains the main workflow functions that orchestrate the complete
video generation process. It coordinates between all modules to maintain the
same output as the original system while providing clean, readable code for
senior engineers.

EXACT SAME APPROACH AS LEGACY SYSTEM - PROVEN TO WORK
"""

import logging
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import modular functions
from ai.robust_script_generator import generate_video_scripts
from video.poster_generator import create_enhanced_movie_posters
# Import clip processing (standard video processing without AI + parallel Vizard AI)
from video.clip_processor import process_movie_trailers_to_clips, process_movie_trailers_to_clips_vizard, process_movie_trailers_to_clips_vizard_parallel

# Import database functions
from database.movie_extractor import extract_movie_data

# Import HeyGen functions
from ai.heygen_client import create_heygen_video, get_heygen_videos_for_creatomate

# Import video functions
from video.scroll_generator import generate_scroll_video
from video.creatomate_client import create_creatomate_video

# Import media utilities for background music selection
from media.media_utils import select_background_music, get_background_music_info

# Import centralized settings
from config.settings import get_scroll_settings, get_video_settings

# Import test data caching utilities
from utils.test_data_cache import (
    load_test_data, save_workflow_result,
    get_app_env, should_use_cache, should_save_results,
    is_local_mode, is_development_mode, is_production_mode
)

# Import webhook client for real-time step updates
from utils.webhook_client import create_webhook_client

# Import job logger for persistent logging
from utils.job_logger import get_job_logger

logger = logging.getLogger(__name__)

# =============================================================================
# MAIN WORKFLOW ORCHESTRATION
# =============================================================================

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
                     heygen_template_id: str = None,
                     pause_after_extraction: bool = False) -> dict:
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
    save_enabled = should_save_results()
    
    print("🚀 Starting StreamGank video generation workflow")
    
    # Enhanced environment logging
    if is_local_mode():
        print(f"🌍 Environment: APP_ENV='{app_env}' (LOCAL: Cache only, no API calls)")
    elif is_development_mode():
        print(f"🌍 Environment: APP_ENV='{app_env}' (DEVELOPMENT: API calls + save results)")
    elif is_production_mode():
        print(f"🌍 Environment: APP_ENV='{app_env}' (PRODUCTION: API calls only, no saving)")
    else:
        print(f"🌍 Environment: APP_ENV='{app_env}' (Cache: {'ENABLED' if cache_enabled else 'DISABLED'}, Save: {'ENABLED' if save_enabled else 'DISABLED'})")
    
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
    
    # Initialize webhook client for real-time step updates
    webhook_client = create_webhook_client()
    
    # Initialize job logger for persistent logging
    job_logger = get_job_logger()
    job_id = os.getenv('JOB_ID', f"workflow_{int(time.time())}")
    
    # Log workflow start
    job_logger.log_job_event(job_id, "workflow_started", "Video generation workflow initiated", {
        'parameters': workflow_results['parameters'],
        'environment': app_env,
        'cache_enabled': cache_enabled,
        'save_enabled': save_enabled
    })
    
    # Send webhook notification
    webhook_client.send_workflow_started(total_steps=7)
    
    try:
        # =============================================================================
        # STEP 1: DATABASE EXTRACTION
        # =============================================================================
        print(f"\n[STEP 1/7] Database Extraction - Extracting {num_movies} movies from database")
        step_start = time.time()
        print(f"   Filters: {country}, {genre}, {platform}, {content_type}")
        
        # Send real-time webhook update for step start
        webhook_client.send_step_update(
            step_number=1,
            step_name="Database Extraction",
            status="started",
            duration=0,
            details={'country': country, 'genre': genre, 'platform': platform, 'num_movies': num_movies}
        )
        
        # Log step start
        job_logger.log_step_start(job_id, 1, "Database Extraction", {
            'num_movies': num_movies,
            'filters': {
                'country': country,
                'genre': genre,
                'platform': platform,
                'content_type': content_type
            }
        })
        
        raw_movies = extract_movie_data(
            num_movies=num_movies,
            country=country,
            genre=genre,
            platform=platform,
            content_type=content_type
        )
        
        if not raw_movies:
            raise Exception("Database extraction failed - no movies found")
        
        # Log the extracted movies for user visibility
        print(f"\n📋 Movies extracted from database:")
        for i, movie in enumerate(raw_movies, 1):
            movie_title = movie.get('title', 'Unknown Title')
            movie_year = movie.get('year', 'Unknown Year')
            imdb_score = movie.get('imdb', 'N/A')
            print(f"   {i}. {movie_title} ({movie_year}) - IMDB: {imdb_score}")
        
        # Check if we have fewer than requested movies and stop gracefully
        if len(raw_movies) < num_movies:
            error_message = f"Insufficient movies found - only {len(raw_movies)} movie(s) available with current filters"
            print(f"\n❌ {error_message}")
            print(f"   Filters used: Country={country}, Genre={genre}, Platform={platform}, Content Type={content_type}")
            
            # Show the movies that were found
            print(f"\n🎬 Movies found with current filters:")
            for i, movie in enumerate(raw_movies, 1):
                movie_title = movie.get('title', 'Unknown Title')
                movie_year = movie.get('year', 'Unknown Year')
                print(f"   {i}. {movie_title} ({movie_year})")
            
            print(f"\n   Please try different filters to find more movies")
            print(f"   Suggestions:")
            print(f"     - Try a different genre")
            print(f"     - Try a different platform") 
            print(f"     - Try a different content type (Movies vs TV Shows)")
            print(f"     - Try a different country")
            raise Exception(error_message)
        
        workflow_results['raw_movies'] = raw_movies
        workflow_results['steps_completed'].append('database_extraction')
        
        # Save incremental progress in development mode
        if save_enabled:
            save_workflow_result(workflow_results, country, genre, platform)
        
        step_duration = time.time() - step_start
        print(f"✅ STEP 1 COMPLETED - Found {len(raw_movies)} movies in {step_duration:.1f}s")
        
        # Log step completion
        job_logger.log_step_complete(job_id, 1, "Database Extraction", step_duration, {
            'movies_found': len(raw_movies),
            'movies_data': [{'title': m.get('title'), 'imdb_score': m.get('imdb_score')} 
                           for m in raw_movies[:3]]  # Log first 3 movies as sample
        })
        
        # Send real-time webhook update
        webhook_client.send_step_update(
            step_number=1,
            step_name="Database Extraction",
            status="completed", 
            duration=step_duration,
            details={'movies_found': len(raw_movies)}
        )
        
        # =============================================================================
        # PAUSE AFTER EXTRACTION (if requested)
        # =============================================================================
        if pause_after_extraction:
            print(f"\n⏸️  PROCESS PAUSED - Movie extraction completed")
            print(f"📋 Found {len(raw_movies)} movies:")
            for i, movie in enumerate(raw_movies, 1):
                title = movie.get('title', 'Unknown Title')
                year = movie.get('year', 'Unknown Year')
                imdb_score = movie.get('imdb', 'N/A')  # Use 'imdb' field to match the regular extraction
                print(f"   {i}. {title} ({year}) - IMDB: {imdb_score}")
            
            print(f"\n💡 To continue with video generation, run without --pause-after-extraction flag")
            print(f"📊 Movies data saved to workflow results")
            
            # Return results with extracted movies for review
            workflow_results['paused_after_extraction'] = True
            workflow_results['extraction_summary'] = {
                'total_movies': len(raw_movies),
                'movies': raw_movies,
                'filters_used': {
                    'country': country,
                    'genre': genre, 
                    'platform': platform,
                    'content_type': content_type
                }
            }
            
            return workflow_results
        
        # =============================================================================
        # STEP 2: SCRIPT GENERATION (MODULAR FUNCTION WITH TEST DATA CACHING)
        # =============================================================================
        print(f"\n[STEP 2/7] Script Generation - Generating scripts for {genre} content on {platform}")
        step_start = time.time()
        
        # Send real-time webhook update for step start
        webhook_client.send_step_update(
            step_number=2,
            step_name="Script Generation",
            status="started",
            duration=0,
            details={'genre': genre, 'platform': platform, 'num_movies': len(raw_movies)}
        )
        
        # Log step start
        job_logger.log_step_start(job_id, 2, "Script Generation", {
            'genre': genre,
            'platform': platform,
            'cache_enabled': cache_enabled
        })
        
        # Try to load existing script data from test_output
        cached_script_data = load_test_data('script_result', country, genre, platform)
        
        # For testing intelligent highlights, we want to use cached scripts if available
        if cached_script_data and should_use_cache():
        #if True:
            print("   📂 Using cached script data from test_output...")
            
            # Extract data from cached result (with safe fallbacks)
            combined_script = cached_script_data.get('combined_script', '') if isinstance(cached_script_data, dict) else ''
            script_file_path = cached_script_data.get('script_file_path', '') if isinstance(cached_script_data, dict) else ''
            individual_scripts = cached_script_data.get('individual_scripts', {}) if isinstance(cached_script_data, dict) else {}
            
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
            
            # Script results saved via save_workflow_result() call below
        
        workflow_results['combined_script'] = combined_script
        workflow_results['script_file_path'] = script_file_path
        workflow_results['individual_scripts'] = individual_scripts
        workflow_results['steps_completed'].append('script_generation')
        
        # Save incremental progress in development mode
        if save_enabled:
            save_workflow_result(workflow_results, country, genre, platform)
        
        step_duration = time.time() - step_start
        print(f"✅ STEP 2 COMPLETED - Using {len(individual_scripts)} scripts in {step_duration:.1f}s")
        
        # Log step completion
        job_logger.log_step_complete(job_id, 2, "Script Generation", step_duration, {
            'scripts_generated': len(individual_scripts),
            'scripts_from_cache': should_use_cache() and cached_script_data is not None,
            'combined_script_length': len(combined_script) if combined_script else 0
        })
        
        # Send real-time webhook update
        webhook_client.send_step_update(
            step_number=2,
            step_name="Script Generation",
            status="completed",
            duration=step_duration,
            details={'scripts_generated': len(individual_scripts)}
        )
        
        # =============================================================================
        # STEP 3: ASSET PREPARATION (MODULAR FUNCTIONS WITH TEST DATA CACHING)
        # =============================================================================
        print(f"\n[STEP 3/7] Asset Preparation - Creating enhanced posters and movie clips")
        step_start = time.time()
        
        # Send real-time webhook update for step start
        webhook_client.send_step_update(
            step_number=3,
            step_name="Asset Preparation",
            status="started",
            duration=0,
            details={'num_movies': len(raw_movies), 'cache_enabled': cache_enabled}
        )
        
        # Log step start
        job_logger.log_step_start(job_id, 3, "Asset Preparation", {
            'num_movies': len(raw_movies),
            'cache_enabled': cache_enabled
        })
        
        # Try to load existing asset data from test_output
        cached_assets_data = load_test_data('assets', country, genre, platform)
        
        if cached_assets_data and should_use_cache():
        # if False: # TESTING POSTER UPLOAD TO streamgank-reels/enhanced-poster-cover
            print("   📂 Using cached asset data from test_output...")
            
            enhanced_posters = cached_assets_data.get('enhanced_posters', {})
            dynamic_clips = cached_assets_data.get('dynamic_clips', {})
            
            print(f"   📋 Loaded {len(enhanced_posters)} cached posters and {len(dynamic_clips)} cached clips")
            
            # Check if cached data already has background music, otherwise select new one
            if 'background_music_url' in cached_assets_data:
                background_music_url = cached_assets_data['background_music_url']
                background_music_info = cached_assets_data.get('background_music_info', 
                    get_background_music_info(genre))
                print(f"   📋 Loaded cached background music: {background_music_info['type']}")
            else:
                print("   🎵 No cached background music found, selecting new one...")
                background_music_url = select_background_music(genre)
                background_music_info = get_background_music_info(genre)
                print(f"   ✅ Selected {background_music_info['type']} background music for {genre}")
            
            print(f"   🔗 Music URL: {background_music_url}")
            
        else:
            print("   🔄 No cached assets found, generating new assets...")
            
            # Create enhanced posters (MODULAR FUNCTION)
            print("   Creating enhanced movie posters with metadata overlays...")
            enhanced_posters = create_enhanced_movie_posters(raw_movies, max_movies=3)
            
            if not enhanced_posters or len(enhanced_posters) < 3:
                raise Exception(f"Failed to create enhanced posters - got {len(enhanced_posters) if enhanced_posters else 0}, need 3")
            
            # Process movie clips with Vizard AI (NEW IMPLEMENTATION)
            print("   🚀 Processing movie trailers with VIZARD AI - PARALLEL MODE!")
            print("   ⚡ PARALLEL PROCESSING: 66-75% FASTER than sequential (2-4 min vs 6-12 min)")
            print("   🔥 Step 1: Creating ALL Vizard projects SIMULTANEOUSLY")
            print("   ⏳ Step 2: Polling ALL projects in PARALLEL until complete")
            print("   🏆 Step 3: Selecting clips with highest viral scores (per movie)")
            print("   📥 Step 4: Downloading clips from Vizard AI (parallel downloads)")
            print("   ⏱️ Step 5: Checking duration and trimming to 20s if ≥30s")
            print("   ☁️ Step 6: Uploading clips to Cloudinary (streamgank-reels/movie-clips)")
            print("   📊 Step 7: Extracting clip metadata (duration, viral reason, etc.)")
            print("   ✅ Step 8: ALL movies complete simultaneously - proceeding to next step")
            print("")
            print("   📡 Response Codes:")
            print("     - Code 1000: Still processing (continue waiting)")
            print("     - Code 2000: Processing complete (clips ready)")
            print("   🔁 Retry Mechanism:")
            print("     - 3 attempts per API query (prevents timeout errors)")
            print("     - Smart retry for Code 2000 + empty videos (API glitch)")
            print("     - Exponential backoff: 10s, 12s, 14s delays")
            print("   🚀 IMPORTANT: This step processes ALL movies AT THE SAME TIME!")
            print("   ⏰ Expected total time: 2-4 minutes (instead of 6-12 minutes sequential)")
            print("")
            
            # Use Vizard AI to process the movie trailers (PARALLEL IMPLEMENTATION - 66-75% FASTER!)
            dynamic_clips = process_movie_trailers_to_clips_vizard_parallel(
                raw_movies, 
                max_movies=3, 
                transform_mode="youtube_shorts"
            )
            # Old function (FALLBACK): dynamic_clips = process_movie_trailers_to_clips(
            #     raw_movies, 
            #     max_movies=3, 
            #     transform_mode="youtube_shorts"
            # )
            
            # Enhanced: Allow partial success with graceful handling
            if not dynamic_clips or len(dynamic_clips) == 0:
                raise Exception("Failed to create any movie clips - cannot proceed without video content")
            elif len(dynamic_clips) < 3:
                logger.warning(f"⚠️ Partial clip success: Got {len(dynamic_clips)}/3 clips - continuing with available content")
                print(f"   ⚠️ Some trailers failed processing (YouTube restrictions/short videos) - continuing with {len(dynamic_clips)} clips")
            
            # Asset results saved via save_workflow_result() call below
        
        # Select background music based on genre (NEW FEATURE)
        print("   🎵 Selecting background music based on genre...")
        background_music_url = select_background_music(genre)
        background_music_info = get_background_music_info(genre)
        
        print(f"   ✅ Selected {background_music_info['type']} background music for {genre}")
        print(f"   🔗 Music URL: {background_music_url}")
        
        # Extract URLs for Creatomate
        movie_covers = list(enhanced_posters.values())[:3]
        movie_clips = list(dynamic_clips.values())[:3]
        
        workflow_results['movie_covers'] = movie_covers
        workflow_results['movie_clips'] = movie_clips
        workflow_results['enhanced_posters'] = enhanced_posters
        workflow_results['dynamic_clips'] = dynamic_clips
        workflow_results['background_music_url'] = background_music_url
        workflow_results['background_music_info'] = background_music_info
        workflow_results['steps_completed'].append('asset_preparation')
        
        # Save incremental progress in development mode
        if save_enabled:
            save_workflow_result(workflow_results, country, genre, platform)
        
        step_duration = time.time() - step_start
        print(f"✅ STEP 3 COMPLETED - Created {len(movie_covers)} posters and {len(movie_clips)} clips in {step_duration:.1f}s")
        
        # Log step completion
        job_logger.log_step_complete(job_id, 3, "Asset Preparation", step_duration, {
            'posters_created': len(movie_covers),
            'clips_processed': len(movie_clips),
            'assets_from_cache': should_use_cache() and cached_assets_data is not None
        })
        
        # Send real-time webhook update
        webhook_client.send_step_update(
            step_number=3,
            step_name="Asset Preparation",
            status="completed",
            duration=step_duration,
            details={
                'posters_created': len(movie_covers),
                'clips_processed': len(movie_clips)
            }
        )
        
        # =============================================================================
        # STEP 4: HEYGEN VIDEO CREATION (WITH ENVIRONMENT-AWARE CACHING)
        # =============================================================================
        print(f"\n[STEP 4/7] HeyGen Video Creation - Generating AI avatar videos")
        step_start = time.time()
        
        # Send real-time webhook update for step start
        webhook_client.send_step_update(
            step_number=4,
            step_name="HeyGen Video Creation",
            status="started",
            duration=0,
            details={'num_scripts': len(individual_scripts), 'heygen_template_id': heygen_template_id}
        )
        
        # Log step start
        job_logger.log_step_start(job_id, 4, "HeyGen Video Creation", {
            'num_scripts': len(individual_scripts),
            'heygen_template_id': heygen_template_id,
            'cache_enabled': cache_enabled
        })
        
        # Try to load existing HeyGen data from cache
        cached_heygen_data = load_test_data('heygen', country, genre, platform)
        
        if cached_heygen_data and should_use_cache():
            print("   📂 Using cached HeyGen data from test_output...")
            
            # Extract data from cached result (with safe fallbacks)
            heygen_video_ids = cached_heygen_data.get('video_ids', {}) if isinstance(cached_heygen_data, dict) else {}
            template_id_used = cached_heygen_data.get('template_id', heygen_template_id) if isinstance(cached_heygen_data, dict) else heygen_template_id
            
            print(f"   📋 Loaded {len(heygen_video_ids)} cached HeyGen video IDs")
            
        else:
            if is_local_mode():
                raise Exception("LOCAL MODE: No cached HeyGen data available. Run with APP_ENV=development first to generate and cache data.")
            
            print("   🔄 No cached HeyGen data found, creating new videos...")
            print("   Using HeyGen API for video generation...")
            
            heygen_video_ids = create_heygen_video(individual_scripts, True, heygen_template_id)
            
            if not heygen_video_ids:
                raise Exception("HeyGen video creation failed")
            
            # HeyGen results saved via save_workflow_result() call below
        
        workflow_results['heygen_video_ids'] = heygen_video_ids
        workflow_results['steps_completed'].append('heygen_creation')
        
        # Save incremental progress in development mode
        if save_enabled:
            save_workflow_result(workflow_results, country, genre, platform)
        
        step_duration = time.time() - step_start
        print(f"✅ STEP 4 COMPLETED - {'Loaded' if should_use_cache() and cached_heygen_data else 'Created'} {len(heygen_video_ids)} HeyGen videos in {step_duration:.1f}s")
        
        # Log step completion
        job_logger.log_step_complete(job_id, 4, "HeyGen Video Creation", step_duration, {
            'videos_created': len(heygen_video_ids),
            'from_cache': should_use_cache() and cached_heygen_data is not None,
            'template_id': heygen_template_id
        })
        
        # Send real-time webhook update
        webhook_client.send_step_update(
            step_number=4,
            step_name="HeyGen Video Creation",
            status="completed",
            duration=step_duration,
            details={
                'videos_created': len(heygen_video_ids),
                'from_cache': should_use_cache() and cached_heygen_data is not None
            }
        )
        
        # =============================================================================
        # STEP 5: GET HEYGEN VIDEO URLS (WITH ENVIRONMENT-AWARE CACHING)
        # =============================================================================
        print(f"\n[STEP 5/7] HeyGen Video Processing - Waiting for video completion")
        step_start = time.time()
        
        # Send real-time webhook update for step start
        webhook_client.send_step_update(
            step_number=5,
            step_name="HeyGen Processing",
            status="started",
            duration=0,
            details={'video_ids_count': len(heygen_video_ids), 'cache_enabled': cache_enabled}
        )
        
        # Log step start
        job_logger.log_step_start(job_id, 5, "HeyGen Processing", {
            'video_ids_count': len(heygen_video_ids),
            'cache_enabled': cache_enabled
        })
        
        # Try to load existing HeyGen URLs from cache
        cached_heygen_urls_data = load_test_data('heygen_urls', country, genre, platform)
        
        if cached_heygen_urls_data and should_use_cache():
            print("   📂 Using cached HeyGen URLs from test_output...")
            
            # Extract data from cached result (with safe fallbacks)
            heygen_video_urls = cached_heygen_urls_data.get('video_urls', {}) if isinstance(cached_heygen_urls_data, dict) else {}
            
            print(f"   📋 Loaded {len(heygen_video_urls)} cached HeyGen video URLs")
            
        else:
            if is_local_mode():
                raise Exception("LOCAL MODE: No cached HeyGen URL data available. Run with APP_ENV=development first to generate and cache data.")
            
            print("   🔄 No cached HeyGen URLs found, fetching from API...")
            print("   Waiting for HeyGen video processing completion...")
            
            heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids, individual_scripts)
            
            if not heygen_video_urls:
                raise Exception("HeyGen video URL retrieval failed")
            
            # HeyGen URLs saved via save_workflow_result() call below
        
        workflow_results['heygen_video_urls'] = heygen_video_urls
        workflow_results['steps_completed'].append('heygen_processing')
        
        # Save incremental progress in development mode
        if save_enabled:
            save_workflow_result(workflow_results, country, genre, platform)
        
        print(f"✅ STEP 5 COMPLETED - Got {len(heygen_video_urls)} video URLs in {time.time() - step_start:.1f}s")
        
        # Send real-time webhook update
        webhook_client.send_step_update(
            step_number=5,
            step_name="HeyGen Processing",
            status="completed",
            duration=time.time() - step_start,
            details={'video_urls_retrieved': len(heygen_video_urls)}
        )
        
        # =============================================================================
        # STEP 6: SCROLL VIDEO GENERATION (WITH ENVIRONMENT-AWARE CACHING)
        # =============================================================================
        scroll_video_url = None
        if not skip_scroll_video:
            print(f"\n[STEP 6/7] Scroll Video Generation - Creating StreamGank scroll overlay")
            step_start = time.time()
            
            # Send real-time webhook update for step start
            webhook_client.send_step_update(
                step_number=6,
                step_name="Scroll Video Generation",
                status="started",
                duration=0,
                details={'skip_scroll_video': skip_scroll_video, 'smooth_scroll': smooth_scroll, 'scroll_distance': scroll_distance}
            )
            
            # Log step start
            job_logger.log_step_start(job_id, 6, "Scroll Video Generation", {
                'skip_scroll_video': skip_scroll_video,
                'smooth_scroll': smooth_scroll,
                'scroll_distance': scroll_distance,
                'cache_enabled': cache_enabled
            })
            
            # Try to load existing scroll video data from cache
            cached_scroll_data = load_test_data('scroll_video', country, genre, platform)
            
            if cached_scroll_data and should_use_cache():
                print("   📂 Using cached scroll video data from test_output...")
                
                # Extract data from cached result (with safe fallbacks)
                scroll_video_url = cached_scroll_data.get('scroll_video_url', None) if isinstance(cached_scroll_data, dict) else None
                
                if scroll_video_url:
                    print(f"   📋 Loaded cached scroll video URL")
                else:
                    print(f"   ⚠️ Cached scroll video data found but no valid URL")
                
            else:
                if is_local_mode():
                    print("   🌍 LOCAL MODE: No cached scroll video data available")
                    print("   ⚠️ Continuing without scroll video (no API calls in local mode)")
                    scroll_video_url = None
                else:
                    print("   🔄 No cached scroll video data found, generating new video...")
                    print("   Using scroll video generation API...")
                    
                    scroll_video_url = generate_scroll_video(
                        country=country,
                        genre=genre,
                        platform=platform,
                        content_type=content_type,
                        smooth=smooth_scroll,
                        scroll_distance=scroll_distance,
                        duration=scroll_settings.get('target_duration', 4)
                    )
                    
                    # Scroll video results saved via save_workflow_result() call below
            
            if scroll_video_url:
                workflow_results['scroll_video_url'] = scroll_video_url
                print(f"✅ STEP 6 COMPLETED - {'Loaded' if should_use_cache() and cached_scroll_data and cached_scroll_data.get('scroll_video_url') else 'Generated'} scroll video in {time.time() - step_start:.1f}s")
            else:
                print(f"⚠️ STEP 6 SKIPPED - Scroll video {'not available in cache' if is_local_mode() else 'generation failed'}, continuing without it")
                
            # Send real-time webhook update
            webhook_client.send_step_update(
                step_number=6,
                step_name="Scroll Video Generation",
                status="completed",
                duration=time.time() - step_start,
                details={
                    'scroll_video_created': scroll_video_url is not None,
                    'from_cache': should_use_cache() and cached_scroll_data and cached_scroll_data.get('scroll_video_url')
                }
            )
        else:
            print(f"\n[STEP 6/7] Scroll Video Generation - SKIPPED (user requested)")
            
            # Send real-time webhook update for skipped step
            webhook_client.send_step_update(
                step_number=6,
                step_name="Scroll Video Generation",
                status="completed",
                duration=0,
                details={'skip_scroll_video': True, 'reason': 'User requested to skip scroll video'}
            )
            
            # Log skipped step 6
            job_logger.log_job_event(job_id, "step_skipped", "Step 6/7 skipped: Scroll Video Generation", {
                'step_number': 6,
                'step_name': 'Scroll Video Generation',
                'reason': 'User requested to skip scroll video',
                'skip_scroll_video': skip_scroll_video
            })
        
        workflow_results['steps_completed'].append('scroll_generation')
        
        # Save incremental progress in development mode
        if save_enabled:
            save_workflow_result(workflow_results, country, genre, platform)
        
        # =============================================================================
        # STEP 7: CREATOMATE FINAL ASSEMBLY (WITH ENVIRONMENT-AWARE CACHING)
        # =============================================================================
        print(f"\n[STEP 7/7] Creatomate Assembly - Creating final video")
        step_start = time.time()
        
        # Send real-time webhook update for step start
        webhook_client.send_step_update(
            step_number=7,
            step_name="Creatomate Assembly",
            status="started",
            duration=0,
            details={'heygen_urls_count': len(heygen_video_urls), 'poster_timing_mode': poster_timing_mode, 'has_scroll_video': scroll_video_url is not None}
        )
        
        # Log step start
        job_logger.log_step_start(job_id, 7, "Creatomate Assembly", {
            'heygen_urls_count': len(heygen_video_urls),
            'poster_timing_mode': poster_timing_mode,
            'has_scroll_video': scroll_video_url is not None,
            'cache_enabled': cache_enabled
        })
        
        # Try to load existing Creatomate data from cache
        cached_creatomate_data = load_test_data('creatomate', country, genre, platform)
        
        #if cached_creatomate_data and should_use_cache():
        if False:
            print("   📂 Using cached Creatomate data from test_output...")
            
            # Extract data from cached result (with safe fallbacks)
            creatomate_id = cached_creatomate_data.get('render_id', '') if isinstance(cached_creatomate_data, dict) else ''
            
            if creatomate_id and not creatomate_id.startswith('error'):
                print(f"   📋 Loaded cached Creatomate render ID: {creatomate_id}")
            else:
                raise Exception(f"LOCAL MODE: Invalid cached Creatomate data: {creatomate_id}")
            
        else:
            if is_local_mode():
                raise Exception("LOCAL MODE: No cached Creatomate data available. Run with APP_ENV=development first to generate and cache data.")
            
            print("   🔄 No cached Creatomate data found, creating new video...")
            print("   Using Creatomate API for final video assembly...")
            
            creatomate_id = create_creatomate_video(
                heygen_video_urls=heygen_video_urls,
                movie_covers=movie_covers,
                movie_clips=movie_clips,
                scroll_video_url=scroll_video_url,
                scripts=individual_scripts,
                poster_timing_mode=poster_timing_mode,
                background_music_url=workflow_results.get('background_music_url')
            )
            
            if not creatomate_id or creatomate_id.startswith('error'):
                raise Exception(f"Creatomate video creation failed: {creatomate_id}")
            
            # Creatomate results saved via save_workflow_result() call below
        
        workflow_results['creatomate_id'] = creatomate_id
        workflow_results['steps_completed'].append('creatomate_assembly')
        
        # Save incremental progress in development mode
        if save_enabled:
            save_workflow_result(workflow_results, country, genre, platform)
        
        step_duration = time.time() - step_start
        print(f"✅ STEP 7 COMPLETED - {'Loaded' if should_use_cache() and cached_creatomate_data else 'Created'} final video in {step_duration:.1f}s")
        
        # Log step completion
        job_logger.log_step_complete(job_id, 7, "Creatomate Assembly", step_duration, {
            'creatomate_id': creatomate_id,
            'from_cache': should_use_cache() and cached_creatomate_data is not None,
            'poster_timing_mode': poster_timing_mode
        })
        
        # Send real-time webhook update
        webhook_client.send_step_update(
            step_number=7,
            step_name="Creatomate Assembly",
            status="completed",
            duration=step_duration,
            details={
                'creatomate_id': creatomate_id,
                'from_cache': should_use_cache() and cached_creatomate_data is not None
            }
        )
        
        # =============================================================================
        # WORKFLOW COMPLETION
        # =============================================================================
        total_duration = time.time() - workflow_results['start_time']
        workflow_results['status'] = 'completed'
        workflow_results['total_duration'] = total_duration
        workflow_results['end_time'] = time.time()
        
        # Save complete workflow results for development mode
        save_workflow_result(workflow_results, country, genre, platform)
        
        print(f"\n🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
        print(f"   ⏱️ Total duration: {total_duration:.1f}s")
        print(f"   📊 Steps completed: {len(workflow_results['steps_completed'])}/7")
        print(f"   🎬 Creatomate ID: {creatomate_id}")
        
        # Log workflow completion
        job_logger.log_workflow_complete(job_id, total_duration, creatomate_id, {
            'steps_completed': len(workflow_results['steps_completed']),
            'environment': app_env,
            'cache_used': cache_enabled,
            'final_creatomate_id': creatomate_id
        })
        
        # Send final workflow completion webhook
        webhook_client.send_workflow_completed(
            total_duration=total_duration,
            creatomate_id=creatomate_id
        )
        
        # Show environment-specific completion message
        if is_local_mode():
            print(f"   🌍 LOCAL MODE: Used cached data for all steps")
        elif is_development_mode():
            print(f"   🔧 DEVELOPMENT MODE: Generated and saved data for future use")
        elif is_production_mode():
            print(f"   💼 PRODUCTION MODE: Generated fresh data without caching")
        
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
        
        # Log workflow failure
        failed_step = len(workflow_results['steps_completed']) + 1
        job_logger.log_workflow_failed(job_id, str(e), failed_step, {
            'steps_completed_before_failure': len(workflow_results['steps_completed']),
            'failed_at_step': failed_step,
            'duration_before_failure': total_duration
        })
        
        # Send workflow failure webhook
        webhook_client.send_workflow_failed(
            error=str(e),
            step_number=failed_step
        )
        
        # Show environment-specific error guidance
        if is_local_mode() and "No cached" in str(e):
            print(f"   💡 LOCAL MODE TIP: Run with APP_ENV=development first to generate cache data")
        elif is_production_mode():
            print(f"   💼 PRODUCTION MODE: Check API connectivity and quotas")
        elif is_development_mode():
            print(f"   🔧 DEVELOPMENT MODE: Check API connectivity, cached data will be preserved")
        
        # Save partial results if output file specified
        if output:
            try:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(workflow_results, f, indent=2, ensure_ascii=False)
                print(f"   📁 Partial results saved to: {output}")
            except Exception as save_error:
                print(f"   ⚠️ Failed to save partial results: {str(save_error)}")
        
        # Re-raise the original exception instead of a generic one
        raise

# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================

def process_existing_heygen_videos(heygen_video_ids: Dict[str, str],
                                  output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Process existing HeyGen video IDs and create Creatomate video
    
    This function maintains compatibility with the legacy system for processing
    existing HeyGen videos without running the full workflow.
    
    Args:
        heygen_video_ids (Dict[str, str]): Dictionary with HeyGen video IDs
        output_file (Optional[str]): Output file path for results
        
    Returns:
        Dict[str, Any]: Processing results
    """
    logger.info("🔄 Processing existing HeyGen video IDs")
    
    results = {
        'input_video_ids': heygen_video_ids,
        'timestamp': time.strftime("%Y%m%d_%H%M%S")
    }
    
    try:
        # Get HeyGen video URLs
        logger.info("Step 1: Getting HeyGen video URLs")
        # Use empty scripts dict for existing video processing
        empty_scripts = {key: f"Existing video {i+1}" for i, key in enumerate(heygen_video_ids.keys())}
        heygen_video_urls = get_heygen_videos_for_creatomate(heygen_video_ids, empty_scripts)
        
        if not heygen_video_urls:
            logger.error("❌ No HeyGen video URLs obtained")
            results['status'] = 'failed'
            results['error'] = 'No HeyGen video URLs obtained'
            return results
        
        results['heygen_video_urls'] = heygen_video_urls
        logger.info(f"✅ Successfully obtained {len(heygen_video_urls)} HeyGen video URLs")
        
        # Create Creatomate video (using placeholder assets for existing videos workflow)
        logger.info("Step 2: Creating Creatomate video from existing HeyGen videos")
        creatomate_id = create_creatomate_video(
            heygen_video_urls=heygen_video_urls,
            scripts=None
        )
        
        results['creatomate_id'] = creatomate_id
        
        if creatomate_id.startswith('error') or creatomate_id.startswith('exception'):
            logger.error(f"❌ Creatomate video creation failed: {creatomate_id}")
            results['status'] = 'failed'
            results['error'] = f'Creatomate creation failed: {creatomate_id}'
        else:
            logger.info(f"🎬 Successfully submitted Creatomate video: {creatomate_id}")
            results['status'] = 'success'
            results['creatomate_status'] = 'submitted'
            results['status_check_command'] = f"python main.py --check-creatomate {creatomate_id}"
        
        # Save results
        if output_file:
            try:
                import json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"Results saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save results: {str(e)}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing existing HeyGen videos: {str(e)}")
        results['status'] = 'error'
        results['error'] = str(e)
        return results

def validate_workflow_inputs(num_movies: int,
                           country: str,
                           genre: str, 
                           platform: str,
                           content_type: str) -> Dict[str, Any]:
    """
    Validate workflow input parameters
    
    Args:
        num_movies (int): Number of movies to process
        country (str): Country code
        genre (str): Genre filter
        platform (str): Platform name
        content_type (str): Content type
        
    Returns:
        Dict[str, Any]: Validation results
    """
    validation_results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Validate num_movies
    if not isinstance(num_movies, int) or num_movies < 1 or num_movies > 10:
        validation_results['valid'] = False
        validation_results['errors'].append(f"Invalid num_movies: {num_movies} (must be 1-10)")
    
    # Validate country
    if not country or not isinstance(country, str):
        validation_results['valid'] = False
        validation_results['errors'].append("Country is required and must be a string")
    
    # Validate genre
    if not genre or not isinstance(genre, str):
        validation_results['valid'] = False
        validation_results['errors'].append("Genre is required and must be a string")
    
    # Validate platform
    if not platform or not isinstance(platform, str):
        validation_results['valid'] = False
        validation_results['errors'].append("Platform is required and must be a string")
    
    # Validate content_type
    if not content_type or not isinstance(content_type, str):
        validation_results['valid'] = False
        validation_results['errors'].append("Content type is required and must be a string")
    
    return validation_results

def get_workflow_status(workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current workflow status and progress
    
    Args:
        workflow_results (Dict[str, Any]): Current workflow results
        
    Returns:
        Dict[str, Any]: Status information
    """
    if not workflow_results:
        return {'status': 'not_started', 'progress': 0}
    
    status = workflow_results.get('status', 'unknown')
    steps_completed = workflow_results.get('steps_completed', [])
    total_steps = 7
    
    progress = (len(steps_completed) / total_steps) * 100 if total_steps > 0 else 0
    
    return {
        'status': status,
        'progress': progress,
        'steps_completed': steps_completed,
        'total_steps': total_steps,
        'current_step': len(steps_completed) + 1 if status != 'completed' else total_steps
    }