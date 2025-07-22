# StreamGankProject - Heygen to Creatomate Video Pipeline

This project creates automated videos using Heygen AI videos combined with show clips uploaded to Cloudinary, then rendered with Creatomate.

## Core Files for Heygen-Creatomate Pipeline

### 0. Fully Automated Pipeline (New!)
- **automated_video_generator.py**: Complete end-to-end pipeline script that automates the entire process
- **heygen_creatomate_integration.py**: Integration module for HeyGen and Creatomate services

### 1. Heygen Video Generation
- **create_heygen_template_video.py**: Creates Heygen videos using specified template
- **custom_heygen_shows.py**: Customization for Heygen videos about specific shows
- **heygen_script_generator.py**: Generates scripts for Heygen videos
- **preview_heygen_script.py**: Preview tool for Heygen scripts

### 2. Video Processing
- **download_heygen_videos.py**: Downloads completed Heygen videos
- **upload_heygen_to_cloudinary.py**: Uploads Heygen videos to Cloudinary

### 3. Creatomate Integration
- **create_sequential_composition.py**: [RECOMMENDED] Creates sequential videos with no overlaps
- **create_linear_video.py**: Creates linear videos using a stacked timeline
- **create_creatomate_direct.py**: Uses Creatomate templates via direct API calls

## Automated Workflow (Recommended)

Use the automated pipeline for a complete end-to-end solution:

```
python automated_video_generator.py --generate-scripts --enrich-movies --create-video --process-with-creatomate
```

This will:
1. Extract and enrich movie data
2. Generate HeyGen scripts
3. Create HeyGen videos
4. Wait for HeyGen videos to complete processing
5. Process HeyGen videos with Creatomate

### Direct URL Feature (New!)

To speed up the integration process and avoid downloading large video files, use the `--use-direct-urls` flag:

```
python automated_video_generator.py --process-with-creatomate --use-direct-urls
```

This option makes the following improvements:
- Completely bypasses downloading HeyGen videos (which can be slow or fail)
- Uses direct HeyGen CDN URLs in the Creatomate template
- Eliminates the need to upload videos to Cloudinary as an intermediate step
- Significantly speeds up the integration process

### Mock Mode (New!)

For testing without making actual API calls to HeyGen, use the `--mock-mode` flag:

```
python automated_video_generator.py --process-with-creatomate --mock-mode
```

## Traditional Step-by-Step Workflow

If you prefer the manual approach, you can still use individual scripts:

1. Generate Heygen scripts with `heygen_script_generator.py`
2. Preview scripts with `preview_heygen_script.py`
3. Create Heygen videos with `create_heygen_template_video.py`
4. Download videos with `download_heygen_videos.py`
5. Upload to Cloudinary with `upload_heygen_to_cloudinary.py`
6. Create final video with `create_sequential_composition.py`

## CLI Options for Automated Pipeline

```
python automated_video_generator.py --help
```

Key options:
- `--generate-scripts`: Generate HeyGen scripts from movie data
- `--enrich-movies`: Enrich movie data with additional metadata
- `--create-video`: Create HeyGen videos using generated scripts
- `--process-with-creatomate`: Process HeyGen videos with Creatomate
- `--use-direct-urls`: Use direct HeyGen video URLs in Creatomate (bypass download)
- `--mock-mode`: Run in mock mode without making real API calls
- `--input`: Input JSON file path
- `--output`: Output JSON file path
- `--wait-for-completion`: Wait for all HeyGen videos to complete

## Environment Variables (.env)
- HEYGEN_API_KEY - Required for HeyGen API access
- CLOUDINARY_CLOUD_NAME - Required for Cloudinary uploads
- CLOUDINARY_API_KEY - Required for Cloudinary uploads
- CLOUDINARY_API_SECRET - Required for Cloudinary uploads
- CREATOMATE_API_KEY - Required for Creatomate video composition
- SUPABASE_URL - Optional for database storage
- SUPABASE_KEY - Optional for database storage
