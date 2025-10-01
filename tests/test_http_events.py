#!/usr/bin/env python3
"""
Simple HTTP Event Tester
========================

Tests the HTTP event endpoint to verify event flow without Socket.IO complexity.
"""

import json
import sys
import time
from datetime import datetime, timezone

import requests


def test_http_event_endpoint():
    """Test the HTTP event endpoint."""
    url = "http://localhost:8765/api/events"

    # Test event data
    test_event = {
        "type": "hook",
        "subtype": "test_http",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"test_id": "http_test_001", "message": "Testing HTTP event endpoint"},
        "source": "test_script",
    }

    try:
        print(f"🚀 Sending HTTP POST to {url}")
        print(f"📦 Event data: {json.dumps(test_event, indent=2)}")

        response = requests.post(
            url,
            json=test_event,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )

        print(f"📡 Response status: {response.status_code}")
        print(f"📄 Response headers: {dict(response.headers)}")

        if response.text:
            print(f"📝 Response body: {response.text}")

        if response.status_code == 204:
            print("✅ HTTP event sent successfully!")
            return True
        print(f"❌ HTTP event failed with status {response.status_code}")
        return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the monitor server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_health_endpoint():
    """Test if the server is responding."""
    try:
        response = requests.get("http://localhost:8765/", timeout=5)
        if response.status_code == 200:
            print("✅ Server is responding")
            return True
        print(f"⚠️ Server responded with status {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing HTTP Event Endpoint")
    print("=" * 40)

    # Test server health first
    if not test_health_endpoint():
        print("❌ Server is not responding, cannot test events")
        sys.exit(1)

    # Test HTTP event endpoint
    success = test_http_event_endpoint()

    if success:
        print("\n✅ HTTP event test completed successfully")
        print(
            "💡 Check the dashboard at http://localhost:8765 to see if the event appeared"
        )
    else:
        print("\n❌ HTTP event test failed")
        sys.exit(1)
