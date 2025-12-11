# Monitor Server Architecture

## Overview

Claude MPM uses a **two-tier server architecture** for its monitoring dashboard. Understanding this architecture is critical when adding features or debugging routing issues.

## Server Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│          claude-mpm monitor command                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         UnifiedMonitorServer                            │
│  (src/claude_mpm/services/monitor/server.py)           │
│                                                          │
│  • Wraps SocketIOServer                                 │
│  • Adds HTTP routes for dashboards                      │
│  • Serves static files                                  │
│  • Used by CLI monitor command                          │
│                                                          │
│  Routes:                                                 │
│    GET  /                 → Legacy dashboard            │
│    GET  /svelte           → Svelte dashboard            │
│    GET  /_app/*           → Svelte assets               │
│    GET  /api/health       → Health check                │
│    GET  /api/config       → Configuration               │
│                                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         SocketIOServer                                  │
│  (src/claude_mpm/services/socketio/server/core.py)     │
│                                                          │
│  • Low-level Socket.IO server with aiohttp              │
│  • Handles Socket.IO events                             │
│  • NOT directly used by monitor command                 │
│  • Can run standalone in daemon mode                    │
│                                                          │
│  Socket.IO Events:                                       │
│    - connect / disconnect                               │
│    - project_update                                      │
│    - agent_event                                         │
│    - ticket_event                                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Which Server Does What?

### UnifiedMonitorServer (Higher Level)

**Used by**: `claude-mpm monitor` command
**Location**: `src/claude_mpm/services/monitor/server.py`
**Purpose**: Complete monitoring solution with HTTP dashboard and Socket.IO

**Responsibilities**:
- Serves static dashboard files
- Provides HTTP API endpoints
- Wraps SocketIOServer for WebSocket functionality
- Routes HTTP requests to appropriate handlers
- Manages dashboard asset serving

**When to use**:
- Adding HTTP routes for dashboard features
- Serving static files
- Providing REST API endpoints
- Implementing dashboard-specific functionality

### SocketIOServer (Lower Level)

**Used by**: Direct Socket.IO daemon mode (advanced)
**Location**: `src/claude_mpm/services/socketio/server/core.py`
**Purpose**: Core Socket.IO event handling

**Responsibilities**:
- Socket.IO connection management
- Real-time event broadcasting
- WebSocket protocol handling
- Low-level aiohttp server setup

**When to use**:
- Adding Socket.IO event handlers
- Modifying WebSocket behavior
- Low-level server configuration

## 🎯 Where to Add Routes

### HTTP Routes for Dashboard Features

**✅ CORRECT**: Add to `UnifiedMonitorServer._setup_http_routes()`

```python
# src/claude_mpm/services/monitor/server.py

async def _setup_http_routes(self):
    """Setup HTTP routes - ADD DASHBOARD ROUTES HERE"""

    # Dashboard routes
    self.app.router.add_get('/', self._serve_dashboard)
    self.app.router.add_get('/svelte', self._serve_svelte_dashboard)

    # API routes
    self.app.router.add_get('/api/health', self._handle_health_check)
    self.app.router.add_get('/api/config', self._handle_config)

    # 👇 ADD NEW DASHBOARD ROUTES HERE
    self.app.router.add_get('/api/my-new-endpoint', self._handle_new_feature)
```

**❌ WRONG**: Adding dashboard routes to `SocketIOServer`

```python
# ❌ DON'T DO THIS - Routes won't be available in monitor command
# src/claude_mpm/services/socketio/server/core.py

class SocketIOServer:
    def _setup_routes(self):
        # Dashboard routes added here won't work with `claude-mpm monitor`
        self.app.router.add_get('/api/my-endpoint', ...)  # ❌ WRONG PLACE
```

### Socket.IO Event Handlers

**✅ EITHER SERVER**: Socket.IO events can be added to either server

```python
# Option 1: In SocketIOServer (inherited by UnifiedMonitorServer)
@self.sio.event
async def my_event(sid, data):
    pass

# Option 2: In UnifiedMonitorServer (extends inherited handlers)
@self.socketio_server.sio.event
async def my_event(sid, data):
    pass
```

## Dashboard Serving Configuration

### Static File Locations

```
claude-mpm/
├── src/claude_mpm/
│   ├── dashboard/
│   │   └── static/               # Legacy dashboard
│   │       ├── index.html        # → served at /
│   │       ├── styles.css
│   │       └── script.js
│   │
│   └── dashboard/
│       └── static/
│           └── svelte-build/     # Svelte dashboard
│               ├── index.html    # → served at /svelte
│               └── _app/         # → served at /_app/*
│                   ├── immutable/
│                   └── version.json
```

### Route Mapping

| URL Path | Serves | Configured In |
|----------|--------|---------------|
| `/` | Legacy dashboard | `UnifiedMonitorServer._serve_dashboard()` |
| `/svelte` | Svelte dashboard | `UnifiedMonitorServer._serve_svelte_dashboard()` |
| `/_app/*` | Svelte assets | `UnifiedMonitorServer._setup_http_routes()` |
| `/api/*` | REST API | `UnifiedMonitorServer._setup_http_routes()` |

### Path Resolution

**✅ CORRECT**: Use package-relative paths

```python
from pathlib import Path
import claude_mpm

# Get package root
package_root = Path(claude_mpm.__file__).parent

# Static file paths
legacy_dashboard = package_root / "dashboard" / "static"
svelte_dashboard = package_root / "dashboard" / "static" / "svelte-build"
```

**❌ WRONG**: Using project root paths

```python
# ❌ DON'T DO THIS - Breaks when installed as package
from claude_mpm.utils.path_utils import get_project_root

dashboard_path = get_project_root() / "dashboard" / "static"  # ❌ WRONG
```

## Common Mistakes to Avoid

### ❌ Mistake #1: Adding Dashboard Routes to Wrong Server

**Problem**: Routes added to `SocketIOServer` won't be available when using `claude-mpm monitor`.

**Solution**: Always add dashboard HTTP routes to `UnifiedMonitorServer._setup_http_routes()`.

### ❌ Mistake #2: Not Restarting Daemon After Code Changes

**Problem**: Code changes to server don't take effect because daemon is still running old code.

**Solution**:
```bash
# Stop daemon
claude-mpm monitor stop

# Restart with new code
claude-mpm monitor start
```

### ❌ Mistake #3: Using Project Root for Package Files

**Problem**: `get_project_root()` returns the user's project directory, not the package location.

**Solution**: Use `Path(claude_mpm.__file__).parent` for package-relative paths.

### ❌ Mistake #4: Forgetting Static File Route Order

**Problem**: Catch-all routes override specific routes if added first.

**Solution**: Add specific routes before catch-all routes:

```python
# ✅ CORRECT ORDER
self.app.router.add_get('/api/health', self._handle_health_check)  # Specific first
self.app.router.add_get('/', self._serve_dashboard)  # Catch-all last

# ❌ WRONG ORDER
self.app.router.add_get('/', self._serve_dashboard)  # Catch-all first
self.app.router.add_get('/api/health', self._handle_health_check)  # Never reached!
```

## Debugging Tips

### Check Which Server is Running

```bash
# Check monitor process
ps aux | grep "claude-mpm monitor"

# Check Python processes
ps aux | grep python | grep monitor
```

### Check Port Binding

```bash
# See what's listening on monitor port (default: 8765)
lsof -i :8765

# Should show Python process with UnifiedMonitorServer
```

### Enable Debug Logging

```bash
# Set environment variable for detailed logs
export CLAUDE_MPM_SOCKETIO_DEBUG=true
claude-mpm monitor start

# Or inline
CLAUDE_MPM_SOCKETIO_DEBUG=true claude-mpm monitor start
```

### Verify Dashboard Files Exist

```bash
# Check legacy dashboard
ls -la $(python -c "import claude_mpm; from pathlib import Path; print(Path(claude_mpm.__file__).parent / 'dashboard' / 'static')")

# Check Svelte dashboard
ls -la $(python -c "import claude_mpm; from pathlib import Path; print(Path(claude_mpm.__file__).parent / 'dashboard' / 'static' / 'svelte-build')")
```

### Test Route Availability

```bash
# Test health check (should work)
curl http://localhost:8765/api/health

# Test legacy dashboard (should return HTML)
curl http://localhost:8765/

# Test Svelte dashboard (should return HTML)
curl http://localhost:8765/svelte

# Test Svelte assets (should return JS)
curl http://localhost:8765/_app/version.json
```

## Development Workflow

### Adding a New Dashboard Feature

1. **Determine route type**:
   - HTTP endpoint? → Add to `UnifiedMonitorServer._setup_http_routes()`
   - Socket.IO event? → Add to either server (prefer `SocketIOServer` for reusability)

2. **Add route handler**:
   ```python
   # In UnifiedMonitorServer class
   async def _handle_new_feature(self, request):
       """Handle new feature request"""
       return web.json_response({"status": "ok"})

   async def _setup_http_routes(self):
       # ... existing routes ...
       self.app.router.add_get('/api/new-feature', self._handle_new_feature)
   ```

3. **Test locally**:
   ```bash
   # Restart server
   claude-mpm monitor stop
   claude-mpm monitor start

   # Test endpoint
   curl http://localhost:8765/api/new-feature
   ```

4. **Update dashboard frontend** (if needed):
   - Legacy: Edit `src/claude_mpm/dashboard/static/script.js`
   - Svelte: Edit Svelte components, rebuild with `npm run build`

### Modifying Static File Serving

1. **Locate static files**: `src/claude_mpm/dashboard/static/`

2. **Update serving logic**: `UnifiedMonitorServer._serve_dashboard()` or `_serve_svelte_dashboard()`

3. **Test file access**:
   ```bash
   curl http://localhost:8765/  # Legacy dashboard
   curl http://localhost:8765/svelte  # Svelte dashboard
   ```

### Adding Socket.IO Events

1. **Add event handler**:
   ```python
   # In SocketIOServer or UnifiedMonitorServer
   @self.sio.event
   async def my_custom_event(sid, data):
       """Handle custom event"""
       await self.sio.emit('response_event', {'result': 'processed'})
   ```

2. **Test with Socket.IO client**:
   ```python
   import socketio

   sio = socketio.Client()
   sio.connect('http://localhost:8765')
   sio.emit('my_custom_event', {'test': 'data'})
   ```

## Architecture Decision Records

### Why Two Servers?

**Context**: Originally had only `SocketIOServer`, but dashboard features required HTTP routes.

**Decision**: Created `UnifiedMonitorServer` as a wrapper instead of modifying `SocketIOServer`.

**Rationale**:
- Separation of concerns (Socket.IO vs HTTP serving)
- `SocketIOServer` can be used standalone for advanced use cases
- `UnifiedMonitorServer` provides user-friendly CLI integration
- Easier to maintain and test separately

**Consequences**:
- ✅ Clean separation of responsibilities
- ✅ Flexibility for different use cases
- ⚠️ Potential confusion about which server to modify
- ⚠️ Need for clear documentation (this document!)

### Why Package-Relative Paths?

**Context**: Initial implementation used `get_project_root()` for dashboard files.

**Decision**: Switched to `Path(claude_mpm.__file__).parent` for package-relative paths.

**Rationale**:
- Dashboard files are part of the package, not the user's project
- `get_project_root()` returns user's project directory (where `claude-mpm` is run)
- Package files need to work regardless of where command is executed

**Consequences**:
- ✅ Works correctly when installed via pip
- ✅ Dashboard accessible from any project directory
- ✅ Consistent behavior in development and production

## Related Documentation

- [Dashboard Development Guide](../developer/dashboard-development.md)
- [Socket.IO Event Reference](../developer/socketio-events.md)
- [Monitor Command Usage](../user/monitor-command.md)

---

**Last Updated**: 2025-12-11
**Maintainer**: Claude MPM Team
