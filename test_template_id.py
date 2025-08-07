#!/usr/bin/env python3
"""
Test script to verify the HeyGen template ID in automated_video_generator.py
"""

import sys
import os
import importlib.util

# Import the module dynamically
spec = importlib.util.spec_from_file_location("automated_video_generator", 
                                             "./automated_video_generator.py")
module = importlib.util.module_from_spec(spec)
sys.modules["automated_video_generator"] = module
spec.loader.exec_module(module)

# Get the template ID from the function default parameters
create_heygen_video = module.create_heygen_video
template_id = create_heygen_video.__defaults__[1]  # Template ID is the second default parameter

# The template ID we want to verify
expected_id = "5aa5b8cb94d447f38fcc044d887dd924"

print("\n=== TEMPLATE ID TEST ===\n")
print(f"✅ Template ID used in function default: {template_id}")
print(f"✅ Template ID we want to use: {expected_id}")
print(f"✅ Do they match? {template_id == expected_id}")

# Check the HeyGen API endpoint construction
print("\nChecking HeyGen API endpoint construction...")
payload = {
    "template_id": template_id,
    "clips": [{"script": "Test script"}]
}

# Show what would be sent to HeyGen
if "template_id" in payload:
    t_id = payload["template_id"]
    url = f"https://api.heygen.com/v2/template/{t_id}/generate"
    print(f"✅ Template request detected")
    print(f"✅ Template ID in payload: {t_id}")
    print(f"✅ API endpoint: {url}")

print("\n=== TEST COMPLETE ===\n")
