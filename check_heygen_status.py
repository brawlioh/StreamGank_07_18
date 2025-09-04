#!/usr/bin/env python3
"""
HeyGen Video Status Checker
===========================
Utility script to check HeyGen video status when timeouts occur.
This helps recover from HeyGen timeout situations by checking if videos are ready.

Usage:
    python check_heygen_status.py <video_id1> [video_id2] [video_id3]
    
Example:
    python check_heygen_status.py 4bc9df6a6c3a42eebabb59e1dc9cd739
"""

import sys
import os
import json
from ai.heygen_client import get_heygen_video_status

def check_video_status(video_id: str):
    """Check the status of a single HeyGen video."""
    print(f"\n🔍 Checking HeyGen video: {video_id}")
    print("-" * 50)
    
    try:
        status = get_heygen_video_status(video_id)
        
        if status['success']:
            print(f"✅ Status: {status.get('status', 'unknown')}")
            
            if status.get('video_url'):
                print(f"🎬 Video URL: {status['video_url']}")
                print("✅ Video is ready for use!")
            elif status.get('status') == 'processing':
                print("⏳ Video is still processing...")
                if 'progress' in status:
                    print(f"📊 Progress: {status['progress']}%")
            elif status.get('status') == 'failed':
                print("❌ Video processing failed")
                if 'error' in status:
                    print(f"💡 Error: {status['error']}")
            else:
                print("🔄 Video status unclear - may need more time")
                
        else:
            print(f"❌ Failed to check status: {status.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error checking video {video_id}: {e}")
    
    print("-" * 50)
    return status if 'status' in locals() else None

def main():
    """Main function to check multiple video IDs."""
    if len(sys.argv) < 2:
        print("❌ Error: Please provide at least one HeyGen video ID")
        print("\nUsage:")
        print("  python check_heygen_status.py <video_id1> [video_id2] [video_id3]")
        print("\nExample:")
        print("  python check_heygen_status.py 4bc9df6a6c3a42eebabb59e1dc9cd739")
        sys.exit(1)
    
    video_ids = sys.argv[1:]
    
    print(f"🎭 HeyGen Video Status Checker")
    print(f"📋 Checking {len(video_ids)} video(s)...")
    
    results = {}
    ready_videos = []
    processing_videos = []
    failed_videos = []
    
    for video_id in video_ids:
        result = check_video_status(video_id)
        if result:
            results[video_id] = result
            
            if result.get('success') and result.get('video_url'):
                ready_videos.append(video_id)
            elif result.get('status') == 'processing':
                processing_videos.append(video_id)
            elif result.get('status') == 'failed':
                failed_videos.append(video_id)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    if ready_videos:
        print(f"✅ Ready videos ({len(ready_videos)}):")
        for vid in ready_videos:
            print(f"   • {vid} - {results[vid].get('video_url', 'URL available')}")
    
    if processing_videos:
        print(f"⏳ Still processing ({len(processing_videos)}):")
        for vid in processing_videos:
            progress = results[vid].get('progress', 'unknown')
            print(f"   • {vid} - Progress: {progress}")
    
    if failed_videos:
        print(f"❌ Failed videos ({len(failed_videos)}):")
        for vid in failed_videos:
            error = results[vid].get('error', 'No error details')
            print(f"   • {vid} - {error}")
    
    # Recovery suggestions
    if ready_videos:
        print(f"\n💡 Recovery Options:")
        print(f"   1. Ready videos can be used immediately")
        print(f"   2. Update your job manually with the video URLs")
        print(f"   3. Or retry the job - it should use these completed videos")
    
    if processing_videos:
        print(f"\n⏳ For processing videos:")
        print(f"   1. Wait 10-15 more minutes and check again")
        print(f"   2. Run: python check_heygen_status.py {' '.join(processing_videos)}")
    
    if failed_videos:
        print(f"\n❌ For failed videos:")
        print(f"   1. Check your HeyGen account credits")
        print(f"   2. Retry the entire job with different parameters")
        print(f"   3. Contact HeyGen support if the issue persists")

if __name__ == "__main__":
    main()
