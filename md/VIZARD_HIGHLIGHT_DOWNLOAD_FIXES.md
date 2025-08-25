# Vizard AI Highlight Download Fixes

## Summary
This document summarizes the fixes made to the VizardAIClient class to properly download highlight clips from Vizard AI projects.

## Problems Fixed

1. **URL-format Project IDs**: Fixed the client to handle project IDs provided as full URLs (e.g., `https://vizard.ai/project/23103701`) by extracting the numeric ID.

2. **Project ID Formats**: Enhanced client methods to handle various ID formats:
   - URL format (`https://vizard.ai/project/23103701`)
   - Prefixed format (`project-23103701`)
   - Raw numeric format (`23103701`)

3. **API Response Structure**: Updated the clip URL extraction logic to handle different field names:
   - Added support for `videoUrl` field which is the actual field used in the API responses
   - Maintained compatibility with other potential field names (`url`, `fileUrl`, `downloadUrl`, `highlightUrl`)

4. **Status Handling**: Added `force_download` parameter to allow downloading clips even if project status is not "COMPLETED", "SUCCESS", or "DONE".

## Key Files Modified

- `ai/vizard_client.py`
  - Updated `download_highlights` method
  - Enhanced `get_project_status` method
  - Fixed `get_existing_project` method

## New Test Scripts

- `test_specific_vizard_project.py`: Script to test downloading highlights from an existing project with a known ID.

## Testing Results

- Successfully downloaded highlight clips from existing Vizard AI project (ID: 23103701)
- Verified end-to-end workflow with debug flags enabled
- Confirmed project status checking works correctly
- Validated proper handling of URL-format project IDs

## API Endpoints

The client now properly uses the official Vizard AI API endpoint for querying project clips:
```
https://elb-api.vizard.ai/hvizard-server-front/open-api/v1/project/query/{raw_project_id}
```

## Usage Example

```python
from ai.vizard_client import VizardAIClient

# Initialize client
client = VizardAIClient(api_key)

# Download highlights (works with any project ID format)
clips = client.download_highlights(
    project_id="https://vizard.ai/project/23103701",  # URL format works
    movie_title="Movie Title",  # Used for naming downloaded files
    output_dir="./output_clips",
    force_download=True  # Override status check if needed
)
```

## Notes for Future Development

1. The Vizard API status endpoints consistently return 404 errors, but the project query endpoint works correctly.
2. Some projects may return status "UNKNOWN" but still have clips available for download.
3. Continue using `force_download=True` for testing purposes.
