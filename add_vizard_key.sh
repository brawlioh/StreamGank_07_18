#!/bin/bash
# Script to add VIZARD_API_KEY to .env file

# Check if .env file exists
if [ ! -f .env ]; then
  echo "❌ .env file not found"
  exit 1
fi

# Prompt for API key
echo "Enter your Vizard AI API key:"
read -s API_KEY

# Check if key was provided
if [ -z "$API_KEY" ]; then
  echo "❌ No API key provided"
  exit 1
fi

# Check if VIZARD_API_KEY already exists in .env
if grep -q "VIZARD_API_KEY=" .env; then
  # Update existing key
  sed -i '' "s/VIZARD_API_KEY=.*/VIZARD_API_KEY=$API_KEY/" .env
  echo "✅ Updated VIZARD_API_KEY in .env"
else
  # Add new key
  echo "" >> .env
  echo "# Vizard AI Configuration" >> .env
  echo "VIZARD_API_KEY=$API_KEY" >> .env
  echo "✅ Added VIZARD_API_KEY to .env"
fi
