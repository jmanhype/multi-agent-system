#!/usr/bin/env python3
"""
Claude OAuth implementation with Dynamic Client Registration.

This module handles the OAuth flow specifically for Claude, which requires:
1. Dynamic Client Registration (DCR)
2. PKCE (Proof Key for Code Exchange)
3. Specific OAuth scopes
"""

import os
import base64
import hashlib
import json
import webbrowser
import http.server
import socketserver
from urllib.parse import urlencode, urlparse, parse_qs
from typing import Optional, Dict, Any
import threading
import time
import requests


class ClaudeOAuth:
    """Handle Claude OAuth with Dynamic Client Registration."""
    
    def __init__(self):
        self.auth_result = None
        self.auth_error = None
        self.callback_received = threading.Event()
        
    def authenticate(self, callback_port: int = 8080) -> Optional[str]:
        """
        Perform Claude OAuth authentication with DCR.
        
        Returns:
            Access token if successful, None otherwise.
        """
        from .oauth_server import OAuthDCRServer
        
        # Start DCR server
        print("🔧 Starting OAuth Dynamic Client Registration server...")
        dcr_server = OAuthDCRServer()
        dcr_base_url = dcr_server.start()
        
        try:
            # Register client dynamically
            print("📝 Registering client with Claude...")
            redirect_uri = f"http://localhost:{callback_port}/callback"
            client_data = dcr_server.register_client(
                client_name="DataAgent CLI",
                redirect_uris=[redirect_uri]
            )
            
            client_id = client_data['client_id']
            print(f"✅ Registered client: {client_id}")
            
            # Generate PKCE parameters
            code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode('utf-8').rstrip('=')
            
            # Generate state for CSRF protection
            state = os.urandom(16).hex()
            
            # Build authorization URL
            auth_params = {
                'client_id': client_id,
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'scope': 'org:create_api_key user:profile user:inference',  # Correct scopes from claude_max
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256',
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            auth_url = f"https://claude.ai/oauth/authorize?{urlencode(auth_params)}"
            
            # Start callback server
            callback_server = self._start_callback_server(callback_port, state)
            
            # Open browser for authentication
            print(f"\n🔐 Opening browser for authentication...")
            print(f"If browser doesn't open, visit: {auth_url}\n")
            webbrowser.open(auth_url)
            
            # Wait for callback (max 2 minutes)
            print("⏳ Waiting for authentication...")
            if self.callback_received.wait(timeout=120):
                if self.auth_result and 'code' in self.auth_result:
                    # Exchange code for token
                    print("🔄 Exchanging authorization code for token...")
                    token = self._exchange_code_for_token(
                        self.auth_result['code'],
                        client_id,
                        redirect_uri,
                        code_verifier
                    )
                    
                    if token:
                        print("✅ Authentication successful!")
                        return token
                    else:
                        print("❌ Failed to exchange code for token")
                elif self.auth_error:
                    print(f"❌ Authentication failed: {self.auth_error}")
            else:
                print("⏱️ Authentication timeout")
                
        finally:
            # Clean up
            dcr_server.stop()
            if callback_server:
                callback_server.shutdown()
                
        return None
        
    def _start_callback_server(self, port: int, expected_state: str):
        """Start local server to receive OAuth callback."""
        
        class CallbackHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(handler_self):
                parsed = urlparse(handler_self.path)
                
                if parsed.path == '/callback':
                    query_params = parse_qs(parsed.query)
                    
                    # Verify state to prevent CSRF
                    if query_params.get('state', [None])[0] != expected_state:
                        handler_self.send_error(400, "Invalid state parameter")
                        return
                        
                    if 'code' in query_params:
                        self.auth_result = {
                            'code': query_params['code'][0],
                            'state': query_params.get('state', [None])[0]
                        }
                        
                        # Send success response
                        handler_self.send_response(200)
                        handler_self.send_header('Content-type', 'text/html; charset=utf-8')
                        handler_self.end_headers()
                        html_response = """
                        <html>
                        <head>
                            <title>Authentication Successful</title>
                            <style>
                                body { font-family: system-ui; text-align: center; padding: 50px; }
                                h1 { color: #22c55e; }
                            </style>
                        </head>
                        <body>
                            <h1>✅ Authentication Successful!</h1>
                            <p>You can close this window and return to the CLI.</p>
                            <script>setTimeout(function() { window.close(); }, 2000);</script>
                        </body>
                        </html>
                        """
                        handler_self.wfile.write(html_response.encode('utf-8'))
                    elif 'error' in query_params:
                        self.auth_error = {
                            'error': query_params['error'][0],
                            'description': query_params.get('error_description', [''])[0]
                        }
                        
                        # Send error response
                        handler_self.send_response(200)
                        handler_self.send_header('Content-type', 'text/html; charset=utf-8')
                        handler_self.end_headers()
                        error_html = """
                        <html>
                        <head>
                            <title>Authentication Failed</title>
                            <style>
                                body { font-family: system-ui; text-align: center; padding: 50px; }
                                h1 { color: #ef4444; }
                            </style>
                        </head>
                        <body>
                            <h1>❌ Authentication Failed</h1>
                            <p>Check the console for error details.</p>
                        </body>
                        </html>
                        """
                        handler_self.wfile.write(error_html.encode('utf-8'))
                    
                    # Signal that callback was received
                    self.callback_received.set()
                    
                else:
                    handler_self.send_error(404)
                    
            def log_message(self, format, *args):
                # Suppress default logging
                pass
                
        # Start server in background thread
        server = socketserver.TCPServer(("", port), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        return server
        
    def _exchange_code_for_token(self, code: str, client_id: str, 
                                 redirect_uri: str, code_verifier: str) -> Optional[str]:
        """Exchange authorization code for access token."""
        
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier
        }
        
        try:
            response = requests.post(
                'https://claude.ai/oauth/token',
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                token_response = response.json()
                return token_response.get('access_token')
            else:
                print(f"Token exchange failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Token exchange error: {e}")
            return None


def test_claude_oauth():
    """Test Claude OAuth authentication."""
    oauth = ClaudeOAuth()
    token = oauth.authenticate()
    
    if token:
        print(f"\n✅ Got access token: {token[:20]}...")
        
        # Test the token
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('https://claude.ai/api/user', headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Token valid! User: {user_data.get('email', 'Unknown')}")
        else:
            print(f"❌ Token test failed: {response.status_code}")
    else:
        print("\n❌ Authentication failed")


if __name__ == "__main__":
    test_claude_oauth()