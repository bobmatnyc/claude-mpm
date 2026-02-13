"""Tests for ConfigFileLock advisory file locking.

Covers lock acquisition/release, concurrent access, timeout behavior,
exception safety, directory creation, per-file independence, consistency
under contention, mtime helper, and PID metadata.
"""

import os
import threading
import time
from pathlib import Path

import pytest

from claude_mpm.core.config_file_lock import (
    ConfigFileLockTimeout,
    config_file_lock,
    get_config_file_mtime,
)


# ---------------------------------------------------------------------------
# 1. test_lock_acquire_release
# ---------------------------------------------------------------------------
def test_lock_acquire_release(tmp_path: Path) -> None:
    """Acquire lock, verify lock file exists, release, verify cleanup."""
    config_path = tmp_path / "config.yaml"
    config_path.touch()  # create the target config file
    lock_path = config_path.with_suffix(".yaml.lock")

    with config_file_lock(config_path):
        # While lock is held, lock file must exist
        assert lock_path.exists(), "Lock file should exist while lock is held"

    # After exiting the context manager the fd is closed.
    # The lock file itself may still exist on disk (advisory locks don't
    # require deletion), but we can re-acquire immediately, proving release.
    with config_file_lock(config_path, timeout=1.0):
        pass  # successful re-acquire proves the lock was released


# ---------------------------------------------------------------------------
# 2. test_lock_blocks_concurrent
# ---------------------------------------------------------------------------
def test_lock_blocks_concurrent(tmp_path: Path) -> None:
    """First thread holds lock; second blocks until first releases."""
    config_path = tmp_path / "config.yaml"
    config_path.touch()

    order: list[str] = []
    barrier = threading.Event()

    def holder() -> None:
        with config_file_lock(config_path, timeout=2.0):
            order.append("holder_acquired")
            barrier.set()  # signal that lock is held
            time.sleep(0.5)
            order.append("holder_released")

    def waiter() -> None:
        barrier.wait(timeout=2.0)  # wait until holder has the lock
        time.sleep(0.05)  # small delay so holder is definitely still holding
        with config_file_lock(config_path, timeout=2.0):
            order.append("waiter_acquired")

    t_hold = threading.Thread(target=holder)
    t_wait = threading.Thread(target=waiter)

    t_hold.start()
    t_wait.start()
    t_hold.join(timeout=5.0)
    t_wait.join(timeout=5.0)

    # Waiter must acquire *after* holder releases
    assert order == [
        "holder_acquired",
        "holder_released",
        "waiter_acquired",
    ], f"Unexpected ordering: {order}"


# ---------------------------------------------------------------------------
# 3. test_lock_timeout
# ---------------------------------------------------------------------------
def test_lock_timeout(tmp_path: Path) -> None:
    """Second lock attempt on same file within timeout raises ConfigFileLockTimeout."""
    config_path = tmp_path / "config.yaml"
    config_path.touch()

    acquired = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with config_file_lock(config_path, timeout=5.0):
            acquired.set()
            release.wait(timeout=5.0)

    t = threading.Thread(target=holder)
    t.start()
    acquired.wait(timeout=2.0)

    try:
        # Very short timeout -- should fail quickly
        with pytest.raises(ConfigFileLockTimeout):
            with config_file_lock(config_path, timeout=0.3, poll_interval=0.05):
                pass  # should never reach here
    finally:
        release.set()
        t.join(timeout=5.0)


# ---------------------------------------------------------------------------
# 4. test_lock_released_on_exception
# ---------------------------------------------------------------------------
def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Exception inside `with` block still releases lock; next acquire succeeds.

    Note: The config_file_lock context manager wraps non-ConfigFileLockError
    exceptions in a ConfigFileLockError, so we catch that wrapper type.
    """
    from claude_mpm.core.config_file_lock import ConfigFileLockError

    config_path = tmp_path / "config.yaml"
    config_path.touch()

    with pytest.raises(ConfigFileLockError, match="boom"):
        with config_file_lock(config_path, timeout=1.0):
            raise RuntimeError("boom")

    # Lock must be released -- re-acquire should succeed quickly
    with config_file_lock(config_path, timeout=1.0):
        pass


# ---------------------------------------------------------------------------
# 5. test_lock_nonexistent_directory
# ---------------------------------------------------------------------------
def test_lock_nonexistent_directory(tmp_path: Path) -> None:
    """Lock on file in non-existent directory creates directory."""
    config_path = tmp_path / "deep" / "nested" / "dir" / "config.yaml"

    # Parent directory does not exist yet
    assert not config_path.parent.exists()

    with config_file_lock(config_path, timeout=1.0):
        # Directory should have been created by the lock helper
        assert config_path.parent.exists(), "Lock should create parent directories"


# ---------------------------------------------------------------------------
# 6. test_lock_different_files_independent
# ---------------------------------------------------------------------------
def test_lock_different_files_independent(tmp_path: Path) -> None:
    """Lock on one file does NOT block lock on a different file."""
    config_a = tmp_path / "a.yaml"
    config_b = tmp_path / "b.yaml"
    config_a.touch()
    config_b.touch()

    results: list[str] = []

    with config_file_lock(config_a, timeout=1.0):
        results.append("a_acquired")
        # Should be able to acquire b while a is locked
        with config_file_lock(config_b, timeout=1.0):
            results.append("b_acquired")

    assert results == ["a_acquired", "b_acquired"]


# ---------------------------------------------------------------------------
# 7. test_concurrent_writes_consistent
# ---------------------------------------------------------------------------
def test_concurrent_writes_consistent(tmp_path: Path) -> None:
    """10 concurrent threads each increment a counter; final value is 10."""
    config_path = tmp_path / "counter.yaml"
    config_path.write_text("0")

    errors: list[Exception] = []

    def increment() -> None:
        try:
            with config_file_lock(config_path, timeout=5.0):
                value = int(config_path.read_text().strip())
                time.sleep(0.01)  # simulate work
                config_path.write_text(str(value + 1))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=increment) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15.0)

    assert not errors, f"Unexpected errors: {errors}"
    assert int(config_path.read_text().strip()) == 10, (
        "Counter should be exactly 10 after 10 serialized increments"
    )


# ---------------------------------------------------------------------------
# 8. test_get_config_file_mtime
# ---------------------------------------------------------------------------
def test_get_config_file_mtime(tmp_path: Path) -> None:
    """Returns correct mtime for existing file, 0.0 for non-existent."""
    # Non-existent file
    missing = tmp_path / "does_not_exist.yaml"
    assert get_config_file_mtime(missing) == 0.0

    # Existing file
    existing = tmp_path / "config.yaml"
    existing.write_text("hello")
    mtime = get_config_file_mtime(existing)
    assert mtime > 0.0, "Mtime of existing file must be positive"

    # Mtime should approximately match os.path.getmtime
    expected = existing.stat().st_mtime
    assert abs(mtime - expected) < 0.01, (
        f"Mtime mismatch: got {mtime}, expected ~{expected}"
    )


# ---------------------------------------------------------------------------
# 9. test_lock_pid_written
# ---------------------------------------------------------------------------
def test_lock_pid_written(tmp_path: Path) -> None:
    """Lock file contains PID of holding process."""
    config_path = tmp_path / "config.yaml"
    config_path.touch()
    lock_path = config_path.with_suffix(".yaml.lock")

    with config_file_lock(config_path, timeout=1.0):
        assert lock_path.exists(), "Lock file should exist"
        contents = lock_path.read_text().strip()
        assert contents == str(os.getpid()), (
            f"Lock file should contain PID {os.getpid()}, got '{contents}'"
        )
