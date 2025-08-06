"""
Pytest Configuration and Fixtures

This file contains pytest configuration, fixtures, and shared test utilities
for the StreamGank modular testing framework.
"""

import pytest
import os
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Test logger
logger = logging.getLogger(__name__)

# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests for individual functions/classes")
    config.addinivalue_line("markers", "integration: Integration tests for workflows")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "database: Tests that require database connection")
    config.addinivalue_line("markers", "api: Tests that make external API calls")
    config.addinivalue_line("markers", "file_io: Tests that perform file operations")
    
    # Set test environment
    os.environ['TESTING'] = 'true'
    os.environ['PYTEST_RUNNING'] = 'true'


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests based on file location
        if 'unit' in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Auto-mark tests based on name patterns
        if 'database' in item.name.lower():
            item.add_marker(pytest.mark.database)
        if 'api' in item.name.lower():
            item.add_marker(pytest.mark.api)
        if 'slow' in item.name.lower():
            item.add_marker(pytest.mark.slow)

# =============================================================================
# FIXTURE SCOPES AND UTILITIES
# =============================================================================

@pytest.fixture(scope="session")
def test_session_config():
    """Session-wide test configuration."""
    return {
        'mock_apis': True,
        'cleanup_files': True,
        'verbose_logging': False,
        'timeout': 30,
        'max_retries': 3
    }


@pytest.fixture(scope="function")
def temp_directory():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory(prefix='streamgank_test_') as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="function")
def mock_logger():
    """Mock logger for testing logging calls."""
    return Mock(spec=logging.Logger)

# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for database tests."""
    mock_client = MagicMock()
    
    # Mock table method
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    
    # Mock query methods
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    
    return mock_client


@pytest.fixture
def sample_movie_data():
    """Sample movie data for testing."""
    return [
        {
            'movie_id': 1,
            'content_type': 'Film',
            'imdb_score': 8.5,
            'imdb_votes': 500000,
            'runtime': 120,
            'release_year': 2023,
            'movie_localizations': [{
                'title': 'Test Horror Movie',
                'country_code': 'US',
                'platform_name': 'Netflix',
                'poster_url': 'https://example.com/poster1.jpg',
                'cloudinary_poster_url': 'https://cloudinary.com/poster1.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test1',
                'streaming_url': 'https://netflix.com/title/12345'
            }],
            'movie_genres': [{'genre': 'Horror'}, {'genre': 'Thriller'}]
        },
        {
            'movie_id': 2,
            'content_type': 'Série',
            'imdb_score': 7.8,
            'imdb_votes': 300000,
            'runtime': 45,
            'release_year': 2022,
            'movie_localizations': [{
                'title': 'Test Comedy Series',
                'country_code': 'US',
                'platform_name': 'Max',
                'poster_url': 'https://example.com/poster2.jpg',
                'cloudinary_poster_url': 'https://cloudinary.com/poster2.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test2',
                'streaming_url': 'https://max.com/series/67890'
            }],
            'movie_genres': [{'genre': 'Comedy'}]
        }
    ]


@pytest.fixture
def database_response_success(sample_movie_data):
    """Mock successful database response."""
    mock_response = MagicMock()
    mock_response.data = sample_movie_data
    return mock_response


@pytest.fixture
def database_response_empty():
    """Mock empty database response."""
    mock_response = MagicMock()
    mock_response.data = []
    return mock_response


@pytest.fixture
def database_response_error():
    """Mock database response with error."""
    mock_response = MagicMock()
    del mock_response.data  # Remove data attribute to simulate error
    return mock_response

# =============================================================================
# API FIXTURES
# =============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for AI tests."""
    mock_client = MagicMock()
    
    # Mock chat completions response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test generated script content"
    
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_heygen_response():
    """Mock HeyGen API response."""
    return {
        'data': {
            'video_id': 'test_video_123',
            'status': 'processing'
        }
    }


@pytest.fixture
def mock_creatomate_response():
    """Mock Creatomate API response."""
    return {
        'id': 'render_456',
        'status': 'queued',
        'url': 'https://creatomate.com/render/456'
    }


@pytest.fixture
def mock_cloudinary_response():
    """Mock Cloudinary upload response."""
    return {
        'public_id': 'test_upload_789',
        'secure_url': 'https://res.cloudinary.com/test/image/upload/test_upload_789.jpg',
        'url': 'https://res.cloudinary.com/test/image/upload/test_upload_789.jpg'
    }

# =============================================================================
# FILE AND MEDIA FIXTURES
# =============================================================================

@pytest.fixture
def sample_script_data():
    """Sample script data for testing."""
    return {
        'intro': 'Welcome to StreamGank horror movies!',
        'movie_1': 'This terrifying film will haunt your dreams!',
        'movie_2': 'Experience pure psychological terror!',
        'movie_3': 'The ultimate horror experience awaits!',
        'combined_script': 'Welcome to StreamGank horror movies! This terrifying film will haunt your dreams! Experience pure psychological terror! The ultimate horror experience awaits!'
    }


@pytest.fixture
def sample_video_urls():
    """Sample video URLs for testing."""
    return {
        'intro': 'https://heygen.com/video/intro_123.mp4',
        'movie_1': 'https://heygen.com/video/movie1_456.mp4',
        'movie_2': 'https://heygen.com/video/movie2_789.mp4',
        'movie_3': 'https://heygen.com/video/movie3_012.mp4'
    }


@pytest.fixture
def sample_asset_urls():
    """Sample asset URLs for testing."""
    return {
        'movie_covers': [
            'https://cloudinary.com/poster1.jpg',
            'https://cloudinary.com/poster2.jpg',
            'https://cloudinary.com/poster3.jpg'
        ],
        'movie_clips': [
            'https://cloudinary.com/clip1.mp4',
            'https://cloudinary.com/clip2.mp4',
            'https://cloudinary.com/clip3.mp4'
        ],
        'scroll_video': 'https://cloudinary.com/scroll_video.mp4'
    }

# =============================================================================
# ENVIRONMENT AND CONFIG FIXTURES
# =============================================================================

@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing."""
    env_vars = {
        'OPENAI_API_KEY': 'test_openai_key',
        'HEYGEN_API_KEY': 'test_heygen_key',
        'CREATOMATE_API_KEY': 'test_creatomate_key',
        'CLOUDINARY_CLOUD_NAME': 'test_cloud',
        'CLOUDINARY_API_KEY': 'test_cloudinary_key',
        'CLOUDINARY_API_SECRET': 'test_cloudinary_secret',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_supabase_key'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def workflow_config():
    """Configuration for workflow testing."""
    return {
        'num_movies': 3,
        'country': 'US',
        'genre': 'Horror',
        'platform': 'Netflix',
        'content_type': 'Film',
        'skip_scroll_video': False,
        'smooth_scroll': True,
        'scroll_distance': 1.5,
        'poster_timing_mode': 'heygen_last3s',
        'heygen_template_id': 'e2ad0e5c7e71483991536f5c93594e42'
    }

# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture
def capture_logs():
    """Capture log messages during tests."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Clean up
    root_logger.removeHandler(handler)
    root_logger.setLevel(original_level)


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    mocks = {
        'open': patch('builtins.open'),
        'path_exists': patch('pathlib.Path.exists'),
        'path_mkdir': patch('pathlib.Path.mkdir'),
        'path_unlink': patch('pathlib.Path.unlink'),
        'shutil_rmtree': patch('shutil.rmtree')
    }
    
    with patch.multiple('builtins', **{k: v for k, v in mocks.items() if k != 'shutil_rmtree'}):
        with mocks['shutil_rmtree']:
            yield mocks


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global state or singletons here
    yield
    # Cleanup after test


# =============================================================================
# TEST DATA GENERATORS
# =============================================================================

def generate_test_movie(movie_id: int = 1, **overrides) -> Dict[str, Any]:
    """Generate test movie data with optional overrides."""
    base_movie = {
        'movie_id': movie_id,
        'content_type': 'Film',
        'imdb_score': 7.5,
        'imdb_votes': 100000,
        'runtime': 120,
        'release_year': 2023,
        'movie_localizations': [{
            'title': f'Test Movie {movie_id}',
            'country_code': 'US',
            'platform_name': 'Netflix',
            'poster_url': f'https://example.com/poster{movie_id}.jpg',
            'trailer_url': f'https://youtube.com/watch?v=test{movie_id}',
            'streaming_url': f'https://netflix.com/title/{12345 + movie_id}'
        }],
        'movie_genres': [{'genre': 'Drama'}]
    }
    
    # Apply overrides
    base_movie.update(overrides)
    return base_movie


def generate_test_movies(count: int = 3) -> List[Dict[str, Any]]:
    """Generate multiple test movies."""
    return [generate_test_movie(i + 1) for i in range(count)]