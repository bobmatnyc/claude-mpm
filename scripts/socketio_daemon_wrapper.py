#!/usr/bin/env python3
"""
Wrapper script to use the hardened daemon by default while maintaining compatibility.

WHY: Provides a smooth transition path from the original daemon to the hardened version
without breaking existing workflows or scripts.
"""

import os
import sys
import subprocess
from pathlib import Path

# Determine which daemon to use
USE_HARDENED = os.environ.get('SOCKETIO_USE_HARDENED', 'true').lower() == 'true'

# Find the appropriate daemon script
script_dir = Path(__file__).parent.parent / "src" / "claude_mpm" / "scripts"

if USE_HARDENED:
    daemon_script = script_dir / "socketio_daemon_hardened.py"
    if not daemon_script.exists():
        # Fall back to original if hardened doesn't exist
        daemon_script = script_dir / "socketio_daemon.py"
    else:
        print("Using hardened Socket.IO daemon for improved reliability")
else:
    daemon_script = script_dir / "socketio_daemon.py"
    print("Using original Socket.IO daemon (set SOCKETIO_USE_HARDENED=true for hardened version)")

# Pass through all arguments to the selected daemon
if daemon_script.exists():
    result = subprocess.run([sys.executable, str(daemon_script)] + sys.argv[1:])
    sys.exit(result.returncode)
else:
    print(f"Error: Daemon script not found at {daemon_script}")
    sys.exit(1)