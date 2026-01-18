"""Commander command handler for CLI."""

import asyncio
import logging
import threading
import time

logger = logging.getLogger(__name__)


def handle_commander_command(args) -> int:
    """Handle the commander command with auto-starting daemon.

    Args:
        args: Parsed command line arguments with:
            - port: Port for daemon (default: 8765)
            - host: Host for daemon (default: 127.0.0.1)
            - state_dir: Optional state directory path
            - debug: Enable debug logging
            - no_chat: Start daemon only without interactive chat
            - daemon_only: Alias for no_chat

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Import here to avoid circular dependencies
        import requests

        from claude_mpm.commander.chat.cli import run_commander
        from claude_mpm.commander.config import DaemonConfig
        from claude_mpm.commander.daemon import main as daemon_main

        # Setup debug logging if requested
        if getattr(args, "debug", False):
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        # Get arguments
        port = getattr(args, "port", 8765)
        host = getattr(args, "host", "127.0.0.1")
        state_dir = getattr(args, "state_dir", None)
        no_chat = getattr(args, "no_chat", False) or getattr(args, "daemon_only", False)

        # Check if daemon already running
        daemon_running = False
        try:
            resp = requests.get(f"http://{host}:{port}/api/health", timeout=1)
            if resp.status_code == 200:
                print(f"✓ Commander daemon already running on {host}:{port}")
                daemon_running = True
        except (requests.RequestException, requests.ConnectionError):
            pass

        # Start daemon if not running
        if not daemon_running:
            print(f"Starting Commander daemon on {host}:{port}...")

            # Create daemon config
            config_kwargs = {"host": host, "port": port}
            if state_dir:
                config_kwargs["state_dir"] = state_dir
            config = DaemonConfig(**config_kwargs)

            # Start daemon in background thread
            daemon_thread = threading.Thread(
                target=lambda: asyncio.run(daemon_main(config)), daemon=True
            )
            daemon_thread.start()

            # Wait for daemon to be ready (max 3 seconds)
            for _ in range(30):
                time.sleep(0.1)
                try:
                    resp = requests.get(f"http://{host}:{port}/api/health", timeout=1)
                    if resp.status_code == 200:
                        print("✓ Commander daemon started")
                        daemon_running = True
                        break
                except (requests.RequestException, requests.ConnectionError):
                    pass
            else:
                print("✗ Failed to start daemon (timeout)")
                return 1

        # If daemon-only mode, keep running until interrupted
        if no_chat:
            print(f"\nDaemon running. API at http://{host}:{port}")
            print("Press Ctrl+C to stop\n")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                return 0

        # Launch interactive chat
        print("\nLaunching Commander chat interface...\n")
        asyncio.run(run_commander(port=port, state_dir=state_dir))

        return 0

    except KeyboardInterrupt:
        logger.info("Commander interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Commander error: {e}", exc_info=True)
        return 1
