"""
Unit Tests for StreamGank Video Module

Tests video processing including Creatomate integration, scroll video generation,
composition building, and video processing utilities.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
from streamgank_modular.video.creatomate_client import (
    create_creatomate_video,
    send_creatomate_request,
    check_render_status,
    wait_for_completion,
    get_creatomate_video_url,
    create_multiple_videos,
    get_creatomate_config_status,
    estimate_render_time
)

from streamgank_modular.video.scroll_generator import (
    generate_scroll_video,
    create_scroll_video_from_url,
    get_scroll_video_url,
    validate_scroll_parameters
)

from streamgank_modular.video.composition_builder import (
    build_video_composition,
    get_poster_timing_strategy,
    create_poster_timing,
    HeyGenLast3sStrategy,
    WithMovieClipsStrategy
)

from streamgank_modular.video.video_processor import (
    calculate_video_durations,
    get_video_duration_from_url,
    estimate_clip_durations,
    validate_video_urls,
    check_url_accessibility,
    extract_video_metadata,
    analyze_video_quality,
    batch_analyze_videos
)


class TestCreatomateClient:
    """Test Creatomate API integration functionality."""
    
    @patch('streamgank_modular.video.creatomate_client._get_creatomate_headers')
    @patch('streamgank_modular.video.creatomate_client.validate_video_urls')
    @patch('streamgank_modular.video.creatomate_client.build_video_composition')
    @patch('streamgank_modular.video.creatomate_client.send_creatomate_request')
    def test_create_creatomate_video_success(self, mock_send, mock_build, mock_validate, mock_headers):
        """Test successful Creatomate video creation."""
        # Setup mocks
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        mock_validate.return_value = {'is_valid': True, 'errors': []}
        mock_build.return_value = {'width': 1080, 'height': 1920, 'elements': []}
        mock_send.return_value = 'render_id_123'
        
        heygen_urls = {'movie1': 'https://example.com/video1.mp4'}
        movie_covers = ['https://example.com/poster1.jpg']
        movie_clips = ['https://example.com/clip1.mp4']
        
        result = create_creatomate_video(heygen_urls, movie_covers, movie_clips)
        
        assert result == 'render_id_123'
        mock_validate.assert_called_once()
        mock_build.assert_called_once()
        mock_send.assert_called_once()
    
    @patch('streamgank_modular.video.creatomate_client._get_creatomate_headers')
    def test_create_creatomate_video_no_headers(self, mock_headers):
        """Test Creatomate video creation when headers unavailable."""
        mock_headers.return_value = None
        
        result = create_creatomate_video({'movie1': 'test_url'})
        
        assert result is None
    
    @patch('requests.post')
    @patch('streamgank_modular.video.creatomate_client._get_creatomate_headers')
    def test_send_creatomate_request_success(self, mock_headers, mock_post):
        """Test successful Creatomate render request."""
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'render_id_123'}
        mock_post.return_value = mock_response
        
        composition = {'width': 1080, 'height': 1920, 'elements': []}
        
        result = send_creatomate_request(composition)
        
        assert result == 'render_id_123'
        mock_post.assert_called_once()
    
    @patch('requests.post')
    @patch('streamgank_modular.video.creatomate_client._get_creatomate_headers')
    def test_send_creatomate_request_rate_limit(self, mock_headers, mock_post):
        """Test Creatomate request with rate limiting."""
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        
        # First call: rate limit, second call: success
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {'id': 'render_id_456'}
        
        mock_post.side_effect = [rate_limit_response, success_response]
        
        composition = {'width': 1080, 'height': 1920}
        
        with patch('time.sleep'):  # Skip actual sleeping
            result = send_creatomate_request(composition)
        
        assert result == 'render_id_456'
        assert mock_post.call_count == 2
    
    @patch('requests.get')
    @patch('streamgank_modular.video.creatomate_client._get_creatomate_headers')
    def test_check_render_status_completed(self, mock_headers, mock_get):
        """Test checking render status when completed."""
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'succeeded',
            'progress': 100,
            'url': 'https://example.com/video.mp4',
            'duration': 30.0
        }
        mock_get.return_value = mock_response
        
        result = check_render_status('render_id_123')
        
        assert result['status'] == 'succeeded'
        assert result['progress'] == 100
        assert result['url'] == 'https://example.com/video.mp4'
        assert result['duration'] == 30.0
    
    @patch('streamgank_modular.video.creatomate_client.check_render_status')
    def test_wait_for_completion_success(self, mock_check_status):
        """Test waiting for completion when render completes quickly."""
        # First call: processing, second call: completed
        mock_check_status.side_effect = [
            {'status': 'processing', 'progress': 50},
            {'status': 'succeeded', 'url': 'https://example.com/video.mp4'}
        ]
        
        with patch('time.sleep'):  # Skip actual sleeping
            result = wait_for_completion('render_id_123', max_wait_time=60, poll_interval=1)
        
        assert result['status'] == 'succeeded'
        assert result['url'] == 'https://example.com/video.mp4'
    
    @patch('streamgank_modular.video.creatomate_client.wait_for_completion')
    def test_get_creatomate_video_url_success(self, mock_wait):
        """Test getting video URL from completed render."""
        mock_wait.return_value = {
            'status': 'succeeded',
            'url': 'https://example.com/final_video.mp4'
        }
        
        result = get_creatomate_video_url('render_id_123')
        
        assert result == 'https://example.com/final_video.mp4'
    
    def test_estimate_render_time(self):
        """Test render time estimation."""
        simple_composition = {
            'duration': 30,
            'elements': [{'type': 'video'}, {'type': 'image'}]
        }
        
        complex_composition = {
            'duration': 60,
            'elements': [{'type': 'video'} for _ in range(25)]  # Many elements
        }
        
        simple_time = estimate_render_time(simple_composition)
        complex_time = estimate_render_time(complex_composition)
        
        assert simple_time > 0
        assert complex_time > simple_time  # Complex should take longer
    
    @patch.dict('os.environ', {'CREATOMATE_API_KEY': 'test_key'})
    def test_get_creatomate_config_status_configured(self):
        """Test Creatomate configuration status when configured."""
        status = get_creatomate_config_status()
        
        assert status['api_key_set'] is True
        assert status['headers_available'] is True


class TestScrollGenerator:
    """Test scroll video generation functionality."""
    
    @patch('streamgank_modular.video.scroll_generator.create_scroll_video')
    @patch('streamgank_modular.video.scroll_generator.upload_clip_to_cloudinary')
    def test_generate_scroll_video_success(self, mock_upload, mock_create):
        """Test successful scroll video generation."""
        mock_create.return_value = '/temp/scroll_video.mp4'
        mock_upload.return_value = 'https://cloudinary.com/scroll_video.mp4'
        
        result = generate_scroll_video(
            country='US',
            genre='Horror',
            platform='Netflix',
            content_type='Movies',
            duration=4
        )
        
        assert result == 'https://cloudinary.com/scroll_video.mp4'
        mock_create.assert_called_once()
        mock_upload.assert_called_once()
    
    @patch('streamgank_modular.video.scroll_generator.create_scroll_video')
    def test_generate_scroll_video_creation_failed(self, mock_create):
        """Test scroll video generation when creation fails."""
        mock_create.return_value = None
        
        result = generate_scroll_video('US', 'Horror', 'Netflix', 'Movies')
        
        assert result is None
    
    def test_get_scroll_video_url(self):
        """Test scroll video URL building."""
        with patch('streamgank_modular.video.scroll_generator.build_streamgank_url') as mock_build:
            mock_build.return_value = 'https://streamgank.com/us/horror/netflix/movies'
            
            result = get_scroll_video_url('US', 'Horror', 'Netflix', 'Movies')
            
            assert result == 'https://streamgank.com/us/horror/netflix/movies'
            mock_build.assert_called_once_with('US', 'Horror', 'Netflix', 'Movies')
    
    def test_validate_scroll_parameters_valid(self):
        """Test scroll parameter validation with valid parameters."""
        result = validate_scroll_parameters(duration=4, scroll_distance=1.5)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_scroll_parameters_invalid_duration(self):
        """Test scroll parameter validation with invalid duration."""
        result = validate_scroll_parameters(duration=0, scroll_distance=1.5)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert 'must be at least 1 second' in result['errors'][0]
    
    def test_validate_scroll_parameters_warnings(self):
        """Test scroll parameter validation with warning conditions."""
        result = validate_scroll_parameters(duration=12, scroll_distance=3.5)
        
        assert result['is_valid'] is True
        assert len(result['warnings']) == 2  # Long duration and long scroll distance


class TestCompositionBuilder:
    """Test video composition building functionality."""
    
    @patch('streamgank_modular.video.composition_builder.calculate_video_durations')
    @patch('streamgank_modular.video.composition_builder.estimate_clip_durations')
    def test_build_video_composition_success(self, mock_clip_durations, mock_video_durations):
        """Test successful video composition building."""
        # Setup mocks
        mock_video_durations.return_value = {
            'heygen1': 8.0, 'heygen2': 7.5, 'heygen3': 9.0
        }
        mock_clip_durations.return_value = {
            'clip1': 12.0, 'clip2': 11.5, 'clip3': 13.0
        }
        
        heygen_urls = {
            'movie1': 'https://example.com/heygen1.mp4',
            'movie2': 'https://example.com/heygen2.mp4',
            'movie3': 'https://example.com/heygen3.mp4'
        }
        movie_covers = [
            'https://example.com/poster1.jpg',
            'https://example.com/poster2.jpg',
            'https://example.com/poster3.jpg'
        ]
        movie_clips = [
            'https://example.com/clip1.mp4',
            'https://example.com/clip2.mp4',
            'https://example.com/clip3.mp4'
        ]
        
        result = build_video_composition(heygen_urls, movie_covers, movie_clips)
        
        assert result is not None
        assert result['width'] == 1080
        assert result['height'] == 1920
        assert result['frame_rate'] == 30
        assert len(result['elements']) > 0
    
    def test_get_poster_timing_strategy_heygen_last3s(self):
        """Test getting HeyGen last 3s timing strategy."""
        strategy = get_poster_timing_strategy('heygen_last3s')
        
        assert isinstance(strategy, HeyGenLast3sStrategy)
    
    def test_get_poster_timing_strategy_with_clips(self):
        """Test getting with movie clips timing strategy."""
        strategy = get_poster_timing_strategy('with_movie_clips')
        
        assert isinstance(strategy, WithMovieClipsStrategy)
    
    def test_get_poster_timing_strategy_default(self):
        """Test getting default timing strategy for unknown mode."""
        strategy = get_poster_timing_strategy('unknown_mode')
        
        assert isinstance(strategy, HeyGenLast3sStrategy)  # Should default
    
    def test_heygen_last3s_strategy_calculate_timing(self):
        """Test HeyGen last 3s timing calculation."""
        strategy = HeyGenLast3sStrategy()
        
        heygen_durations = {'heygen1': 8.0, 'heygen2': 7.0, 'heygen3': 9.0}
        clip_durations = {'clip1': 12.0, 'clip2': 11.0, 'clip3': 13.0}
        
        result = strategy.calculate_timing(heygen_durations, clip_durations)
        
        assert 'poster1' in result
        assert 'poster2' in result
        assert 'poster3' in result
        
        # Check that poster durations are reasonable
        for poster_key in result:
            assert result[poster_key]['duration'] >= 0.5
            assert result[poster_key]['duration'] <= 3.0
    
    def test_with_movie_clips_strategy_calculate_timing(self):
        """Test with movie clips timing calculation."""
        strategy = WithMovieClipsStrategy()
        
        heygen_durations = {'heygen1': 8.0, 'heygen2': 7.0, 'heygen3': 9.0}
        clip_durations = {'clip1': 12.0, 'clip2': 11.0, 'clip3': 13.0}
        
        result = strategy.calculate_timing(heygen_durations, clip_durations)
        
        assert 'poster1' in result
        assert 'poster2' in result
        assert 'poster3' in result
        
        # Posters should have same duration as clips
        assert result['poster1']['duration'] == 12.0
        assert result['poster2']['duration'] == 11.0
        assert result['poster3']['duration'] == 13.0
    
    def test_create_poster_timing(self):
        """Test poster timing element creation."""
        poster_timings = {
            'poster1': {'time': 5.0, 'duration': 3.0},
            'poster2': {'time': 15.0, 'duration': 2.5},
            'poster3': {'time': 25.0, 'duration': 3.5}
        }
        movie_covers = [
            'https://example.com/poster1.jpg',
            'https://example.com/poster2.jpg',
            'https://example.com/poster3.jpg'
        ]
        
        result = create_poster_timing(poster_timings, movie_covers)
        
        assert len(result) == 3
        
        # Check first poster element
        poster1 = result[0]
        assert poster1['type'] == 'image'
        assert poster1['track'] == 2
        assert poster1['time'] == 5.0
        assert poster1['duration'] == 3.0
        assert poster1['source'] == movie_covers[0]
        assert len(poster1['animations']) == 2  # Fade in and out


class TestVideoProcessor:
    """Test video processing functionality."""
    
    @patch('streamgank_modular.video.video_processor.get_video_duration_from_url')
    def test_calculate_video_durations_success(self, mock_get_duration):
        """Test successful video duration calculation."""
        mock_get_duration.side_effect = [8.5, 7.2, 9.1]  # Different durations
        
        video_urls = {
            'heygen1': 'https://example.com/video1.mp4',
            'heygen2': 'https://example.com/video2.mp4',
            'heygen3': 'https://example.com/video3.mp4'
        }
        
        result = calculate_video_durations(video_urls)
        
        assert result is not None
        assert len(result) == 3
        assert result['heygen1'] == 8.5
        assert result['heygen2'] == 7.2
        assert result['heygen3'] == 9.1
    
    @patch('streamgank_modular.video.video_processor.get_video_duration_from_url')
    @patch('streamgank_modular.video.video_processor.estimate_video_duration')
    def test_calculate_video_durations_with_fallback(self, mock_estimate, mock_get_duration):
        """Test video duration calculation with script-based fallback."""
        mock_get_duration.side_effect = [8.5, None, 9.1]  # Second video fails
        mock_estimate.return_value = 7.0
        
        video_urls = {
            'heygen1': 'https://example.com/video1.mp4',
            'heygen2': 'https://example.com/video2.mp4',
            'heygen3': 'https://example.com/video3.mp4'
        }
        scripts = {
            'heygen2': 'This is a test script for estimation'
        }
        
        result = calculate_video_durations(video_urls, scripts)
        
        assert result is not None
        assert result['heygen1'] == 8.5
        assert result['heygen2'] == 7.0  # Estimated
        assert result['heygen3'] == 9.1
    
    @patch('subprocess.run')
    def test_get_video_duration_from_url_success(self, mock_run):
        """Test successful video duration extraction from URL."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'format': {'duration': '123.45'}
        })
        mock_run.return_value = mock_result
        
        duration = get_video_duration_from_url('https://example.com/video.mp4')
        
        assert duration == 123.45
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_video_duration_from_url_invalid_url(self, mock_run):
        """Test video duration extraction from invalid URL."""
        duration = get_video_duration_from_url('not-a-url')
        
        assert duration is None
        mock_run.assert_not_called()
    
    def test_estimate_clip_durations_with_urls(self):
        """Test clip duration estimation with URLs."""
        clip_urls = [
            'https://example.com/clip1.mp4',
            'https://example.com/clip2.mp4',
            'https://example.com/clip3.mp4'
        ]
        
        with patch('streamgank_modular.video.video_processor.get_video_duration_from_url', return_value=15.0):
            result = estimate_clip_durations(clip_urls)
        
        assert len(result) == 3
        assert all(duration == 15.0 for duration in result.values())
    
    def test_estimate_clip_durations_no_urls(self):
        """Test clip duration estimation without URLs."""
        result = estimate_clip_durations(None)
        
        assert len(result) == 3
        assert all(duration == 12.0 for duration in result.values())  # Default
    
    @patch('streamgank_modular.video.video_processor.check_url_accessibility')
    def test_validate_video_urls_all_valid(self, mock_check):
        """Test video URL validation when all URLs are valid."""
        mock_check.return_value = {'accessible': True, 'status_code': 200}
        
        heygen_urls = {'movie1': 'https://example.com/video1.mp4'}
        movie_covers = ['https://example.com/poster1.jpg']
        movie_clips = ['https://example.com/clip1.mp4']
        
        result = validate_video_urls(heygen_urls, movie_covers, movie_clips)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
    
    @patch('streamgank_modular.video.video_processor.check_url_accessibility')
    def test_validate_video_urls_heygen_invalid(self, mock_check):
        """Test video URL validation when HeyGen URL is invalid."""
        mock_check.return_value = {'accessible': False, 'error': 'HTTP 404'}
        
        heygen_urls = {'movie1': 'https://example.com/invalid_video.mp4'}
        
        result = validate_video_urls(heygen_urls)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert 'HeyGen movie1' in result['errors'][0]
    
    @patch('requests.head')
    def test_check_url_accessibility_success(self, mock_head):
        """Test URL accessibility check for accessible URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'video/mp4', 'content-length': '1024000'}
        mock_head.return_value = mock_response
        
        result = check_url_accessibility('https://example.com/video.mp4')
        
        assert result['accessible'] is True
        assert result['status_code'] == 200
        assert result['content_type'] == 'video/mp4'
    
    @patch('requests.head')
    def test_check_url_accessibility_not_found(self, mock_head):
        """Test URL accessibility check for 404 URL."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response
        
        result = check_url_accessibility('https://example.com/missing.mp4')
        
        assert result['accessible'] is False
        assert result['status_code'] == 404
        assert result['error'] == 'HTTP 404'
    
    @patch('subprocess.run')
    def test_extract_video_metadata_success(self, mock_run):
        """Test successful video metadata extraction."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'format': {
                'duration': '120.0',
                'size': '10240000',
                'format_name': 'mp4',
                'bit_rate': '2000000'
            },
            'streams': [
                {
                    'codec_type': 'video',
                    'width': 1920,
                    'height': 1080,
                    'codec_name': 'h264',
                    'pix_fmt': 'yuv420p',
                    'r_frame_rate': '30/1'
                },
                {
                    'codec_type': 'audio',
                    'codec_name': 'aac',
                    'sample_rate': '44100',
                    'channels': 2
                }
            ]
        })
        mock_run.return_value = mock_result
        
        metadata = extract_video_metadata('https://example.com/video.mp4')
        
        assert metadata is not None
        assert metadata['duration'] == 120.0
        assert metadata['width'] == 1920
        assert metadata['height'] == 1080
        assert metadata['video_codec'] == 'h264'
        assert metadata['audio_codec'] == 'aac'
        assert metadata['frame_rate'] == 30.0
    
    def test_analyze_video_quality_high_quality(self):
        """Test video quality analysis for high quality video."""
        metadata = {
            'width': 1920,
            'height': 1080,
            'bit_rate': 8000000,  # 8 Mbps
            'duration': 60.0
        }
        
        quality = analyze_video_quality(metadata)
        
        assert quality['resolution_quality'] == 'high'
        assert quality['aspect_ratio'] == 'landscape'
        assert quality['bitrate_quality'] == 'high'
        assert quality['overall_quality'] == 'high'
    
    def test_analyze_video_quality_low_quality(self):
        """Test video quality analysis for low quality video."""
        metadata = {
            'width': 640,
            'height': 480,
            'bit_rate': 500000,  # 0.5 Mbps
            'duration': 60.0
        }
        
        quality = analyze_video_quality(metadata)
        
        assert quality['resolution_quality'] == 'low'
        assert quality['bitrate_quality'] == 'low'
        assert quality['overall_quality'] == 'low'
        assert len(quality['recommendations']) > 0
    
    @patch('streamgank_modular.video.video_processor.extract_video_metadata')
    @patch('streamgank_modular.video.video_processor.analyze_video_quality')
    def test_batch_analyze_videos(self, mock_analyze, mock_extract):
        """Test batch video analysis."""
        # Setup mocks
        mock_extract.side_effect = [
            {'duration': 120.0, 'width': 1920, 'height': 1080},
            {'duration': 90.0, 'width': 1280, 'height': 720},
            None  # Third video fails
        ]
        mock_analyze.side_effect = [
            {'overall_quality': 'high'},
            {'overall_quality': 'medium'}
        ]
        
        video_urls = [
            'https://example.com/video1.mp4',
            'https://example.com/video2.mp4',
            'https://example.com/video3.mp4'
        ]
        
        result = batch_analyze_videos(video_urls)
        
        assert len(result) == 3
        assert 'metadata' in result[video_urls[0]]
        assert 'quality' in result[video_urls[0]]
        assert 'metadata' in result[video_urls[1]]
        assert 'error' in result[video_urls[2]]


class TestVideoIntegration:
    """Test integration between video modules."""
    
    @patch('streamgank_modular.video.composition_builder.calculate_video_durations')
    @patch('streamgank_modular.video.composition_builder.estimate_clip_durations')
    @patch('streamgank_modular.video.creatomate_client.send_creatomate_request')
    def test_composition_to_creatomate_integration(self, mock_send, mock_clip_durations, mock_video_durations):
        """Test integration from composition building to Creatomate rendering."""
        # Setup mocks for composition building
        mock_video_durations.return_value = {
            'heygen1': 8.0, 'heygen2': 7.5, 'heygen3': 9.0
        }
        mock_clip_durations.return_value = {
            'clip1': 12.0, 'clip2': 11.5, 'clip3': 13.0
        }
        
        # Mock Creatomate request
        mock_send.return_value = 'render_id_123'
        
        # Build composition
        heygen_urls = {'movie1': 'https://example.com/heygen1.mp4'}
        composition = build_video_composition(heygen_urls)
        
        # Send to Creatomate
        if composition:
            render_id = send_creatomate_request(composition)
        
        assert composition is not None
        assert render_id == 'render_id_123'
        mock_send.assert_called_once_with(composition)
    
    @patch('streamgank_modular.video.scroll_generator.generate_scroll_video')
    @patch('streamgank_modular.video.composition_builder.build_video_composition')
    def test_scroll_video_in_composition(self, mock_build_composition, mock_generate_scroll):
        """Test integration of scroll video into composition."""
        # Mock scroll video generation
        mock_generate_scroll.return_value = 'https://cloudinary.com/scroll.mp4'
        
        # Mock composition building (should include scroll video)
        mock_build_composition.return_value = {
            'width': 1080,
            'height': 1920,
            'elements': [
                {'type': 'video', 'source': 'https://cloudinary.com/scroll.mp4'}
            ]
        }
        
        # Generate scroll video
        scroll_url = mock_generate_scroll('US', 'Horror', 'Netflix', 'Movies')
        
        # Build composition with scroll video
        composition = mock_build_composition(
            heygen_video_urls={'movie1': 'test'},
            scroll_video_url=scroll_url
        )
        
        assert scroll_url == 'https://cloudinary.com/scroll.mp4'
        assert composition is not None
        assert len(composition['elements']) > 0
    
    @patch('streamgank_modular.video.video_processor.validate_video_urls')
    @patch('streamgank_modular.video.creatomate_client.create_creatomate_video')
    def test_url_validation_before_creation(self, mock_create, mock_validate):
        """Test URL validation before video creation."""
        # Mock validation success
        mock_validate.return_value = {'is_valid': True, 'errors': []}
        mock_create.return_value = 'render_id_123'
        
        heygen_urls = {'movie1': 'https://example.com/video1.mp4'}
        movie_covers = ['https://example.com/poster1.jpg']
        
        # This should trigger validation inside create_creatomate_video
        result = mock_create(heygen_urls, movie_covers)
        
        assert result == 'render_id_123'
    
    def test_timing_strategy_with_video_durations(self):
        """Test timing strategy calculation with real video durations."""
        # Use real strategy classes
        strategy = HeyGenLast3sStrategy()
        
        # Realistic video durations
        heygen_durations = {'heygen1': 8.2, 'heygen2': 6.8, 'heygen3': 9.5}
        clip_durations = {'clip1': 12.3, 'clip2': 11.7, 'clip3': 13.1}
        
        timing = strategy.calculate_timing(heygen_durations, clip_durations)
        
        # Verify timing makes sense
        assert timing['poster1']['time'] >= 1.0  # After intro
        assert timing['poster1']['duration'] <= 3.0  # Max poster duration
        assert timing['poster2']['time'] > timing['poster1']['time']  # Sequential
        assert timing['poster3']['time'] > timing['poster2']['time']  # Sequential