#!/usr/bin/env python3
"""Test Socket.IO loading in activity.html"""

import re

import requests

# Test if Socket.IO is being loaded correctly
url = "http://localhost:8765/static/activity.html"
response = requests.get(url)

if response.status_code == 200:
    content = response.text

    # Check for Socket.IO script tag
    socket_io_tag = re.search(
        r'<script[^>]*src=["\']([^"\']*socket\.io[^"\']*)["\']', content
    )
    if socket_io_tag:
        print(f"✓ Socket.IO script tag found: {socket_io_tag.group(1)}")

        # Test if the Socket.IO file is accessible
        socket_io_url = socket_io_tag.group(1)
        if not socket_io_url.startswith("http"):
            socket_io_url = f"http://localhost:8765{socket_io_url}"

        socket_response = requests.get(socket_io_url)
        if socket_response.status_code == 200:
            print(f"✓ Socket.IO library is accessible at {socket_io_url}")
            print(f"  Size: {len(socket_response.content)} bytes")
        else:
            print(f"✗ Socket.IO library NOT accessible: {socket_response.status_code}")
    else:
        print("✗ No Socket.IO script tag found")

    # Check for Socket.IO verification code
    if "typeof io === 'undefined'" in content:
        print("✓ Socket.IO verification code present")

    # Check for socket client import
    if "socket-client.js" in content:
        print("✓ socket-client.js import found")

    # Check connection code
    if "socketClient.connect()" in content:
        print("✓ Socket connection code found")

    # Look for any console.log statements that might help debug
    console_logs = re.findall(r'console\.log\([\'"]([^"\']+)', content)
    if console_logs:
        print("\nConsole log statements found:")
        for log in console_logs[:5]:
            print(f"  - {log}")
else:
    print(f"✗ Failed to load activity.html: {response.status_code}")

# Test Socket.IO endpoint directly
print("\n--- Testing Socket.IO endpoint ---")
socket_test = requests.get("http://localhost:8765/socket.io/?EIO=4&transport=polling")
if socket_test.status_code == 200:
    print(f"✓ Socket.IO endpoint working: {socket_test.text[:100]}...")
else:
    print(f"✗ Socket.IO endpoint error: {socket_test.status_code}")
