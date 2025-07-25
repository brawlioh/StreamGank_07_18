# StreamGank Unit Tests

This directory contains all unit tests for the StreamGank video generation system.

## Quick Start

### Test Only Smooth Scrolling Video (6 seconds - Always 60 FPS Ultra!)

```bash
# Test with default settings (FR, Horror, Netflix, Series) - NOW 60 FPS ULTRA by default!
python tests/test_smooth_scrolling.py

# Test with custom parameters (still 60 FPS ultra)
python tests/test_smooth_scrolling.py --country US --genre Action --platform "Prime Video" --content-type Film

# Test different scroll distances (always 60 FPS ultra)
python tests/test_smooth_scrolling.py --scroll-distance 1.0  # Shorter scroll
python tests/test_smooth_scrolling.py --scroll-distance 2.0  # Longer scroll
python tests/test_smooth_scrolling.py --no-smooth-scroll      # Disable micro-scrolling
```

### Run All Tests

```bash
# Run all tests
python tests/run_all_tests.py

# Run only quick tests (recommended for development)
python tests/run_all_tests.py --quick

# List available tests
python tests/run_all_tests.py --list
```

### Run Specific Test

```bash
# Run specific test by ID
python tests/run_all_tests.py --test smooth_scrolling
python tests/run_all_tests.py --test creatomate
```

## Available Tests

### ✅ Quick Tests (recommended for frequent testing)

| Test ID            | Description                                                | Module                     |
| ------------------ | ---------------------------------------------------------- | -------------------------- |
| `smooth_scrolling` | **6-second ultra 60 FPS micro-scrolling video generation** | `test_smooth_scrolling.py` |

### ⏳ Slow Tests (run occasionally)

| Test ID               | Description                                          | Module                        |
| --------------------- | ---------------------------------------------------- | ----------------------------- |
| `dynamic_clips`       | Dynamic movie trailer clip processing                | `test_dynamic_clips.py`       |
| `portrait_conversion` | Video portrait conversion                            | `test_portrait_conversion.py` |
| `cinematic_portrait`  | **Cinematic portrait with Gaussian blur background** | `test_cinematic_portrait.py`  |
| `enhanced_posters`    | **Enhanced movie posters with metadata overlays**    | `test_enhanced_posters.py`    |
| `video_quality`       | Video quality processing                             | `test_video_quality.py`       |

## Test Parameters

### Smooth Scrolling Test Parameters (Always 60 FPS Ultra!)

```bash
# StreamGank filters
--country FR|US|UK|CA                    # Country filter (default: FR)
--genre "Horror"|"Action"|"Drama"        # Genre filter (default: Horror)
--platform "Netflix"|"Prime Video"       # Platform filter (default: Netflix)
--content-type "Series"|"Film"           # Content type (default: Series)

# Scrolling settings (Always 60 FPS!)
--smooth-scroll                          # Enable micro-scrolling (default)
--no-smooth-scroll                       # Disable micro-scrolling
--scroll-distance 1.0|1.5|2.0           # Scroll distance multiplier (default: 1.5)

# Output options
--no-upload                              # Skip Cloudinary upload
--verbose                                # Enable verbose logging
```

## Example Usage Scenarios

### 1. Quick Development Testing

```bash
# Test ultra-smooth 60 FPS scrolling with different distances
python tests/test_smooth_scrolling.py --scroll-distance 1.0   # Short scroll
python tests/test_smooth_scrolling.py --scroll-distance 2.0   # Longer scroll
```

### 2. Full Quality Assurance

```bash
# Run all quick tests
python tests/run_all_tests.py --quick

# If quick tests pass, run all tests
python tests/run_all_tests.py
```

### 3. Debugging Specific Issues

```bash
# Test with verbose output
python tests/test_smooth_scrolling.py --verbose --no-upload

# Test without micro-scrolling
python tests/test_smooth_scrolling.py --no-smooth-scroll
```

## Test Output

Each test provides:

-   ✅ **Success/Failure status**
-   ⏱️ **Execution duration**
-   📁 **Generated file paths**
-   ☁️ **Cloudinary URLs** (if uploaded)
-   📊 **Video analysis** (duration, resolution, file size)
-   🎯 **Target validation** (6-second duration check)

## Directory Structure

```
tests/
├── README.md                    # This documentation
├── __init__.py                  # Package initialization
├── run_all_tests.py            # Test runner script
├── test_smooth_scrolling.py    # 6-second 60 FPS ultra video test ⭐
├── test_dynamic_clips.py       # Movie clips processing test
├── test_portrait_conversion.py # Portrait conversion test
├── test_cinematic_portrait.py  # Cinematic portrait with Gaussian blur test
├── test_enhanced_posters.py    # Enhanced movie posters with metadata test
└── test_video_quality.py       # Video quality test
```

## Best Practices

1. **Use `test_smooth_scrolling.py` for frequent testing** - it's fast and focused, always 60 FPS ultra!
2. **Run `--quick` tests during development** - saves time
3. **Use `--verbose` when debugging** - provides detailed output
4. **Test different scroll distances** for optimal readability:
    - `1.0` = Very short, minimal scrolling (60 FPS)
    - `1.5` = Default, balanced readability (60 FPS)
    - `2.0` = Longer scrolling, more content (60 FPS)

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure you're running from the project root directory
2. **FFmpeg not found**: Install FFmpeg for video analysis
3. **Cloudinary upload fails**: Check your Cloudinary credentials in `.env`
4. **Browser issues**: Ensure Playwright browsers are installed: `playwright install`

### Getting Help

```bash
# Get help for specific test
python tests/test_smooth_scrolling.py --help

# Get help for test runner
python tests/run_all_tests.py --help
```
