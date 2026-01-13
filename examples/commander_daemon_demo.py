#!/usr/bin/env python
"""Demo script for Commander daemon.

This script demonstrates how to:
1. Initialize and start the Commander daemon
2. Register a project
3. Create a project session
4. Manage session lifecycle (start, pause, resume, stop)

Usage:
    python examples/commander_daemon_demo.py
"""

import asyncio
import tempfile
from pathlib import Path

from claude_mpm.commander import (
    CommanderDaemon,
    DaemonConfig,
)


async def demo_project_session():
    """Demonstrate ProjectSession lifecycle."""
    print("=" * 60)
    print("Demo: ProjectSession Lifecycle")
    print("=" * 60)
    print()

    # Create temporary project directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir) / "test-project"
        project_path.mkdir()

        print(f"Created test project: {project_path}")
        print()

        # Create daemon with test config
        config = DaemonConfig(
            port=18765,  # Use test port
            log_level="INFO",
            state_dir=Path(tmp_dir) / "commander",
        )

        daemon = CommanderDaemon(config)
        print(f"Created daemon (port={config.port})")
        print()

        # Register project
        project = daemon.registry.register(str(project_path), "Test Project")
        print(f"Registered project: {project.name} (id={project.id})")
        print()

        # Create session
        session = daemon.get_or_create_session(project.id)
        print(f"Created session for project {project.id}")
        print(f"  Initial state: {session.state}")
        print()

        # Start session
        print("Starting session...")
        await session.start()
        print(f"  State after start: {session.state}")
        print(f"  Is ready: {session.is_ready()}")
        print(f"  Can accept work: {session.can_accept_work()}")
        print()

        # Pause session
        print("Pausing session (simulating blocking event)...")
        await session.pause("Waiting for user approval")
        print(f"  State after pause: {session.state}")
        print(f"  Pause reason: {session.pause_reason}")
        print(f"  Is ready: {session.is_ready()}")
        print()

        # Resume session
        print("Resuming session (event resolved)...")
        await session.resume()
        print(f"  State after resume: {session.state}")
        print(f"  Pause reason: {session.pause_reason}")
        print(f"  Is ready: {session.is_ready()}")
        print()

        # Stop session
        print("Stopping session...")
        await session.stop()
        print(f"  State after stop: {session.state}")
        print()

        print("Demo complete!")


async def demo_daemon_lifecycle():
    """Demonstrate daemon startup and shutdown (without actually starting)."""
    print("=" * 60)
    print("Demo: Daemon Lifecycle (Simulated)")
    print("=" * 60)
    print()

    with tempfile.TemporaryDirectory() as tmp_dir:
        config = DaemonConfig(
            port=18765,
            log_level="INFO",
            state_dir=Path(tmp_dir) / "commander",
        )

        daemon = CommanderDaemon(config)
        print("Created daemon:")
        print(f"  Host: {config.host}")
        print(f"  Port: {config.port}")
        print(f"  State dir: {config.state_dir}")
        print(f"  Max projects: {config.max_projects}")
        print()

        print("Initial state:")
        print(f"  Running: {daemon.is_running}")
        print(f"  Registered projects: {len(daemon.registry.list_all())}")
        print(f"  Active sessions: {len(daemon.sessions)}")
        print()

        print("Demo complete!")
        print()
        print("To actually run the daemon:")
        print("  python -m claude_mpm.commander.daemon")
        print("Or:")
        print("  claude-mpm commander start")


async def main():
    """Run all demos."""
    await demo_project_session()
    print()
    await demo_daemon_lifecycle()


if __name__ == "__main__":
    asyncio.run(main())
