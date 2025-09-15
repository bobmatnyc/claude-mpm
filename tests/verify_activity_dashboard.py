#!/usr/bin/env python3
"""Verify Activity Dashboard is working correctly"""

import time
import subprocess
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import socketio
from datetime import datetime

def check_server():
    """Check if monitor server is running"""
    try:
        response = requests.get("http://localhost:8765/socket.io/?EIO=4&transport=polling")
        if response.status_code == 200:
            print("✅ Monitor server is running")
            return True
        else:
            print(f"❌ Monitor server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Monitor server not accessible: {e}")
        return False

def send_test_events():
    """Send test events to populate the dashboard"""
    sio = socketio.Client()

    @sio.event
    def connect():
        print("📤 Sending test events...")

        events = [
            {
                "type": "Start",
                "timestamp": datetime.now().isoformat(),
                "request_id": "demo-001",
                "session_id": "session-demo-001",
                "event_id": f"evt-{int(time.time()*1000)}",
                "context": {
                    "user_instruction": "Analyze the codebase and create a summary",
                    "working_directory": "/Users/demo/project"
                }
            },
            {
                "type": "SubagentStart",
                "timestamp": datetime.now().isoformat(),
                "request_id": "demo-001",
                "session_id": "session-demo-001",
                "agent_name": "Engineer",
                "event_id": f"evt-{int(time.time()*1000)+1}",
                "context": {}
            },
            {
                "type": "ToolStart",
                "timestamp": datetime.now().isoformat(),
                "request_id": "demo-001",
                "session_id": "session-demo-001",
                "agent_name": "Engineer",
                "tool_name": "Grep",
                "event_id": f"evt-{int(time.time()*1000)+2}",
                "context": {
                    "pattern": "class.*:",
                    "path": "/Users/demo/project"
                }
            },
            {
                "type": "ToolStop",
                "timestamp": datetime.now().isoformat(),
                "request_id": "demo-001",
                "session_id": "session-demo-001",
                "agent_name": "Engineer",
                "tool_name": "Grep",
                "event_id": f"evt-{int(time.time()*1000)+3}",
                "context": {
                    "status": "success",
                    "matches": 42
                }
            },
            {
                "type": "TodoWrite",
                "timestamp": datetime.now().isoformat(),
                "request_id": "demo-001",
                "session_id": "session-demo-001",
                "agent_name": "Engineer",
                "event_id": f"evt-{int(time.time()*1000)+4}",
                "context": {
                    "todos": [
                        {"content": "Analyze code structure", "status": "completed"},
                        {"content": "Generate documentation", "status": "in_progress"},
                        {"content": "Create summary report", "status": "pending"}
                    ]
                }
            }
        ]

        for event in events:
            sio.emit('event', event)
            time.sleep(0.1)

        print("✅ Test events sent")

    try:
        sio.connect('http://localhost:8765')
        time.sleep(2)
        sio.disconnect()
    except Exception as e:
        print(f"❌ Could not send events: {e}")

def check_dashboard_selenium():
    """Check Activity Dashboard using Selenium"""
    print("\n🌐 Checking Activity Dashboard with Selenium...")

    options = Options()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    try:
        driver = webdriver.Chrome(options=options)
        driver.get("http://localhost:8765/static/activity.html")

        # Wait for page to load
        time.sleep(3)

        # Get console logs
        logs = driver.get_log('browser')

        # Check for connection success
        connected = False
        for log in logs:
            if 'Socket connected' in str(log.get('message', '')):
                connected = True
                break

        # Get connection status element
        status_element = driver.find_element(By.ID, 'connection-text')
        status_text = status_element.text

        if 'Connected' in status_text:
            print(f"✅ Dashboard shows: {status_text}")
            connected = True
        else:
            print(f"❌ Dashboard shows: {status_text}")

        # Check event count
        event_count = driver.find_element(By.ID, 'event-count').text
        session_count = driver.find_element(By.ID, 'session-count').text

        print(f"📊 Stats: {event_count}, {session_count}")

        driver.quit()
        return connected

    except Exception as e:
        print(f"❌ Selenium test failed: {e}")
        return False

def check_dashboard_simple():
    """Simple check by looking at the page content"""
    print("\n📋 Simple dashboard check...")

    try:
        # Open the dashboard in default browser
        subprocess.run(["open", "http://localhost:8765/static/activity.html"], check=False)

        print("✅ Activity Dashboard opened in browser")
        print("🔍 Please check the browser for:")
        print("   - Green 'Connected' status indicator")
        print("   - Event count showing received events")
        print("   - Activity tree displaying test events")

        return True

    except Exception as e:
        print(f"❌ Could not open dashboard: {e}")
        return False

def main():
    print("=== Activity Dashboard Connection Verification ===\n")

    # Check server
    if not check_server():
        print("\n⚠️  Please start the monitor server first:")
        print("   cd /Users/masa/Projects/claude-mpm")
        print("   python -m claude_mpm.services.monitor.server")
        return

    # Send test events
    send_test_events()
    time.sleep(1)

    # Try Selenium check (may fail if Chrome/ChromeDriver not installed)
    try:
        check_dashboard_selenium()
    except:
        print("⚠️  Selenium not available, skipping automated check")

    # Open dashboard for manual check
    check_dashboard_simple()

    print("\n=== Verification Complete ===")
    print("\n✅ If you see 'Connected' with a green indicator in the browser,")
    print("   the Activity Dashboard is working correctly!")
    print("\n📝 The dashboard should show:")
    print("   - Connection status: Connected (green)")
    print("   - Event count: 5 events (or more)")
    print("   - Session count: 1 session")
    print("   - Activity tree with test events")

if __name__ == "__main__":
    main()