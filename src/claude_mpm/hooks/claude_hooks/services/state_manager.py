"""State management service for Claude hook handler.

This service manages:
- Agent delegation tracking
- Git branch caching
- Session state management
- Cleanup of old entries
"""

import os
import subprocess
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import constants for configuration
try:
    from claude_mpm.core.constants import TimeoutConfig
except ImportError:
    # Fallback values if constants module not available
    class TimeoutConfig:
        QUICK_TIMEOUT = 2.0


# Debug mode is enabled by default for better visibility into hook processing
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"


class StateManagerService:
    """Manages state for the Claude hook handler."""

    def __init__(self):
        """Initialize state management service."""
        # Maximum sizes for tracking
        self.MAX_DELEGATION_TRACKING = 200
        self.MAX_PROMPT_TRACKING = 100
        self.MAX_CACHE_AGE_SECONDS = 300
        self.CLEANUP_INTERVAL_EVENTS = 100

        # Agent delegation tracking
        # Store recent Task delegations: session_id -> agent_type
        self.active_delegations = {}
        # Use deque to limit memory usage (keep last 100 delegations)
        self.delegation_history = deque(maxlen=100)
        # Store delegation request data for response correlation: session_id -> request_data
        self.delegation_requests = {}

        # Git branch cache (to avoid repeated subprocess calls)
        self._git_branch_cache = {}
        self._git_branch_cache_time = {}

        # Store current user prompts for comprehensive response tracking
        self.pending_prompts = {}  # session_id -> prompt data

        # Track events for periodic cleanup
        self.events_processed = 0
        self.last_cleanup = time.time()

    def track_delegation(
        self, session_id: str, agent_type: str, request_data: Optional[dict] = None
    ):
        """Track a new agent delegation with optional request data for response correlation."""
        if DEBUG:
            import sys

            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...",
                file=sys.stderr,
            )
            print(f"  - agent_type: {agent_type}", file=sys.stderr)
            print(f"  - request_data provided: {bool(request_data)}", file=sys.stderr)
            print(
                f"  - delegation_requests size before: {len(self.delegation_requests)}",
                file=sys.stderr,
            )

        if session_id and agent_type and agent_type != "unknown":
            self.active_delegations[session_id] = agent_type
            key = f"{session_id}:{datetime.now(timezone.utc).timestamp()}"
            self.delegation_history.append((key, agent_type))

            # Store request data for response tracking correlation
            if request_data:
                self.delegation_requests[session_id] = {
                    "agent_type": agent_type,
                    "request": request_data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                if DEBUG:
                    import sys

                    print(
                        f"  - ✅ Stored in delegation_requests[{session_id[:16]}...]",
                        file=sys.stderr,
                    )
                    print(
                        f"  - delegation_requests size after: {len(self.delegation_requests)}",
                        file=sys.stderr,
                    )

            # Clean up old delegations (older than 5 minutes)
            cutoff_time = datetime.now(timezone.utc).timestamp() - 300
            keys_to_remove = []
            for sid in list(self.active_delegations.keys()):
                # Check if this is an old entry by looking in history
                found_recent = False
                for hist_key, _ in reversed(self.delegation_history):
                    if hist_key.startswith(sid):
                        _, timestamp = hist_key.split(":", 1)
                        if float(timestamp) > cutoff_time:
                            found_recent = True
                            break
                if not found_recent:
                    keys_to_remove.append(sid)

            for key in keys_to_remove:
                if key in self.active_delegations:
                    del self.active_delegations[key]
                if key in self.delegation_requests:
                    del self.delegation_requests[key]

    def get_delegation_agent_type(self, session_id: str) -> str:
        """Get the agent type for a session's active delegation."""
        # First try exact session match
        if session_id and session_id in self.active_delegations:
            return self.active_delegations[session_id]

        # Then try to find in recent history
        if session_id:
            for key, agent_type in reversed(self.delegation_history):
                if key.startswith(session_id):
                    return agent_type

        return "unknown"

    def cleanup_old_entries(self):
        """Clean up old entries to prevent memory growth."""
        datetime.now(timezone.utc).timestamp() - self.MAX_CACHE_AGE_SECONDS

        # Clean up delegation tracking dictionaries
        for storage in [self.active_delegations, self.delegation_requests]:
            if len(storage) > self.MAX_DELEGATION_TRACKING:
                # Keep only the most recent entries
                sorted_keys = sorted(storage.keys())
                excess = len(storage) - self.MAX_DELEGATION_TRACKING
                for key in sorted_keys[:excess]:
                    del storage[key]

        # Clean up pending prompts
        if len(self.pending_prompts) > self.MAX_PROMPT_TRACKING:
            sorted_keys = sorted(self.pending_prompts.keys())
            excess = len(self.pending_prompts) - self.MAX_PROMPT_TRACKING
            for key in sorted_keys[:excess]:
                del self.pending_prompts[key]

        # Clean up git branch cache
        expired_keys = [
            key
            for key, cache_time in self._git_branch_cache_time.items()
            if datetime.now(timezone.utc).timestamp() - cache_time
            > self.MAX_CACHE_AGE_SECONDS
        ]
        for key in expired_keys:
            self._git_branch_cache.pop(key, None)
            self._git_branch_cache_time.pop(key, None)

    def get_git_branch(self, working_dir: Optional[str] = None) -> str:
        """Get git branch for the given directory with caching.

        WHY caching approach:
        - Avoids repeated subprocess calls which are expensive
        - Caches results for 30 seconds per directory
        - Falls back gracefully if git command fails
        - Returns 'Unknown' for non-git directories
        """
        # Use current working directory if not specified
        if not working_dir:
            working_dir = Path.cwd()

        # Check cache first (cache for 30 seconds)
        current_time = datetime.now(timezone.utc).timestamp()
        cache_key = working_dir

        if (
            cache_key in self._git_branch_cache
            and cache_key in self._git_branch_cache_time
            and current_time - self._git_branch_cache_time[cache_key] < 30
        ):
            return self._git_branch_cache[cache_key]

        # Try to get git branch
        try:
            # Change to the working directory temporarily
            original_cwd = Path.cwd()
            os.chdir(working_dir)

            # Run git command to get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=TimeoutConfig.QUICK_TIMEOUT,
                check=False,  # Quick timeout to avoid hanging
            )

            # Restore original directory
            os.chdir(original_cwd)

            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # Cache the result
                self._git_branch_cache[cache_key] = branch
                self._git_branch_cache_time[cache_key] = current_time
                return branch
            # Not a git repository or no branch
            self._git_branch_cache[cache_key] = "Unknown"
            self._git_branch_cache_time[cache_key] = current_time
            return "Unknown"

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
            OSError,
        ):
            # Git not available or command failed
            self._git_branch_cache[cache_key] = "Unknown"
            self._git_branch_cache_time[cache_key] = current_time
            return "Unknown"

    def find_matching_request(self, session_id: str) -> Optional[dict]:
        """Find matching request data for a session, with fuzzy matching fallback."""
        # First try exact match
        request_info = self.delegation_requests.get(session_id)

        # If exact match fails, try partial matching
        if not request_info and session_id:
            if DEBUG:
                import sys

                print(
                    f"  - Trying fuzzy match for session {session_id[:16]}...",
                    file=sys.stderr,
                )
            # Try to find a session that matches the first 8-16 characters
            for stored_sid in list(self.delegation_requests.keys()):
                if (
                    stored_sid.startswith(session_id[:8])
                    or session_id.startswith(stored_sid[:8])
                    or (
                        len(session_id) >= 16
                        and len(stored_sid) >= 16
                        and stored_sid[:16] == session_id[:16]
                    )
                ):
                    if DEBUG:
                        import sys

                        print(
                            f"  - ✅ Fuzzy match found: {stored_sid[:16]}...",
                            file=sys.stderr,
                        )
                    request_info = self.delegation_requests.get(stored_sid)
                    # Update the key to use the current session_id for consistency
                    if request_info:
                        self.delegation_requests[session_id] = request_info
                        # Optionally remove the old key to avoid duplicates
                        if stored_sid != session_id:
                            del self.delegation_requests[stored_sid]
                    break

        return request_info

    def remove_request(self, session_id: str):
        """Remove request data for a session."""
        if session_id in self.delegation_requests:
            del self.delegation_requests[session_id]

    def increment_events_processed(self) -> bool:
        """Increment events processed counter and return True if cleanup is needed."""
        self.events_processed += 1
        return self.events_processed % self.CLEANUP_INTERVAL_EVENTS == 0
