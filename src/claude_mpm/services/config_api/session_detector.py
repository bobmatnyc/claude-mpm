"""Active Claude Code session detection.

Detects running Claude Code processes via ps aux to warn users
before performing operations that might conflict with an active session.

Fails open: any error returns an empty list rather than blocking operations.
"""

import subprocess  # nosec B404
from typing import Dict, List

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)

# Process name patterns that indicate an active Claude Code session
CLAUDE_PATTERNS = ("claude", "claude-code", "claude_code")


def detect_active_claude_sessions() -> List[Dict[str, str]]:
    """Check for running Claude Code processes.

    Scans the process table via ``ps aux`` and filters for claude-related
    process names. Excludes the grep process itself from results.

    Returns:
        List of dicts with "pid" and "command" keys for each detected session.
        Returns empty list on any error (fail-open design).
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            ["ps", "aux"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug("ps aux returned non-zero exit code: %d", result.returncode)
            return []

        sessions: List[Dict[str, str]] = []

        for line in result.stdout.splitlines():
            # Skip header line
            if line.startswith("USER"):
                continue

            lower_line = line.lower()

            # Check if line matches any claude pattern
            if not any(pattern in lower_line for pattern in CLAUDE_PATTERNS):
                continue

            # Exclude grep itself from results
            if "grep" in lower_line:
                continue

            # Exclude this detection process
            if "session_detector" in lower_line:
                continue

            # Parse ps aux output: USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND
            parts = line.split(None, 10)
            if len(parts) >= 11:
                sessions.append(
                    {
                        "pid": parts[1],
                        "command": parts[10],
                    }
                )
            elif len(parts) >= 2:
                sessions.append(
                    {
                        "pid": parts[1],
                        "command": line,
                    }
                )

        if sessions:
            logger.info("Detected %d active Claude session(s)", len(sessions))
        else:
            logger.debug("No active Claude sessions detected")

        return sessions

    except subprocess.TimeoutExpired:
        logger.debug("ps aux timed out, failing open")
        return []
    except FileNotFoundError:
        logger.debug("ps command not found, failing open")
        return []
    except Exception as e:
        logger.debug("Session detection failed (fail-open): %s", e)
        return []
