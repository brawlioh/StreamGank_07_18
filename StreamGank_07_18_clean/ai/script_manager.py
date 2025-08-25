"""
StreamGank Script Manager

This module provides script processing, validation, and management utilities
for AI-generated content in the StreamGang video generation system.

Features:
- Script content validation and quality checks
- Text processing and sanitization
- Script file management (save/load)
- Script combination and formatting
- Content optimization for different platforms
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import re

from utils.formatters import sanitize_script_text, clean_filename
from utils.file_utils import ensure_directory, safe_write_file, safe_read_file
from utils.validators import validate_file_path

logger = logging.getLogger(__name__)

# =============================================================================
# SCRIPT VALIDATION FUNCTIONS
# =============================================================================

def validate_script_content(script: str, script_type: str = "general") -> bool:
    """
    Validate script content for quality and compliance.
    
    Args:
        script (str): Script content to validate
        script_type (str): Type of script ("hook", "intro", "general")
        
    Returns:
        bool: True if script passes validation
    """
    try:
        if not script or not isinstance(script, str):
            logger.debug("Script validation failed: empty or non-string content")
            return False
        
        # Basic content checks
        script_clean = script.strip()
        
        if len(script_clean) < 3:
            logger.debug("Script validation failed: too short")
            return False
        
        if len(script_clean) > 500:
            logger.debug("Script validation failed: too long")
            return False
        
        # Word count validation based on script type
        words = script_clean.split()
        word_count = len(words)
        
        if script_type == "hook":
            if word_count > 20:
                logger.debug(f"Hook validation failed: {word_count} words (max 20)")
                return False
            if word_count < 3:
                logger.debug(f"Hook validation failed: {word_count} words (min 3)")
                return False
                
        elif script_type == "intro":
            if word_count > 30:
                logger.debug(f"Intro validation failed: {word_count} words (max 30)")
                return False
            if word_count < 5:
                logger.debug(f"Intro validation failed: {word_count} words (min 5)")
                return False
        
        # Content quality checks
        if not _has_proper_punctuation(script_clean):
            logger.debug("Script validation failed: missing proper punctuation")
            return False
        
        if _has_inappropriate_content(script_clean):
            logger.debug("Script validation failed: inappropriate content detected")
            return False
        
        # Platform optimization checks
        if not _is_social_media_optimized(script_clean, script_type):
            logger.debug("Script validation warning: not optimized for social media")
            # This is a warning, not a failure
        
        logger.debug(f"Script validation passed: {word_count} words, type: {script_type}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating script content: {str(e)}")
        return False


def validate_script_batch(scripts: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate a batch of scripts and provide detailed feedback.
    
    Args:
        scripts (Dict): Dictionary of script name to content
        
    Returns:
        Dict[str, Any]: Validation results with details
    """
    results = {
        'valid_scripts': [],
        'invalid_scripts': [],
        'warnings': [],
        'total_scripts': len(scripts),
        'total_words': 0,
        'validation_passed': True
    }
    
    try:
        for script_name, script_content in scripts.items():
            # Determine script type from name
            script_type = "general"
            if "hook" in script_name.lower() or script_name.startswith("movie"):
                script_type = "hook"
            elif "intro" in script_name.lower():
                script_type = "intro"
            
            # Validate script
            is_valid = validate_script_content(script_content, script_type)
            
            if is_valid:
                results['valid_scripts'].append(script_name)
                word_count = len(script_content.split()) if script_content else 0
                results['total_words'] += word_count
            else:
                results['invalid_scripts'].append(script_name)
                results['validation_passed'] = False
            
            # Additional quality checks
            if script_content:
                quality_issues = _check_script_quality(script_content, script_type)
                if quality_issues:
                    results['warnings'].extend([f"{script_name}: {issue}" for issue in quality_issues])
        
        logger.info(f"📋 Script batch validation: {len(results['valid_scripts'])}/{results['total_scripts']} valid")
        
        return results
        
    except Exception as e:
        logger.error(f"Error validating script batch: {str(e)}")
        results['validation_passed'] = False
        return results

# =============================================================================
# SCRIPT PROCESSING FUNCTIONS
# =============================================================================

def process_script_text(script: str, optimization_mode: str = "tiktok") -> Optional[str]:
    """
    Process and optimize script text for specific platforms.
    
    Args:
        script (str): Raw script text
        optimization_mode (str): Platform optimization mode
        
    Returns:
        str: Processed script text or None if processing failed
    """
    try:
        if not script:
            return None
        
        # Step 1: Basic sanitization
        processed = sanitize_script_text(script)
        
        # Step 2: Platform-specific optimization
        if optimization_mode.lower() in ['tiktok', 'instagram', 'shorts']:
            processed = _optimize_for_short_form(processed)
        elif optimization_mode.lower() in ['youtube', 'facebook']:
            processed = _optimize_for_long_form(processed)
        
        # Step 3: Ensure proper formatting
        processed = _ensure_proper_formatting(processed)
        
        # Step 4: Final validation
        if validate_script_content(processed):
            return processed
        else:
            logger.warning(f"⚠️ Processed script failed validation: {processed}")
            return script  # Return original if processing makes it worse
        
    except Exception as e:
        logger.error(f"Error processing script text: {str(e)}")
        return None


def combine_scripts(scripts: Dict[str, str], 
                   order: Optional[List[str]] = None,
                   separator: str = "\n\n") -> str:
    """
    Combine multiple scripts into a single script.
    
    Args:
        scripts (Dict): Dictionary of script name to content
        order (List): Optional order for combining scripts
        separator (str): Text separator between scripts
        
    Returns:
        str: Combined script text
    """
    try:
        if not scripts:
            return ""
        
        # Use specified order or default order
        if order:
            script_order = [name for name in order if name in scripts]
        else:
            # Default order: intro first, then movies
            script_order = []
            if 'intro' in scripts:
                script_order.append('intro')
            
            # Add movie scripts in order
            movie_scripts = [name for name in scripts.keys() if name.startswith('movie')]
            movie_scripts.sort()  # Sort to ensure consistent order
            script_order.extend(movie_scripts)
            
            # Add any remaining scripts
            remaining = [name for name in scripts.keys() if name not in script_order]
            script_order.extend(remaining)
        
        # Combine scripts
        combined_parts = []
        for script_name in script_order:
            if script_name in scripts and scripts[script_name]:
                processed_script = process_script_text(scripts[script_name])
                if processed_script:
                    combined_parts.append(processed_script)
        
        combined_script = separator.join(combined_parts)
        
        logger.info(f"📝 Combined {len(combined_parts)} scripts into {len(combined_script.split())} words")
        
        return combined_script
        
    except Exception as e:
        logger.error(f"Error combining scripts: {str(e)}")
        return ""

# =============================================================================
# SCRIPT FILE MANAGEMENT
# =============================================================================

def save_scripts_to_files(scripts: Dict[str, str], 
                         output_dir: str = "videos",
                         format: str = "txt") -> Dict[str, str]:
    """
    Save scripts to individual files.
    
    Args:
        scripts (Dict): Dictionary of script name to content
        output_dir (str): Output directory for script files
        format (str): File format ("txt", "json")
        
    Returns:
        Dict[str, str]: Dictionary mapping script names to file paths
    """
    file_paths = {}
    
    try:
        # Ensure output directory exists
        ensure_directory(output_dir)
        
        for script_name, script_content in scripts.items():
            if not script_content:
                continue
            
            # Generate filename
            clean_name = clean_filename(script_name)
            
            if format == "json":
                filename = f"script_{clean_name}.json"
                file_path = os.path.join(output_dir, filename)
                
                # Save as JSON with metadata
                script_data = {
                    'name': script_name,
                    'content': script_content,
                    'word_count': len(script_content.split()),
                    'character_count': len(script_content),
                    'created_at': str(Path().cwd()),  # Placeholder for timestamp
                    'type': _detect_script_type(script_name)
                }
                
                success = safe_write_file(file_path, json.dumps(script_data, indent=2))
                
            else:  # Default to txt
                filename = f"script_{clean_name}.txt"
                file_path = os.path.join(output_dir, filename)
                success = safe_write_file(file_path, script_content)
            
            if success:
                file_paths[script_name] = file_path
                logger.debug(f"💾 Saved {script_name}: {file_path}")
            else:
                logger.error(f"❌ Failed to save {script_name}")
        
        logger.info(f"💾 Saved {len(file_paths)}/{len(scripts)} scripts to {output_dir}")
        
        return file_paths
        
    except Exception as e:
        logger.error(f"Error saving scripts to files: {str(e)}")
        return file_paths


def load_scripts_from_files(file_paths: Dict[str, str]) -> Dict[str, str]:
    """
    Load scripts from files.
    
    Args:
        file_paths (Dict): Dictionary mapping script names to file paths
        
    Returns:
        Dict[str, str]: Dictionary of script name to content
    """
    scripts = {}
    
    try:
        for script_name, file_path in file_paths.items():
            # Validate file path
            if not validate_file_path(file_path, must_exist=True)['is_valid']:
                logger.warning(f"⚠️ Invalid file path for {script_name}: {file_path}")
                continue
            
            # Load content based on file extension
            if file_path.endswith('.json'):
                content = safe_read_file(file_path)
                if content:
                    try:
                        script_data = json.loads(content)
                        scripts[script_name] = script_data.get('content', '')
                    except json.JSONDecodeError:
                        logger.error(f"❌ Invalid JSON in {file_path}")
                        continue
            else:
                # Assume text file
                content = safe_read_file(file_path)
                if content:
                    scripts[script_name] = content
            
            if script_name in scripts:
                logger.debug(f"📖 Loaded {script_name}: {len(scripts[script_name])} characters")
        
        logger.info(f"📖 Loaded {len(scripts)} scripts from files")
        
        return scripts
        
    except Exception as e:
        logger.error(f"Error loading scripts from files: {str(e)}")
        return scripts


def backup_scripts(scripts: Dict[str, str], backup_dir: str = "backups") -> Optional[str]:
    """
    Create a backup of scripts with timestamp.
    
    Args:
        scripts (Dict): Scripts to backup
        backup_dir (str): Backup directory
        
    Returns:
        str: Backup file path or None if failed
    """
    try:
        import datetime
        
        # Ensure backup directory exists
        ensure_directory(backup_dir)
        
        # Generate backup filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"scripts_backup_{timestamp}.json"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create backup data
        backup_data = {
            'timestamp': timestamp,
            'script_count': len(scripts),
            'total_words': sum(len(script.split()) for script in scripts.values()),
            'scripts': scripts
        }
        
        # Save backup
        success = safe_write_file(backup_path, json.dumps(backup_data, indent=2))
        
        if success:
            logger.info(f"💾 Scripts backed up to: {backup_path}")
            return backup_path
        else:
            logger.error("❌ Failed to create script backup")
            return None
        
    except Exception as e:
        logger.error(f"Error creating script backup: {str(e)}")
        return None

# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _has_proper_punctuation(script: str) -> bool:
    """Check if script has proper punctuation."""
    script = script.strip()
    if not script:
        return False
    
    # Should end with proper punctuation
    return script[-1] in '.!?'


def _has_inappropriate_content(script: str) -> bool:
    """Check for inappropriate content (basic filter)."""
    # Basic inappropriate content check
    inappropriate_words = [
        'explicit', 'violence', 'hate', 'discrimination'
        # Add more as needed
    ]
    
    script_lower = script.lower()
    return any(word in script_lower for word in inappropriate_words)


def _is_social_media_optimized(script: str, script_type: str) -> bool:
    """Check if script is optimized for social media."""
    # Check for viral elements
    viral_starters = ['this', 'why', 'what', 'how', 'the reason', 'you won\'t believe']
    first_word = script.split()[0].lower() if script.split() else ""
    
    has_viral_starter = any(starter in script.lower()[:20] for starter in viral_starters)
    
    # Check for engagement elements
    engagement_words = ['shocking', 'amazing', 'unbelievable', 'secret', 'hidden', 'revealed']
    has_engagement = any(word in script.lower() for word in engagement_words)
    
    return has_viral_starter or has_engagement


def _check_script_quality(script: str, script_type: str) -> List[str]:
    """Check script quality and return list of issues."""
    issues = []
    
    if not script:
        return ["Empty script content"]
    
    words = script.split()
    word_count = len(words)
    
    # Length checks
    if script_type == "hook" and word_count > 18:
        issues.append(f"Hook too long ({word_count} words, max 18)")
    
    if script_type == "intro" and word_count > 25:
        issues.append(f"Intro too long ({word_count} words, max 25)")
    
    # Repetition check
    unique_words = set(word.lower() for word in words)
    if len(unique_words) < len(words) * 0.7:  # Less than 70% unique words
        issues.append("High word repetition detected")
    
    # Punctuation check
    if not script.strip().endswith(('.', '!', '?')):
        issues.append("Missing end punctuation")
    
    # Social media optimization check
    if not _is_social_media_optimized(script, script_type):
        issues.append("Could be more optimized for social media engagement")
    
    return issues


def _optimize_for_short_form(script: str) -> str:
    """Optimize script for short-form content (TikTok, etc.)."""
    try:
        words = script.split()
        
        # Truncate if too long
        if len(words) > 15:
            script = ' '.join(words[:15])
        
        # Ensure strong ending
        if not script.endswith(('!', '?')):
            script = script.rstrip('.') + '!'
        
        # Add viral elements if missing
        if not any(starter in script.lower()[:10] for starter in ['this', 'why', 'what']):
            if len(words) < 12:  # Only if there's room
                script = f"This {script.lower()}"
        
        return script
        
    except Exception:
        return script


def _optimize_for_long_form(script: str) -> str:
    """Optimize script for long-form content (YouTube, etc.)."""
    try:
        # For long-form, we can be more descriptive
        # But still keep it concise for attention span
        words = script.split()
        
        if len(words) > 25:
            script = ' '.join(words[:25])
        
        # Ensure proper ending
        if not script.endswith(('.', '!', '?')):
            script += '.'
        
        return script
        
    except Exception:
        return script


def _ensure_proper_formatting(script: str) -> str:
    """Ensure script has proper formatting."""
    try:
        script = script.strip()
        
        # Fix spacing issues
        script = re.sub(r'\s+', ' ', script)  # Multiple spaces to single
        
        # Ensure proper capitalization
        if script:
            script = script[0].upper() + script[1:]
        
        # Ensure proper ending
        if script and not script.endswith(('.', '!', '?')):
            script += '!'
        
        return script
        
    except Exception:
        return script


def _detect_script_type(script_name: str) -> str:
    """Detect script type from name."""
    name_lower = script_name.lower()
    
    if 'intro' in name_lower:
        return 'intro'
    elif 'hook' in name_lower or name_lower.startswith('movie'):
        return 'hook'
    elif 'outro' in name_lower:
        return 'outro'
    else:
        return 'general'

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_script_statistics(scripts: Dict[str, str]) -> Dict[str, Any]:
    """
    Get statistics about a collection of scripts.
    
    Args:
        scripts (Dict): Dictionary of scripts
        
    Returns:
        Dict[str, Any]: Script statistics
    """
    stats = {
        'total_scripts': len(scripts),
        'valid_scripts': 0,
        'total_words': 0,
        'total_characters': 0,
        'script_types': {},
        'word_distribution': {},
        'quality_issues': []
    }
    
    try:
        for script_name, script_content in scripts.items():
            if not script_content:
                continue
            
            # Basic counts
            words = script_content.split()
            word_count = len(words)
            char_count = len(script_content)
            
            stats['total_words'] += word_count
            stats['total_characters'] += char_count
            
            # Validation
            if validate_script_content(script_content):
                stats['valid_scripts'] += 1
            
            # Script type
            script_type = _detect_script_type(script_name)
            stats['script_types'][script_type] = stats['script_types'].get(script_type, 0) + 1
            
            # Word distribution
            stats['word_distribution'][script_name] = word_count
            
            # Quality issues
            issues = _check_script_quality(script_content, script_type)
            if issues:
                stats['quality_issues'].extend([f"{script_name}: {issue}" for issue in issues])
        
        # Calculate averages
        if stats['total_scripts'] > 0:
            stats['average_words'] = stats['total_words'] / stats['total_scripts']
            stats['average_characters'] = stats['total_characters'] / stats['total_scripts']
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting script statistics: {str(e)}")
        return stats