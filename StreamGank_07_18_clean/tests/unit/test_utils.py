"""
Unit Tests for StreamGank Utils Module

Tests utility functions including URL builders, validators, formatters,
and file utilities.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Import modules to test
from streamgank_modular.utils.url_builder import (
    get_genre_mapping_by_country,
    get_platform_mapping,
    get_content_type_mapping,
    build_streamgank_url,
    get_available_genres_for_country,
    get_all_mappings_for_country,
    validate_genre,
    validate_platform,
    validate_content_type
)

from streamgank_modular.utils.validators import (
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

from streamgank_modular.utils.formatters import (
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

from streamgank_modular.utils.file_utils import (
    ensure_directory,
    is_directory_writable,
    get_temp_filename,
    safe_write_file,
    safe_read_file,
    safe_delete_file,
    get_file_info,
    find_files_by_pattern,
    cleanup_streamgank_temp_files
)


class TestURLBuilder:
    """Test URL building and mapping functionality."""
    
    def test_get_genre_mapping_by_country(self):
        """Test genre mapping retrieval (US-only simplified)."""
        mapping = get_genre_mapping_by_country('US')
        assert isinstance(mapping, dict)
        assert 'Horror' in mapping
        assert 'Comedy' in mapping
        assert 'Action & Adventure' in mapping
        
        # Test that country code is ignored (US-only workflow)
        fr_mapping = get_genre_mapping_by_country('FR')
        assert mapping == fr_mapping
    
    def test_get_platform_mapping(self):
        """Test platform mapping retrieval."""
        mapping = get_platform_mapping()
        assert isinstance(mapping, dict)
        assert 'Netflix' in mapping
        assert mapping['Netflix'] == 'netflix'
        assert mapping['Prime Video'] == 'amazon'
        assert mapping['Disney+'] == 'disney'
    
    def test_get_content_type_mapping(self):
        """Test content type mapping retrieval."""
        mapping = get_content_type_mapping()
        assert isinstance(mapping, dict)
        assert mapping['Film'] == 'Film'
        assert mapping['Movie'] == 'Film'
        assert mapping['Série'] == 'Serie'
        assert mapping['Series'] == 'Serie'
    
    def test_build_streamgank_url_full(self):
        """Test complete URL building with all parameters."""
        url = build_streamgank_url('US', 'Horror', 'Netflix', 'Film')
        
        assert url.startswith('https://streamgank.com/?')
        assert 'country=US' in url
        assert 'genres=Horror' in url
        assert 'platforms=netflix' in url
        assert 'type=Film' in url
    
    def test_build_streamgank_url_partial(self):
        """Test URL building with partial parameters."""
        # Only country and genre
        url = build_streamgank_url('FR', 'Comedy')
        assert 'country=FR' in url
        assert 'genres=Comedy' in url
        assert 'platforms=' not in url
        assert 'type=' not in url
    
    def test_build_streamgank_url_empty(self):
        """Test URL building with no parameters."""
        url = build_streamgank_url()
        assert url == 'https://streamgank.com/'
    
    def test_get_available_genres_for_country(self):
        """Test available genres retrieval."""
        genres = get_available_genres_for_country('US')
        assert isinstance(genres, list)
        assert 'Horror' in genres
        assert 'Comedy' in genres
        assert len(genres) > 10  # Should have many genres
    
    def test_get_all_mappings_for_country(self):
        """Test comprehensive mappings retrieval."""
        mappings = get_all_mappings_for_country('US')
        assert isinstance(mappings, dict)
        assert 'genres' in mappings
        assert 'platforms' in mappings
        assert 'content_types' in mappings
        
        # Verify structure
        assert isinstance(mappings['genres'], dict)
        assert isinstance(mappings['platforms'], dict)
        assert isinstance(mappings['content_types'], dict)
    
    def test_validate_genre(self):
        """Test genre validation."""
        assert validate_genre('Horror', 'US') is True
        assert validate_genre('Comedy', 'US') is True
        assert validate_genre('Unknown Genre', 'US') is False
        assert validate_genre('', 'US') is False
        assert validate_genre(None, 'US') is False
    
    def test_validate_platform(self):
        """Test platform validation."""
        assert validate_platform('Netflix', 'US') is True
        assert validate_platform('Prime Video', 'US') is True
        assert validate_platform('Unknown Platform', 'US') is False
        assert validate_platform('', 'US') is False
    
    def test_validate_content_type(self):
        """Test content type validation."""
        assert validate_content_type('Film') is True
        assert validate_content_type('Série') is True
        assert validate_content_type('Movie') is True
        assert validate_content_type('Unknown Type') is False


class TestValidators:
    """Test validation functionality."""
    
    def test_validate_movie_data_valid(self):
        """Test movie data validation with valid data."""
        valid_movie = {
            'id': 123,
            'title': 'Test Movie',
            'year': 2023,
            'trailer_url': 'https://youtube.com/watch?v=test',
            'imdb_score': 8.5
        }
        
        result = validate_movie_data(valid_movie)
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_movie_data_missing_required(self):
        """Test movie data validation with missing required fields."""
        invalid_movie = {
            'year': 2023  # Missing 'id' and 'title'
        }
        
        result = validate_movie_data(invalid_movie)
        assert result['is_valid'] is False
        assert 'title' in result['missing_fields']
        assert 'id' in result['missing_fields']
    
    def test_validate_movie_data_invalid_fields(self):
        """Test movie data validation with invalid field values."""
        invalid_movie = {
            'id': 123,
            'title': 'Test Movie',
            'year': 2050,  # Future year
            'trailer_url': 'not-a-url'
        }
        
        result = validate_movie_data(invalid_movie)
        # Should have warnings for unusual year and invalid URL
        assert len(result['warnings']) > 0
    
    def test_validate_movie_list_valid(self):
        """Test movie list validation with valid data."""
        valid_movies = [
            {'id': 1, 'title': 'Movie 1'},
            {'id': 2, 'title': 'Movie 2'}
        ]
        
        result = validate_movie_list(valid_movies)
        assert result['is_valid'] is True
        assert result['valid_count'] == 2
        assert result['total_count'] == 2
    
    def test_validate_movie_list_empty(self):
        """Test movie list validation with empty list."""
        result = validate_movie_list([])
        assert result['is_valid'] is False
        assert result['error'] == 'Movies list is empty'
    
    def test_validate_movie_list_not_list(self):
        """Test movie list validation with non-list input."""
        result = validate_movie_list("not a list")
        assert result['is_valid'] is False
        assert result['error'] == 'Movies data must be a list'
    
    def test_validate_script_data_valid(self):
        """Test script data validation with valid data."""
        valid_scripts = {
            'intro': {'text': 'Welcome to StreamGank!'},
            'movie_1': {'text': 'This horror movie will terrify you!'},
            'movie_2': 'Simple string script'
        }
        
        result = validate_script_data(valid_scripts)
        assert result['is_valid'] is True
        assert result['script_count'] == 3
    
    def test_validate_script_data_empty(self):
        """Test script data validation with empty data."""
        result = validate_script_data({})
        assert result['is_valid'] is False
        assert 'Script data is empty' in result['errors']
    
    def test_validate_script_data_missing_text(self):
        """Test script data validation with missing text."""
        invalid_scripts = {
            'intro': {'path': 'test.txt'},  # Missing 'text'
            'movie_1': {'text': ''}  # Empty text
        }
        
        result = validate_script_data(invalid_scripts)
        assert result['is_valid'] is False
        assert len(result['errors']) == 2
    
    def test_validate_api_response_valid(self):
        """Test API response validation with valid response."""
        valid_response = {
            'status': 'success',
            'data': {'video_id': '123'},
            'message': 'Video created'
        }
        
        result = validate_api_response(valid_response, ['status', 'data'])
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_api_response_missing_fields(self):
        """Test API response validation with missing expected fields."""
        invalid_response = {
            'status': 'success'
            # Missing 'data' field
        }
        
        result = validate_api_response(invalid_response, ['status', 'data'])
        assert result['is_valid'] is False
        assert 'data' in result['missing_fields']
    
    def test_is_valid_url(self):
        """Test URL validation."""
        assert is_valid_url('https://example.com') is True
        assert is_valid_url('http://test.org/path') is True
        assert is_valid_url('ftp://files.com') is True
        
        assert is_valid_url('not-a-url') is False
        assert is_valid_url('') is False
        assert is_valid_url(None) is False
    
    def test_is_valid_youtube_url(self):
        """Test YouTube URL validation."""
        valid_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://youtube.com/embed/dQw4w9WgXcQ'
        ]
        
        for url in valid_urls:
            assert is_valid_youtube_url(url) is True
        
        invalid_urls = [
            'https://vimeo.com/123456',
            'https://example.com/video',
            'not-a-url'
        ]
        
        for url in invalid_urls:
            assert is_valid_youtube_url(url) is False
    
    @patch.dict(os.environ, {'TEST_VAR': 'test_value'})
    def test_validate_environment_variables_valid(self):
        """Test environment variable validation with valid variables."""
        result = validate_environment_variables(['TEST_VAR'])
        assert result['is_valid'] is True
        assert 'TEST_VAR' in result['valid_vars']
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_variables_missing(self):
        """Test environment variable validation with missing variables."""
        result = validate_environment_variables(['MISSING_VAR'])
        assert result['is_valid'] is False
        assert 'MISSING_VAR' in result['missing_vars']


class TestFormatters:
    """Test text formatting functionality."""
    
    def test_sanitize_script_text(self):
        """Test script text sanitization."""
        dirty_text = '"This is a test" with \'quotes\' and extra   spaces!'
        clean_text = sanitize_script_text(dirty_text)
        
        assert '"' not in clean_text
        assert "'" not in clean_text
        assert '  ' not in clean_text  # No double spaces
        assert clean_text.endswith('!')
    
    def test_sanitize_script_text_empty(self):
        """Test script text sanitization with empty input."""
        assert sanitize_script_text('') == ''
        assert sanitize_script_text(None) == ''
        assert sanitize_script_text(123) == ''
    
    def test_format_hook_sentence(self):
        """Test hook sentence formatting."""
        long_text = 'This is a very long hook sentence with many words that should be truncated to meet the maximum word limit'
        formatted = format_hook_sentence(long_text, max_words=10)
        
        words = formatted.split()
        assert len(words) <= 10
        assert formatted.endswith('!')
    
    def test_format_intro_text(self):
        """Test intro text formatting."""
        long_intro = 'This is a very long introduction that should be truncated to meet the word limit for intro scripts'
        formatted = format_intro_text(long_intro, max_words=15)
        
        words = formatted.split()
        assert len(words) <= 15
        assert formatted.endswith('!')
    
    def test_format_movie_title(self):
        """Test movie title formatting."""
        # Normal title
        assert format_movie_title('Test Movie') == 'Test Movie'
        
        # Long title
        long_title = 'A' * 100
        formatted = format_movie_title(long_title, max_length=20)
        assert len(formatted) <= 20
        assert formatted.endswith('...')
        
        # Title with problematic characters
        problematic = 'Movie<>:"/\\|?*Title'
        cleaned = format_movie_title(problematic)
        assert '<' not in cleaned
        assert '>' not in cleaned
        assert ':' not in cleaned
    
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(90) == '1:30'
        assert format_duration(3665) == '1:01:05'
        assert format_duration(30) == '0:30'
        assert format_duration(-5) == '0:00'
        assert format_duration('invalid') == '0:00'
    
    def test_truncate_text(self):
        """Test text truncation."""
        long_text = 'This is a long text that needs truncation'
        truncated = truncate_text(long_text, 20, '...')
        
        assert len(truncated) == 20
        assert truncated.endswith('...')
    
    def test_clean_text_for_display(self):
        """Test text cleaning for display."""
        dirty_text = 'Text with\x00control\x1fcharacters\x7f'
        clean_text = clean_text_for_display(dirty_text)
        
        assert '\x00' not in clean_text
        assert '\x1f' not in clean_text
        assert '\x7f' not in clean_text
    
    def test_extract_words(self):
        """Test word extraction."""
        text = 'This is a test sentence with multiple words'
        words = extract_words(text, max_words=5)
        
        assert isinstance(words, list)
        assert len(words) <= 5
        assert words[0] == 'This'
    
    def test_count_words(self):
        """Test word counting."""
        assert count_words('One two three') == 3
        assert count_words('') == 0
        assert count_words('Single') == 1
        assert count_words(None) == 0
    
    def test_clean_filename(self):
        """Test filename cleaning."""
        dirty_filename = 'test<>:"/\\|?*file.txt'
        clean_filename_result = clean_filename(dirty_filename)
        
        problematic_chars = '<>:"/\\|?*'
        for char in problematic_chars:
            assert char not in clean_filename_result
    
    def test_generate_unique_filename(self):
        """Test unique filename generation."""
        filename = generate_unique_filename('test', 'txt', timestamp=True)
        
        assert filename.startswith('test_')
        assert filename.endswith('.txt')
        assert len(filename) > len('test.txt')  # Should include timestamp
    
    def test_format_genre_list(self):
        """Test genre list formatting."""
        genres = ['Horror', 'Thriller', 'Mystery']
        formatted = format_genre_list(genres, max_display=2)
        
        assert 'Horror' in formatted
        assert 'Thriller' in formatted
        assert '+1 more' in formatted
    
    def test_format_platform_name(self):
        """Test platform name formatting."""
        assert format_platform_name('netflix') == 'Netflix'
        assert format_platform_name('prime video') == 'Prime Video'
        assert format_platform_name('disney+') == 'Disney+'
        assert format_platform_name('unknown') == 'Unknown'
    
    def test_format_content_type(self):
        """Test content type formatting."""
        assert format_content_type('film') == 'Movie'
        assert format_content_type('série') == 'Series'
        assert format_content_type('tv show') == 'Series'
        assert format_content_type('unknown') == 'Unknown'


class TestFileUtils:
    """Test file utility functionality."""
    
    def test_ensure_directory(self, temp_directory):
        """Test directory creation."""
        test_dir = temp_directory / 'test_create'
        assert not test_dir.exists()
        
        result = ensure_directory(str(test_dir))
        assert result is True
        assert test_dir.exists()
    
    def test_ensure_directory_exists(self, temp_directory):
        """Test directory ensuring when directory already exists."""
        result = ensure_directory(str(temp_directory))
        assert result is True
    
    def test_is_directory_writable(self, temp_directory):
        """Test directory writability check."""
        result = is_directory_writable(str(temp_directory))
        assert result is True
    
    def test_is_directory_writable_nonexistent(self):
        """Test directory writability check for non-existent directory."""
        result = is_directory_writable('/nonexistent/directory')
        assert result is False
    
    def test_get_temp_filename(self):
        """Test temporary filename generation."""
        filename = get_temp_filename('test', 'suffix', 'txt')
        
        assert 'test_' in filename
        assert filename.endswith('suffix.txt')
        assert os.path.isabs(filename)  # Should be absolute path
    
    @patch('builtins.open', new_callable=mock_open)
    def test_safe_write_file(self, mock_file, temp_directory):
        """Test safe file writing."""
        test_file = temp_directory / 'test.txt'
        content = 'Test content'
        
        with patch('streamgank_modular.utils.file_utils.ensure_directory', return_value=True):
            result = safe_write_file(str(test_file), content)
            assert result is True
            mock_file.assert_called_once()
    
    @patch('builtins.open', new_callable=mock_open, read_data='Test content')
    def test_safe_read_file(self, mock_file, temp_directory):
        """Test safe file reading."""
        test_file = temp_directory / 'test.txt'
        
        with patch('pathlib.Path.exists', return_value=True):
            content = safe_read_file(str(test_file))
            assert content == 'Test content'
            mock_file.assert_called_once()
    
    def test_safe_read_file_nonexistent(self):
        """Test safe file reading with non-existent file."""
        content = safe_read_file('/nonexistent/file.txt')
        assert content is None
    
    @patch('pathlib.Path.unlink')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=True)
    def test_safe_delete_file(self, mock_is_file, mock_exists, mock_unlink):
        """Test safe file deletion."""
        result = safe_delete_file('/test/file.txt')
        assert result is True
        mock_unlink.assert_called_once()
    
    def test_get_file_info_nonexistent(self):
        """Test file info for non-existent file."""
        info = get_file_info('/nonexistent/file.txt')
        assert info['exists'] is False
        assert info['size_bytes'] == 0
    
    def test_find_files_by_pattern_nonexistent_dir(self):
        """Test finding files in non-existent directory."""
        files = find_files_by_pattern('/nonexistent/directory', '*.txt')
        assert files == []
    
    @patch('tempfile.gettempdir')
    @patch('pathlib.Path.glob')
    def test_cleanup_streamgank_temp_files(self, mock_glob, mock_gettempdir, temp_directory):
        """Test StreamGank temp file cleanup."""
        mock_gettempdir.return_value = str(temp_directory)
        
        # Mock some temp files
        mock_files = [
            temp_directory / 'streamgank_test_file.txt',
            temp_directory / 'video_script_123.json'
        ]
        
        for mock_file in mock_files:
            mock_file.touch()  # Create the files
        
        mock_glob.return_value = mock_files
        
        result = cleanup_streamgank_temp_files()
        assert isinstance(result, dict)
        assert 'files_deleted' in result
        assert 'bytes_freed' in result


class TestUtilsIntegration:
    """Test integration between utils modules."""
    
    def test_url_builder_validator_consistency(self):
        """Test consistency between URL builder and validators."""
        # Get supported genres from URL builder
        genres = get_available_genres_for_country('US')
        
        # Test that validator accepts these genres
        for genre in genres[:5]:  # Test first 5 genres
            assert validate_genre(genre, 'US') is True
    
    def test_formatter_validator_integration(self):
        """Test integration between formatters and validators."""
        # Test that formatter output passes validation
        test_movie = {
            'id': 123,
            'title': 'Test Movie',
            'year': 2023
        }
        
        formatted_title = format_movie_title(test_movie['title'])
        test_movie['title'] = formatted_title
        
        validation_result = validate_movie_data(test_movie)
        assert validation_result['is_valid'] is True
    
    def test_file_utils_formatter_integration(self):
        """Test integration between file utils and formatters."""
        # Test that formatted filenames are safe for file operations
        dirty_filename = 'test<>:"/\\|?*file'
        clean_name = clean_filename(dirty_filename)
        
        # Should be safe for file operations
        temp_filename = get_temp_filename(clean_name, '', 'txt')
        assert '<' not in temp_filename
        assert '>' not in temp_filename
        assert ':' not in temp_filename or temp_filename.count(':') == 1  # Allow drive letter on Windows