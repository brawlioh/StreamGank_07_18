#!/usr/bin/env python3
"""
StreamGank Railway Deployment Helper

This script helps prepare your project for Railway deployment by:
1. Validating required files
2. Checking dependencies
3. Testing the API server locally
4. Providing deployment instructions
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a required file exists"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (MISSING)")
        return False

def check_requirements():
    """Check if all required files exist"""
    print("🔍 Checking deployment requirements...\n")
    
    required_files = [
        ("api_server.py", "FastAPI server"),
        ("requirements.txt", "Python dependencies"),
        ("Procfile", "Railway process configuration"),
        ("railway.json", "Railway deployment configuration"),
        ("gui/config.js", "Frontend configuration"),
        ("gui/index.html", "Frontend interface"),
        ("gui/js/script.js", "Frontend JavaScript"),
        ("gui/css/style.css", "Frontend styling")
    ]
    
    all_present = True
    for file_path, description in required_files:
        if not check_file_exists(file_path, description):
            all_present = False
    
    return all_present

def test_local_server():
    """Test if the API server can start locally"""
    print("\n🧪 Testing local API server...")
    
    try:
        # Try to import FastAPI dependencies
        import fastapi
        import uvicorn
        import pydantic
        print("✅ FastAPI dependencies available")
        
        # Test if api_server.py can be imported
        sys.path.insert(0, str(Path.cwd()))
        
        try:
            import api_server
            print("✅ api_server.py imports successfully")
            return True
        except ImportError as e:
            print(f"❌ Error importing api_server.py: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def validate_config():
    """Validate configuration files"""
    print("\n🔧 Validating configuration...")
    
    # Check Procfile
    if os.path.exists("Procfile"):
        with open("Procfile", "r") as f:
            procfile_content = f.read().strip()
            if "uvicorn api_server:app" in procfile_content:
                print("✅ Procfile configured correctly")
            else:
                print("❌ Procfile missing uvicorn command")
                return False
    
    # Check railway.json
    if os.path.exists("railway.json"):
        try:
            with open("railway.json", "r") as f:
                railway_config = json.load(f)
                if "deploy" in railway_config and "startCommand" in railway_config["deploy"]:
                    print("✅ railway.json configured correctly")
                else:
                    print("❌ railway.json missing deploy configuration")
                    return False
        except json.JSONDecodeError:
            print("❌ railway.json has invalid JSON")
            return False
    
    return True

def show_deployment_instructions():
    """Show step-by-step deployment instructions"""
    print("\n🚀 DEPLOYMENT INSTRUCTIONS")
    print("=" * 50)
    
    print("\n1️⃣ RAILWAY BACKEND DEPLOYMENT:")
    print("   • Go to https://railway.app")
    print("   • Click 'New Project' → 'Deploy from GitHub repo'")
    print("   • Select your repository")
    print("   • Railway will auto-deploy using Procfile")
    print("   • Add environment variables in Railway dashboard")
    
    print("\n2️⃣ ENVIRONMENT VARIABLES TO SET:")
    env_vars = [
        "SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY",
        "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET",
        "HEYGEN_API_KEY", "CREATOMATE_API_KEY"
    ]
    for var in env_vars:
        print(f"   • {var}")
    
    print("\n3️⃣ UPDATE FRONTEND CONFIG:")
    print("   • Get your Railway URL (e.g., https://your-app.railway.app)")
    print("   • Update gui/config.js with your Railway URL")
    print("   • Replace 'https://streamgank-api.railway.app' with your actual URL")
    
    print("\n4️⃣ NETLIFY FRONTEND DEPLOYMENT:")
    print("   • Go to https://netlify.com")
    print("   • Drag & drop your 'gui/' folder")
    print("   • Or connect GitHub repo with publish directory: 'gui'")
    
    print("\n5️⃣ TEST YOUR DEPLOYMENT:")
    print("   • Visit your Railway URL to see API dashboard")
    print("   • Visit your Netlify URL to test frontend")
    print("   • Try generating a video to test full workflow")

def main():
    """Main deployment checker"""
    print("🎬 StreamGank Railway Deployment Checker")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Some required files are missing. Please create them first.")
        return False
    
    # Test local server
    if not test_local_server():
        print("\n❌ Local server test failed. Please fix dependencies.")
        return False
    
    # Validate config
    if not validate_config():
        print("\n❌ Configuration validation failed. Please fix config files.")
        return False
    
    print("\n✅ ALL CHECKS PASSED!")
    print("Your project is ready for Railway deployment! 🚀")
    
    # Show deployment instructions
    show_deployment_instructions()
    
    print(f"\n📖 For detailed instructions, see: RAILWAY_DEPLOYMENT.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
