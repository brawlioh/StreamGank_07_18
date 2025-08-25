#!/usr/bin/env python3
"""
Vizard Workflow Integration Script

This script loads local Vizard clips and injects them into the StreamGank workflow
as a replacement for dynamically generated clips. It integrates with the main workflow
by preparing the clip metadata in the format expected by the workflow system.

Usage:
    python3 integrate_vizard_workflow.py --clips-metadata vizard_clips_metadata.json --test-mode
"""

import os
import sys
import json
import argparse
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_clip_metadata(metadata_file: str) -> List[Dict[str, Any]]:
    """
    Load clip metadata from JSON file
    
    Args:
        metadata_file: Path to JSON metadata file
        
    Returns:
        List of clip metadata entries
    """
    try:
        if not os.path.isfile(metadata_file):
            logger.error(f"❌ Metadata file not found: {metadata_file}")
            return []
            
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            
        if not data or 'clips' not in data:
            logger.error(f"❌ Invalid metadata format in {metadata_file}")
            return []
            
        clips = data['clips']
        logger.info(f"✅ Loaded {len(clips)} clips from metadata file")
        return clips
        
    except Exception as e:
        logger.error(f"❌ Error loading clip metadata: {str(e)}")
        return []

def verify_clip_files(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Verify that clip files exist and have valid content
    
    Args:
        clips: List of clip metadata entries
        
    Returns:
        List of valid clip metadata entries
    """
    valid_clips = []
    
    for clip in clips:
        local_path = clip.get('local_path')
        if not local_path:
            logger.warning(f"⚠️ Clip missing local_path: {clip.get('name')}")
            continue
            
        # Check if file exists
        if not os.path.isfile(local_path):
            logger.warning(f"⚠️ Clip file not found: {local_path}")
            continue
            
        # Check if file has content (not empty)
        if os.path.getsize(local_path) == 0:
            logger.warning(f"⚠️ Clip file is empty: {local_path}")
            continue
            
        valid_clips.append(clip)
        
    logger.info(f"✅ Found {len(valid_clips)}/{len(clips)} valid clip files")
    return valid_clips

def prepare_workflow_data(clips: List[Dict[str, Any]], max_clips: int = 3) -> Dict[str, Any]:
    """
    Prepare data structure for workflow integration
    
    Args:
        clips: List of valid clip metadata entries
        max_clips: Maximum number of clips to use
        
    Returns:
        Dictionary with workflow integration data
    """
    # Limit to max_clips
    if len(clips) > max_clips:
        logger.info(f"ℹ️ Limiting to {max_clips} clips (out of {len(clips)} available)")
        clips = clips[:max_clips]
    
    # Create workflow data structure
    highlight_clips = []
    
    for clip in clips:
        highlight_clips.append({
            'local_path': clip.get('local_path'),
            'url': clip.get('url'),
            'name': clip.get('name', f"Vizard_Highlight_{clip.get('index', 0) + 1}"),
            'index': clip.get('index', 0)
        })
    
    workflow_data = {
        'highlight_clips': highlight_clips,
        'timestamp': int(time.time()),
        'clip_count': len(highlight_clips)
    }
    
    return workflow_data

def simulate_workflow_integration(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate workflow integration for test mode
    
    Args:
        workflow_data: Prepared workflow data
        
    Returns:
        Simulated workflow result data
    """
    highlight_clips = workflow_data.get('highlight_clips', [])
    
    # Simulate processing time
    logger.info("🔄 Simulating workflow integration...")
    time.sleep(1)
    
    # Create simulated dynamic clips structure
    dynamic_clips = {}
    for i, clip in enumerate(highlight_clips):
        movie_name = f"Test_Movie_{i+1}"
        dynamic_clips[movie_name] = clip.get('local_path')
    
    # Create workflow result structure
    result = {
        'final_movie_clips': [clip.get('local_path') for clip in highlight_clips],
        'dynamic_clips': dynamic_clips,
        'vizard_ai_clips': highlight_clips,
        'timestamp': int(time.time())
    }
    
    return result

def save_workflow_data(workflow_data: Dict[str, Any], output_file: str) -> bool:
    """
    Save workflow data to JSON file
    
    Args:
        workflow_data: Prepared workflow data
        output_file: Path to output JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(output_file, 'w') as f:
            json.dump(workflow_data, f, indent=2)
            
        logger.info(f"✅ Saved workflow data to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving workflow data: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Integrate Vizard clips into StreamGank workflow")
    parser.add_argument("--clips-metadata", default="vizard_clips_metadata.json", 
                        help="Path to clip metadata JSON file (default: vizard_clips_metadata.json)")
    parser.add_argument("--output", default="vizard_workflow_data.json",
                        help="Path to output workflow data file (default: vizard_workflow_data.json)")
    parser.add_argument("--max-clips", type=int, default=3,
                        help="Maximum number of clips to use (default: 3)")
    parser.add_argument("--test-mode", action="store_true",
                        help="Run in test mode (simulate workflow integration)")
    args = parser.parse_args()
    
    # Print banner
    print("\n" + "=" * 80)
    print("🎬 VIZARD WORKFLOW INTEGRATION")
    print("=" * 80)
    print(f"📋 Clip Metadata: {args.clips_metadata}")
    print(f"📄 Output File: {args.output}")
    print(f"🔢 Max Clips: {args.max_clips}")
    print(f"🧪 Test Mode: {'Yes' if args.test_mode else 'No'}")
    print("-" * 80 + "\n")
    
    # Load clip metadata
    clips = load_clip_metadata(args.clips_metadata)
    if not clips:
        print("❌ Failed to load clip metadata. Exiting.")
        return 1
    
    # Verify clip files
    valid_clips = verify_clip_files(clips)
    if not valid_clips:
        print("❌ No valid clip files found. Exiting.")
        return 1
    
    # Prepare workflow data
    workflow_data = prepare_workflow_data(valid_clips, args.max_clips)
    
    # Save workflow data
    if not save_workflow_data(workflow_data, args.output):
        print("❌ Failed to save workflow data. Exiting.")
        return 1
    
    # Test mode: simulate workflow integration
    if args.test_mode:
        result = simulate_workflow_integration(workflow_data)
        
        # Save test result
        test_output = f"vizard_test_result_{workflow_data['timestamp']}.json"
        with open(test_output, 'w') as f:
            json.dump(result, f, indent=2)
            
        print(f"✅ Saved test workflow result to {test_output}")
        
        # Print integration details
        print("\n" + "-" * 80)
        print("🧪 TEST WORKFLOW INTEGRATION SUMMARY")
        print("-" * 80)
        print(f"🎬 Clips processed: {len(workflow_data['highlight_clips'])}")
        print(f"📂 Clip paths:")
        for i, clip in enumerate(workflow_data['highlight_clips']):
            print(f"   {i+1}. {clip['local_path']}")
        print("-" * 80)
        print("✅ Test workflow integration completed successfully")
        print("You can now run the main workflow with:")
        print("python main.py --country US --platform Netflix --genre Action --content-type movie --use-vizard-ai --app-env test")
        print("-" * 80)
    
    print("\n✅ Workflow integration data prepared successfully")
    print(f"📋 {len(workflow_data['highlight_clips'])} clips ready for integration")
    print(f"📄 Workflow data saved to {args.output}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
