#!/bin/bash

# Test Manual Vizard Clip Integration
# Usage: ./test_manual_vizard_integration.sh

# Settings
CLIPS_DIR="test_vizard_clips"
METADATA_FILE="test_clips_metadata.json"
TEST_COUNTRY="US"
TEST_PLATFORM="Netflix"
TEST_GENRE="Action"
TEST_CONTENT_TYPE="movie"

echo "🧪 StreamGank - Testing Manual Vizard Clip Integration"
echo "======================================================"

# Step 1: Process any clips in the test directory
echo -e "\n📂 Step 1: Processing clips from $CLIPS_DIR"

if [ ! -d "$CLIPS_DIR" ]; then
  echo "⚠️  Warning: $CLIPS_DIR directory does not exist. Creating empty directory."
  mkdir -p "$CLIPS_DIR"
  echo "ℹ️  Please add some test Vizard clips to $CLIPS_DIR before continuing."
  exit 1
fi

# Count clips in directory
CLIP_COUNT=$(find "$CLIPS_DIR" -type f -name "*.mp4" | wc -l)

if [ "$CLIP_COUNT" -eq 0 ]; then
  echo "⚠️  No MP4 clips found in $CLIPS_DIR directory."
  echo "ℹ️  Please add some test Vizard clips to $CLIPS_DIR before continuing."
  exit 1
fi

echo "✅ Found $CLIP_COUNT clips in $CLIPS_DIR directory."

# Step 2: Run integrate_vizard_clips.py to process the clips
echo -e "\n🔄 Step 2: Processing clips with integrate_vizard_clips.py"

python integrate_vizard_clips.py \
  --clip-dir "$CLIPS_DIR" \
  --output-file "$METADATA_FILE" \
  --upload-to-cloudinary

# Check if metadata file was created
if [ ! -f "$METADATA_FILE" ]; then
  echo "❌ Error: Failed to create metadata file $METADATA_FILE"
  exit 1
fi

echo "✅ Successfully created metadata file: $METADATA_FILE"

# Step 3: Run the main workflow with the metadata file
echo -e "\n🚀 Step 3: Running main workflow with Vizard metadata"

python main.py \
  --country "$TEST_COUNTRY" \
  --platform "$TEST_PLATFORM" \
  --genre "$TEST_GENRE" \
  --content-type "$TEST_CONTENT_TYPE" \
  --use-vizard-ai \
  --vizard-metadata "$METADATA_FILE"

echo -e "\n✅ Test completed!"
echo "Check the console output above for any errors."
