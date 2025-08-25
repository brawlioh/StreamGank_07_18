"""
Comprehensive Unit Tests for StreamGank Video Module

Tests all video processing including Creatomate integration, composition building,
scroll video generation, and video processing utilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import video modules to test
from video.creatomate_client import (
    create_creatomate_video,
    send_creatomate_request,
    check_render_status,
    wait_for_completion,
    get_creatomate_video_url,
    create_multiple_videos,
    get_creatomate_config_status,
    estimate_render_time,
    _get_creatomate_headers,
    _get_creatomate_config
)

from video.composition_builder import (
    build_video_composition,
    get_poster_timing_strategy,
    create_poster_timing,
    HeyGenLast3sStrategy,
    WithMovieClipsStrategy,
    PosterTimingStrategy,
    _build_composition_structure
)

from video.scroll_generator import (
    generate_scroll_video,
    create_scroll_video_from_url,
    get_scroll_video_url,
    validate_scroll_parameters
)

from video.video_processor import (
    calculate_video_durations,
    get_video_duration_from_url,
    estimate_clip_durations,
    validate_duration_consistency,
    validate_video_urls,
    check_url_accessibility,
    extract_video_metadata,
    analyze_video_quality,
    batch_analyze_videos,
    _parse_frame_rate
)


class TestCreatomateClient:
    """Test Creatomate API integration functionality."""
    
    @patch.dict('os.environ', {'CREATOMATE_API_KEY': 'test_key'})
    def test_get_creatomate_headers_success(self):
        """Test Creatomate headers retrieval with API key."""
        headers = _get_creatomate_headers()
        
        assert headers is not None
        assert 'Authorization' in headers
        assert 'Bearer test_key' in headers['Authorization']
        
    @patch.dict('os.environ', {}, clear=True)
    def test_get_creatomate_headers_no_key(self):
        """Test Creatomate headers retrieval without API key."""
        headers = _get_creatomate_headers()
        
        assert headers is None
        
    def test_get_creatomate_config(self):
        """Test Creatomate configuration retrieval."""
        config = _get_creatomate_config()
        
        assert isinstance(config, dict)
        assert 'api_url' in config
        assert 'timeout' in config
        
    @patch('video.creatomate_client._get_creatomate_headers')
    @patch('video.creatomate_client.build_video_composition')
    @patch('video.creatomate_client.send_creatomate_request')
    def test_create_creatomate_video_success(self, mock_send, mock_composition, mock_headers):
        """Test successful Creatomate video creation."""
        # Setup mocks
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        mock_composition.return_value = {'elements': []}
        mock_send.return_value = 'render_id_123'
        
        heygen_urls = {
            'movie1': 'https://heygen.com/video1.mp4',
            'movie2': 'https://heygen.com/video2.mp4',
            'movie3': 'https://heygen.com/video3.mp4'
        }
        
        movie_covers = {
            'movie1': 'https://cloudinary.com/poster1.jpg',
            'movie2': 'https://cloudinary.com/poster2.jpg',
            'movie3': 'https://cloudinary.com/poster3.jpg'
        }
        
        movie_clips = {
            'movie1': 'https://cloudinary.com/clip1.mp4',
            'movie2': 'https://cloudinary.com/clip2.mp4',
            'movie3': 'https://cloudinary.com/clip3.mp4'
        }
        
        result = create_creatomate_video(
            heygen_video_urls=heygen_urls,
            movie_covers=movie_covers,
            movie_clips=movie_clips
        )
        
        assert result == 'render_id_123'
        mock_composition.assert_called_once()
        mock_send.assert_called_once()
        
    @patch('video.creatomate_client._get_creatomate_headers')
    def test_create_creatomate_video_no_headers(self, mock_headers):
        """Test Creatomate video creation without headers."""
        mock_headers.return_value = None
        
        result = create_creatomate_video({}, {}, {})
        
        assert result is None
        
    @patch('requests.post')
    @patch('video.creatomate_client._get_creatomate_headers')
    def test_send_creatomate_request_success(self, mock_headers, mock_post):
        """Test successful Creatomate request sending."""
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'render_123'}
        mock_post.return_value = mock_response
        
        composition = {'elements': []}
        result = send_creatomate_request(composition)
        
        assert result == 'render_123'
        
    @patch('requests.get')
    @patch('video.creatomate_client._get_creatomate_headers')
    def test_check_render_status_completed(self, mock_headers, mock_get):
        """Test render status check for completed video."""
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'succeeded',
            'url': 'https://creatomate.com/final_video.mp4'
        }
        mock_get.return_value = mock_response
        
        result = check_render_status('render_123')
        
        assert result['status'] == 'succeeded'
        assert result['url'] == 'https://creatomate.com/final_video.mp4'
        
    @patch('video.creatomate_client.check_render_status')
    @patch('time.sleep')
    def test_wait_for_completion_success(self, mock_sleep, mock_check):
        """Test waiting for video completion."""
        # Mock progression: processing -> completed
        mock_check.side_effect = [
            {'status': 'processing'},
            {'status': 'succeeded', 'url': 'https://creatomate.com/video.mp4'}
        ]
        
        result = wait_for_completion('render_123', max_wait_minutes=1)
        
        assert result is not None
        assert result['status'] == 'succeeded'
        assert result['url'] == 'https://creatomate.com/video.mp4'
        
    def test_estimate_render_time(self):
        """Test render time estimation."""
        simple_composition = {'elements': [{'type': 'video'}]}
        complex_composition = {'elements': [
            {'type': 'video'}, {'type': 'image'}, {'type': 'text'},
            {'type': 'video'}, {'type': 'image'}, {'type': 'text'}
        ]}
        
        simple_time = estimate_render_time(simple_composition)
        complex_time = estimate_render_time(complex_composition)
        
        assert simple_time > 0
        assert complex_time > simple_time


class TestCompositionBuilder:
    """Test video composition building functionality."""
    
    def test_poster_timing_strategy_abstract(self):
        """Test PosterTimingStrategy abstract base class."""
        # Should not be able to instantiate abstract class
        with pytest.raises(TypeError):
            PosterTimingStrategy()
            
    def test_heygen_last3s_strategy(self):
        """Test HeyGenLast3sStrategy implementation."""
        strategy = HeyGenLast3sStrategy()
        
        heygen_durations = {
            'movie1': 10.0,
            'movie2': 12.0,
            'movie3': 8.0
        }
        
        timings = strategy.calculate_poster_timing(heygen_durations)
        
        assert isinstance(timings, dict)
        assert 'movie1' in timings
        assert 'movie2' in timings
        assert 'movie3' in timings
        
        # Each movie should have start and end times
        for movie, timing in timings.items():
            assert 'start' in timing
            assert 'end' in timing
            assert timing['end'] > timing['start']
            
    def test_with_movie_clips_strategy(self):
        """Test WithMovieClipsStrategy implementation."""
        strategy = WithMovieClipsStrategy()
        
        heygen_durations = {
            'movie1': 10.0,
            'movie2': 12.0,
            'movie3': 8.0
        }
        
        clip_durations = {
            'movie1': 15.0,
            'movie2': 15.0,
            'movie3': 15.0
        }
        
        timings = strategy.calculate_poster_timing(heygen_durations, clip_durations)
        
        assert isinstance(timings, dict)
        assert len(timings) == 3
        
    def test_get_poster_timing_strategy(self):
        """Test poster timing strategy factory."""
        heygen_strategy = get_poster_timing_strategy('heygen_last3s')
        clips_strategy = get_poster_timing_strategy('with_movie_clips')
        
        assert isinstance(heygen_strategy, HeyGenLast3sStrategy)
        assert isinstance(clips_strategy, WithMovieClipsStrategy)
        
        # Test invalid strategy
        with pytest.raises(ValueError):
            get_poster_timing_strategy('invalid_strategy')
            
    @patch('video.composition_builder.calculate_video_durations')
    def test_build_video_composition(self, mock_durations):
        """Test complete video composition building."""
        mock_durations.return_value = {
            'movie1': 10.0,
            'movie2': 12.0,
            'movie3': 8.0
        }
        
        heygen_urls = {
            'movie1': 'https://heygen.com/video1.mp4',
            'movie2': 'https://heygen.com/video2.mp4',
            'movie3': 'https://heygen.com/video3.mp4'
        }
        
        movie_covers = {
            'movie1': 'https://cloudinary.com/poster1.jpg',
            'movie2': 'https://cloudinary.com/poster2.jpg',
            'movie3': 'https://cloudinary.com/poster3.jpg'
        }
        
        movie_clips = {
            'movie1': 'https://cloudinary.com/clip1.mp4',
            'movie2': 'https://cloudinary.com/clip2.mp4',
            'movie3': 'https://cloudinary.com/clip3.mp4'
        }
        
        composition = build_video_composition(
            heygen_video_urls=heygen_urls,
            movie_covers=movie_covers,
            movie_clips=movie_clips,
            poster_timing_mode='heygen_last3s'
        )
        
        assert isinstance(composition, dict)
        assert 'elements' in composition
        assert len(composition['elements']) > 0
        
        # Should include intro image element
        intro_elements = [e for e in composition['elements'] if e.get('name') == 'intro_image']
        assert len(intro_elements) > 0
        
        # Should include HeyGen video elements
        heygen_elements = [e for e in composition['elements'] if 'heygen' in e.get('name', '').lower()]
        assert len(heygen_elements) == 3


class TestScrollGenerator:
    """Test scroll video generation functionality."""
    
    @patch('video.scroll_generator.create_scroll_video_from_url')
    def test_generate_scroll_video(self, mock_create):
        """Test scroll video generation."""
        mock_create.return_value = 'https://scroll-video-url.mp4'
        
        result = generate_scroll_video(
            country='US',
            genre='Horror',
            platform='Netflix',
            content_type='Film',
            duration=4,
            scroll_distance=1.5
        )
        
        assert result == 'https://scroll-video-url.mp4'
        mock_create.assert_called_once()
        
    def test_get_scroll_video_url(self):
        """Test scroll video URL generation."""
        url = get_scroll_video_url('US', 'Horror', 'Netflix', 'Film')
        
        assert isinstance(url, str)
        assert len(url) > 0
        
    def test_validate_scroll_parameters_valid(self):
        """Test scroll parameter validation with valid params."""
        result = validate_scroll_parameters(duration=4, scroll_distance=1.5)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        
    def test_validate_scroll_parameters_invalid(self):
        """Test scroll parameter validation with invalid params."""
        result = validate_scroll_parameters(duration=-1, scroll_distance=0)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0


class TestVideoProcessor:
    """Test video processing utilities."""
    
    @patch('requests.head')
    def test_check_url_accessibility_success(self, mock_head):
        """Test URL accessibility check for accessible URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        result = check_url_accessibility('https://test.com/video.mp4')
        
        assert result['is_accessible'] is True
        assert result['status_code'] == 200
        
    @patch('requests.head')
    def test_check_url_accessibility_failure(self, mock_head):
        """Test URL accessibility check for inaccessible URL."""
        mock_head.side_effect = Exception("Connection failed")
        
        result = check_url_accessibility('https://invalid-url.com/video.mp4')
        
        assert result['is_accessible'] is False
        assert 'error' in result
        
    def test_validate_video_urls_valid(self):
        """Test video URL validation with valid URLs."""
        heygen_urls = {
            'movie1': 'https://heygen.com/video1.mp4',
            'movie2': 'https://heygen.com/video2.mp4',
            'movie3': 'https://heygen.com/video3.mp4'
        }
        
        clip_urls = [
            'https://cloudinary.com/clip1.mp4',
            'https://cloudinary.com/clip2.mp4',
            'https://cloudinary.com/clip3.mp4'
        ]
        
        with patch('video.video_processor.check_url_accessibility') as mock_check:
            mock_check.return_value = {'is_accessible': True, 'status_code': 200}
            
            result = validate_video_urls(heygen_urls, clip_urls)
            
            assert result['all_accessible'] is True
            assert result['total_urls'] == 6  # 3 HeyGen + 3 clips
            
    def test_estimate_clip_durations(self):
        """Test clip duration estimation."""
        clip_urls = [
            'https://test.com/clip1.mp4',
            'https://test.com/clip2.mp4',
            'https://test.com/clip3.mp4'
        ]
        
        durations = estimate_clip_durations(clip_urls)
        
        assert isinstance(durations, dict)
        assert len(durations) == 3
        for url, duration in durations.items():
            assert duration > 0
            
    @patch('video.video_processor.get_video_duration_from_url')
    def test_calculate_video_durations(self, mock_get_duration):
        """Test video duration calculation."""
        mock_get_duration.side_effect = [10.0, 12.0, 8.0]
        
        video_urls = {
            'movie1': 'https://heygen.com/video1.mp4',
            'movie2': 'https://heygen.com/video2.mp4',
            'movie3': 'https://heygen.com/video3.mp4'
        }
        
        durations = calculate_video_durations(video_urls)
        
        assert durations['movie1'] == 10.0
        assert durations['movie2'] == 12.0
        assert durations['movie3'] == 8.0
        
    def test_validate_duration_consistency(self):
        """Test duration consistency validation."""
        heygen_durations = {
            'movie1': 10.0,
            'movie2': 12.0,
            'movie3': 8.0
        }
        
        clip_durations = {
            'movie1': 15.0,
            'movie2': 15.0,
            'movie3': 15.0
        }
        
        result = validate_duration_consistency(heygen_durations, clip_durations)
        
        assert result['is_consistent'] is True or result['is_consistent'] is False
        assert 'duration_differences' in result
        
    def test_parse_frame_rate(self):
        """Test frame rate parsing."""
        assert _parse_frame_rate("30.00") == 30.0
        assert _parse_frame_rate("25/1") == 25.0
        assert _parse_frame_rate("invalid") == 30.0  # Default
        
    @patch('video.video_processor.extract_video_metadata')
    def test_analyze_video_quality(self, mock_extract):
        """Test video quality analysis."""
        mock_metadata = {
            'duration': 10.0,
            'width': 1920,
            'height': 1080,
            'frame_rate': '30.00',
            'bit_rate': '5000000'
        }
        
        quality = analyze_video_quality(mock_metadata)
        
        assert 'resolution_quality' in quality
        assert 'duration_quality' in quality
        assert 'overall_score' in quality
        assert isinstance(quality['overall_score'], (int, float))
        
    @patch('video.video_processor.extract_video_metadata')
    def test_batch_analyze_videos(self, mock_extract):
        """Test batch video analysis."""
        mock_extract.return_value = {
            'duration': 10.0,
            'width': 1920,
            'height': 1080
        }
        
        video_urls = [
            'https://test.com/video1.mp4',
            'https://test.com/video2.mp4'
        ]
        
        results = batch_analyze_videos(video_urls)
        
        assert len(results) == 2
        for result in results:
            assert 'url' in result
            assert 'quality_analysis' in result


class TestWorkflowVideoIntegration:
    """Test video module integration with workflow."""
    
    @patch('video.creatomate_client.create_creatomate_video')
    @patch('video.composition_builder.build_video_composition')
    def test_complete_video_workflow(self, mock_composition, mock_create):
        """Test complete video creation workflow."""
        # Mock composition building
        mock_composition.return_value = {
            'elements': [
                {'type': 'image', 'name': 'intro_image'},
                {'type': 'video', 'name': 'heygen_movie1'},
                {'type': 'video', 'name': 'heygen_movie2'},
                {'type': 'video', 'name': 'heygen_movie3'}
            ]
        }
        
        # Mock video creation
        mock_create.return_value = 'render_id_123'
        
        # Workflow test data
        heygen_urls = {
            'movie1': 'https://heygen.com/intro_movie1.mp4',  # Contains intro + hook
            'movie2': 'https://heygen.com/movie2.mp4',
            'movie3': 'https://heygen.com/movie3.mp4'
        }
        
        movie_covers = {
            'movie1': 'https://cloudinary.com/godzilla.jpg',
            'movie2': 'https://cloudinary.com/train.jpg',
            'movie3': 'https://cloudinary.com/wailing.jpg'
        }
        
        movie_clips = {
            'movie1': 'https://cloudinary.com/godzilla_clip.mp4',
            'movie2': 'https://cloudinary.com/train_clip.mp4',
            'movie3': 'https://cloudinary.com/wailing_clip.mp4'
        }
        
        # Test composition building
        composition = build_video_composition(
            heygen_video_urls=heygen_urls,
            movie_covers=movie_covers,
            movie_clips=movie_clips,
            poster_timing_mode='heygen_last3s'
        )
        
        # Test video creation
        render_id = create_creatomate_video(
            heygen_video_urls=heygen_urls,
            movie_covers=movie_covers,
            movie_clips=movie_clips
        )
        
        assert render_id == 'render_id_123'
        mock_composition.assert_called()
        mock_create.assert_called_once()
        
    def test_video_structure_validation(self):
        """Test video structure matches workflow requirements."""
        # Test that intro integration doesn't affect video composition structure
        with patch('video.composition_builder.calculate_video_durations') as mock_durations:
            mock_durations.return_value = {
                'movie1': 15.0,  # Longer due to intro + hook
                'movie2': 10.0,
                'movie3': 8.0
            }
            
            heygen_urls = {
                'movie1': 'https://heygen.com/intro_movie1.mp4',
                'movie2': 'https://heygen.com/movie2.mp4',
                'movie3': 'https://heygen.com/movie3.mp4'
            }
            
            composition = build_video_composition(
                heygen_video_urls=heygen_urls,
                movie_covers={},
                movie_clips={}
            )
            
            # Should still have intro image element
            intro_elements = [e for e in composition['elements'] if e.get('name') == 'intro_image']
            assert len(intro_elements) > 0
            
            # Should have exactly 3 HeyGen videos
            heygen_elements = [e for e in composition['elements'] if 'heygen' in e.get('name', '').lower()]
            assert len(heygen_elements) == 3
            
    def test_scroll_video_integration(self):
        """Test scroll video integration with workflow."""
        with patch('video.scroll_generator.create_scroll_video_from_url') as mock_create:
            mock_create.return_value = 'https://scroll-video.mp4'
            
            scroll_url = generate_scroll_video(
                country='US',
                genre='Horror',
                platform='Netflix',
                content_type='Film',
                duration=4,
                scroll_distance=1.5
            )
            
            assert scroll_url == 'https://scroll-video.mp4'
            mock_create.assert_called_once()
            
            # Validate scroll parameters
            validation = validate_scroll_parameters(duration=4, scroll_distance=1.5)
            assert validation['is_valid'] is True