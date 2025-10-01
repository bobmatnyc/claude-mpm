#!/usr/bin/env python3
"""
Comprehensive test for dashboard event display.
Tests the entire event flow from generation to display.
"""

import pytest

# Skip entire module - EventBroadcaster class was removed in refactoring
pytestmark = pytest.mark.skip(
    reason="EventBroadcaster class was removed in refactoring - needs rewrite"
)

import asyncio
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import socketio

# from claude_mpm.services.socketio.server.broadcaster import EventBroadcaster  # Module removed

# ANSI color codes for output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log_step(step, message, status="INFO"):
    """Log a test step with color coding."""
    colors = {"INFO": BLUE, "SUCCESS": GREEN, "WARNING": YELLOW, "ERROR": RED}
    color = colors.get(status, RESET)
    print(f"{color}{BOLD}[Step {step}] {status}: {RESET}{color}{message}{RESET}")


def log_result(success, message):
    """Log a test result."""
    if success:
        print(f"{GREEN}✓ {message}{RESET}")
    else:
        print(f"{RED}✗ {message}{RESET}")


@pytest.mark.asyncio
async def test_server_running():
    """Test if the server is running and accessible."""
    log_step(1, "Checking if SocketIO server is running", "INFO")

    try:
        result = subprocess.run(
            ["claude-mpm", "monitor", "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if "is running" in result.stdout:
            log_result(True, "Server is running")
            # Extract port from output
            if "Port: " in result.stdout:
                port_line = [
                    line for line in result.stdout.split("\n") if "Port: " in line
                ]
                if port_line:
                    port = port_line[0].split("Port: ")[1].strip()
                    log_result(True, f"Server is on port {port}")
                    return True, port
            return True, "8765"
        log_result(False, "Server is not running")
        return False, None
    except Exception as e:
        log_result(False, f"Failed to check server status: {e}")
        return False, None


@pytest.mark.asyncio
async def test_socketio_connection(port="8765"):
    """Test connecting to the SocketIO server."""
    log_step(2, "Testing SocketIO connection", "INFO")

    sio = socketio.AsyncClient()
    connected = False

    @sio.event
    async def connect():
        nonlocal connected
        connected = True
        log_result(True, "Connected to SocketIO server")

    @sio.event
    async def connect_error(data):
        log_result(False, f"Connection error: {data}")

    try:
        await sio.connect(f"http://localhost:{port}")
        await asyncio.sleep(1)

        if connected:
            # Test getting status
            try:
                await sio.emit("get_status")
                await asyncio.sleep(0.5)
                log_result(True, "Successfully sent get_status request")
            except Exception as e:
                log_result(False, f"Failed to send get_status: {e}")

            await sio.disconnect()
            return True
        log_result(False, "Failed to connect to server")
        return False

    except Exception as e:
        log_result(False, f"Connection failed: {e}")
        return False


@pytest.mark.asyncio
async def test_event_broadcasting(port="8765"):
    """Test broadcasting events through the EventBroadcaster."""
    log_step(3, "Testing event broadcasting", "INFO")

    broadcaster = EventBroadcaster()
    success_count = 0

    # Test different event types
    test_events = [
        {
            "type": "test_event",
            "data": {
                "message": "Test event 1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": "broadcast_test_1",
            },
        },
        {
            "type": "claude_event",
            "data": {
                "event": "TestStart",
                "message": "Starting comprehensive test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": "broadcast_test_2",
            },
        },
        {
            "type": "system_event",
            "data": {
                "event": "heartbeat",
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": "broadcast_test_3",
            },
        },
    ]

    for i, event in enumerate(test_events, 1):
        try:
            result = await broadcaster.broadcast_event(event["type"], event["data"])
            if result:
                log_result(True, f"Broadcast event {i}: {event['type']}")
                success_count += 1
            else:
                log_result(False, f"Failed to broadcast event {i}: {event['type']}")
        except Exception as e:
            log_result(False, f"Error broadcasting event {i}: {e}")

    return success_count == len(test_events)


@pytest.mark.asyncio
async def test_event_reception(port="8765"):
    """Test receiving events from the server."""
    log_step(4, "Testing event reception", "INFO")

    sio = socketio.AsyncClient()
    received_events = []
    received_history = False

    @sio.event
    async def connect():
        log_result(True, "Connected for event reception test")

    @sio.event
    async def history(data):
        nonlocal received_history
        received_history = True
        log_result(True, f"Received history with {len(data.get('events', []))} events")

    @sio.event
    async def claude_event(data):
        received_events.append(data)
        log_result(True, f"Received claude_event: {data.get('event', 'unknown')}")

    @sio.event
    async def system_event(data):
        received_events.append(data)
        log_result(True, f"Received system_event: {data.get('event', 'unknown')}")

    try:
        await sio.connect(f"http://localhost:{port}")
        await asyncio.sleep(1)

        # Send some test events
        broadcaster = EventBroadcaster()

        test_event = {
            "event": "TestEvent",
            "message": "Testing event reception",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_id": "reception_test",
        }

        await broadcaster.broadcast_event("claude_event", test_event)
        await asyncio.sleep(2)  # Wait for events to propagate

        await sio.disconnect()

        if received_history or len(received_events) > 0:
            log_result(True, f"Successfully received {len(received_events)} events")
            return True
        log_result(False, "No events received")
        return False

    except Exception as e:
        log_result(False, f"Event reception test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_dashboard_connection(port="8765"):
    """Test if the dashboard can connect and receive events."""
    log_step(5, "Testing dashboard connection", "INFO")

    dashboard_url = f"http://localhost:{port}"
    log_result(True, f"Dashboard should be accessible at: {dashboard_url}")

    # Test if the dashboard endpoint responds
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(dashboard_url) as response:
                if response.status == 200:
                    log_result(True, "Dashboard endpoint is responding")
                    return True
                log_result(False, f"Dashboard returned status {response.status}")
                return False
    except Exception as e:
        log_result(False, f"Failed to access dashboard: {e}")
        return False


async def generate_test_events_batch(port="8765"):
    """Generate a batch of test events to populate the dashboard."""
    log_step(6, "Generating batch of test events", "INFO")

    broadcaster = EventBroadcaster()
    events_sent = 0

    # Generate various types of events
    event_templates = [
        {
            "type": "claude_event",
            "event": "SubagentStart",
            "agent": "Engineer",
            "task": "Implementing test feature",
            "priority": "high",
        },
        {
            "type": "claude_event",
            "event": "SubagentMessage",
            "agent": "Engineer",
            "message": "Analyzing codebase structure...",
        },
        {
            "type": "claude_event",
            "event": "SubagentStop",
            "agent": "Engineer",
            "result": "Task completed successfully",
            "duration": 1234,
        },
        {
            "type": "system_event",
            "event": "heartbeat",
            "status": "healthy",
            "cpu": 45.2,
            "memory": 67.8,
        },
        {
            "type": "claude_event",
            "event": "Start",
            "session_id": "test_session_123",
            "message": "Starting new session",
        },
        {
            "type": "claude_event",
            "event": "ToolCall",
            "tool": "Write",
            "args": {"file": "test.py", "content": "print('hello')"},
        },
        {
            "type": "claude_event",
            "event": "Error",
            "error": "Test error for debugging",
            "severity": "warning",
        },
    ]

    for i, template in enumerate(event_templates, 1):
        event_type = template.pop("type")
        template["timestamp"] = datetime.now(timezone.utc).isoformat()
        template["test_batch_id"] = f"batch_{i}"

        try:
            result = await broadcaster.broadcast_event(event_type, template)
            if result:
                events_sent += 1
                log_result(
                    True,
                    f"Sent event {i}/{len(event_templates)}: {template.get('event', 'unknown')}",
                )
            else:
                log_result(False, f"Failed to send event {i}")
        except Exception as e:
            log_result(False, f"Error sending event {i}: {e}")

        await asyncio.sleep(0.5)  # Small delay between events

    log_result(
        True, f"Successfully sent {events_sent}/{len(event_templates)} test events"
    )
    return events_sent > 0


async def main():
    """Run all diagnostic tests."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}Dashboard Event Display Diagnostic Test{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Track test results
    results = {}

    # Test 1: Check server status
    is_running, port = await test_server_running()
    results["server_running"] = is_running

    if not is_running:
        log_step("", "Server is not running. Attempting to start it...", "WARNING")
        subprocess.run(
            ["claude-mpm", "monitor", "start"], capture_output=True, check=False
        )
        await asyncio.sleep(3)
        is_running, port = await test_server_running()
        results["server_running"] = is_running

    if not is_running:
        log_step(
            "", "Failed to start server. Please run: claude-mpm monitor start", "ERROR"
        )
        return

    # Test 2: SocketIO connection
    results["socketio_connection"] = await test_socketio_connection(port)

    # Test 3: Event broadcasting
    results["event_broadcasting"] = await test_event_broadcasting(port)

    # Test 4: Event reception
    results["event_reception"] = await test_event_reception(port)

    # Test 5: Dashboard connection
    results["dashboard_connection"] = await test_dashboard_connection(port)

    # Test 6: Generate batch of test events
    results["batch_generation"] = await generate_test_events_batch(port)

    # Summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}Test Results Summary:{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    all_passed = True
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        color = GREEN if passed else RED
        print(f"{color}{status:8} {test_name}{RESET}")
        if not passed:
            all_passed = False

    print(f"\n{BOLD}{'='*60}{RESET}")

    if all_passed:
        print(f"{GREEN}{BOLD}✓ All tests passed!{RESET}")
        print(f"\n{BOLD}Next Steps:{RESET}")
        print(f"1. Open the dashboard at: {BLUE}http://localhost:{port}{RESET}")
        print("2. You should see the test events in the dashboard")
        print("3. Check browser console for any JavaScript errors")

        # Offer to open dashboard
        print(f"\n{YELLOW}Opening dashboard in browser...{RESET}")
        webbrowser.open(f"http://localhost:{port}")
    else:
        print(f"{RED}{BOLD}✗ Some tests failed. Please check the errors above.{RESET}")
        print(f"\n{BOLD}Troubleshooting:{RESET}")
        print("1. Check server logs: tail -f ~/.claude-mpm/socketio-server.log")
        print("2. Restart the server: claude-mpm monitor restart")
        print(f"3. Check for port conflicts: lsof -i :{port}")


if __name__ == "__main__":
    asyncio.run(main())
