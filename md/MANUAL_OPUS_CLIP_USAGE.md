# Manual Opus Clip Workflow Guide

This guide explains how to use the new manual Opus Clip workflow for generating high-quality video highlights without requiring an API key subscription.

## Overview

Since the Opus Clip API is not available with your monthly subscription, we've created an alternative workflow that:

1. Generates a direct link to the Opus Clip web interface with your YouTube URL pre-filled
2. Allows you to manually download the generated highlights
3. Integrates these manually downloaded clips into your existing workflow

## How to Use the Manual Workflow

### 1. Run your script with the `--use-manual-opus` flag:

```bash
python main.py --country US --platform Netflix --genre Horror --use-manual-opus
```

### 2. For each movie trailer, the system will:

- Generate a URL to the Opus Clip web interface
- Display step-by-step instructions in the terminal
- Continue processing other movies while you handle the manual steps

### 3. Manual Processing Steps:

1. Click the Opus Clip URL provided in the terminal
2. Wait for Opus Clip to process the video (1-2 minutes)
3. Download the generated highlights
4. Save the downloaded clips to the `temp_clips` directory (or whatever directory you're using)
5. Name the files according to the pattern shown in the instructions

### 4. Integration with Your Workflow:

- The manually downloaded clips can be processed through the rest of your pipeline
- For proper integration, follow the naming pattern exactly:
  - `highlight_{youtube_id}_{clip_length}s_1.mp4` (where 1 can be any number for multiple clips)

## Benefits of this Approach

- **No API Key Required**: Uses the free web interface
- **Same Quality Results**: Gets the same AI-powered highlights and subtitles
- **Integrated Workflow**: Can still be part of your automated pipeline
- **Fallback Available**: System will still use the traditional method while waiting for manual downloads

## Command Line Options

| Option | Description |
|--------|-------------|
| `--use-manual-opus` | Enable the manual Opus Clip workflow |
| `--opus-api-key` | (Optional) Use API if you get access in the future |

## Customization

You can customize the clip parameters by modifying the `generate_opus_clip_web_url` function in `legacy_streamgank_helpers.py`:

```python
def generate_opus_clip_web_url(video_url: str, clip_length: int = 15) -> str:
    # You can modify parameters here:
    opus_web_url = f"https://clip.opus.pro?videoUrl={urllib.parse.quote(video_url)}&clipLength={clip_length}&numClips=3"
    # Add more parameters as needed
    return opus_web_url
```

Available URL parameters include:
- `clipLength`: Length of clips in seconds
- `numClips`: Number of clips to generate
- `subtitlesEnabled`: Whether to add subtitles (true/false)
- `aspectRatio`: Video aspect ratio (vertical/horizontal)
