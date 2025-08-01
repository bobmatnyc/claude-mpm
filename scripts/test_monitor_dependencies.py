#!/usr/bin/env python3
"""
Quick test for --monitor dependency installation.

WHY: This script tests just the dependency checking part of --monitor
without running the full Claude session.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.utils.dependency_manager import ensure_socketio_dependencies
from claude_mpm.core.logger import get_logger


def simulate_monitor_mode():
    """Simulate the dependency checking that happens in --monitor mode."""
    logger = get_logger("test_monitor")
    
    print("🔧 Checking Socket.IO dependencies...")
    dependencies_ok, error_msg = ensure_socketio_dependencies(logger)
    
    if not dependencies_ok:
        print(f"❌ Failed to install Socket.IO dependencies: {error_msg}")
        print("  Please install manually: pip install python-socketio aiohttp python-engineio")
        print("  Or install with extras: pip install claude-mpm[monitor]")
        return False
    else:
        print("✓ Socket.IO dependencies ready")
    
    try:
        import socketio
        print(f"✓ Socket.IO server can be enabled")
        return True
    except ImportError as e:
        print(f"⚠️  Socket.IO still not available after installation attempt: {e}")
        print("  This might be a virtual environment issue.")
        print("  Try: pip install python-socketio aiohttp python-engineio")
        print("  Or: pip install claude-mpm[monitor]")
        return False


if __name__ == "__main__":
    print("Testing --monitor dependency installation flow...")
    print("=" * 50)
    success = simulate_monitor_mode()
    print("=" * 50)
    if success:
        print("🎉 Monitor mode dependency checking: SUCCESS")
        print("The --monitor flag should work seamlessly!")
    else:
        print("❌ Monitor mode dependency checking: FAILED")
        print("Users will see installation instructions.")
    
    sys.exit(0 if success else 1)