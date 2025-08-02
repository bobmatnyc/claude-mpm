# Claude MPM Dashboard Documentation

The Claude MPM Dashboard provides real-time monitoring of Claude MPM sessions with multiple dashboard options, including the new Socket.IO-enhanced dashboard and the legacy WebSocket dashboard. This documentation covers the complete architecture, implementation details, and optimization strategies.

## Table of Contents

1. [Overview](#overview)
2. [Dashboard Options](#dashboard-options)
3. [Getting Started](#getting-started)
4. [Architecture](#architecture)
5. [Migration Guide](#migration-guide)
6. [Advanced Usage](#advanced-usage)
7. [Documentation](#documentation)

## Overview

The Claude MPM Dashboard ecosystem provides comprehensive real-time monitoring of Claude MPM sessions, including:

- Claude process hook events (UserPromptSubmit, PreToolUse, PostToolUse)
- Session lifecycle management and status
- Agent delegation and task execution
- Todo list updates and progress tracking
- Memory system operations and learning events
- Real-time logging and error monitoring
- System events and health status

### Key Features

- **Real-time Updates**: Events appear instantly via Socket.IO or WebSocket connections
- **Multi-namespace Organization**: Events organized by category for better filtering
- **Session Isolation**: View events from specific sessions to avoid cross-instance pollution
- **Zero Latency**: Optimized hook handling ensures no keystroke latency
- **Persistent Server**: Server runs independently of Claude sessions
- **Auto-reconnection**: Dashboard automatically reconnects if connection is lost
- **Interactive Filtering**: Search, filter, and export event data
- **Admin UI Integration**: Professional admin interface for detailed monitoring

## Dashboard Options

### 🚀 Socket.IO Dashboard (Recommended)

**File**: `src/claude_mpm/web/templates/index.html` (served at `/dashboard`)

The new Socket.IO-based dashboard with enhanced features:

- **Better Reliability**: Automatic reconnection with exponential backoff
- **Namespace Organization**: Events organized by type (`/system`, `/session`, `/claude`, etc.)
- **Enhanced Filtering**: Multi-level filtering by namespace, event type, and content
- **Admin UI Support**: Integrates with Socket.IO Admin UI for detailed monitoring
- **Modern Interface**: Clean, responsive design with dark mode
- **Export Functionality**: Export filtered events to JSON
- **Keyboard Shortcuts**: Ctrl+K (search), Ctrl+E (export), Ctrl+R (clear)

### 🔧 Legacy WebSocket Dashboard

**File**: `scripts/claude_mpm_dashboard.html`

The original WebSocket-based dashboard:

- **Simple Setup**: Direct WebSocket connection
- **Basic Filtering**: Session-based filtering
- **Lightweight**: Minimal dependencies
- **Stable**: Well-tested implementation

## Getting Started

### Quick Start with Socket.IO Dashboard (Recommended)

1. **Launch Socket.IO Dashboard**:
   ```bash
   python scripts/launch_socketio_dashboard.py
   ```
   This will:
   - Install Node.js dependencies if needed
   - Start the Socket.IO server on port 3000
   - Open the dashboard in your browser

2. **Start Claude MPM**:
   ```bash
   ./claude-mpm --monitor
   ```

3. **Access Interfaces**:
   - Dashboard: http://localhost:3000/dashboard
   - Admin UI: http://localhost:3000/admin

### Alternative: Legacy WebSocket Dashboard

1. **Start WebSocket Server**:
   ```bash
   python scripts/websocket_server_production.py
   ```

2. **Launch Claude MPM**:
   ```bash
   ./claude-mpm run --monitor
   ```

3. **Open Dashboard**:
   ```bash
   open scripts/claude_mpm_dashboard.html?port=8765
   ```

### Session-Specific Filtering

For both dashboards, you can filter to specific sessions:

**Socket.IO Dashboard**:
```
http://localhost:3000/dashboard?session=your-session-id&autoconnect=true
```

**Legacy Dashboard**:
```
file:///path/to/claude_mpm_dashboard.html?port=8765&session=your-session-id
```

## Architecture

### Socket.IO Architecture (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                    Socket.IO Server                         │
│                   (Node.js + Socket.IO)                    │
├─────────────────────────────────────────────────────────────┤
│  Namespaces:                                               │
│  • /system    - Server status, connections                 │
│  • /session   - Session lifecycle events                   │
│  • /claude    - Claude process events                      │
│  • /agent     - Agent delegation events                    │
│  • /hook      - Hook execution events                      │
│  • /todo      - Todo list updates                          │
│  • /memory    - Memory system events                       │
│  • /log       - Real-time logging                          │
└─────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    ▼                         ▼                         ▼
┌──────────────┐    ┌──────────────┐         ┌──────────────┐
│   Dashboard  │    │   Admin UI   │         │ Custom       │
│  (HTML/JS)   │    │  (Socket.IO) │         │ Clients      │
└──────────────┘    └──────────────┘         └──────────────┘
```

### Legacy WebSocket Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude MPM     │────▶│   Hook Handler  │────▶│ WebSocket       │
│    Session      │     │  (Optimized)    │     │   Server        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Dashboard     │
                                                 │   (HTML/JS)     │
                                                 └─────────────────┘
```

### Communication Flow

**Socket.IO Flow**:
1. Claude MPM triggers an event (e.g., agent delegation)
2. Socket.IO server receives event via HTTP/WebSocket client
3. Server broadcasts to appropriate namespace (`/agent`, `/session`, etc.)
4. Dashboard clients subscribed to namespace receive the event
5. Dashboard displays event with namespace-specific styling

**Legacy WebSocket Flow**:
1. Claude MPM triggers a hook (e.g., user submits a prompt)
2. Hook handler receives event data via stdin
3. Handler processes event and sends to WebSocket server
4. WebSocket server broadcasts to all connected dashboard clients
5. Dashboard displays the event in real-time

## Migration Guide

### From Legacy WebSocket to Socket.IO

The Socket.IO implementation is designed to be backward compatible, but here's how to migrate:

1. **Update Launch Method**:
   ```bash
   # Old way
   python scripts/websocket_server_production.py &
   ./claude-mpm run --monitor
   
   # New way
   python scripts/launch_socketio_dashboard.py
   ./claude-mpm --monitor
   ```

2. **Update Bookmarks**:
   - Old: `file:///path/to/claude_mpm_dashboard.html?port=8765`
   - New: `http://localhost:3000/dashboard`

3. **Custom Clients**:
   - Replace WebSocket client code with Socket.IO client
   - Update to use namespaces instead of single connection
   - See [Socket.IO Guide](./SOCKETIO_GUIDE.md#custom-client-integration)

### Backward Compatibility

The Socket.IO server maintains compatibility with existing hooks and integrations:

- Hook handlers continue to work unchanged
- Legacy WebSocket clients can still connect to port 8765
- Environment variables remain the same
- Session filtering works identically

## Advanced Usage

### Custom Event Broadcasting

**Socket.IO**:
```python
from claude_mpm.services.websocket_server import get_socketio_server

server = get_socketio_server()
server.emit_event('/system', 'custom_event', {
    "message": "Custom data",
    "timestamp": "2025-01-31T14:30:00Z"
})
```

**Legacy WebSocket**:
```python
from claude_mpm.services.websocket_server import get_websocket_server

server = get_websocket_server()
server.broadcast_event("custom.event", {
    "message": "Custom data"
})
```

### Multiple Dashboard Sessions

Run multiple dashboard instances for different purposes:

```bash
# Main monitoring dashboard
python scripts/launch_socketio_dashboard.py --port 3000

# Development dashboard on different port
python scripts/launch_socketio_dashboard.py --port 3001 --admin-only

# Access both
# http://localhost:3000/dashboard
# http://localhost:3001/admin
```

## Documentation

### Detailed Guides

- **[Socket.IO Implementation Guide](./SOCKETIO_GUIDE.md)** - Comprehensive guide to the new Socket.IO system
  - Architecture and namespace design
  - API reference with examples
  - Custom client integration
  - Configuration and security
  - Troubleshooting and performance

- **[Legacy WebSocket Documentation](./websocket-hooks.md)** - Original WebSocket implementation
  - WebSocket architecture details
  - Hook handling optimization
  - Legacy client examples

### Quick Reference Files

- **[Claude Code Hook Handling](./claude-code-hooks.md)** - How hooks are processed
- **[Hook Server Details](./hook-server.md)** - WebSocket server implementation  
- **[Dashboard Implementation](./dashboard-implementation.md)** - UI implementation details
- **[Latency Optimization](./latency-optimization.md)** - Performance improvements
- **[Troubleshooting Guide](./troubleshooting.md)** - Common issues and solutions

## Configuration

### Environment Variables

- `CLAUDE_MPM_SOCKETIO_TOKEN`: Authentication token for Socket.IO connections
- `CLAUDE_MPM_HOOK_DEBUG`: Enable debug logging (impacts performance)
- `SOCKETIO_PORT`: Override default Socket.IO port (default: 3000)

### Hook Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "/path/to/hook_wrapper.sh"
      }]
    }],
    "PreToolUse": [...],
    "PostToolUse": [...]
  }
}
```

## Key Files

### Socket.IO Implementation
- `src/claude_mpm/web/templates/index.html` - Modular Socket.IO dashboard (served at `/dashboard`)
- `scripts/launch_socketio_dashboard.py` - Socket.IO server launcher
- `scripts/socketio_server.js` - Node.js Socket.IO server
- `src/claude_mpm/services/websocket_server.py` - Python Socket.IO integration
- `src/claude_mpm/core/websocket_handler.py` - Socket.IO logging handler

### Legacy WebSocket Implementation
- `scripts/claude_mpm_dashboard.html` - Original WebSocket dashboard
- `scripts/websocket_server_production.py` - Production WebSocket server
- `scripts/websocket_server_manager.py` - Server manager with auto-restart
- `src/claude_mpm/hooks/claude_hooks/hook_handler.py` - Optimized hook handler

### Documentation
- `docs/developer/dashboard/SOCKETIO_GUIDE.md` - Complete Socket.IO guide
- `docs/developer/dashboard/README.md` - This file
- `docs/developer/dashboard/troubleshooting.md` - Troubleshooting guide

## Getting Help

1. **Socket.IO Issues**: See [SOCKETIO_GUIDE.md](./SOCKETIO_GUIDE.md#troubleshooting)
2. **Legacy WebSocket Issues**: See [troubleshooting.md](./troubleshooting.md)
3. **Performance Problems**: See [latency-optimization.md](./latency-optimization.md)
4. **Configuration Questions**: Check environment variables and hook configuration above

For additional support, check the server logs and enable debug mode for detailed troubleshooting information.