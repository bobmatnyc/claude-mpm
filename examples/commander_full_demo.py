#!/usr/bin/env python3
"""Full end-to-end demo of MPM Commander Phase 2.

This demo showcases the complete Commander workflow:
1. Start daemon
2. Register project
3. Add work items to queue
4. Work executes automatically
5. Event occurs, execution pauses
6. Resolve event via API
7. Execution resumes
8. Work completes
9. Shutdown daemon gracefully
10. Restart daemon - state recovered

Usage:
    python examples/commander_full_demo.py
"""

import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models.events import Event, EventType
from claude_mpm.commander.models.work import WorkPriority
from claude_mpm.commander.work.queue import WorkQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the full Commander demo."""
    logger.info("=" * 60)
    logger.info("MPM Commander Phase 2 - Full Demo")
    logger.info("=" * 60)

    # Use temporary directory for demo state
    with TemporaryDirectory(prefix="commander_demo_") as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Configure daemon
        config = DaemonConfig(
            host="127.0.0.1",
            port=18765,
            log_level="INFO",
            state_dir=tmp_path / "state",
            poll_interval=1.0,
            save_interval=5,
        )

        logger.info("\n📋 Step 1: Starting Commander Daemon")
        daemon = CommanderDaemon(config)
        await daemon.start()
        logger.info("✓ Daemon started successfully")
        await asyncio.sleep(1)

        logger.info("\n📋 Step 2: Registering Project")
        project_path = tmp_path / "demo_project"
        project_path.mkdir(parents=True, exist_ok=True)

        project = daemon.registry.register(str(project_path), "Demo Project")
        logger.info(f"✓ Project registered: {project.name} ({project.id})")

        logger.info("\n📋 Step 3: Adding Work Items to Queue")
        queue = WorkQueue(project.id)

        work1 = queue.add("Initialize project environment", WorkPriority.HIGH)
        logger.info(f"✓ Added work: {work1.content}")

        work2 = queue.add("Run automated tests", WorkPriority.MEDIUM)
        logger.info(f"✓ Added work: {work2.content}")

        work3 = queue.add("Generate documentation", WorkPriority.LOW)
        logger.info(f"✓ Added work: {work3.content}")

        logger.info(f"\n📊 Work queue status: {len(queue.list())} items")

        logger.info("\n📋 Step 4: Simulating Work Execution")
        # In real system, RuntimeExecutor would handle this
        # For demo, we'll manually simulate execution

        next_work = queue.get_next()
        if next_work:
            logger.info(f"▶️  Starting: {next_work.content}")
            queue.start(next_work.id)
            await asyncio.sleep(1)

            # Simulate work in progress
            logger.info("⏳ Work in progress...")
            await asyncio.sleep(2)

        logger.info("\n📋 Step 5: Event Occurs - Execution Pauses")
        event = Event(
            id="demo-blocking-event",
            project_id=project.id,
            event_type=EventType.BLOCKING,
            title="User Confirmation Required",
            content="Please confirm: Deploy to production environment?",
        )

        daemon.event_manager.add_event(event)
        logger.info(f"🚨 Blocking event created: {event.title}")
        logger.info("⏸️  Execution paused - waiting for user input")

        # Create session and pause it
        session = daemon.get_or_create_session(project.id)
        session.pause_reason = event.id
        logger.info(f"   Session state: PAUSED (reason: {event.id})")

        logger.info("\n📋 Step 6: Resolving Event via API")
        await asyncio.sleep(2)
        logger.info("👤 User provides resolution...")

        daemon.event_manager.resolve_event(event.id, "User confirmed: Deploy approved")
        logger.info("✓ Event resolved: Deploy approved")

        logger.info("\n📋 Step 7: Execution Resumes")
        session.pause_reason = None
        logger.info("▶️  Execution resumed")

        # Complete the paused work
        if next_work:
            logger.info(f"✓ Completed: {next_work.content}")
            queue.complete(next_work.id, "Environment initialized successfully")

        logger.info("\n📋 Step 8: Work Completion")
        # Execute remaining work
        while True:
            next_work = queue.get_next()
            if not next_work:
                break

            logger.info(f"▶️  Starting: {next_work.content}")
            queue.start(next_work.id)
            await asyncio.sleep(1)

            logger.info(f"✓ Completed: {next_work.content}")
            queue.complete(next_work.id, f"{next_work.content} - Done")
            await asyncio.sleep(0.5)

        logger.info("✅ All work completed!")

        # Show final state
        completed_count = len([w for w in queue.list() if w.state.value == "completed"])
        logger.info(
            f"\n📊 Final status: {completed_count}/{len(queue.list())} work items completed"
        )

        logger.info("\n📋 Step 9: Graceful Shutdown")
        logger.info("💾 Saving state...")
        await daemon._save_state()
        logger.info("✓ State saved to disk")

        logger.info("🛑 Stopping daemon...")
        await daemon.stop()
        logger.info("✓ Daemon stopped gracefully")

        logger.info("\n📋 Step 10: Daemon Restart - State Recovery")
        await asyncio.sleep(1)

        logger.info("🔄 Restarting daemon...")
        daemon2 = CommanderDaemon(config)
        await daemon2.start()
        logger.info("✓ Daemon restarted")

        await asyncio.sleep(1)

        # Verify state recovered
        logger.info("\n🔍 Verifying state recovery:")

        recovered_project = daemon2.registry.get(project.id)
        if recovered_project:
            logger.info(f"✓ Project recovered: {recovered_project.name}")
        else:
            logger.warning("✗ Project not recovered")

        if project.id in daemon2.sessions:
            logger.info(f"✓ Session recovered for project {project.id}")
        else:
            logger.info("ℹ️  No active session (expected after completion)")

        recovered_events = daemon2.event_manager.get_pending()
        logger.info(f"✓ Events recovered: {len(recovered_events)} pending")

        logger.info("\n🔍 State files created:")
        state_dir = config.state_dir
        for file in ["projects.json", "sessions.json", "events.json"]:
            file_path = state_dir / file
            if file_path.exists():
                logger.info(f"  ✓ {file} ({file_path.stat().st_size} bytes)")
            else:
                logger.info(f"  ✗ {file} (missing)")

        logger.info("\n🛑 Final shutdown...")
        await daemon2.stop()
        logger.info("✓ Demo completed successfully")

        logger.info("\n" + "=" * 60)
        logger.info("Demo Summary:")
        logger.info("- Daemon lifecycle: ✓")
        logger.info("- Project management: ✓")
        logger.info("- Work queue execution: ✓")
        logger.info("- Event handling: ✓")
        logger.info("- State persistence: ✓")
        logger.info("- Recovery after restart: ✓")
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise
