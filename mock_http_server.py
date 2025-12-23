#!/usr/bin/env python3
"""
Mock HTTP Server for testing audit log HTTP transport.

This server accepts POST requests with Basic Auth and prints received events.
"""

import base64
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockHTTPHandler(BaseHTTPRequestHandler):
    """Handler for mock HTTP server"""

    # Expected credentials (username:password)
    EXPECTED_USERNAME = "admin"
    EXPECTED_PASSWORD = "secret"

    def _validate_auth(self) -> bool:
        """Validate Basic Auth header"""
        auth_header = self.headers.get("Authorization")
        if not auth_header:
            self.log_message("Missing Authorization header")
            return False

        try:
            auth_type, auth_data = auth_header.split(" ", 1)
            if auth_type.lower() != "basic":
                self.log_message(f"Invalid auth type: {auth_type}")
                return False

            decoded = base64.b64decode(auth_data).decode("utf-8")
            username, password = decoded.split(":", 1)

            if (
                username == self.EXPECTED_USERNAME
                and password == self.EXPECTED_PASSWORD
            ):
                return True
            else:
                self.log_message(f"Invalid credentials: {username}:***")
                return False
        except Exception as e:
            self.log_message(f"Auth validation error: {e}")
            return False

    def do_POST(self):
        """Handle POST requests"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Validate authentication
        if not self._validate_auth():
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_header("WWW-Authenticate", 'Basic realm="Mock HTTP Server"')
            self.end_headers()
            response = {"error": "Unauthorized"}
            self.wfile.write(json.dumps(response).encode())
            return

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            event = json.loads(body.decode("utf-8"))

            # Log received event
            print("=" * 80)
            print(f"[{timestamp}] Received event:")
            print(f"  Path: {self.path}")
            print(f"  Content-Type: {self.headers.get('Content-Type')}")
            print(f"  Content-Length: {content_length} bytes")
            print("  Event data:")
            print(json.dumps(event, indent=2, ensure_ascii=False))
            print("=" * 80)

            # Send success response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "success", "message": "Event received"}
            self.wfile.write(json.dumps(response).encode())

        except json.JSONDecodeError as e:
            print(f"[{timestamp}] ERROR: Invalid JSON: {e}")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"error": "Invalid JSON"}
            self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        """Override to customize log format"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys.stdout.write(f"[{timestamp}] {format % args}\n")


def run_server(port: int = 8080):
    """Run the mock HTTP server"""
    server_address = ("", port)
    httpd = HTTPServer(server_address, MockHTTPHandler)

    print("=" * 80)
    print("Mock HTTP Server for Audit Logs")
    print("=" * 80)
    print(f"Server listening on: http://0.0.0.0:{port}")
    print(
        f"Expected credentials: {MockHTTPHandler.EXPECTED_USERNAME}:{MockHTTPHandler.EXPECTED_PASSWORD}"
    )
    print("Test with:")
    print(f"  curl -X POST http://localhost:{port}/events \\")
    print("       -H 'Content-Type: application/json' \\")
    print(
        f"       -u {MockHTTPHandler.EXPECTED_USERNAME}:{MockHTTPHandler.EXPECTED_PASSWORD} \\"
    )
    print('       -d \'{{"event_id": "test123", "message": "Test event"}}\'')
    print("=" * 80)
    print("Press Ctrl+C to stop the server")
    print()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n" + "=" * 80)
        print("Server stopped")
        print("=" * 80)


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            print(f"Usage: python3 {sys.argv[0]} [port]")
            sys.exit(1)

    run_server(port)
