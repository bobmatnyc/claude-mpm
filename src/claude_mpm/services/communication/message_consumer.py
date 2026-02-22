#!/usr/bin/env python3
"""
Huey consumer for processing the message queue.

This script runs the Huey consumer to process messages in the background.
It should be started as a daemon or system service in production.

Usage:
    python -m claude_mpm.services.communication.message_consumer
"""

import argparse
import logging
import signal
import sys

from huey.consumer import Consumer

from ...core.logging_utils import get_logger
from .message_bus import MessageBus

logger = get_logger(__name__)


class MessageConsumer:
    """Manages the Huey consumer for message processing."""

    def __init__(self, workers: int = 2, quiet: bool = False):
        """
        Initialize the message consumer.

        Args:
            workers: Number of worker threads
            quiet: Suppress output if True
        """
        self.workers = workers
        self.quiet = quiet
        self.bus = MessageBus()
        self.consumer = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        if self.consumer:
            self.consumer.stop()
        sys.exit(0)

    def run(self):
        """Start the consumer and process messages."""
        try:
            # Configure logging
            if not self.quiet:
                logging.basicConfig(
                    level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                )

            logger.info(f"Starting message consumer with {self.workers} workers")
            logger.info("Queue database: ~/.claude-mpm/message_queue.db")
            logger.info("Press Ctrl+C to stop")

            # Create and run consumer
            self.consumer = Consumer(
                self.bus.huey,
                workers=self.workers,
                periodic=True,  # Enable periodic tasks
                initial_delay=0.1,  # Small delay before starting
                backoff=1.15,  # Exponential backoff multiplier
                max_delay=10.0,  # Max delay between retries
                scheduler_interval=1,  # Check schedule every second
                worker_type="thread",  # Use threads (default)
            )

            # Run the consumer (blocks until stopped)
            self.consumer.run()

        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except Exception as e:
            logger.error(f"Consumer error: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point for the message consumer."""
    parser = argparse.ArgumentParser(
        description="Run the Claude MPM message queue consumer"
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=2,
        help="Number of worker threads (default: 2)",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress output")
    parser.add_argument(
        "-d",
        "--daemon",
        action="store_true",
        help="Run as daemon (detach from terminal)",
    )

    args = parser.parse_args()

    if args.daemon:
        # Daemonize the process
        import os

        # Fork and detach
        if os.fork() > 0:
            sys.exit(0)

        os.setsid()

        if os.fork() > 0:
            sys.exit(0)

        # Redirect stdio to /dev/null
        with open("/dev/null") as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())
        with open("/dev/null", "a+") as devnull:
            os.dup2(devnull.fileno(), sys.stdout.fileno())
            os.dup2(devnull.fileno(), sys.stderr.fileno())

    # Run the consumer
    consumer = MessageConsumer(workers=args.workers, quiet=args.quiet)
    consumer.run()


if __name__ == "__main__":
    main()
