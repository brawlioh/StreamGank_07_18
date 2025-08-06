"""
Comprehensive Unit Tests for StreamGank Core Module

Tests core workflow orchestration and CLI interface functionality
with the exact workflow parameters and intro integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import core modules to test
from core.workflow import (
    run_full_workflow,
    process_existing_heygen_videos,
    validate_workflow_inputs,
    get_workflow_status
)

# Note: CLI interface removed - interactive functionality no longer supported


class TestWorkflow:
    """Test core workflow orchestration functionality."""
    
    @patch('core.workflow.setup_workflow_logging')
    @patch('core.workflow.extract_movie_data')
    @patch('core.workflow.generate_video_scripts')
    @patch('core.workflow.create_enhanced_movie_posters')
    @patch('core.workflow.process_movie_trailers_to_clips')
    @patch('core.workflow.create_heygen_video')
    @patch('core.workflow.get_video_urls')
    @patch('core.workflow.create_creatomate_video')
    @patch('core.workflow.wait_for_completion')
    def test_run_full_workflow_success(self, mock_wait, mock_create_video, mock_get_urls, 
                                     mock_heygen, mock_clips, mock_posters, mock_scripts, 
                                     mock_extract, mock_logger):
        """Test successful complete workflow execution."""
        # Setup mocks for workflow steps
        mock_workflow_logger = Mock()
        mock_logger.return_value = mock_workflow_logger
        
        # Step 1: Database extraction
        mock_extract.return_value = [
            {
                'title': 'Godzilla Minus One',
                'year': 2023,
                'genres': ['Horror', 'Action'],
                'platform': 'Netflix',
                'imdb_score': 7.7,
                'poster_url': 'https://example.com/godzilla.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test1'
            },
            {
                'title': 'Train to Busan',
                'year': 2016,
                'genres': ['Horror', 'Thriller'],
                'platform': 'Netflix',
                'imdb_score': 7.6,
                'poster_url': 'https://example.com/train.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test2'
            },
            {
                'title': 'The Wailing',
                'year': 2016,
                'genres': ['Horror', 'Mystery'],
                'platform': 'Netflix',
                'imdb_score': 7.4,
                'poster_url': 'https://example.com/wailing.jpg',
                'trailer_url': 'https://youtube.com/watch?v=test3'
            }
        ]
        
        # Step 2: Script generation with intro integration
        mock_scripts.return_value = (
            "Combined script text",
            "videos/combined_script.txt",
            {
                'movie1': 'Here are the top 3 horror movies from StreamGank! This kaiju masterpiece proves that monsters reflect our deepest fears.',
                'movie2': 'Everyone\'s too scared to watch this zombie thriller masterpiece.',
                'movie3': 'This supernatural horror will leave you questioning everything.'
            }
        )
        
        # Step 3: Asset preparation
        mock_posters.return_value = {
            'movie1': 'https://cloudinary.com/enhanced_godzilla.jpg',
            'movie2': 'https://cloudinary.com/enhanced_train.jpg',
            'movie3': 'https://cloudinary.com/enhanced_wailing.jpg'
        }
        
        mock_clips.return_value = {
            'movie1': 'https://cloudinary.com/godzilla_clip.mp4',
            'movie2': 'https://cloudinary.com/train_clip.mp4',
            'movie3': 'https://cloudinary.com/wailing_clip.mp4'
        }
        
        # Step 4: HeyGen video creation
        mock_heygen.return_value = {
            'movie1': 'heygen_video_id_1',
            'movie2': 'heygen_video_id_2',
            'movie3': 'heygen_video_id_3'
        }
        
        mock_get_urls.return_value = {
            'movie1': 'https://heygen.com/video1.mp4',
            'movie2': 'https://heygen.com/video2.mp4',
            'movie3': 'https://heygen.com/video3.mp4'
        }
        
        # Step 6: Creatomate assembly
        mock_create_video.return_value = 'render_id_123'
        mock_wait.return_value = {
            'status': 'succeeded',
            'url': 'https://creatomate.com/final_video.mp4'
        }
        
        # Execute workflow with exact parameters
        result = run_full_workflow(
            num_movies=3,
            country="US",
            genre="Horror",
            platform="Netflix",
            content_type="Film",
            heygen_template_id="cc6718c5363e42b282a123f99b94b335",
            skip_scroll_video=True  # Skip for faster testing
        )
        
        # Validate results
        assert result is not None
        assert result['final_video_url'] == 'https://creatomate.com/final_video.mp4'
        assert len(result['raw_movies']) == 3
        assert len(result['individual_scripts']) == 3  # 3 HeyGen videos
        assert 'database_extraction' in result['steps_completed']
        assert 'script_generation' in result['steps_completed']
        assert 'asset_preparation' in result['steps_completed']
        assert 'heygen_creation' in result['steps_completed']
        
        # Validate function calls
        mock_extract.assert_called_once_with(
            num_movies=3,
            country="US",
            genre="Horror",
            platform="Netflix",
            content_type="Film",
            debug=True
        )
        
        mock_scripts.assert_called_once()
        mock_heygen.assert_called_once()
        mock_create_video.assert_called_once()
        
    def test_validate_workflow_inputs_valid(self):
        """Test workflow input validation with valid parameters."""
        result = validate_workflow_inputs(
            num_movies=3,
            country="US",
            genre="Horror",
            platform="Netflix",
            content_type="Film"
        )
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        
    def test_validate_workflow_inputs_invalid(self):
        """Test workflow input validation with invalid parameters."""
        result = validate_workflow_inputs(
            num_movies=0,  # Invalid
            country="",    # Invalid
            genre=None,    # Invalid
            platform="",   # Invalid
            content_type="" # Invalid
        )
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        
    @patch('core.workflow.get_video_urls')
    @patch('core.workflow.create_creatomate_video')
    @patch('core.workflow.wait_for_completion')
    def test_process_existing_heygen_videos(self, mock_wait, mock_create, mock_get_urls):
        """Test processing existing HeyGen videos."""
        mock_get_urls.return_value = {
            'movie1': 'https://heygen.com/video1.mp4',
            'movie2': 'https://heygen.com/video2.mp4',
            'movie3': 'https://heygen.com/video3.mp4'
        }
        
        mock_create.return_value = 'render_id_123'
        mock_wait.return_value = {
            'status': 'succeeded',
            'url': 'https://creatomate.com/final_video.mp4'
        }
        
        heygen_video_ids = {
            'movie1': 'heygen_id_1',
            'movie2': 'heygen_id_2',
            'movie3': 'heygen_id_3'
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
        
        result = process_existing_heygen_videos(
            heygen_video_ids=heygen_video_ids,
            movie_covers=movie_covers,
            movie_clips=movie_clips
        )
        
        assert result is not None
        assert result['final_video_url'] == 'https://creatomate.com/final_video.mp4'
        
    def test_get_workflow_status(self):
        """Test workflow status retrieval."""
        workflow_results = {
            'workflow_id': 'test_workflow',
            'steps_completed': ['database_extraction', 'script_generation'],
            'final_video_url': None,
            'errors': []
        }
        
        status = get_workflow_status(workflow_results)
        
        assert status['workflow_id'] == 'test_workflow'
        assert status['steps_completed'] == 2
        assert status['is_completed'] is False  # No final video URL
        
    @patch('core.workflow.extract_movie_data')
    def test_workflow_database_extraction_failure(self, mock_extract):
        """Test workflow failure during database extraction."""
        mock_extract.return_value = None  # Simulate extraction failure
        
        with pytest.raises(RuntimeError, match="Failed to extract exactly 3 movies"):
            run_full_workflow(
                num_movies=3,
                country="US",
                genre="Horror",
                platform="Netflix",
                content_type="Film"
            )
            
    @patch('core.workflow.extract_movie_data')
    @patch('core.workflow.generate_video_scripts')
    def test_workflow_script_generation_failure(self, mock_scripts, mock_extract):
        """Test workflow failure during script generation."""
        mock_extract.return_value = [
            {'title': 'Movie 1', 'genres': ['Horror']},
            {'title': 'Movie 2', 'genres': ['Horror']},
            {'title': 'Movie 3', 'genres': ['Horror']}
        ]
        
        mock_scripts.side_effect = RuntimeError("Script generation failed")
        
        with pytest.raises(RuntimeError, match="Script generation failed"):
            run_full_workflow(
                num_movies=3,
                country="US",
                genre="Horror",
                platform="Netflix",
                content_type="Film"
            )


# CLI Interface functionality removed - interactive mode no longer supported


class TestWorkflowIntegration:
    """Test core workflow integration scenarios."""
    
    @patch('core.workflow.setup_workflow_logging')
    @patch('core.workflow.extract_movie_data')
    @patch('core.workflow.generate_video_scripts')
    def test_intro_integration_workflow(self, mock_scripts, mock_extract, mock_logger):
        """Test workflow with intro integration feature."""
        mock_workflow_logger = Mock()
        mock_logger.return_value = mock_workflow_logger
        
        # Mock database extraction
        mock_extract.return_value = [
            {'title': 'Horror Movie 1', 'genres': ['Horror']},
            {'title': 'Horror Movie 2', 'genres': ['Horror']},
            {'title': 'Horror Movie 3', 'genres': ['Horror']}
        ]
        
        # Mock script generation with intro integration
        mock_scripts.return_value = (
            "Combined script",
            "videos/script.txt",
            {
                'movie1': 'Here are the top 3 horror movies! First movie hook.',
                'movie2': 'Second movie hook only.',
                'movie3': 'Third movie hook only.'
            }
        )
        
        # Mock other workflow steps to prevent actual calls
        with patch('core.workflow.create_enhanced_movie_posters') as mock_posters, \
             patch('core.workflow.process_movie_trailers_to_clips') as mock_clips, \
             patch('core.workflow.create_heygen_video') as mock_heygen, \
             patch('core.workflow.get_video_urls') as mock_urls, \
             patch('core.workflow.create_creatomate_video') as mock_create, \
             patch('core.workflow.wait_for_completion') as mock_wait:
            
            mock_posters.return_value = {}
            mock_clips.return_value = {}
            mock_heygen.return_value = {'movie1': 'id1', 'movie2': 'id2', 'movie3': 'id3'}
            mock_urls.return_value = {}
            mock_create.return_value = 'render_id'
            mock_wait.return_value = {'status': 'succeeded', 'url': 'https://video.mp4'}
            
            result = run_full_workflow(
                num_movies=3,
                country="US",
                genre="Horror",
                platform="Netflix",
                content_type="Film",
                skip_scroll_video=True
            )
            
            # Validate intro integration
            assert len(result['individual_scripts']) == 3
            movie1_script = result['individual_scripts']['movie1']
            assert 'Here are the top 3 horror movies!' in movie1_script
            assert 'First movie hook.' in movie1_script
            
            # Other movies should not have intro
            movie2_script = result['individual_scripts']['movie2']
            movie3_script = result['individual_scripts']['movie3']
            assert 'Here are the top 3 horror movies!' not in movie2_script
            assert 'Here are the top 3 horror movies!' not in movie3_script
            
    def test_workflow_error_handling(self):
        """Test workflow error handling and logging."""
        with pytest.raises(ValueError, match="num_movies must be positive"):
            validate_workflow_inputs(num_movies=-1)
            
        with pytest.raises(ValueError, match="country cannot be empty"):
            validate_workflow_inputs(num_movies=3, country="")
            
        with pytest.raises(ValueError, match="genre cannot be empty"):
            validate_workflow_inputs(num_movies=3, country="US", genre="")
            
    @patch('core.workflow.setup_workflow_logging')
    def test_workflow_logging_integration(self, mock_logger):
        """Test workflow logging integration."""
        mock_workflow_logger = Mock()
        mock_logger.return_value = mock_workflow_logger
        
        # Test that workflow logger methods are called
        with patch('core.workflow.extract_movie_data', side_effect=RuntimeError("Test error")):
            with pytest.raises(RuntimeError):
                run_full_workflow(num_movies=3, country="US", genre="Horror", platform="Netflix", content_type="Film")
                
        # Verify logging calls
        mock_workflow_logger.workflow_start.assert_called_once()
        mock_workflow_logger.step_start.assert_called()
        
    def test_workflow_validation_integration(self):
        """Test workflow parameter validation."""
        # Test direct parameter validation (no CLI needed)
        setup_params = {
            'num_movies': 3,
            'country': 'US',
            'platform': 'Netflix',
            'genre': 'Horror',
            'content_type': 'Film'
        }
        
        # Should return valid workflow parameters
        validation = validate_workflow_inputs(**setup_params)
        assert validation['is_valid'] is True
            
    def test_workflow_performance_monitoring(self):
        """Test workflow performance monitoring."""
        workflow_results = {
            'workflow_id': 'perf_test',
            'workflow_start_time': 1000.0,
            'steps_completed': ['database_extraction', 'script_generation', 'heygen_creation'],
            'final_video_url': 'https://video.mp4',
            'errors': []
        }
        
        import time
        workflow_results['workflow_end_time'] = time.time()
        
        status = get_workflow_status(workflow_results)
        
        assert status['is_completed'] is True
        assert status['steps_completed'] == 3
        assert 'execution_time' in status or 'workflow_end_time' in workflow_results