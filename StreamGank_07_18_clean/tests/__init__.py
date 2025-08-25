"""
StreamGank Modular Testing Framework

Comprehensive testing suite for the StreamGank video generation system.
Includes unit tests, integration tests, and mocking utilities.

Test Structure:
    - unit/: Individual module and function tests
    - integration/: End-to-end workflow tests  
    - mocks/: Mock objects and test data
    
Usage:
    # Run all tests
    python -m pytest streamgank_modular/tests/
    
    # Run specific test category
    python -m pytest streamgank_modular/tests/unit/
    python -m pytest streamgank_modular/tests/integration/
    
    # Run tests with coverage
    python -m pytest streamgank_modular/tests/ --cov=streamgank_modular
    
    # Run specific test module
    python -m pytest streamgank_modular/tests/unit/test_config.py
"""

import os
import sys
import logging
from pathlib import Path

# Add the streamgank_modular directory to Python path for imports
current_dir = Path(__file__).parent
modular_dir = current_dir.parent
project_root = modular_dir.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if str(modular_dir) not in sys.path:
    sys.path.insert(0, str(modular_dir))

# Configure test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_results.log')
    ]
)

# Test configuration
TEST_CONFIG = {
    'test_data_dir': current_dir / 'mocks' / 'test_data',
    'mock_apis': True,
    'verbose_logging': False,
    'cleanup_temp_files': True,
    'database_mock_enabled': True,
    'api_timeout': 30,
    'max_test_duration': 300  # 5 minutes max per test
}

def setup_test_environment():
    """Set up the testing environment with required configurations."""
    # Ensure test directories exist
    (TEST_CONFIG['test_data_dir']).mkdir(parents=True, exist_ok=True)
    
    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['MOCK_APIS'] = str(TEST_CONFIG['mock_apis']).lower()
    
    # Configure logging level for tests
    if TEST_CONFIG['verbose_logging']:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print(f"✅ Test environment configured")
    print(f"   Test data directory: {TEST_CONFIG['test_data_dir']}")
    print(f"   Mock APIs enabled: {TEST_CONFIG['mock_apis']}")


def teardown_test_environment():
    """Clean up after tests."""
    if TEST_CONFIG['cleanup_temp_files']:
        # Clean up any temporary test files
        import tempfile
        import shutil
        
        temp_patterns = ['streamgank_test_*', 'test_*']
        temp_dir = Path(tempfile.gettempdir())
        
        for pattern in temp_patterns:
            for file_path in temp_dir.glob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"⚠️ Could not clean up {file_path}: {e}")
    
    print("✅ Test environment cleaned up")


# Test utilities
def get_test_config(key: str, default=None):
    """Get test configuration value."""
    return TEST_CONFIG.get(key, default)


def is_mock_enabled() -> bool:
    """Check if API mocking is enabled."""
    return TEST_CONFIG.get('mock_apis', True)


def get_test_data_path(filename: str) -> Path:
    """Get path to test data file."""
    return TEST_CONFIG['test_data_dir'] / filename

# Automatically set up test environment when imported
setup_test_environment()