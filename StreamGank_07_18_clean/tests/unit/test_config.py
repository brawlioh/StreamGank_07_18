"""
Unit Tests for StreamGank Config Module

Tests configuration management, template selection, settings validation,
and constants functionality.
"""

import pytest
import os
from unittest.mock import patch, Mock

# Import modules to test
from streamgank_modular.config.templates import (
    get_heygen_template_id, 
    get_template_info,
    list_available_templates,
    get_templates_by_genre,
    validate_template_id,
    get_template_for_content,
    HEYGEN_TEMPLATES
)

from streamgank_modular.config.settings import (
    get_api_config,
    validate_environment,
    get_missing_env_vars,
    is_environment_ready,
    get_system_config,
    API_SETTINGS,
    VIDEO_SETTINGS,
    SCROLL_SETTINGS
)

from streamgank_modular.config.constants import (
    get_platform_colors,
    get_genre_colors,
    get_thematic_colors,
    normalize_content_type,
    get_country_info,
    is_supported_country,
    get_supported_platforms,
    get_supported_genres,
    PLATFORM_COLORS,
    GENRE_COLORS
)


class TestHeyGenTemplates:
    """Test HeyGen template management functionality."""
    
    def test_get_heygen_template_id_horror(self):
        """Test template ID retrieval for horror genre."""
        template_id = get_heygen_template_id('Horror')
        assert template_id == 'e2ad0e5c7e71483991536f5c93594e42'
        
        # Test case insensitive
        template_id_lower = get_heygen_template_id('horror')
        assert template_id_lower == 'e2ad0e5c7e71483991536f5c93594e42'
    
    def test_get_heygen_template_id_comedy(self):
        """Test template ID retrieval for comedy genre."""
        template_id = get_heygen_template_id('Comedy')
        assert template_id == '15d9eadcb46a45dbbca1834aa0a23ede'
        
        # Test French version
        template_id_french = get_heygen_template_id('Comédie')
        assert template_id_french == '15d9eadcb46a45dbbca1834aa0a23ede'
    
    def test_get_heygen_template_id_action(self):
        """Test template ID retrieval for action genre."""
        template_id = get_heygen_template_id('Action')
        assert template_id == 'e44b139a1b94446a997a7f2ac5ac4178'
        
        # Test with adventure
        template_id_adventure = get_heygen_template_id('Action & Adventure')
        assert template_id_adventure == 'e44b139a1b94446a997a7f2ac5ac4178'
    
    def test_get_heygen_template_id_default(self):
        """Test default template ID for unknown genres."""
        template_id = get_heygen_template_id('Drama')
        assert template_id == '7fb75067718944ac8f02e661c2c61522'
        
        # Test with None
        template_id_none = get_heygen_template_id(None)
        assert template_id_none == '7fb75067718944ac8f02e661c2c61522'
        
        # Test with empty string
        template_id_empty = get_heygen_template_id('')
        assert template_id_empty == '7fb75067718944ac8f02e661c2c61522'
    
    def test_get_template_info(self):
        """Test template information retrieval."""
        # Test valid template
        template_info = get_template_info('e2ad0e5c7e71483991536f5c93594e42')
        assert template_info is not None
        assert template_info['name'] == 'Horror Template'
        assert 'Horror' in template_info['genres']
        
        # Test invalid template
        invalid_info = get_template_info('invalid_template_id')
        assert invalid_info is None
    
    def test_list_available_templates(self):
        """Test listing all available templates."""
        templates = list_available_templates()
        assert isinstance(templates, dict)
        assert 'horror' in templates
        assert 'comedy' in templates
        assert 'action' in templates
        assert 'default' in templates
        
        # Verify structure
        for template_key, template_data in templates.items():
            assert 'id' in template_data
            assert 'name' in template_data
            assert 'description' in template_data
            assert 'genres' in template_data
    
    def test_get_templates_by_genre(self):
        """Test genre to template mapping."""
        genre_mapping = get_templates_by_genre()
        assert isinstance(genre_mapping, dict)
        
        # Check specific mappings
        assert genre_mapping['Horror'] == 'e2ad0e5c7e71483991536f5c93594e42'
        assert genre_mapping['Comedy'] == '15d9eadcb46a45dbbca1834aa0a23ede'
        assert genre_mapping['Action'] == 'e44b139a1b94446a997a7f2ac5ac4178'
    
    def test_validate_template_id(self):
        """Test template ID validation."""
        # Valid template IDs
        assert validate_template_id('e2ad0e5c7e71483991536f5c93594e42') is True
        assert validate_template_id('7fb75067718944ac8f02e661c2c61522') is True
        
        # Invalid template ID
        assert validate_template_id('invalid_id') is False
        assert validate_template_id('') is False
        assert validate_template_id(None) is False
    
    def test_get_template_for_content(self):
        """Test template selection for content parameters."""
        # Horror content
        template_config = get_template_for_content('Horror', 'Film', 'Netflix')
        assert template_config['template_id'] == 'e2ad0e5c7e71483991536f5c93594e42'
        assert template_config['template_name'] == 'Horror Template'
        assert template_config['selected_for']['genre'] == 'Horror'
        
        # Unknown genre (should use default)
        default_config = get_template_for_content('Unknown Genre', 'Series', 'Max')
        assert default_config['template_id'] == '7fb75067718944ac8f02e661c2c61522'
        assert default_config['template_name'] == 'Default Template'


class TestSettings:
    """Test settings and configuration management."""
    
    def test_get_api_config(self):
        """Test API configuration retrieval."""
        # Test OpenAI config
        openai_config = get_api_config('openai')
        assert openai_config['model'] == 'gpt-4'
        assert openai_config['temperature'] == 0.8
        assert openai_config['hook_max_tokens'] == 40
        
        # Test HeyGen config
        heygen_config = get_api_config('heygen')
        assert heygen_config['base_url'] == 'https://api.heygen.com/v2'
        assert heygen_config['poll_interval'] == 15
        
        # Test invalid service
        invalid_config = get_api_config('invalid_service')
        assert invalid_config == {}
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'HEYGEN_API_KEY': 'test_key',
        'CREATOMATE_API_KEY': 'test_key',
        'CLOUDINARY_CLOUD_NAME': 'test_cloud',
        'CLOUDINARY_API_KEY': 'test_key',
        'CLOUDINARY_API_SECRET': 'test_secret'
    })
    def test_validate_environment_success(self):
        """Test environment validation with all variables set."""
        validation = validate_environment()
        
        assert validation['OPENAI_API_KEY'] is True
        assert validation['HEYGEN_API_KEY'] is True
        assert validation['CREATOMATE_API_KEY'] is True
        assert validation['CLOUDINARY_CLOUD_NAME'] is True
        assert validation['CLOUDINARY_API_KEY'] is True
        assert validation['CLOUDINARY_API_SECRET'] is True
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_missing(self):
        """Test environment validation with missing variables."""
        validation = validate_environment()
        
        # All should be False when environment is cleared
        for var_name in validation:
            assert validation[var_name] is False
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_missing_env_vars(self):
        """Test missing environment variables detection."""
        missing_vars = get_missing_env_vars()
        
        # Should include all required variables
        expected_vars = ['OPENAI_API_KEY', 'HEYGEN_API_KEY', 'CREATOMATE_API_KEY',
                        'CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
        
        for var in expected_vars:
            assert var in missing_vars
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'HEYGEN_API_KEY': 'test_key',
        'CREATOMATE_API_KEY': 'test_key',
        'CLOUDINARY_CLOUD_NAME': 'test_cloud',
        'CLOUDINARY_API_KEY': 'test_key',
        'CLOUDINARY_API_SECRET': 'test_secret'
    })
    def test_is_environment_ready_true(self):
        """Test environment readiness check when all variables are set."""
        assert is_environment_ready() is True
    
    @patch.dict(os.environ, {}, clear=True)
    def test_is_environment_ready_false(self):
        """Test environment readiness check when variables are missing."""
        assert is_environment_ready() is False
    
    def test_get_system_config(self):
        """Test complete system configuration retrieval."""
        config = get_system_config()
        
        # Check structure
        assert 'api' in config
        assert 'video' in config
        assert 'scroll' in config
        assert 'workflow' in config
        assert 'logging' in config
        assert 'environment' in config
        
        # Check API section
        assert config['api'] == API_SETTINGS
        
        # Check video section
        assert config['video'] == VIDEO_SETTINGS
        
        # Check scroll section
        assert config['scroll'] == SCROLL_SETTINGS
        
        # Check environment section
        assert 'ready' in config['environment']
        assert 'missing_vars' in config['environment']


class TestConstants:
    """Test constants and mappings."""
    
    def test_get_platform_colors(self):
        """Test platform color retrieval."""
        # Test Netflix colors
        netflix_colors = get_platform_colors('Netflix')
        assert netflix_colors['primary'] == (229, 9, 20)
        assert netflix_colors['secondary'] == (139, 0, 0)
        
        # Test unknown platform (should return Netflix default)
        unknown_colors = get_platform_colors('Unknown Platform')
        assert unknown_colors['primary'] == (229, 9, 20)  # Netflix default
    
    def test_get_genre_colors(self):
        """Test genre color retrieval."""
        # Test Horror colors
        horror_colors = get_genre_colors('Horror')
        assert horror_colors['primary'] == (139, 0, 0)
        assert horror_colors['mood'] == 'intense'
        
        # Test Comedy colors
        comedy_colors = get_genre_colors('Comedy')
        assert comedy_colors['primary'] == (255, 165, 0)
        assert comedy_colors['mood'] == 'cheerful'
        
        # Test unknown genre (should return default)
        unknown_colors = get_genre_colors('Unknown Genre')
        assert unknown_colors['primary'] == (60, 60, 100)
        assert unknown_colors['mood'] == 'neutral'
    
    def test_get_thematic_colors_priority(self):
        """Test thematic color priority: Title > Genre > Platform."""
        # Test title-specific override
        stranger_colors = get_thematic_colors('Netflix', ['Horror'], 'Stranger Things')
        assert stranger_colors['primary'] == (220, 20, 60)  # Title-specific
        
        # Test genre-based selection
        horror_colors = get_thematic_colors('Netflix', ['Horror'], 'Unknown Movie')
        assert horror_colors['primary'] == (139, 0, 0)  # Genre-based
        
        # Test platform fallback
        platform_colors = get_thematic_colors('Netflix', ['Unknown Genre'], 'Unknown Movie')
        assert platform_colors['primary'] == (229, 9, 20)  # Platform-based
    
    def test_normalize_content_type(self):
        """Test content type normalization."""
        # Test standard mappings
        assert normalize_content_type('Film') == 'movie'
        assert normalize_content_type('Movie') == 'movie'
        assert normalize_content_type('Série') == 'series'
        assert normalize_content_type('Series') == 'series'
        assert normalize_content_type('TV Show') == 'series'
        
        # Test unknown type
        assert normalize_content_type('Unknown') == 'movie'  # Default
    
    def test_get_country_info(self):
        """Test country information retrieval."""
        # Test US info
        us_info = get_country_info('US')
        assert us_info['name'] == 'United States'
        assert us_info['language'] == 'en'
        assert us_info['currency'] == 'USD'
        
        # Test France info
        fr_info = get_country_info('FR')
        assert fr_info['name'] == 'France'
        assert fr_info['language'] == 'fr'
        assert fr_info['currency'] == 'EUR'
        
        # Test unknown country (should return US default)
        unknown_info = get_country_info('XX')
        assert unknown_info['name'] == 'United States'  # Default
    
    def test_is_supported_country(self):
        """Test country support checking."""
        # Test supported countries
        assert is_supported_country('US') is True
        assert is_supported_country('FR') is True
        assert is_supported_country('DE') is True
        
        # Test unsupported country
        assert is_supported_country('XX') is False
        assert is_supported_country('') is False
        assert is_supported_country(None) is False
    
    def test_get_supported_platforms(self):
        """Test supported platforms list."""
        platforms = get_supported_platforms()
        assert isinstance(platforms, list)
        assert 'Netflix' in platforms
        assert 'Max' in platforms
        assert 'Prime Video' in platforms
        assert 'Disney+' in platforms
    
    def test_get_supported_genres(self):
        """Test supported genres list."""
        genres = get_supported_genres()
        assert isinstance(genres, list)
        assert 'Horror' in genres
        assert 'Comedy' in genres
        assert 'Action & Adventure' in genres
        assert 'Drama' in genres


class TestConfigIntegration:
    """Test integration between config modules."""
    
    def test_template_genre_consistency(self):
        """Test consistency between template genres and genre constants."""
        template_genres = get_templates_by_genre()
        supported_genres = get_supported_genres()
        
        # Check that template genres are in supported genres
        for genre in template_genres.keys():
            # Skip wildcard genres
            if genre != '*':
                assert genre in supported_genres or any(
                    genre.lower() in supported_genre.lower() for supported_genre in supported_genres
                ), f"Template genre '{genre}' not found in supported genres"
    
    def test_settings_template_consistency(self):
        """Test consistency between settings and template configurations."""
        heygen_config = get_api_config('heygen')
        default_template = heygen_config.get('default_template_id')
        
        if default_template:
            assert validate_template_id(default_template), f"Default template ID '{default_template}' is not valid"
    
    @patch('streamgank_modular.config.settings.os.getenv')
    def test_environment_integration(self, mock_getenv):
        """Test environment variable integration across modules."""
        # Mock environment variables
        mock_getenv.side_effect = lambda var, default=None: {
            'OPENAI_API_KEY': 'test_openai',
            'HEYGEN_API_KEY': 'test_heygen',
            'CREATOMATE_API_KEY': 'test_creatomate',
            'CLOUDINARY_CLOUD_NAME': 'test_cloud',
            'CLOUDINARY_API_KEY': 'test_cloudinary_key',
            'CLOUDINARY_API_SECRET': 'test_cloudinary_secret'
        }.get(var, default)
        
        # Test environment readiness
        assert is_environment_ready() is True
        
        # Test system configuration
        config = get_system_config()
        assert config['environment']['ready'] is True
        assert len(config['environment']['missing_vars']) == 0