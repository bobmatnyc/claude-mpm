#!/usr/bin/env python3
"""
Start the event aggregator service for activity logging.

This script starts the event aggregator that captures all agent activity
from the Socket.IO dashboard and saves it to .claude-mpm/activity/
"""

import signal
import sys
import time

# Since we're now inside the claude_mpm package, use relative imports
from ..core.config import Config
from ..core.logger import get_logger
from ..services.event_aggregator import EventAggregator

logger = get_logger("activity_logging")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Shutting down activity logging...")
    if aggregator:
        aggregator.stop()
    sys.exit(0)


if __name__ == "__main__":
    # Load configuration
    config = Config()

    # Check if event aggregator is enabled
    if not config.get("event_aggregator.enabled", True):
        logger.warning("Event aggregator is disabled in configuration")
        logger.warning("Enable it by setting event_aggregator.enabled: true")
        sys.exit(1)

    # Get configuration values
    activity_dir = config.get(
        "event_aggregator.activity_directory", ".claude-mpm/activity"
    )
    dashboard_port = config.get("event_aggregator.dashboard_port", 8765)

    logger.info("=" * 60)
    logger.info("Starting Activity Logging Service")
    logger.info("=" * 60)
    logger.info(f"Activity Directory: {activity_dir}")
    logger.info(f"Dashboard Port: {dashboard_port}")
    logger.info("Connecting to Socket.IO dashboard...")

    # Initialize aggregator
    aggregator = EventAggregator(
        host="localhost",
        port=dashboard_port,
        save_dir=None,  # Will use config value
    )

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the aggregator
    try:
        aggregator.start()
        logger.info("✅ Activity logging started successfully!")
        logger.info(f"📁 Saving activity to: {aggregator.save_dir}")
        logger.info("Press Ctrl+C to stop")

        # Keep running and show periodic status
        while aggregator.running:
            time.sleep(30)

            # Show status every 30 seconds
            status = aggregator.get_status()
            if status["active_sessions"] > 0:
                logger.info(
                    f"📊 Status: {status['active_sessions']} active sessions, "
                    f"{status['total_events']} events captured"
                )

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Error running activity logging: {e}")
    finally:
        if aggregator:
            aggregator.stop()
            # Save any remaining sessions
            aggregator._save_all_sessions()
            logger.info("Activity logging stopped")
