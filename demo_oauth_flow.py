#!/usr/bin/env python3
"""Demo script to simulate the OAuth authentication flow."""

import requests
import time
import os

def simulate_oauth_callback():
    """Simulate what happens when user authorizes in browser."""
    
    print("🌐 Simulating user authorization in browser...")
    time.sleep(1)
    
    # Simulate the OAuth provider redirecting back with an auth code
    auth_code = "demo_auth_code_" + os.urandom(8).hex()
    
    print(f"✓ User authorized the application")
    print(f"📝 Received authorization code: {auth_code[:20]}...")
    
    # Simulate the callback to localhost
    try:
        response = requests.get(
            f"http://localhost:8080/callback",
            params={
                'code': auth_code,
                'state': 'matching_state_parameter'
            },
            timeout=5
        )
        print(f"✓ Callback successful: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("ℹ️  Local server not running (expected in demo)")
    
    return auth_code

if __name__ == "__main__":
    print("=" * 60)
    print("DataAgent OAuth Flow Demonstration")
    print("=" * 60)
    print()
    
    print("Step 1: User runs 'dataagent auth login'")
    print("  → CLI starts local server on port 8080")
    print("  → CLI opens browser to Claude OAuth page")
    print()
    
    print("Step 2: Browser opens to:")
    print("  https://claude.ai/oauth/authorize?")
    print("    client_id=dataagent-cli-prod")
    print("    response_type=code")
    print("    redirect_uri=http://localhost:8080/callback")
    print("    scope=data:analyze model:access subscription:read")
    print()
    
    print("Step 3: User authorizes in browser")
    auth_code = simulate_oauth_callback()
    print()
    
    print("Step 4: CLI exchanges auth code for tokens")
    print("  → POST to https://claude.ai/oauth/token")
    print("  → Receives access_token and refresh_token")
    print()
    
    print("Step 5: Tokens saved locally")
    print("  → Saved to ~/.dataagent/tokens.json")
    print("  → File permissions set to 600 (user-only)")
    print()
    
    print("✅ Authentication complete!")
    print()
    print("User can now run:")
    print("  dataagent analyze 'Show sales trends' -s data.csv")
    print()
    print("=" * 60)