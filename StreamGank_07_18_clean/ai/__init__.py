"""
StreamGank AI Module

This module handles all AI-powered content generation for the StreamGang 
video generation system, including OpenAI script generation and HeyGen integration.

Modules:
    - openai_scripts: OpenAI-powered script generation for hooks and intros
    - heygen_client: HeyGen API integration for AI avatar video creation
    - script_manager: Script processing, validation, and management utilities
    - prompt_templates: Reusable prompt templates and configurations
"""

from .openai_scripts import *
from .heygen_client import *
from .script_manager import *
from .prompt_templates import *

__all__ = [
    # OpenAI Script Generation
    'generate_video_scripts',
    'generate_hook_script',
    'generate_intro_script',
    'generate_scripts_batch',
    
    # HeyGen Integration
    'create_heygen_video',
    'create_heygen_videos_batch',
    'check_video_status',
    'wait_for_completion',
    'get_video_urls',
    
    # Script Management
    'validate_script_content',
    'process_script_text',
    'save_scripts_to_files',
    'load_scripts_from_files',
    'combine_scripts',
    
    # Prompt Templates
    'get_hook_prompt_template',
    'get_intro_prompt_template',
    'build_context_prompt',
    'customize_prompt_for_genre'
]