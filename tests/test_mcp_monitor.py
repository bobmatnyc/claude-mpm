#!/usr/bin/env python3
"""
Test script for MCP monitoring solution.
This creates mock services to test the monitoring functionality.
"""

import os
import sys
import time
import signal
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class MockHealthHandler(BaseHTTPRequestHandler):
    """Mock health endpoint handler."""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
            
    def log_message(self, format, *args):
        # Suppress default logging
        pass


def run_mock_service(port: int, name: str, fail_after: int = None):
    """Run a mock service on the specified port."""
    print(f"Starting mock {name} on port {port}")
    
    server = HTTPServer(('localhost', port), MockHealthHandler)
    
    if fail_after:
        # Simulate failure after specified seconds
        def fail():
            time.sleep(fail_after)
            print(f"Mock {name} simulating failure...")
            server.shutdown()
            
        fail_thread = threading.Thread(target=fail)
        fail_thread.daemon = True
        fail_thread.start()
    
    try:
        server.serve_forever()
    except:
        pass
    finally:
        print(f"Mock {name} stopped")


def test_monitoring():
    """Test the monitoring system with mock services."""
    print("MCP Monitoring Test")
    print("==================")
    print()
    print("This test will:")
    print("1. Start mock services on ports 3001-3003")
    print("2. Simulate service failures")
    print("3. Verify the monitor restarts them")
    print()
    print("Press Ctrl+C to stop the test")
    print()
    
    # Start mock services in threads
    services = [
        threading.Thread(target=run_mock_service, args=(3001, "eva-memory", 30)),
        threading.Thread(target=run_mock_service, args=(3002, "cloud-bridge", 45)),
        threading.Thread(target=run_mock_service, args=(3003, "desktop-gateway", 60))
    ]
    
    for service in services:
        service.daemon = True
        service.start()
    
    # Give services time to start
    time.sleep(2)
    
    print("\nMock services started. You can now test the monitor.")
    print("The services will fail at:")
    print("  - eva-memory: 30 seconds")
    print("  - cloud-bridge: 45 seconds") 
    print("  - desktop-gateway: 60 seconds")
    print()
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest stopped")


if __name__ == '__main__':
    test_monitoring()