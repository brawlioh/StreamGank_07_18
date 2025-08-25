#!/bin/bash
# Test command for Vizard AI integration

echo "🚀 Running StreamGank with Vizard AI Integration"
echo "================================================"

# Run the workflow with Vizard AI enabled
python main.py \
  --country US \
  --platform Netflix \
  --genre Action \
  --content-type movie \
  --num-movies 3 \
  --use-vizard-ai
