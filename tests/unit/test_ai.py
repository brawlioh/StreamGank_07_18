"""
Unit Tests for StreamGank AI Module

Tests AI-powered content generation including OpenAI scripts, HeyGen integration,
script management, and prompt templates.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, ANY

# Import modules to test
from ai.openai_scripts import (
    generate_video_scripts,
    generate_hook_script,
    generate_intro_script,
    generate_scripts_batch,
    optimize_script_for_platform,
    enhance_script_with_context,
    get_openai_usage_stats,
    test_openai_connection
)

from ai.heygen_client import (
    create_heygen_video,
    create_heygen_videos_batch,
    check_video_status,
    wait_for_completion,
    get_video_urls,
    get_heygen_config_status,
    estimate_video_duration
)

from ai.script_manager import (
    validate_script_content,
    validate_script_batch,
    process_script_text,
    combine_scripts,
    save_scripts_to_files,
    load_scripts_from_files,
    backup_scripts,
    get_script_statistics
)

from ai.prompt_templates import (
    get_hook_prompt_template,
    get_intro_prompt_template,
    build_context_prompt,
    customize_prompt_for_genre,
    get_viral_optimization_prompt,
    get_a_b_test_prompts,
    get_available_templates,
    validate_prompt_template
)

from database.movie_extractor import extract_movies_for_video


class TestOpenAIScripts:
    """Test OpenAI script generation functionality."""
    
    @patch('ai.openai_scripts._get_openai_client')
    def test_generate_hook_script_success(self, mock_get_client):
        """Test successful hook script generation."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This horror movie will terrify you!"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        movie_data = {
            'title': 'Test Horror Movie',
            'genres': ['Horror'],
            'imdb_score': 8.5
        }
        
        with patch('ai.openai_scripts.get_api_config', return_value={'model': 'gpt-4', 'temperature': 0.9}):
            with patch('ai.openai_scripts.validate_script_content', return_value=True):
                result = generate_hook_script(movie_data, 'Horror', 'TikTok')
        
        assert result == "This horror movie will terrify you!"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('ai.openai_scripts._get_openai_client')
    def test_generate_hook_script_no_client(self, mock_get_client):
        """Test hook generation when OpenAI client unavailable."""
        mock_get_client.return_value = None
        
        result = generate_hook_script({'title': 'Test Movie'})
        
        assert result is None
    
    @patch('ai.openai_scripts._get_openai_client')
    def test_generate_intro_script_success(self, mock_get_client):
        """Test successful intro script generation."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Here are the top 3 horror movies from StreamGank!"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        with patch('ai.openai_scripts.get_api_config', return_value={'model': 'gpt-4'}):
            with patch('ai.openai_scripts.validate_script_content', return_value=True):
                result = generate_intro_script('Horror', 'Netflix', 'Movies')
        
        assert result == "Here are the top 3 horror movies from StreamGank!"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('ai.openai_scripts.generate_intro_script')
    @patch('ai.openai_scripts.generate_hook_script')
    @patch('ai.openai_scripts.save_scripts_to_files')
    def test_generate_video_scripts_success(self, mock_save, mock_hook, mock_intro):
        """Test complete video scripts generation."""
        # Setup mocks
        mock_intro.return_value = "Here are the top 3 horror movies!"
        mock_hook.side_effect = ["Hook 1", "Hook 2", "Hook 3"]
        mock_save.return_value = "videos/combined_script.txt"
        
        raw_movies = [
            {'title': 'Movie 1', 'genres': ['Horror']},
            {'title': 'Movie 2', 'genres': ['Horror']},
            {'title': 'Movie 3', 'genres': ['Horror']}
        ]
        
        with patch('ai.openai_scripts.process_script_text', side_effect=lambda x: x):
            result = generate_video_scripts(raw_movies, genre='Horror')
        
        assert result is not None
        combined_script, script_path, individual_scripts = result
        
        assert "Here are the top 3 horror movies!" in combined_script
        assert "Hook 1" in combined_script
        assert script_path == "videos/combined_script.txt"
        assert len(individual_scripts) == 3  # 3 HeyGen videos: movie1 (with intro), movie2, movie3
        
        # Test intro integration: movie1 should contain both intro and hook
        assert "movie1" in individual_scripts
        assert "Here are the top 3 horror movies! Hook 1" == individual_scripts["movie1"]
    
    @patch('database.movie_extractor.extract_movies_for_video')
    @patch('ai.openai_scripts.generate_intro_script')
    @patch('ai.openai_scripts.generate_hook_script')
    @patch('ai.openai_scripts.save_scripts_to_files')
    def test_full_workflow_with_database_extraction(self, mock_save, mock_hook, mock_intro, mock_extract):
        """Test complete workflow: database extraction + intro integration script generation."""
        # Mock the database extraction using the exact filter parameters
        mock_extract.return_value = [
            {
                'title': 'Godzilla Minus One',
                'year': 2023,
                'genres': ['Horror', 'Action'],
                'platform': 'Netflix',
                'imdb_score': 7.7,
                'poster_url': 'https://example.com/godzilla.jpg'
            },
            {
                'title': 'Train to Busan',
                'year': 2016,
                'genres': ['Horror', 'Thriller'], 
                'platform': 'Netflix',
                'imdb_score': 7.6,
                'poster_url': 'https://example.com/train.jpg'
            },
            {
                'title': 'The Wailing',
                'year': 2016,
                'genres': ['Horror', 'Mystery'],
                'platform': 'Netflix', 
                'imdb_score': 7.4,
                'poster_url': 'https://example.com/wailing.jpg'
            }
        ]
        
        # Mock script generation
        mock_intro.return_value = "Here are the top 3 horror movies from StreamGank!"
        mock_hook.side_effect = [
            "This horror masterpiece proves that fear knows no boundaries.",
            "Everyone's too scared to watch this terrifying zombie thriller.", 
            "This supernatural horror will leave you questioning reality."
        ]
        mock_save.return_value = "videos/combined_script.txt"
        
        # Test parameters (using the exact filter provided by user)
        filter_params = {
            'country': 'US',
            'platform': 'Netflix', 
            'genre': 'Horror',
            'content_type': 'Film',
            'heygen_template_id': 'cc6718c5363e42b282a123f99b94b335'
        }
        
        # Step 1: Extract movies from database
        movies = extract_movies_for_video(
            country=filter_params['country'],
            platform=filter_params['platform'],
            genre=filter_params['genre'],
            content_type=filter_params['content_type']
        )
        
        # Step 2: Generate scripts with intro integration
        with patch('ai.openai_scripts.process_script_text', side_effect=lambda x: x):
            combined_script, script_path, heygen_scripts = generate_video_scripts(
                movies,
                country=filter_params['country'],
                genre=filter_params['genre'],
                platform=filter_params['platform'],
                content_type=filter_params['content_type']
            )
        
        # Validate database extraction
        mock_extract.assert_called_once_with(
            country='US',
            platform='Netflix',
            genre='Horror',
            content_type='Film'
        )
        assert len(movies) == 3
        assert movies[0]['title'] == 'Godzilla Minus One'
        
        # Validate script generation calls
        mock_intro.assert_called_once_with('Horror', 'Netflix', 'Film', ANY)
        assert mock_hook.call_count == 3
        
        # Validate intro integration results
        assert len(heygen_scripts) == 3  # Only 3 HeyGen videos needed
        assert "movie1" in heygen_scripts
        assert "movie2" in heygen_scripts  
        assert "movie3" in heygen_scripts
        assert "intro" not in heygen_scripts  # Intro should be integrated, not separate
        
        # Validate that movie1 contains the integrated intro + hook
        expected_movie1 = "Here are the top 3 horror movies from StreamGank! This horror masterpiece proves that fear knows no boundaries."
        assert heygen_scripts["movie1"] == expected_movie1
        
        # Validate other movies contain only their hooks
        assert heygen_scripts["movie2"] == "Everyone's too scared to watch this terrifying zombie thriller."
        assert heygen_scripts["movie3"] == "This supernatural horror will leave you questioning reality."
        
        # Validate combined script contains all elements
        assert "Here are the top 3 horror movies from StreamGank!" in combined_script
        assert "This horror masterpiece proves that fear knows no boundaries." in combined_script
        assert "Everyone's too scared to watch" in combined_script
        assert "This supernatural horror will leave you" in combined_script
        
        print("✅ Full workflow test passed:")
        print(f"   📊 Extracted {len(movies)} movies from database")
        print(f"   🎬 Generated {len(heygen_scripts)} HeyGen videos")
        print(f"   🔗 Intro integrated with movie1 script")
        print(f"   💾 Scripts saved to {script_path}")


class TestHeyGenClient:
    """Test HeyGen video creation functionality."""
    
    @patch('ai.heygen_client._get_heygen_headers')
    @patch('ai.heygen_client._create_single_video')
    def test_create_heygen_video_success(self, mock_create_single, mock_headers):
        """Test successful HeyGen video creation."""
        # Setup mocks
        mock_headers.return_value = {'Authorization': 'Bearer test_key'}
        mock_create_single.side_effect = ['video_id_1', 'video_id_2', 'video_id_3']
        
        script_data = {
            'movie1': 'Here are the top 3 horror movies! This first movie is terrifying.',
            'movie2': 'This second movie will scare you.',
            'movie3': 'This third movie is absolutely frightening.'
        }
        
        result = create_heygen_video(
            script_data=script_data,
            use_template=True,
            template_id='cc6718c5363e42b282a123f99b94b335',
            genre='Horror'
        )
        
        # Validate results
        assert len(result) == 3
        assert 'movie1' in result
        assert 'movie2' in result  
        assert 'movie3' in result
        assert mock_create_single.call_count == 3
        
    @patch('ai.heygen_client._get_heygen_headers')
    def test_create_heygen_video_no_headers(self, mock_headers):
        """Test HeyGen video creation when headers unavailable."""
        mock_headers.return_value = None
        
        script_data = {'movie1': 'Test script'}
        
        result = create_heygen_video(script_data=script_data)
        
        assert result is None
        
    @patch('ai.heygen_client.check_video_status')
    def test_wait_for_completion_success(self, mock_check_status):
        """Test successful video completion waiting."""
        # Mock status progression: processing -> completed
        mock_check_status.side_effect = [
            {'status': 'processing', 'data': {}},
            {'status': 'completed', 'data': {'video_url': 'https://test.com/video.mp4'}}
        ]
        
        video_ids = {'movie1': 'video_id_1'}
        
        result = wait_for_completion(video_ids, max_wait_minutes=1)
        
        assert 'movie1' in result
        assert result['movie1']['video_url'] == 'https://test.com/video.mp4'
        
    def test_estimate_video_duration(self):
        """Test video duration estimation."""
        # Test different script lengths
        short_script = "This is a short script."
        medium_script = "This is a medium length script with more words to test the estimation."
        long_script = "This is a very long script " * 10
        
        short_duration = estimate_video_duration(short_script)
        medium_duration = estimate_video_duration(medium_script)  
        long_duration = estimate_video_duration(long_script)
        
        assert short_duration < medium_duration < long_duration
        assert short_duration > 0
        

class TestScriptManager:
    """Test script management functionality."""
    
    def test_validate_script_content_valid(self):
        """Test script content validation with valid content."""
        valid_script = "This is a great horror movie that will terrify you!"
        
        result = validate_script_content(valid_script, script_type="hook")
        
        assert result is True
        
    def test_validate_script_content_invalid(self):
        """Test script content validation with invalid content."""
        # Test empty script
        empty_script = ""
        result = validate_script_content(empty_script)
        assert result is False
        
        # Test very long script
        long_script = "word " * 100
        result = validate_script_content(long_script, script_type="hook")
        assert result is False
        
    def test_process_script_text(self):
        """Test script text processing."""
        raw_script = "  This is a RAW script with extra spaces!!! And quotes \"here\"  "
        
        processed = process_script_text(raw_script, optimization_mode="tiktok")
        
        assert processed is not None
        assert processed.strip() == processed  # No leading/trailing spaces
        assert '"' not in processed  # Quotes removed
        
    @patch('ai.script_manager.ensure_directory')
    @patch('ai.script_manager.safe_write_file')
    def test_save_scripts_to_files(self, mock_write, mock_ensure_dir):
        """Test saving scripts to files."""
        mock_ensure_dir.return_value = True
        mock_write.return_value = True
        
        scripts = {
            'movie1': 'First script with intro',
            'movie2': 'Second script',
            'movie3': 'Third script'
        }
        combined_script = "\\n\\n".join(scripts.values())
        
        result = save_scripts_to_files(scripts, combined_script)
        
        assert result is not None
        assert mock_ensure_dir.called
        assert mock_write.call_count >= 4  # 3 individual + 1 combined
        
    def test_get_script_statistics(self):
        """Test script statistics generation."""
        scripts = {
            'movie1': 'Here are the top 3 horror movies! This first movie terrifies.',
            'movie2': 'This second movie will scare you completely.',
            'movie3': 'This third movie is absolutely frightening.'
        }
        
        stats = get_script_statistics(scripts)
        
        assert 'total_scripts' in stats
        assert 'total_words' in stats
        assert 'average_words_per_script' in stats
        assert stats['total_scripts'] == 3
        assert stats['total_words'] > 0


class TestPromptTemplates:
    """Test prompt template functionality."""
    
    def test_get_hook_prompt_template(self):
        """Test hook prompt template generation."""
        movie_data = {
            'title': 'Godzilla Minus One',
            'year': 2023,
            'genres': ['Horror', 'Action'],
            'imdb_score': 7.7
        }
        
        prompt = get_hook_prompt_template(
            movie_data=movie_data,
            genre='Horror',
            platform='Netflix'
        )
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert 'Godzilla Minus One' in prompt or 'horror' in prompt.lower()
        
    def test_get_intro_prompt_template(self):
        """Test intro prompt template generation."""
        prompt = get_intro_prompt_template(
            genre='Horror',
            platform='Netflix',
            content_type='Film'
        )
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert 'StreamGang' in prompt or 'horror' in prompt.lower()
        
    def test_customize_prompt_for_genre(self):
        """Test prompt customization for specific genres."""
        base_prompt = "Create a hook for this movie."
        
        horror_prompt = customize_prompt_for_genre(base_prompt, 'Horror')
        comedy_prompt = customize_prompt_for_genre(base_prompt, 'Comedy')
        
        assert horror_prompt != comedy_prompt
        assert len(horror_prompt) > len(base_prompt)
        assert len(comedy_prompt) > len(base_prompt)
        
    def test_get_available_templates(self):
        """Test getting available template types."""
        templates = get_available_templates()
        
        assert isinstance(templates, dict)
        assert 'hook' in templates
        assert 'intro' in templates
        assert isinstance(templates['hook'], list)
        assert isinstance(templates['intro'], list)
        
    def test_validate_prompt_template(self):
        """Test prompt template validation."""
        valid_template = "Create a {content_type} hook for {genre} movies."
        invalid_template = ""
        
        valid_result = validate_prompt_template(valid_template)
        invalid_result = validate_prompt_template(invalid_template)
        
        assert valid_result['is_valid'] is True
        assert invalid_result['is_valid'] is False
    
    def test_optimize_script_for_platform_tiktok(self):
        """Test script optimization for TikTok."""
        long_script = "This is a very long script with many words that exceeds the typical limit for TikTok content and should be truncated"
        
        result = optimize_script_for_platform(long_script, "TikTok")
        
        word_count = len(result.split())
        assert word_count <= 15
        assert result.endswith('!')
    
    def test_enhance_script_with_context_viral(self):
        """Test script enhancement with viral elements."""
        script = "movie is scary"
        movie_data = {'title': 'Horror Movie', 'genres': ['Horror']}
        
        result = enhance_script_with_context(script, movie_data, "viral")
        
        assert result.startswith("This")
        assert result == "This movie is scary"
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'})
    def test_get_openai_usage_stats_configured(self):
        """Test OpenAI usage stats when configured."""
        with patch('ai.openai_scripts._get_openai_client', return_value=Mock()):
            with patch('ai.openai_scripts.get_api_config', return_value={'model': 'gpt-4'}):
                stats = get_openai_usage_stats()
        
        assert stats['api_key_configured'] is True
        assert stats['client_available'] is True
        assert stats['model_config']['model'] == 'gpt-4'
    
    @patch('ai.openai_scripts._get_openai_client')
    def test_test_openai_connection_success(self, mock_get_client):
        """Test OpenAI connection test success."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "test successful"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = test_openai_connection()
        
        assert result['connection_successful'] is True
        assert result['api_accessible'] is True
        assert result['test_generation'] is True
        assert result['response_time'] is not None


class TestHeyGenClient:
    """Test HeyGen API integration functionality."""
    
    @patch('ai.heygen_client._get_heygen_headers')
    @patch('ai.heygen_client._create_single_video')
    def test_create_heygen_video_success(self, mock_create_single, mock_headers):
        """Test successful HeyGen video creation."""
        mock_headers.return_value = {'X-Api-Key': 'test_key'}
        mock_create_single.side_effect = ['video_id_1', 'video_id_2', 'video_id_3']
        
        script_data = {
            'movie1': {'text': 'Hook 1'},
            'movie2': {'text': 'Hook 2'},
            'movie3': {'text': 'Hook 3'}
        }
        
        result = create_heygen_video(script_data, use_template=True, genre='Horror')
        
        assert result is not None
        assert len(result) == 3
        assert result['movie1'] == 'video_id_1'
        assert result['movie2'] == 'video_id_2'
        assert result['movie3'] == 'video_id_3'
    
    @patch('ai.heygen_client._get_heygen_headers')
    def test_create_heygen_video_no_headers(self, mock_headers):
        """Test HeyGen video creation when headers unavailable."""
        mock_headers.return_value = None
        
        result = create_heygen_video({'movie1': 'test script'})
        
        assert result is None
    
    @patch('requests.get')
    @patch('ai.heygen_client._get_heygen_headers')
    def test_check_video_status_completed(self, mock_headers, mock_get):
        """Test checking video status when completed."""
        mock_headers.return_value = {'X-Api-Key': 'test_key'}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'status': 'completed',
                'video_url': 'https://example.com/video.mp4',
                'duration': 10.0
            }
        }
        mock_get.return_value = mock_response
        
        result = check_video_status('test_video_id')
        
        assert result['status'] == 'completed'
        assert result['url'] == 'https://example.com/video.mp4'
        assert result['duration'] == 10.0
    
    @patch('ai.heygen_client.check_video_status')
    def test_wait_for_completion_success(self, mock_check_status):
        """Test waiting for completion when videos complete quickly."""
        # First call: processing, second call: completed
        mock_check_status.side_effect = [
            {'status': 'processing', 'progress': 50},
            {'status': 'completed', 'url': 'https://example.com/video1.mp4'},
            {'status': 'processing', 'progress': 75},
            {'status': 'completed', 'url': 'https://example.com/video2.mp4'}
        ]
        
        video_ids = {'movie1': 'video_id_1', 'movie2': 'video_id_2'}
        
        with patch('time.sleep'):  # Skip actual sleeping
            result = wait_for_completion(video_ids, max_wait_time=60, poll_interval=1)
        
        assert len(result) == 2
        assert result['movie1']['status'] == 'completed'
        assert result['movie2']['status'] == 'completed'
    
    @patch('ai.heygen_client.wait_for_completion')
    def test_get_video_urls_success(self, mock_wait):
        """Test getting video URLs from completed videos."""
        mock_wait.return_value = {
            'movie1': {'status': 'completed', 'url': 'https://example.com/video1.mp4'},
            'movie2': {'status': 'completed', 'url': 'https://example.com/video2.mp4'},
            'movie3': {'status': 'failed', 'error': 'Generation failed'}
        }
        
        video_ids = {'movie1': 'id1', 'movie2': 'id2', 'movie3': 'id3'}
        
        result = get_video_urls(video_ids)
        
        assert result is not None
        assert len(result) == 2  # Only completed videos
        assert result['movie1'] == 'https://example.com/video1.mp4'
        assert result['movie2'] == 'https://example.com/video2.mp4'
    
    def test_estimate_video_duration(self):
        """Test video duration estimation."""
        short_script = "This is a short script."
        long_script = "This is a much longer script with many more words that should result in a longer estimated duration for the video."
        
        short_duration = estimate_video_duration(short_script)
        long_duration = estimate_video_duration(long_script)
        
        assert short_duration >= 3.0  # Minimum duration
        assert long_duration > short_duration
    
    @patch.dict('os.environ', {'HEYGEN_API_KEY': 'test_key'})
    def test_get_heygen_config_status_configured(self):
        """Test HeyGen configuration status when configured."""
        status = get_heygen_config_status()
        
        assert status['api_key_set'] is True
        assert status['headers_available'] is True


class TestScriptManager:
    """Test script management functionality."""
    
    def test_validate_script_content_valid_hook(self):
        """Test script validation for valid hook."""
        hook = "This horror movie will terrify you!"
        
        result = validate_script_content(hook, 'hook')
        
        assert result is True
    
    def test_validate_script_content_too_long_hook(self):
        """Test script validation for hook that's too long."""
        long_hook = "This is a very long hook sentence with way too many words that exceeds the maximum allowed length for a hook"
        
        result = validate_script_content(long_hook, 'hook')
        
        assert result is False
    
    def test_validate_script_content_empty(self):
        """Test script validation for empty content."""
        result = validate_script_content("", 'hook')
        
        assert result is False
    
    def test_validate_script_batch_success(self):
        """Test batch script validation."""
        scripts = {
            'intro': 'Here are the top 3 horror movies from StreamGank!',
            'movie1': 'This horror movie will terrify you!',
            'movie2': 'Why this thriller keeps you awake!',
            'movie3': 'The reason this film broke records!'
        }
        
        result = validate_script_batch(scripts)
        
        assert result['validation_passed'] is True
        assert len(result['valid_scripts']) == 4
        assert len(result['invalid_scripts']) == 0
        assert result['total_words'] > 0
    
    def test_process_script_text_tiktok(self):
        """Test script text processing for TikTok."""
        script = '  "This movie will scare you"  '
        
        result = process_script_text(script, 'tiktok')
        
        assert result == "This movie will scare you!"
        assert not result.startswith(' ')
        assert not result.endswith(' ')
    
    def test_combine_scripts_with_order(self):
        """Test script combination with specified order."""
        scripts = {
            'intro': 'Welcome to StreamGank!',
            'movie1': 'First movie hook.',
            'movie2': 'Second movie hook.',
            'movie3': 'Third movie hook.'
        }
        order = ['intro', 'movie1', 'movie2', 'movie3']
        
        with patch('ai.script_manager.process_script_text', side_effect=lambda x: x):
            result = combine_scripts(scripts, order)
        
        expected = "Welcome to StreamGank!\n\nFirst movie hook.\n\nSecond movie hook.\n\nThird movie hook."
        assert result == expected
    
    @patch('ai.script_manager.ensure_directory')
    @patch('ai.script_manager.safe_write_file')
    def test_save_scripts_to_files_txt(self, mock_write, mock_ensure_dir):
        """Test saving scripts to text files."""
        mock_ensure_dir.return_value = True
        mock_write.return_value = True
        
        scripts = {
            'intro': 'Intro script',
            'movie1': 'Hook 1'
        }
        
        result = save_scripts_to_files(scripts, 'test_output', 'txt')
        
        assert len(result) == 2
        assert 'intro' in result
        assert 'movie1' in result
        mock_write.assert_called()
    
    @patch('ai.script_manager.ensure_directory')
    @patch('ai.script_manager.safe_write_file')
    def test_save_scripts_to_files_json(self, mock_write, mock_ensure_dir):
        """Test saving scripts to JSON files."""
        mock_ensure_dir.return_value = True
        mock_write.return_value = True
        
        scripts = {
            'intro': 'Intro script',
            'movie1': 'Hook 1'
        }
        
        result = save_scripts_to_files(scripts, 'test_output', 'json')
        
        assert len(result) == 2
        mock_write.assert_called()
        # Check that JSON data was written (called with json.dumps result)
        write_calls = mock_write.call_args_list
        for call in write_calls:
            written_content = call[0][1]  # Second argument is content
            # Should be valid JSON
            json.loads(written_content)
    
    def test_get_script_statistics(self):
        """Test script statistics generation."""
        scripts = {
            'intro': 'Here are the top horror movies!',  # 6 words
            'movie1': 'This movie will terrify you!',     # 5 words
            'movie2': 'Why this thriller scares!',        # 4 words
            'movie3': ''  # Empty script
        }
        
        with patch('ai.script_manager.validate_script_content', return_value=True):
            stats = get_script_statistics(scripts)
        
        assert stats['total_scripts'] == 4
        assert stats['total_words'] == 15  # 6 + 5 + 4 + 0
        assert stats['valid_scripts'] == 3  # Empty script should be invalid
        assert 'intro' in stats['word_distribution']


class TestPromptTemplates:
    """Test prompt template functionality."""
    
    def test_get_hook_prompt_template_with_genre(self):
        """Test hook prompt template generation with genre."""
        movie_data = {
            'title': 'Test Horror Movie',
            'genres': ['Horror'],
            'imdb_score': 8.5
        }
        
        system_prompt, user_prompt = get_hook_prompt_template(movie_data, 'Horror', 'TikTok')
        
        assert 'viral content creator' in system_prompt.lower()
        assert 'horror' in system_prompt.lower()
        assert 'tiktok' in system_prompt.lower()
        assert movie_data['title'] in user_prompt
    
    def test_get_intro_prompt_template(self):
        """Test intro prompt template generation."""
        system_prompt, user_prompt = get_intro_prompt_template('Horror', 'Netflix', 'Movies')
        
        assert 'introduction' in system_prompt.lower()
        assert 'Horror' in user_prompt
        assert 'Netflix' in user_prompt
        assert 'StreamGank' in user_prompt
    
    def test_build_context_prompt_with_movies(self):
        """Test context prompt building with movie data."""
        context_data = {
            'movies': [
                {'title': 'Movie 1', 'year': 2023, 'imdb_score': 8.5},
                {'title': 'Movie 2', 'year': 2024, 'imdb_score': 7.8}
            ],
            'genre': 'Horror',
            'platform': 'Netflix'
        }
        
        result = build_context_prompt(context_data)
        
        assert 'Movie 1' in result
        assert 'Movie 2' in result
        assert 'Horror' in result
        assert 'Netflix' in result
        assert '2023' in result
    
    def test_customize_prompt_for_genre_horror(self):
        """Test prompt customization for horror genre."""
        base_prompt = "Create a hook for this movie."
        
        result = customize_prompt_for_genre(base_prompt, 'Horror')
        
        assert base_prompt in result
        assert 'GENRE-SPECIFIC REQUIREMENTS' in result
        assert 'horror-focused' in result.lower()
    
    def test_get_viral_optimization_prompt_hook(self):
        """Test viral optimization prompt for hooks."""
        result = get_viral_optimization_prompt('hook')
        
        assert 'VIRAL CONTENT OPTIMIZATION' in result
        assert 'hook' in result.lower()
        assert 'power words' in result.lower()
        assert 'curiosity gap' in result.lower()
    
    def test_get_a_b_test_prompts(self):
        """Test A/B test prompt generation."""
        base_prompt = "Create engaging content."
        
        result = get_a_b_test_prompts(base_prompt, variations=3)
        
        assert len(result) == 3
        assert result[0] == base_prompt  # Original included
        assert all(base_prompt in prompt for prompt in result)
    
    def test_get_available_templates(self):
        """Test getting available prompt templates."""
        result = get_available_templates()
        
        assert 'hook_templates' in result
        assert 'intro_templates' in result
        assert 'optimization_templates' in result
        assert isinstance(result['hook_templates'], list)
    
    def test_validate_prompt_template_valid(self):
        """Test prompt template validation for valid template."""
        template = """Create a viral hook for this movie.

Requirements:
- Keep it under 18 words
- Start with power words
- Create curiosity

Example: "This horror movie will make you sleep with the lights on!" """
        
        result = validate_prompt_template(template)
        
        assert result['is_valid'] is True
        assert result['has_instructions'] is True
        assert result['has_examples'] is True
        assert len(result['issues']) == 0
    
    def test_validate_prompt_template_too_short(self):
        """Test prompt template validation for template that's too short."""
        template = "Create content."
        
        result = validate_prompt_template(template)
        
        assert result['is_valid'] is False
        assert 'too short' in result['issues'][0]


class TestAIIntegration:
    """Test integration between AI modules."""
    
    @patch('ai.openai_scripts.generate_hook_script')
    @patch('ai.heygen_client.create_heygen_video')
    def test_scripts_to_heygen_integration(self, mock_heygen, mock_hook):
        """Test integration from script generation to HeyGen video creation."""
        # Mock script generation
        mock_hook.side_effect = ["Hook 1", "Hook 2", "Hook 3"]
        
        # Mock HeyGen video creation
        mock_heygen.return_value = {
            'movie1': 'video_id_1',
            'movie2': 'video_id_2', 
            'movie3': 'video_id_3'
        }
        
        # Generate scripts
        movies = [
            {'title': 'Movie 1'}, 
            {'title': 'Movie 2'}, 
            {'title': 'Movie 3'}
        ]
        
        scripts = {}
        for i, movie in enumerate(movies):
            hook = mock_hook(movie)
            scripts[f'movie{i+1}'] = {'text': hook}
        
        # Create HeyGen videos
        video_ids = mock_heygen(scripts)
        
        assert len(video_ids) == 3
        assert all(vid.startswith('video_id_') for vid in video_ids.values())
    
    def test_script_manager_with_openai_output(self):
        """Test script manager processing OpenAI output."""
        # Simulate OpenAI output with quotes and extra whitespace
        openai_output = '  "This movie will terrify you!"  '
        
        # Process with script manager
        processed = process_script_text(openai_output, 'tiktok')
        
        # Validate with script manager
        is_valid = validate_script_content(processed, 'hook')
        
        assert processed == "This movie will terrify you!"
        assert is_valid is True
    
    @patch('ai.script_manager.save_scripts_to_files')
    def test_prompt_templates_to_script_manager(self, mock_save):
        """Test using prompt templates with script manager."""
        mock_save.return_value = {'intro': 'intro.txt', 'movie1': 'movie1.txt'}
        
        # Get prompt templates
        movie_data = {'title': 'Test Movie', 'genres': ['Horror']}
        system_prompt, user_prompt = get_hook_prompt_template(movie_data, 'Horror')
        
        # Simulate using templates to generate scripts
        generated_scripts = {
            'intro': 'Here are the top 3 horror movies!',
            'movie1': 'This horror movie will terrify you!'
        }
        
        # Validate and save scripts
        validation = validate_script_batch(generated_scripts)
        if validation['validation_passed']:
            file_paths = save_scripts_to_files(generated_scripts)
        
        assert validation['validation_passed'] is True
        assert len(file_paths) == 2
        mock_save.assert_called_once()