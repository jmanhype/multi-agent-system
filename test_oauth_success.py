#!/usr/bin/env python3
"""Test the OAuth callback by simulating a successful authorization."""

import requests
import time
import sys

def test_oauth_callback():
    """Simulate Claude calling back with an authorization code."""
    
    # Wait a moment for the server to be ready
    print("Waiting for server to start...")
    time.sleep(2)
    
    # Simulate the OAuth callback
    callback_url = "http://localhost:8080/callback"
    params = {
        'code': 'test_authorization_code_12345',
        'state': input("Enter the state parameter from the URL: ")
    }
    
    try:
        print(f"\n🔄 Simulating OAuth callback to {callback_url}")
        response = requests.get(callback_url, params=params, timeout=5)
        
        if response.status_code == 200:
            print("✅ Callback successful!")
            print("The CLI should now show 'Authentication Successful!'")
        else:
            print(f"❌ Callback failed with status: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to localhost:8080")
        print("Make sure 'dataagent auth login' is running in another terminal")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("OAuth Callback Tester")
    print("=" * 60)
    print("\n1. Run 'python -m lib.agents.data_agent.cli auth login' in another terminal")
    print("2. Copy the 'state' parameter from the authorization URL")
    print("3. Paste it here when prompted\n")
    
    test_oauth_callback()