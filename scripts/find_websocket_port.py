#!/usr/bin/env python3
"""Find an available port for WebSocket server."""

import socket
import sys

def find_available_port(start_port=8765, max_attempts=100):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            # Port is in use, try next
            continue
    
    return None

def check_port_in_use(port):
    """Check if a port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return False
    except OSError:
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Check specific port
        port = int(sys.argv[1])
        if check_port_in_use(port):
            print(f"Port {port} is IN USE")
            sys.exit(1)
        else:
            print(f"Port {port} is AVAILABLE")
            sys.exit(0)
    else:
        # Find available port
        port = find_available_port()
        if port:
            print(f"Available port: {port}")
            print(f"\nRun claude-mpm with:")
            print(f"  claude-mpm --monitor --websocket-port {port}")
            sys.exit(0)
        else:
            print("No available ports found in range 8765-8865")
            sys.exit(1)