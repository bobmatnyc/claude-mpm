#!/usr/bin/env python3
"""
Check and optionally install monitor dependencies for claude-mpm.

This script checks if the Socket.IO and monitor dependencies are installed,
and provides instructions or automatic installation if needed.
"""

import subprocess
import sys
from importlib import import_module


def check_module(module_name):
    """Check if a module is installed."""
    try:
        import_module(module_name)
        return True
    except ImportError:
        return False


def check_monitor_dependencies():
    """Check if all monitor dependencies are installed."""
    required_modules = {
        "socketio": "python-socketio",
        "aiohttp": "aiohttp",
        "aiohttp_cors": "aiohttp-cors",
        "engineio": "python-engineio",
        "aiofiles": "aiofiles",
        "websockets": "websockets",
    }

    missing = []
    for module, package in required_modules.items():
        if not check_module(module):
            missing.append(package)

    return missing


def install_with_pipx(packages):
    """Install packages using pipx inject."""
    try:
        cmd = ["pipx", "inject", "claude-mpm"] + packages
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing with pipx: {e}")
        return False
    except FileNotFoundError:
        print("pipx not found")
        return False


def install_with_pip(packages):
    """Install packages using pip."""
    try:
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing with pip: {e}")
        return False


def main():
    """Main entry point."""
    print("🔍 Checking claude-mpm monitor dependencies...")

    missing = check_monitor_dependencies()

    if not missing:
        print("✅ All monitor dependencies are installed!")
        print("🚀 You can start the monitor with: claude-mpm --monitor")
        return 0

    print(f"\n⚠️  Missing monitor dependencies: {', '.join(missing)}")

    # Check if we're in a pipx environment
    in_pipx = "pipx" in sys.executable or ".local/pipx" in sys.executable

    if in_pipx:
        print("\n📦 Detected pipx installation")
        print("Installing missing dependencies...")
        if install_with_pipx(missing):
            print("✅ Dependencies installed successfully!")
            print("🚀 You can now start the monitor with: claude-mpm --monitor")
            return 0
        print("\n❌ Automatic installation failed")
        print("Please run manually:")
        print(f"  pipx inject claude-mpm {' '.join(missing)}")
        return 1
    print("\n📦 Installing missing dependencies with pip...")
    if install_with_pip(missing):
        print("✅ Dependencies installed successfully!")
        print("🚀 You can now start the monitor with: claude-mpm --monitor")
        return 0
    print("\n❌ Automatic installation failed")
    print("Please install manually:")
    print(f"  pip install {' '.join(missing)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
