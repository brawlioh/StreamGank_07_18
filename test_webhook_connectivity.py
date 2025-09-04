#!/usr/bin/env python3
"""
Test webhook connectivity for StreamGank job updates
"""

import requests
import json
import time
import os
from utils.webhook_client import create_webhook_client

def test_webhook_connectivity():
    """Test webhook connectivity to ensure job page synchronization works"""
    
    # Test configuration
    webhook_base_url = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:3000')
    test_job_id = f"test_job_{int(time.time())}"
    
    print(f"🧪 Testing webhook connectivity...")
    print(f"   Base URL: {webhook_base_url}")
    print(f"   Test Job ID: {test_job_id}")
    
    # Create webhook client
    webhook_client = create_webhook_client(test_job_id)
    
    # Test 1: Webhook endpoint availability
    print(f"\n📡 Test 1: Checking webhook endpoint availability...")
    try:
        response = requests.get(f"{webhook_base_url}/api/webhooks/status", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Webhook endpoint is reachable (status: {response.status_code})")
            status_data = response.json()
            print(f"   📊 Webhook status: {json.dumps(status_data, indent=2)}")
        else:
            print(f"   ❌ Webhook endpoint returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Cannot reach webhook endpoint: {str(e)}")
        print(f"   💡 Make sure the frontend server is running on {webhook_base_url}")
        return False
    
    # Test 2: Step update webhook
    print(f"\n📡 Test 2: Sending test step update webhook...")
    success = webhook_client.send_step_update(
        step_number=1,
        step_name="Test Step",
        status="started",
        duration=0,
        details={'test': True, 'connectivity_check': True}
    )
    
    if success:
        print(f"   ✅ Step update webhook sent successfully")
    else:
        print(f"   ❌ Step update webhook failed")
        return False
    
    # Test 3: Workflow started webhook
    print(f"\n📡 Test 3: Sending workflow started webhook...")
    success = webhook_client.send_workflow_started(total_steps=7)
    
    if success:
        print(f"   ✅ Workflow started webhook sent successfully")
    else:
        print(f"   ❌ Workflow started webhook failed")
        return False
    
    # Test 4: Manual webhook test via API
    print(f"\n📡 Test 4: Testing webhook endpoint via API...")
    try:
        test_url = f"{webhook_base_url}/api/webhooks/step-update"
        response = requests.post(f"{webhook_base_url}/api/webhooks/test", 
                               json={"url": test_url}, 
                               timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ API webhook test successful: {json.dumps(result, indent=2)}")
        else:
            print(f"   ❌ API webhook test failed (status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API webhook test error: {str(e)}")
        return False
    
    print(f"\n🎉 All webhook connectivity tests passed!")
    print(f"   The job page should receive real-time updates properly.")
    print(f"   If the job page is still not updating, check:")
    print(f"   1. Frontend server is running on {webhook_base_url}")
    print(f"   2. Job ID is being passed correctly to the Python workflow")
    print(f"   3. Browser console for SSE connection errors")
    
    return True

if __name__ == "__main__":
    test_webhook_connectivity()
