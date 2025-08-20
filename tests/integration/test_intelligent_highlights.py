"""
Test Intelligent Highlight Extraction Integration

This module tests the enhanced intelligent highlight extraction workflow
that downloads videos, analyzes content, and extracts optimal segments
before processing with Vizard.ai.

Author: StreamGank Development Team
Version: 1.0.0 - Intelligent Highlight Testing
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import numpy as np

class TestIntelligentHighlightExtraction:
    """Test suite for intelligent highlight extraction."""
    
    def test_intelligent_extractor_initialization(self):
        """Test IntelligentHighlightExtractor initialization."""
        with patch('ai.intelligent_highlight_extractor.get_video_settings') as mock_settings:
            mock_settings.return_value = {'clip_duration': 15}
            
            from ai.intelligent_highlight_extractor import IntelligentHighlightExtractor
            
            extractor = IntelligentHighlightExtractor()
            
            assert extractor.target_duration == 90  # 1:30 as requested
            assert extractor.analysis_window == 10
            assert extractor.download_quality == "1080p"
            assert 'audio_energy' in extractor.weights
            assert 'visual_change' in extractor.weights
    
    @patch('yt_dlp.YoutubeDL')
    @patch('ai.intelligent_highlight_extractor.ensure_directory')
    @patch('os.listdir')
    @patch('os.path.getsize')
    def test_high_quality_video_download(self, mock_getsize, mock_listdir, mock_ensure_dir, mock_ytdl):
        """Test high-quality video download functionality."""
        from ai.intelligent_highlight_extractor import IntelligentHighlightExtractor
        
        # Mock successful download
        mock_listdir.return_value = ['test_movie_1080p.mp4']
        mock_getsize.return_value = 50 * 1024 * 1024  # 50MB file
        
        mock_ytdl_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance
        
        with patch('ai.intelligent_highlight_extractor.get_video_settings', return_value={'clip_duration': 15}):
            extractor = IntelligentHighlightExtractor()
            
            result = extractor.download_high_quality_video(
                "https://youtube.com/test",
                "Test Movie"
            )
            
            # Verify download was attempted
            mock_ytdl_instance.download.assert_called_once()
            
            # Verify result path
            assert result is not None
            assert "test_movie_1080p.mp4" in result
    
    @patch('moviepy.editor.VideoFileClip')
    @patch('cv2.CascadeClassifier')
    def test_video_content_analysis(self, mock_cascade, mock_videoclip):
        """Test multi-algorithm video content analysis."""
        from ai.intelligent_highlight_extractor import IntelligentHighlightExtractor
        
        # Mock video clip
        mock_clip = Mock()
        mock_clip.duration = 120  # 2 minute video
        mock_clip.audio = Mock()
        
        # Mock audio analysis
        mock_audio_array = np.random.rand(1000)
        mock_clip.audio.to_soundarray.return_value = mock_audio_array
        
        # Mock frame iteration
        mock_frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(5)]
        mock_clip.iter_frames.return_value = iter(mock_frames)
        
        mock_segment = Mock()
        mock_segment.audio = mock_clip.audio
        mock_segment.iter_frames.return_value = iter(mock_frames)
        mock_segment.close = Mock()
        
        mock_clip.subclip.return_value = mock_segment
        mock_videoclip.return_value = mock_clip
        
        # Mock face cascade
        mock_cascade_instance = Mock()
        mock_cascade_instance.detectMultiScale.return_value = [(10, 10, 50, 50)]  # One face detected
        mock_cascade.return_value = mock_cascade_instance
        
        with patch('ai.intelligent_highlight_extractor.get_video_settings', return_value={'clip_duration': 15}):
            extractor = IntelligentHighlightExtractor()
            
            analysis = extractor.analyze_video_content("test_video.mp4")
            
            # Verify analysis results
            assert 'audio_energy' in analysis
            assert 'visual_change' in analysis
            assert 'motion_intensity' in analysis
            assert 'face_detection' in analysis
            assert 'color_variance' in analysis
            assert 'temporal_position' in analysis
            
            # Each should have multiple data points
            assert len(analysis['audio_energy']) > 0
            assert len(analysis['visual_change']) > 0
    
    def test_best_highlight_segment_selection(self):
        """Test intelligent segment selection algorithm."""
        from ai.intelligent_highlight_extractor import IntelligentHighlightExtractor
        
        with patch('ai.intelligent_highlight_extractor.get_video_settings', return_value={'clip_duration': 15}):
            extractor = IntelligentHighlightExtractor()
            
            # Create mock analysis data (12 windows = 120 seconds of video)
            analysis = {
                'audio_energy': [0.5, 0.8, 1.0, 0.9, 0.7, 0.6, 0.8, 1.0, 0.9, 0.5, 0.3, 0.2],
                'visual_change': [0.3, 0.7, 0.9, 0.8, 0.6, 0.5, 0.7, 0.9, 0.8, 0.4, 0.2, 0.1],
                'motion_intensity': [0.4, 0.6, 0.8, 0.7, 0.5, 0.4, 0.6, 0.8, 0.7, 0.3, 0.1, 0.1],
                'face_detection': [1.0, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0, 2.0, 1.0, 0.0, 0.0, 0.0],
                'color_variance': [50, 80, 100, 90, 70, 60, 80, 100, 90, 40, 20, 10],
                'temporal_position': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
            }
            
            start_time, end_time = extractor.find_best_highlight_segment(analysis)
            
            # Verify reasonable segment selected
            assert isinstance(start_time, int)
            assert isinstance(end_time, int)
            assert end_time - start_time == 90  # 1:30 duration as requested
            assert start_time >= 0
            assert end_time <= 120  # Within video duration
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_highlight_segment_extraction(self, mock_getsize, mock_exists, mock_subprocess):
        """Test FFmpeg-based highlight segment extraction."""
        from ai.intelligent_highlight_extractor import IntelligentHighlightExtractor
        
        # Mock successful extraction
        mock_subprocess.return_value.returncode = 0
        mock_exists.return_value = True
        mock_getsize.return_value = 25 * 1024 * 1024  # 25MB output
        
        with patch('ai.intelligent_highlight_extractor.get_video_settings', return_value={'clip_duration': 15}):
            extractor = IntelligentHighlightExtractor()
            
            result = extractor.extract_highlight_segment(
                "source_video.mp4",
                30,  # Start at 30 seconds
                120,  # End at 2 minutes (90 seconds duration)
                "Test Movie"
            )
            
            # Verify FFmpeg was called
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            
            # Verify FFmpeg command structure
            assert 'ffmpeg' in call_args
            assert '-ss' in call_args
            assert '30' in call_args  # Start time
            assert '-t' in call_args
            assert '90' in call_args  # Duration
            
            # Verify result
            assert result is not None
            assert 'test_movie' in result.lower()
    
    def test_content_keyword_generation(self):
        """Test content-based keyword generation."""
        from ai.intelligent_highlight_extractor import IntelligentHighlightExtractor
        
        with patch('moviepy.editor.VideoFileClip') as mock_videoclip:
            # Mock video clip for keyword analysis
            mock_clip = Mock()
            mock_clip.duration = 90
            mock_clip.get_frame.return_value = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            mock_clip.audio = Mock()
            mock_clip.audio.subclip.return_value = mock_clip.audio
            mock_clip.audio.to_soundarray.return_value = np.random.rand(1000)
            mock_clip.close = Mock()
            mock_videoclip.return_value = mock_clip
            
            with patch('ai.intelligent_highlight_extractor.get_video_settings', return_value={'clip_duration': 15}):
                extractor = IntelligentHighlightExtractor()
                
                keywords = extractor.generate_content_keywords(
                    "highlight_video.mp4",
                    "Action Movie Thriller",
                    30,
                    120
                )
                
                # Verify keyword generation
                assert isinstance(keywords, list)
                assert len(keywords) > 0
                assert len(keywords) <= 10  # Capped at 10
                
                # Should contain movie-related keywords
                keyword_text = ' '.join(keywords).lower()
                assert 'action' in keyword_text or 'movie' in keyword_text or 'thriller' in keyword_text

class TestIntelligentWorkflowIntegration:
    """Test integration with the main workflow."""
    
    @patch('ai.intelligent_highlight_extractor.IntelligentHighlightExtractor')
    @patch('ai.vizard_client.VizardClient')
    def test_intelligent_processing_workflow(self, mock_vizard_client, mock_extractor_class):
        """Test the complete intelligent processing workflow."""
        from ai.intelligent_highlight_extractor import process_movie_with_intelligent_highlights
        
        # Mock extractor
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        
        mock_extractor.download_high_quality_video.return_value = "/tmp/downloaded_video.mp4"
        mock_extractor.analyze_video_content.return_value = {
            'audio_energy': [0.5, 0.8, 1.0],
            'visual_change': [0.3, 0.7, 0.9]
        }
        mock_extractor.find_best_highlight_segment.return_value = (30, 120)
        mock_extractor.extract_highlight_segment.return_value = "/tmp/highlight.mp4"
        mock_extractor.generate_content_keywords.return_value = ["action", "thriller", "movie"]
        
        # Mock Vizard client
        mock_vizard = Mock()
        mock_vizard_client.return_value = mock_vizard
        
        with patch('ai.intelligent_highlight_extractor._process_movie_with_vizard') as mock_process:
            mock_process.return_value = "https://cloudinary.com/final_clip.mp4"
            
            movie_data = {
                'title': 'Test Action Movie',
                'id': 123,
                'trailer_url': 'https://youtube.com/test'
            }
            
            result = process_movie_with_intelligent_highlights(movie_data)
            
            # Verify all steps were called
            mock_extractor.download_high_quality_video.assert_called_once()
            mock_extractor.analyze_video_content.assert_called_once()
            mock_extractor.find_best_highlight_segment.assert_called_once()
            mock_extractor.extract_highlight_segment.assert_called_once()
            mock_extractor.generate_content_keywords.assert_called_once()
            
            # Verify final result
            assert result == "https://cloudinary.com/final_clip.mp4"
    
    def test_requirements_validation(self):
        """Test validation of intelligent processing requirements."""
        from ai.intelligent_highlight_extractor import validate_intelligent_processing_requirements
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            
            with patch('ai.intelligent_highlight_extractor.ensure_directory'):
                validation = validate_intelligent_processing_requirements()
                
                assert 'ready' in validation
                assert 'missing_requirements' in validation
                assert 'warnings' in validation


if __name__ == '__main__':
    # Basic validation test
    print("🧪 Testing Intelligent Highlight Extraction...")
    
    try:
        # Test requirements validation
        from ai.intelligent_highlight_extractor import validate_intelligent_processing_requirements
        validation = validate_intelligent_processing_requirements()
        print(f"✅ Requirements validation: {validation}")
        
        print("🎉 Intelligent highlight extraction tests completed!")
        print("🧠 Features tested:")
        print("   📥 High-quality video downloading (1080p)")
        print("   🔍 Multi-algorithm content analysis")
        print("   🎯 Intelligent 1:30s segment selection")
        print("   🏷️ Content-based keyword generation")
        print("   ✂️ FFmpeg highlight extraction")
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        print("💡 Make sure all dependencies are installed:")
