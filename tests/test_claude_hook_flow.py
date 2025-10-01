#!/usr/bin/env python3
"""Test Claude hook event flow with CORRECT format.

This script tests the complete event flow from Claude hooks through to the dashboard
using the CORRECT event format that Claude actually sends.

CRITICAL: Claude sends events with `hook_event_name` field, NOT `event` or `type` field!
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

try:
    import aiohttp
except ImportError:
    print("Please install required packages: pip install aiohttp")
    sys.exit(1)


class ClaudeEventTester:
    """Test Claude hook events with proper format."""

    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        self.events_sent = 0
        self.events_failed = 0

    def create_claude_event(self, event_name: str, **kwargs) -> Dict[str, Any]:
        """Create a properly formatted Claude event.

        This matches the EXACT format that Claude sends to the hook handler.
        The key field is `hook_event_name`, NOT `event` or `type`.
        """
        base_event = {
            "hook_event_name": event_name,  # THIS IS THE CRITICAL FIELD!
            "hook_event_type": event_name,  # Also included by Claude
            "sessionId": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hook_run_id": f"run-{uuid.uuid4().hex[:8]}",
        }

        # Add event-specific data based on type
        if event_name == "UserPromptSubmit":
            base_event["hook_input_data"] = {
                "prompt": kwargs.get("prompt", "Test prompt from automated test"),
                "prompt_preview": kwargs.get(
                    "prompt", "Test prompt from automated test"
                )[:50],
            }

        elif event_name == "PreToolUse":
            tool_name = kwargs.get("tool_name", "Bash")
            base_event["hook_input_data"] = {
                "tool_name": tool_name,
                "params": kwargs.get("params", {"command": "ls -la"}),
                "tool_id": f"tool-{uuid.uuid4().hex[:8]}",
            }
            # Special handling for Task tool (delegation)
            if tool_name == "Task":
                base_event["hook_input_data"]["delegation_details"] = {
                    "agent_type": kwargs.get("agent_type", "engineer"),
                    "task_description": kwargs.get("task", "Implement feature X"),
                }

        elif event_name == "PostToolUse":
            base_event["hook_input_data"] = {
                "tool_name": kwargs.get("tool_name", "Bash"),
                "tool_id": kwargs.get("tool_id", f"tool-{uuid.uuid4().hex[:8]}"),
                "success": kwargs.get("success", True),
                "result": kwargs.get("result", "Command executed successfully"),
                "error": kwargs.get("error"),
            }

        elif event_name == "Stop":
            base_event["hook_input_data"] = {
                "reason": kwargs.get("reason", "task_completed"),
                "final_message": kwargs.get("message", "Task completed successfully"),
            }

        elif event_name == "SubagentStop":
            base_event["hook_input_data"] = {
                "agent_type": kwargs.get("agent_type", "engineer"),
                "subagent_type": kwargs.get("agent_type", "engineer"),  # Both fields
                "reason": kwargs.get("reason", "task_completed"),
                "result": kwargs.get("result", "Subagent task completed"),
            }
            # Also add at top level for compatibility
            base_event["agent_type"] = kwargs.get("agent_type", "engineer")
            base_event["subagent_type"] = kwargs.get("agent_type", "engineer")

        elif event_name == "AssistantResponse":
            base_event["hook_input_data"] = {
                "message": kwargs.get("message", "This is an assistant response"),
                "content_type": "text",
            }

        # Add any additional kwargs that weren't handled
        for key, value in kwargs.items():
            if key not in [
                "prompt",
                "tool_name",
                "params",
                "success",
                "result",
                "error",
                "reason",
                "message",
                "agent_type",
                "task",
            ]:
                base_event[key] = value

        return base_event

    async def send_event(self, event: Dict[str, Any]) -> bool:
        """Send event to the dashboard HTTP endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/events",
                    json=event,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 204:
                        self.events_sent += 1
                        print(
                            f"✅ Sent {event['hook_event_name']} event (#{self.events_sent})"
                        )
                        return True
                    self.events_failed += 1
                    text = await response.text()
                    print(
                        f"❌ Failed to send {event['hook_event_name']}: {response.status} - {text}"
                    )
                    return False
        except Exception as e:
            self.events_failed += 1
            print(f"❌ Error sending event: {e}")
            return False

    async def test_basic_flow(self):
        """Test a basic Claude interaction flow."""
        print("\n" + "=" * 60)
        print("Testing Basic Claude Event Flow")
        print("=" * 60)

        # 1. User submits a prompt
        event = self.create_claude_event(
            "UserPromptSubmit", prompt="Help me create a Python function"
        )
        await self.send_event(event)
        await asyncio.sleep(0.5)

        # 2. Claude uses a tool (Read)
        event = self.create_claude_event(
            "PreToolUse", tool_name="Read", params={"file_path": "/test/file.py"}
        )
        await self.send_event(event)
        await asyncio.sleep(0.3)

        event = self.create_claude_event(
            "PostToolUse",
            tool_name="Read",
            success=True,
            result="File contents here...",
        )
        await self.send_event(event)
        await asyncio.sleep(0.5)

        # 3. Claude uses another tool (Edit)
        event = self.create_claude_event(
            "PreToolUse",
            tool_name="Edit",
            params={
                "file_path": "/test/file.py",
                "old_string": "def old()",
                "new_string": "def new()",
            },
        )
        await self.send_event(event)
        await asyncio.sleep(0.3)

        event = self.create_claude_event("PostToolUse", tool_name="Edit", success=True)
        await self.send_event(event)
        await asyncio.sleep(0.5)

        # 4. Claude completes the task
        event = self.create_claude_event(
            "Stop", reason="task_completed", message="Function created successfully"
        )
        await self.send_event(event)

    async def test_delegation_flow(self):
        """Test Claude delegating to a subagent."""
        print("\n" + "=" * 60)
        print("Testing Delegation Flow (PM → Engineer Agent)")
        print("=" * 60)

        # 1. User asks PM to delegate
        event = self.create_claude_event(
            "UserPromptSubmit", prompt="Implement a new feature for user authentication"
        )
        await self.send_event(event)
        await asyncio.sleep(0.5)

        # 2. PM delegates to Engineer agent using Task tool
        event = self.create_claude_event(
            "PreToolUse",
            tool_name="Task",
            agent_type="engineer",
            task="Implement user authentication feature",
        )
        await self.send_event(event)
        await asyncio.sleep(0.5)

        # 3. Subagent starts (implicit from Task tool)
        # This would normally be generated by the framework

        # 4. Engineer agent works (simulated)
        event = self.create_claude_event(
            "PreToolUse",
            tool_name="Write",
            params={"file_path": "/src/auth.py", "content": "# Auth module"},
        )
        # Mark as from subagent
        event["agent_type"] = "engineer"
        event["subagent_type"] = "engineer"
        await self.send_event(event)
        await asyncio.sleep(0.3)

        event = self.create_claude_event("PostToolUse", tool_name="Write", success=True)
        event["agent_type"] = "engineer"
        event["subagent_type"] = "engineer"
        await self.send_event(event)
        await asyncio.sleep(0.5)

        # 5. Subagent completes
        event = self.create_claude_event(
            "SubagentStop",
            agent_type="engineer",
            reason="task_completed",
            result="Authentication feature implemented",
        )
        await self.send_event(event)
        await asyncio.sleep(0.5)

        # 6. PM completes after receiving subagent result
        event = self.create_claude_event(
            "PostToolUse",
            tool_name="Task",
            success=True,
            result="Engineer agent completed: Authentication feature implemented",
        )
        await self.send_event(event)
        await asyncio.sleep(0.5)

        event = self.create_claude_event(
            "Stop",
            reason="task_completed",
            message="Feature implemented successfully by Engineer agent",
        )
        await self.send_event(event)

    async def test_all_event_types(self):
        """Test all major event types with correct format."""
        print("\n" + "=" * 60)
        print("Testing All Event Types")
        print("=" * 60)

        event_types = [
            ("UserPromptSubmit", {"prompt": "Test all events"}),
            ("PreToolUse", {"tool_name": "Bash", "params": {"command": "echo test"}}),
            ("PostToolUse", {"tool_name": "Bash", "success": True}),
            ("AssistantResponse", {"message": "Here's my response"}),
            ("SubagentStop", {"agent_type": "research", "reason": "completed"}),
            ("Stop", {"reason": "all_tests_complete"}),
        ]

        for event_name, kwargs in event_types:
            event = self.create_claude_event(event_name, **kwargs)
            await self.send_event(event)
            await asyncio.sleep(0.3)

    async def run_all_tests(self):
        """Run all test scenarios."""
        print("=" * 60)
        print("Claude Hook Event Flow Tester")
        print("=" * 60)
        print(f"Target: {self.base_url}")
        print(f"Session ID: {self.session_id}")
        print("=" * 60)

        # Check dashboard health
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Dashboard is healthy: {data}")
                    else:
                        print(f"⚠️ Dashboard health check returned {response.status}")
        except Exception as e:
            print(f"❌ Cannot connect to dashboard: {e}")
            print("\nMake sure the dashboard is running:")
            print("  mpm dashboard start")
            return

        # Run test scenarios
        await self.test_basic_flow()
        await asyncio.sleep(1)

        await self.test_delegation_flow()
        await asyncio.sleep(1)

        await self.test_all_event_types()

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Events sent: {self.events_sent}")
        print(f"Events failed: {self.events_failed}")
        print(
            f"Success rate: {(self.events_sent / max(self.events_sent + self.events_failed, 1)) * 100:.1f}%"
        )
        print(
            "\n✨ Test complete! Check the dashboard monitor to verify events were received."
        )


async def main():
    """Main entry point."""
    tester = ClaudeEventTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("\n🔧 Claude Hook Event Flow Tester")
    print(
        "This script sends properly formatted events that match Claude's actual format.\n"
    )
    asyncio.run(main())
