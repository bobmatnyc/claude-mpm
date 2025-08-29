#!/usr/bin/env python3
"""
Wrapper script to use the hardened daemon by default while maintaining compatibility.

WHY: Provides a smooth transition path from the original daemon to the hardened version
without breaking existing workflows or scripts.
"""

import os
import subprocess
import sys
from pathlib import Path

# Determine which daemon to use
USE_HARDENED = os.environ.get("SOCKETIO_USE_HARDENED", "true").lower() == "true"

# Find the appropriate daemon script using proper resource resolution
try:
    # Try using importlib.resources for proper package resource access
    try:
        from importlib import resources

        # We're in the same package, so try direct import
        import claude_mpm.scripts

        scripts_package = claude_mpm.scripts

        if USE_HARDENED:
            try:
                with resources.path(
                    scripts_package, "socketio_daemon_hardened.py"
                ) as p:
                    daemon_script = p
                print("Using hardened Socket.IO daemon for improved reliability")
            except (FileNotFoundError, ModuleNotFoundError):
                # Fall back to original if hardened doesn't exist
                with resources.path(scripts_package, "socketio_daemon.py") as p:
                    daemon_script = p
        else:
            with resources.path(scripts_package, "socketio_daemon.py") as p:
                daemon_script = p
            print(
                "Using original Socket.IO daemon (set SOCKETIO_USE_HARDENED=true for hardened version)"
            )
    except (ImportError, AttributeError, ModuleNotFoundError):
        # Fallback for older Python versions or if resources not available
        script_dir = Path(__file__).parent

        if USE_HARDENED:
            daemon_script = script_dir / "socketio_daemon_hardened.py"
            if not daemon_script.exists():
                # Fall back to original if hardened doesn't exist
                daemon_script = script_dir / "socketio_daemon.py"
            else:
                print("Using hardened Socket.IO daemon for improved reliability")
        else:
            daemon_script = script_dir / "socketio_daemon.py"
            print(
                "Using original Socket.IO daemon (set SOCKETIO_USE_HARDENED=true for hardened version)"
            )
except Exception:
    # Ultimate fallback - try relative to current file
    script_dir = Path(__file__).parent
    daemon_script = script_dir / (
        "socketio_daemon_hardened.py" if USE_HARDENED else "socketio_daemon.py"
    )
    if not daemon_script.exists():
        daemon_script = script_dir / "socketio_daemon.py"

# Pass through all arguments to the selected daemon
if daemon_script.exists():
    result = subprocess.run(
        [sys.executable, str(daemon_script)] + sys.argv[1:], check=False
    )
    sys.exit(result.returncode)
else:
    print(f"Error: Daemon script not found at {daemon_script}")
    sys.exit(1)
