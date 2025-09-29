#!/usr/bin/env python3
"""
OAuth 2.1 Dynamic Client Registration server for Claude integration.

This implements the required endpoints for Claude's OAuth flow:
- /.well-known/oauth-protected-resource
- /.well-known/oauth-authorization-server
- /register (for dynamic client registration)
"""

import json
import uuid
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any
import threading
import socket

class OAuthDCRServer:
    """OAuth Dynamic Client Registration server for Claude."""
    
    def __init__(self, port: int = 9000):
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.registered_clients = {}
        self.server = None
        self.server_thread = None
        
    def start(self):
        """Start the DCR server in the background."""
        dcr_server = self  # Reference to OAuthDCRServer instance
        
        class DCRHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = urlparse(self.path).path
                
                if path == "/.well-known/oauth-protected-resource":
                    self.handle_protected_resource()
                elif path == "/.well-known/oauth-authorization-server":
                    self.handle_authorization_server()
                else:
                    self.send_response(404)
                    self.end_headers()
                    
            def do_POST(self):
                path = urlparse(self.path).path
                
                if path == "/register":
                    self.handle_register()
                else:
                    self.send_response(404)
                    self.end_headers()
                    
            def handle_protected_resource(self):
                """Provide OAuth protected resource metadata."""
                response = {
                    "resource": dcr_server.base_url,
                    "authorization_servers": [dcr_server.base_url],
                    "bearer_methods_supported": ["header"]
                }
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            def handle_authorization_server(self):
                """Provide OAuth authorization server metadata."""
                response = {
                    "issuer": dcr_server.base_url,
                    "authorization_endpoint": "https://claude.ai/oauth/authorize",
                    "token_endpoint": "https://claude.ai/oauth/token",
                    "registration_endpoint": f"{dcr_server.base_url}/register",
                    "scopes_supported": ["chat:write", "chat:read", "account:read"],
                    "response_types_supported": ["code"],
                    "grant_types_supported": ["authorization_code", "refresh_token"],
                    "code_challenge_methods_supported": ["S256"],
                    "token_endpoint_auth_methods_supported": ["none"]
                }
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            def handle_register(self):
                """Handle dynamic client registration."""
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length > 0 else b"{}"
                
                try:
                    request_data = json.loads(body.decode()) if body else {}
                except json.JSONDecodeError:
                    request_data = {}
                
                # Generate a unique client ID
                client_id = f"dataagent-{uuid.uuid4().hex[:8]}"
                
                # Get redirect URIs from request or use default
                redirect_uris = request_data.get("redirect_uris", [
                    "http://localhost:8080/callback",
                    "http://localhost:8081/callback",
                    "http://localhost:8082/callback"
                ])
                
                # Create registration response
                registration = {
                    "client_id": client_id,
                    "client_name": request_data.get("client_name", "DataAgent CLI"),
                    "client_secret": None,  # Public client
                    "redirect_uris": redirect_uris,
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "token_endpoint_auth_method": "none",
                    "application_type": "native",
                    "scope": "chat:write chat:read account:read",
                    "client_id_issued_at": int(time.time())
                }
                
                # Store registration
                dcr_server.registered_clients[client_id] = registration
                
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(registration).encode())
                
            def log_message(self, format, *args):
                """Suppress default logging."""
                pass
                
        # Find available port if specified port is in use
        server_address = ('', self.port)
        try:
            self.server = HTTPServer(server_address, DCRHandler)
        except OSError:
            # Port in use, find another
            with socket.socket() as s:
                s.bind(('', 0))
                self.port = s.getsockname()[1]
            self.base_url = f"http://localhost:{self.port}"
            server_address = ('', self.port)
            self.server = HTTPServer(server_address, DCRHandler)
            
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        return self.base_url
        
    def stop(self):
        """Stop the DCR server."""
        if self.server:
            self.server.shutdown()
            self.server_thread.join(timeout=1)
            
    def register_client(self, client_name: str = "DataAgent CLI", 
                       redirect_uris: list = None) -> Dict[str, Any]:
        """Register a client programmatically."""
        import requests
        
        data = {
            "client_name": client_name,
            "redirect_uris": redirect_uris or ["http://localhost:8080/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "application_type": "native"
        }
        
        response = requests.post(f"{self.base_url}/register", json=data)
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to register client: {response.text}")


def test_dcr_server():
    """Test the DCR server."""
    import requests
    
    print("Starting OAuth DCR Server...")
    server = OAuthDCRServer()
    base_url = server.start()
    print(f"Server running at: {base_url}")
    
    try:
        # Test protected resource endpoint
        print("\n1. Testing protected resource endpoint...")
        resp = requests.get(f"{base_url}/.well-known/oauth-protected-resource")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
        
        # Test authorization server endpoint
        print("\n2. Testing authorization server endpoint...")
        resp = requests.get(f"{base_url}/.well-known/oauth-authorization-server")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
        
        # Test client registration
        print("\n3. Testing dynamic client registration...")
        registration_data = {
            "client_name": "Test Client",
            "redirect_uris": ["http://localhost:8080/callback"]
        }
        resp = requests.post(f"{base_url}/register", json=registration_data)
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
        
        if resp.status_code == 201:
            client_data = resp.json()
            print(f"\n✅ Successfully registered client: {client_data['client_id']}")
            
    finally:
        print("\nStopping server...")
        server.stop()
        

if __name__ == "__main__":
    test_dcr_server()