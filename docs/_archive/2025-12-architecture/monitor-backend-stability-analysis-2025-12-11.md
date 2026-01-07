# Claude MPM Monitor Backend Stability Analysis

**Date**: 2025-12-11
**Researcher**: Research Agent
**Scope**: Monitor backend process management, Socket.IO stability, hot reload, error handling, and resource management

---

## Executive Summary

The Claude MPM monitor backend has **7 critical stability issues**, **5 moderate issues**, and **3 low-priority issues** that could cause crashes, race conditions, resource leaks, and zombie processes. The most severe issues involve:

1. **Threading hazards in watchdog file watcher** (CRITICAL)
2. **Event loop lifecycle management** (CRITICAL)
3. **Race conditions in daemon startup** (CRITICAL)
4. **Missing task cancellation in heartbeat** (CRITICAL)
5. **Socket.IO connection management** (MODERATE)

---

## CRITICAL Issues (Severity: High)

### 1. Threading Timer Race Condition in File Watcher

**Location**: `src/claude_mpm/services/monitor/server.py:69-93`

**Issue**: The `SvelteBuildWatcher` uses `threading.Timer` with debouncing, but doesn't properly clean up timers on shutdown. This creates a race condition where:
- Timer threads can outlive the event loop
- Multiple timers can accumulate during rapid file changes
- Timers can fire after the event loop is closed

**Code**:
```python
class SvelteBuildWatcher(FileSystemEventHandler):
    def __init__(self, sio: socketio.AsyncServer, loop: asyncio.AbstractEventLoop, logger):
        self.debounce_timer = None  # NOT thread-safe
        self.debounce_delay = 0.5

    def on_any_event(self, event):
        # Cancel existing timer
        if self.debounce_timer:
            self.debounce_timer.cancel()  # ❌ NOT ATOMIC - race condition!

        # Schedule reload after debounce delay
        self.debounce_timer = threading.Timer(  # ❌ Can leak threads
            self.debounce_delay,
            self._trigger_reload
        )
        self.debounce_timer.start()

    def _trigger_reload(self):
        asyncio.run_coroutine_threadsafe(
            self._emit_reload_event(),
            self.loop  # ❌ Loop might be closed
        )
```

**Problems**:
1. **Race condition**: Between `cancel()` and assignment of new timer, multiple timers can exist
2. **No cleanup on shutdown**: Timer threads continue running after server stops
3. **Event loop closure**: `run_coroutine_threadsafe` can fail if loop is closed
4. **No thread safety**: Multiple file events can create overlapping timers

**Recommended Fix**:
```python
class SvelteBuildWatcher(FileSystemEventHandler):
    def __init__(self, sio: socketio.AsyncServer, loop: asyncio.AbstractEventLoop, logger):
        self.debounce_timer = None
        self.debounce_delay = 0.5
        self.timer_lock = threading.Lock()  # ✅ Thread-safe timer management
        self.shutdown = False  # ✅ Shutdown flag

    def on_any_event(self, event):
        if self.shutdown:
            return

        with self.timer_lock:  # ✅ Atomic timer replacement
            if self.debounce_timer:
                self.debounce_timer.cancel()

            self.debounce_timer = threading.Timer(
                self.debounce_delay,
                self._trigger_reload
            )
            self.debounce_timer.daemon = True  # ✅ Daemon thread cleanup
            self.debounce_timer.start()

    def _trigger_reload(self):
        if self.shutdown:
            return

        try:
            # Check if loop is running before scheduling
            if self.loop and not self.loop.is_closed():  # ✅ Safety check
                asyncio.run_coroutine_threadsafe(
                    self._emit_reload_event(),
                    self.loop
                )
        except Exception as e:
            self.logger.error(f"Error triggering reload: {e}")

    def cleanup(self):  # ✅ NEW: Proper cleanup
        self.shutdown = True
        with self.timer_lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
                self.debounce_timer = None
```

**Severity**: CRITICAL - Can cause crashes when file watcher triggers after shutdown

---

### 2. Event Loop Not Closed in Server Thread

**Location**: `src/claude_mpm/services/monitor/server.py:232-273`

**Issue**: The event loop cleanup in `_run_server()` has timing issues that can cause "I/O operation on closed kqueue" errors on macOS:

**Code**:
```python
finally:
    if loop is not None:
        try:
            self._cancel_all_tasks(loop)

            # Clear the loop reference from the instance first
            self.loop = None  # ❌ Cleared before tasks finish

            # Stop the loop if it's still running
            if loop.is_running():
                loop.stop()

            # Wait a moment for the loop to stop
            time.sleep(0.1)  # ❌ Not enough time for cleanup

            # Clear the event loop from the thread BEFORE closing
            asyncio.set_event_loop(None)

            # Now close the loop
            if not loop.is_closed():
                loop.close()
                time.sleep(0.05)  # ❌ Still too short
```

**Problems**:
1. **`self.loop = None` too early**: Set before tasks are cancelled, can cause AttributeError
2. **Insufficient sleep time**: 0.1s and 0.05s sleeps not enough for cleanup
3. **No verification**: Doesn't verify tasks are actually cancelled
4. **kqueue file descriptors**: Not properly closed before loop.close()

**Recommended Fix**:
```python
finally:
    if loop is not None:
        try:
            # Keep loop reference until fully cleaned up
            # Cancel all tasks FIRST
            self._cancel_all_tasks(loop)

            # Wait for tasks to actually cancel
            if not loop.is_closed():
                try:
                    loop.run_until_complete(asyncio.sleep(0.5))  # ✅ Give tasks time
                except RuntimeError:
                    pass

            # Stop the loop if running
            if loop.is_running():
                loop.stop()
                time.sleep(0.3)  # ✅ Longer wait for loop to stop

            # Verify no tasks remain
            try:
                remaining = asyncio.all_tasks(loop)
                if remaining:
                    self.logger.warning(f"{len(remaining)} tasks still pending during shutdown")
            except RuntimeError:
                pass

            # Clear event loop from thread
            asyncio.set_event_loop(None)

            # Wait before closing
            time.sleep(0.5)  # ✅ Longer wait for OS cleanup

            # Close the loop
            if not loop.is_closed():
                loop.close()
                time.sleep(0.2)  # ✅ Final wait for kqueue cleanup

            # NOW clear instance reference
            self.loop = None  # ✅ Cleared last

        except Exception as e:
            self.logger.debug(f"Error during event loop cleanup: {e}")
```

**Severity**: CRITICAL - Causes kqueue errors and crashes on macOS

---

### 3. Race Condition in Daemon Startup

**Location**: `src/claude_mpm/services/monitor/daemon.py:128-243`

**Issue**: The `_start_daemon()` method has multiple race conditions between port cleanup, PID file checks, and subprocess creation:

**Code**:
```python
def _start_daemon(self, force_restart: bool = False) -> bool:
    if force_restart:
        if not self.daemon_manager.cleanup_port_conflicts(max_retries=3):
            return False
        time.sleep(2)  # ❌ Fixed delay, not verification

    # Check if already running via daemon manager
    if self.daemon_manager.is_running():  # ❌ RACE: Port might be released here
        existing_pid = self.daemon_manager.get_pid()
        if not force_restart:
            return False

    # Check for our service on the port
    is_ours, pid = self.daemon_manager.is_our_service()  # ❌ RACE: Another process might start here
    if is_ours and pid and not force_restart:
        return False

    # Use subprocess approach
    if self.daemon_manager.use_subprocess_daemon():
        return self.daemon_manager.start_daemon_subprocess()  # ❌ No lock protection
```

**Problems**:
1. **TOCTOU bug**: Time-of-check/time-of-use between `cleanup_port_conflicts()` and subprocess start
2. **No atomicity**: Multiple checks without locking, another process can grab port
3. **Fixed sleeps**: `time.sleep(2)` doesn't verify port is actually free
4. **PID file race**: Subprocess writes PID file, but parent checks it without synchronization

**Recommended Fix**:
```python
def _start_daemon(self, force_restart: bool = False) -> bool:
    # Use daemon manager's internal lock for atomicity
    with self.daemon_manager._lock:  # ✅ Atomic operation
        if force_restart:
            if not self.daemon_manager.cleanup_port_conflicts(max_retries=3):
                return False

            # VERIFY port is free (not just sleep)
            if not self._wait_for_port_available(timeout=5.0):  # ✅ Verify, don't trust
                return False

        # Single atomic check (all checks together)
        if self.daemon_manager.is_running():
            existing_pid = self.daemon_manager.get_pid()
            if not force_restart:
                return False

        # Re-verify port is available right before starting
        if not self.daemon_manager._is_port_available():  # ✅ Final check
            self.logger.error("Port became unavailable during startup")
            return False

        # Start subprocess while holding lock
        if self.daemon_manager.use_subprocess_daemon():
            return self.daemon_manager.start_daemon_subprocess()

        return self.daemon_manager.daemonize()

def _wait_for_port_available(self, timeout: float = 5.0) -> bool:
    """Wait for port to actually be available, not just sleep."""
    start = time.time()
    while time.time() - start < timeout:
        if self.daemon_manager._is_port_available():
            return True
        time.sleep(0.1)
    return False
```

**Severity**: CRITICAL - Can cause multiple daemon instances or port binding failures

---

### 4. Heartbeat Task Not Cancelled Properly

**Location**: `src/claude_mpm/services/monitor/server.py:304, 851-855`

**Issue**: The heartbeat task is created but cancellation doesn't wait for completion, leading to dangling tasks:

**Code**:
```python
# Created:
self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

# Cancelled:
if self.heartbeat_task and not self.heartbeat_task.done():
    self.heartbeat_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await self.heartbeat_task  # ❌ But task might not cancel immediately
    self.logger.debug("Heartbeat task cancelled")
```

**Problems**:
1. **No timeout**: `await self.heartbeat_task` can hang if task doesn't respond to cancel
2. **suppressed CancelledError**: Hides potential issues
3. **No verification**: Doesn't verify task actually stopped

**Recommended Fix**:
```python
if self.heartbeat_task and not self.heartbeat_task.done():
    self.heartbeat_task.cancel()
    try:
        # Wait for cancellation with timeout
        await asyncio.wait_for(self.heartbeat_task, timeout=2.0)  # ✅ Timeout
    except asyncio.CancelledError:
        self.logger.debug("Heartbeat task cancelled successfully")
    except asyncio.TimeoutError:
        self.logger.warning("Heartbeat task cancellation timed out")  # ✅ Detect hangs
    except Exception as e:
        self.logger.error(f"Error cancelling heartbeat task: {e}")
    finally:
        self.heartbeat_task = None
```

**Severity**: CRITICAL - Can prevent clean shutdown and cause resource leaks

---

### 5. File Observer Not Properly Stopped

**Location**: `src/claude_mpm/services/monitor/server.py:838-848`

**Issue**: The watchdog `Observer` cleanup doesn't handle hung threads:

**Code**:
```python
if self.file_observer:
    try:
        self.file_observer.stop()
        self.file_observer.join(timeout=2)  # ❌ No verification of join success
        self.logger.debug("File observer stopped")
    except Exception as e:
        self.logger.debug(f"Error stopping file observer: {e}")
    finally:
        self.file_observer = None  # ❌ Set to None even if thread still running
        self.file_watcher = None
```

**Problems**:
1. **No join verification**: Doesn't check if `join(timeout=2)` succeeded
2. **Silent failure**: Thread might still be running but reference is cleared
3. **Timer cleanup**: Doesn't call `file_watcher.cleanup()` to stop pending timers

**Recommended Fix**:
```python
if self.file_observer:
    try:
        # Stop file watcher timers FIRST
        if self.file_watcher:
            self.file_watcher.cleanup()  # ✅ NEW: Stop timers

        # Stop observer
        self.file_observer.stop()

        # Wait with verification
        self.file_observer.join(timeout=3)

        # Check if thread actually stopped
        if self.file_observer.is_alive():  # ✅ Verify
            self.logger.warning("File observer thread still alive after timeout, forcing...")
            # Force cleanup by clearing reference (thread will die when program exits)
        else:
            self.logger.debug("File observer stopped successfully")

    except Exception as e:
        self.logger.debug(f"Error stopping file observer: {e}")
    finally:
        self.file_observer = None
        self.file_watcher = None
```

**Severity**: CRITICAL - Can create zombie threads that prevent clean shutdown

---

### 6. Subprocess Daemon Premature Exit Detection Missing

**Location**: `src/claude_mpm/services/monitor/daemon_manager.py:651-709`

**Issue**: The `start_daemon_subprocess()` method waits for PID file and port binding, but the process might exit prematurely and the error is only logged, not propagated:

**Code**:
```python
while time.time() - start_time < max_wait:
    # Check if process is still running
    returncode = process.poll()
    if returncode is not None:
        # Process exited - this is the bug we're fixing!
        self.logger.error(
            f"Monitor daemon subprocess exited prematurely with code {returncode}"
        )
        self.logger.error(
            f"Port {self.port} daemon failed to start. Check {self.log_file} for details."
        )
        return False  # ✅ Returns False, but...

    # ... continues checking ...

    if pid_file_found and port_bound:
        # ❌ PROBLEM: Might reach here even if process exited
        if self._verify_daemon_health(max_attempts=3):
            return True
        return True  # ❌ Returns success even if health check failed!
```

**Problems**:
1. **Health check failure ignored**: Returns `True` even if health check fails
2. **Race condition**: Process can exit between `poll()` check and success return
3. **No final verification**: Doesn't re-check process state before returning success

**Recommended Fix**:
```python
if pid_file_found and port_bound:
    # CRITICAL: Re-verify process is still running
    returncode = process.poll()
    if returncode is not None:
        self.logger.error(f"Daemon exited after binding port (exit code: {returncode})")
        return False

    # Verify health
    if self._verify_daemon_health(max_attempts=3):
        self.logger.info("Daemon health check passed")
        return True

    # Health check failed - this is a problem
    self.logger.error("Daemon started but failed health check")

    # Kill the process since it's unhealthy
    if process.poll() is None:
        process.terminate()
        time.sleep(1)
        if process.poll() is None:
            process.kill()

    return False  # ✅ Don't return success if health check fails
```

**Severity**: CRITICAL - Can report successful startup when daemon has actually crashed

---

### 7. Event Loop Cleanup in Daemon Thread Has Timing Issue

**Location**: `src/claude_mpm/services/monitor/daemon.py:605-634`

**Issue**: The `_cleanup_asyncio_resources()` method tries to close event loops but doesn't handle all edge cases:

**Code**:
```python
def _cleanup_asyncio_resources(self):
    try:
        loop = asyncio.get_event_loop()
        if loop and not loop.is_closed():
            # Cancel any pending tasks
            pending = asyncio.all_tasks(loop)  # ❌ Can raise RuntimeError
            for task in pending:
                task.cancel()

            # Stop and close the loop
            if loop.is_running():
                loop.stop()  # ❌ Doesn't wait for stop to complete

            asyncio.set_event_loop(None)
            loop.close()  # ❌ Can close while tasks still running

    except RuntimeError:
        pass  # ❌ Silently ignores errors
```

**Problems**:
1. **`asyncio.all_tasks()` can raise**: If no event loop, raises RuntimeError
2. **`loop.stop()` is async**: Doesn't wait for loop to actually stop
3. **Tasks not awaited**: Cancels tasks but doesn't wait for them to finish
4. **Silent failures**: All exceptions suppressed

**Recommended Fix**:
```python
def _cleanup_asyncio_resources(self):
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in current thread
            return

        if loop and not loop.is_closed():
            try:
                # Cancel all tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()

                # Wait for tasks to cancel
                if pending and not loop.is_running():
                    try:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    except Exception as e:
                        self.logger.debug(f"Error waiting for task cancellation: {e}")

            except RuntimeError:
                # Tasks list changed, that's okay
                pass

            # Stop loop and wait
            if loop.is_running():
                loop.stop()
                # Give loop time to actually stop
                for _ in range(10):
                    time.sleep(0.1)
                    if not loop.is_running():
                        break

            # Clear and close
            asyncio.set_event_loop(None)
            time.sleep(0.2)  # ✅ Wait for OS cleanup
            loop.close()
            time.sleep(0.1)  # ✅ Final wait

    except Exception as e:
        self.logger.debug(f"Error cleaning up asyncio resources: {e}")
```

**Severity**: CRITICAL - Can cause event loop corruption and kqueue errors

---

## MODERATE Issues (Severity: Medium)

### 8. Socket.IO Ping Timeout Too Aggressive

**Location**: `src/claude_mpm/services/monitor/server.py:278-285`

**Issue**: Socket.IO ping configuration might be too aggressive for slow networks:

**Code**:
```python
self.sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_interval=30,   # 30 seconds
    ping_timeout=60,    # 60 seconds - might be too short
)
```

**Problem**: On slow networks or during high load, 60-second ping timeout can cause premature disconnections.

**Recommended Fix**:
```python
self.sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_interval=30,
    ping_timeout=120,  # ✅ Increase to 2 minutes for stability
    max_http_buffer_size=1e8,  # ✅ Add buffer size limit
)
```

**Severity**: MODERATE - Can cause connection drops under load

---

### 9. HTTP Session Not Closed in Event Emitter

**Location**: `src/claude_mpm/services/monitor/event_emitter.py:282-301`

**Issue**: The HTTP session cleanup has proper timing, but the error handling could be improved:

**Code**:
```python
if self._http_session:
    try:
        await self._http_session.close()
        await asyncio.sleep(0.25)  # Good
    except Exception as e:
        self.logger.debug(f"Error closing HTTP session: {e}")  # ❌ Debug level
    finally:
        self._http_session = None
```

**Problem**: Errors during session close are only logged at DEBUG level, making troubleshooting difficult.

**Recommended Fix**:
```python
if self._http_session:
    try:
        # Check for pending requests
        if hasattr(self._http_session, '_connector') and self._http_session._connector:
            active = len(self._http_session._connector._acquired)
            if active > 0:
                self.logger.warning(f"Closing session with {active} active connections")  # ✅ Warn
            await asyncio.sleep(0.1)

        await self._http_session.close()
        await asyncio.sleep(0.25)
    except Exception as e:
        self.logger.warning(f"Error closing HTTP session: {e}")  # ✅ Warning level
    finally:
        self._http_session = None
```

**Severity**: MODERATE - Can hide resource leak issues

---

### 10. No Connection Limit for Socket.IO

**Location**: `src/claude_mpm/services/monitor/server.py:278-285`

**Issue**: Socket.IO server doesn't limit concurrent connections:

**Code**:
```python
self.sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    # ❌ No max_connections parameter
    # ❌ No rate limiting
)
```

**Problem**: Unlimited connections can cause resource exhaustion under attack or bug conditions.

**Recommended Fix**:
```python
self.sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_interval=30,
    ping_timeout=120,
    max_http_buffer_size=1e8,
    async_mode='aiohttp',  # ✅ Explicit mode
)

# Add custom middleware to track connections
@self.sio.event
async def connect(sid, environ):
    if len(self.dashboard_handler.connected_clients) >= 100:  # ✅ Limit
        self.logger.warning(f"Connection limit reached, rejecting {sid}")
        return False
    return True
```

**Severity**: MODERATE - Can cause resource exhaustion

---

### 11. Port Cleanup Retry Logic Could Be Improved

**Location**: `src/claude_mpm/services/monitor/daemon_manager.py:98-141`

**Issue**: Port cleanup uses fixed retry delays:

**Code**:
```python
for attempt in range(max_retries):
    if self._is_port_available():
        return True

    if self._kill_processes_on_port():
        time.sleep(2 if attempt == 0 else 3)  # ❌ Fixed delays
```

**Problem**: Fixed delays don't account for OS cleanup time variations.

**Recommended Fix**:
```python
for attempt in range(max_retries):
    if self._is_port_available():
        return True

    if self._kill_processes_on_port():
        # Exponential backoff with verification
        delay = min(2 ** attempt, 10)  # ✅ Exponential: 1s, 2s, 4s, 8s, max 10s

        # Poll for availability instead of blind sleep
        for _ in range(int(delay * 10)):
            if self._is_port_available():
                return True
            time.sleep(0.1)
```

**Severity**: MODERATE - Can cause unnecessary delays or failures

---

### 12. Weak References Not Cleaned Proactively

**Location**: `src/claude_mpm/services/monitor/event_emitter.py:234-242`

**Issue**: Dead weak references are only cleaned on emit, not proactively:

**Code**:
```python
def _cleanup_dead_references(self):
    to_remove = []
    for weak_ref in self._socketio_servers:
        if weak_ref() is None:
            to_remove.append(weak_ref)

    for weak_ref in to_remove:
        self._socketio_servers.discard(weak_ref)
```

**Problem**: Dead references accumulate until next emit event.

**Recommended Fix**:
```python
# Add periodic cleanup task
async def _periodic_cleanup(self):
    """Periodically clean up dead weak references."""
    while not self._shutdown:
        await asyncio.sleep(60)  # Every minute
        self._cleanup_dead_references()

# In __init__:
self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

# In close():
if self._cleanup_task:
    self._cleanup_task.cancel()
    try:
        await self._cleanup_task
    except asyncio.CancelledError:
        pass
```

**Severity**: MODERATE - Can cause memory bloat over time

---

## LOW Priority Issues

### 13. Health Check Timeout Too Short

**Location**: `src/claude_mpm/services/monitor/daemon_manager.py:476-523`

**Issue**: Health check uses 2-second timeout which might be too short for cold start:

**Code**:
```python
response = requests.get(
    f"http://{self.host}:{self.port}/health",
    timeout=2  # ❌ Might be too short
)
```

**Recommended Fix**:
```python
response = requests.get(
    f"http://{self.host}:{self.port}/health",
    timeout=5  # ✅ More generous for cold start
)
```

**Severity**: LOW - Minor inconvenience, not critical

---

### 14. File Path Security Check Could Be Stricter

**Location**: `src/claude_mpm/services/monitor/server.py:498-501`

**Issue**: File path validation only checks if absolute:

**Code**:
```python
if not file_path or not Path(file_path).is_absolute():
    return web.json_response(
        {"success": False, "error": "Invalid file path"}, status=400
    )
```

**Recommended Fix**:
```python
# Add path traversal protection
try:
    file_path_obj = Path(file_path).resolve()
    # Ensure path doesn't escape allowed directories
    allowed_dirs = [Path.cwd(), Path.home() / "Projects"]
    if not any(file_path_obj.is_relative_to(d) for d in allowed_dirs):
        return web.json_response(
            {"success": False, "error": "Path not in allowed directories"},
            status=403
        )
except (ValueError, OSError):
    return web.json_response(
        {"success": False, "error": "Invalid file path"}, status=400
    )
```

**Severity**: LOW - Security hardening, not urgent

---

### 15. Git Command Subprocess Has No Error Logging

**Location**: `src/claude_mpm/services/monitor/server.py:610-622`

**Issue**: Git subprocess failures are silently ignored:

**Code**:
```python
try:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        timeout=2,
        cwd=Path.cwd(),
        check=False,  # ❌ Errors not logged
    )
    if result.returncode == 0 and result.stdout.strip():
        config["gitBranch"] = result.stdout.strip()
except Exception:
    pass  # ❌ Silent failure
```

**Recommended Fix**:
```python
try:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        timeout=2,
        cwd=Path.cwd(),
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        config["gitBranch"] = result.stdout.strip()
    elif result.returncode != 0:
        self.logger.debug(f"Git branch command failed: {result.stderr}")  # ✅ Log
except Exception as e:
    self.logger.debug(f"Git branch detection error: {e}")  # ✅ Log
```

**Severity**: LOW - Cosmetic, doesn't affect core functionality

---

## Resource Leak Analysis

### Memory Leaks

1. **Dead weak references** (MODERATE): Accumulate until manually cleaned
2. **Uncancelled timers** (CRITICAL): `threading.Timer` objects not cleaned up
3. **HTTP connector connections** (LOW): Properly cleaned with timeouts

### File Handle Leaks

1. **Log file handles** (LOW): Properly managed with context managers
2. **Socket descriptors** (CRITICAL): Event loop kqueue cleanup issues

### Thread Leaks

1. **Watchdog observer threads** (CRITICAL): May not stop on timeout
2. **Timer threads** (CRITICAL): Not cancelled on shutdown
3. **Server thread** (LOW): Daemon thread, cleaned automatically

---

## Recommended Priority Order

### Immediate (Week 1)
1. **Fix threading timer cleanup** - Add `cleanup()` method to `SvelteBuildWatcher`
2. **Fix event loop closure timing** - Increase sleep delays in `_run_server()` finally block
3. **Fix heartbeat task cancellation** - Add timeout to task cancellation

### Short-term (Week 2)
4. **Fix daemon startup race conditions** - Add locking to `_start_daemon()`
5. **Fix file observer stop verification** - Check `is_alive()` after join
6. **Fix subprocess health check** - Don't return success if health check fails

### Medium-term (Month 1)
7. **Add Socket.IO connection limits** - Prevent resource exhaustion
8. **Improve port cleanup** - Use exponential backoff
9. **Add periodic weak reference cleanup** - Reduce memory bloat

### Long-term (Nice to have)
10. **Security hardening** - Path traversal protection
11. **Better error logging** - Git command failures
12. **Health check tuning** - Longer timeouts

---

## Testing Recommendations

### Unit Tests Needed
1. `test_file_watcher_cleanup()` - Verify timer threads stop
2. `test_event_loop_cleanup()` - Verify no kqueue errors
3. `test_heartbeat_cancellation()` - Verify task stops within timeout
4. `test_daemon_startup_race()` - Concurrent startup attempts
5. `test_port_cleanup_retry()` - Port becomes available during retry

### Integration Tests Needed
1. **Stress test**: Start/stop monitor 100 times, verify no leaks
2. **Load test**: 100 concurrent Socket.IO connections
3. **Failure test**: Kill daemon mid-startup, verify cleanup
4. **Hot reload test**: Rapid file changes, verify no timer leaks

### Manual Testing Checklist
- [ ] Start monitor in background mode
- [ ] Trigger hot reload 10 times rapidly
- [ ] Stop monitor, verify no zombie threads (`ps aux | grep python`)
- [ ] Restart monitor multiple times
- [ ] Check for file handle leaks (`lsof -p <pid>`)
- [ ] Monitor memory usage over 1 hour

---

## Metrics to Monitor

### Health Metrics
- Server uptime
- Connected clients count
- Event emission rate (direct vs HTTP)
- Failed event count

### Resource Metrics
- Thread count (should stay constant)
- File descriptor count (should not grow)
- Memory usage (should stabilize)
- Event loop tasks pending

### Error Metrics
- kqueue errors per hour
- Port binding failures
- Health check failures
- Task cancellation timeouts

---

## Conclusion

The Claude MPM monitor backend has significant stability issues, particularly around **threading hazards** in the file watcher, **event loop lifecycle management**, and **daemon startup race conditions**. The issues are well-defined with specific code locations and recommended fixes.

**Estimated Impact**:
- **Critical issues**: 7 (could cause crashes, hangs, or data loss)
- **Moderate issues**: 5 (could cause resource leaks or poor UX)
- **Low issues**: 3 (minor improvements)

**Estimated Fix Time**:
- Critical fixes: 2-3 days
- Moderate fixes: 1-2 days
- Low priority: 1 day
- **Total**: ~1 week for all fixes

**Risk Assessment**: WITHOUT fixes, monitor stability is **MEDIUM-HIGH RISK** in production. WITH fixes, stability becomes **LOW RISK**.
