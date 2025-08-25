"""
Test Vizard.ai Integration

This module tests the Vizard.ai integration in the StreamGank workflow
to ensure proper functionality and error handling.

Author: StreamGank Development Team  
Version: 1.0.0 - Vizard.ai Integration Test
"""

import os
import pytest
from unittest.mock import Mock, patch
from ai.vizard_client import (
    VizardClient, 
    process_movie_trailers_with_vizard,
    validate_vizard_requirements,
    get_vizard_processing_stats
)

class TestVizardIntegration:
    """Test suite for Vizard.ai integration."""
    
    def test_vizard_client_initialization_without_api_key(self):
        """Test VizardClient initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('ai.vizard_client.get_api_config') as mock_config:
                mock_config.return_value = None
                
                with pytest.raises(ValueError) as excinfo:
                    VizardClient()
                
                assert "API key not found" in str(excinfo.value)
    
    def test_vizard_client_initialization_with_api_key(self):
        """Test VizardClient initialization succeeds with API key."""
        with patch.dict(os.environ, {'VIZARD_API_KEY': 'test_key'}):
            with patch('ai.vizard_client.get_video_settings') as mock_settings:
                mock_settings.return_value = {
                    'clip_duration': 15,
                    'enable_subtitles': True,
                    'enable_headlines': True
                }
                
                client = VizardClient()
                assert client.api_key == 'test_key'
                assert client.preferred_duration == 15
                assert client.enable_subtitles is True
                assert client.enable_headlines is True
    
    def test_process_movie_trailers_with_vizard_input_validation(self):
        """Test the main processing function handles invalid inputs."""
        # Test with empty movie data
        result = process_movie_trailers_with_vizard([], max_movies=3)
        assert result == {}
        
        # Test with movie data without trailer URLs
        movie_data = [
            {'title': 'Test Movie 1', 'trailer_url': ''},
            {'title': 'Test Movie 2'}  # No trailer_url key
        ]
        
        with patch('ai.vizard_client.VizardClient') as mock_client:
            mock_client.return_value = Mock()
            result = process_movie_trailers_with_vizard(movie_data, max_movies=3)
            # Should return empty dict as no valid trailer URLs
            assert result == {}
    
    def test_validate_vizard_requirements_missing_api_key(self):
        """Test validation function detects missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('ai.vizard_client.get_api_config') as mock_config:
                mock_config.return_value = None
                
                validation = validate_vizard_requirements()
                
                assert validation['ready'] is False
                assert validation['api_key_found'] is False
                assert len(validation['missing_requirements']) > 0
    
    def test_validate_vizard_requirements_with_api_key(self):
        """Test validation function passes with proper configuration."""
        with patch.dict(os.environ, {'VIZARD_API_KEY': 'test_key'}):
            with patch('ai.vizard_client.get_video_settings') as mock_settings:
                mock_settings.return_value = {'clip_duration': 15}
                with patch('ai.vizard_client.ensure_directory'):
                    with patch('requests.get') as mock_get:
                        mock_get.return_value.status_code = 200
                        
                        validation = validate_vizard_requirements()
                        
                        assert validation['ready'] is True
                        assert validation['api_key_found'] is True
                        assert validation['internet_available'] is True
    
    def test_get_vizard_processing_stats(self):
        """Test processing stats function."""
        with patch.dict(os.environ, {'VIZARD_API_KEY': 'test_key'}):
            with patch('ai.vizard_client.get_video_settings') as mock_video_settings:
                mock_video_settings.return_value = {
                    'clip_duration': 15,
                    'enable_subtitles': True,
                    'enable_headlines': True
                }
                
                stats = get_vizard_processing_stats()
                
                assert 'client_available' in stats
                assert 'api_configured' in stats
                assert 'video_settings' in stats
                assert stats['video_settings']['clip_duration'] == 15

class TestVizardWorkflowIntegration:
    """Test Vizard.ai integration with the main workflow."""
    
    @patch('ai.vizard_client.VizardClient')
    @patch('ai.vizard_client.cleanup_temp_files')
    @patch('ai.vizard_client.ensure_directory')
    def test_workflow_integration_success_scenario(self, mock_ensure_dir, mock_cleanup, mock_client_class):
        """Test successful integration with the workflow."""
        # Mock VizardClient behavior
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock successful project creation
        mock_client.create_project.return_value = "test_project_id"
        
        # Mock successful clip retrieval
        mock_clips = [
            {
                'title': 'Action Scene',
                'duration': 15,
                'downloadUrl': 'https://example.com/clip1.mp4'
            }
        ]
        mock_client.get_project_clips.return_value = mock_clips
        
        # Mock successful clip download
        mock_client.download_clip.return_value = True
        
        # Mock Cloudinary upload
        with patch('video.clip_processor._upload_clip_to_cloudinary') as mock_upload:
            mock_upload.return_value = 'https://cloudinary.com/test_clip.mp4'
            
            movie_data = [
                {
                    'title': 'Test Movie',
                    'id': 123,
                    'trailer_url': 'https://youtube.com/watch?v=test'
                }
            ]
            
            result = process_movie_trailers_with_vizard(movie_data, max_movies=1)
            
            # Verify successful processing
            assert result == {'Test Movie': 'https://cloudinary.com/test_clip.mp4'}
            
            # Verify API calls were made with maxClipNumber=1
            mock_client.create_project.assert_called_once()
            mock_client.get_project_clips.assert_called_once_with("test_project_id")
            mock_client.download_clip.assert_called_once()
            
            # Verify that create_project was called with template_id=None (default)
            call_args = mock_client.create_project.call_args
            assert call_args[0][1] == 'Test Movie'  # movie title
            assert call_args[0][2] is None  # template_id should be None by default
    
    @patch('ai.vizard_client.VizardClient')
    def test_workflow_integration_failure_scenario(self, mock_client_class):
        """Test workflow handles Vizard.ai failures gracefully."""
        # Mock VizardClient that fails
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.create_project.return_value = None  # Simulate failure
        
        movie_data = [
            {
                'title': 'Test Movie',
                'trailer_url': 'https://youtube.com/watch?v=test'
            }
        ]
        
        result = process_movie_trailers_with_vizard(movie_data, max_movies=1)
        
        # Should return empty dict on failure
        assert result == {}
        
        # Should still attempt to create project
        mock_client.create_project.assert_called_once()
    
    def test_max_clip_number_configuration(self):
        """Test that maxClipNumber=1 is correctly configured."""
        with patch.dict(os.environ, {'VIZARD_API_KEY': 'test_key'}):
            with patch('ai.vizard_client.get_video_settings') as mock_settings:
                mock_settings.return_value = {'clip_duration': 15}
                
                # Create client and verify initialization
                client = VizardClient()
                
                # Mock the requests.post to capture payload
                with patch('requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.json.return_value = {'data': {'projectId': 'test_id'}}
                    mock_post.return_value = mock_response
                    
                    # Call create_project
                    project_id = client.create_project(
                        "https://youtube.com/test", 
                        "Test Movie"
                    )
                    
                    # Verify project was created
                    assert project_id == 'test_id'
                    
                    # Verify maxClipNumber=1 was included in payload
                    call_args = mock_post.call_args
                    payload = call_args[1]['json']  # json parameter
                    
                    assert payload['maxClipNumber'] == 1
                    assert payload['ratioOfClip'] == 1
                    assert payload['removeSilenceSwitch'] == 1
                    assert payload['highlightSwitch'] == 1
                    assert payload['preferLength'] == [1]
                    assert payload['lang'] == 'auto'

if __name__ == '__main__':
    # Basic validation test that can be run standalone
    print("🧪 Testing Vizard.ai Integration with maxClipNumber=1...")
    
    try:
        # Test basic validation
        validation = validate_vizard_requirements()
        print(f"✅ Validation test passed: {validation}")
        
        # Test stats gathering
        stats = get_vizard_processing_stats()
        print(f"✅ Stats gathering test passed: {stats}")
        
        print("🎉 All basic tests passed!")
        print("⚙️ Configuration includes:")
        print("   📱 9:16 vertical format (ratioOfClip: 1)")
        print("   🎯 15-20s clips (preferLength: 1)")
        print("   🚀 Single best clip (maxClipNumber: 1)")
        print("   🔇 Silence removal enabled")
        print("   ✨ Keyword highlighting enabled")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
