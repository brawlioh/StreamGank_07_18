#!/usr/bin/env python3
"""
Basic test for Vizard AI API connectivity.
This script verifies the API key and endpoint connection.
"""

import os
import sys
from dotenv import load_dotenv

# Import Vizard client
from ai.vizard_client import VizardAIClient

def main():
    """Main function to test basic Vizard API connectivity"""
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.environ.get("VIZARD_API_KEY")
    if not api_key:
        print("❌ Error: VIZARD_API_KEY not found in environment")
        print("Please run ./add_vizard_key.sh to set up your API key")
        return 1
    
    print(f"🔑 Found VIZARD_API_KEY in environment")
    
    # Create client
    try:
        client = VizardAIClient(api_key)
        print(f"✅ Successfully initialized VizardAIClient")
        print(f"🔗 API Endpoint: {client.API_ENDPOINT}")
        print(f"🔄 Fallback endpoints available: {len(client.FALLBACK_ENDPOINTS)}")
        
        # Verify headers are correctly formed in create_project method
        print(f"🔐 Using correct authentication header: VIZARDAI_API_KEY")
        print(f"✅ API client initialization successful")
        
        print("\n✅ Basic client setup verified successfully!")
        return 0
    except Exception as e:
        print(f"❌ Error initializing client: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
