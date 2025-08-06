"""
StreamGank Modular Testing Runner

Main test runner for the StreamGank modular testing framework.
Provides convenient ways to run different test suites and generate reports.

Usage:
    # Run all tests
    python streamgank_modular/tests/run_tests.py
    
    # Run only unit tests
    python streamgank_modular/tests/run_tests.py --unit
    
    # Run only integration tests
    python streamgank_modular/tests/run_tests.py --integration
    
    # Run with coverage report
    python streamgank_modular/tests/run_tests.py --coverage
    
    # Run specific test module
    python streamgank_modular/tests/run_tests.py --module test_config
    
    # Run with verbose output
    python streamgank_modular/tests/run_tests.py --verbose
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# Import test framework
from tests import setup_test_environment, teardown_test_environment

def run_pytest_command(args_list):
    """
    Run pytest with given arguments and return results.
    
    Args:
        args_list (list): List of pytest arguments
        
    Returns:
        dict: Test results with return code and timing
    """
    start_time = time.time()
    
    try:
        # Run pytest as subprocess
        cmd = ['python', '-m', 'pytest'] + args_list
        print(f"🔧 Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        execution_time = time.time() - start_time
        
        return {
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'execution_time': execution_time,
            'success': result.returncode == 0
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            'return_code': -1,
            'stdout': '',
            'stderr': str(e),
            'execution_time': execution_time,
            'success': False
        }


def run_unit_tests(verbose=False, module=None):
    """
    Run unit tests.
    
    Args:
        verbose (bool): Enable verbose output
        module (str): Specific module to test
        
    Returns:
        dict: Test results
    """
    print("🧪 Running Unit Tests")
    print("=" * 50)
    
    args = ['streamgank_modular/tests/unit/', '-m', 'unit']
    
    if verbose:
        args.extend(['-v', '-s'])
    
    if module:
        # Find specific test module
        test_file = f"streamgank_modular/tests/unit/test_{module}.py"
        if Path(project_root / test_file).exists():
            args = [test_file] + args[1:]  # Replace directory with specific file
        else:
            print(f"⚠️ Test module {test_file} not found")
            return {'success': False, 'error': f'Module {module} not found'}
    
    return run_pytest_command(args)


def run_integration_tests(verbose=False):
    """
    Run integration tests.
    
    Args:
        verbose (bool): Enable verbose output
        
    Returns:
        dict: Test results
    """
    print("🔗 Running Integration Tests")
    print("=" * 50)
    
    args = ['streamgank_modular/tests/integration/', '-m', 'integration']
    
    if verbose:
        args.extend(['-v', '-s'])
    
    return run_pytest_command(args)


def run_all_tests(verbose=False, coverage=False):
    """
    Run all tests.
    
    Args:
        verbose (bool): Enable verbose output
        coverage (bool): Generate coverage report
        
    Returns:
        dict: Test results
    """
    print("🚀 Running All Tests")
    print("=" * 50)
    
    args = ['streamgank_modular/tests/']
    
    if verbose:
        args.extend(['-v', '-s'])
    
    if coverage:
        args.extend([
            '--cov=streamgank_modular',
            '--cov-report=html:htmlcov',
            '--cov-report=term-missing',
            '--cov-fail-under=80'  # Require 80% coverage
        ])
    
    return run_pytest_command(args)


def run_specific_tests(test_pattern, verbose=False):
    """
    Run tests matching a specific pattern.
    
    Args:
        test_pattern (str): Test pattern to match
        verbose (bool): Enable verbose output
        
    Returns:
        dict: Test results
    """
    print(f"🎯 Running Tests Matching: {test_pattern}")
    print("=" * 50)
    
    args = ['streamgank_modular/tests/', '-k', test_pattern]
    
    if verbose:
        args.extend(['-v', '-s'])
    
    return run_pytest_command(args)


def print_test_summary(results):
    """
    Print test execution summary.
    
    Args:
        results (dict): Test results from pytest
    """
    print("\n" + "=" * 60)
    print("📊 TEST EXECUTION SUMMARY")
    print("=" * 60)
    
    if results['success']:
        print("✅ Status: PASSED")
    else:
        print("❌ Status: FAILED")
    
    print(f"⏱️ Execution Time: {results['execution_time']:.2f} seconds")
    print(f"🔢 Return Code: {results['return_code']}")
    
    if results['stdout']:
        print("\n📄 Test Output:")
        print(results['stdout'])
    
    if results['stderr'] and not results['success']:
        print("\n❌ Error Output:")
        print(results['stderr'])


def check_test_dependencies():
    """
    Check if required testing dependencies are installed.
    
    Returns:
        bool: True if all dependencies are available
    """
    required_packages = ['pytest', 'pytest-cov', 'pytest-mock']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required testing packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(
        description="StreamGank Modular Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all tests
  %(prog)s --unit                   # Run only unit tests
  %(prog)s --integration           # Run only integration tests
  %(prog)s --coverage              # Run with coverage report
  %(prog)s --module config         # Run config module tests only
  %(prog)s --pattern "test_url"    # Run tests matching pattern
  %(prog)s --verbose              # Run with verbose output
        """
    )
    
    # Test selection arguments
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument('--unit', action='store_true', help='Run unit tests only')
    test_group.add_argument('--integration', action='store_true', help='Run integration tests only')
    test_group.add_argument('--all', action='store_true', help='Run all tests (default)')
    
    # Test specification arguments
    parser.add_argument('--module', type=str, help='Run specific test module (e.g., "config", "utils")')
    parser.add_argument('--pattern', type=str, help='Run tests matching pattern')
    
    # Output and reporting arguments
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose test output')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--no-cleanup', action='store_true', help='Skip test environment cleanup')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Default to all tests if no specific option chosen
    if not any([args.unit, args.integration, args.pattern, args.module]):
        args.all = True
    
    # Print header
    print("🧪 StreamGank Modular Testing Framework")
    print("=" * 60)
    print(f"📁 Project Root: {project_root}")
    print(f"🐍 Python Version: {sys.version.split()[0]}")
    print()
    
    # Check dependencies
    if not check_test_dependencies():
        return 1
    
    # Setup test environment
    try:
        setup_test_environment()
        print("✅ Test environment initialized")
        print()
    except Exception as e:
        print(f"❌ Failed to setup test environment: {e}")
        return 1
    
    # Run tests based on arguments
    try:
        if args.pattern:
            results = run_specific_tests(args.pattern, args.verbose)
        elif args.module:
            results = run_unit_tests(args.verbose, args.module)
        elif args.unit:
            results = run_unit_tests(args.verbose)
        elif args.integration:
            results = run_integration_tests(args.verbose)
        else:  # args.all or default
            results = run_all_tests(args.verbose, args.coverage)
        
        # Print summary
        print_test_summary(results)
        
        # Generate additional reports
        if args.coverage and results['success']:
            print("\n📊 Coverage report generated in htmlcov/index.html")
        
        return 0 if results['success'] else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return 1
    
    finally:
        # Cleanup test environment
        if not args.no_cleanup:
            try:
                teardown_test_environment()
            except Exception as e:
                print(f"⚠️ Test cleanup warning: {e}")


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)