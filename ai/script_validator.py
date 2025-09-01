#!/usr/bin/env python3
"""
Minimal Script Validator for HeyGen Integration
StreamGank Video Generation System

This module provides ONLY the essential validation functions needed by HeyGen client.
Replaces the bloated ai/script_manager.py with 90% fewer functions.

Author: StreamGank Development Team  
Version: 2.0.0 - Streamlined Essential Functions Only
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

def validate_script_content(script: str, script_type: str = "general") -> bool:
    """
    Essential script validation for HeyGen integration.
    
    Args:
        script (str): Script content to validate
        script_type (str): Type of script ("hook", "intro", "general")
        
    Returns:
        bool: True if script passes validation
    """
    try:
        # Basic checks
        if not script or not isinstance(script, str):
            return False
        
        script_clean = script.strip()
        
        # Length validation
        if len(script_clean) < 3 or len(script_clean) > 500:
            return False
        
        # Word count validation by type
        word_count = len(script_clean.split())
        
        if script_type == "hook":
            if not (3 <= word_count <= 20):
                return False
        elif script_type == "intro":
            if not (9 <= word_count <= 14):
                return False
        
        # Must end with punctuation
        if not script_clean[-1] in '.!?':
            return False
        
        # Basic inappropriate content check
        inappropriate_words = ['explicit', 'violence', 'hate', 'discrimination']
        script_lower = script_clean.lower()
        if any(word in script_lower for word in inappropriate_words):
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating script: {str(e)}")
        return False

def clean_script_text(script: str) -> str:
    """
    Clean script text for HeyGen submission.
    
    Args:
        script (str): Raw script text
        
    Returns:
        str: Cleaned script text
    """
    if not script:
        return ""
    
    # Remove quotes and extra whitespace
    cleaned = script.replace('"', '').replace("'", "").strip()
    
    # Ensure proper ending punctuation
    if cleaned and not cleaned[-1] in '.!?':
        cleaned += "!"
    
    return cleaned

def get_script_word_count(script: str) -> int:
    """
    Get word count for script.
    
    Args:
        script (str): Script text
        
    Returns:
        int: Word count
    """
    return len(script.split()) if script else 0

# That's it! 3 essential functions vs 16 bloated ones.
# Total: ~80 lines vs ~600+ lines in original script_manager.py
