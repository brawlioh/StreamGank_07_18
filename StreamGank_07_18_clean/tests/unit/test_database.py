"""
Unit Tests for StreamGank Database Module

Tests database operations including connection management, movie extraction,
filtering, and data validation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from streamgank_modular.database.connection import (
    get_supabase_client,
    test_supabase_connection,
    validate_database_config,
    get_database_info,
    reset_connection,
    DatabaseConnection
)

from streamgank_modular.database.movie_extractor import (
    extract_movie_data,
    extract_movies_by_filters,
    get_movie_details,
    simulate_movie_data,
    get_movies_sample
)

from streamgank_modular.database.filters import (
    build_movie_query,
    apply_filters,
    apply_content_filters,
    apply_localization_filters,
    apply_genre_filters,
    apply_quality_filters,
    apply_date_filters,
    validate_filter_values
)

from streamgank_modular.database.validators import (
    validate_extraction_params,
    validate_movie_response,
    validate_movie_record,
    process_movie_data,
    process_single_movie,
    format_imdb_display,
    format_runtime_display
)


class TestDatabaseConnection:
    """Test database connection management."""
    
    @patch('streamgank_modular.database.connection.create_client')
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test_key'})
    def test_get_supabase_client_success(self, mock_create_client):
        """Test successful Supabase client creation."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        client = get_supabase_client()
        assert client == mock_client
        mock_create_client.assert_called_once_with('https://test.supabase.co', 'test_key')
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_supabase_client_missing_config(self):
        """Test client creation with missing configuration."""
        client = get_supabase_client()
        assert client is None
    
    @patch('streamgank_modular.database.connection.get_supabase_client')
    def test_test_supabase_connection_success(self, mock_get_client):
        """Test successful database connection test."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{'movie_id': 1}]
        
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = test_supabase_connection()
        assert result is True
    
    @patch('streamgank_modular.database.connection.get_supabase_client')
    def test_test_supabase_connection_failure(self, mock_get_client):
        """Test database connection test failure."""
        mock_get_client.return_value = None
        
        result = test_supabase_connection()
        assert result is False
    
    @patch('streamgank_modular.database.connection.test_supabase_connection')
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test_key'})
    def test_validate_database_config_success(self, mock_test_connection):
        """Test database configuration validation success."""
        mock_test_connection.return_value = True
        
        result = validate_database_config()
        assert result['is_valid'] is True
        assert result['connection_test'] is True
        assert len(result['missing_vars']) == 0
    
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_database_config_missing_vars(self):
        """Test database configuration validation with missing variables."""
        result = validate_database_config()
        assert result['is_valid'] is False
        assert 'SUPABASE_URL' in result['missing_vars']
        assert 'SUPABASE_KEY' in result['missing_vars']
    
    @patch('streamgank_modular.database.connection.get_supabase_client')
    def test_get_database_info(self, mock_get_client):
        """Test database information retrieval."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{'movie_id': 1}, {'movie_id': 2}]
        
        mock_client.table.return_value.select.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        info = get_database_info()
        assert info['connected'] is True
        assert info['movies_count'] == 2
        assert 'movies' in info['tables_accessible']
    
    @patch('streamgank_modular.database.connection.test_supabase_connection')
    def test_reset_connection(self, mock_test_connection):
        """Test connection reset."""
        mock_test_connection.return_value = True
        
        result = reset_connection()
        assert result is True
    
    def test_database_connection_context_manager(self, mock_supabase_client):
        """Test DatabaseConnection context manager."""
        with patch('streamgank_modular.database.connection.get_supabase_client', return_value=mock_supabase_client):
            with patch('streamgank_modular.database.connection.test_supabase_connection', return_value=True):
                with DatabaseConnection() as db:
                    assert db.is_connected() is True
                    assert db.get_client() == mock_supabase_client


class TestMovieExtractor:
    """Test movie data extraction functionality."""
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_extract_movie_data_success(self, mock_db_connection, database_response_success, sample_movie_data):
        """Test successful movie data extraction."""
        # Setup mock database connection
        mock_db = MagicMock()
        mock_db.is_connected.return_value = True
        mock_client = MagicMock()
        mock_db.get_client.return_value = mock_client
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        # Setup mock query chain
        mock_query = MagicMock()
        mock_client.from_.return_value.select.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = database_response_success
        
        # Mock the query building and filtering functions
        with patch('streamgank_modular.database.movie_extractor.build_movie_query', return_value=mock_query):
            with patch('streamgank_modular.database.movie_extractor.apply_filters', return_value=mock_query):
                with patch('streamgank_modular.database.movie_extractor.validate_extraction_params', return_value={'is_valid': True}):
                    with patch('streamgank_modular.database.movie_extractor.validate_movie_response', return_value={'is_valid': True}):
                        with patch('streamgank_modular.database.movie_extractor.process_movie_data', return_value=sample_movie_data):
                            
                            result = extract_movie_data(3, 'US', 'Horror', 'Netflix', 'Film')
                            
                            assert result is not None
                            assert len(result) == 2  # Based on sample_movie_data
                            assert result[0]['title'] == 'Test Horror Movie'
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_extract_movie_data_connection_failure(self, mock_db_connection):
        """Test movie data extraction with connection failure."""
        mock_db = MagicMock()
        mock_db.is_connected.return_value = False
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        with patch('streamgank_modular.database.movie_extractor.validate_extraction_params', return_value={'is_valid': True}):
            result = extract_movie_data(3, 'US', 'Horror', 'Netflix', 'Film')
            assert result is None
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_extract_movie_data_validation_failure(self, mock_db_connection):
        """Test movie data extraction with parameter validation failure."""
        mock_db = MagicMock()
        mock_db.is_connected.return_value = True
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        with patch('streamgank_modular.database.movie_extractor.validate_extraction_params', 
                  return_value={'is_valid': False, 'errors': ['Invalid parameters']}):
            result = extract_movie_data(-1, 'INVALID', None, None, None)
            assert result is None
    
    def test_extract_movies_by_filters(self):
        """Test movie extraction using filters dictionary."""
        filters = {
            'num_movies': 3,
            'country': 'US',
            'genre': 'Horror',
            'platform': 'Netflix',
            'content_type': 'Film',
            'debug': True
        }
        
        with patch('streamgank_modular.database.movie_extractor.extract_movie_data') as mock_extract:
            mock_extract.return_value = [{'title': 'Test Movie'}]
            
            result = extract_movies_by_filters(filters)
            
            mock_extract.assert_called_once_with(
                num_movies=3,
                country='US',
                genre='Horror',
                platform='Netflix',
                content_type='Film',
                debug=True
            )
            assert result == [{'title': 'Test Movie'}]
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_get_movie_details(self, mock_db_connection, database_response_success):
        """Test getting details for a specific movie."""
        mock_db = MagicMock()
        mock_db.is_connected.return_value = True
        mock_client = MagicMock()
        mock_db.get_client.return_value = mock_client
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        # Setup mock query chain
        mock_query = MagicMock()
        mock_client.from_.return_value.select.return_value = mock_query
        mock_query.eq.return_value.execute.return_value = database_response_success
        
        with patch('streamgank_modular.database.movie_extractor.build_movie_query', return_value=mock_query):
            with patch('streamgank_modular.database.movie_extractor.process_movie_data', return_value=[{'title': 'Test Movie'}]):
                
                result = get_movie_details(123)
                
                assert result is not None
                assert result['title'] == 'Test Movie'
                mock_query.eq.assert_called_once_with('movie_id', 123)
    
    def test_simulate_movie_data(self):
        """Test movie data simulation."""
        result = simulate_movie_data(3, 'Horror')
        
        assert isinstance(result, list)
        assert len(result) == 3
        
        # Check structure of simulated data
        for movie in result:
            assert 'id' in movie
            assert 'title' in movie
            assert 'year' in movie
            assert 'imdb' in movie
            assert 'genres' in movie
    
    def test_simulate_movie_data_no_genre(self):
        """Test movie data simulation without genre preference."""
        result = simulate_movie_data(2)
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_get_movies_sample_success(self, mock_db_connection, database_response_success):
        """Test getting random movie sample."""
        mock_db = MagicMock()
        mock_db.is_connected.return_value = True
        mock_client = MagicMock()
        mock_db.get_client.return_value = mock_client
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        mock_query = MagicMock()
        mock_client.from_.return_value.select.return_value = mock_query
        mock_query.range.return_value.execute.return_value = database_response_success
        
        with patch('streamgank_modular.database.movie_extractor.build_movie_query', return_value=mock_query):
            with patch('streamgank_modular.database.movie_extractor.process_movie_data', return_value=[{'title': 'Sample Movie'}]):
                
                result = get_movies_sample(3)
                
                assert result is not None
                assert len(result) == 1
                assert result[0]['title'] == 'Sample Movie'
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_get_movies_sample_fallback(self, mock_db_connection):
        """Test getting movie sample with database fallback."""
        mock_db = MagicMock()
        mock_db.is_connected.return_value = False
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        result = get_movies_sample(2)
        
        # Should fall back to simulated data
        assert result is not None
        assert len(result) == 2


class TestDatabaseFilters:
    """Test database filtering functionality."""
    
    def test_build_movie_query(self, mock_supabase_client):
        """Test movie query building."""
        mock_table = MagicMock()
        mock_supabase_client.from_.return_value = mock_table
        
        query = build_movie_query(mock_supabase_client)
        
        mock_supabase_client.from_.assert_called_once_with('movies')
        mock_table.select.assert_called_once()
    
    def test_apply_filters(self):
        """Test applying filters to query."""
        mock_query = MagicMock()
        
        result = apply_filters(mock_query, 'Film', 'US', 'Netflix', 'Horror')
        
        # Should call eq method for each filter
        assert mock_query.eq.call_count == 4
        mock_query.eq.assert_any_call('content_type', 'Film')
        mock_query.eq.assert_any_call('movie_localizations.country_code', 'US')
        mock_query.eq.assert_any_call('movie_localizations.platform_name', 'Netflix')
        mock_query.eq.assert_any_call('movie_genres.genre', 'Horror')
    
    def test_apply_filters_partial(self):
        """Test applying partial filters."""
        mock_query = MagicMock()
        
        result = apply_filters(mock_query, 'Film', None, 'Netflix', None)
        
        # Should only call eq for non-None filters
        assert mock_query.eq.call_count == 2
        mock_query.eq.assert_any_call('content_type', 'Film')
        mock_query.eq.assert_any_call('movie_localizations.platform_name', 'Netflix')
    
    def test_apply_content_filters(self):
        """Test content type filtering."""
        mock_query = MagicMock()
        
        # Test with normalization
        result = apply_content_filters(mock_query, 'Movie')
        mock_query.eq.assert_called_once_with('content_type', 'Film')
        
        # Test with no filter
        mock_query.reset_mock()
        result = apply_content_filters(mock_query, None)
        mock_query.eq.assert_not_called()
    
    def test_apply_localization_filters(self):
        """Test localization filtering."""
        mock_query = MagicMock()
        
        result = apply_localization_filters(mock_query, 'US', 'Netflix')
        
        assert mock_query.eq.call_count == 2
        mock_query.eq.assert_any_call('movie_localizations.country_code', 'US')
        mock_query.eq.assert_any_call('movie_localizations.platform_name', 'Netflix')
    
    def test_apply_genre_filters(self):
        """Test genre filtering with normalization."""
        mock_query = MagicMock()
        
        # Test with normalization
        result = apply_genre_filters(mock_query, 'Sci-Fi')
        mock_query.eq.assert_called_once_with('movie_genres.genre', 'Science-Fiction')
        
        # Test without normalization
        mock_query.reset_mock()
        result = apply_genre_filters(mock_query, 'Horror')
        mock_query.eq.assert_called_once_with('movie_genres.genre', 'Horror')
    
    def test_apply_quality_filters(self):
        """Test quality-based filtering."""
        mock_query = MagicMock()
        
        result = apply_quality_filters(mock_query, min_imdb_score=7.0, min_votes=10000, max_runtime=180)
        
        mock_query.gte.assert_any_call('imdb_score', 7.0)
        mock_query.gte.assert_any_call('imdb_votes', 10000)
        mock_query.lte.assert_called_once_with('runtime', 180)
    
    def test_apply_date_filters(self):
        """Test date-based filtering."""
        mock_query = MagicMock()
        
        result = apply_date_filters(mock_query, min_year=2020, max_year=2023)
        
        mock_query.gte.assert_called_once_with('release_year', 2020)
        mock_query.lte.assert_called_once_with('release_year', 2023)
    
    def test_validate_filter_values(self):
        """Test filter value validation."""
        valid_filters = {
            'content_type': 'Film',
            'country': 'US',
            'platform': 'Netflix',
            'min_imdb_score': 7.5,
            'min_votes': 10000
        }
        
        result = validate_filter_values(valid_filters)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['corrected_filters']['min_imdb_score'] == 7.5
    
    def test_validate_filter_values_invalid(self):
        """Test filter value validation with invalid values."""
        invalid_filters = {
            'min_imdb_score': 15.0,  # Out of range
            'min_votes': -100,       # Negative
            'min_year': 'invalid'    # Not numeric
        }
        
        result = validate_filter_values(invalid_filters)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0


class TestDatabaseValidators:
    """Test database validation functionality."""
    
    def test_validate_extraction_params_valid(self):
        """Test extraction parameter validation with valid parameters."""
        result = validate_extraction_params(3, 'US', 'Horror', 'Netflix', 'Film')
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['corrected_params']['num_movies'] == 3
        assert result['corrected_params']['country'] == 'US'
    
    def test_validate_extraction_params_invalid(self):
        """Test extraction parameter validation with invalid parameters."""
        result = validate_extraction_params(-1, 123, '', None, None)
        
        assert result['is_valid'] is False
        assert 'num_movies must be positive' in result['errors']
        assert 'country must be a string' in result['errors']
    
    def test_validate_extraction_params_warnings(self):
        """Test extraction parameter validation with warnings."""
        result = validate_extraction_params(150, 'USA', 'Horror', 'Netflix', 'Film')
        
        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
        assert result['corrected_params']['num_movies'] == 100  # Should be capped
    
    def test_validate_movie_response_valid(self, database_response_success):
        """Test movie response validation with valid response."""
        result = validate_movie_response(database_response_success)
        
        assert result['is_valid'] is True
        assert result['data_count'] == 2
        assert result['valid_records'] > 0
    
    def test_validate_movie_response_empty(self, database_response_empty):
        """Test movie response validation with empty response."""
        result = validate_movie_response(database_response_empty)
        
        assert result['data_count'] == 0
        assert 'No movies found matching criteria' in result['warnings']
    
    def test_validate_movie_response_invalid(self, database_response_error):
        """Test movie response validation with invalid response."""
        result = validate_movie_response(database_response_error)
        
        assert result['is_valid'] is False
        assert 'Response missing data attribute' in result['errors']
    
    def test_validate_movie_record_valid(self):
        """Test individual movie record validation."""
        valid_record = {
            'movie_id': 123,
            'imdb_score': 8.5,
            'imdb_votes': 100000,
            'release_year': 2023,
            'content_type': 'Film',
            'movie_localizations': [{
                'title': 'Test Movie',
                'country_code': 'US',
                'platform_name': 'Netflix'
            }],
            'movie_genres': [{'genre': 'Horror'}]
        }
        
        result = validate_movie_record(valid_record)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_movie_record_missing_required(self):
        """Test movie record validation with missing required fields."""
        invalid_record = {
            'imdb_score': 8.5
            # Missing movie_id
        }
        
        result = validate_movie_record(invalid_record)
        
        assert result['is_valid'] is False
        assert 'movie_id' in result['missing_fields']
    
    def test_process_movie_data(self, sample_movie_data):
        """Test movie data processing."""
        result = process_movie_data(sample_movie_data)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check processed structure
        movie = result[0]
        assert 'id' in movie
        assert 'title' in movie
        assert 'imdb' in movie
        assert 'genres' in movie
    
    def test_process_single_movie(self):
        """Test single movie processing."""
        raw_movie = {
            'movie_id': 123,
            'imdb_score': 8.5,
            'imdb_votes': 100000,
            'runtime': 120,
            'release_year': 2023,
            'content_type': 'Film',
            'movie_localizations': [{
                'title': 'Test Movie',
                'country_code': 'US',
                'platform_name': 'Netflix',
                'poster_url': 'https://example.com/poster.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test'
            }],
            'movie_genres': [{'genre': 'Horror'}, {'genre': 'Thriller'}]
        }
        
        result = process_single_movie(raw_movie)
        
        assert result is not None
        assert result['id'] == 123
        assert result['title'] == 'Test Movie'
        assert result['imdb'] == '8.5/10 (100,000 votes)'
        assert result['runtime'] == '120 min'
        assert result['genres'] == ['Horror', 'Thriller']
    
    def test_process_single_movie_invalid(self):
        """Test single movie processing with invalid data."""
        invalid_movie = {
            'movie_id': 123
            # Missing required localization data
        }
        
        result = process_single_movie(invalid_movie)
        assert result is None
    
    def test_format_imdb_display(self):
        """Test IMDB display formatting."""
        assert format_imdb_display(8.5, 100000) == '8.5/10 (100,000 votes)'
        assert format_imdb_display(7.0, 50000) == '7.0/10 (50,000 votes)'
        assert format_imdb_display(None, None) == '0.0/10 (0 votes)'
        assert format_imdb_display('invalid', 'invalid') == '0.0/10 (0 votes)'
    
    def test_format_runtime_display(self):
        """Test runtime display formatting."""
        assert format_runtime_display(120) == '120 min'
        assert format_runtime_display(0) == 'Unknown'
        assert format_runtime_display(None) == 'Unknown'
        assert format_runtime_display('invalid') == 'Unknown'


class TestDatabaseIntegration:
    """Test integration between database modules."""
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_full_extraction_workflow(self, mock_db_connection, sample_movie_data):
        """Test complete movie extraction workflow."""
        # Setup mocks for full workflow
        mock_db = MagicMock()
        mock_db.is_connected.return_value = True
        mock_client = MagicMock()
        mock_db.get_client.return_value = mock_client
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.data = sample_movie_data
        
        mock_query = MagicMock()
        mock_client.from_.return_value.select.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = mock_response
        
        with patch('streamgank_modular.database.movie_extractor.build_movie_query', return_value=mock_query):
            with patch('streamgank_modular.database.movie_extractor.apply_filters', return_value=mock_query):
                
                result = extract_movie_data(3, 'US', 'Horror', 'Netflix', 'Film')
                
                # Verify workflow steps
                assert result is not None
                assert len(result) > 0
                
                # Verify query building and filtering were called
                mock_client.from_.assert_called_once_with('movies')
                mock_query.order.assert_called_once()
                mock_query.limit.assert_called_once()
    
    def test_filter_validator_integration(self):
        """Test integration between filters and validators."""
        # Test that filter validation passes for valid query parameters
        valid_filters = {
            'content_type': 'Film',
            'country': 'US',
            'genre': 'Horror',
            'platform': 'Netflix'
        }
        
        validation_result = validate_filter_values(valid_filters)
        assert validation_result['is_valid'] is True
        
        # Test parameter validation
        param_validation = validate_extraction_params(3, 'US', 'Horror', 'Netflix', 'Film')
        assert param_validation['is_valid'] is True
    
    def test_connection_extractor_integration(self):
        """Test integration between connection and extractor modules."""
        with patch('streamgank_modular.database.connection.test_supabase_connection', return_value=True):
            with patch('streamgank_modular.database.connection.get_supabase_client') as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client
                
                # Test that database info gathering works with extractor
                info = get_database_info()
                assert info['connected'] is True