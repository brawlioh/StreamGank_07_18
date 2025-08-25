#!/bin/bash
# Test script for direct Vizard AI API integration
# This script extracts highlights from YouTube trailers via Vizard AI
# and uploads them to Cloudinary for use with Creatomate

# Set defaults
YOUTUBE_URL=""
MOVIE_TITLE="Test Movie"
NUM_CLIPS=3
CLIP_LENGTH=2
OUTPUT_DIR="temp_clips"
DEBUG_MODE=""

# Display help
function show_help {
  echo "Usage: ./vizard_direct_api_test.sh --youtube-url <URL> [options]"
  echo ""
  echo "Options:"
  echo "  --youtube-url URL      YouTube URL to process (required)"
  echo "  --movie-title TITLE    Movie title for clips (default: Test Movie)"
  echo "  --num-clips N          Number of clips to extract (default: 3)"
  echo "  --clip-length N        Clip length: 1=short, 2=medium, 3=long (default: 2)"
  echo "  --output-dir DIR       Directory for clips (default: temp_clips)"
  echo "  --debug                Enable debug mode with detailed error output"
  echo "  --help                 Show this help message"
  exit 1
}

# Check if the first argument looks like a URL (no flag)
if [[ $1 == http* && $1 != "--"* ]]; then
  # Handle positional arguments
  YOUTUBE_URL="$1"
  # If there's a second positional argument, use it as movie title
  if [[ $# -gt 1 && $2 != "--"* ]]; then
    MOVIE_TITLE="$2"
    shift 2
  else
    shift 1
  fi
else
  # Parse flag-style arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --youtube-url)
        YOUTUBE_URL="$2"
        shift 2
        ;;
      --movie-title)
        MOVIE_TITLE="$2"
        shift 2
        ;;
      --num-clips)
        NUM_CLIPS="$2"
        shift 2
        ;;
      --clip-length)
        CLIP_LENGTH="$2"
        shift 2
        ;;
      --output-dir)
        OUTPUT_DIR="$2"
        shift 2
        ;;
      --debug)
        DEBUG_MODE="--debug"
        shift 1
        ;;
      --help)
        show_help
        ;;
      *)
        echo "Unknown option: $1"
        show_help
        ;;
    esac
  done
fi

# Check required arguments
if [ -z "$YOUTUBE_URL" ]; then
  echo "❌ Error: YouTube URL is required"
  show_help
fi

echo "🚀 StreamGank - Testing Direct Vizard AI Integration"
echo "=================================================="
echo "YouTube URL: $YOUTUBE_URL"
echo "Movie Title: $MOVIE_TITLE"
echo "Number of clips: $NUM_CLIPS"
echo "Clip length: $CLIP_LENGTH"
echo "Output directory: $OUTPUT_DIR"

# Run the Python test script
python test_vizard_api.py \
  --youtube-url "$YOUTUBE_URL" \
  --movie-title "$MOVIE_TITLE" \
  --num-clips "$NUM_CLIPS" \
  --clip-length "$CLIP_LENGTH" \
  --output-dir "$OUTPUT_DIR" \
  $DEBUG_MODE

# Check if test was successful
if [ $? -eq 0 ]; then
  echo -e "\n✅ Vizard API integration test completed successfully!"
else
  echo -e "\n❌ Vizard API integration test failed."
fi
