"""
Comprehensive Unit Tests for StreamGank Database Module

Tests all database operations including movie extraction, connection management,
filtering, and validation with the exact workflow parameters:
--country US --platform Netflix --genre Horror --content-type Film
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import database modules to test
from database.movie_extractor import (
    extract_movie_data,
    extract_movies_by_filters,
    get_movie_details,
    simulate_movie_data,
    get_movies_sample
)

from database.connection import (
    get_supabase_client,
    test_supabase_connection,
    validate_database_config,
    get_database_info,
    reset_connection,
    DatabaseConnection
)

from database.filters import (
    build_movie_query,
    apply_filters,
    apply_content_filters,
    apply_localization_filters,
    apply_genre_filters,
    apply_quality_filters,
    apply_date_filters,
    apply_availability_filters,
    validate_filter_values,
    get_popular_filter_combinations
)

from database.validators import (
    validate_extraction_params,
    validate_movie_response,
    validate_movie_record,
    validate_localization_record,
    process_movie_data,
    process_single_movie,
    format_imdb_display,
    format_runtime_display,
    extract_year_from_movie,
    extract_score_from_movie
)


class TestMovieExtractor:
    """Test movie data extraction functionality."""
    
    @patch('database.movie_extractor.get_supabase_client')
    def test_extract_movie_data_success(self, mock_client):
        """Test successful movie extraction with workflow parameters."""
        # Mock Supabase response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 1,
                'title': 'Godzilla Minus One',
                'year': 2023,
                'genres': ['Horror', 'Action'],
                'platform': 'Netflix',
                'imdb_score': 7.7,
                'imdb_votes': 150000,
                'poster_url': 'https://example.com/godzilla.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test1'
            },
            {
                'id': 2,
                'title': 'Train to Busan',
                'year': 2016,
                'genres': ['Horror', 'Thriller'],
                'platform': 'Netflix',
                'imdb_score': 7.6,
                'imdb_votes': 200000,
                'poster_url': 'https://example.com/train.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test2'
            },
            {
                'id': 3,
                'title': 'The Wailing',
                'year': 2016,
                'genres': ['Horror', 'Mystery'],
                'platform': 'Netflix',
                'imdb_score': 7.4,
                'imdb_votes': 120000,
                'poster_url': 'https://example.com/wailing.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test3'
            }
        ]
        
        mock_supabase = Mock()
        mock_supabase.table().select().eq().eq().contains().eq().gte().is_().not_().is_().order().limit().execute.return_value = mock_response
        mock_client.return_value = mock_supabase
        
        # Test extraction with exact workflow parameters
        result = extract_movie_data(
            num_movies=3,
            country="US",
            genre="Horror",
            platform="Netflix",
            content_type="Film"
        )
        
        # Validate results
        assert result is not None
        assert len(result) == 3
        assert result[0]['title'] == 'Godzilla Minus One'
        assert result[1]['title'] == 'Train to Busan'
        assert result[2]['title'] == 'The Wailing'
        
        # Validate all movies have horror genre
        for movie in result:
            assert 'Horror' in movie['genres']
            assert movie['platform'] == 'Netflix'
            
    @patch('database.movie_extractor.get_supabase_client')
    def test_extract_movie_data_no_connection(self, mock_client):
        """Test movie extraction when database connection fails."""
        mock_client.return_value = None
        
        result = extract_movie_data(num_movies=3, genre="Horror")
        
        assert result is None
        
    def test_simulate_movie_data(self):
        """Test movie data simulation for testing."""
        # Test horror genre simulation
        horror_movies = simulate_movie_data(num_movies=3, genre="Horror")
        
        assert len(horror_movies) == 3
        for movie in horror_movies:
            assert 'title' in movie
            assert 'genres' in movie
            assert 'Horror' in movie['genres']
            assert 'imdb_score' in movie
            assert isinstance(movie['imdb_score'], (int, float))
            
    @patch('database.movie_extractor.get_supabase_client')
    def test_get_movie_details(self, mock_client):
        """Test individual movie details retrieval."""
        mock_response = Mock()
        mock_response.data = [{
            'id': 1,
            'title': 'Test Movie',
            'overview': 'A test movie overview',
            'runtime': 120,
            'director': 'Test Director'
        }]
        
        mock_supabase = Mock()
        mock_supabase.table().select().eq().execute.return_value = mock_response
        mock_client.return_value = mock_supabase
        
        result = get_movie_details(movie_id=1)
        
        assert result is not None
        assert result['title'] == 'Test Movie'
        assert result['runtime'] == 120


class TestDatabaseConnection:
    """Test database connection management."""
    
    @patch.dict('os.environ', {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    })
    @patch('database.connection.create_client')
    def test_get_supabase_client_success(self, mock_create_client):
        """Test successful Supabase client creation."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        client = get_supabase_client()
        
        assert client is not None
        mock_create_client.assert_called_once()
        
    @patch.dict('os.environ', {}, clear=True)
    def test_get_supabase_client_no_env(self):
        """Test client creation without environment variables."""
        client = get_supabase_client()
        
        assert client is None
        
    @patch('database.connection.get_supabase_client')
    def test_test_supabase_connection_success(self, mock_client):
        """Test successful database connection test."""
        mock_response = Mock()
        mock_response.data = [{'count': 100}]
        
        mock_supabase = Mock()
        mock_supabase.table().select().limit().execute.return_value = mock_response
        mock_client.return_value = mock_supabase
        
        result = test_supabase_connection()
        
        assert result is True
        
    @patch('database.connection.get_supabase_client')
    def test_test_supabase_connection_failure(self, mock_client):
        """Test database connection failure."""
        mock_client.return_value = None
        
        result = test_supabase_connection()
        
        assert result is False
        
    @patch.dict('os.environ', {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    })
    def test_validate_database_config_valid(self):
        """Test database configuration validation."""
        result = validate_database_config()
        
        assert result['is_valid'] is True
        assert 'supabase_url' in result
        assert 'supabase_key' in result
        
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_database_config_invalid(self):
        """Test database configuration validation with missing vars."""
        result = validate_database_config()
        
        assert result['is_valid'] is False
        assert len(result['missing_vars']) > 0


class TestDatabaseFilters:
    """Test database filtering functionality."""
    
    def test_validate_filter_values_valid(self):
        """Test filter value validation with valid values."""
        valid_filters = {
            'country': 'US',
            'platform': 'Netflix',
            'genre': 'Horror',
            'content_type': 'Film'
        }
        
        result = validate_filter_values(valid_filters)
        
        assert result['country'] == 'US'
        assert result['platform'] == 'Netflix'
        assert result['genre'] == 'Horror'
        assert result['content_type'] == 'Film'
        
    def test_validate_filter_values_invalid(self):
        """Test filter value validation with invalid values."""
        invalid_filters = {
            'country': '',
            'platform': None,
            'genre': 'InvalidGenre'
        }
        
        result = validate_filter_values(invalid_filters)
        
        # Should clean up invalid values
        assert result.get('country') != ''
        assert 'platform' not in result or result['platform'] is not None
        
    @patch('database.filters.get_supabase_client')
    def test_build_movie_query(self, mock_client):
        """Test movie query building."""
        mock_supabase = Mock()
        mock_client.return_value = mock_supabase
        
        query = build_movie_query(mock_supabase)
        
        assert query is not None
        
    def test_get_popular_filter_combinations(self):
        """Test getting popular filter combinations."""
        combinations = get_popular_filter_combinations()
        
        assert isinstance(combinations, list)
        assert len(combinations) > 0
        
        # Check for our workflow combination
        horror_netflix_combo = None
        for combo in combinations:
            if combo.get('genre') == 'Horror' and combo.get('platform') == 'Netflix':
                horror_netflix_combo = combo
                break
                
        assert horror_netflix_combo is not None


class TestDatabaseValidators:
    """Test database validation functionality."""
    
    def test_validate_extraction_params_valid(self):
        """Test extraction parameter validation with valid params."""
        result = validate_extraction_params(
            num_movies=3,
            country="US",
            genre="Horror",
            platform="Netflix",
            content_type="Film"
        )
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        
    def test_validate_extraction_params_invalid(self):
        """Test extraction parameter validation with invalid params."""
        result = validate_extraction_params(
            num_movies=0,  # Invalid
            country="",    # Invalid
            genre=None     # Invalid
        )
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        
    def test_validate_movie_record_valid(self):
        """Test movie record validation with valid data."""
        valid_movie = {
            'id': 1,
            'title': 'Godzilla Minus One',
            'year': 2023,
            'genres': ['Horror', 'Action'],
            'imdb_score': 7.7,
            'poster_url': 'https://example.com/poster.jpg',
            'trailer_url': 'https://youtube.com/watch?v=test'
        }
        
        result = validate_movie_record(valid_movie)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        
    def test_validate_movie_record_invalid(self):
        """Test movie record validation with invalid data."""
        invalid_movie = {
            'id': None,      # Missing ID
            'title': '',     # Empty title
            'year': 'abc',   # Invalid year
            'genres': [],    # No genres
            'imdb_score': 15 # Invalid score
        }
        
        result = validate_movie_record(invalid_movie)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        
    def test_process_movie_data(self):
        """Test movie data processing."""
        raw_data = [
            {
                'id': 1,
                'title': 'Test Movie',
                'year': 2023,
                'genres': ['Horror'],
                'imdb_score': 7.5,
                'poster_url': 'https://test.com/poster.jpg'
            }
        ]
        
        result = process_movie_data(raw_data, debug=True)
        
        assert isinstance(result, list)
        assert len(result) <= len(raw_data)  # May filter out invalid records
        
    def test_format_imdb_display(self):
        """Test IMDB score display formatting."""
        result = format_imdb_display(7.7, 150000)
        
        assert '7.7' in result
        assert '150' in result  # Formatted vote count
        
    def test_format_runtime_display(self):
        """Test runtime display formatting."""
        result = format_runtime_display(120)  # 2 hours
        
        assert '2h' in result
        assert '0m' in result
        
    def test_extract_year_from_movie(self):
        """Test year extraction from movie data."""
        movie_with_year = {'year': 2023}
        movie_with_date = {'release_date': '2023-05-15'}
        movie_no_year = {'title': 'Test Movie'}
        
        assert extract_year_from_movie(movie_with_year) == 2023
        assert extract_year_from_movie(movie_with_date) == 2023
        assert extract_year_from_movie(movie_no_year) == 0
        
    def test_extract_score_from_movie(self):
        """Test score extraction from movie data."""
        movie_with_score = {'imdb_score': 7.7}
        movie_no_score = {'title': 'Test Movie'}
        
        assert extract_score_from_movie(movie_with_score) == 7.7
        assert extract_score_from_movie(movie_no_score) == 0.0


class TestWorkflowIntegration:
    """Test database integration with workflow parameters."""
    
    @patch('database.movie_extractor.extract_movie_data')
    def test_workflow_database_extraction(self, mock_extract):
        """Test complete database extraction workflow."""
        # Mock the exact response for workflow parameters
        mock_extract.return_value = [
            {
                'title': 'Godzilla Minus One',
                'year': 2023,
                'genres': ['Horror', 'Action'],
                'platform': 'Netflix',
                'imdb_score': 7.7
            },
            {
                'title': 'Train to Busan',
                'year': 2016,
                'genres': ['Horror', 'Thriller'],
                'platform': 'Netflix',
                'imdb_score': 7.6
            },
            {
                'title': 'The Wailing',
                'year': 2016,
                'genres': ['Horror', 'Mystery'],
                'platform': 'Netflix',
                'imdb_score': 7.4
            }
        ]
        
        # Test with exact workflow parameters
        movies = extract_movie_data(
            num_movies=3,
            country="US",
            genre="Horror",
            platform="Netflix",
            content_type="Film"
        )
        
        # Validate workflow requirements
        assert movies is not None
        assert len(movies) == 3
        
        # All movies should be horror
        for movie in movies:
            assert 'Horror' in movie['genres']
            
        # All movies should be on Netflix
        for movie in movies:
            assert movie['platform'] == 'Netflix'
            
        # Movies should be ordered by IMDB score (descending)
        scores = [movie['imdb_score'] for movie in movies]
        assert scores == sorted(scores, reverse=True)
        
        mock_extract.assert_called_once_with(
            num_movies=3,
            country="US",
            genre="Horror",
            platform="Netflix",
            content_type="Film"
        )
        
    def test_database_error_handling(self):
        """Test database error handling in workflow."""
        # Test with invalid parameters
        with pytest.raises(ValueError, match="num_movies must be positive"):
            validate_extraction_params(num_movies=-1)
            
        with pytest.raises(ValueError, match="country cannot be empty"):
            validate_extraction_params(num_movies=3, country="")