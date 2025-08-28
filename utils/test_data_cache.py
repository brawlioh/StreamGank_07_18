"""
StreamGank Test Data Caching Utility

This module provides functions for caching test data to avoid regenerating
expensive operations during development and testing.

Features:
- Save/load script generation results
- Save/load asset generation results (posters, clips)
- Standardized file naming based on parameters
- JSON serialization with UTF-8 encoding
- Automatic directory creation

Author: StreamGank Development Team
Version: 1.0.0 - Test Data Caching System
"""

import os
import json
import logging
import re
import time
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

def get_app_env() -> str:
    """
    Get the current application environment.
    
    Returns:
        str: Application environment ('local', 'prod', etc.)
    """
    return os.getenv('APP_ENV', 'local').lower()


def should_use_cache() -> bool:
    """
    Determine if test data caching should be used based on environment.
    
    3-tier environment system:
    - production: No cache, API calls only
    - development: API calls + save all results 
    - local: Cache only, no API calls
    
    Returns:
        bool: True if cache should be used for reading, False otherwise
    """
    app_env = get_app_env()
    
    # Use cache in local development, not in production
    if app_env == 'local':
        logger.info(f"🌍 LOCAL MODE: Cache reading ENABLED - will use cached data")
        return True
    elif app_env in ['prod', 'production']:
        logger.info(f"🌍 PRODUCTION MODE: Cache reading DISABLED - will generate fresh data")
        return False
    elif app_env in ['dev', 'development']:
        # Development mode - use APIs but will save results
        logger.info(f"🌍 DEVELOPMENT MODE: Cache reading DISABLED - will generate fresh data and save results")
        return False  # Don't read cache initially, but will save
    else:
        # For other environments (staging, test, etc.), use cache by default
        logger.info(f"🌍 UNKNOWN APP_ENV '{app_env}': Defaulting to cache reading ENABLED")
        return True


def should_save_results() -> bool:
    """
    Determine if results should be saved based on environment.
    
    Returns:
        bool: True if results should be saved to cache, False otherwise
    """
    app_env = get_app_env()
    
    if app_env in ['local', 'dev', 'development']:
        logger.info(f"🌍 APP_ENV='{app_env}': Cache saving ENABLED - will save all results")
        return True
    elif app_env in ['prod', 'production']:
        logger.info(f"🌍 APP_ENV='{app_env}': Cache saving DISABLED - will not save results")
        return False
    else:
        # For other environments, default to saving
        logger.info(f"🌍 APP_ENV='{app_env}': Cache saving ENABLED (default)")
        return True


def is_local_mode() -> bool:
    """
    Check if we're in local mode (no API calls, cache only).
    
    Returns:
        bool: True if in local mode, False otherwise
    """
    app_env = get_app_env()
    return app_env == 'local'


def is_development_mode() -> bool:
    """
    Check if we're in development mode (API calls + save results).
    
    Returns:
        bool: True if in development mode, False otherwise
    """
    app_env = get_app_env()
    return app_env in ['dev', 'development']


def is_production_mode() -> bool:
    """
    Check if we're in production mode (API calls only, no saving).
    
    Returns:
        bool: True if in production mode, False otherwise
    """
    app_env = get_app_env()
    return app_env in ['prod', 'production']

# =============================================================================
# TEST DATA CACHING FUNCTIONS
# =============================================================================

def get_test_data_path(data_type: str, country: str, genre: str, platform: str) -> str:
    """
    Generate standardized path for test data files.
    
    Args:
        data_type (str): Type of data ('script_result', 'movie_data', 'assets', etc.)
        country (str): Country parameter
        genre (str): Genre parameter  
        platform (str): Platform parameter
        
    Returns:
        str: Path to test data file
    """
    # Create safe filename from parameters
    safe_country = country.replace(' ', '_').lower()
    safe_genre = genre.replace(' ', '_').replace('&', 'and').lower()
    safe_platform = platform.replace(' ', '_').lower()
    
    filename = f"{data_type}_{safe_country}_{safe_genre}_{safe_platform}.json"
    return os.path.join('test_output', filename)


def save_test_data(data: Any, data_type: str, country: str, genre: str, platform: str) -> str:
    """
    Save test data to test_output directory based on environment.
    
    Args:
        data: Data to save (must be JSON serializable)
        data_type (str): Type of data being saved
        country (str): Country parameter
        genre (str): Genre parameter
        platform (str): Platform parameter
        
    Returns:
        str: Path where data was saved, empty string if failed or not saved
    """
    try:
        # Check if we should save results based on environment
        if not should_save_results():
            app_env = get_app_env()
            logger.info(f"💼 Results not saved for APP_ENV='{app_env}' (production mode)")
            return ""  # Don't save in production mode
        # Ensure test_output directory exists
        os.makedirs('test_output', exist_ok=True)
        
        file_path = get_test_data_path(data_type, country, genre, platform)
        
        # Add metadata to the saved data
        data_with_metadata = {
            'data': data,
            'metadata': {
                'data_type': data_type,
                'parameters': {
                    'country': country,
                    'genre': genre,
                    'platform': platform
                },
                'saved_timestamp': time.time(),
                'saved_datetime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_with_metadata, f, indent=2, ensure_ascii=False)
        
        app_env = get_app_env()
        logger.info(f"💾 Saved {data_type} test data to: {file_path} (APP_ENV='{app_env}')")
        return file_path
        
    except Exception as e:
        logger.error(f"❌ Error saving test data: {str(e)}")
        return ""


def try_load_from_workflow(data_type: str, country: str, genre: str, platform: str) -> Optional[Any]:
    """
    Try to extract specific data from existing workflow files as fallback.
    
    Args:
        data_type (str): Type of data to extract
        country (str): Country parameter
        genre (str): Genre parameter  
        platform (str): Platform parameter
        
    Returns:
        Any: Extracted data or None if not found
    """
    try:
        # Construct workflow file path - FIXED ORDER: Replace & with 'and' BEFORE removing special chars
        country_clean = re.sub(r'[^\w\s-]', '', country.strip()).replace(' ', '_').lower()
        genre_clean = genre.strip().replace('&', 'and').replace(' ', '_').lower()
        genre_clean = re.sub(r'[^\w-]', '', genre_clean)  # Clean after replacements
        platform_clean = re.sub(r'[^\w\s-]', '', platform.strip()).replace(' ', '_').lower()
        
        workflow_filename = f"workflow_{country_clean}_{genre_clean}_{platform_clean}.json"
        workflow_path = os.path.join('test_output', workflow_filename)
        
        logger.info(f"🔍 CONSTRUCTED filename: {workflow_filename}")
        logger.info(f"   Parameters: country='{country}' -> '{country_clean}', genre='{genre}' -> '{genre_clean}', platform='{platform}' -> '{platform_clean}'")
        logger.info(f"🔍 WORKFLOW FALLBACK: Looking for {data_type} in {workflow_filename}")
        
        if not os.path.exists(workflow_path):
            logger.warning(f"❌ WORKFLOW FILE NOT FOUND: {workflow_path}")
            return None
            
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_file = json.load(f)
        
        # Handle the actual structure with "data" wrapper
        if isinstance(workflow_file, dict) and 'data' in workflow_file:
            workflow_data = workflow_file['data']
            logger.info(f"✅ Found workflow data structure with 'data' wrapper")
        else:
            workflow_data = workflow_file
            logger.info(f"✅ Using direct workflow data structure")
        
        logger.info(f"🔍 Available keys in workflow_data: {list(workflow_data.keys()) if isinstance(workflow_data, dict) else 'Not a dict'}")
        
        # Extract specific data based on type - NEW ORGANIZED STEP STRUCTURE ONLY
        if data_type == 'script_result':
            logger.info(f"🔍 Looking for script_result data...")
            # Check if script data exists in step 2
            if 'step_2_script_generation' in workflow_data:
                step_data = workflow_data['step_2_script_generation']
                logger.info(f"✅ FOUND script data in step_2_script_generation!")
                result = {
                    'combined_script': step_data.get('combined_script', ''),
                    'script_file_path': step_data.get('script_file_path', ''),
                    'individual_scripts': step_data.get('individual_scripts', {})
                }
                logger.info(f"✅ RETURNING script data with {len(result['individual_scripts'])} individual scripts")
                return result
            else:
                logger.warning(f"❌ No 'step_2_script_generation' found in workflow data")
                
        elif data_type == 'assets':
            logger.info(f"🔍 Looking for assets data...")
            # Check if asset data exists in step 3
            if 'step_3_asset_preparation' in workflow_data:
                step_data = workflow_data['step_3_asset_preparation']
                logger.info(f"✅ FOUND asset data in step_3_asset_preparation!")
                result = {
                    'enhanced_posters': step_data.get('enhanced_posters', {}),
                    'dynamic_clips': step_data.get('dynamic_clips', {}),
                    'movie_covers': step_data.get('movie_covers', []),
                    'movie_clips': step_data.get('movie_clips', []),
                    'background_music_url': step_data.get('background_music_url', ''),
                    'background_music_info': step_data.get('background_music_info', {})
                }
                logger.info(f"✅ RETURNING asset data with {len(result['enhanced_posters'])} posters and {len(result['dynamic_clips'])} clips")
                return result
            else:
                logger.warning(f"❌ No 'step_3_asset_preparation' found in workflow data")
                
        elif data_type == 'heygen':
            logger.info(f"🔍 Looking for heygen data...")
            # Check if heygen data exists in step 4
            if 'step_4_heygen_creation' in workflow_data:
                step_data = workflow_data['step_4_heygen_creation']
                logger.info(f"✅ FOUND heygen data in step_4_heygen_creation!")
                result = {
                    'video_ids': step_data.get('heygen_video_ids', {}),
                    'template_id': step_data.get('template_id_used', '')
                }
                logger.info(f"✅ RETURNING heygen data with {len(result['video_ids'])} video IDs")
                return result
            else:
                logger.warning(f"❌ No 'step_4_heygen_creation' found in workflow data")
                
        elif data_type == 'heygen_urls':
            logger.info(f"🔍 Looking for heygen URLs data...")
            # Check if heygen URLs exist in step 5
            if 'step_5_heygen_processing' in workflow_data:
                step_data = workflow_data['step_5_heygen_processing']
                logger.info(f"✅ FOUND heygen URLs in step_5_heygen_processing!")
                result = {
                    'video_urls': step_data.get('heygen_video_urls', {})
                }
                logger.info(f"✅ RETURNING heygen URLs with {len(result['video_urls'])} URLs")
                return result
            else:
                logger.warning(f"❌ No 'step_5_heygen_processing' found in workflow data")
                
        elif data_type == 'scroll_video':
            logger.info(f"🔍 Looking for scroll video data...")
            # Check if scroll video exists in step 6
            if 'step_6_scroll_generation' in workflow_data:
                step_data = workflow_data['step_6_scroll_generation']
                logger.info(f"✅ FOUND scroll video in step_6_scroll_generation!")
                result = {
                    'scroll_video_url': step_data.get('scroll_video_url')
                }
                logger.info(f"✅ RETURNING scroll video URL")
                return result
            else:
                logger.warning(f"❌ No 'step_6_scroll_generation' found in workflow data")
                
        elif data_type == 'creatomate':
            logger.info(f"🔍 Looking for creatomate data...")
            # Check if creatomate data exists in step 7
            if 'step_7_creatomate_assembly' in workflow_data:
                step_data = workflow_data['step_7_creatomate_assembly']
                logger.info(f"✅ FOUND creatomate data in step_7_creatomate_assembly!")
                result = {
                    'render_id': step_data.get('creatomate_id', '')
                }
                logger.info(f"✅ RETURNING creatomate render ID")
                return result
            else:
                logger.warning(f"❌ No 'step_7_creatomate_assembly' found in workflow data")
        
        logger.warning(f"❌ No data found for type '{data_type}' in workflow file")
        return None
            
    except Exception as e:
        logger.error(f"❌ EXCEPTION in try_load_from_workflow({data_type}): {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None


def load_test_data(data_type: str, country: str, genre: str, platform: str) -> Optional[Any]:
    """
    Load test data from unified workflow files in test_output directory.
    
    NEW ARCHITECTURE: All data is saved in single workflow files.
    Direct extraction from workflow_*.json files based on data_type.
    
    Args:
        data_type (str): Type of data to load
        country (str): Country parameter
        genre (str): Genre parameter
        platform (str): Platform parameter
        
    Returns:
        Any: Loaded data or None if file doesn't exist, loading fails, or cache disabled
    """
    try:
        # Check if caching should be used based on environment
        if not should_use_cache():
            app_env = get_app_env()
            logger.info(f"🚫 Cache disabled for APP_ENV='{app_env}' - will generate fresh data")
            return None
        
        app_env = get_app_env()
        logger.info(f"🔍 Loading {data_type} from workflow file for APP_ENV='{app_env}'")
        
        # Load directly from workflow file (new unified system)
        workflow_data = try_load_from_workflow(data_type, country, genre, platform)
        if workflow_data:
            logger.info(f"✅ Loaded {data_type} from workflow file")
            return workflow_data
        
        # If no workflow data found
        if is_local_mode():
            logger.error(f"❌ LOCAL MODE: No workflow data found for {data_type}")
            logger.error(f"   💡 Run with APP_ENV=development first to generate and save workflow data")
        else:
            logger.info(f"📁 No workflow data found for {data_type} - will generate fresh")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error loading test data: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None


def clear_test_data(data_type: Optional[str] = None, country: Optional[str] = None, 
                   genre: Optional[str] = None, platform: Optional[str] = None) -> int:
    """
    Clear test data files based on filters.
    
    Args:
        data_type (str, optional): Specific data type to clear
        country (str, optional): Specific country to clear
        genre (str, optional): Specific genre to clear  
        platform (str, optional): Specific platform to clear
        
    Returns:
        int: Number of files deleted
    """
    try:
        if not os.path.exists('test_output'):
            logger.info("📁 No test_output directory found")
            return 0
        
        files_deleted = 0
        
        for filename in os.listdir('test_output'):
            if not filename.endswith('.json'):
                continue
            
            # Parse filename to check filters
            parts = filename.replace('.json', '').split('_')
            if len(parts) < 4:
                continue
            
            file_data_type = parts[0]
            file_country = parts[1]
            file_genre = '_'.join(parts[2:-1])  # Handle multi-word genres
            file_platform = parts[-1]
            
            # Check if file matches filters
            should_delete = True
            
            if data_type and file_data_type != data_type.lower():
                should_delete = False
            if country and file_country != country.replace(' ', '_').lower():
                should_delete = False
            if genre and file_genre != genre.replace(' ', '_').replace('&', 'and').lower():
                should_delete = False
            if platform and file_platform != platform.replace(' ', '_').lower():
                should_delete = False
            
            if should_delete:
                file_path = os.path.join('test_output', filename)
                os.remove(file_path)
                files_deleted += 1
                logger.info(f"🗑️ Deleted test data: {filename}")
        
        logger.info(f"✅ Cleared {files_deleted} test data files")
        return files_deleted
        
    except Exception as e:
        logger.error(f"❌ Error clearing test data: {str(e)}")
        return 0


def list_test_data() -> Dict[str, Any]:
    """
    List all available test data files with their metadata.
    
    Returns:
        Dict: Information about available test data files
    """
    try:
        if not os.path.exists('test_output'):
            return {'files': [], 'total_count': 0, 'total_size_mb': 0}
        
        files_info = []
        total_size = 0
        
        for filename in os.listdir('test_output'):
            if not filename.endswith('.json'):
                continue
            
            file_path = os.path.join('test_output', filename)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            
            # Try to load metadata
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                metadata = data.get('metadata', {}) if isinstance(data, dict) and 'metadata' in data else {}
                
                file_info = {
                    'filename': filename,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / 1024 / 1024, 2),
                    'data_type': metadata.get('data_type', 'unknown'),
                    'parameters': metadata.get('parameters', {}),
                    'saved_datetime': metadata.get('saved_datetime', 'unknown')
                }
                
                files_info.append(file_info)
                
            except Exception:
                # If we can't load the file, just add basic info
                file_info = {
                    'filename': filename,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / 1024 / 1024, 2),
                    'data_type': 'unknown',
                    'parameters': {},
                    'saved_datetime': 'unknown'
                }
                files_info.append(file_info)
        
        return {
            'files': files_info,
            'total_count': len(files_info),
            'total_size_mb': round(total_size / 1024 / 1024, 2)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing test data: {str(e)}")
        return {'files': [], 'total_count': 0, 'total_size_mb': 0, 'error': str(e)}


# =============================================================================
# CONVENIENCE FUNCTIONS FOR SPECIFIC DATA TYPES
# =============================================================================

def save_script_result(script_data: Dict, country: str, genre: str, platform: str) -> str:
    """
    Save script generation result with additional metadata based on environment.
    
    Args:
        script_data (Dict): Script data including combined_script, individual_scripts, etc.
        country (str): Country parameter
        genre (str): Genre parameter
        platform (str): Platform parameter
        
    Returns:
        str: Path where data was saved, empty string if not saved
    """
    # Check if we should save results based on environment
    if not should_save_results():
        app_env = get_app_env()
        logger.debug(f"💼 Script results not saved for APP_ENV='{app_env}'")
        return ""
    
    # Add script-specific metadata
    enhanced_data = {
        **script_data,
        'script_count': len(script_data.get('individual_scripts', {})),
        'generation_timestamp': time.time()
    }
    
    return save_test_data(enhanced_data, 'script_result', country, genre, platform)


def save_assets_result(assets_data: Dict, country: str, genre: str, platform: str) -> str:
    """
    Save asset generation result with additional metadata based on environment.
    
    Args:
        assets_data (Dict): Asset data including enhanced_posters, dynamic_clips, etc.
        country (str): Country parameter
        genre (str): Genre parameter
        platform (str): Platform parameter
        
    Returns:
        str: Path where data was saved, empty string if not saved
    """
    # Check if we should save results based on environment
    if not should_save_results():
        app_env = get_app_env()
        logger.debug(f"💼 Asset results not saved for APP_ENV='{app_env}'")
        return ""
    
    # Add asset-specific metadata
    enhanced_data = {
        **assets_data,
        'poster_count': len(assets_data.get('enhanced_posters', {})),
        'clip_count': len(assets_data.get('dynamic_clips', {})),
        'generation_timestamp': time.time()
    }
    
    return save_test_data(enhanced_data, 'assets', country, genre, platform)


def save_heygen_result(heygen_data: Dict, country: str, genre: str, platform: str) -> str:
    """
    Save HeyGen generation result based on environment.
    
    Args:
        heygen_data (Dict): HeyGen data including video_ids, urls, etc.
        country (str): Country parameter
        genre (str): Genre parameter
        platform (str): Platform parameter
        
    Returns:
        str: Path where data was saved, empty string if not saved
    """
    if not should_save_results():
        app_env = get_app_env()
        logger.debug(f"💼 HeyGen results not saved for APP_ENV='{app_env}'")
        return ""
    
    enhanced_data = {
        **heygen_data,
        'video_count': len(heygen_data.get('video_ids', {})),
        'generation_timestamp': time.time()
    }
    
    return save_test_data(enhanced_data, 'heygen', country, genre, platform)


def save_creatomate_result(creatomate_data: Dict, country: str, genre: str, platform: str) -> str:
    """
    Save Creatomate generation result based on environment.
    
    Args:
        creatomate_data (Dict): Creatomate data including render_id, status, etc.
        country (str): Country parameter
        genre (str): Genre parameter
        platform (str): Platform parameter
        
    Returns:
        str: Path where data was saved, empty string if not saved
    """
    if not should_save_results():
        app_env = get_app_env()
        logger.debug(f"💼 Creatomate results not saved for APP_ENV='{app_env}'")
        return ""
    
    enhanced_data = {
        **creatomate_data,
        'generation_timestamp': time.time()
    }
    
    return save_test_data(enhanced_data, 'creatomate', country, genre, platform)


def save_workflow_result(workflow_data: Dict, country: str, genre: str, platform: str) -> str:
    """
    Save complete workflow result based on environment.
    
    Args:
        workflow_data (Dict): Complete workflow data including all steps
        country (str): Country parameter
        genre (str): Genre parameter
        platform (str): Platform parameter
        
    Returns:
        str: Path where data was saved, empty string if not saved
    """
    if not should_save_results():
        app_env = get_app_env()
        logger.debug(f"💼 Workflow results not saved for APP_ENV='{app_env}'")
        return ""
    
    enhanced_data = {
        **workflow_data,
        'completed_steps': len(workflow_data.get('steps_completed', [])),
        'final_timestamp': time.time()
    }
    
    return save_test_data(enhanced_data, 'workflow', country, genre, platform)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the test data cache.
    
    Returns:
        Dict: Cache statistics and information
    """
    cache_info = list_test_data()
    
    # Group by data type
    data_types = {}
    for file_info in cache_info['files']:
        data_type = file_info['data_type']
        if data_type not in data_types:
            data_types[data_type] = {'count': 0, 'size_mb': 0}
        
        data_types[data_type]['count'] += 1
        data_types[data_type]['size_mb'] += file_info['size_mb']
    
    return {
        'total_files': cache_info['total_count'],
        'total_size_mb': cache_info['total_size_mb'],
        'data_types': data_types,
        'cache_directory': 'test_output',
        'cache_available': os.path.exists('test_output')
    }