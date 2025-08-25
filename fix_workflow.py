#!/usr/bin/env python3
"""
Script to fix workflow.py file for local Vizard clips integration.
This script modifies the workflow.py file to add support for using locally
downloaded Vizard clips without requiring Cloudinary uploads.
"""

import os
import sys
import re

WORKFLOW_FILE = "core/workflow.py"
BACKUP_FILE = "core/workflow.py.bak"

def add_load_local_vizard_clips_function(content):
    """Add the load_local_vizard_clips function to workflow.py"""
    
    function_code = """
# Function to load local Vizard clip metadata
def load_local_vizard_clips(metadata_file="vizard_workflow_data.json") -> List[Dict[str, Any]]:
    \"\"\"
    Load local Vizard clip metadata from JSON file
    
    Args:
        metadata_file: Path to JSON metadata file with clip info
        
    Returns:
        List of clip metadata entries or empty list if file not found/invalid
    \"\"\"
    try:
        if not os.path.isfile(metadata_file):
            logging.warning(f"Local Vizard clip metadata file not found: {metadata_file}")
            return []
            
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            
        if not data or 'highlight_clips' not in data:
            logging.warning(f"Invalid local Vizard clip metadata format in {metadata_file}")
            return []
            
        clips = data['highlight_clips']
        logging.info(f"Loaded {len(clips)} local Vizard clips from metadata file")
        return clips
        
    except Exception as e:
        logging.error(f"Error loading local Vizard clip metadata: {str(e)}")
        return []
"""

    # Make sure we have pathlib imported
    if "from pathlib import Path" not in content:
        content = re.sub(
            r"import tempfile\s+from typing",
            "import tempfile\nfrom pathlib import Path\nfrom typing",
            content
        )
    
    # Add the function after imports
    pattern = r"from database\.movie_extractor import extract_movie_data\s+"
    replacement = "from database.movie_extractor import extract_movie_data\n" + function_code + "\n"
    return re.sub(pattern, replacement, content)

def update_vizard_ai_section(content):
    """Update the Vizard AI integration section to support local clips"""
    
    # First, fix the indentation issues and any syntax errors in the Vizard AI section
    
    # Pattern 1: Check for locally prepared Vizard clips
    pattern1 = r"(elif use_vizard_ai:\s+print\(\s*\".*Using Vizard AI for highlight extraction from trailers.*\"\))\s+"
    replacement1 = r"\1\n                \n                # Check for locally prepared Vizard clips first\n                local_vizard_clips = load_local_vizard_clips()\n                \n"
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern 2: Handle local clips
    pattern2 = r"(# Initialize lists? for collecting highlight clips\s+highlight_clips = \[\])\s+"
    replacement2 = r"# Initialize list for collecting highlight clips\n                    highlight_clips = []\n                \n                if local_vizard_clips:\n                    print(f\"   📂 Using {len(local_vizard_clips)} pre-prepared local Vizard clips\")\n                    highlight_clips = local_vizard_clips\n                    print(\"   ✅ Local Vizard clips loaded successfully, skipping API calls\")\n                else:\n                    # No local clips, use the API\n                    print(\"   ⚠️ No local Vizard clips found, will make fresh API calls to Vizard for each trailer\")\n                    print(\"   🔄 Generating fresh highlights from movie trailers using Vizard AI\")\n                    print(\"   🛠️ Using the fixed VizardAIClient implementation\")\n                    \n"
    
    content = re.sub(pattern2, replacement2, content)
    
    # Pattern 3: Fix processing of highlight clips
    pattern3 = r"(# If we have highlights, upload them to Cloudinary and use them\s+if highlight_clips:.*?\n.*?Processing.*?highlights.*?Creatomate assembly.*?\n.*?Upload to Cloudinary for Creatomate compatibility.*?\n.*?Check if we have pre-uploaded clips with URLs.*?\n.*?has_pre_uploaded.*?\n\s+if has_pre_uploaded:.*?\n.*?Using.*?pre-uploaded clips with existing URLs.*?\n.*?vizard_clip_urls = \[clip\['url'\].*?\n.*?else:.*?\n.*?Need to upload the clips to Cloudinary.*?\n.*?vizard_clip_paths = \[clip\['local_path'\].*?\n\s+vizard_clip_urls = process_vizard_highlights_for_creatomate\(.*?\n.*?highlight_clips=vizard_clip_paths,.*?\n.*?folder=\"vizard_ai_clips\".*?\n.*?\))"
    
    replacement3 = """                # If we have highlights, process them for the workflow
                if highlight_clips:
                    print(f"\\n🎬 Processing {len(highlight_clips)} Vizard AI highlights for Creatomate assembly...")
                    
                    # Check if we have pre-uploaded clips with URLs or local paths
                    has_pre_uploaded = any(clip.get('url') for clip in highlight_clips)
                    has_local_paths = any(clip.get('local_path') for clip in highlight_clips)
                    
                    if has_pre_uploaded:
                        # Use existing Cloudinary URLs
                        print(f"   💾 Using {len(highlight_clips)} pre-uploaded clips with existing URLs")
                        vizard_clip_urls = [clip['url'] for clip in highlight_clips if clip.get('url')]
                    elif has_local_paths and not os.environ.get('CLOUDINARY_CLOUD_NAME'):
                        # Use local paths if Cloudinary is not configured
                        print(f"   💾 Using {len(highlight_clips)} local clip paths (Cloudinary not configured)")
                        # Get absolute paths for local clips
                        vizard_clip_urls = []
                        for clip in highlight_clips:
                            if clip.get('local_path'):
                                # Make sure we use absolute paths
                                path = clip['local_path']
                                if not os.path.isabs(path):
                                    path = os.path.abspath(path)
                                vizard_clip_urls.append(path)
                        print(f"   ✅ Found {len(vizard_clip_urls)} local clips to use directly")
                    else:
                        # Need to upload the clips to Cloudinary
                        print(f"   💾 Processing clips for Cloudinary upload")
                        vizard_clip_paths = [clip['local_path'] for clip in highlight_clips if clip.get('local_path')]
                        
                        try:
                            vizard_clip_urls = process_vizard_highlights_for_creatomate(
                                highlight_clips=vizard_clip_paths,
                                folder="vizard_ai_clips"
                            )
                            print(f"   ✅ Successfully uploaded {len(vizard_clip_urls)} clips to Cloudinary")
                        except Exception as e:
                            print(f"   ⚠️ Failed to upload clips to Cloudinary: {str(e)}")
                            # Fallback to local paths if upload fails
                            print(f"   🔄 Falling back to local clip paths")
                            vizard_clip_urls = [os.path.abspath(path) for path in vizard_clip_paths]"""
    
    # Use re.DOTALL to match across multiple lines
    content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)
    
    return content

def main():
    """Main function to fix workflow.py"""
    
    if not os.path.exists(WORKFLOW_FILE):
        print(f"Error: {WORKFLOW_FILE} not found")
        return 1
    
    # Read the current workflow file
    with open(WORKFLOW_FILE, 'r') as f:
        content = f.read()
    
    # Create a backup
    with open(BACKUP_FILE, 'w') as f:
        f.write(content)
    
    # Add the load_local_vizard_clips function
    content = add_load_local_vizard_clips_function(content)
    
    # Update the Vizard AI integration section
    content = update_vizard_ai_section(content)
    
    # Write the updated content back
    with open(WORKFLOW_FILE, 'w') as f:
        f.write(content)
    
    print(f"✅ Successfully updated {WORKFLOW_FILE} with local Vizard clips support")
    print(f"📋 Created backup at {BACKUP_FILE}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
