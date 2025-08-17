#!/usr/bin/env python3
"""
Demo script showing automatic Socket.IO dependency installation.

WHY: This script demonstrates the new automatic dependency installation
feature for the --monitor flag, showing users what to expect.

USAGE: python scripts/demo_monitor_installation.py
"""

import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.core.logger import get_logger
from claude_mpm.utils.dependency_manager import (
    check_dependency,
    check_virtual_environment,
    ensure_socketio_dependencies,
)


def demo_monitor_installation():
    """Demonstrate the automatic installation feature."""
    print("🚀 Claude MPM Monitor Mode - Automatic Dependency Installation Demo")
    print("=" * 70)

    # Show environment info
    is_venv, venv_info = check_virtual_environment()
    print(f"Environment: {venv_info}")
    print()

    # Show what happens when user runs --monitor
    print("💻 When you run: claude-mpm --monitor")
    print("   The system automatically:")
    print()

    print("   1️⃣ Checks for Socket.IO dependencies:")
    print("      🔧 Checking Socket.IO dependencies...")

    # Check current status
    socketio_deps = [
        ("python-socketio", "socketio", "Socket.IO Server"),
        ("aiohttp", "aiohttp", "Async HTTP Client"),
        ("python-engineio", "engineio", "Engine.IO Protocol"),
    ]

    all_present = True
    for package_name, import_name, description in socketio_deps:
        available = check_dependency(package_name, import_name)
        status = "✅" if available else "❌"
        print(f"      {status} {description} ({package_name})")
        if not available:
            all_present = False

    print()

    if all_present:
        print("   2️⃣ All dependencies found:")
        print("      ✅ Socket.IO dependencies ready")
    else:
        print("   2️⃣ Missing dependencies detected:")
        print("      ⚙️  Installing missing Socket.IO dependencies...")
        print("      📦 Running: pip install python-socketio aiohttp python-engineio")
        print("      ✅ Socket.IO dependencies installed and verified")

    print()
    print("   3️⃣ Starts Claude with monitoring:")
    print("      ✅ Socket.IO server enabled at http://localhost:8765")
    print("      🌐 Opening Socket.IO dashboard in browser")
    print("      🎯 Starting Claude session with real-time monitoring")

    print()
    print("🎉 RESULT: Zero manual setup required!")
    print("   Users just run 'claude-mpm --monitor' and everything works.")

    print()
    print("📋 Alternative Installation Methods:")
    print("   • Automatic: claude-mpm --monitor  (installs on-demand)")
    print("   • Manual: pip install python-socketio aiohttp python-engineio")
    print("   • With extras: pip install claude-mpm[monitor]")

    print()
    print("🔧 Technical Details:")
    print(f"   • Virtual Environment: {'Yes' if is_venv else 'No'}")
    print(f"   • Python: {sys.executable}")
    print(f"   • Install Method: subprocess with pip")
    print(f"   • Timeout: 5 minutes per installation")
    print(f"   • Error Handling: Graceful fallback with clear messages")


if __name__ == "__main__":
    demo_monitor_installation()
