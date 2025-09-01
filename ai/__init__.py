"""
StreamGank AI Module - CLEAN VERSION

This module handles all AI-powered content generation for the StreamGank 
video generation system, using clean, professional code.

ACTIVE MODULES:
    - clean_script_generator: Professional script generation (1 function replaces 80+ bloated ones)
    - heygen_client: HeyGen API integration for AI avatar video creation  
    - script_validator: Essential validation functions
    - prompt_templates: Reusable prompt templates and configurations

REMOVED BLOATED MODULES:
    - openai_scripts: ✅ DELETED (22 over-engineered functions)
    - script_manager: ✅ DELETED (19 bloated functions) 
    - formatters: ✅ DELETED (26 1-line functions)
    - robust_script_generator: ✅ DELETED (replaced by clean version)
"""

# Import streamlined modules
from .clean_script_generator import generate_video_scripts
from .heygen_client import *
from .script_validator import *
from .prompt_templates import *

__all__ = [
    # STREAMLINED Script Generation (from robust_script_generator)
    'generate_video_scripts',  # Main entry point - streamlined version
    
    # HeyGen Integration (from heygen_client - kept as-is)
    'create_heygen_video',
    'create_heygen_videos_batch', 
    'check_video_status',
    'wait_for_completion',
    'get_video_urls',
    
    # Essential Validation (from script_validator - streamlined)
    'validate_script_content',  # Streamlined version
    'clean_script_text',        # Basic cleaning only
    'get_script_word_count',    # Simple utility
    
    # Prompt Templates (from prompt_templates - kept with dynamic genres)
    'get_hook_prompt_template',
    'get_intro_prompt_template', 
    'build_context_prompt',
    'customize_prompt_for_genre'
]

# DEPRECATED FUNCTIONS (still accessible but marked for removal):
# These are from bloated modules - use streamlined versions above instead
# 'generate_hook_script',      # ❌ Use generate_video_scripts instead
# 'generate_intro_script',     # ❌ Use generate_video_scripts instead  
# 'generate_scripts_batch',    # ❌ Over-engineered, not used
# 'process_script_text',       # ❌ Use clean_script_text instead
# 'save_scripts_to_files',     # ❌ Handled internally by generate_video_scripts
# 'load_scripts_from_files',   # ❌ Not needed in streamlined workflow
# 'combine_scripts',           # ❌ Handled internally by generate_video_scripts