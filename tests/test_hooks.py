#!/usr/bin/env python3
"""Test hook functionality."""

import time

import requests

# Check if hook service is running
try:
    response = requests.get("http://localhost:8080/health", timeout=2)
    print(f"Hook service health: {response.json()}")

    # List available hooks
    hooks_response = requests.get("http://localhost:8080/hooks/list", timeout=2)
    hooks = hooks_response.json()
    print(f"\nAvailable hooks: {len(hooks['hooks'])} hooks registered")
    for hook in hooks["hooks"]:
        print(
            f"  - {hook['name']} (type: {hook['hook_type']}, priority: {hook['priority']})"
        )

    # Test submit hook with urgent ticket
    test_payload = {
        "hook_type": "submit",
        "context": {
            "prompt": "urgent: fix bug TSK-123 in the payment system",
            "timestamp": time.time(),
        },
    }

    exec_response = requests.post(
        "http://localhost:8080/hooks/execute", json=test_payload, timeout=5
    )
    result = exec_response.json()
    print("\nSubmit hook test result:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Results: {result.get('results', [])}")

except requests.exceptions.ConnectionError:
    print("Hook service is not running on port 8080")
except Exception as e:
    print(f"Error testing hooks: {e}")
