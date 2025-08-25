# Vizard AI Manual Clip Integration

This document explains how to use the manual Vizard AI clip integration feature, which allows you to:

1. Use pre-downloaded highlight clips from Vizard AI
2. Avoid unnecessary API credit usage
3. Integrate manually downloaded clips seamlessly into the StreamGank workflow

## Background

The Vizard AI integration allows automatic extraction of highlights from YouTube trailers. However, sometimes API connectivity issues or rate limiting can prevent direct extraction. This manual integration provides a fallback that works with clips you've already downloaded from the Vizard AI dashboard.

## How to Use

### Step 1: Download Clips from Vizard AI Dashboard

1. Log in to your Vizard AI dashboard
2. Navigate to your completed project
3. Download the highlight clips to a local directory (e.g., `test_vizard_clips/`)

### Step 2: Process the Downloaded Clips

Use the `integrate_vizard_clips.py` script to process the downloaded clips:

```bash
python integrate_vizard_clips.py \
  --clips-dir test_vizard_clips/ \
  --output-file test_clips_metadata.json \
  --upload-to-cloudinary
```

Arguments:
- `--clips-dir`: Directory containing downloaded Vizard clips
- `--output-file`: Where to save the generated metadata
- `--upload-to-cloudinary`: (Optional) Upload clips to Cloudinary
- `--folder`: (Optional) Cloudinary folder name (default: "vizard_ai_clips")

### Step 3: Run the StreamGank Workflow with Metadata

Use the generated metadata file with the main workflow:

```bash
python main.py \
  --country US \
  --platform Netflix \
  --genre Action \
  --content-type movie \
  --use-vizard-ai \
  --vizard-metadata test_clips_metadata.json
```

## Metadata File Format

The generated metadata JSON file has the following structure:

```json
{
  "clips": [
    {
      "name": "Movie Title 1",
      "local_path": "/path/to/clip1.mp4",
      "url": "https://res.cloudinary.com/your-cloud/video/upload/v1234567890/vizard_ai_clips/clip1.mp4"
    },
    {
      "name": "Movie Title 2",
      "local_path": "/path/to/clip2.mp4",
      "url": "https://res.cloudinary.com/your-cloud/video/upload/v1234567890/vizard_ai_clips/clip2.mp4"
    }
  ],
  "timestamp": "2023-08-17T14:35:22.123456",
  "total_clips": 2
}
```

## Environment Variables

You can also set the metadata file path using an environment variable:

```bash
export VIZARD_CLIPS_METADATA=/path/to/test_clips_metadata.json
```

## Workflow Behavior

When using manual clips integration:

1. If a metadata file is provided (via command line or environment variable), the workflow will use the pre-processed clips instead of making API calls to Vizard AI
2. If the clips in the metadata file already have Cloudinary URLs, they'll be used directly
3. If only local paths are available, the clips will be uploaded to Cloudinary first
4. The workflow will use as many clips as available from the metadata file

## Troubleshooting

- **Metadata file not found**: Check that the path provided to `--vizard-metadata` is correct
- **No clips in metadata**: Ensure the metadata file has the correct structure with non-empty clips array
- **Error loading metadata**: Verify the JSON format is valid
- **Cloudinary upload failure**: Check your Cloudinary API credentials in the .env file
