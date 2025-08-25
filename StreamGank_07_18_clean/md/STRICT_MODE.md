# StreamGank Strict Mode Documentation

## Overview

StreamGank now operates in **STRICT MODE** by default, implementing a **fail-fast** architecture with **no fallbacks**. This ensures production reliability and prevents the generation of incorrect or low-quality videos.

## Core Principles

### 🔒 **Fail-Fast Architecture**

-   **No Fallbacks**: System stops immediately when any error occurs
-   **Complete Validation**: All dependencies checked before processing begins
-   **Clear Error Messages**: Detailed logging for easy debugging
-   **Guaranteed Output**: If a function returns, the output is guaranteed to be valid

### 🚫 **What We Don't Do Anymore**

-   ❌ No placeholder assets when real assets fail to load
-   ❌ No default timing when actual timing calculation fails
-   ❌ No estimated durations when real duration extraction fails
-   ❌ No partial script generation when any script fails
-   ❌ No "best effort" composition with missing elements

### ✅ **What We Enforce**

-   ✅ All 3 HeyGen videos must be generated successfully
-   ✅ All 3 movie covers must be created and uploaded
-   ✅ All 3 movie clips must be processed and uploaded
-   ✅ All API keys must be configured and accessible
-   ✅ All video durations must be accurately calculated
-   ✅ All scripts must be generated and validated
-   ✅ Complete Creatomate composition with exact element count

## Module-by-Module Changes

### 📹 Video Module (`streamgank_modular/video/`)

#### `composition_builder.py`

-   **Removed**: Fallback timing calculations
-   **Added**: Strict validation of all inputs (HeyGen URLs, movie covers, clips)
-   **Added**: URL accessibility validation
-   **Added**: Duration validation (no zero or negative durations)
-   **Added**: Composition structure validation (minimum 8 elements)

```python
# OLD: Fallback behavior
if not heygen_durations:
    return None  # Silent failure

# NEW: Strict mode
if not heygen_durations:
    raise RuntimeError("❌ CRITICAL: Failed to calculate HeyGen video durations - cannot proceed")
```

#### `creatomate_client.py`

-   **Removed**: Silent failures returning `None`
-   **Added**: Comprehensive input validation before processing
-   **Added**: API header validation
-   **Added**: Strict render job submission with guaranteed render ID

### 🤖 AI Module (`streamgank_modular/ai/`)

#### `openai_scripts.py`

-   **Removed**: Partial script generation with fallbacks
-   **Added**: Mandatory OpenAI client validation
-   **Added**: Required genre/platform/content_type validation
-   **Added**: All scripts must be generated (intro + 3 movie hooks)
-   **Added**: Script processing validation (no empty scripts)
-   **Added**: Minimum word count validation

```python
# OLD: Partial generation
if not intro_script:
    logger.warning("Failed to generate intro")
    # Continue anyway

# NEW: Strict mode
if not intro_script:
    raise RuntimeError("❌ CRITICAL: Failed to generate intro script - cannot proceed")
```

### 🏗️ Assets Module (`streamgank_modular/assets/`)

#### Enhanced Poster Generation

-   **Added**: Strict image validation before processing
-   **Added**: Cloudinary upload validation
-   **Added**: Poster dimensions and quality validation

#### Clip Processing

-   **Added**: YouTube URL validation before download
-   **Added**: Clip extraction validation (no empty clips)
-   **Added**: Duration validation for all clips

### ⚙️ Configuration (`streamgank_modular/config/`)

#### New `strict_mode.py`

Complete strict mode configuration system with:

-   Global strict mode settings
-   Requirement validation utilities
-   Custom error classes
-   Validation decorators
-   Comprehensive logging

## Error Handling

### 🚨 Error Types

1. **ValueError**: Invalid or missing required data

    ```
    ❌ CRITICAL: Exactly 3 movie cover URLs required - no fallback available
    ```

2. **RuntimeError**: System failures during processing

    ```
    ❌ CRITICAL: Failed to calculate HeyGen video durations - cannot proceed
    ```

3. **StrictModeError**: Custom strict mode violations
    ```
    ❌ STRICT MODE: Expected exactly 3 movies, got 2
    ```

### 📋 Validation Checks

#### Pre-Process Validation

-   ✅ Exactly 3 movies required
-   ✅ All API keys configured
-   ✅ All required parameters provided
-   ✅ Database connectivity

#### Asset Validation

-   ✅ All HeyGen video URLs valid and accessible
-   ✅ All movie cover URLs valid and accessible
-   ✅ All movie clip URLs valid and accessible
-   ✅ All video durations > 0

#### Output Validation

-   ✅ Complete Creatomate composition (8+ elements)
-   ✅ All scripts generated and validated
-   ✅ All file saves successful
-   ✅ Final video render ID received

## Migration Guide

### For Developers

#### Before (Fallback Mode)

```python
def process_assets(assets):
    try:
        result = process(assets)
        return result if result else default_assets()
    except Exception:
        return default_assets()
```

#### After (Strict Mode)

```python
def process_assets(assets):
    if not assets or len(assets) != 3:
        raise ValueError("❌ CRITICAL: Exactly 3 assets required")

    # All processing must succeed
    result = process(assets)

    if not result:
        raise RuntimeError("❌ CRITICAL: Asset processing failed")

    return result
```

### For Operations

#### Monitoring

-   Monitor for strict mode errors in logs
-   Set up alerts for `❌ CRITICAL` error messages
-   Track success/failure rates (should be binary)

#### Debugging

-   Look for detailed error messages with `❌ CRITICAL` prefix
-   Check dependency availability when errors occur
-   Validate API keys and configurations

### For Testing

#### Test Scenarios

-   Test with missing dependencies (should fail fast)
-   Test with invalid inputs (should provide clear errors)
-   Test with API failures (should stop immediately)
-   Test successful runs (should complete fully)

## Benefits

### 🎯 **Production Reliability**

-   **No Partial Results**: Videos are either perfect or not generated
-   **Predictable Failures**: Clear error conditions and messages
-   **Fast Debugging**: Immediate failure with detailed context

### 🔍 **Quality Assurance**

-   **Complete Assets**: All required components guaranteed present
-   **Validated Output**: Every output passes strict validation
-   **Consistent Results**: No variation based on fallback conditions

### 🚀 **Development Experience**

-   **Clear Error Messages**: Easy to understand what went wrong
-   **Fast Feedback**: Immediate failure instead of silent degradation
-   **Reliable Testing**: Consistent behavior across environments

## Configuration

### Enable/Disable Strict Mode

```python
from streamgank_modular.config.strict_mode import update_strict_config

# Disable for development/testing
update_strict_config(enabled=False)

# Re-enable for production
update_strict_config(enabled=True)
```

### Custom Requirements

```python
# Adjust movie count requirement
update_strict_config(require_exact_movie_count=5)

# Disable specific validations
update_strict_config(require_accessible_urls=False)
```

## Troubleshooting

### Common Issues

#### API Key Missing

```
❌ CRITICAL: OpenAI client not available - cannot generate scripts
```

**Solution**: Set `OPENAI_API_KEY` environment variable

#### Wrong Movie Count

```
❌ CRITICAL: Exactly 3 movies required for script generation
```

**Solution**: Ensure database query returns exactly 3 movies

#### URL Accessibility

```
❌ CRITICAL: Invalid HeyGen URL for movie1: invalid-url
```

**Solution**: Check HeyGen video generation and URL validity

#### Composition Elements

```
❌ CRITICAL: Invalid composition structure - insufficient elements
```

**Solution**: Verify all assets (HeyGen videos, covers, clips) are provided

### Debug Mode

For detailed debugging, enable debug logging:

```python
import logging
logging.getLogger('streamgank_modular').setLevel(logging.DEBUG)
```

This will show all validation steps and strict mode checks.

---

**StreamGank Strict Mode** ensures that every video generated meets the highest quality standards by enforcing complete asset availability and validation at every step. No compromises, no fallbacks, just reliable results.
