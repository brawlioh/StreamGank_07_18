#!/usr/bin/env python3
"""
Cleanup script to organize the StreamGank project files and remove redundant code
"""

import os
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("cleanup")

# Project root directory
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))

# Create an archive directory for obsolete files
ARCHIVE_DIR = PROJECT_ROOT / "archive"
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# Files to move to archive (redundant or superseded files)
FILES_TO_ARCHIVE = [
    "automated_video_generator.py.bak",
    "create_creatomate_with_heygen.py",  # Superseded by create_sequential_composition.py
    "create_final_video.py",             # Superseded by create_sequential_composition.py
    "create_sequential_video.py",        # Superseded by create_sequential_composition.py
    "create_scroll_video.py",            # Not part of the main workflow
    "upload_heygen_videos_to_cloudinary.py",  # Superseded by upload_heygen_to_cloudinary.py
    "upload_videos_direct.py",           # Superseded by upload_heygen_to_cloudinary.py
    "upload_videos_to_cloudinary.py",    # Superseded by upload_heygen_to_cloudinary.py
]

# JSON response files that can be archived
JSON_FILES_TO_ARCHIVE = [
    "linear_video_response.json",
    "sequential_video_response.json",
    "sequential_composition_response.json",
]

def archive_files():
    """
    Move obsolete files to the archive directory
    """
    logger.info(f"Archiving obsolete files to {ARCHIVE_DIR}")
    
    for filename in FILES_TO_ARCHIVE:
        src_path = PROJECT_ROOT / filename
        if os.path.exists(src_path):
            dst_path = ARCHIVE_DIR / filename
            try:
                shutil.move(src_path, dst_path)
                logger.info(f"Moved {filename} to archive")
            except Exception as e:
                logger.error(f"Error moving {filename}: {str(e)}")
        else:
            logger.warning(f"File {filename} not found, skipping")
    
    # Archive JSON response files
    for filename in JSON_FILES_TO_ARCHIVE:
        src_path = PROJECT_ROOT / filename
        if os.path.exists(src_path):
            dst_path = ARCHIVE_DIR / filename
            try:
                shutil.move(src_path, dst_path)
                logger.info(f"Moved {filename} to archive")
            except Exception as e:
                logger.error(f"Error moving {filename}: {str(e)}")
        else:
            logger.warning(f"File {filename} not found, skipping")

def create_directories():
    """
    Create organized directory structure for project files
    """
    # Create directories for different components
    dirs_to_create = [
        "heygen",           # For Heygen-related scripts
        "cloudinary",       # For Cloudinary upload scripts
        "creatomate",       # For Creatomate rendering scripts
        "utils",            # For utility scripts
        "responses",        # For API responses
        "archive"           # For archived files
    ]
    
    for dirname in dirs_to_create:
        dir_path = PROJECT_ROOT / dirname
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory {dirname}")

def main():
    """
    Main cleanup function
    """
    logger.info("Starting project cleanup")
    
    # Create organized directory structure
    create_directories()
    
    # Archive obsolete files
    archive_files()
    
    logger.info("Project cleanup complete")
    logger.info("Please refer to README.md for the main workflow files and usage instructions")

if __name__ == "__main__":
    main()
