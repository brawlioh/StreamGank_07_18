"""
Comprehensive Unit Tests for StreamGang Config Module

Tests all configuration management including settings, templates, constants,
and strict mode functionality with workflow parameters.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import config modules to test
from config.settings import (
    get_api_config,
    validate_environment,
    get_missing_env_vars,
    is_environment_ready,
    get_system_config
)

from config.templates import (
    get_heygen_template_id,
    get_template_info,
    list_available_templates,
    get_templates_by_genre,
    validate_template_id,
    get_template_for_content
)

from config.constants import (
    get_platform_colors,
    get_genre_colors,
    get_thematic_colors,
    normalize_content_type,
    get_country_info,
    is_supported_country,
    get_supported_platforms,
    get_supported_genres
)

from config.strict_mode import (
    StrictModeConfig,
    is_strict_mode_enabled,
    get_strict_config,
    update_strict_config,
    validate_strict_requirements,
    enforce_exact_count,
    enforce_api_availability,
    enforce_url_accessibility,
    enforce_minimum_quality,
    StrictModeError,
    StrictModeValidationError,
    strict_mode_required,
    log_strict_mode_status
)


class TestSettings:
    """Test configuration settings functionality."""
    
    def test_get_api_config_openai(self):
        """Test OpenAI API configuration retrieval."""
        config = get_api_config('openai')
        
        assert isinstance(config, dict)
        # Should have model and temperature settings
        if config:  # Only check if config exists
            assert 'model' in config or len(config) == 0
            
    def test_get_api_config_heygen(self):
        """Test HeyGen API configuration retrieval."""
        config = get_api_config('heygen')
        
        assert isinstance(config, dict)
        # Should return config dict (may be empty if not configured)
        
    def test_get_api_config_invalid_service(self):
        """Test API configuration for invalid service."""
        config = get_api_config('invalid_service')
        
        assert config == {}
        
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'test_openai_key',
        'HEYGEN_API_KEY': 'test_heygen_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_supabase_key'
    })
    def test_validate_environment_complete(self):
        """Test environment validation with all required variables."""
        result = validate_environment()
        
        assert isinstance(result, dict)
        assert result.get('openai', False) is True
        assert result.get('heygen', False) is True
        assert result.get('supabase', False) is True
        
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_environment_missing(self):
        """Test environment validation with missing variables."""
        result = validate_environment()
        
        assert isinstance(result, dict)
        # Most services should be False due to missing env vars
        
    @patch.dict('os.environ', {}, clear=True)
    def test_get_missing_env_vars(self):
        """Test getting missing environment variables."""
        missing = get_missing_env_vars()
        
        assert isinstance(missing, list)
        assert len(missing) > 0  # Should have missing vars
        assert 'OPENAI_API_KEY' in missing
        
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'test',
        'HEYGEN_API_KEY': 'test',
        'SUPABASE_URL': 'test',
        'SUPABASE_KEY': 'test',
        'CREATOMATE_API_KEY': 'test',
        'CLOUDINARY_CLOUD_NAME': 'test',
        'CLOUDINARY_API_KEY': 'test',
        'CLOUDINARY_API_SECRET': 'test'
    })
    def test_is_environment_ready_true(self):
        """Test environment readiness when all vars present."""
        result = is_environment_ready()
        
        assert result is True
        
    @patch.dict('os.environ', {}, clear=True)
    def test_is_environment_ready_false(self):
        """Test environment readiness when vars missing."""
        result = is_environment_ready()
        
        assert result is False
        
    def test_get_system_config(self):
        """Test system configuration retrieval."""
        config = get_system_config()
        
        assert isinstance(config, dict)
        assert 'version' in config
        assert 'environment' in config
        assert 'strict_mode' in config


class TestTemplates:
    """Test HeyGen template management."""
    
    def test_get_heygen_template_id_horror(self):
        """Test HeyGen template ID for Horror genre."""
        template_id = get_heygen_template_id("Horror")
        
        assert template_id is not None
        assert isinstance(template_id, str)
        # Horror should use specific template
        assert template_id == 'e2ad0e5c7e71483991536f5c93594e42'
        
    def test_get_heygen_template_id_comedy(self):
        """Test HeyGen template ID for Comedy genre."""
        template_id = get_heygen_template_id("Comedy")
        
        assert template_id == '15d9eadcb46a45dbbca1834aa0a23ede'
        
    def test_get_heygen_template_id_action(self):
        """Test HeyGen template ID for Action genre."""
        template_id = get_heygen_template_id("Action")
        
        assert template_id == 'e44b139a1b94446a997a7f2ac5ac4178'
        
    def test_get_heygen_template_id_default(self):
        """Test HeyGen template ID for unknown genre."""
        template_id = get_heygen_template_id("UnknownGenre")
        
        assert template_id == 'cc6718c5363e42b282a123f99b94b335'  # Default
        
    def test_get_heygen_template_id_none(self):
        """Test HeyGen template ID with None genre."""
        template_id = get_heygen_template_id(None)
        
        assert template_id == 'cc6718c5363e42b282a123f99b94b335'  # Default
        
    def test_get_template_info_valid(self):
        """Test template info retrieval for valid template."""
        template_id = 'cc6718c5363e42b282a123f99b94b335'  # Default template
        info = get_template_info(template_id)
        
        assert isinstance(info, dict)
        assert 'id' in info
        assert info['id'] == template_id
        
    def test_get_template_info_invalid(self):
        """Test template info retrieval for invalid template."""
        info = get_template_info('invalid_template_id')
        
        assert info == {}
        
    def test_list_available_templates(self):
        """Test listing all available templates."""
        templates = list_available_templates()
        
        assert isinstance(templates, dict)
        assert len(templates) > 0
        # Should contain genre-specific templates
        assert any('Horror' in str(templates).upper() for templates in templates.values())
        
    def test_get_templates_by_genre(self):
        """Test getting templates organized by genre."""
        templates_by_genre = get_templates_by_genre()
        
        assert isinstance(templates_by_genre, dict)
        assert 'Horror' in templates_by_genre
        assert 'Comedy' in templates_by_genre
        assert 'Action' in templates_by_genre
        assert 'Default' in templates_by_genre
        
    def test_validate_template_id_valid(self):
        """Test template ID validation for valid ID."""
        valid_id = 'cc6718c5363e42b282a123f99b94b335'
        result = validate_template_id(valid_id)
        
        assert result is True
        
    def test_validate_template_id_invalid(self):
        """Test template ID validation for invalid ID."""
        result = validate_template_id('invalid_id')
        
        assert result is False
        
    def test_get_template_for_content_horror_netflix(self):
        """Test template selection for Horror Netflix content."""
        template_info = get_template_for_content(
            genre='Horror',
            content_type='Film',
            platform='Netflix'
        )
        
        assert isinstance(template_info, dict)
        assert template_info['id'] == 'e2ad0e5c7e71483991536f5c93594e42'


class TestConstants:
    """Test constants and mappings."""
    
    def test_get_platform_colors_netflix(self):
        """Test Netflix platform colors."""
        colors = get_platform_colors('Netflix')
        
        assert isinstance(colors, dict)
        assert 'primary' in colors
        assert 'secondary' in colors
        # Netflix should have red colors
        primary = colors['primary']
        assert isinstance(primary, tuple)
        assert len(primary) == 3  # RGB tuple
        
    def test_get_genre_colors_horror(self):
        """Test Horror genre colors."""
        colors = get_genre_colors('Horror')
        
        assert isinstance(colors, dict)
        assert 'primary' in colors
        assert 'secondary' in colors
        # Horror should have dark/scary colors
        
    def test_get_thematic_colors_horror_netflix(self):
        """Test thematic colors for Horror Netflix combination."""
        colors = get_thematic_colors('Netflix', ['Horror'])
        
        assert isinstance(colors, dict)
        assert 'primary' in colors
        assert 'secondary' in colors
        
    def test_normalize_content_type_film(self):
        """Test content type normalization."""
        assert normalize_content_type('Movies') == 'Film'
        assert normalize_content_type('Films') == 'Film'
        assert normalize_content_type('film') == 'Film'
        assert normalize_content_type('FILM') == 'Film'
        
    def test_get_country_info_us(self):
        """Test US country information."""
        info = get_country_info('US')
        
        assert isinstance(info, dict)
        assert info['code'] == 'US'
        assert info['name'] == 'United States'
        
    def test_is_supported_country_us(self):
        """Test US country support."""
        assert is_supported_country('US') is True
        assert is_supported_country('XX') is False
        
    def test_get_supported_platforms(self):
        """Test getting supported platforms."""
        platforms = get_supported_platforms()
        
        assert isinstance(platforms, list)
        assert 'Netflix' in platforms
        assert 'Amazon Prime' in platforms or 'Prime Video' in platforms
        
    def test_get_supported_genres(self):
        """Test getting supported genres."""
        genres = get_supported_genres()
        
        assert isinstance(genres, list)
        assert 'Horror' in genres
        assert 'Comedy' in genres
        assert 'Action' in genres


class TestStrictMode:
    """Test strict mode functionality."""
    
    def test_strict_mode_config_creation(self):
        """Test StrictModeConfig creation."""
        config = StrictModeConfig()
        
        assert config.enabled is True
        assert config.fail_fast is True
        assert config.require_exact_movie_count is True
        assert config.require_all_assets is True
        
    def test_is_strict_mode_enabled(self):
        """Test strict mode status check."""
        result = is_strict_mode_enabled()
        
        assert isinstance(result, bool)
        
    def test_get_strict_config(self):
        """Test getting strict mode configuration."""
        config = get_strict_config()
        
        assert isinstance(config, StrictModeConfig)
        assert hasattr(config, 'enabled')
        assert hasattr(config, 'fail_fast')
        
    def test_update_strict_config(self):
        """Test updating strict mode configuration."""
        original_config = get_strict_config()
        
        update_strict_config(enabled=False)
        updated_config = get_strict_config()
        
        # Reset to original
        update_strict_config(enabled=original_config.enabled)
        
    def test_enforce_exact_count_success(self):
        """Test exact count enforcement with correct count."""
        items = ['item1', 'item2', 'item3']
        
        # Should not raise exception
        enforce_exact_count(items, 3, 'test_items')
        
    def test_enforce_exact_count_failure(self):
        """Test exact count enforcement with incorrect count."""
        items = ['item1', 'item2']
        
        with pytest.raises(StrictModeError):
            enforce_exact_count(items, 3, 'test_items')
            
    def test_enforce_api_availability_success(self):
        """Test API availability enforcement with available API."""
        mock_client = Mock()
        mock_config = {'api_key': 'test_key'}
        
        # Should not raise exception
        enforce_api_availability('Test API', mock_client, mock_config)
        
    def test_enforce_api_availability_failure(self):
        """Test API availability enforcement with unavailable API."""
        with pytest.raises(StrictModeError):
            enforce_api_availability('Test API', None)
            
    def test_enforce_url_accessibility_success(self):
        """Test URL accessibility enforcement."""
        urls = {
            'test_url': 'https://httpbin.org/status/200'  # Should be accessible
        }
        
        # Note: This might fail in test environment, so we'll mock it
        with patch('requests.head') as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            # Should not raise exception
            enforce_url_accessibility(urls, 'test_urls')
            
    def test_enforce_minimum_quality_success(self):
        """Test minimum quality enforcement with sufficient quality."""
        enforce_minimum_quality(8.5, 7.0, 'IMDB Score')
        
    def test_enforce_minimum_quality_failure(self):
        """Test minimum quality enforcement with insufficient quality."""
        with pytest.raises(StrictModeError):
            enforce_minimum_quality(6.0, 7.0, 'IMDB Score')
            
    def test_strict_mode_exceptions(self):
        """Test strict mode exception hierarchy."""
        # Test base exception
        base_error = StrictModeError("Base error")
        assert str(base_error) == "Base error"
        
        # Test validation error
        validation_error = StrictModeValidationError("Validation failed")
        assert isinstance(validation_error, StrictModeError)
        
        # Test API error
        api_error = StrictModeAPIError("API failed")
        assert isinstance(api_error, StrictModeError)
        
    @patch('config.strict_mode.is_strict_mode_enabled')
    def test_strict_mode_required_decorator(self, mock_enabled):
        """Test strict mode required decorator."""
        mock_enabled.return_value = True
        
        @strict_mode_required
        def test_function():
            return "success"
            
        result = test_function()
        assert result == "success"
        
    def test_log_strict_mode_status(self):
        """Test logging strict mode status."""
        # Should not raise exception
        log_strict_mode_status()


class TestWorkflowConfigIntegration:
    """Test config integration with workflow parameters."""
    
    def test_workflow_template_selection(self):
        """Test template selection for workflow parameters."""
        # Test Horror genre template selection
        template_id = get_heygen_template_id("Horror")
        assert template_id == 'e2ad0e5c7e71483991536f5c93594e42'
        
        # Validate template exists
        template_info = get_template_info(template_id)
        assert template_info['id'] == template_id
        
    def test_workflow_platform_colors(self):
        """Test platform colors for Netflix."""
        colors = get_platform_colors('Netflix')
        
        assert isinstance(colors, dict)
        assert 'primary' in colors
        # Should have Netflix red branding
        
    def test_workflow_environment_validation(self):
        """Test environment validation for workflow."""
        # Check that all required services are validated
        env_status = validate_environment()
        
        assert 'openai' in env_status
        assert 'heygen' in env_status
        assert 'supabase' in env_status
        assert 'creatomate' in env_status
        
    @patch('config.strict_mode.is_strict_mode_enabled')
    def test_workflow_strict_mode_validation(self, mock_enabled):
        """Test strict mode validation for workflow."""
        mock_enabled.return_value = True
        
        # Test exact movie count enforcement
        movies = [
            {'title': 'Movie 1'},
            {'title': 'Movie 2'},
            {'title': 'Movie 3'}
        ]
        
        # Should not raise exception with exactly 3 movies
        enforce_exact_count(movies, 3, 'movies')
        
        # Should raise exception with wrong count
        with pytest.raises(StrictModeError):
            enforce_exact_count(movies[:2], 3, 'movies')
            
    def test_content_type_normalization_workflow(self):
        """Test content type normalization for workflow."""
        # Workflow uses "Film" content type
        assert normalize_content_type('Film') == 'Film'
        assert normalize_content_type('Movies') == 'Film'
        assert normalize_content_type('films') == 'Film'