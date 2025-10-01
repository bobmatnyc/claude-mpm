#!/usr/bin/env python3
"""
Dashboard Connection Status Summary
Shows the current status of all Claude MPM dashboards.
"""

import time
from datetime import datetime

import requests
import socketio


def check_server():
    """Check if the server is running."""
    try:
        response = requests.get("http://localhost:8765/health", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        # Try socket.io endpoint
        try:
            response = requests.get("http://localhost:8765/socket.io/", timeout=2)
            return True
        except requests.RequestException:
            return False


def check_dashboard(dashboard_name):
    """Check if a dashboard is accessible and has proper Socket.IO setup."""
    url = f"http://localhost:8765/static/{dashboard_name}"
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            content = response.text
            has_socketio = "socket.io.min.js" in content
            has_verification = "typeof io === 'undefined'" in content
            has_wait = "waitForSocketIO" in content

            return {
                "accessible": True,
                "has_socketio": has_socketio,
                "has_verification": has_verification,
                "has_wait": has_wait,
                "fully_fixed": has_socketio and has_verification,
            }
    except Exception as e:
        return {"accessible": False, "error": str(e)}
    return {"accessible": False}


def test_websocket():
    """Test WebSocket connection."""
    sio = socketio.Client()
    connected = False

    @sio.event
    def connect():
        nonlocal connected
        connected = True

    try:
        sio.connect("http://localhost:8765", transports=["polling", "websocket"])
        time.sleep(1)
        result = connected
        sio.disconnect()
        return result
    except (socketio.exceptions.ConnectionError, OSError, TimeoutError):
        return False


def main():
    print("=" * 70)
    print("📊 CLAUDE MPM DASHBOARD CONNECTION STATUS SUMMARY")
    print("=" * 70)
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check server
    print("🖥️  SERVER STATUS")
    print("-" * 40)
    server_running = check_server()
    print(f"   Monitor Server: {'✅ Running' if server_running else '❌ Not Running'}")
    print("   URL: http://localhost:8765")

    # Test WebSocket
    ws_connected = test_websocket() if server_running else False
    print(f"   WebSocket: {'✅ Connected' if ws_connected else '❌ Not Connected'}")
    print()

    # Check dashboards
    dashboards = [
        ("activity.html", "🎯 Activity Dashboard"),
        ("events.html", "📊 Events Dashboard"),
        ("agents.html", "🤖 Agents Dashboard"),
        ("tools.html", "🔧 Tools Dashboard"),
        ("files.html", "📁 Files Dashboard"),
    ]

    print("📱 DASHBOARD STATUS")
    print("-" * 40)

    all_working = True
    for filename, name in dashboards:
        status = check_dashboard(filename)

        if status.get("accessible"):
            if status.get("fully_fixed"):
                icon = "✅"
                status_text = "Connected & Working"
            elif status.get("has_socketio"):
                icon = "⚠️"
                status_text = "Partial (needs fix)"
                all_working = False
            else:
                icon = "❌"
                status_text = "Not configured"
                all_working = False
        else:
            icon = "❌"
            status_text = "Not accessible"
            all_working = False

        print(f"   {icon} {name:25} - {status_text}")

    print()
    print("🔍 CONNECTION FIX DETAILS")
    print("-" * 40)

    for filename, name in dashboards:
        status = check_dashboard(filename)
        if status.get("accessible"):
            checks = []
            checks.append(
                "✅ Socket.IO loaded"
                if status.get("has_socketio")
                else "❌ Socket.IO missing"
            )
            checks.append(
                "✅ Fallback to CDN"
                if status.get("has_verification")
                else "❌ No CDN fallback"
            )
            if filename != "events.html":  # Events.html doesn't need waitForSocketIO
                checks.append(
                    "✅ Wait for IO ready"
                    if status.get("has_wait")
                    else "❌ No IO wait"
                )

            print(f"   {name}:")
            for check in checks:
                print(f"      {check}")

    print()
    print("=" * 70)
    print("📌 SUMMARY")
    print("-" * 40)

    if server_running and ws_connected and all_working:
        print("✅ All systems operational! Dashboards are connected and working.")
        print()
        print("🎯 Next Steps:")
        print("   1. Open any dashboard: http://localhost:8765/static/activity.html")
        print("   2. Look for green 'Connected' status in the header")
        print("   3. Events should appear in real-time")
    else:
        print("⚠️  Some issues detected:")
        if not server_running:
            print("   - Start the monitor server: claude-mpm monitor")
        if not ws_connected:
            print("   - WebSocket connection failed - check server logs")
        if not all_working:
            print("   - Some dashboards need fixing - run fix script")

    print()
    print("🧪 TEST COMMANDS:")
    print("   - Test connection: python3 scripts/test-websocket-connections.py")
    print("   - Send test events: python3 scripts/verify-dashboard-connection.py")
    print("   - Fix dashboards: python3 scripts/fix-dashboard-socket-loading.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
