#!/usr/bin/env python3
"""
Ticket Management Wrapper for claude-mpm

WHY: This script provides backward compatibility for users who are accustomed to
using the 'ticket' command directly. It delegates all operations to the integrated
claude-mpm tickets command.

DESIGN DECISION: Rather than duplicating functionality, this thin wrapper translates
the old interface to the new claude-mpm tickets subcommands, ensuring consistency
and maintainability.

Usage:
    ticket create <title> [options]
    ticket list [options]
    ticket view <id>
    ticket update <id> [options]
    ticket close <id>
    ticket delete <id> [options]
    ticket search <query> [options]
    ticket comment <id> <comment>
    ticket workflow <id> <state>
    ticket help

This wrapper delegates to:
    claude-mpm tickets create <title> [options]
    claude-mpm tickets list [options]
    ... etc
"""

import os
# Disable telemetry by default
os.environ['DISABLE_TELEMETRY'] = '1'

import subprocess
import sys
from pathlib import Path


def main():
    """Main entry point that delegates to claude-mpm tickets command."""
    # Build the claude-mpm command
    # Find claude-mpm executable
    claude_mpm = "claude-mpm"

    # Check if we're running from source (development mode)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    if (project_root / "src" / "claude_mpm").exists():
        # Running from source, use the local claude-mpm
        claude_mpm_script = project_root / "claude-mpm"
        if claude_mpm_script.exists():
            claude_mpm = str(claude_mpm_script)

    # Convert ticket command to claude-mpm tickets command
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        # Show help
        cmd = [claude_mpm, "tickets", "--help"]
    else:
        # Pass through all arguments to claude-mpm tickets
        cmd = [claude_mpm, "tickets"] + sys.argv[1:]

    # Execute the command
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print(
            "Error: claude-mpm not found. Please ensure it's installed and in your PATH."
        )
        print("Install with: pip install claude-mpm")
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
