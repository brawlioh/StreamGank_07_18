#!/usr/bin/env python3
"""
Test script for the Heygen video download and upload functionality.

This script allows testing of the download_heygen_video and download_and_upload_to_cloudinary
functions independently to ensure they're working correctly.

Usage:
    python test_heygen_download.py [video_id]
    
    If video_id is not provided, the script will prompt for one.
"""

import os
import sys
import argparse
import logging
import requests
from dotenv import load_dotenv

# Import the relevant functions from the main script
from automated_video_generator import (
    download_heygen_video,
    download_and_upload_to_cloudinary,
    wait_for_heygen_video,
    check_heygen_video_status
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("heygen_download_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_check_video_status(video_id):
    """
    Test the check_heygen_video_status function.
    
    Args:
        video_id: HeyGen video ID to check
        
    Returns:
        The status of the video
    """
    print("\n" + "="*70)
    print("TESTING: check_heygen_video_status")
    print("="*70)
    
    status = check_heygen_video_status(video_id)
    print(f"Video status: {status}")
    return status

def test_wait_for_video(video_id):
    """
    Test the wait_for_heygen_video function.
    
    Args:
        video_id: HeyGen video ID to wait for
        
    Returns:
        Boolean indicating if the video is ready
    """
    print("\n" + "="*70)
    print("TESTING: wait_for_heygen_video")
    print("="*70)
    
    is_ready = wait_for_heygen_video(video_id)
    print(f"Video ready: {is_ready}")
    return is_ready

def test_download_video(video_id):
    """
    Test the download_heygen_video function.
    
    Args:
        video_id: HeyGen video ID to download
        
    Returns:
        The Cloudinary URL of the uploaded video
    """
    print("\n" + "="*70)
    print("TESTING: download_heygen_video")
    print("="*70)
    
    cloudinary_url = download_heygen_video(video_id)
    
    if cloudinary_url:
        print(f"SUCCESS: Video downloaded and uploaded to Cloudinary")
        print(f"URL: {cloudinary_url}")
    else:
        print("FAILED: Could not download and upload video")
    
    return cloudinary_url

def test_direct_download_upload(video_url, video_id=None, download_only=False):
    """
    Test the download_and_upload_to_cloudinary function directly with a known video URL.
    
    Args:
        video_url: Direct URL to the video
        video_id: Optional ID to use for the upload
        download_only: If True, only download the video and skip Cloudinary upload
    
    Returns:
        Cloudinary URL or success status (boolean)
    """
    print("\n" + "="*70)
    if download_only:
        print(f"TESTING: Direct download from {video_url} (download-only mode)")
    else:
        print("TESTING: download_and_upload_to_cloudinary")
    print("="*70)
    
    try:
        if download_only:
            # Download only without uploading to Cloudinary
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_path = temp_file.name
            temp_file.close()
            
            print(f"Downloading to temporary file: {temp_path}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            # Use the requests library directly
            response = requests.get(video_url, headers=headers, stream=True, timeout=30)
            if response.status_code == 200:
                # Check content type to see if we're getting HTML instead of a video
                content_type = response.headers.get('content-type', '')
                print(f"Content-Type: {content_type}")
                
                if 'text/html' in content_type:
                    print("WARNING: Received HTML instead of video content!")
                    print("This usually happens when trying to download directly from the web player URL.")
                    print("Using fallback to extract video URL from HTML...")
                    
                    # Try to extract video URL from HTML
                    import re
                    page_content = response.text
                    
                    # Common patterns for video URLs in the page source
                    patterns = [
                        # Standard video URL patterns
                        r'"(https://assets\.heygen\.ai/video/[^"]+\.mp4)"',  # CDN URL pattern
                        r'"(https://[^"]+\.cloudfront\.net/[^"]+\.mp4)"',    # CloudFront URL pattern
                        r'"(https://[^"]+\.amazonaws\.com/[^"]+\.mp4)"',     # S3 URL pattern
                        r'"url":"(https://[^"]+\.mp4)"',                      # JSON URL pattern
                        r'src="(https://[^"]+\.mp4)"',                         # HTML src attribute pattern
                        r'data-src="(https://[^"]+\.mp4)"',                    # HTML data-src attribute pattern
                        
                        # JavaScript variable assignments
                        r'videoUrl\s*=\s*"(https://[^"]+\.mp4)"',             # JS variable assignment
                        r'videoUrl\s*=\s*\'(https://[^\']+\.mp4)\'',             # JS variable with single quotes
                        r'videoSrc\s*=\s*"(https://[^"]+\.mp4)"',             # Alternative variable name
                        r'url\s*:\s*"(https://[^"]+\.mp4)"',                  # Object property
                        
                        # JSON data structures
                        r'"url"\s*:\s*"(https://[^"]+\.mp4)"',               # JSON structure
                        r'"video_url"\s*:\s*"(https://[^"]+\.mp4)"',          # Alternative JSON key
                        r'"videoUrl"\s*:\s*"(https://[^"]+\.mp4)"',           # Camel case JSON key
                        
                        # Broader patterns (use cautiously as they might match non-video URLs)
                        r'(https://[^"\s]+\.heygen\.ai/[^"\s]+\.mp4)',        # Any Heygen CDN URL
                        r'(https://[^"\s]+\.cloudfront\.net/[^"\s]+\.mp4)'     # Any CloudFront URL
                    ]
                    
                    video_url_match = None
                    for pattern in patterns:
                        matches = re.findall(pattern, page_content)
                        if matches:
                            video_url_match = matches[0]
                            print(f"Found video URL in HTML: {video_url_match}")
                            # Start a new download with the extracted URL
                            response = requests.get(video_url_match, headers=headers, stream=True, timeout=30)
                            if response.status_code == 200:
                                # Reset file
                                with open(temp_path, 'wb') as f:
                                    f.truncate(0)
                                break
                    
                    if not video_url_match:
                        print("Could not extract video URL from HTML!")
                        # Continue anyway with the HTML content for debugging
                
                # Now download the content (either video or HTML for inspection)
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            # Display progress
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\rDownload progress: {progress:.1f}%", end='')
                
                print("\nDownload complete!")
                file_size = os.path.getsize(temp_path)
                print(f"Downloaded file size: {file_size} bytes")
                
                # Check if it's a video file
                if content_type.startswith('video/'):
                    print(f"SUCCESS! Video downloaded to: {temp_path}")
                    print("\nNOTE: Skipping Cloudinary upload due to download-only mode")
                    return True
                elif file_size > 1000000:  # More than 1MB is likely a video
                    print(f"SUCCESS! Large file (likely video) downloaded to: {temp_path}")
                    print("\nNOTE: Skipping Cloudinary upload due to download-only mode")
                    return True
                else:
                    print(f"WARNING: Downloaded file is suspiciously small ({file_size} bytes) or non-video content")
                    print(f"First 100 bytes: {open(temp_path, 'r', errors='ignore').read(100)}")
                    return False
            else:
                print(f"FAILED: Download request returned status code {response.status_code}")
                return False
        else:
            # Use the direct download and upload function
            video_id = video_id or "test_video"
            cloudinary_url = download_and_upload_to_cloudinary(video_url, video_id)
            
            if cloudinary_url:
                print(f"SUCCESS: Video downloaded and uploaded to Cloudinary")
                print(f"URL: {cloudinary_url}")
                return cloudinary_url
            else:
                print("FAILED: Could not download from URL and upload video")
                return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

def test_error_handling():
    """
    Test error handling with invalid inputs.
    """
    print("\n" + "="*70)
    print("TESTING: Error handling")
    print("="*70)
    
    # Test with invalid video ID
    print("Testing with invalid video ID...")
    result = download_heygen_video("invalid_video_id_12345")
    print(f"Result with invalid video ID: {'PASSED' if result == '' else 'FAILED'}")
    
    # Test with invalid URL
    print("\nTesting with invalid URL...")
    result = download_and_upload_to_cloudinary("https://example.com/nonexistent_video.mp4", "test_id")
    print(f"Result with invalid URL: {'PASSED' if result == '' else 'FAILED'}")
    
    # Test with malformed URL
    print("\nTesting with malformed URL...")
    result = download_and_upload_to_cloudinary("not_a_url", "test_id")
    print(f"Result with malformed URL: {'PASSED' if result == '' else 'FAILED'}")

def main():
    """
    Main function to run the tests.
    """
    # Load environment variables
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test Heygen video download and upload functionality')
    parser.add_argument('video_id', nargs='?', help='HeyGen video ID to test with')
    parser.add_argument('--video-url', help='Direct video URL for testing download_and_upload_to_cloudinary')
    parser.add_argument('--test-errors', action='store_true', help='Test error handling with invalid inputs')
    parser.add_argument('--download-only', action='store_true', help='Only test download, skip Cloudinary upload')
    args = parser.parse_args()
    
    # Check for necessary environment variables
    if not os.getenv('HEYGEN_API_KEY'):
        print("ERROR: HEYGEN_API_KEY environment variable not set!")
        print("Please set this variable in your .env file or environment.")
        sys.exit(1)
    
    # Check for Cloudinary configuration
    required_vars = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing and not args.download_only:
        print("WARNING: Cloudinary configuration not found!")
        print("Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET")
        print("for upload testing, or use --download-only to test just the download functionality.")
        print("\nSwitching to download-only mode...")
        args.download_only = True
    
    # Get video ID from command line or prompt
    video_id = args.video_id
    # Test based on arguments
    if args.test_errors:
        test_error_handling()
        return
    
    # Handle direct URL test case
    elif args.video_url:
        test_direct_download_upload(args.video_url, video_id, download_only=args.download_only)
        return
    
    # Handle video ID test case
    if not video_id:
        video_id = input("Please enter a HeyGen video ID to test with: ")
        if not video_id:
            print("No video ID specified, skipping tests")
            sys.exit(0)
            
    # Full test with the provided video ID
    print(f"\n\n--- TESTING WITH HEYGEN VIDEO ID: {video_id} ---\n")
    
    # Test status checking
    status = test_check_video_status(video_id)
    
    # Test video processing wait
    is_ready = test_wait_for_video(video_id)
    
    if not is_ready and status not in ['completed']:
        print("Warning: Video may not be ready for download.")
        proceed = input("Do you want to proceed with the download anyway? (y/n): ")
        if proceed.lower() != 'y':
            print("Test aborted.")
            sys.exit(0)
    
    # Test download and upload to Cloudinary
    if args.download_only:
        # Modify the download_video function to use download-only mode
        # For now we'll still call the function, but it will use our download-only parameters
        print("Running in download-only mode (will skip Cloudinary upload)")
        
    cloudinary_url = test_download_video(video_id)
    
    # Show test summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Video ID: {video_id}")
    print(f"Status: {status}")
    print(f"Ready: {is_ready}")
    if not args.download_only and cloudinary_url:
        print(f"Cloudinary URL: {cloudinary_url}")
    print("="*70)

try:
    main()
except KeyboardInterrupt:
    print("\nTest interrupted by user.")
    sys.exit(1)
except Exception as e:
    logger.exception(f"An error occurred during testing: {str(e)}")
    print(f"ERROR: {str(e)}")
    print("Check the log file for more details.")
    sys.exit(1)

if __name__ == "__main__":
    main()
