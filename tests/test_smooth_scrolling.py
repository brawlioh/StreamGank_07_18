#!/usr/bin/env python3
"""
Unit Test for 6-Second Ultra 60 FPS Scrolling Video Generation

This test allows you to test ONLY the ultra-smooth 60 FPS scrolling video functionality
without running the entire video generation workflow.

Usage:
    # Test with default settings (FR, Horror, Netflix, Series) - Always 60 FPS Ultra!
    python tests/test_smooth_scrolling.py
    
    # Test with custom parameters
    python tests/test_smooth_scrolling.py --country US --genre Action --platform "Prime Video" --content-type Film
    
    # Test different scroll distances (always 60 FPS)
    python tests/test_smooth_scrolling.py --scroll-distance 1.0  # Shorter scroll
    python tests/test_smooth_scrolling.py --no-smooth-scroll     # Test without micro-scrolling
"""

import os
import sys
import logging
import argparse
import time
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.append(str(Path(__file__).parent.parent))

from archive.create_scroll_video import create_scroll_video
from automated_video_generator import upload_video_to_cloudinary

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmoothScrollingTest:
    """Unit test class for smooth scrolling video generation"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_test(self, country="FR", genre="Horror", platform="Netflix", content_type="Film", 
                 smooth_scroll=True, scroll_distance=1.5, upload_to_cloudinary=True):
        """
        Run the smooth scrolling video generation test - ULTRA 60 FPS ONLY!
        
        Args:
            country: Country filter for StreamGank
            genre: Genre filter  
            platform: Platform filter
            content_type: Content type filter
            smooth_scroll: Enable micro-scrolling
            scroll_distance: Scroll distance multiplier
            upload_to_cloudinary: Upload result to Cloudinary
            
        Returns:
            dict: Test results with video path, duration, and metrics
        """
        logger.info("🧪 STARTING ULTRA 60 FPS SMOOTH SCROLLING VIDEO TEST")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        # Test parameters
        test_params = {
            'country': country,
            'genre': genre, 
            'platform': platform,
            'content_type': content_type,
            'smooth_scroll': smooth_scroll,
            'scroll_speed': 'ultra',  # Always ultra (60 FPS)
            'scroll_distance': scroll_distance,
            'target_duration': 6
        }
        
        logger.info("📋 TEST PARAMETERS:")
        for key, value in test_params.items():
            logger.info(f"   {key}: {value}")
        logger.info("")
         
        try:
            # Generate the test video
            logger.info("🎬 Generating 6-second smooth scrolling video...")
            
            video_path = create_scroll_video(
                country=country,
                genre=genre,
                platform=platform, 
                content_type=content_type,
                target_duration=6,
                output_video=None,  # Auto-generate unique filename
                smooth_scroll=smooth_scroll,
                scroll_distance=scroll_distance
            )
            
            if not video_path or not os.path.exists(video_path):
                raise Exception("Video generation failed - no output file created")
            
            # Analyze the generated video
            video_stats = self._analyze_video(video_path)
            
            # Upload to Cloudinary if requested
            cloudinary_url = None
            if upload_to_cloudinary:
                try:
                    logger.info("☁️ Uploading test video to Cloudinary...")
                    cloudinary_url = upload_video_to_cloudinary(video_path, "test_videos")
                    logger.info(f"✅ Uploaded to: {cloudinary_url}")
                except Exception as e:
                    logger.warning(f"⚠️ Cloudinary upload failed: {str(e)}")
            
            self.end_time = time.time()
            test_duration = self.end_time - self.start_time
            
            # Compile test results
            self.test_results = {
                'status': 'SUCCESS',
                'test_duration': test_duration,
                'video_path': video_path,
                'cloudinary_url': cloudinary_url,
                'video_stats': video_stats,
                'test_params': test_params,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self._print_test_results()
            return self.test_results
            
        except Exception as e:
            self.end_time = time.time()
            test_duration = self.end_time - self.start_time if self.start_time else 0
            
            self.test_results = {
                'status': 'FAILED',
                'error': str(e),
                'test_duration': test_duration,
                'test_params': test_params,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.error(f"❌ TEST FAILED: {str(e)}")
            self._print_test_results()
            return self.test_results
    
    def _analyze_video(self, video_path):
        """Analyze the generated video file"""
        import subprocess
        
        try:
            # Get video information using ffprobe
            cmd = [
                "ffprobe", "-v", "error", 
                "-show_entries", "format=duration,size:stream=width,height,r_frame_rate",
                "-of", "csv=p=0", video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            
            # Parse results
            format_line = lines[0].split(',')
            stream_line = lines[1].split(',') if len(lines) > 1 else ['', '', '']
            
            duration = float(format_line[0]) if format_line[0] else 0
            file_size = int(format_line[1]) if format_line[1] else 0
            width = int(stream_line[0]) if stream_line[0] else 0
            height = int(stream_line[1]) if stream_line[1] else 0
            frame_rate = stream_line[2] if len(stream_line) > 2 else ''
            
            stats = {
                'duration': duration,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'resolution': f"{width}x{height}",
                'frame_rate': frame_rate,
                'is_portrait': height > width,
                'duration_match': abs(duration - 6.0) < 0.1  # Within 0.1 seconds of target
            }
            
            logger.info("📊 VIDEO ANALYSIS:")
            logger.info(f"   Duration: {duration:.2f}s (target: 6.0s)")
            logger.info(f"   File size: {stats['file_size_mb']} MB")
            logger.info(f"   Resolution: {stats['resolution']}")
            logger.info(f"   Frame rate: {frame_rate}")
            logger.info(f"   Portrait format: {stats['is_portrait']}")
            logger.info(f"   Duration match: {'✅' if stats['duration_match'] else '❌'}")
            
            return stats
            
        except Exception as e:
            logger.warning(f"⚠️ Video analysis failed: {str(e)}")
            return {
                'duration': 0,
                'file_size_mb': 0,
                'resolution': 'unknown',
                'frame_rate': 'unknown',
                'is_portrait': False,
                'duration_match': False,
                'analysis_error': str(e)
            }
    
    def _print_test_results(self):
        """Print formatted test results"""
        logger.info("")
        logger.info("🏁 TEST RESULTS")
        logger.info("=" * 60)
        
        if self.test_results['status'] == 'SUCCESS':
            logger.info("✅ STATUS: SUCCESS")
            logger.info(f"⏱️  Test Duration: {self.test_results['test_duration']:.2f} seconds")
            logger.info(f"📁 Video File: {self.test_results['video_path']}")
            
            if self.test_results['cloudinary_url']:
                logger.info(f"☁️  Cloudinary URL: {self.test_results['cloudinary_url']}")
            
            stats = self.test_results['video_stats']
            logger.info(f"📊 Video Duration: {stats['duration']:.2f}s")
            logger.info(f"📏 Resolution: {stats['resolution']}")
            logger.info(f"📱 Portrait: {stats['is_portrait']}")
            logger.info(f"🎯 Duration Target Met: {'✅' if stats['duration_match'] else '❌'}")
            
        else:
            logger.error("❌ STATUS: FAILED")
            logger.error(f"💥 Error: {self.test_results['error']}")
            logger.error(f"⏱️  Test Duration: {self.test_results['test_duration']:.2f} seconds")
        
        logger.info("=" * 60)

def main():
    """Main test function with CLI arguments"""
    parser = argparse.ArgumentParser(description="Test 6-second smooth scrolling video generation")
    
    # StreamGank filters
    parser.add_argument("--country", default="FR", help="Country filter (default: FR)")
    parser.add_argument("--genre", default="Horror", help="Genre filter (default: Horror)")
    parser.add_argument("--platform", default="Netflix", help="Platform filter (default: Netflix)")
    parser.add_argument("--content-type", default="Series", help="Content type filter (default: Series)")
    
    # Scrolling settings
    parser.add_argument("--smooth-scroll", action="store_true", default=True, help="Enable micro-scrolling (default: True)")
    parser.add_argument("--no-smooth-scroll", action="store_false", dest="smooth_scroll", help="Disable micro-scrolling")
    parser.add_argument("--scroll-distance", type=float, default=1.5, help="Scroll distance multiplier (default: 1.5)")
    
    # Output options
    parser.add_argument("--no-upload", action="store_false", dest="upload_to_cloudinary", help="Skip Cloudinary upload")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the test
    test = SmoothScrollingTest()
    results = test.run_test(
        country=args.country,
        genre=args.genre,
        platform=args.platform,
        content_type=args.content_type,
        smooth_scroll=args.smooth_scroll,
        scroll_distance=args.scroll_distance,
        upload_to_cloudinary=args.upload_to_cloudinary
    )
    
    # Exit with appropriate code
    exit_code = 0 if results['status'] == 'SUCCESS' else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 