#!/usr/bin/env python3
"""
Standalone dashboard launcher for Claude MPM.

This script provides a way to launch the dashboard independently when needed.
For normal usage, use: claude-mpm run --monitor
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Launch Claude MPM Dashboard")
    parser.add_argument(
        "--port", type=int, default=8765, help="Port for dashboard (default: 8765)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open browser automatically"
    )
    args = parser.parse_args()

    try:
        import asyncio

        from claude_mpm.services.cli.dashboard_launcher import DashboardLauncher
        from claude_mpm.services.socketio_server import SocketIOServer

        print(f"Starting Claude MPM Dashboard on http://{args.host}:{args.port}")

        # Initialize and start server
        server = SocketIOServer(host=args.host, port=args.port)

        async def run_server():
            await server.start()

            if not args.no_browser:
                launcher = DashboardLauncher()
                launcher.open_dashboard(f"http://{args.host}:{args.port}")

            # Keep server running
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                print("\nShutting down dashboard...")
                await server.stop()

        asyncio.run(run_server())

    except ImportError as e:
        print(f"Error: Missing dependencies for dashboard: {e}")
        print("\nTo install required dependencies:")
        print("  pip install claude-mpm[monitor]")
        print("\nOr install manually:")
        print("  pip install python-socketio aiohttp python-engineio")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
