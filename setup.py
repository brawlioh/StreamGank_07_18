#!/usr/bin/env python3
"""
Setup script for StreamGank Automated Video Generator
Installs all required dependencies and Playwright browsers
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a shell command and print the output"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🎬 StreamGank Automated Video Generator - Setup")
    print("=" * 50)
    
    # Install Python dependencies
    print("\n📦 Installing Python dependencies...")
    if not run_command("pip install -r requirements.txt"):
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Install Playwright browsers
    print("\n🌐 Installing Playwright browsers...")
    if not run_command("python -m playwright install"):
        print("❌ Failed to install Playwright browsers")
        sys.exit(1)
    
    print("\n✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Set up your environment variables in a .env file:")
    print("   - SUPABASE_URL")
    print("   - SUPABASE_KEY") 
    print("   - OPENAI_API_KEY")
    print("   - HEYGEN_API_KEY")
    print("   - CREATOMATE_API_KEY")
    print("   - CLOUDINARY_CLOUD_NAME")
    print("   - CLOUDINARY_API_KEY")
    print("   - CLOUDINARY_API_SECRET")
    print("\n2. Run the script:")
    print("   python automated_video_generator.py --all")
    print("\n🚀 Ready to generate videos!")

if __name__ == "__main__":
    main() 