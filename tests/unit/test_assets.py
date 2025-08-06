"""
Unit Tests for StreamGank Assets Module

Tests asset processing including poster generation, clip processing,
Cloudinary uploads, and media utilities.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from PIL import Image

# Import modules to test
from streamgank_modular.assets.poster_generator import (
    create_enhanced_movie_poster,
    create_enhanced_movie_posters,
    generate_poster_metadata,
    apply_cinematic_effects
)

from streamgank_modular.assets.clip_processor import (
    extract_youtube_video_id,
    download_youtube_trailer,
    extract_highlight_clip,
    process_movie_trailers_to_clips,
    batch_extract_clips
)

from streamgank_modular.assets.cloudinary_uploader import (
    upload_poster_to_cloudinary,
    upload_clip_to_cloudinary,
    get_cloudinary_transformation,
    batch_upload_assets,
    get_cloudinary_config_status
)

from streamgank_modular.assets.media_utils import (
    validate_image_url,
    validate_video_file,
    get_video_duration,
    get_image_dimensions,
    get_fallback_poster,
    clean_temp_files,
    detect_media_format,
    is_portrait_format
)


class TestPosterGenerator:
    """Test poster generation functionality."""
    
    def test_generate_poster_metadata(self):
        """Test poster metadata generation."""
        movie_data = {
            'title': 'Test Horror Movie',
            'year': 2023,
            'platform': 'Netflix',
            'genres': ['Horror', 'Thriller'],
            'imdb_score': 8.5,
            'runtime': '120 min',
            'poster_url': 'https://example.com/poster.jpg'
        }
        
        metadata = generate_poster_metadata(movie_data)
        
        assert metadata['title'] == 'Test Horror Movie'
        assert metadata['dimensions'] == (1080, 1920)
        assert metadata['format'] == '9:16 portrait'
        assert metadata['has_poster_url'] is True
        assert metadata['metadata_items'] > 0
        assert 'thematic_colors' in metadata
    
    def test_generate_poster_metadata_missing_data(self):
        """Test poster metadata generation with missing data."""
        movie_data = {}
        
        metadata = generate_poster_metadata(movie_data)
        
        assert metadata == {}
    
    @patch('streamgank_modular.assets.poster_generator.ensure_directory')
    @patch('streamgank_modular.assets.poster_generator._download_and_process_poster')
    @patch('streamgank_modular.assets.poster_generator.get_fallback_poster')
    @patch('streamgank_modular.assets.poster_generator.Image')
    def test_create_enhanced_movie_poster_success(self, mock_image, mock_fallback, mock_download, mock_ensure_dir):
        """Test successful enhanced poster creation."""
        # Setup mocks
        mock_ensure_dir.return_value = True
        mock_poster = MagicMock()
        mock_poster.size = (600, 900)
        mock_download.return_value = mock_poster
        
        mock_canvas = MagicMock()
        mock_image.new.return_value = mock_canvas
        
        movie_data = {
            'title': 'Test Movie',
            'year': 2023,
            'platform': 'Netflix',
            'genres': ['Horror'],
            'imdb_score': 8.0,
            'poster_url': 'https://example.com/poster.jpg'
        }
        
        with patch('streamgank_modular.assets.poster_generator._apply_thematic_background', return_value=mock_canvas):
            with patch('streamgank_modular.assets.poster_generator._calculate_poster_positioning', return_value={'size': (600, 900), 'position': (240, 100)}):
                with patch('streamgank_modular.assets.poster_generator._apply_cinematic_effects', return_value=mock_canvas):
                    with patch('streamgank_modular.assets.poster_generator._add_metadata_panel', return_value=mock_canvas):
                        with patch('streamgank_modular.assets.poster_generator._save_enhanced_poster', return_value='/test/poster.png'):
                            
                            result = create_enhanced_movie_poster(movie_data, 'test_output')
                            
                            assert result == '/test/poster.png'
                            mock_ensure_dir.assert_called_once_with('test_output')
    
    def test_create_enhanced_movie_poster_no_title(self):
        """Test poster creation with missing title."""
        movie_data = {'year': 2023}
        
        result = create_enhanced_movie_poster(movie_data)
        
        assert result is None
    
    @patch('streamgank_modular.assets.poster_generator.create_enhanced_movie_poster')
    @patch('streamgank_modular.assets.poster_generator.upload_poster_to_cloudinary')
    @patch('streamgank_modular.assets.poster_generator.ensure_directory')
    def test_create_enhanced_movie_posters_batch(self, mock_ensure_dir, mock_upload, mock_create):
        """Test batch poster creation."""
        # Setup mocks
        mock_ensure_dir.return_value = True
        mock_create.return_value = '/test/poster1.png'
        mock_upload.return_value = 'https://cloudinary.com/poster1.jpg'
        
        movie_data = [
            {'title': 'Movie 1', 'id': 1},
            {'title': 'Movie 2', 'id': 2}
        ]
        
        result = create_enhanced_movie_posters(movie_data, max_movies=2)
        
        assert len(result) == 2
        assert 'Movie 1' in result
        assert 'Movie 2' in result
        assert result['Movie 1'] == 'https://cloudinary.com/poster1.jpg'
    
    @patch('os.path.exists')
    def test_apply_cinematic_effects(self, mock_exists):
        """Test cinematic effects application."""
        mock_exists.return_value = True
        
        # Create mock image
        with patch('PIL.Image.open') as mock_open:
            mock_image = MagicMock()
            mock_open.return_value = mock_image
            
            result = apply_cinematic_effects('/test/image.jpg', '/test/output.jpg')
            
            # Should return output path on success
            assert result == '/test/output.jpg'
    
    def test_apply_cinematic_effects_missing_file(self):
        """Test cinematic effects with missing file."""
        result = apply_cinematic_effects('/nonexistent/image.jpg')
        
        assert result is None


class TestClipProcessor:
    """Test clip processing functionality."""
    
    def test_extract_youtube_video_id_standard_url(self):
        """Test YouTube video ID extraction from standard URL."""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        video_id = extract_youtube_video_id(url)
        
        assert video_id == 'dQw4w9WgXcQ'
    
    def test_extract_youtube_video_id_short_url(self):
        """Test YouTube video ID extraction from short URL."""
        url = 'https://youtu.be/dQw4w9WgXcQ'
        video_id = extract_youtube_video_id(url)
        
        assert video_id == 'dQw4w9WgXcQ'
    
    def test_extract_youtube_video_id_embed_url(self):
        """Test YouTube video ID extraction from embed URL."""
        url = 'https://www.youtube.com/embed/dQw4w9WgXcQ'
        video_id = extract_youtube_video_id(url)
        
        assert video_id == 'dQw4w9WgXcQ'
    
    def test_extract_youtube_video_id_invalid_url(self):
        """Test YouTube video ID extraction from invalid URL."""
        url = 'https://example.com/not-youtube'
        video_id = extract_youtube_video_id(url)
        
        assert video_id is None
    
    @patch('streamgank_modular.assets.clip_processor.is_valid_youtube_url')
    def test_download_youtube_trailer_invalid_url(self, mock_is_valid):
        """Test trailer download with invalid URL."""
        mock_is_valid.return_value = False
        
        result = download_youtube_trailer('invalid-url')
        
        assert result is None
    
    @patch('streamgank_modular.assets.clip_processor.is_valid_youtube_url')
    @patch('streamgank_modular.assets.clip_processor.extract_youtube_video_id')
    def test_download_youtube_trailer_no_video_id(self, mock_extract_id, mock_is_valid):
        """Test trailer download when video ID extraction fails."""
        mock_is_valid.return_value = True
        mock_extract_id.return_value = None
        
        result = download_youtube_trailer('https://youtube.com/watch?v=invalid')
        
        assert result is None
    
    @patch('streamgank_modular.assets.clip_processor.validate_video_file')
    def test_extract_highlight_clip_invalid_video(self, mock_validate):
        """Test highlight extraction with invalid video file."""
        mock_validate.return_value = False
        
        result = extract_highlight_clip('/path/to/invalid/video.mp4')
        
        assert result is None
    
    @patch('streamgank_modular.assets.clip_processor.validate_video_file')
    @patch('streamgank_modular.assets.clip_processor.get_video_duration')
    @patch('streamgank_modular.assets.clip_processor.ensure_directory')
    @patch('streamgank_modular.assets.clip_processor._extract_clip_with_ffmpeg')
    def test_extract_highlight_clip_success(self, mock_ffmpeg, mock_ensure_dir, mock_duration, mock_validate):
        """Test successful highlight extraction."""
        # Setup mocks
        mock_validate.side_effect = [True, True]  # Initial validation and final validation
        mock_duration.return_value = 120.0  # 2 minutes
        mock_ensure_dir.return_value = True
        mock_ffmpeg.return_value = True
        
        result = extract_highlight_clip('/test/video.mp4', clip_duration=15, output_dir='test_clips')
        
        assert result is not None
        assert 'highlight' in result
        mock_ffmpeg.assert_called_once()
    
    @patch('streamgank_modular.assets.clip_processor.ensure_directory')
    @patch('streamgank_modular.assets.clip_processor.download_youtube_trailer')
    @patch('streamgank_modular.assets.clip_processor.extract_highlight_clip')
    @patch('streamgank_modular.assets.clip_processor.upload_clip_to_cloudinary')
    def test_process_movie_trailers_to_clips(self, mock_upload, mock_extract, mock_download, mock_ensure_dir):
        """Test batch trailer processing."""
        # Setup mocks
        mock_ensure_dir.return_value = True
        mock_download.return_value = '/temp/trailer.mp4'
        mock_extract.return_value = '/temp/clip.mp4'
        mock_upload.return_value = 'https://cloudinary.com/clip.mp4'
        
        movie_data = [
            {'title': 'Movie 1', 'id': 1, 'trailer_url': 'https://youtube.com/watch?v=test1'},
            {'title': 'Movie 2', 'id': 2, 'trailer_url': 'https://youtube.com/watch?v=test2'}
        ]
        
        result = process_movie_trailers_to_clips(movie_data, max_movies=2)
        
        assert len(result) == 2
        assert 'Movie 1' in result
        assert 'Movie 2' in result
        assert result['Movie 1'] == 'https://cloudinary.com/clip.mp4'
    
    @patch('streamgank_modular.assets.clip_processor.ensure_directory')
    @patch('streamgank_modular.assets.clip_processor.extract_highlight_clip')
    def test_batch_extract_clips(self, mock_extract, mock_ensure_dir):
        """Test batch clip extraction."""
        # Setup mocks
        mock_ensure_dir.return_value = True
        mock_extract.side_effect = ['/clips/clip1.mp4', '/clips/clip2.mp4']
        
        video_paths = ['/videos/video1.mp4', '/videos/video2.mp4']
        
        result = batch_extract_clips(video_paths, 'batch_clips')
        
        assert len(result) == 2
        assert result['/videos/video1.mp4'] == '/clips/clip1.mp4'
        assert result['/videos/video2.mp4'] == '/clips/clip2.mp4'


class TestCloudinaryUploader:
    """Test Cloudinary upload functionality."""
    
    @patch.dict('os.environ', {
        'CLOUDINARY_CLOUD_NAME': 'test_cloud',
        'CLOUDINARY_API_KEY': 'test_key',
        'CLOUDINARY_API_SECRET': 'test_secret'
    })
    def test_get_cloudinary_config_status_configured(self):
        """Test Cloudinary configuration status when properly configured."""
        with patch('cloudinary.api.ping') as mock_ping:
            mock_ping.return_value = True
            
            status = get_cloudinary_config_status()
            
            assert status['configured'] is True
            assert status['cloud_name'] == 'test_cloud'
            assert status['api_key_set'] is True
            assert status['api_secret_set'] is True
            assert status['connection_test'] is True
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_cloudinary_config_status_not_configured(self):
        """Test Cloudinary configuration status when not configured."""
        status = get_cloudinary_config_status()
        
        assert status['configured'] is False
        assert status['cloud_name'] is None
        assert status['api_key_set'] is False
        assert status['api_secret_set'] is False
        assert status['connection_test'] is False
    
    def test_get_cloudinary_transformation_youtube_shorts(self):
        """Test Cloudinary transformation for YouTube Shorts."""
        transformation = get_cloudinary_transformation('youtube_shorts')
        
        assert transformation['width'] == 1080
        assert transformation['height'] == 1920
        assert transformation['crop'] == 'fill'
        assert transformation['gravity'] == 'center'
    
    def test_get_cloudinary_transformation_fit_mode(self):
        """Test Cloudinary transformation for fit mode."""
        transformation = get_cloudinary_transformation('fit')
        
        assert transformation['width'] == 1080
        assert transformation['height'] == 1920
        assert transformation['crop'] == 'fit'
        assert transformation['background'] == 'black'
    
    def test_get_cloudinary_transformation_unknown_mode(self):
        """Test Cloudinary transformation for unknown mode (should default to fit)."""
        transformation = get_cloudinary_transformation('unknown_mode')
        
        # Should default to fit mode
        assert transformation['crop'] == 'fit'
        assert transformation['width'] == 1080
        assert transformation['height'] == 1920
    
    @patch('streamgank_modular.assets.cloudinary_uploader._ensure_cloudinary_config')
    def test_upload_poster_to_cloudinary_not_configured(self, mock_ensure_config):
        """Test poster upload when Cloudinary is not configured."""
        mock_ensure_config.return_value = False
        
        result = upload_poster_to_cloudinary('/test/poster.jpg', 'Test Movie')
        
        assert result is None
    
    @patch('streamgank_modular.assets.cloudinary_uploader._ensure_cloudinary_config')
    @patch('streamgank_modular.assets.cloudinary_uploader.validate_file_path')
    def test_upload_poster_to_cloudinary_invalid_file(self, mock_validate, mock_ensure_config):
        """Test poster upload with invalid file."""
        mock_ensure_config.return_value = True
        mock_validate.return_value = {'is_valid': False}
        
        result = upload_poster_to_cloudinary('/invalid/poster.jpg', 'Test Movie')
        
        assert result is None
    
    @patch('streamgank_modular.assets.cloudinary_uploader._ensure_cloudinary_config')
    @patch('streamgank_modular.assets.cloudinary_uploader.validate_file_path')
    @patch('streamgank_modular.assets.cloudinary_uploader.get_file_info')
    @patch('cloudinary.uploader.upload')
    def test_upload_poster_to_cloudinary_success(self, mock_upload, mock_get_info, mock_validate, mock_ensure_config):
        """Test successful poster upload."""
        # Setup mocks
        mock_ensure_config.return_value = True
        mock_validate.return_value = {'is_valid': True}
        mock_get_info.return_value = {'size_mb': 2.5}
        mock_upload.return_value = {
            'secure_url': 'https://cloudinary.com/poster.jpg',
            'public_id': 'enhanced_posters/test_movie_123',
            'width': 1080,
            'height': 1920
        }
        
        result = upload_poster_to_cloudinary('/test/poster.jpg', 'Test Movie', '123')
        
        assert result == 'https://cloudinary.com/poster.jpg'
        mock_upload.assert_called_once()
    
    @patch('streamgank_modular.assets.cloudinary_uploader._ensure_cloudinary_config')
    @patch('streamgank_modular.assets.cloudinary_uploader.validate_file_path')
    @patch('streamgank_modular.assets.cloudinary_uploader.get_file_info')
    @patch('streamgank_modular.assets.cloudinary_uploader.get_cloudinary_transformation')
    @patch('cloudinary.uploader.upload')
    def test_upload_clip_to_cloudinary_success(self, mock_upload, mock_get_transform, mock_get_info, mock_validate, mock_ensure_config):
        """Test successful clip upload."""
        # Setup mocks
        mock_ensure_config.return_value = True
        mock_validate.return_value = {'is_valid': True}
        mock_get_info.return_value = {'size_mb': 15.2}
        mock_get_transform.return_value = {'width': 1080, 'height': 1920, 'crop': 'fill'}
        mock_upload.return_value = {
            'secure_url': 'https://cloudinary.com/clip.mp4',
            'public_id': 'movie_clips/test_movie_123_clip',
            'duration': 15.0,
            'width': 1080,
            'height': 1920
        }
        
        result = upload_clip_to_cloudinary('/test/clip.mp4', 'Test Movie', '123', 'youtube_shorts')
        
        assert result == 'https://cloudinary.com/clip.mp4'
        mock_upload.assert_called_once()
        mock_get_transform.assert_called_once_with('youtube_shorts')
    
    @patch('streamgank_modular.assets.cloudinary_uploader._ensure_cloudinary_config')
    @patch('streamgank_modular.assets.cloudinary_uploader._detect_asset_type')
    @patch('streamgank_modular.assets.cloudinary_uploader.upload_poster_to_cloudinary')
    @patch('streamgank_modular.assets.cloudinary_uploader.upload_clip_to_cloudinary')
    def test_batch_upload_assets(self, mock_upload_clip, mock_upload_poster, mock_detect_type, mock_ensure_config):
        """Test batch asset upload."""
        # Setup mocks
        mock_ensure_config.return_value = True
        mock_detect_type.side_effect = ['poster', 'clip']
        mock_upload_poster.return_value = 'https://cloudinary.com/poster.jpg'
        mock_upload_clip.return_value = 'https://cloudinary.com/clip.mp4'
        
        file_paths = ['/test/poster.jpg', '/test/clip.mp4']
        
        result = batch_upload_assets(file_paths, 'auto')
        
        assert len(result) == 2
        assert result['/test/poster.jpg'] == 'https://cloudinary.com/poster.jpg'
        assert result['/test/clip.mp4'] == 'https://cloudinary.com/clip.mp4'


class TestMediaUtils:
    """Test media utility functions."""
    
    def test_validate_image_url_valid_extension(self):
        """Test image URL validation with valid extension."""
        url = 'https://example.com/image.jpg'
        
        result = validate_image_url(url)
        
        assert result is True
    
    def test_validate_image_url_invalid_url(self):
        """Test image URL validation with invalid URL."""
        url = 'not-a-url'
        
        result = validate_image_url(url)
        
        assert result is False
    
    @patch('requests.head')
    def test_validate_image_url_content_type_check(self, mock_head):
        """Test image URL validation with content type check."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/png'}
        mock_head.return_value = mock_response
        
        url = 'https://example.com/image'  # No extension
        
        result = validate_image_url(url)
        
        assert result is True
        mock_head.assert_called_once()
    
    @patch('os.path.exists')
    def test_validate_video_file_not_exists(self, mock_exists):
        """Test video file validation when file doesn't exist."""
        mock_exists.return_value = False
        
        result = validate_video_file('/nonexistent/video.mp4')
        
        assert result is False
    
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_validate_video_file_ffprobe_success(self, mock_run, mock_exists):
        """Test video file validation with successful FFprobe."""
        mock_exists.return_value = True
        
        # Mock FFprobe response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'streams': [{'codec_type': 'video'}],
            'format': {'duration': '120.0'}
        })
        mock_run.return_value = mock_result
        
        result = validate_video_file('/test/video.mp4')
        
        assert result is True
    
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_get_video_duration_success(self, mock_run, mock_exists):
        """Test video duration extraction."""
        mock_exists.return_value = True
        
        # Mock FFprobe response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'format': {'duration': '123.45'}
        })
        mock_run.return_value = mock_result
        
        duration = get_video_duration('/test/video.mp4')
        
        assert duration == 123.45
    
    @patch('os.path.exists')
    def test_get_video_duration_file_not_exists(self, mock_exists):
        """Test video duration extraction when file doesn't exist."""
        mock_exists.return_value = False
        
        duration = get_video_duration('/nonexistent/video.mp4')
        
        assert duration is None
    
    @patch('os.path.exists')
    @patch('PIL.Image.open')
    def test_get_image_dimensions_success(self, mock_open, mock_exists):
        """Test image dimensions extraction."""
        mock_exists.return_value = True
        
        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_open.return_value.__enter__.return_value = mock_image
        
        dimensions = get_image_dimensions('/test/image.jpg')
        
        assert dimensions == (1920, 1080)
    
    def test_get_fallback_poster(self):
        """Test fallback poster generation."""
        poster = get_fallback_poster('Test Movie', 600, 900)
        
        assert isinstance(poster, Image.Image)
        assert poster.size == (600, 900)
        assert poster.mode == 'RGB'
    
    def test_get_fallback_poster_default_params(self):
        """Test fallback poster generation with default parameters."""
        poster = get_fallback_poster()
        
        assert isinstance(poster, Image.Image)
        assert poster.size == (600, 900)  # Default size
    
    @patch('os.path.exists')
    @patch('os.walk')
    @patch('shutil.rmtree')
    def test_clean_temp_files_success(self, mock_rmtree, mock_walk, mock_exists):
        """Test temporary file cleanup."""
        # Setup mocks
        mock_exists.return_value = True
        mock_walk.return_value = [('/temp', [], ['file1.txt', 'file2.txt'])]
        
        # Mock directory size calculation
        with patch('streamgank_modular.assets.media_utils._get_directory_size', return_value=1024000):
            result = clean_temp_files('/temp/dir1', '/temp/dir2')
        
        assert result['directories_cleaned'] == 2
        assert result['files_deleted'] == 0  # Function counts directories, not files
        assert result['bytes_freed'] == 2048000  # 2 * 1024000
        assert len(result['errors']) == 0
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_detect_media_format_image(self, mock_getsize, mock_exists):
        """Test media format detection for image."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024000
        
        with patch('streamgank_modular.assets.media_utils.get_image_dimensions', return_value=(1920, 1080)):
            result = detect_media_format('/test/image.jpg')
        
        assert result['exists'] is True
        assert result['type'] == 'image'
        assert result['format'] == 'jpg'
        assert result['valid'] is True
        assert result['width'] == 1920
        assert result['height'] == 1080
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_detect_media_format_video(self, mock_getsize, mock_exists):
        """Test media format detection for video."""
        mock_exists.return_value = True
        mock_getsize.return_value = 10240000
        
        with patch('streamgank_modular.assets.media_utils.validate_video_file', return_value=True):
            with patch('streamgank_modular.assets.media_utils.get_video_info', return_value={'duration': 120.0, 'width': 1920, 'height': 1080}):
                result = detect_media_format('/test/video.mp4')
        
        assert result['exists'] is True
        assert result['type'] == 'video'
        assert result['format'] == 'mp4'
        assert result['valid'] is True
        assert result['duration'] == 120.0
    
    def test_detect_media_format_not_exists(self):
        """Test media format detection for non-existent file."""
        result = detect_media_format('/nonexistent/file.jpg')
        
        assert result['exists'] is False
        assert result['type'] == 'unknown'
        assert result['valid'] is False
    
    def test_is_portrait_format_portrait(self):
        """Test portrait format detection for portrait image."""
        with patch('streamgank_modular.assets.media_utils.detect_media_format') as mock_detect:
            mock_detect.return_value = {
                'valid': True,
                'width': 1080,
                'height': 1920
            }
            
            result = is_portrait_format('/test/portrait.jpg')
            
            assert result is True
    
    def test_is_portrait_format_landscape(self):
        """Test portrait format detection for landscape image."""
        with patch('streamgank_modular.assets.media_utils.detect_media_format') as mock_detect:
            mock_detect.return_value = {
                'valid': True,
                'width': 1920,
                'height': 1080
            }
            
            result = is_portrait_format('/test/landscape.jpg')
            
            assert result is False
    
    def test_is_portrait_format_invalid_file(self):
        """Test portrait format detection for invalid file."""
        with patch('streamgank_modular.assets.media_utils.detect_media_format') as mock_detect:
            mock_detect.return_value = {'valid': False}
            
            result = is_portrait_format('/test/invalid.jpg')
            
            assert result is None


class TestAssetsIntegration:
    """Test integration between assets modules."""
    
    def test_poster_to_cloudinary_integration(self):
        """Test integration between poster generator and Cloudinary uploader."""
        # Mock successful poster creation
        with patch('streamgank_modular.assets.poster_generator.create_enhanced_movie_poster') as mock_create:
            mock_create.return_value = '/temp/poster.png'
            
            # Mock successful Cloudinary upload
            with patch('streamgank_modular.assets.poster_generator.upload_poster_to_cloudinary') as mock_upload:
                mock_upload.return_value = 'https://cloudinary.com/poster.jpg'
                
                movie_data = [{'title': 'Test Movie', 'id': 1}]
                
                result = create_enhanced_movie_posters(movie_data, max_movies=1)
                
                assert len(result) == 1
                assert 'Test Movie' in result
                assert result['Test Movie'] == 'https://cloudinary.com/poster.jpg'
    
    def test_clip_processing_chain_integration(self):
        """Test full clip processing chain integration."""
        # Mock successful trailer download
        with patch('streamgank_modular.assets.clip_processor.download_youtube_trailer') as mock_download:
            mock_download.return_value = '/temp/trailer.mp4'
            
            # Mock successful clip extraction
            with patch('streamgank_modular.assets.clip_processor.extract_highlight_clip') as mock_extract:
                mock_extract.return_value = '/temp/clip.mp4'
                
                # Mock successful Cloudinary upload
                with patch('streamgank_modular.assets.clip_processor.upload_clip_to_cloudinary') as mock_upload:
                    mock_upload.return_value = 'https://cloudinary.com/clip.mp4'
                    
                    movie_data = [{
                        'title': 'Test Movie',
                        'id': 1,
                        'trailer_url': 'https://youtube.com/watch?v=test'
                    }]
                    
                    result = process_movie_trailers_to_clips(movie_data, max_movies=1)
                    
                    assert len(result) == 1
                    assert 'Test Movie' in result
                    assert result['Test Movie'] == 'https://cloudinary.com/clip.mp4'
    
    def test_media_utils_validation_integration(self):
        """Test integration between different media validation functions."""
        # Test that video validation uses proper utilities
        with patch('os.path.exists', return_value=True):
            with patch('subprocess.run') as mock_run:
                # Mock successful FFprobe response
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({
                    'streams': [{'codec_type': 'video'}],
                    'format': {'duration': '120.0'}
                })
                mock_run.return_value = mock_result
                
                # Both functions should work with same file
                is_valid = validate_video_file('/test/video.mp4')
                duration = get_video_duration('/test/video.mp4')
                
                assert is_valid is True
                assert duration == 120.0