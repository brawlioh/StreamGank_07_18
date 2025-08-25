# Manual Opus Clip Workflow Guide

This document provides detailed instructions for using the manual Opus Clip workflow feature in the StreamGank video generation pipeline.

## Overview

The manual Opus Clip workflow allows you to generate highlight clips from movie trailers using the Opus Clip web interface when API access is unavailable or restricted. This process:

1. Generates clickable URLs for processing movie trailers with Opus Clip's web interface
2. Pauses the workflow while you manually download and organize the highlight clips
3. Resumes after you've prepared the clips, continuing with the Creatomate video assembly

## Prerequisites

- YouTube trailers associated with each movie in your database or sample data
- Web browser to access the Opus Clip web interface
- Basic knowledge of file management

## Usage Instructions

### 1. Running the Workflow

Launch the workflow with the following command:

```bash
python main.py --country US --platform Netflix --genre Horror --content-type Movies --num-movies 3 --skip-heygen --use-manual-opus
```

Key flags:
- `--skip-heygen`: Reuses existing HeyGen videos instead of generating new ones
- `--use-manual-opus`: Activates the manual Opus Clip workflow

### 2. Following the Manual Instructions

When the workflow reaches the manual Opus Clip step, it will:

1. Display instructions for each movie trailer
2. Generate clickable URLs for the Opus Clip web interface
3. Pause and wait for your input

### 3. Processing Trailers with Opus Clip

For each trailer:

1. Open the generated URL in your browser (example: `https://clip.opus.pro?videoUrl=https%3A//www.youtube.com/watch%3Fv%3D-m5Qwjs_-rc&clipLength=15&numClips=3`)
2. Wait for Opus Clip to process the video (typically 1-2 minutes)
3. Download the generated highlight clips
4. Save the clips to the `temp_clips` directory following the naming convention: `highlight_VIDEO_ID_15s_1.mp4`, `highlight_VIDEO_ID_15s_2.mp4`, etc.

Example naming for a trailer with ID `-m5Qwjs_-rc`:
- `highlight_-m5Qwjs_-rc_15s_1.mp4`
- `highlight_-m5Qwjs_-rc_15s_2.mp4`
- `highlight_-m5Qwjs_-rc_15s_3.mp4`

### 4. Resuming the Workflow

Once you've downloaded and saved all clips:

1. Return to the terminal where the workflow is paused
2. Press Enter to resume the workflow
3. The system will check for clips in the `temp_clips` directory and proceed to the final Creatomate assembly

## Troubleshooting

### No clips found in temp_clips directory

If you press Enter to resume the workflow but didn't place any clips in the `temp_clips` directory:
- The workflow will display a warning but continue to the Creatomate assembly step
- The resulting video will not contain the Opus Clip highlights

### Invalid clip naming

Ensure clip filenames follow the exact format: `highlight_VIDEO_ID_15s_1.mp4` 
- The `VIDEO_ID` must match the YouTube video ID from the URL
- The numbering (`1.mp4`, `2.mp4`, etc.) helps maintain proper sequence

## Integration with Existing Features

The manual Opus Clip workflow works seamlessly with:

1. **HeyGen Reuse**: Use with `--skip-heygen` to bypass HeyGen API requirements
2. **Sample Data Fallback**: Automatically uses sample data if database extraction fails
3. **Cloudinary Integration**: Works with Cloudinary-hosted HeyGen videos

## Example Workflow

```
[STEP 6.5] Manual Opus Clip Workflow - Generating instructions
   📋 Processing trailer for Sandman with Manual Opus Clip...

================================================================================
📝 MANUAL OPUS CLIP PROCESSING INSTRUCTIONS
================================================================================
1. Open this URL in your browser: https://clip.opus.pro?videoUrl=https%3A//www.youtube.com/watch%3Fv%3D-m5Qwjs_-rc&clipLength=15&numClips=3
2. Wait for Opus Clip to process the video (this may take 1-2 minutes)
3. When processing is complete, download the generated highlights
4. Save the downloaded clips to the 'temp_clips' directory
5. Name the files as 'highlight_-m5Qwjs_-rc_15s_1.mp4', etc.
================================================================================

   ✅ Manual Opus Clip URL generated for Sandman

================================================================================
🛑 WORKFLOW PAUSED FOR MANUAL OPUS CLIP PROCESSING
================================================================================
1. Visit the Opus Clip URLs provided above in your browser
2. Download the generated highlight clips
3. Save them to the 'temp_clips' directory with the specified naming format
4. Once all clips are ready, resume the workflow

⏸️  Press Enter when you've completed the manual Opus Clip processing...
```

## Benefits

- No API key required for Opus Clip
- Works with any YouTube trailer URL
- Full control over clip selection and quality
- Seamless integration with the existing StreamGank workflow
