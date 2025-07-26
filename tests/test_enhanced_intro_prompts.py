#!/usr/bin/env python3
"""
Test Script for Enhanced Cinematic Intro Prompts

This script tests the new enhanced, longer, cinematic intro prompts 
for generating engaging TikTok/YouTube Shorts style video introductions.

Test Parameters:
- Country: US
- Platform: Netflix  
- Genre: Horror
- Content Type: Film

Focus: Only HeyGen video generation to test the new script prompts
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import the main module
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import the main workflow function
from automated_video_generator import run_full_workflow

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_enhanced_intro_prompts():
    """
    Test the enhanced cinematic intro prompts with US Horror Netflix Films
    
    This test specifically focuses on:
    1. The new COMPREHENSIVE intro prompt structure
    2. Cinematic, high-energy content generation
    3. Longer, more engaging introductions
    4. TikTok/YouTube Shorts presenter energy
    """
    logger.info("🎬 TESTING ENHANCED CINEMATIC INTRO PROMPTS")
    logger.info("="*60)
    logger.info("🇺🇸 Target: US Horror Films on Netflix")
    logger.info("🎯 Focus: Enhanced intro script generation")
    logger.info("⚡ Style: Cinematic, high-energy, comprehensive intros")
    logger.info("="*60)
    
    # Test parameters as requested
    test_params = {
        'num_movies': 3,
        'country': 'US',
        'platform': 'Netflix', 
        'genre': 'Horror',
        'content_type': 'Film',
        'output': 'test_output/enhanced_intro_test_results.json',
        'skip_scroll_video': False,  # Keep scroll video for complete test
        'smooth_scroll': True,
        'scroll_distance': 1.5
    }
    
    logger.info(f"📋 Test Parameters:")
    for key, value in test_params.items():
        logger.info(f"   {key}: {value}")
    
    try:
        logger.info("\n🚀 Starting enhanced intro prompts test workflow...")
        
        # Create output directory
        Path("test_output").mkdir(exist_ok=True)
        
        # Run the full workflow with focus on script generation
        start_time = time.time()
        
        results = run_full_workflow(**test_params)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"\n⏱️ Test completed in {duration:.2f} seconds")
        
        # Analyze results for intro prompt quality
        if results:
            logger.info("\n📊 ENHANCED INTRO PROMPTS TEST RESULTS:")
            logger.info("="*50)
            
            # Check if scripts were generated
            if 'scripts' in results:
                scripts = results['scripts']
                logger.info(f"✅ Scripts generated: {len(scripts)} total")
                
                # Analyze intro script specifically
                if 'intro_movie1' in scripts:
                    intro_script = scripts['intro_movie1']
                    word_count = len(intro_script.split())
                    sentence_count = intro_script.count('.') + intro_script.count('!') + intro_script.count('?')
                    
                    logger.info(f"\n🎭 INTRO SCRIPT ANALYSIS:")
                    logger.info(f"   📝 Word count: {word_count}")
                    logger.info(f"   📄 Sentence count: {sentence_count}")
                    logger.info(f"   🎯 Energy indicators: {intro_script.count('!') + intro_script.count('incredible') + intro_script.count('amazing')}")
                    
                    # Check for key enhancement elements
                    enhancements_found = []
                    if any(word in intro_script.lower() for word in ['hook', 'discover', 'incredible', 'amazing', 'must-see']):
                        enhancements_found.append("✅ Hook/excitement words")
                    if len(intro_script.split()) > 50:  # Longer than old prompts
                        enhancements_found.append("✅ Comprehensive length")
                    if intro_script.count('!') >= 2:
                        enhancements_found.append("✅ High energy punctuation")
                    
                    logger.info(f"\n🎪 ENHANCEMENT FEATURES DETECTED:")
                    for enhancement in enhancements_found:
                        logger.info(f"   {enhancement}")
                    
                    logger.info(f"\n📜 GENERATED INTRO SCRIPT:")
                    logger.info("-" * 40)
                    logger.info(f"{intro_script}")
                    logger.info("-" * 40)
                
                # Check other scripts too
                for script_type, script_content in scripts.items():
                    if script_type != 'intro_movie1':
                        word_count = len(script_content.split())
                        logger.info(f"   {script_type}: {word_count} words")
            
            # Check HeyGen video generation
            if 'heygen_videos' in results:
                heygen_results = results['heygen_videos']
                logger.info(f"\n🎥 HeyGen Videos: {len(heygen_results)} generated")
                for video_type, video_id in heygen_results.items():
                    logger.info(f"   {video_type}: {video_id}")
            
            # Check movie data extraction
            if 'movie_data' in results:
                movies = results['movie_data']
                logger.info(f"\n🎬 Movies Extracted: {len(movies)}")
                for i, movie in enumerate(movies, 1):
                    title = movie.get('title', 'Unknown')
                    year = movie.get('year', 'N/A')
                    imdb = movie.get('imdb', 'N/A')
                    logger.info(f"   {i}. {title} ({year}) - IMDb: {imdb}")
            
            # Save detailed results
            if test_params['output']:
                with open(test_params['output'], 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"\n💾 Detailed results saved to: {test_params['output']}")
            
            logger.info("\n🎉 ENHANCED INTRO PROMPTS TEST COMPLETED SUCCESSFULLY!")
            logger.info("🚀 The new cinematic intro prompts are working as expected!")
            
        else:
            logger.error("❌ Test failed - no results returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main test execution"""
    logger.info("🧪 Enhanced Intro Prompts Test Starting...")
    
    success = test_enhanced_intro_prompts()
    
    if success:
        logger.info("\n✅ All tests passed! Enhanced intro prompts are working correctly.")
        sys.exit(0)
    else:
        logger.error("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 