#!/usr/bin/env python3
"""
Standalone dashboard launcher for claude-mpm.

This script can be used to start the dashboard server across different
installation methods (direct, pip, pipx, homebrew, npm).

Usage:
    python scripts/start-dashboard.py [--host HOST] [--port PORT] [--debug]
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to Python path for development installs
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

try:
    from claude_mpm.services.dashboard.stable_server import StableDashboardServer
except ImportError as e:
    print(f"❌ Error importing claude-mpm: {e}")
    print("Please ensure Claude MPM is properly installed:")
    print("  pip install claude-mpm")
    print("  # or")
    print("  pipx install claude-mpm")
    print("  # or")
    print("  brew install claude-mpm")
    print("  # or")
    print("  npm install -g claude-mpm")
    sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Start Claude MPM Dashboard Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to (default: 8765)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    print("🚀 Claude MPM Dashboard Server")
    print(f"📍 Starting on http://{args.host}:{args.port}")
    
    server = StableDashboardServer(host=args.host, port=args.port, debug=args.debug)
    
    try:
        success = server.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
