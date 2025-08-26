#!/usr/bin/env python3
"""Analyze agent-related events from Socket.IO server."""

import asyncio
import json
from datetime import datetime

import socketio

# Track agent events
agent_events = []


async def main():
    sio = socketio.AsyncClient()

    @sio.on("connect")
    async def on_connect():
        print("✅ Connected to Socket.IO server")
        print("📊 Monitoring for agent-related events...\n")

    @sio.on("claude_event")
    async def on_event(data):
        event_type = data.get("type", "")

        # Check if this is an agent-related event
        is_agent_event = False
        agent_info = {}

        # Check for Task tool usage (agent delegation)
        if (
            event_type == "hook.pre_tool"
            and data.get("data", {}).get("tool_name") == "Task"
        ):
            is_agent_event = True
            event_data = data.get("data", {})
            agent_info = {
                "event": "Agent Delegation",
                "agent_type": event_data.get("tool_parameters", {}).get(
                    "subagent_type", "unknown"
                ),
                "description": event_data.get("tool_parameters", {}).get(
                    "description", ""
                ),
                "prompt_preview": event_data.get("tool_parameters", {}).get(
                    "prompt_preview", ""
                ),
                "delegation_details": event_data.get("delegation_details", {}),
            }

        # Check for agent completion
        elif event_type == "hook.subagent_stop":
            is_agent_event = True
            event_data = data.get("data", {})
            agent_info = {
                "event": "Agent Completed",
                "agent_type": event_data.get("agent_type", "unknown"),
                "agent_id": event_data.get("agent_id", ""),
                "reason": event_data.get("reason", ""),
                "successful": event_data.get("is_successful_completion", False),
            }

        # Check for agent.delegation events
        elif event_type == "agent.delegation":
            is_agent_event = True
            event_data = data.get("data", {})
            agent_info = {
                "event": "Agent Status",
                "agent": event_data.get("agent", "unknown"),
                "task": event_data.get("task", ""),
                "status": event_data.get("status", ""),
            }

        if is_agent_event:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 🤖 {agent_info['event']}:")
            for key, value in agent_info.items():
                if key != "event" and value:
                    print(f"   {key}: {value}")
            print()

            agent_events.append(
                {
                    "timestamp": timestamp,
                    "type": event_type,
                    "info": agent_info,
                    "raw_data": data,
                }
            )

    # Connect to server
    try:
        await sio.connect("http://localhost:8765")

        # Request history to see past events
        await sio.emit("get_history", {"limit": 500})

        print("\n🔍 Waiting for agent events...")
        print("💡 To generate agent events, use prompts like:")
        print('   - "Use the research agent to analyze this code"')
        print('   - "Ask the pm agent to create a project plan"')
        print('   - "Have the engineer agent optimize this function"')
        print("\nPress Ctrl+C to stop and see summary...\n")

        # Keep connection alive
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n\n📊 AGENT EVENT SUMMARY")
        print("=" * 50)

        if not agent_events:
            print("No agent events detected.")
            print("\nPossible reasons:")
            print("1. No agent delegations were triggered")
            print("2. Hook events are not being emitted properly")
            print("3. The Task tool parameters are not being captured")
        else:
            print(f"Total agent events: {len(agent_events)}")

            # Group by event type
            by_type = {}
            for event in agent_events:
                event_type = event["info"]["event"]
                if event_type not in by_type:
                    by_type[event_type] = []
                by_type[event_type].append(event)

            for event_type, events in by_type.items():
                print(f"\n{event_type}: {len(events)} events")
                for event in events[:3]:  # Show first 3
                    print(
                        f"  - {event['timestamp']}: {event['info'].get('agent_type', 'unknown')}"
                    )

        # Save events for analysis
        with open("agent_events_analysis.json", "w") as f:
            json.dump(agent_events, f, indent=2, default=str)
        print("\n💾 Full event data saved to: agent_events_analysis.json")

    finally:
        await sio.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
