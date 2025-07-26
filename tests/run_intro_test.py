#!/usr/bin/env python3
"""
Quick Runner for Enhanced Intro Prompts Test

Usage:
    python tests/run_intro_test.py
    
This will test the new enhanced cinematic intro prompts with:
- Country: US
- Platform: Netflix
- Genre: Horror
- Content Type: Film
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the enhanced intro prompts test"""
    print("🎬 Enhanced Intro Prompts Test Runner")
    print("="*50)
    print("🇺🇸 Testing: US Horror Films on Netflix")
    print("⚡ Focus: Cinematic, high-energy intro generation")
    print("="*50)
    
    # Get the test script path
    test_script = Path(__file__).parent / "test_enhanced_intro_prompts.py"
    
    if not test_script.exists():
        print(f"❌ Test script not found: {test_script}")
        sys.exit(1)
    
    try:
        # Run the test
        print("\n🚀 Starting test...")
        result = subprocess.run([sys.executable, str(test_script)], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print("\n✅ Test completed successfully!")
        else:
            print(f"\n❌ Test failed with return code: {result.returncode}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Failed to run test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 