#!/usr/bin/env python3
"""
Test script to verify debugging fixes for git branch "Unknown" error and HUD display issues.

WHY: This script helps verify that the comprehensive debugging we added is working
correctly by starting the socket server and providing a way to test both issues:
1. Git branch "Unknown" error tracing
2. HUD not displaying issue tracing

Usage:
    python scripts/test_debug_fixes.py
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.services.socketio_server import SocketIOServer
import logging

def setup_logging():
    """Set up detailed logging to see debug messages."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug_test.log')
        ]
    )
    
    # Set the socketio server to info level to see our debug messages
    socketio_logger = logging.getLogger('socketio_server')
    socketio_logger.setLevel(logging.INFO)
    
    return logging.getLogger('debug_test')

def main():
    """Main test function."""
    logger = setup_logging()
    logger.info("Starting debug test for git branch and HUD issues")
    
    # Start the SocketIO server
    try:
        logger.info("Starting SocketIO server on port 8765")
        server = SocketIOServer(host='localhost', port=8765)
        server.start()
        
        # Give server time to start
        time.sleep(2)
        
        # Open browser to dashboard
        dashboard_url = "http://localhost:8765/dashboard"
        logger.info(f"Opening dashboard in browser: {dashboard_url}")
        webbrowser.open(dashboard_url)
        
        print("\n" + "="*80)
        print("DEBUG TEST INSTRUCTIONS")
        print("="*80)
        print("1. The dashboard should now be open in your browser")
        print("2. Open browser developer console (F12) to see debug logs")
        print("3. Look for logs starting with:")
        print("   - [SESSION-DEBUG] - Session manager debugging")
        print("   - [WORKING-DIR-DEBUG] - Working directory debugging") 
        print("   - [GIT-BRANCH-DEBUG] - Git branch debugging")
        print("   - [HUD-DEBUG] - HUD manager debugging")
        print("\n4. Test scenarios:")
        print("   a) Change working directory - watch for 'Unknown' values")
        print("   b) Select different sessions - watch HUD button state")
        print("   c) Try to enable HUD - watch for session selection issues")
        print("\n5. Server logs are also saved to 'debug_test.log'")
        print("\nPress Ctrl+C to stop the server when done testing...")
        print("="*80)
        
        # Keep server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, stopping server")
            
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if 'server' in locals():
            logger.info("Stopping SocketIO server")
            server.stop()

if __name__ == '__main__':
    main()