#!/usr/bin/env python3
"""Debug script for Vizard API status"""

import os
import json
import sys
from dotenv import load_dotenv
from ai.vizard_client import VizardAIClient

# Load environment variables
load_dotenv()

def main():
    # Check if we have a project ID from command line
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        # Default to one from screenshot
        project_id = "23157540"

    print(f"\n🔍 Vizard API Status Checker")
    print(f"==========================")
    print(f"Checking status for project ID: {project_id}")

    # Initialize client
    client = VizardAIClient()

    # Get raw status response with both formats
    formats = [f"open-api-{project_id}", f"project-{project_id}", project_id]
    
    for format_id in formats:
        print(f"\n🔄 Checking with format: {format_id}")
        response = client.get_project_status(format_id)
        
        # Print raw response
        print(f"📊 API response:")
        print(json.dumps(response, indent=2))
        
        # Extract status information
        if isinstance(response, dict):
            status = ""
            if "status" in response:
                status = response.get("status", "UNKNOWN")
            elif "data" in response and "status" in response["data"]:
                status = response["data"]["status"]
                
            print(f"\n🔎 Extracted status: {status}")
            
            # Check for clips/results
            if "data" in response and "clips" in response["data"]:
                clips = response["data"]["clips"]
                print(f"🎬 Found {len(clips)} clips in response")
                
                # Show first clip info
                if len(clips) > 0:
                    print(f"  Example clip: {json.dumps(clips[0], indent=2)}")

if __name__ == "__main__":
    main()
