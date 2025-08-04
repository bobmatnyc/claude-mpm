#!/usr/bin/env python3
"""Socket.IO Dashboard Launcher for Claude MPM.

WHY: This script provides a streamlined solution for launching the Socket.IO
monitoring dashboard using only the Python Socket.IO server implementation.
It handles server startup, dashboard creation, and browser opening.

DESIGN DECISION: Uses only python-socketio and aiohttp for a clean,
Node.js-free implementation. This simplifies deployment and reduces
dependencies while maintaining full functionality.

The script handles:
1. Python Socket.IO server startup
2. Dashboard HTML creation and serving
3. Browser opening with proper URL construction
4. Background/daemon mode operation
5. Graceful error handling and user feedback
"""

import argparse
import os
import sys
import time
import webbrowser
import signal
from pathlib import Path
from typing import Optional

# Get script directory for relative paths  
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # Go up to project root from src/claude_mpm/scripts/

def check_python_dependencies() -> bool:
    """Check if Python Socket.IO dependencies are available.
    
    WHY: We need python-socketio and aiohttp packages for the server.
    This function validates the environment and provides clear feedback.
    
    Returns:
        bool: True if Python dependencies are ready, False otherwise
    """
    try:
        import socketio
        import aiohttp
        socketio_version = getattr(socketio, '__version__', 'unknown')
        aiohttp_version = getattr(aiohttp, '__version__', 'unknown')
        print(f"✓ python-socketio v{socketio_version} detected")
        print(f"✓ aiohttp v{aiohttp_version} detected")
        return True
    except ImportError as e:
        print(f"❌ Required Python packages missing: {e}")
        print("   Install with: pip install python-socketio aiohttp")
        return False



def check_dashboard_availability(port: int):
    """Check if the modular dashboard is available.
    
    WHY: The new architecture uses a modular dashboard served by the Socket.IO server
    instead of creating static HTML files. This validates the proper dashboard exists.
    
    Args:
        port: Port number for the Socket.IO server
    """
    # Check if new modular dashboard is available
    web_templates_dir = PROJECT_ROOT / "src" / "claude_mpm" / "web" / "templates"
    modular_dashboard = web_templates_dir / "index.html"
    if modular_dashboard.exists():
        print(f"✓ Modular dashboard found at {modular_dashboard}")
        return True
    else:
        print(f"⚠️  Modular dashboard not found at {modular_dashboard}")
        print(f"   Expected path: {modular_dashboard}")
        return False

def check_server_running(port: int) -> bool:
    """Check if a Socket.IO server is already running on the specified port.
    
    WHY: We want to avoid starting multiple servers on the same port
    and provide clear feedback to users about existing servers.
    
    Args:
        port: Port number to check
        
    Returns:
        bool: True if server is running, False otherwise
    """
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"✓ Socket.IO server already running on port {port}")
                return True
    except Exception:
        pass
    
    return False

def start_python_server(port: int, daemon: bool = False) -> Optional:
    """Start the Python Socket.IO server.
    
    WHY: Uses python-socketio and aiohttp for a clean, Node.js-free
    implementation that handles all Socket.IO functionality.
    
    Args:
        port: Port number for the server
        daemon: Whether to run in background mode
        
    Returns:
        Thread object if successful, None otherwise
    """
    try:
        # Import the existing Python Socket.IO server
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from claude_mpm.services.socketio_server import SocketIOServer
        
        server = SocketIOServer(port=port)
        
        if daemon:
            # Start in background thread
            server.start()
            print(f"🚀 Python Socket.IO server started on port {port}")
            return server.thread
        else:
            # Start and block
            print(f"🚀 Starting Python Socket.IO server on port {port}")
            server.start()
            
            # Keep alive until interrupted
            try:
                while server.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\\n🛑 Shutting down Python server...")
                server.stop()
            
            return None
            
    except Exception as e:
        print(f"❌ Failed to start Python server: {e}")
        return None

def open_dashboard(port: int, no_browser: bool = False):
    """Open the Socket.IO dashboard in browser.
    
    WHY: Users need easy access to the monitoring dashboard. This function
    handles URL construction and browser opening with fallback options.
    Now uses the new modular dashboard location.
    
    Args:
        port: Port number for the Socket.IO server
        no_browser: Skip browser opening if True
    """
    if no_browser:
        print(f"📊 Dashboard available at: http://localhost:{port}/dashboard")
        return
    
    dashboard_url = f"http://localhost:{port}/dashboard?autoconnect=true&port={port}"
    
    try:
        print(f"🌐 Opening dashboard: {dashboard_url}")
        webbrowser.open(dashboard_url)
        
    except Exception as e:
        print(f"⚠️  Failed to open browser automatically: {e}")
        print(f"📊 Dashboard: {dashboard_url}")

def cleanup_handler(signum, frame):
    """Handle cleanup on shutdown signals.
    
    WHY: Proper cleanup ensures sockets are closed and resources freed
    when the script is terminated.
    """
    print("\\n🛑 Shutting down Socket.IO launcher...")
    sys.exit(0)

def main():
    """Main entry point for the Socket.IO dashboard launcher.
    
    WHY: This orchestrates the entire launch process, from dependency checking
    to server startup and dashboard opening, with comprehensive error handling.
    """
    parser = argparse.ArgumentParser(
        description="Launch Socket.IO dashboard for Claude MPM monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python launch_socketio_dashboard.py                    # Start with default settings
  python launch_socketio_dashboard.py --port 3000       # Use specific port
  python launch_socketio_dashboard.py --daemon          # Run in background
  python launch_socketio_dashboard.py --no-browser      # Don't open browser
  python launch_socketio_dashboard.py --setup-only      # Just create files
        '''
    )
    
    parser.add_argument('--port', type=int, default=3000,
                       help='Socket.IO server port (default: 3000)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run server in background mode')
    parser.add_argument('--no-browser', action='store_true',
                       help='Skip opening browser automatically')
    parser.add_argument('--setup-only', action='store_true',
                       help='Create necessary files without starting server')
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    print("🚀 Claude MPM Socket.IO Dashboard Launcher")
    print("=" * 50)
    
    # Check dashboard availability (modular dashboard)
    check_dashboard_availability(args.port)
    
    if args.setup_only:
        # Just setup files, don't start server
        print("📁 Setup complete - files created")
        return
    
    # Check if server is already running
    if check_server_running(args.port):
        print(f"✅ Using existing server on port {args.port}")
        open_dashboard(args.port, args.no_browser)
        return
    
    # Check Python dependencies
    if not check_python_dependencies():
        print("❌ Required Python packages not available")
        sys.exit(1)
    
    # Start Python Socket.IO server
    print("🟢 Using Python Socket.IO server")
    
    try:
        server_thread = start_python_server(args.port, args.daemon)
        
        if server_thread or not args.daemon:
            # Server started or is starting
            time.sleep(2)  # Give server time to start
            open_dashboard(args.port, args.no_browser)
            
            if args.daemon and server_thread:
                print(f"🔄 Python server running in background")
                print(f"   Dashboard: http://localhost:{args.port}/dashboard")
        else:
            print("❌ Failed to start Socket.IO server")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n✅ Socket.IO launcher stopped")
    except Exception as e:
        print(f"❌ Launcher error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()