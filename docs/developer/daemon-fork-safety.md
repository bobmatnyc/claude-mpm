# Daemon Fork Safety on macOS

## The Problem: `EXC_BAD_ACCESS` / `SIGSEGV` after `os.fork()`

### Root cause

macOS uses CoreFoundation (CF) internally for logging, Objective-C runtime
bookkeeping, and operating-system services.  CoreFoundation registers
thread-local allocators, port rights, and dispatch sources at process startup.

When a Python process that has multiple threads (e.g. an asyncio event loop,
a uvicorn server, or any `threading.Thread`) calls `os.fork()`, the child
process inherits the **address space snapshot** of the parent but only the
**single calling thread**.  All other threads cease to exist in the child, but
the CF data structures they owned are now dangling — the locks are held by
threads that no longer exist, and the port rights point to Mach ports that the
kernel has already torn down.

The first time the child touches CF-backed functionality — writing to `os_log`,
calling `setproctitle`, initialising a new `NSRunLoop`, or even calling
`logging.getLogger(...)` which may internally use CF — the kernel delivers
`EXC_BAD_ACCESS (SIGSEGV)` because the child is accessing deallocated or
corrupted memory.

This is documented in Apple's own POSIX fork(2) man page supplement:

> After a fork() in a multithreaded program, the child can safely call
> only async-signal-safe functions (see signal(3)) until it calls exec(2).

Python's `os.fork()` makes no special effort to satisfy this constraint.

### Why PR #691 (`fork_safety.py` / `multiprocessing.set_start_method`) was not the real fix

PR #691 added `claude_mpm/mcp/fork_safety.py` and called
`multiprocessing.set_start_method("spawn")`.  This guards
`multiprocessing.Process(...)` usages.  However:

1. `multiprocessing.set_start_method` has no effect on **raw `os.fork()`
   calls** — they remain fork-based regardless.
2. The daemon managers in `services/` used raw `os.fork()` directly (not
   `multiprocessing.Process`), so they were completely unaffected.
3. macOS has defaulted `multiprocessing` to `"spawn"` since Python 3.8, so
   the call was largely a no-op on the target platform anyway.

The `fork_safety.py` module is harmless defense-in-depth for edge cases where
the default is overridden, but it was not and cannot be the fix for the daemon
SIGSEGV.

---

## The Fix: exec-based daemon spawn (issue #693)

### Pattern

Replace every raw `os.fork()` double-fork daemonization with
`subprocess.Popen(start_new_session=True)`:

```python
import os, subprocess, sys

# Parent: spawn a fresh interpreter (no fork, no CF state inheritance)
process = subprocess.Popen(
    [sys.executable, "-m", "my_package.my_daemon_entry"],
    stdin=subprocess.DEVNULL,
    stdout=open("/path/to/daemon.log", "a"),
    stderr=subprocess.STDOUT,
    start_new_session=True,          # ← replaces the double-fork + os.setsid()
    env={**os.environ, "MY_DAEMON_CHILD": "1"},
)

# Child (detected by env var): runs the daemon loop in the foreground.
# It was exec'd from scratch — no CF state, no dangling threads.
```

`start_new_session=True` instructs the OS (both macOS and Linux) to call
`setsid()` before `exec()`, which:

- Creates a new process group and session (detaches from the terminal).
- Is the exact session-detachment that the old `os.setsid()` call in the
  first-fork child was providing.

Because `subprocess.Popen` always `exec()`s a new interpreter image, the child
process starts with a clean, single-threaded CF state — no inherited kqueue
descriptors, no dangling Mach ports, no locked CF allocators.

### What the double-fork provided and how `Popen` preserves it

| Double-fork behaviour | `subprocess.Popen` equivalent |
|---|---|
| Session detachment (`os.setsid()`) | `start_new_session=True` |
| `stdin` closed / `/dev/null` | `stdin=subprocess.DEVNULL` |
| `stdout`/`stderr` → log file | `stdout=open(log, "a"), stderr=subprocess.STDOUT` |
| Working directory (`os.chdir("/")`) | `cwd="/"` if needed (current modules omit this; daemon-relative paths resolve correctly) |
| `umask(0)` | Child inherits parent umask; daemons that need specific permissions set `umask` themselves after startup |
| PID file written by daemon | Child writes PID file after starting (`os.getpid()`) |
| Parent returns immediately | Parent gets child `pid = process.pid` and optionally polls for the PID file |

### Recursion guard

Because the parent calls itself (re-invokes `sys.executable -m
my_package.cli ...`), the child would loop forever without a guard.  Every
daemon uses an environment variable to break the recursion:

| Daemon | Guard variable |
|---|---|
| `SocketIODaemonManager` | `CLAUDE_MPM_SOCKETIO_DAEMON=1` |
| `MessageConsumer --daemon` | `CLAUDE_MPM_MSG_CONSUMER_DAEMON=1` |
| `DaemonLifecycle` / monitor | `CLAUDE_MPM_SUBPROCESS_DAEMON=1` |
| `DaemonManager` (monitor) | `CLAUDE_MPM_SUBPROCESS_DAEMON=1` |

When the child detects its guard variable it skips spawning another subprocess
and runs the daemon loop directly in the foreground.

---

## Files changed in issue #693

| File | Change |
|---|---|
| `src/claude_mpm/services/infrastructure/daemon_manager.py` | Replaced `os.fork()` single-fork with `_start_subprocess_daemon()` + `_SOCKETIO_DAEMON_ENV_KEY` guard |
| `src/claude_mpm/services/communication/message_consumer.py` | Replaced double-fork `--daemon` path with `subprocess.Popen(start_new_session=True)` |
| `src/claude_mpm/services/monitor/management/lifecycle.py` | Replaced double-fork `daemonize()` with `subprocess.Popen(start_new_session=True)` |
| `src/claude_mpm/services/monitor/daemon_manager.py` | Removed double-fork body from `daemonize()`; method now returns `False` with an error log (callers use `start_daemon_subprocess()`) |
| `tests/services/test_daemon_fork_safety.py` | New: AST no-fork invariant + per-daemon Popen/PID/stop/restart/idempotency tests |
| `docs/developer/daemon-fork-safety.md` | This file |

---

## Inherited in-memory state: what had to be reconstructed

The old double-fork inherited everything from the parent in-memory because it
shared the parent's address space.  The exec-based child gets a fresh
interpreter and must reconstruct all runtime state from config/args/env.

**`SocketIODaemonManager`**: The parent passes `host` and `port` as Python
literals embedded in the `-c` command string.  The child instantiates a fresh
`SocketIODaemonManager` and calls `start()`, which detects the env flag and
runs `_run_server()` directly.  No stateful objects are inherited.

**`MessageConsumer`**: Stateless — the child re-imports `MessageBus` from
scratch and creates a new `Consumer`.  Queue state lives in SQLite
(`~/.claude-mpm/message_queue.db`) which is on disk, not in memory.

**`DaemonLifecycle`**: The parent passes `--port`, `--pid-file`, and
`--log-file` as CLI arguments.  The startup-status-file path is passed via
`CLAUDE_MPM_STARTUP_STATUS_FILE`.  The child reconstructs a `DaemonLifecycle`
instance from CLI args and calls `write_pid_file()` + `_report_startup_success()`
itself.

**`DaemonManager`**: Identical pattern to `DaemonLifecycle`.  Port, host,
pid-file, and log-file are forwarded as CLI args.  The child writes its own
PID file after binding the port.

---

## Checklist for adding future daemons safely

1. **Never call `os.fork()` from a multithreaded Python parent on macOS.**
   If you must fork, ensure `exec()` happens as the very next system call with
   no CF/logging/Python-runtime touches in between.

2. **Use `subprocess.Popen([sys.executable, ...], start_new_session=True)`**
   to spawn daemon processes.  Pass `stdin=subprocess.DEVNULL` and redirect
   `stdout`/`stderr` to a log file.

3. **Choose a unique environment variable** as a recursion guard (e.g.
   `MY_DAEMON_CHILD=1`).  The child detects this and runs in foreground mode
   without spawning another subprocess.

4. **Pass all required configuration** as CLI arguments or environment
   variables — the child cannot inherit in-memory objects.

5. **Write the PID file in the child** (after startup), not in the parent.
   The parent waits for the PID file to appear (or polls a status file) to
   confirm startup.

6. **Add a test** in `tests/services/test_daemon_fork_safety.py` that:
   - Patches `os.fork` to raise and asserts your start path never calls it.
   - Asserts `subprocess.Popen` is called with `start_new_session=True`.
   - Tests PID file write/cleanup.
   - Tests stop/restart.

7. **On Linux**, `start_new_session=True` behaves identically to macOS —
   it calls `setsid(2)` before `execve(2)`.  Your daemon will work on both
   platforms without platform-specific branches.
