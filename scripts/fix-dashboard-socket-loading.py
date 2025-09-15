#!/usr/bin/env python3
"""
Fix Socket.IO loading in all dashboard HTML files.
Ensures proper Socket.IO initialization and connection handling.
"""

import os
import re
from pathlib import Path

# Dashboard HTML files to update
DASHBOARD_FILES = [
    'activity.html',
    'events.html',
    'agents.html',
    'tools.html',
    'files.html'
]

STATIC_DIR = Path('/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static')

# Socket.IO verification script to inject
SOCKET_IO_VERIFICATION = '''    <!-- Load Socket.IO -->
    <script src="/static/socket.io.min.js"></script>

    <!-- Verify Socket.IO is loaded -->
    <script>
        // Check if Socket.IO is loaded and available
        if (typeof io === 'undefined') {
            console.error('Socket.IO not loaded, attempting to load from CDN...');
            var script = document.createElement('script');
            script.src = 'https://cdn.socket.io/4.8.1/socket.io.min.js';
            script.onerror = function() {
                console.error('Failed to load Socket.IO from CDN');
            };
            document.head.appendChild(script);
        } else {
            console.log('Socket.IO loaded successfully, version:', io.version || 'unknown');
        }
    </script>'''

# Module initialization wrapper
MODULE_INIT_WRAPPER = '''    <!-- Load components -->
    <script type="module">
        // Wait for Socket.IO to be available
        function waitForSocketIO() {
            return new Promise((resolve) => {
                if (typeof io !== 'undefined') {
                    console.log('Socket.IO is ready');
                    resolve();
                } else {
                    console.log('Waiting for Socket.IO...');
                    setTimeout(() => waitForSocketIO().then(resolve), 100);
                }
            });
        }

        // Initialize after Socket.IO is ready
        await waitForSocketIO();
        console.log('Starting dashboard initialization...');'''

def fix_socket_loading(file_path):
    """Fix Socket.IO loading in a dashboard HTML file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check if already fixed
    if 'waitForSocketIO' in content:
        print(f"  ✓ {file_path.name} already fixed")
        return False

    # Replace Socket.IO loading section
    pattern = r'    <!-- Load Socket\.IO -->\s*<script src="/static/socket\.io\.min\.js"></script>'
    if re.search(pattern, content):
        content = re.sub(pattern, SOCKET_IO_VERIFICATION, content)
        print(f"  ✓ Updated Socket.IO loading in {file_path.name}")
    else:
        print(f"  ⚠ Socket.IO loading pattern not found in {file_path.name}")

    # Replace module initialization if not already done
    module_pattern = r'    <!-- Load components -->\s*<script type="module">'
    if re.search(module_pattern, content) and 'waitForSocketIO' not in content:
        content = re.sub(module_pattern, MODULE_INIT_WRAPPER, content)
        print(f"  ✓ Updated module initialization in {file_path.name}")

    # Write back
    with open(file_path, 'w') as f:
        f.write(content)

    return True

def main():
    """Main function to fix all dashboard files."""
    print("Fixing Socket.IO loading in dashboard files...")
    print(f"Target directory: {STATIC_DIR}")
    print()

    fixed_count = 0
    for file_name in DASHBOARD_FILES:
        file_path = STATIC_DIR / file_name
        if file_path.exists():
            print(f"Processing {file_name}:")
            if fix_socket_loading(file_path):
                fixed_count += 1
            print()
        else:
            print(f"  ✗ {file_name} not found")
            print()

    print(f"Summary: Fixed {fixed_count} files")

    # Test connection
    print("\nTo test the connection:")
    print("1. Open http://localhost:8765/static/test-socket-connection.html")
    print("2. Check browser console for connection status")
    print("3. Open any dashboard (e.g., http://localhost:8765/static/activity.html)")

if __name__ == '__main__':
    main()