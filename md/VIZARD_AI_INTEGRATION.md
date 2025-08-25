# Vizard AI Integration for Automatic Highlight Extraction

This feature integrates the Vizard AI API for automatic extraction of highlights from movie trailers, eliminating the need for manual highlight selection.

## Overview

The Vizard AI integration provides a fully automated alternative to the manual Opus Clip workflow. It uses AI to analyze YouTube trailers and automatically extract the most engaging segments, creating professionally edited highlight clips with subtitles.

## Key Features

- **Automatic Highlight Detection**: AI-powered identification of engaging moments in trailers
- **Subtitle Integration**: Automatically adds subtitles to highlight clips
- **Full Automation**: No manual intervention required for clip selection
- **YouTube Integration**: Works directly with YouTube trailer URLs
- **Cloudinary Upload**: Automatic upload to Cloudinary for Creatomate compatibility

## Requirements

1. A valid Vizard AI API key set in your `.env` file:
   ```
   VIZARD_API_KEY=your_vizard_api_key_here
   ```

2. Valid YouTube trailer URLs in your movie data

## Usage

Add the `--use-vizard-ai` flag to your StreamGank command:

```bash
python main.py --country US --platform Netflix --genre Action --content-type movie \
  --num-movies 3 --use-vizard-ai
```

### Command Line Arguments

- `--use-vizard-ai`: Enable Vizard AI highlight extraction (mutually exclusive with `--use-manual-opus`)
- `--num-movies`: Number of movies to process (default: 3)

## How It Works

1. The system extracts movie data with trailer URLs from the database
2. For each movie with a valid YouTube trailer URL:
   - Vizard AI analyzes the trailer to identify engaging moments
   - AI extracts the highlight clip with subtitles
   - The clip is downloaded to local storage (`temp_clips` directory)
3. All downloaded clips are uploaded to Cloudinary with proper formatting
4. Cloudinary URLs replace the standard movie clips in the Creatomate composition

## Example Workflow

```
[STEP 6.5] Vizard AI Highlight Extraction - Processing trailers
   📋 Processing trailer for "The Matrix" with Vizard AI...
   ✅ Created Vizard AI project abc123
   ⏳ Waiting for Vizard AI to process project abc123...
   📊 Current status: PROCESSING (attempt 1/30)
   📊 Current status: COMPLETED (attempt 2/30)
   📥 Downloading 1 clips from project abc123...
   ✅ Downloaded 1/1 clips
   📝 Renamed highlight to: vizard_dQw4w9WgXcQ_The_Matrix_1.mp4
   
🎬 Processing 1 Vizard AI highlights for Creatomate assembly...
   📤 Uploading highlight 1/1: vizard_dQw4w9WgXcQ_The_Matrix_1.mp4
   ✅ Successfully uploaded: vizard_dQw4w9WgXcQ_The_Matrix_1.mp4
   🌐 Cloudinary URL: https://res.cloudinary.com/example/video/upload/v123/vizard_ai_clips/vizard_highlight_1.mp4
   🔄 Replaced 1/3 original clips with Vizard AI clips
   ℹ️ Keeping 2/3 original clips
```

## Advanced Options

You can modify the `extract_highlights_with_vizard` function in `ai/extract_highlights.py` to adjust:

1. Number of highlight clips per movie (`num_clips` parameter)
2. Preferred clip length (`clip_length` parameter - 1=short, 2=medium, 3=long)
3. Output directory for temporary clip storage

## Troubleshooting

If you encounter errors:

1. **Invalid API Key**: Ensure your Vizard AI API key is correctly set in `.env`
2. **Invalid YouTube URLs**: Verify that trailer URLs start with "https://www.youtube.com"
3. **Processing Failures**: Check Vizard AI status responses for error details
4. **File Permission Issues**: Ensure the `temp_clips` directory is writable

## Implementation Notes

- **Local File Usage**: Vizard AI downloads clips to local storage before uploading to Cloudinary
- **Cloudinary Integration**: All clips must be uploaded to Cloudinary for Creatomate compatibility
- **Fallback Mechanism**: If Vizard AI fails, the system falls back to using original clips
