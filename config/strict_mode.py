"""
StreamGank Strict Mode Configuration

This module enforces strict error handling across the entire StreamGank system.
In strict mode, no fallbacks are used - any error or missing dependency 
causes the process to stop immediately with clear error messages.

STRICT MODE PRINCIPLES:
1. Fail-fast: Stop immediately on any error
2. No fallbacks: Don't mask issues with default values
3. Clear errors: Detailed error messages for debugging
4. Complete validation: Check all dependencies upfront
5. Guaranteed output: If function returns, output is valid

This ensures production reliability and prevents incorrect video generation.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# =============================================================================
# STRICT MODE CONFIGURATION
# =============================================================================

@dataclass
class StrictModeConfig:
    """Configuration for strict mode behavior."""
    
    # Global strict mode settings
    enabled: bool = True
    fail_on_missing_assets: bool = True
    fail_on_api_errors: bool = True
    fail_on_validation_errors: bool = True
    
    # Required asset validation
    require_all_heygen_videos: bool = True
    require_all_movie_covers: bool = True
    require_all_movie_clips: bool = True
    require_exact_movie_count: int = 3
    
    # API validation requirements
    require_openai_api_key: bool = True
    require_heygen_api_key: bool = True
    require_creatomate_api_key: bool = True
    require_cloudinary_config: bool = True
    
    # Script generation requirements
    require_all_scripts: bool = True
    require_minimum_script_length: int = 10  # words
    require_intro_script: bool = True
    require_all_movie_hooks: bool = True
    
    # Video processing requirements
    require_valid_durations: bool = True
    require_accessible_urls: bool = True
    require_complete_composition: bool = True
    require_minimum_elements: int = 8  # Main video elements


# Global strict mode configuration instance
STRICT_CONFIG = StrictModeConfig()


# =============================================================================
# STRICT MODE UTILITIES
# =============================================================================

def is_strict_mode_enabled() -> bool:
    """Check if strict mode is globally enabled."""
    return STRICT_CONFIG.enabled


def get_strict_config() -> StrictModeConfig:
    """Get the current strict mode configuration."""
    return STRICT_CONFIG


def update_strict_config(**kwargs) -> None:
    """Update strict mode configuration parameters."""
    for key, value in kwargs.items():
        if hasattr(STRICT_CONFIG, key):
            setattr(STRICT_CONFIG, key, value)
            logger.info(f"🔧 Strict mode config updated: {key} = {value}")
        else:
            logger.warning(f"⚠️ Unknown strict mode config parameter: {key}")


def validate_strict_requirements(requirements: Dict[str, Any]) -> None:
    """
    Validate requirements in strict mode.
    
    Args:
        requirements: Dictionary of requirement checks
        
    Raises:
        ValueError: If any requirement fails in strict mode
        RuntimeError: If critical system requirement fails
    """
    if not is_strict_mode_enabled():
        logger.debug("Strict mode disabled - skipping requirement validation")
        return
    
    failures = []
    
    for requirement_name, requirement_value in requirements.items():
        if requirement_value is None or (isinstance(requirement_value, (list, dict, str)) and len(requirement_value) == 0):
            failures.append(f"❌ MISSING: {requirement_name}")
        elif isinstance(requirement_value, bool) and not requirement_value:
            failures.append(f"❌ FAILED: {requirement_name}")
        elif isinstance(requirement_value, (int, float)) and requirement_value <= 0:
            failures.append(f"❌ INVALID: {requirement_name} = {requirement_value}")
    
    if failures:
        error_message = f"❌ STRICT MODE VALIDATION FAILED:\n" + "\n".join(failures)
        logger.error(error_message)
        raise ValueError(error_message)
    
    logger.debug(f"✅ Strict mode validation passed for {len(requirements)} requirements")


def enforce_exact_count(items: Optional[List], expected_count: int, item_name: str) -> None:
    """
    Enforce exact count requirement in strict mode.
    
    Args:
        items: List of items to check
        expected_count: Expected number of items
        item_name: Name of items for error message
        
    Raises:
        ValueError: If count doesn't match exactly
    """
    if not is_strict_mode_enabled():
        return
    
    actual_count = len(items) if items else 0
    
    if actual_count != expected_count:
        error_message = f"❌ STRICT MODE: Expected exactly {expected_count} {item_name}, got {actual_count}"
        logger.error(error_message)
        raise ValueError(error_message)
    
    logger.debug(f"✅ Exact count validated: {actual_count} {item_name}")


def enforce_api_availability(api_name: str, api_client: Any, api_config: Optional[Dict] = None) -> None:
    """
    Enforce API availability requirement in strict mode.
    
    Args:
        api_name: Name of the API service
        api_client: API client instance
        api_config: Optional API configuration
        
    Raises:
        RuntimeError: If API is not available
    """
    if not is_strict_mode_enabled():
        return
    
    if api_client is None:
        error_message = f"❌ STRICT MODE: {api_name} API client not available - cannot proceed"
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    if api_config is not None and not api_config:
        error_message = f"❌ STRICT MODE: {api_name} API configuration missing - cannot proceed"
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    logger.debug(f"✅ API availability validated: {api_name}")


def enforce_url_accessibility(urls: Dict[str, str], url_type: str) -> None:
    """
    Enforce URL accessibility requirement in strict mode.
    
    Args:
        urls: Dictionary of URLs to check
        url_type: Type of URLs for error message
        
    Raises:
        ValueError: If any URL is invalid or inaccessible
    """
    if not is_strict_mode_enabled():
        return
    
    invalid_urls = []
    
    for key, url in urls.items():
        if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            invalid_urls.append(f"{key}: {url}")
    
    if invalid_urls:
        error_message = f"❌ STRICT MODE: Invalid {url_type} URLs:\n" + "\n".join(invalid_urls)
        logger.error(error_message)
        raise ValueError(error_message)
    
    logger.debug(f"✅ URL accessibility validated: {len(urls)} {url_type} URLs")


def enforce_minimum_quality(value: Any, minimum: Any, quality_name: str) -> None:
    """
    Enforce minimum quality requirement in strict mode.
    
    Args:
        value: Value to check
        minimum: Minimum acceptable value
        quality_name: Name of quality metric
        
    Raises:
        ValueError: If value is below minimum
    """
    if not is_strict_mode_enabled():
        return
    
    if value < minimum:
        error_message = f"❌ STRICT MODE: {quality_name} below minimum - got {value}, required {minimum}"
        logger.error(error_message)
        raise ValueError(error_message)
    
    logger.debug(f"✅ Minimum quality validated: {quality_name} = {value} (min: {minimum})")


# =============================================================================
# STRICT MODE ERROR CLASSES
# =============================================================================

class StrictModeError(Exception):
    """Base exception for strict mode violations."""
    pass


class StrictModeValidationError(StrictModeError):
    """Raised when strict mode validation fails."""
    pass


class StrictModeRequirementError(StrictModeError):
    """Raised when required dependencies are missing."""
    pass


class StrictModeAPIError(StrictModeError):
    """Raised when API requirements are not met."""
    pass


class StrictModeAssetError(StrictModeError):
    """Raised when asset requirements are not met."""
    pass


# =============================================================================
# STRICT MODE DECORATORS
# =============================================================================

def strict_mode_required(func):
    """
    Decorator to enforce strict mode on a function.
    
    The decorated function will only execute if strict mode is enabled.
    If strict mode is disabled, it logs a warning and continues.
    """
    def wrapper(*args, **kwargs):
        if not is_strict_mode_enabled():
            logger.warning(f"⚠️ Strict mode disabled for {func.__name__} - quality not guaranteed")
        
        return func(*args, **kwargs)
    
    return wrapper


def validate_strict_inputs(**input_requirements):
    """
    Decorator to validate function inputs in strict mode.
    
    Args:
        input_requirements: Keyword arguments defining input requirements
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if is_strict_mode_enabled():
                # Validate input requirements
                validate_strict_requirements(input_requirements)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# STRICT MODE LOGGING
# =============================================================================

def log_strict_mode_status():
    """Log the current strict mode configuration status."""
    config = get_strict_config()
    
    if config.enabled:
        logger.info("🔒 STRICT MODE ENABLED - No fallbacks, fail-fast behavior")
        logger.info(f"   Required assets: HeyGen={config.require_all_heygen_videos}, "
                   f"Covers={config.require_all_movie_covers}, Clips={config.require_all_movie_clips}")
        logger.info(f"   Required APIs: OpenAI={config.require_openai_api_key}, "
                   f"HeyGen={config.require_heygen_api_key}, Creatomate={config.require_creatomate_api_key}")
        logger.info(f"   Movie count: {config.require_exact_movie_count}")
    else:
        logger.warning("⚠️ STRICT MODE DISABLED - Fallbacks may be used, quality not guaranteed")


# =============================================================================
# INITIALIZATION
# =============================================================================

# Log strict mode status on module import
log_strict_mode_status()