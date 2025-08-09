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
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import modular functions
from ai.robust_script_generator import generate_video_scripts
from video.poster_generator import create_enhanced_movie_posters
from video.clip_processor import process_movie_trailers_to_clips

# Import database functions
from database.movie_extractor import extract_movie_data

# Import HeyGen functions
from ai.heygen_client import create_heygen_video, get_heygen_videos_for_creatomate

# Import video functions
from video.scroll_generator import generate_scroll_video
from video.creatomate_client import create_creatomate_video

# Import centralized settings
from config.settings import get_scroll_settings, get_video_settings

# Import test data caching utilities
from utils.test_data_cache import load_test_data, save_script_result, save_assets_result, get_app_env, should_use_cache

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
        
        # Log the extracted movies for user visibility
        print(f"\n📋 Movies extracted from database:")
        for i, movie in enumerate(raw_movies, 1):
            movie_title = movie.get('title', 'Unknown Title')
            movie_year = movie.get('year', 'Unknown Year')
            imdb_score = movie.get('imdb', 'N/A')
            print(f"   {i}. {movie_title} ({movie_year}) - IMDB: {imdb_score}")
        
        # Check if we have fewer than 3 movies and stop gracefully
        if len(raw_movies) < 3:
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
        
        print(f"✅ STEP 1 COMPLETED - Found {len(raw_movies)} movies in {time.time() - step_start:.1f}s")
        
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