"""
StreamGank File Utilities

This module provides file operations, directory management, temporary file
handling, and cleanup utilities used throughout the StreamGank system.
"""

import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict
import json
import time

logger = logging.getLogger(__name__)

# =============================================================================
# DIRECTORY MANAGEMENT
# =============================================================================

def ensure_directory(directory_path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path (str): Path to directory
        
    Returns:
        bool: True if directory exists or was created successfully
    """
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {str(e)}")
        return False


def is_directory_writable(directory_path: str) -> bool:
    """
    Check if a directory is writable.
    
    Args:
        directory_path (str): Path to directory
        
    Returns:
        bool: True if directory is writable
    """
    try:
        path = Path(directory_path)
        if not path.exists():
            return False
        
        # Try to create a temporary file
        test_file = path / f".write_test_{int(time.time())}"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception:
        return False


def get_directory_size(directory_path: str) -> int:
    """
    Get total size of directory in bytes.
    
    Args:
        directory_path (str): Path to directory
        
    Returns:
        int: Total size in bytes, 0 if error
    """
    try:
        total_size = 0
        path = Path(directory_path)
        
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    except Exception as e:
        logger.warning(f"Could not calculate directory size for {directory_path}: {str(e)}")
        return 0

# =============================================================================
# TEMPORARY FILE MANAGEMENT
# =============================================================================

def get_temp_filename(prefix: str = "streamgank", suffix: str = "", extension: str = "") -> str:
    """
    Generate a unique temporary filename.
    
    Args:
        prefix (str): Filename prefix
        suffix (str): Filename suffix
        extension (str): File extension (with or without dot)
        
    Returns:
        str: Full path to temporary file
    """
    # Ensure extension starts with dot
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    
    # Create unique filename
    timestamp = str(int(time.time()))
    filename = f"{prefix}_{timestamp}{suffix}{extension}"
    
    # Get temp directory
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / filename
    
    logger.debug(f"Generated temp filename: {temp_path}")
    return str(temp_path)


def create_temp_directory(prefix: str = "streamgank") -> Optional[str]:
    """
    Create a temporary directory.
    
    Args:
        prefix (str): Directory name prefix
        
    Returns:
        str: Path to created directory, None if failed
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"{prefix}_")
        logger.debug(f"Created temp directory: {temp_dir}")
        return temp_dir
    except Exception as e:
        logger.error(f"Failed to create temp directory: {str(e)}")
        return None


def cleanup_temp_files(file_patterns: List[str], temp_dir: str = None) -> Dict[str, Any]:
    """
    Clean up temporary files matching given patterns.
    
    Args:
        file_patterns (list): List of file patterns to clean up
        temp_dir (str): Temp directory to clean, uses system temp if None
        
    Returns:
        dict: Cleanup summary
    """
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()
    
    cleanup_result = {
        'files_deleted': 0,
        'files_failed': 0,
        'bytes_freed': 0,
        'errors': []
    }
    
    try:
        temp_path = Path(temp_dir)
        
        for pattern in file_patterns:
            matching_files = list(temp_path.glob(pattern))
            
            for file_path in matching_files:
                try:
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleanup_result['files_deleted'] += 1
                        cleanup_result['bytes_freed'] += file_size
                        logger.debug(f"Deleted temp file: {file_path}")
                    elif file_path.is_dir():
                        dir_size = get_directory_size(str(file_path))
                        shutil.rmtree(file_path)
                        cleanup_result['files_deleted'] += 1
                        cleanup_result['bytes_freed'] += dir_size
                        logger.debug(f"Deleted temp directory: {file_path}")
                except Exception as e:
                    cleanup_result['files_failed'] += 1
                    cleanup_result['errors'].append(f"Failed to delete {file_path}: {str(e)}")
                    logger.warning(f"Failed to delete {file_path}: {str(e)}")
        
        logger.info(f"Cleanup completed: {cleanup_result['files_deleted']} files deleted, {cleanup_result['bytes_freed']} bytes freed")
        
    except Exception as e:
        cleanup_result['errors'].append(f"Cleanup error: {str(e)}")
        logger.error(f"Temp file cleanup error: {str(e)}")
    
    return cleanup_result

# =============================================================================
# SAFE FILE OPERATIONS
# =============================================================================

def safe_file_operation(operation_func, *args, max_retries: int = 3, **kwargs) -> Any:
    """
    Perform file operation with retry logic and error handling.
    
    Args:
        operation_func: Function to execute
        *args: Arguments for the function
        max_retries (int): Maximum number of retry attempts
        **kwargs: Keyword arguments for the function
        
    Returns:
        Any: Function result or None if all attempts failed
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            result = operation_func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"File operation succeeded on attempt {attempt + 1}")
            return result
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"File operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
            else:
                logger.error(f"File operation failed after {max_retries + 1} attempts: {str(e)}")
    
    return None


def safe_write_file(file_path: str, content: Any, mode: str = 'w', encoding: str = 'utf-8') -> bool:
    """
    Safely write content to a file with error handling.
    
    Args:
        file_path (str): Path to file
        content: Content to write
        mode (str): File open mode
        encoding (str): File encoding
        
    Returns:
        bool: True if successful
    """
    def _write_operation():
        # Ensure directory exists
        ensure_directory(str(Path(file_path).parent))
        
        with open(file_path, mode, encoding=encoding) as f:
            if isinstance(content, (dict, list)):
                json.dump(content, f, indent=2, ensure_ascii=False)
            else:
                f.write(str(content))
        return True
    
    result = safe_file_operation(_write_operation)
    if result:
        logger.debug(f"Successfully wrote file: {file_path}")
    else:
        logger.error(f"Failed to write file: {file_path}")
    
    return bool(result)


def safe_read_file(file_path: str, mode: str = 'r', encoding: str = 'utf-8') -> Optional[Any]:
    """
    Safely read content from a file with error handling.
    
    Args:
        file_path (str): Path to file
        mode (str): File open mode
        encoding (str): File encoding
        
    Returns:
        Any: File content or None if failed
    """
    def _read_operation():
        with open(file_path, mode, encoding=encoding) as f:
            if file_path.lower().endswith('.json'):
                return json.load(f)
            else:
                return f.read()
    
    if not Path(file_path).exists():
        logger.warning(f"File does not exist: {file_path}")
        return None
    
    result = safe_file_operation(_read_operation)
    if result is not None:
        logger.debug(f"Successfully read file: {file_path}")
    else:
        logger.error(f"Failed to read file: {file_path}")
    
    return result


def safe_delete_file(file_path: str) -> bool:
    """
    Safely delete a file with error handling.
    
    Args:
        file_path (str): Path to file
        
    Returns:
        bool: True if successful or file doesn't exist
    """
    def _delete_operation():
        path = Path(file_path)
        if path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        return True
    
    result = safe_file_operation(_delete_operation)
    if result:
        logger.debug(f"Successfully deleted: {file_path}")
    else:
        logger.error(f"Failed to delete: {file_path}")
    
    return bool(result)

# =============================================================================
# FILE INFORMATION AND UTILITIES
# =============================================================================

def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive file information.
    
    Args:
        file_path (str): Path to file
        
    Returns:
        dict: File information
    """
    file_info = {
        'exists': False,
        'is_file': False,
        'is_directory': False,
        'size_bytes': 0,
        'size_mb': 0.0,
        'created': None,
        'modified': None,
        'extension': '',
        'name': '',
        'parent': ''
    }
    
    try:
        path = Path(file_path)
        
        if path.exists():
            file_info['exists'] = True
            file_info['is_file'] = path.is_file()
            file_info['is_directory'] = path.is_dir()
            file_info['name'] = path.name
            file_info['parent'] = str(path.parent)
            file_info['extension'] = path.suffix
            
            if file_info['is_file']:
                stat = path.stat()
                file_info['size_bytes'] = stat.st_size
                file_info['size_mb'] = stat.st_size / (1024 * 1024)
                file_info['created'] = time.ctime(stat.st_ctime)
                file_info['modified'] = time.ctime(stat.st_mtime)
            elif file_info['is_directory']:
                file_info['size_bytes'] = get_directory_size(file_path)
                file_info['size_mb'] = file_info['size_bytes'] / (1024 * 1024)
        
    except Exception as e:
        logger.warning(f"Could not get file info for {file_path}: {str(e)}")
    
    return file_info


def find_files_by_pattern(directory: str, pattern: str, recursive: bool = True) -> List[str]:
    """
    Find files matching a pattern in directory.
    
    Args:
        directory (str): Directory to search
        pattern (str): File pattern (glob style)
        recursive (bool): Whether to search recursively
        
    Returns:
        list: List of matching file paths
    """
    try:
        path = Path(directory)
        
        if not path.exists() or not path.is_dir():
            logger.warning(f"Directory does not exist: {directory}")
            return []
        
        if recursive:
            matching_files = list(path.rglob(pattern))
        else:
            matching_files = list(path.glob(pattern))
        
        # Convert to strings and filter files only
        file_paths = [str(f) for f in matching_files if f.is_file()]
        
        logger.debug(f"Found {len(file_paths)} files matching pattern '{pattern}' in {directory}")
        return file_paths
        
    except Exception as e:
        logger.error(f"Error finding files with pattern '{pattern}' in {directory}: {str(e)}")
        return []


def get_available_space(directory: str) -> Dict[str, Any]:
    """
    Get available disk space for a directory.
    
    Args:
        directory (str): Directory path
        
    Returns:
        dict: Space information in bytes, MB, and GB
    """
    space_info = {
        'total_bytes': 0,
        'used_bytes': 0,
        'free_bytes': 0,
        'total_gb': 0.0,
        'used_gb': 0.0,
        'free_gb': 0.0
    }
    
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(directory),
                ctypes.pointer(free_bytes),
                ctypes.pointer(total_bytes),
                None
            )
            space_info['free_bytes'] = free_bytes.value
            space_info['total_bytes'] = total_bytes.value
            space_info['used_bytes'] = total_bytes.value - free_bytes.value
        else:  # Unix-like
            stat = os.statvfs(directory)
            space_info['total_bytes'] = stat.f_frsize * stat.f_blocks
            space_info['free_bytes'] = stat.f_frsize * stat.f_available
            space_info['used_bytes'] = space_info['total_bytes'] - space_info['free_bytes']
        
        # Convert to GB
        space_info['total_gb'] = space_info['total_bytes'] / (1024**3)
        space_info['used_gb'] = space_info['used_bytes'] / (1024**3)
        space_info['free_gb'] = space_info['free_bytes'] / (1024**3)
        
    except Exception as e:
        logger.warning(f"Could not get disk space info for {directory}: {str(e)}")
    
    return space_info

# =============================================================================
# SPECIALIZED STREAMGANK FILE OPERATIONS
# =============================================================================

def cleanup_streamgank_temp_files() -> Dict[str, Any]:
    """
    Clean up StreamGank-specific temporary files.
    
    Returns:
        dict: Cleanup summary
    """
    patterns = [
        'streamgank_*',
        'video_script_*',
        'scroll_frames_*',
        'test_script_*',
        '*_frame_*.png',
        'temp_trailer_*',
        'highlight_*',
        'enhanced_poster_*'
    ]
    
    return cleanup_temp_files(patterns)


def ensure_streamgank_directories() -> Dict[str, bool]:
    """
    Ensure all required StreamGank directories exist.
    
    Returns:
        dict: Directory creation results
    """
    directories = [
        'clips',
        'covers',
        'videos',
        'scripts',
        'screenshots',
        'test_output',
        'temp_processing'
    ]
    
    results = {}
    for directory in directories:
        results[directory] = ensure_directory(directory)
    
    return results


def save_workflow_results(results: Dict[str, Any], output_file: str = None) -> bool:
    """
    Save workflow results to JSON file with error handling.
    
    Args:
        results (dict): Results dictionary
        output_file (str): Output file path, auto-generated if None
        
    Returns:
        bool: True if successful
    """
    if output_file is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = f"workflow_results_{timestamp}.json"
    
    # Add metadata
    results_with_metadata = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'results': results
    }
    
    return safe_write_file(output_file, results_with_metadata)


def load_workflow_results(input_file: str) -> Optional[Dict[str, Any]]:
    """
    Load workflow results from JSON file.
    
    Args:
        input_file (str): Input file path
        
    Returns:
        dict: Results dictionary or None if failed
    """
    data = safe_read_file(input_file)
    
    if isinstance(data, dict):
        # Return just the results if wrapped with metadata
        return data.get('results', data)
    
    return data