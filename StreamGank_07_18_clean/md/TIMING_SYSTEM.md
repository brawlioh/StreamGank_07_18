# StreamGank Video Timing System

## Overview

The StreamGank video timing system ensures **PRECISE DURATION EXTRACTION** for all video assets (HeyGen videos and movie clips) to create accurate Creatomate compositions. This makes it easy to combine, adjust, and debug video timing.

## Core Principle

> **"Get the actual length of EVERYTHING so Creatomate timing is precise"**

All durations are extracted from **actual video files** using FFprobe - no estimates, no fallbacks, no approximations. This ensures perfect synchronization and timing in the final rendered video.

## Duration Extraction Process

### 🎤 HeyGen Video Durations

```python
def calculate_video_durations(video_urls: Dict[str, str]) -> Dict[str, float]:
    """
    Extract ACTUAL durations from HeyGen videos using FFprobe.

    Returns precise durations (2 decimal places) for:
    - heygen1: Duration of first HeyGen video
    - heygen2: Duration of second HeyGen video
    - heygen3: Duration of third HeyGen video
    """
```

**Process:**

1. Receive HeyGen video URLs from HeyGen API
2. Use FFprobe to extract actual video duration
3. Round to 2 decimal places for precision
4. Validate durations are reasonable (3-60 seconds)
5. Log detailed timing information

**Sample Output:**

```
📏 STRICT MODE: Getting ACTUAL durations for 3 videos
🔍 Extracting ACTUAL duration: heygen1
✅ heygen1: 8.25s (ACTUAL - ready for Creatomate)
🔍 Extracting ACTUAL duration: heygen2
✅ heygen2: 7.83s (ACTUAL - ready for Creatomate)
🔍 Extracting ACTUAL duration: heygen3
✅ heygen3: 9.12s (ACTUAL - ready for Creatomate)
```

### 🎬 Movie Clip Durations

```python
def estimate_clip_durations(clip_urls: List[str]) -> Dict[str, float]:
    """
    Extract ACTUAL durations from movie clips using FFprobe.

    Returns precise durations (2 decimal places) for:
    - clip1: Duration of first movie clip
    - clip2: Duration of second movie clip
    - clip3: Duration of third movie clip
    """
```

**Process:**

1. Receive movie clip URLs from Cloudinary
2. Use FFprobe to extract actual video duration
3. Round to 2 decimal places for precision
4. Validate durations are reasonable (1-30 seconds)
5. Log detailed timing information

**Sample Output:**

```
📹 STRICT MODE: Getting ACTUAL durations for movie clips
🔍 Extracting ACTUAL duration: clip1
✅ clip1: 12.45s (ACTUAL - ready for Creatomate)
🔍 Extracting ACTUAL duration: clip2
✅ clip2: 11.78s (ACTUAL - ready for Creatomate)
🔍 Extracting ACTUAL duration: clip3
✅ clip3: 13.22s (ACTUAL - ready for Creatomate)
```

## Creatomate Composition Timing

### 📐 Video Timeline Structure

```
INTRO (1s) → HEYGEN1 (8.25s) → CLIP1 (12.45s) → HEYGEN2 (7.83s) → CLIP2 (11.78s) → HEYGEN3 (9.12s) → CLIP3 (13.22s) → OUTRO (3s)
```

### 🎯 Precise Timing Calculation

```python
# Total video length using ACTUAL durations
total_video_length = (1 +                    # Intro
                     heygen_durations["heygen1"] +     # 8.25s
                     clip_durations["clip1"] +         # 12.45s
                     heygen_durations["heygen2"] +     # 7.83s
                     clip_durations["clip2"] +         # 11.78s
                     heygen_durations["heygen3"] +     # 9.12s
                     clip_durations["clip3"] +         # 13.22s
                     3)                       # Outro

# Result: 66.65s total video length
```

### 📊 Detailed Timing Breakdown Log

```
🎬 CREATOMATE COMPOSITION TIMING BREAKDOWN:
   📐 INTRO: 0.00s → 1.00s (1.00s duration)
   🎤 HEYGEN1: 1.00s → 9.25s (8.25s duration)
   🎬 CLIP1: 9.25s → 21.70s (12.45s duration)
   🎤 HEYGEN2: 21.70s → 29.53s (7.83s duration)
   🎬 CLIP2: 29.53s → 41.31s (11.78s duration)
   🎤 HEYGEN3: 41.31s → 50.43s (9.12s duration)
   🎬 CLIP3: 50.43s → 63.65s (13.22s duration)
   📐 OUTRO: 63.65s → 66.65s (3.00s duration)
📊 TOTAL VIDEO LENGTH: 66.65s (1.1 minutes)
```

## Poster Timing Integration

### 🖼️ Poster Overlay Timing

Posters are positioned based on actual HeyGen video durations:

```python
# Poster 1: Last 3 seconds of HeyGen 1
poster1_time = 1.00 + max(0, heygen_durations["heygen1"] - 3.0)  # 6.25s
poster1_duration = min(3.0, heygen_durations["heygen1"])         # 3.00s

# Result: Poster 1 shows from 6.25s to 9.25s
```

**Sample Poster Timing Log:**

```
🖼️ POSTER TIMING:
   🖼️ POSTER1: 6.25s → 9.25s (3.00s duration)
   🖼️ POSTER2: 26.03s → 29.03s (3.00s duration)
   🖼️ POSTER3: 47.93s → 49.93s (2.00s duration)
```

## Duration Validation & Quality Checks

### 🔍 Consistency Validation

```python
def validate_duration_consistency(heygen_durations, clip_durations):
    """
    Validates all durations are reasonable and consistent for Creatomate.
    Logs detailed statistics for easy debugging.
    """
```

**Validation Checks:**

-   ✅ All required durations present
-   ✅ HeyGen durations: 3-60 seconds
-   ✅ Clip durations: 1-30 seconds
-   ✅ Content balance (HeyGen vs Clips ratio)
-   ✅ Total duration reasonable

**Sample Validation Log:**

```
🔍 VALIDATING DURATION CONSISTENCY FOR CREATOMATE:
   🎤 Total HeyGen content: 25.20s
   🎬 Total clip content: 37.45s
   📊 Total video content: 62.65s
   🎯 Estimated final video: ~66.65s
   📈 HeyGen: 40.2% | Clips: 59.8%
✅ Duration consistency validated - ready for Creatomate timing
```

## Debugging Features

### 📋 Composition Structure Logging

```
📋 CREATOMATE COMPOSITION STRUCTURE:
   🎬 Resolution: 1080x1920
   🎞️ Frame Rate: 30 fps
   📊 Total Elements: 12

📝 ELEMENT BREAKDOWN:
    1. 🖼️ IMAGE | Track 1 | 0s → 1s | streamGank_intro_cwefmt.jpg
    2. 🎤 HEYGEN | Track 1 | autos → autos
    3. 🎬 CLIP | Track 1 | autos → 12.45s
    4. 🎤 HEYGEN | Track 1 | autos → autos
    5. 🎬 CLIP | Track 1 | autos → 11.78s
    6. 🎤 HEYGEN | Track 1 | autos → autos
    7. 🎬 CLIP | Track 1 | autos → 13.22s
    8. 🖼️ IMAGE | Track 1 | autos → 3s | streamgank_bg_heecu7.png
    9. 🖼️ IMAGE | Track 2 | 6.25s → 3.0s | poster1.jpg
   10. 🖼️ IMAGE | Track 2 | 26.03s → 3.0s | poster2.jpg
   11. 🖼️ IMAGE | Track 2 | 47.93s → 2.0s | poster3.jpg
   12. 🏷️ BRANDING | Track 3 | 1s → 59.65s | Composition-228
```

### 🔗 Asset URL Tracking

All asset URLs are logged for easy debugging:

```
🔗 ASSET URLS IN COMPOSITION:
   🎤 movie1: https://resource.heygen.ai/video/abc123.mp4
   🎤 movie2: https://resource.heygen.ai/video/def456.mp4
   🎤 movie3: https://resource.heygen.ai/video/ghi789.mp4
   🖼️ poster1: https://res.cloudinary.com/dodod8s0v/image/upload/v123/poster1.jpg
   🖼️ poster2: https://res.cloudinary.com/dodod8s0v/image/upload/v456/poster2.jpg
   🖼️ poster3: https://res.cloudinary.com/dodod8s0v/image/upload/v789/poster3.jpg
   🎬 clip1: https://res.cloudinary.com/dodod8s0v/video/upload/v123/clip1.mp4
   🎬 clip2: https://res.cloudinary.com/dodod8s0v/video/upload/v456/clip2.mp4
   🎬 clip3: https://res.cloudinary.com/dodod8s0v/video/upload/v789/clip3.mp4
```

## FFprobe Integration

### 🛠️ Technical Implementation

```python
def get_video_duration_from_url(video_url: str) -> Optional[float]:
    """Extract video duration using FFprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        video_url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        probe_data = json.loads(result.stdout)
        duration = float(probe_data['format']['duration'])
        return duration

    return None
```

**Features:**

-   ✅ Supports HTTP/HTTPS video URLs
-   ✅ 30-second timeout for reliability
-   ✅ JSON output parsing
-   ✅ Error handling and logging
-   ✅ Cross-platform compatibility

## Error Handling

### 🚫 Strict Mode Failures

If ANY duration extraction fails:

```
❌ CRITICAL: Failed to extract ACTUAL durations:
   • heygen2 -> https://resource.heygen.ai/video/invalid.mp4
   • clip3 -> https://res.cloudinary.com/invalid/clip.mp4
🚫 STRICT MODE: Cannot use estimates - Creatomate needs precise timing
```

**No Fallbacks:**

-   ❌ No default durations
-   ❌ No estimated values
-   ❌ No "best guess" timing
-   ✅ Process stops immediately

## Benefits

### 🎯 Precise Creatomate Composition

1. **Accurate Timing**: Every element positioned precisely
2. **Perfect Sync**: Audio/video alignment guaranteed
3. **Easy Debugging**: Detailed logs show exact timings
4. **Predictable Results**: Same input = same timing always

### 🔧 Development & Debugging

1. **Clear Logging**: Every duration extraction logged
2. **Timing Breakdown**: Second-by-second composition view
3. **Asset Tracking**: All URLs logged for reference
4. **Validation Checks**: Quality assurance built-in

### 🚀 Production Reliability

1. **No Surprises**: All timing calculated from real assets
2. **Fail-Fast**: Invalid assets caught immediately
3. **Consistent Output**: Reproducible timing every time
4. **Quality Guaranteed**: All durations validated

---

**The StreamGank timing system ensures that Creatomate receives perfectly timed compositions with actual durations from all video assets, making it easy to combine, adjust, and debug video timing at every step.**
