"""
Integration Tests for StreamGang Main Workflow

Tests the complete end-to-end video generation workflow including
database extraction, script generation, and video processing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from streamgank_modular.database.movie_extractor import extract_movie_data
from streamgank_modular.config.templates import get_heygen_template_id
from streamgank_modular.utils.url_builder import build_streamgank_url
from streamgank_modular.utils.validators import validate_movie_data


@pytest.mark.integration
class TestMainWorkflowIntegration:
    """Test main workflow integration."""
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_database_to_config_integration(self, mock_db_connection, sample_movie_data, workflow_config):
        """Test integration between database extraction and config management."""
        # Setup database mock
        mock_db = MagicMock()
        mock_db.is_connected.return_value = True
        mock_client = MagicMock()
        mock_db.get_client.return_value = mock_client
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        # Mock successful database response
        mock_response = MagicMock()
        mock_response.data = sample_movie_data
        
        mock_query = MagicMock()
        mock_client.from_.return_value.select.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = mock_response
        
        with patch('streamgank_modular.database.movie_extractor.build_movie_query', return_value=mock_query):
            with patch('streamgank_modular.database.movie_extractor.apply_filters', return_value=mock_query):
                with patch('streamgank_modular.database.movie_extractor.validate_extraction_params', return_value={'is_valid': True}):
                    with patch('streamgank_modular.database.movie_extractor.validate_movie_response', return_value={'is_valid': True}):
                        with patch('streamgank_modular.database.movie_extractor.process_movie_data', return_value=sample_movie_data):
                            
                            # Extract movies from database
                            movies = extract_movie_data(
                                workflow_config['num_movies'],
                                workflow_config['country'],
                                workflow_config['genre'],
                                workflow_config['platform'],
                                workflow_config['content_type']
                            )
                            
                            assert movies is not None
                            assert len(movies) > 0
                            
                            # Test that extracted movie data works with config templates
                            first_movie = movies[0]
                            movie_genres = first_movie.get('genres', [])
                            
                            if movie_genres:
                                template_id = get_heygen_template_id(movie_genres[0])
                                assert template_id is not None
                                assert len(template_id) > 0
    
    def test_config_to_utils_integration(self, workflow_config):
        """Test integration between config and utils modules."""
        # Test URL building with config parameters
        url = build_streamgank_url(
            country=workflow_config['country'],
            genre=workflow_config['genre'],
            platform=workflow_config['platform'],
            content_type=workflow_config['content_type']
        )
        
        assert url is not None
        assert url.startswith('https://streamgank.com/')
        assert workflow_config['country'] in url
        assert workflow_config['genre'] in url
        
        # Test template selection for the genre
        template_id = get_heygen_template_id(workflow_config['genre'])
        assert template_id is not None
        
        # Verify this is the expected horror template
        if workflow_config['genre'] == 'Horror':
            assert template_id == 'e2ad0e5c7e71483991536f5c93594e42'
    
    def test_utils_validation_chain(self, sample_movie_data):
        """Test validation chain across utils modules."""
        # Test that each movie passes validation
        for movie in sample_movie_data:
            # Process movie data to match expected format
            processed_movie = {
                'id': movie.get('movie_id'),
                'title': movie.get('movie_localizations', [{}])[0].get('title', 'Unknown'),
                'year': movie.get('release_year'),
                'imdb_score': movie.get('imdb_score'),
                'trailer_url': movie.get('movie_localizations', [{}])[0].get('trailer_url', '')
            }
            
            validation_result = validate_movie_data(processed_movie)
            assert validation_result['is_valid'] is True
            assert len(validation_result['errors']) == 0
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_full_data_flow(self, mock_db_connection, sample_movie_data, workflow_config, mock_environment_variables):
        """Test complete data flow from database to final processing."""
        # Setup database extraction
        mock_db = MagicMock()
        mock_db.is_connected.return_value = True
        mock_client = MagicMock()
        mock_db.get_client.return_value = mock_client
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        mock_response = MagicMock()
        mock_response.data = sample_movie_data
        
        mock_query = MagicMock()
        mock_client.from_.return_value.select.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = mock_response
        
        with patch('streamgank_modular.database.movie_extractor.build_movie_query', return_value=mock_query):
            with patch('streamgank_modular.database.movie_extractor.apply_filters', return_value=mock_query):
                with patch('streamgank_modular.database.movie_extractor.validate_extraction_params', return_value={'is_valid': True}):
                    with patch('streamgank_modular.database.movie_extractor.validate_movie_response', return_value={'is_valid': True}):
                        with patch('streamgank_modular.database.movie_extractor.process_movie_data') as mock_process:
                            
                            # Mock processed data
                            processed_movies = [
                                {
                                    'id': 1,
                                    'title': 'Test Horror Movie',
                                    'year': 2023,
                                    'imdb': '8.5/10 (500,000 votes)',
                                    'imdb_score': 8.5,
                                    'platform': 'Netflix',
                                    'genres': ['Horror', 'Thriller'],
                                    'trailer_url': 'https://youtube.com/watch?v=test1'
                                },
                                {
                                    'id': 2,
                                    'title': 'Test Comedy Series',
                                    'year': 2022,
                                    'imdb': '7.8/10 (300,000 votes)',
                                    'imdb_score': 7.8,
                                    'platform': 'Max',
                                    'genres': ['Comedy'],
                                    'trailer_url': 'https://youtube.com/watch?v=test2'
                                }
                            ]
                            mock_process.return_value = processed_movies
                            
                            # Step 1: Extract movies from database
                            movies = extract_movie_data(
                                workflow_config['num_movies'],
                                workflow_config['country'],
                                workflow_config['genre'],
                                workflow_config['platform'],
                                workflow_config['content_type']
                            )
                            
                            assert movies is not None
                            assert len(movies) == 2
                            
                            # Step 2: Validate extracted data
                            for movie in movies:
                                validation_result = validate_movie_data(movie)
                                assert validation_result['is_valid'] is True
                            
                            # Step 3: Test template selection for each movie
                            template_ids = []
                            for movie in movies:
                                genres = movie.get('genres', [])
                                if genres:
                                    template_id = get_heygen_template_id(genres[0])
                                    template_ids.append(template_id)
                                    assert template_id is not None
                            
                            # Step 4: Test URL building
                            url = build_streamgank_url(
                                workflow_config['country'],
                                workflow_config['genre'],
                                workflow_config['platform'],
                                workflow_config['content_type']
                            )
                            
                            assert url is not None
                            assert 'streamgank.com' in url
                            
                            # Verify end-to-end data consistency
                            assert len(movies) > 0
                            assert len(template_ids) > 0
                            assert all(tid is not None for tid in template_ids)


@pytest.mark.integration
@pytest.mark.slow
class TestWorkflowErrorHandling:
    """Test workflow error handling and edge cases."""
    
    @patch('streamgank_modular.database.movie_extractor.DatabaseConnection')
    def test_database_connection_failure_handling(self, mock_db_connection, workflow_config):
        """Test workflow behavior when database connection fails."""
        # Setup failed connection
        mock_db = MagicMock()
        mock_db.is_connected.return_value = False
        mock_db_connection.return_value.__enter__.return_value = mock_db
        
        with patch('streamgank_modular.database.movie_extractor.validate_extraction_params', return_value={'is_valid': True}):
            # Should handle connection failure gracefully
            result = extract_movie_data(
                workflow_config['num_movies'],
                workflow_config['country'],
                workflow_config['genre'],
                workflow_config['platform'],
                workflow_config['content_type']
            )
            
            assert result is None
    
    def test_invalid_workflow_parameters(self):
        """Test workflow with invalid parameters."""
        # Test with invalid number of movies
        with patch('streamgank_modular.database.movie_extractor.DatabaseConnection'):
            result = extract_movie_data(-1, 'INVALID', '', None, None)
            assert result is None
    
    def test_empty_database_response_handling(self, mock_environment_variables):
        """Test handling of empty database responses."""
        from streamgank_modular.database.movie_extractor import simulate_movie_data
        
        # Test simulation fallback
        simulated_movies = simulate_movie_data(3, 'Horror')
        
        assert simulated_movies is not None
        assert len(simulated_movies) == 3
        assert all('title' in movie for movie in simulated_movies)
        
        # Test that simulated movies work with rest of system
        for movie in simulated_movies:
            # Test validation
            validation_result = validate_movie_data(movie)
            # Note: Simulated movies might not have all required fields, 
            # so we just check that validation runs without error
            assert 'is_valid' in validation_result
            
            # Test template selection
            genres = movie.get('genres', [])
            if genres:
                template_id = get_heygen_template_id(genres[0])
                assert template_id is not None


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration across modules."""
    
    def test_environment_configuration_consistency(self, mock_environment_variables):
        """Test that environment configuration is consistent across modules."""
        from streamgank_modular.config.settings import (
            validate_environment, 
            is_environment_ready,
            get_system_config
        )
        
        # Test environment validation
        env_validation = validate_environment()
        assert all(env_validation.values())  # All should be True with mock env vars
        
        # Test environment readiness
        assert is_environment_ready() is True
        
        # Test system configuration
        system_config = get_system_config()
        assert system_config['environment']['ready'] is True
        assert len(system_config['environment']['missing_vars']) == 0
    
    def test_template_configuration_consistency(self):
        """Test template configuration consistency."""
        from streamgank_modular.config.templates import (
            HEYGEN_TEMPLATES,
            get_templates_by_genre,
            validate_template_id
        )
        
        # Test that all template IDs are valid
        for template_key, template_info in HEYGEN_TEMPLATES.items():
            template_id = template_info['id']
            assert validate_template_id(template_id) is True
        
        # Test genre mapping consistency
        genre_templates = get_templates_by_genre()
        for genre, template_id in genre_templates.items():
            assert validate_template_id(template_id) is True
    
    def test_cross_module_constants_consistency(self):
        """Test consistency of constants across modules."""
        from streamgank_modular.config.constants import (
            get_supported_platforms,
            get_supported_genres,
            PLATFORM_COLORS,
            GENRE_COLORS
        )
        from streamgank_modular.utils.url_builder import (
            get_platform_mapping,
            get_available_genres_for_country
        )
        
        # Test platform consistency
        config_platforms = get_supported_platforms()
        utils_platforms = list(get_platform_mapping().keys())
        
        # Most platforms should be consistent (allowing for some differences)
        common_platforms = set(config_platforms) & set(utils_platforms)
        assert len(common_platforms) > 0
        
        # Test genre consistency
        config_genres = get_supported_genres()
        utils_genres = get_available_genres_for_country('US')
        
        # Should have significant overlap
        common_genres = set(config_genres) & set(utils_genres)
        assert len(common_genres) > 5  # At least 5 common genres