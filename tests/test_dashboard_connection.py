#!/usr/bin/env python3
"""Test dashboard connection and provide quick fixes."""

import os
import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🔌 Testing Dashboard Socket.IO Connection")
    print("=" * 60)
    
    # First, ensure the Socket.IO server is running
    print("\n1. Starting Socket.IO server...")
    server_process = subprocess.Popen(
        [sys.executable, "scripts/start_persistent_socketio_server.py"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give it time to start
    time.sleep(3)
    
    # Open dashboard with debugging
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    
    # Create a test HTML file with extra debugging
    test_dashboard = dashboard_path.read_text()
    
    # Add debugging to the connection
    debug_addition = """
    <script>
        // Add debugging for connection issues
        window.addEventListener('load', function() {
            console.log('Page loaded, checking autoconnect...');
            const urlParams = new URLSearchParams(window.location.search);
            console.log('URL params:', Object.fromEntries(urlParams));
            console.log('autoconnect:', urlParams.get('autoconnect'));
            console.log('port:', urlParams.get('port'));
            
            // Force connection after a delay if not connected
            setTimeout(function() {
                if (!window.socket || !window.socket.connected) {
                    console.log('Not connected after 2s, forcing connection...');
                    connectSocket();
                }
            }, 2000);
        });
        
        // Override console.error to catch any errors
        const originalError = console.error;
        console.error = function(...args) {
            alert('JavaScript Error: ' + args.join(' '));
            originalError.apply(console, args);
        };
    </script>
    """
    
    # Insert before closing body tag
    test_dashboard = test_dashboard.replace('</body>', debug_addition + '\n</body>')
    
    # Save as test file
    test_file = Path(__file__).parent / "test_dashboard_debug.html"
    test_file.write_text(test_dashboard)
    
    # Open with debugging
    test_url = f"file://{test_file}?autoconnect=true&port=8765"
    print(f"\n2. Opening test dashboard: {test_url}")
    webbrowser.open(test_url)
    
    print("\n3. Generating test event...")
    time.sleep(2)
    
    # Generate a test event
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "echo 'Testing Socket.IO connection'",
        "--non-interactive",
        "--monitor"
    ]
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    print("\n4. Check the browser:")
    print("   - Look for connection status in header")
    print("   - Check browser console (F12) for errors")
    print("   - Look for any JavaScript alerts")
    
    print("\n5. Quick fixes to try:")
    print("   a) Manually click 'Connect' button")
    print("   b) Check if port 8765 is blocked")
    print("   c) Try different browser")
    print("   d) Clear browser cache")
    
    print("\n6. If still not working, check for:")
    print("   - JavaScript syntax errors in recent edits")
    print("   - Missing closing tags or brackets")
    print("   - Incorrect variable references")
    
    # Keep server running for testing
    print("\n✅ Server is running. Press Ctrl+C to stop.")
    try:
        server_process.wait()
    except KeyboardInterrupt:
        server_process.terminate()
        print("\n👋 Server stopped.")

if __name__ == "__main__":
    main()