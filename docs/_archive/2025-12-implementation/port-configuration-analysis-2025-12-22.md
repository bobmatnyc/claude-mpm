# Port Configuration Analysis: Dashboard/Monitor Port

**Research Date:** 2025-12-22
**Objective:** Locate all port configuration points for the dashboard/monitor service to support changing from 8765 to custom port range (8765-8864).

---

## Summary

The default monitoring and dashboard port is **8765**, which is defined in multiple locations across the codebase. There is NO current configuration using port 5050. The system uses a port range of **8765-8785** for multiple daemon instances.

**Key Finding:** Port 8765 is hardcoded as a default in 8 primary locations across the codebase. To change to a custom range (8765-8864), you need to modify these specific files.

---

## Default Port Locations

### 1. **Constants Definition** (PRIMARY)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/constants.py`
**Lines:** 44-46

```python
class NetworkConfig:
    """Network-related configuration constants."""

    # Port ranges
    SOCKETIO_PORT_RANGE: Tuple[int, int] = (8765, 8785)
    DEFAULT_SOCKETIO_PORT = 8765
    DEFAULT_DASHBOARD_PORT = 8765
```

**Action Required:** Update the `SOCKETIO_PORT_RANGE` tuple from `(8765, 8785)` to `(8765, 8864)` and optionally update the `DEFAULT_SOCKETIO_PORT` and `DEFAULT_DASHBOARD_PORT`.

---

### 2. **Config Constants** (SECONDARY)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/config_constants.py`
**Lines:** 49-50, 151-153

```python
"socketio_default": 8765,
"socketio_range_start": 8765,
...
return cls.DEFAULT_VALUES["ports"].get(port_type, 8765)
return cls.DEFAULT_VALUES["ports"].get(port_type, 8765)
```

**Action Required:** Update the port defaults in the dictionary and default fallback values.

---

### 3. **Monitor Command** (CLI COMMAND)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/monitor.py`
**Lines:** 71, 159, 183

```python
# Line 71 - _start_monitor method
port = getattr(args, "port", None)
if port is None:
    port = 8765  # Default to 8765 for unified monitor

# Line 159 - _stop_monitor method
if port is None:
    port = 8765  # Default to 8765 for unified monitor

# Line 183 - _restart_monitor method
if port is None:
    port = 8765  # Default to 8765 for unified monitor
```

**Action Required:** Update all three hardcoded `8765` defaults to your new default port or use `NetworkConfig.DEFAULT_SOCKETIO_PORT`.

---

### 4. **Dashboard Command** (CLI COMMAND)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/dashboard.py`
**Lines:** 70, 145, 163, 212

```python
# Line 70 - _start_dashboard method
port = getattr(args, "port", 8765)

# Line 145 - _stop_dashboard method
port = getattr(args, "port", 8765)

# Line 163 - _status_dashboard method
default_port = 8765

# Line 212 - _open_dashboard method
port = getattr(args, "port", 8765)
```

**Action Required:** Update all four hardcoded `8765` defaults to your new default or reference `NetworkConfig.DEFAULT_DASHBOARD_PORT`.

---

### 5. **Dashboard Parser** (CLI ARGUMENT PARSER)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/parsers/dashboard_parser.py`
**Lines:** 49, 76, 109

```python
# Line 49 - start_dashboard_parser
start_dashboard_parser.add_argument(
    "--port",
    type=int,
    default=8765,
    help="Port to start dashboard on (default: 8765)",
)

# Line 76 - stop_dashboard_parser
stop_dashboard_parser.add_argument(
    "--port",
    type=int,
    default=8765,
    help="Port of dashboard to stop (default: 8765)",
)

# Line 109 - open_dashboard_parser
open_dashboard_parser.add_argument(
    "--port",
    type=int,
    default=8765,
    help="Port of dashboard to open (default: 8765)",
)
```

**Action Required:** Update all three argument defaults and help text messages. Consider updating help text to reflect new range (e.g., "default: 8765, range: 8765-8864").

---

### 6. **Monitor Parser** (CLI ARGUMENT PARSER)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/parsers/monitor_parser.py`
**Lines:** 58

```python
# Line 58 - dashboard port help text (note: different port!)
stop_dashboard_parser.add_argument(
    "--dashboard-port",
    type=int,
    default=8766,
    help="Dashboard port (default: 8766)",
)
```

**Note:** The monitor parser has a separate `--dashboard-port` argument with default **8766**. This is different from the main dashboard port.

---

### 7. **Monitor Daemon** (DAEMON CLASS)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/monitor/daemon.py`
**Line:** 43

```python
def __init__(
    self,
    host: str = "localhost",
    port: int = 8765,  # DEFAULT HERE
    daemon_mode: bool = False,
    pid_file: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_hot_reload: bool = False,
):
```

**Action Required:** Update the default parameter value from `8765` to your preferred default.

---

### 8. **Monitor Server** (SERVER CLASS)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/monitor/server.py`
**Line:** 142

```python
def __init__(
    self, host: str = "localhost", port: int = 8765, enable_hot_reload: bool = False
):
```

**Action Required:** Update the default parameter value from `8765` to your preferred default.

---

### 9. **Dashboard Status Check Range**
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/dashboard.py`
**Line:** 177

```python
for port in range(8765, 8786):
    is_running = self.dashboard_manager.is_dashboard_running(port)
```

**Action Required:** Update the range from `range(8765, 8786)` (which checks ports 8765-8785) to `range(8765, 8865)` (to check ports 8765-8864).

---

## Change Summary

### Files to Modify (9 files)

| File | Lines | Changes | Priority |
|------|-------|---------|----------|
| `core/constants.py` | 44-46 | Update `SOCKETIO_PORT_RANGE`, `DEFAULT_SOCKETIO_PORT`, `DEFAULT_DASHBOARD_PORT` | **CRITICAL** |
| `core/config_constants.py` | 49-50, 151-153 | Update port defaults in dictionary and fallback values | **CRITICAL** |
| `cli/commands/monitor.py` | 71, 159, 183 | Update 3 hardcoded `8765` defaults in _start_, _stop_, _restart_ methods | **HIGH** |
| `cli/commands/dashboard.py` | 70, 145, 163, 212 | Update 4 hardcoded `8765` defaults in command methods | **HIGH** |
| `cli/parsers/dashboard_parser.py` | 49, 76, 109 | Update 3 argument defaults and help text | **HIGH** |
| `cli/parsers/monitor_parser.py` | 58 | Update `--dashboard-port` default from 8766 if needed | **MEDIUM** |
| `services/monitor/daemon.py` | 43 | Update default `port` parameter | **HIGH** |
| `services/monitor/server.py` | 142 | Update default `port` parameter | **HIGH** |
| `cli/commands/dashboard.py` | 177 | Update port range check from `range(8765, 8786)` to `range(8765, 8865)` | **MEDIUM** |

---

## Port Range Explained

**Current Range:** 8765-8785 (21 ports)
- **Start:** 8765
- **End:** 8785 (inclusive check with `range(8765, 8786)`)

**Requested Range:** 8765-8864 (100 ports)
- **Start:** 8765 (can remain the same)
- **End:** 8864
- **Range call:** `range(8765, 8865)` (end parameter is exclusive in Python)

---

## Implementation Strategy

### Option 1: Change Default Only (Minimal)
Keep the range as 8765-8785, but change all `8765` defaults to `8765` (no change needed).

### Option 2: Extend Range (Recommended)
Change the port range to support 8765-8864:

```python
# In core/constants.py
SOCKETIO_PORT_RANGE: Tuple[int, int] = (8765, 8864)
DEFAULT_SOCKETIO_PORT = 8765  # or your preferred default
DEFAULT_DASHBOARD_PORT = 8765  # or your preferred default
```

Then update all commands and parsers to use these constants instead of hardcoded values.

### Option 3: Use Environment Variable (Advanced)
Add environment variable support for port configuration:

```python
import os

DEFAULT_PORT = int(os.environ.get("CLAUDE_MPM_DEFAULT_PORT", 8765))
PORT_RANGE_START = int(os.environ.get("CLAUDE_MPM_PORT_RANGE_START", 8765))
PORT_RANGE_END = int(os.environ.get("CLAUDE_MPM_PORT_RANGE_END", 8864))
```

---

## No Port 5050 Found

**Important Finding:** There is NO reference to port 5050 anywhere in the codebase. All references are to port 8765 or the range 8765-8785. If users were previously using port 5050, it was likely a misunderstanding or from a different project version.

---

## Related Configuration Files

Other files that may reference ports (for reference):

1. **Hook Configuration:** `src/claude_mpm/hooks/claude_hooks/installer.py` - May have hooks pointing to port 8765
2. **Event Bus:** `src/claude_mpm/services/event_bus/config.py` - Event bus may reference monitor port
3. **Port Manager:** `src/claude_mpm/services/port_manager.py` - Manages port allocation across instances
4. **SocketIO Pool:** `src/claude_mpm/core/socketio_pool.py` - Connection pool may have port references

---

## Verification Steps

After making changes:

1. **Test Command Help:**
   ```bash
   claude-mpm dashboard start --help
   claude-mpm monitor start --help
   ```
   Should show new default port in help text.

2. **Test Default Behavior:**
   ```bash
   claude-mpm dashboard start
   ```
   Should start on new default port.

3. **Test Port Override:**
   ```bash
   claude-mpm dashboard start --port 8800
   ```
   Should start on specified port within new range.

4. **Test Status Range:**
   ```bash
   claude-mpm dashboard status --show-ports
   ```
   Should show status for all ports in 8765-8864 range.

---

## Testing Recommendations

1. Test with single port specification
2. Test with multiple daemon instances on different ports
3. Verify daemon lifecycle (start/stop/restart) works with new ports
4. Check that port binding errors are handled correctly when port is in use
5. Verify health checks work across new port range

---

## Dependencies & Impacts

- **Hook System:** May need to verify hooks can connect to monitor on new port
- **Event Bus Relay:** May need port configuration updates
- **Client Connections:** Any hardcoded port references in client code
- **Documentation:** Update any docs/guides that reference port 8765

---

## Conclusion

The port configuration is centralized in the constants file but distributed throughout CLI commands and parsers. To change the default port or extend the range, you need to update files in this priority order:

1. **First:** Core constants and configuration
2. **Second:** CLI commands that use defaults
3. **Third:** CLI parsers that define arguments
4. **Finally:** Port range checks in status commands

The recommended approach is to use the `NetworkConfig` constants class in `core/constants.py` as the single source of truth and have all other modules import from there, eliminating hardcoded defaults.
