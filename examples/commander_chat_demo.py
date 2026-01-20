#!/usr/bin/env python3
"""
Commander Chat Interface Demo

Demonstrates the Commander chat interface components including:
- Framework selection
- Command parsing
- Session management
- Instance interaction

Usage:
    uv run python examples/commander_chat_demo.py
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from claude_mpm.commander.chat.commands import CommandParser
from claude_mpm.commander.chat.repl import CommanderREPL
from claude_mpm.commander.frameworks.base import InstanceInfo
from claude_mpm.commander.frameworks.claude_code import ClaudeCodeFramework
from claude_mpm.commander.frameworks.mpm import MPMFramework
from claude_mpm.commander.instance_manager import InstanceManager
from claude_mpm.commander.session.manager import SessionManager

# Colors for output
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_section(title: str):
    """Print a section header."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


async def demo_framework_selection():
    """Demonstrate framework adapter selection."""
    print_section("Framework Selection Demo")

    # Show available frameworks
    print(f"{GREEN}Available Frameworks:{RESET}")
    print("  • cc (Claude Code) - Official Claude CLI")
    print("  • mpm (Multi-Agent) - MPM orchestration framework")

    # Create frameworks
    cc_framework = ClaudeCodeFramework()
    mpm_framework = MPMFramework()

    print(f"\n{GREEN}Claude Code Framework:{RESET}")
    print(f"  Command: {cc_framework.get_command()}")
    print("  Supports: Interactive coding sessions")

    print(f"\n{GREEN}MPM Framework:{RESET}")
    print(f"  Command: {mpm_framework.get_command()}")
    print("  Supports: Multi-agent orchestration")


async def demo_command_parsing():
    """Demonstrate command parsing."""
    print_section("Command Parser Demo")

    parser = CommandParser()

    # Test various commands
    test_commands = [
        "list",
        "ls",
        "start /path/to/project --framework cc --name myapp",
        "stop myapp",
        "connect backend",
        "disconnect",
        "status",
        "help",
        "This is a regular message to send to the instance",
    ]

    print(f"{GREEN}Parsing Commands:{RESET}\n")

    for cmd in test_commands:
        result = parser.parse(cmd)
        if result.is_command:
            print(f"  {YELLOW}Command:{RESET} {result.command}")
            if result.args:
                print(f"    Args: {result.args}")
        else:
            print(f"  {YELLOW}Message:{RESET} {result.message}")


async def demo_session_management():
    """Demonstrate session context management."""
    print_section("Session Management Demo")

    manager = SessionManager()
    context = manager.context

    print(f"{GREEN}Initial State:{RESET}")
    print(f"  Connected: {context.is_connected}")
    print(f"  Instance: {context.connected_instance}")
    print(f"  Messages: {len(context.messages)}")

    # Connect to instance
    manager.connect_to("demo-app")

    print(f"\n{GREEN}After Connection:{RESET}")
    print(f"  Connected: {context.is_connected}")
    print(f"  Instance: {context.connected_instance}")

    # Add messages
    manager.add_message("First message")
    manager.add_message("Second message")

    print(f"\n{GREEN}After Messages:{RESET}")
    print(f"  Message count: {len(context.messages)}")
    for i, msg in enumerate(context.messages, 1):
        print(f"    {i}. {msg.content} ({msg.timestamp.strftime('%H:%M:%S')})")

    # Disconnect
    manager.disconnect()

    print(f"\n{GREEN}After Disconnect:{RESET}")
    print(f"  Connected: {context.is_connected}")
    print(f"  Instance: {context.connected_instance}")
    print(f"  Messages: {len(context.messages)} (preserved)")


async def demo_instance_interaction():
    """Demonstrate instance interaction workflow."""
    print_section("Instance Interaction Demo")

    # Create mock instance manager
    mock_manager = Mock(spec=InstanceManager)
    mock_manager.list_instances = Mock(return_value=[])
    mock_manager.get_instance = Mock(return_value=None)
    mock_manager.start_instance = AsyncMock()
    mock_manager.stop_instance = AsyncMock()
    mock_manager.send_to_instance = AsyncMock(return_value=True)

    # Create session manager
    session = SessionManager()

    # Create REPL
    repl = CommanderREPL(instance_manager=mock_manager, session_manager=session)

    print(f"{GREEN}Simulating Workflow:{RESET}\n")

    # Step 1: List (empty)
    print("1. List instances")
    await repl._cmd_list([])

    # Step 2: Start instance
    print("\n2. Start instance")
    instance = InstanceInfo(
        name="demo-app",
        project_path=Path("/tmp/demo"),  # nosec B108 - Demo only
        framework="cc",
        tmux_session="mpm-commander",
        pane_target="%1",
        git_branch="main",
        git_status="clean",
    )
    mock_manager.start_instance.return_value = instance
    await repl._cmd_start(
        ["/tmp/demo", "--name", "demo-app", "--framework", "cc"]  # nosec B108 - Demo
    )

    # Step 3: List (with instance)
    print("\n3. List instances (after start)")
    mock_manager.list_instances.return_value = [instance]
    await repl._cmd_list([])

    # Step 4: Connect
    print("\n4. Connect to instance")
    mock_manager.get_instance.return_value = instance
    await repl._cmd_connect(["demo-app"])

    # Step 5: Status
    print("\n5. Check status")
    await repl._cmd_status([])

    # Step 6: Send messages
    print("\n6. Send messages")
    await repl._send_to_instance("Show me the project structure")
    await repl._send_to_instance("Create a new file called test.py")

    print(f"   Messages sent: {len(session.context.messages)}")

    # Step 7: Disconnect
    print("\n7. Disconnect")
    await repl._cmd_disconnect([])

    # Step 8: Stop
    print("\n8. Stop instance")
    await repl._cmd_stop(["demo-app"])


async def demo_multi_instance():
    """Demonstrate managing multiple instances."""
    print_section("Multi-Instance Management Demo")

    # Create mock manager
    mock_manager = Mock(spec=InstanceManager)
    session = SessionManager()
    repl = CommanderREPL(instance_manager=mock_manager, session_manager=session)

    # Create multiple instances
    instances = [
        InstanceInfo(
            name="frontend",
            project_path=Path("/tmp/frontend"),  # nosec B108 - Demo only
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            git_branch="feature/ui",
        ),
        InstanceInfo(
            name="backend",
            project_path=Path("/tmp/backend"),  # nosec B108 - Demo only
            framework="mpm",
            tmux_session="mpm-commander",
            pane_target="%2",
            git_branch="feature/api",
        ),
        InstanceInfo(
            name="mobile",
            project_path=Path("/tmp/mobile"),  # nosec B108 - Demo only
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%3",
            git_branch="main",
        ),
    ]

    mock_manager.list_instances.return_value = instances
    mock_manager.get_instance.side_effect = lambda name: next(
        (inst for inst in instances if inst.name == name), None
    )

    print(f"{GREEN}Simulating Multi-Instance Workflow:{RESET}\n")

    # List all instances
    print("1. List all running instances")
    await repl._cmd_list([])

    # Connect to each instance
    print("\n2. Connect to each instance in sequence")
    for instance in instances:
        print(f"\n   Connecting to {instance.name}...")
        await repl._cmd_connect([instance.name])
        await repl._cmd_status([])

    print(f"\n{GREEN}Final state:{RESET}")
    print(f"  Connected to: {session.context.connected_instance}")
    print(f"  Total instances: {len(instances)}")


async def demo_error_handling():
    """Demonstrate error handling."""
    print_section("Error Handling Demo")

    mock_manager = Mock(spec=InstanceManager)
    mock_manager.get_instance.return_value = None
    mock_manager.list_instances.return_value = []

    session = SessionManager()
    repl = CommanderREPL(instance_manager=mock_manager, session_manager=session)

    print(f"{GREEN}Testing Error Scenarios:{RESET}\n")

    # Try to connect to non-existent instance
    print("1. Connect to non-existent instance")
    await repl._cmd_connect(["nonexistent"])

    # Try to disconnect when not connected
    print("\n2. Disconnect when not connected")
    await repl._cmd_disconnect([])

    # Try to send message when not connected
    print("\n3. Send message when not connected")
    await repl._send_to_instance("This should fail gracefully")

    # Try commands with missing arguments
    print("\n4. Commands with missing arguments")
    await repl._cmd_start([])  # Missing path
    await repl._cmd_stop([])  # Missing name
    await repl._cmd_connect([])  # Missing name

    print(f"\n{GREEN}All errors handled gracefully!{RESET}")


async def main():
    """Run all demos."""
    print(f"\n{GREEN}{'*' * 60}{RESET}")
    print(f"{GREEN}Commander Chat Interface Demo{RESET}")
    print(f"{GREEN}{'*' * 60}{RESET}")

    demos = [
        ("Framework Selection", demo_framework_selection),
        ("Command Parsing", demo_command_parsing),
        ("Session Management", demo_session_management),
        ("Instance Interaction", demo_instance_interaction),
        ("Multi-Instance Management", demo_multi_instance),
        ("Error Handling", demo_error_handling),
    ]

    for name, demo_func in demos:
        try:
            await demo_func()
        except Exception as e:
            print(f"\n{YELLOW}Demo '{name}' error: {e}{RESET}")

    print_section("Demo Complete")
    print(f"{GREEN}All Commander chat components demonstrated successfully!{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
