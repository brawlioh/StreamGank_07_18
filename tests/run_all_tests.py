#!/usr/bin/env python3
"""
StreamGank Test Runner

Run all unit tests or specific tests for the StreamGank video generation system.

Usage:
    # Run all tests
    python tests/run_all_tests.py
    
    # Run specific test
    python tests/run_all_tests.py --test smooth_scrolling
    
    # List available tests
    python tests/run_all_tests.py --list
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Test configurations
AVAILABLE_TESTS = {
    'smooth_scrolling': {
        'name': 'Smooth Scrolling Video Generation',
        'description': 'Test 6-second micro-scrolling video generation',
        'module': 'test_smooth_scrolling.py',
        'quick': True
    },
    'dynamic_clips': {
        'name': 'Dynamic Movie Clips',
        'description': 'Test dynamic movie trailer clip processing',
        'module': 'test_dynamic_clips.py',
        'quick': False
    },
    'portrait_conversion': {
        'name': 'Portrait Video Conversion',
        'description': 'Test video portrait conversion',
        'module': 'test_portrait_conversion.py',
        'quick': False
    },
    'video_quality': {
        'name': 'Video Quality Processing',
        'description': 'Test video quality processing',
        'module': 'test_video_quality.py',
        'quick': False
    }
}

class TestRunner:
    """Test runner for StreamGank unit tests"""
    
    def __init__(self):
        self.tests_dir = Path(__file__).parent
        self.project_root = self.tests_dir.parent
        self.results = {}
    
    def list_tests(self):
        """List all available tests"""
        print("📋 AVAILABLE TESTS")
        print("=" * 60)
        
        for test_id, config in AVAILABLE_TESTS.items():
            status = "✅ QUICK" if config['quick'] else "⏳ SLOW"
            print(f"{status} {test_id}")
            print(f"   Name: {config['name']}")
            print(f"   Description: {config['description']}")
            print(f"   Module: {config['module']}")
            print("")
    
    def run_test(self, test_id, verbose=False):
        """Run a specific test"""
        if test_id not in AVAILABLE_TESTS:
            print(f"❌ Test '{test_id}' not found")
            return False
        
        config = AVAILABLE_TESTS[test_id]
        test_file = self.tests_dir / config['module']
        
        if not test_file.exists():
            print(f"❌ Test file not found: {test_file}")
            return False
        
        print(f"🧪 Running test: {config['name']}")
        print(f"📄 Module: {config['module']}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Change to project root directory
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            # Run the test
            cmd = [sys.executable, str(test_file)]
            if verbose:
                cmd.append('--verbose')
            
            result = subprocess.run(cmd, capture_output=not verbose, text=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Store results
            self.results[test_id] = {
                'name': config['name'],
                'success': result.returncode == 0,
                'duration': duration,
                'output': result.stdout if result.stdout else '',
                'error': result.stderr if result.stderr else ''
            }
            
            if result.returncode == 0:
                print(f"✅ {config['name']} - PASSED ({duration:.2f}s)")
                return True
            else:
                print(f"❌ {config['name']} - FAILED ({duration:.2f}s)")
                if not verbose and result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 {config['name']} - ERROR: {str(e)}")
            self.results[test_id] = {
                'name': config['name'],
                'success': False,
                'duration': 0,
                'output': '',
                'error': str(e)
            }
            return False
        finally:
            os.chdir(original_cwd)
    
    def run_all_tests(self, quick_only=False, verbose=False):
        """Run all tests"""
        print("🚀 RUNNING ALL TESTS")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        start_time = time.time()
        
        for test_id, config in AVAILABLE_TESTS.items():
            if quick_only and not config['quick']:
                print(f"⏭️  Skipping slow test: {config['name']}")
                continue
            
            total_tests += 1
            if self.run_test(test_id, verbose):
                passed_tests += 1
            print("")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Print summary
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {(passed_tests/total_tests*100):.1f}%")
        print(f"Total duration: {total_duration:.2f}s")
        print("")
        
        # Detailed results
        for test_id, result in self.results.items():
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            print(f"{status} {result['name']} ({result['duration']:.2f}s)")
        
        return passed_tests == total_tests

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="StreamGank Test Runner")
    
    parser.add_argument("--test", help="Run specific test by ID")
    parser.add_argument("--list", action="store_true", help="List available tests")
    parser.add_argument("--quick", action="store_true", help="Run only quick tests")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.list:
        runner.list_tests()
        return
    
    if args.test:
        # Run specific test
        success = runner.run_test(args.test, args.verbose)
        sys.exit(0 if success else 1)
    else:
        # Run all tests
        success = runner.run_all_tests(args.quick, args.verbose)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 