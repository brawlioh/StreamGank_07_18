#!/usr/bin/env python3
"""
Test Vizard AI Authentication

This script tests the Vizard AI API key authentication without attempting to process any videos.
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_vizard_api_key():
    """Check if the Vizard API key is properly loaded and working"""
    api_key = os.environ.get("VIZARD_API_KEY")
    
    if not api_key:
        print("❌ VIZARD_API_KEY is not set in environment variables")
        print("   Make sure you have a .env file with VIZARD_API_KEY=your_api_key")
        return False
    
    # Check if the key is the placeholder from .env.example
    if api_key == "705aebfc982b4695a7e25236103ae56f":
        print("⚠️ Using example API key from .env.example")
        print("   This key may not work. Please update it with your actual Vizard API key.")
    
    print(f"📝 Using Vizard API key: {api_key[:8]}...{api_key[-4:]}")
    
    # Try simple API request to verify authentication
    headers = {
        "VIZARDAI_API_KEY": api_key,
        "Content-Type": "application/json"
    }
    
    # List of endpoints to try
    endpoints = [
        "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1/user/info",
        "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1/project/query/23157540",  # Test with known project ID
        "https://api.vizard.ai/api/v1/user/info"
    ]
    
    success = False
    for endpoint in endpoints:
        try:
            print(f"🔄 Testing endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Successfully authenticated with endpoint: {endpoint}")
                try:
                    data = response.json()
                    print(f"📊 Response: {json.dumps(data, indent=2)[:500]}...")
                    success = True
                    break
                except:
                    print(f"⚠️ Response is not valid JSON: {response.text[:100]}...")
            elif response.status_code == 401 or response.status_code == 403:
                print(f"❌ Authentication failed with status code {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
            else:
                print(f"⚠️ Received status code {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
        except Exception as e:
            print(f"❌ Error connecting to endpoint: {str(e)}")
    
    if not success:
        print("\n❌ Failed to authenticate with Vizard AI API")
        print("   Please check your API key and network connection")
        return False
    else:
        print("\n✅ Successfully authenticated with Vizard AI API")
        return True

def main():
    """Main function"""
    print("\n🔑 Vizard AI Authentication Test")
    print("==============================\n")
    
    # Check .env file existence
    if not os.path.exists(".env"):
        print("❌ .env file not found")
        print("   Please create a .env file by copying .env.example and updating the API keys")
        print("   Command: cp .env.example .env")
        return 1
    
    # Check if API key is valid
    if check_vizard_api_key():
        print("\n🎉 Authentication test passed!")
        return 0
    else:
        print("\n❌ Authentication test failed")
        return 1

if __name__ == "__main__":
    exit(main())
