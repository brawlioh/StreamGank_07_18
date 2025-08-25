"""
Comprehensive Unit Tests for StreamGank Utils Module

Tests all utility functions including validators, URL builders, formatters,
file utilities, and workflow logging.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
from typing import Dict, List, Any

# Import utils modules to test
from utils.validators import (
    validate_movie_data,
    validate_movie_list,
    validate_script_data,
    validate_api_response,
    is_valid_url,
    is_valid_youtube_url,
    is_valid_genre,
    is_valid_platform,
    validate_environment_variables,
    validate_file_path
)

from utils.url_builder import (
    get_genre_mapping_by_country,
    get_available_genres_for_country,
    get_platform_mapping,
    get_platform_mapping_by_country,
    get_content_type_mapping,
    get_content_type_mapping_by_country,
    build_streamgank_url,
    get_all_mappings_for_country,
    validate_genre,
    validate_platform,
    validate_content_type,
    get_available_platforms_for_country,
    get_supported_countries
)

from utils.formatters import (
    sanitize_script_text,
    format_hook_sentence,
    format_intro_text,
    format_movie_title,
    format_duration,
    truncate_text,
    clean_text_for_display,
    extract_words,
    count_words,
    clean_filename,
    generate_unique_filename,
    format_genre_list,
    format_platform_name,
    format_content_type
)

from utils.file_utils import (
    ensure_directory,
    is_directory_writable,
    get_directory_size,
    get_temp_filename,
    create_temp_directory,
    cleanup_temp_files,
    safe_file_operation,
    safe_write_file,
    safe_read_file,
    safe_delete_file,
    get_file_info,
    find_files_by_pattern,
    get_available_space,
    cleanup_streamgank_temp_files,
    ensure_streamgank_directories,
    save_workflow_results,
    load_workflow_results
)

from utils.workflow_logger import (
    WorkflowLogger,
    StructuredFormatter,
    setup_workflow_logging
)


class TestValidators:
    """Test validation utility functions."""
    
    def test_validate_movie_data_valid(self):
        """Test movie data validation with valid data."""
        valid_movie = {
            'id': 1,
            'title': 'Godzilla Minus One',
            'year': 2023,
            'genres': ['Horror', 'Action'],
            'imdb_score': 7.7,
            'imdb_votes': 150000,
            'poster_url': 'https://example.com/poster.jpg',
            'trailer_url': 'https://youtube.com/watch?v=test'
        }
        
        result = validate_movie_data(valid_movie)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        
    def test_validate_movie_data_invalid(self):
        """Test movie data validation with invalid data."""
        invalid_movie = {
            'id': None,
            'title': '',
            'year': 'not_a_year',
            'genres': [],
            'imdb_score': 15  # Invalid score
        }
        
        result = validate_movie_data(invalid_movie)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        
    def test_validate_movie_list_valid(self):
        """Test movie list validation with valid list."""
        valid_movies = [
            {'title': 'Movie 1', 'year': 2023, 'genres': ['Horror']},
            {'title': 'Movie 2', 'year': 2022, 'genres': ['Action']},
            {'title': 'Movie 3', 'year': 2021, 'genres': ['Comedy']}
        ]
        
        result = validate_movie_list(valid_movies)
        
        assert result['is_valid'] is True
        assert result['valid_count'] == 3
        
    def test_validate_script_data_valid(self):
        """Test script data validation with valid scripts."""
        valid_scripts = {
            'movie1': 'Here are the top 3 horror movies! This first movie terrifies.',
            'movie2': 'This second movie will scare you completely.',
            'movie3': 'This third movie is absolutely frightening.'
        }
        
        result = validate_script_data(valid_scripts)
        
        assert result['is_valid'] is True
        assert result['script_count'] == 3
        
    def test_is_valid_url(self):
        """Test URL validation."""
        assert is_valid_url('https://example.com') is True
        assert is_valid_url('http://test.com/path') is True
        assert is_valid_url('not_a_url') is False
        assert is_valid_url('') is False
        
    def test_is_valid_youtube_url(self):
        """Test YouTube URL validation."""
        assert is_valid_youtube_url('https://youtube.com/watch?v=test123') is True
        assert is_valid_youtube_url('https://youtu.be/test123') is True
        assert is_valid_youtube_url('https://www.youtube.com/embed/test123') is True
        assert is_valid_youtube_url('https://example.com') is False
        
    def test_is_valid_genre(self):
        """Test genre validation."""
        supported_genres = ['Horror', 'Comedy', 'Action', 'Drama']
        
        assert is_valid_genre('Horror', supported_genres) is True
        assert is_valid_genre('Comedy', supported_genres) is True
        assert is_valid_genre('SciFi', supported_genres) is False
        assert is_valid_genre('', supported_genres) is False
        
    def test_is_valid_platform(self):
        """Test platform validation."""
        supported_platforms = ['Netflix', 'Amazon Prime', 'Disney+']
        
        assert is_valid_platform('Netflix', supported_platforms) is True
        assert is_valid_platform('Amazon Prime', supported_platforms) is True
        assert is_valid_platform('Hulu', supported_platforms) is False
        
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'test_key',
        'HEYGEN_API_KEY': 'test_key'
    })
    def test_validate_environment_variables_complete(self):
        """Test environment variable validation with all vars present."""
        required_vars = ['OPENAI_API_KEY', 'HEYGEN_API_KEY']
        
        result = validate_environment_variables(required_vars)
        
        assert result['is_valid'] is True
        assert len(result['missing_vars']) == 0
        
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_environment_variables_missing(self):
        """Test environment variable validation with missing vars."""
        required_vars = ['OPENAI_API_KEY', 'HEYGEN_API_KEY']
        
        result = validate_environment_variables(required_vars)
        
        assert result['is_valid'] is False
        assert len(result['missing_vars']) == 2
        
    def test_validate_file_path_valid(self):
        """Test file path validation."""
        with tempfile.NamedTemporaryFile() as tmp:
            result = validate_file_path(tmp.name, must_exist=True)
            assert result['is_valid'] is True
            
    def test_validate_file_path_invalid(self):
        """Test file path validation with non-existent file."""
        result = validate_file_path('/non/existent/path', must_exist=True)
        assert result['is_valid'] is False


class TestURLBuilder:
    """Test URL building and mapping functionality."""
    
    def test_get_genre_mapping_by_country_us(self):
        """Test genre mapping for US."""
        mapping = get_genre_mapping_by_country('US')
        
        assert isinstance(mapping, dict)
        assert 'Horror' in mapping
        assert 'Comedy' in mapping
        assert 'Action' in mapping
        
    def test_get_available_genres_for_country_us(self):
        """Test available genres for US."""
        genres = get_available_genres_for_country('US')
        
        assert isinstance(genres, list)
        assert 'Horror' in genres
        assert len(genres) > 0
        
    def test_get_platform_mapping(self):
        """Test platform mapping retrieval."""
        mapping = get_platform_mapping()
        
        assert isinstance(mapping, dict)
        assert 'Netflix' in mapping
        assert len(mapping) > 0
        
    def test_get_content_type_mapping(self):
        """Test content type mapping."""
        mapping = get_content_type_mapping()
        
        assert isinstance(mapping, dict)
        assert 'Film' in mapping or 'Movies' in mapping
        
    def test_build_streamgank_url_workflow_params(self):
        """Test URL building with workflow parameters."""
        url = build_streamgank_url(
            country='US',
            platform='Netflix',
            genre='Horror',
            content_type='Film'
        )
        
        assert isinstance(url, str)
        assert 'streamgank' in url.lower()
        assert len(url) > 0
        
    def test_validate_genre_us_horror(self):
        """Test genre validation for US Horror."""
        result = validate_genre('Horror', 'US')
        
        assert result is True
        
    def test_validate_platform_netflix(self):
        """Test platform validation for Netflix."""
        result = validate_platform('Netflix', 'US')
        
        assert result is True
        
    def test_validate_content_type_film(self):
        """Test content type validation for Film."""
        result = validate_content_type('Film')
        
        assert result is True
        
    def test_get_supported_countries(self):
        """Test getting supported countries."""
        countries = get_supported_countries()
        
        assert isinstance(countries, list)
        assert 'US' in countries
        

class TestFormatters:
    """Test text formatting utility functions."""
    
    def test_sanitize_script_text(self):
        """Test script text sanitization."""
        raw_text = '  "This is a script with quotes and extra spaces!"  '
        
        sanitized = sanitize_script_text(raw_text)
        
        assert sanitized.strip() == sanitized  # No leading/trailing spaces
        assert '"' not in sanitized  # Quotes removed
        assert len(sanitized) > 0
        
    def test_format_hook_sentence(self):
        """Test hook sentence formatting."""
        long_text = "This is a very long hook sentence that exceeds the maximum word count and should be truncated"
        
        formatted = format_hook_sentence(long_text, max_words=18)
        
        word_count = len(formatted.split())
        assert word_count <= 18
        
    def test_format_intro_text(self):
        """Test intro text formatting."""
        long_intro = "This is a very long intro text that needs to be formatted and truncated to meet the requirements"
        
        formatted = format_intro_text(long_intro, max_words=25)
        
        word_count = len(formatted.split())
        assert word_count <= 25
        
    def test_format_movie_title(self):
        """Test movie title formatting."""
        long_title = "This is an extremely long movie title that should be truncated"
        
        formatted = format_movie_title(long_title, max_length=50)
        
        assert len(formatted) <= 50
        
    def test_format_duration(self):
        """Test duration formatting."""
        # Test seconds
        assert "1m 30s" in format_duration(90)
        
        # Test hours
        duration_2h = format_duration(7200)  # 2 hours
        assert "2h 0m" in duration_2h
        
    def test_truncate_text(self):
        """Test text truncation."""
        long_text = "This is a long text that needs truncation"
        
        truncated = truncate_text(long_text, max_length=20)
        
        assert len(truncated) <= 23  # 20 + "..." = 23
        assert truncated.endswith("...") or len(long_text) <= 20
        
    def test_clean_text_for_display(self):
        """Test text cleaning for display."""
        dirty_text = "Text\\nwith\\ttabs and\\rreturns"
        
        clean = clean_text_for_display(dirty_text)
        
        assert "\\n" not in clean
        assert "\\t" not in clean
        assert "\\r" not in clean
        
    def test_extract_words(self):
        """Test word extraction."""
        text = "Here are the top 3 horror movies from StreamGank!"
        
        words = extract_words(text, max_words=5)
        
        assert len(words) <= 5
        assert isinstance(words, list)
        
    def test_count_words(self):
        """Test word counting."""
        text = "This is a test sentence"
        
        count = count_words(text)
        
        assert count == 5
        
    def test_clean_filename(self):
        """Test filename cleaning."""
        dirty_name = "my/file\\name:with*bad?chars"
        
        clean = clean_filename(dirty_name)
        
        assert "/" not in clean
        assert "\\" not in clean
        assert ":" not in clean
        assert "*" not in clean
        assert "?" not in clean
        
    def test_generate_unique_filename(self):
        """Test unique filename generation."""
        filename1 = generate_unique_filename("test", ".txt")
        filename2 = generate_unique_filename("test", ".txt")
        
        assert filename1 != filename2
        assert filename1.endswith(".txt")
        assert "test" in filename1
        
    def test_format_genre_list(self):
        """Test genre list formatting."""
        genres = ['Horror', 'Action', 'Thriller', 'Drama']
        
        formatted = format_genre_list(genres, max_display=2)
        
        assert 'Horror' in formatted
        assert 'Action' in formatted
        assert len(formatted.split(',')) <= 3  # 2 + "and X more"
        
    def test_format_platform_name(self):
        """Test platform name formatting."""
        assert format_platform_name('netflix') == 'Netflix'
        assert format_platform_name('AMAZON PRIME') == 'Amazon Prime'
        
    def test_format_content_type(self):
        """Test content type formatting."""
        assert format_content_type('movies') == 'Movies'
        assert format_content_type('FILMS') == 'Films'


class TestFileUtils:
    """Test file utility functions."""
    
    def test_ensure_directory(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = os.path.join(temp_dir, 'test_subdir')
            
            result = ensure_directory(test_dir)
            
            assert result is True
            assert os.path.exists(test_dir)
            
    def test_is_directory_writable(self):
        """Test directory write permission check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = is_directory_writable(temp_dir)
            
            assert result is True
            
    def test_get_temp_filename(self):
        """Test temporary filename generation."""
        filename = get_temp_filename("streamgank", "_test", ".txt")
        
        assert "streamgank" in filename
        assert "_test" in filename
        assert filename.endswith(".txt")
        
    def test_create_temp_directory(self):
        """Test temporary directory creation."""
        temp_dir = create_temp_directory("streamgank")
        
        try:
            assert temp_dir is not None
            assert os.path.exists(temp_dir)
            assert "streamgank" in os.path.basename(temp_dir)
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                
    @patch('os.listdir')
    @patch('os.remove')
    def test_cleanup_temp_files(self, mock_remove, mock_listdir):
        """Test temporary file cleanup."""
        mock_listdir.return_value = ['streamgank_temp1.txt', 'streamgank_temp2.txt', 'other_file.txt']
        
        result = cleanup_temp_files(['streamgank_*.txt'])
        
        assert result['files_found'] >= 0
        
    def test_safe_write_file(self):
        """Test safe file writing."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            result = safe_write_file(tmp_path, "Test content")
            
            assert result is True
            
            # Verify content
            with open(tmp_path, 'r') as f:
                content = f.read()
                assert content == "Test content"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    def test_safe_read_file(self):
        """Test safe file reading."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("Test content")
            tmp_path = tmp.name
            
        try:
            content = safe_read_file(tmp_path)
            
            assert content == "Test content"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    def test_safe_delete_file(self):
        """Test safe file deletion."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            
        # File should exist
        assert os.path.exists(tmp_path)
        
        # Delete it
        result = safe_delete_file(tmp_path)
        
        assert result is True
        assert not os.path.exists(tmp_path)
        
    def test_get_file_info(self):
        """Test file information retrieval."""
        with tempfile.NamedTemporaryFile() as tmp:
            info = get_file_info(tmp.name)
            
            assert 'exists' in info
            assert 'size' in info
            assert 'modified_time' in info
            assert info['exists'] is True
            
    def test_save_workflow_results(self):
        """Test workflow results saving."""
        results = {
            'workflow_id': 'test_workflow',
            'movies': ['Movie 1', 'Movie 2', 'Movie 3'],
            'scripts_generated': 3,
            'status': 'completed'
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            result = save_workflow_results(results, tmp_path)
            
            assert result is True
            assert os.path.exists(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    def test_load_workflow_results(self):
        """Test workflow results loading."""
        results = {
            'workflow_id': 'test_workflow',
            'status': 'completed'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            import json
            json.dump(results, tmp)
            tmp_path = tmp.name
            
        try:
            loaded_results = load_workflow_results(tmp_path)
            
            assert loaded_results is not None
            assert loaded_results['workflow_id'] == 'test_workflow'
            assert loaded_results['status'] == 'completed'
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestWorkflowLogger:
    """Test workflow logging functionality."""
    
    def test_workflow_logger_creation(self):
        """Test WorkflowLogger creation."""
        logger = WorkflowLogger("test_workflow", "test_job")
        
        assert logger.workflow_id == "test_workflow"
        assert logger.job_id == "test_job"
        assert hasattr(logger, 'logger')
        
    def test_setup_workflow_logging(self):
        """Test workflow logging setup."""
        logger = setup_workflow_logging("test_workflow", "test_job")
        
        assert isinstance(logger, WorkflowLogger)
        assert logger.workflow_id == "test_workflow"
        assert logger.job_id == "test_job"
        
    def test_workflow_logger_step_logging(self):
        """Test workflow step logging."""
        logger = WorkflowLogger("test_workflow")
        
        # Should not raise exceptions
        logger.workflow_start({'test': 'params'})
        logger.step_start(1, "test_step", "Testing step")
        logger.step_progress("Progress update", {'progress': 50})
        logger.step_complete(1, "test_step", {'result': 'success'})
        logger.workflow_complete({'final': 'results'})
        
    def test_structured_formatter(self):
        """Test structured log formatting."""
        formatter = StructuredFormatter()
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert isinstance(formatted, str)
        assert "Test message" in formatted


class TestWorkflowUtilsIntegration:
    """Test utils integration with workflow parameters."""
    
    def test_workflow_validation_chain(self):
        """Test complete validation chain for workflow."""
        # Test movie data validation
        movie_data = {
            'title': 'Godzilla Minus One',
            'year': 2023,
            'genres': ['Horror', 'Action'],
            'platform': 'Netflix',
            'imdb_score': 7.7
        }
        
        movie_validation = validate_movie_data(movie_data)
        assert movie_validation['is_valid'] is True
        
        # Test URL building
        url = build_streamgank_url(
            country='US',
            platform='Netflix',
            genre='Horror',
            content_type='Film'
        )
        assert isinstance(url, str)
        
        # Test script formatting
        script = "Here are the top 3 horror movies from StreamGank! This first movie terrifies audiences worldwide."
        formatted_script = format_hook_sentence(script, max_words=18)
        assert len(formatted_script.split()) <= 18
        
    def test_workflow_file_operations(self):
        """Test file operations for workflow."""
        # Test directory creation
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = os.path.join(temp_dir, 'videos')
            scripts_dir = os.path.join(temp_dir, 'scripts')
            
            assert ensure_directory(videos_dir) is True
            assert ensure_directory(scripts_dir) is True
            
            # Test script file writing
            script_content = "Here are the top 3 horror movies! This first movie is terrifying."
            script_path = os.path.join(scripts_dir, 'movie1_script.txt')
            
            assert safe_write_file(script_path, script_content) is True
            
            # Test script file reading
            read_content = safe_read_file(script_path)
            assert read_content == script_content