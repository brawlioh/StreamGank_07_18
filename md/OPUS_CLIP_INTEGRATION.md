# Opus Clip AI Integration for StreamGank

This document explains how to use the new Opus Clip AI integration for extracting high-quality highlights from YouTube trailers.

## Overview

The StreamGank system now features AI-powered highlight extraction using the Opus Clip API. This integration:

1. Automatically extracts the most engaging moments from YouTube trailers
2. Generates professional subtitles for each highlight
3. Creates vertical-format (9:16) clips for TikTok/Instagram
4. Falls back to traditional extraction if needed

## How It Works

The new `extract_highlights` function serves as a unified entry point with intelligent fallback:

```python
highlight_clip = extract_highlights(
    video_url=trailer_url,
    api_key=opus_api_key,
    output_dir=output_dir,
    clip_length=15
)
```

### Processing Flow

1. If an Opus Clip API key is provided:
   - Submit YouTube URL to Opus Clip API
   - Wait for AI processing to complete
   - Download the resulting highlight clips with subtitles
   
2. If no API key is provided OR if Opus Clip processing fails:
   - Automatically falls back to `extract_second_highlight`
   - Uses the traditional FFmpeg-based extraction method
   - No subtitles in fallback mode

## Getting Started

### 1. Get an Opus Clip API Key

Sign up at [opus.pro](https://opus.pro) to obtain an API key.

### 2. Set Your API Key

Add your API key to your `.env` file:

```
OPUS_CLIP_API_KEY=your_opus_clip_api_key_here
```

### 3. Run with the New Feature

```bash
python main.py --country US --platform Netflix --genre Horror --opus-api-key YOUR_API_KEY
```

Or use the environment variable from your `.env` file:

```bash
python main.py --country US --platform Netflix --genre Horror
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--opus-api-key` | Opus Clip API key (overrides environment variable) |

## Configuration Settings

The integration uses these default settings (configurable in `config/settings.py`):

```python
'opus_clip': {
    'clip_length': 15,       # 15-second highlights
    'num_clips': 3,          # Generate 3 highlight options
    'aspect_ratio': 'vertical',  # 9:16 for TikTok/Instagram
    'subtitle_style': 'dynamic'  # Dynamic subtitles
}
```

## Benefits Over Traditional Method

1. **AI-Powered Selection**: Identifies the most engaging moments automatically
2. **Professional Subtitles**: Generates accurate subtitles for better engagement
3. **Better Composition**: Designed specifically for mobile-first vertical video
4. **Robust Fallback**: Falls back to traditional method if API is unavailable

## Troubleshooting

If you encounter issues:

1. Check your API key is correctly set
2. Ensure the YouTube URL is publicly accessible
3. Allow sufficient time for processing (can take 1-3 minutes)
4. Check the logs for detailed error messages
5. Verify your network connection is stable

The fallback mechanism will automatically activate if any issues occur with the Opus Clip API.
