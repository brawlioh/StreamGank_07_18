# StreamGankProject - Heygen to Creatomate Video Pipeline

This project creates automated videos using Heygen AI videos combined with show clips uploaded to Cloudinary, then rendered with Creatomate.

## Core Files for Heygen-Creatomate Pipeline

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

## Workflow

1. Generate Heygen scripts with `heygen_script_generator.py`
2. Preview scripts with `preview_heygen_script.py`
3. Create Heygen videos with `create_heygen_template_video.py`
4. Download videos with `download_heygen_videos.py`
5. Upload to Cloudinary with `upload_heygen_to_cloudinary.py`
6. Create final video with `create_sequential_composition.py`

## Environment Variables (.env)
- HEYGEN_API_KEY
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET
- CREATOMATE_API_KEY
