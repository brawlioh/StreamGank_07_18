#!/usr/bin/env python3
"""
Test script for the improved Vizard AI client
This script tests the VizardAIClient class without making actual API calls
"""

import os
import json
import time
import unittest
from unittest.mock import patch, MagicMock
from ai.vizard_client import VizardAIClient

class TestVizardAIClient(unittest.TestCase):
    """Test cases for VizardAIClient"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test environment variable
        os.environ["VIZARD_API_KEY"] = "test_api_key"
        self.client = VizardAIClient()
        
    def test_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.api_key, "test_api_key")
        self.assertEqual(len(self.client.API_BASE_URLS), 5)
        
    @patch("ai.vizard_client.requests.post")
    def test_create_project(self, mock_post):
        """Test project creation with multiple URLs"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "status": "CREATED"
        }
        mock_response.text = '{"id": "12345", "status": "CREATED"}'
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.client.create_project("https://www.youtube.com/watch?v=test123", {
            "clipCount": 3,
            "minLength": 5,
            "maxLength": 10
        })
        
        # Assertions
        self.assertEqual(result["id"], "12345")
        self.assertEqual(result["status"], "CREATED")
        self.assertEqual(result["raw_response"], '{"id": "12345", "status": "CREATED"}')
        self.assertEqual(result["formattedId"], "open-api-12345")
        
        # Verify all base URLs were attempted until success
        # Should be at least one call
        self.assertTrue(mock_post.called)
        
    @patch("ai.vizard_client.requests.get")
    def test_get_project_status(self, mock_get):
        """Test getting project status"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "COMPLETED",
            "progress": 100,
            "clips": [
                {"url": "https://example.com/clip1.mp4"},
                {"url": "https://example.com/clip2.mp4"}
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.get_project_status("open-api-12345")
        
        # Assertions
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(len(result["clips"]), 2)
        
    @patch("ai.vizard_client.VizardAIClient.get_project_status")
    @patch("time.sleep", return_value=None)  # Don't actually sleep in tests
    def test_wait_for_completion(self, mock_sleep, mock_get_status):
        """Test waiting for project completion"""
        # Set up the mock to return different responses on consecutive calls
        mock_get_status.side_effect = [
            {"status": "PROCESSING", "progress": 30},
            {"status": "PROCESSING", "progress": 60},
            {"status": "COMPLETED", "progress": 100, "clips": [{"url": "https://example.com/clip1.mp4"}]}
        ]
        
        # Call the method with short delays
        result = self.client.wait_for_completion("open-api-12345", initial_delay=0, retry_delay=0)
        
        # Assertions
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["progress"], 100)
        self.assertEqual(len(result["clips"]), 1)
        
        # Verify it was called 3 times
        self.assertEqual(mock_get_status.call_count, 3)
        
    @patch("ai.vizard_client.VizardAIClient.create_project")
    @patch("ai.vizard_client.VizardAIClient.wait_for_completion")
    @patch("ai.vizard_client.VizardAIClient.download_clips")
    def test_extract_highlights(self, mock_download, mock_wait, mock_create):
        """Test end-to-end highlight extraction"""
        # Mock responses
        mock_create.return_value = {
            "projectId": "12345",
            "status": "CREATED"
        }
        mock_wait.return_value = {
            "status": "COMPLETED",
            "clips": [{"clipUrl": "https://example.com/clip1.mp4"}]
        }
        mock_download.return_value = ["/tmp/clip1.mp4"]
        
        # Call the method
        result = self.client.extract_highlights(
            "https://www.youtube.com/watch?v=test123",
            num_clips=3,
            clip_length=2  # Medium
        )
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "/tmp/clip1.mp4")
        
        # Verify correct options were passed based on clip_length
        args, kwargs = mock_create.call_args
        youtube_url, options = args
        self.assertEqual(options["minLength"], 5)
        self.assertEqual(options["maxLength"], 12)
        self.assertEqual(options["clipCount"], 3)

if __name__ == "__main__":
    unittest.main()
