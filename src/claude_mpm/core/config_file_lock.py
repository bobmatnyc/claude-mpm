"""Advisory file locking for configuration file mutations.

Uses fcntl.flock() for POSIX advisory locking. This prevents concurrent
writes from CLI + UI, multiple browser tabs, or external tools.

Design decisions:
- POSIX advisory locks (fcntl.flock), not mandatory locks
- Separate .lock file (not locking the config file itself)
- 5-second timeout with non-blocking retry loop
- Context manager pattern for exception-safe usage
- Per-file granularity (lock agent_sources.yaml independently from skill_sources.yaml)

Limitations:
- POSIX-only (macOS, Linux). Not Windows-compatible.
- Advisory locks require all writers to cooperate (CLI must also use this)
- NFS file systems may not support flock reliably
"""

import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


class ConfigFileLockError(Exception):
    """Raised when a config file lock cannot be acquired."""


class ConfigFileLockTimeout(ConfigFileLockError):
    """Raised when lock acquisition times out."""


@contextmanager
def config_file_lock(
    config_path: Path,
    timeout: float = 5.0,
    poll_interval: float = 0.1,
) -> Generator[None, None, None]:
    """Acquire an advisory file lock on a configuration file.

    Args:
        config_path: Path to the config file being modified.
                     The lock file will be created at config_path.with_suffix('.lock').
        timeout: Maximum seconds to wait for lock acquisition.
                 Default 5.0s -- fail fast, don't block the UI.
        poll_interval: Seconds between lock retry attempts.

    Yields:
        None -- the lock is held for the duration of the with block.

    Raises:
        ConfigFileLockTimeout: If lock cannot be acquired within timeout.
        ConfigFileLockError: If lock file cannot be created or other I/O error.

    Usage:
        with config_file_lock(Path("~/.claude-mpm/config/agent_sources.yaml")):
            config = AgentSourceConfiguration.load()
            config.add_repository(repo)
            config.save()
    """
    lock_path = config_path.with_suffix(config_path.suffix + ".lock")

    # Ensure parent directory exists (config file may not exist yet)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_fd = None
    start_time = time.monotonic()

    try:
        # Open (or create) the lock file
        lock_fd = open(lock_path, "w")

        # Retry loop with timeout
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.debug(f"Lock acquired: {lock_path}")
                break
            except OSError:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    raise ConfigFileLockTimeout(
                        f"Could not acquire lock on {config_path} "
                        f"after {timeout}s. Another process may be "
                        f"modifying this file."
                    ) from None
                time.sleep(poll_interval)

        # Write PID to lock file for debugging stale locks
        lock_fd.seek(0)
        lock_fd.truncate()
        lock_fd.write(f"{os.getpid()}\n")
        lock_fd.flush()

        yield

    except ConfigFileLockError:
        raise
    except Exception as e:
        raise ConfigFileLockError(f"Error managing lock for {config_path}: {e}") from e
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
                logger.debug(f"Lock released: {lock_path}")
            except Exception:
                logger.debug("Error releasing lock %s", lock_path, exc_info=True)


def get_config_file_mtime(config_path: Path) -> float:
    """Get the modification time of a config file.

    Returns 0.0 if the file does not exist.
    Used for external change detection (mtime polling).

    Args:
        config_path: Path to the configuration file.

    Returns:
        File modification time as a float (seconds since epoch),
        or 0.0 if file does not exist.
    """
    try:
        return config_path.stat().st_mtime
    except FileNotFoundError:
        return 0.0
