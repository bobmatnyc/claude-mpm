#!/usr/bin/env python3
"""
Standalone dashboard launcher for Claude MPM.

Provides a programmatic and CLI entry point for launching the dashboard
independently when needed. For normal usage, prefer: claude-mpm run --monitor
"""

import argparse
import sys


def main() -> None:
    """Launch the Claude MPM Dashboard."""
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
        import webbrowser

        from claude_mpm.services.socketio.server.main import SocketIOServer

        print(f"Starting Claude MPM Dashboard on http://{args.host}:{args.port}")

        server = SocketIOServer(host=args.host, port=args.port)

        if not args.no_browser:
            url = f"http://{args.host}:{args.port}"
            webbrowser.open(url)

        server.start_sync()

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
