#!/usr/bin/env python3
"""Final verification that hook events reach the dashboard correctly."""

import asyncio
import os
import sys

# Minimal debug output
os.environ["CLAUDE_MPM_EVENTBUS_DEBUG"] = "false"
os.environ["CLAUDE_MPM_RELAY_DEBUG"] = "false"
os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "false"

sys.path.insert(0, "/Users/masa/Projects/claude-mpm/src")

from claude_mpm.services.event_bus import EventBus
from claude_mpm.services.socketio.server.main import SocketIOServer


async def verify_pipeline():
    """Verify the complete hook to dashboard pipeline."""

    print("\n" + "=" * 70)
    print(" HOOK EVENTS TO DASHBOARD - FINAL VERIFICATION")
    print("=" * 70)

    # Start server
    print("\n[1] Starting SocketIO server with EventBus integration...")
    server = SocketIOServer(port=8765)
    server.start_sync()
    await asyncio.sleep(1)

    # Verify components
    print("\n[2] Checking components:")

    # Check EventBus
    event_bus = EventBus.get_instance()
    print(f"    ✓ EventBus: {'Enabled' if event_bus._enabled else 'Disabled'}")

    # Check integration
    if hasattr(server, "eventbus_integration"):
        integration = server.eventbus_integration
        print(
            f"    ✓ EventBus Integration: {'Active' if integration.is_active() else 'Inactive'}"
        )

        if integration.relay:
            print(f"    ✓ DirectSocketIORelay: Connected={integration.relay.connected}")
            stats = integration.relay.get_stats()
            print(f"      - Has server: {stats['has_server']}")
            print(f"      - Has broadcaster: {stats['has_broadcaster']}")
    else:
        print("    ✗ EventBus Integration: Not found")
        server.stop_sync()
        return

    # Create client to verify reception
    try:
        import socketio

        client = socketio.AsyncClient()
        received_events = []

        @client.event
        async def claude_event(data):
            received_events.append(data)

        await client.connect("http://localhost:8765")
        print("\n[3] Dashboard client connected")
        await asyncio.sleep(0.5)

        # Test events through EventBus only (not connection pool)
        print("\n[4] Publishing test events via EventBus:")

        test_scenarios = [
            (
                "hook.pre_tool",
                {
                    "tool_name": "Read",
                    "file_path": "/test.txt",
                    "sessionId": "test-123",
                },
            ),
            (
                "hook.post_tool",
                {"tool_name": "Write", "result": "success", "sessionId": "test-123"},
            ),
            (
                "hook.subagent_stop",
                {
                    "agent_type": "Engineer",
                    "result": "complete",
                    "sessionId": "test-123",
                },
            ),
        ]

        for event_type, event_data in test_scenarios:
            success = event_bus.publish(event_type, event_data)
            status = "✓" if success else "✗"
            print(f"    {status} Published: {event_type}")
            await asyncio.sleep(0.3)

        # Wait for processing
        await asyncio.sleep(1)

        # Check results
        print("\n[5] Results:")
        print(f"    - Events published: {len(test_scenarios)}")
        print(f"    - Events received by dashboard: {len(received_events)}")

        if received_events:
            print("\n[6] Event details:")
            for i, event in enumerate(received_events, 1):
                subtype = event.get("subtype", "unknown")
                data = event.get("data", {})
                tool = data.get("tool_name", "") or data.get("agent_type", "")
                print(f"    {i}. {subtype}: {tool}")

        # Final assessment
        print("\n" + "=" * 70)

        # Check relay stats
        final_stats = integration.relay.get_stats()
        relayed = final_stats["events_relayed"]

        if len(received_events) >= len(test_scenarios):
            print(" ✅ SUCCESS! Hook events are reaching the dashboard!")
            print(f"    - {relayed} events relayed via EventBus → SocketIO")
            print(f"    - {len(received_events)} events received by dashboard client")
            print("\n The pipeline is working correctly:")
            print("    Hook → EventBus → DirectSocketIORelay → Dashboard")
        else:
            print(" ⚠️  PARTIAL SUCCESS")
            print(
                f"    - Expected {len(test_scenarios)} events, received {len(received_events)}"
            )
            print(f"    - Relay processed {relayed} events")

            # Debug info
            eventbus_stats = event_bus.get_stats()
            print("\n Debug info:")
            print(f"    - EventBus published: {eventbus_stats['events_published']}")
            print(f"    - EventBus filtered: {eventbus_stats['events_filtered']}")
            print(f"    - Relay failures: {final_stats['events_failed']}")

        print("=" * 70)

        await client.disconnect()

    except ImportError:
        print("\n✗ python-socketio not installed for client test")
    except Exception as e:
        print(f"\n✗ Error during test: {e}")

    # Cleanup
    server.stop_sync()
    print("\n[7] Test complete - server stopped")


if __name__ == "__main__":
    asyncio.run(verify_pipeline())
