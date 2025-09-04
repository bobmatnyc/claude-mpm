# Claude MPM Unified Monitor Daemon

## Overview

The Claude MPM Unified Monitor Daemon is a **single stable process** that provides comprehensive monitoring for Claude sessions. It combines HTTP dashboard serving, Socket.IO event handling, real AST analysis, and Claude Code hook ingestion into one cohesive service running on port 8765.

## Quick Start

### Starting the Monitor Daemon

```bash
# Start the unified monitor daemon
claude-mpm monitor start

# The dashboard will be available at:
# http://localhost:8765/
```

### Automatic Claude Code Hook Integration

The monitor daemon automatically receives events from Claude Code sessions - **no additional configuration needed**. When you run Claude Code with claude-mpm hooks installed, events are automatically sent to the monitor daemon via EventBus integration.

## Architecture

### Unified Monitor Daemon (Port 8765)

The unified monitor daemon provides **all monitoring functionality in a single stable process**:

```
┌─────────────────────────────────────────────────────────────┐
│                 Unified Monitor Daemon                     │
│                     (Port 8765)                            │
├─────────────────────────────────────────────────────────────┤
│  ✅ HTTP Server (aiohttp)                                  │
│  ✅ Socket.IO Server                                       │
│  ✅ Real AST Analysis (CodeTreeAnalyzer)                   │
│  ✅ Dashboard Serving                                      │
│  ✅ EventBus Integration                                   │
│  ✅ Claude Code Hook Ingestion                            │
│  ✅ Health Monitoring                                      │
│  ✅ Daemon Management                                      │
└─────────────────────────────────────────────────────────────┘
```

### Event Flow

1. **Claude Code Session** → **Claude Code Hooks** → **EventBus** → **Monitor Daemon** → **Dashboard UI**
2. Events are automatically captured by Claude Code hooks during operations
3. Hooks publish events to EventBus using `hook.{event_type}` topics
4. Monitor daemon's SocketIORelay subscribes to EventBus and forwards events to dashboard
5. Dashboard receives and displays events in real-time via Socket.IO

## Features

### Dashboard UI
- **Real-time Event Stream**: Live view of all Claude operations
- **Code Tree Visualization**: Interactive AST viewer for code analysis
- **Source Code Viewer**: Syntax-highlighted code display
- **Event Filtering**: Filter events by type, tool, or content
- **Session Tracking**: Monitor multiple Claude sessions

### Event Types
- `hook.pre_tool`: Before tool execution
- `hook.post_tool`: After tool execution
- `hook.pre_prompt`: Before sending prompts
- `hook.post_prompt`: After receiving responses
- `code.analyze`: Code analysis events
- `git.operations`: Git-related events

## Configuration

### Default Configuration

The monitor uses these defaults (defined in `src/claude_mpm/core/config.py`):

```python
"monitor_server": {
    "host": "localhost",
    "port": 8765,  # Default monitor port
    "enable_health_monitoring": True,
    "event_buffer_size": 2000,
    "client_timeout": 60
}
```

### Custom Configuration

Create or modify `.claude-mpm/configuration.yaml`:

```yaml
monitor:
  port: 8765
  host: localhost
  auto_open_browser: true
  event_retention: 1000  # Number of events to keep in memory
```

## CLI Commands

### Monitor Daemon Commands

The unified monitor daemon is the **only monitoring process** you need:

```bash
# Start the unified monitor daemon (foreground)
claude-mpm monitor start

# Start as background daemon
claude-mpm monitor start --daemon

# Stop the monitor daemon
claude-mpm monitor stop

# Restart the monitor daemon
claude-mpm monitor restart

# Check monitor daemon status
claude-mpm monitor status

# Check status with verbose output
claude-mpm monitor status --verbose
```

### Legacy Commands (Deprecated)

⚠️ **These commands are deprecated and should not be used:**

```bash
# DEPRECATED - Use 'claude-mpm monitor start' instead
python -m claude_mpm dashboard start

# DEPRECATED - Multiple competing servers
python -m claude_mpm socketio start
```

## API Endpoints

### GET /health
Health check endpoint:

```bash
curl http://localhost:8765/health
# Returns: {"status": "healthy", "service": "unified-monitor", "version": "1.0.0", "port": 8765}
```

### GET /api/directory
List directory contents for code tree:

```bash
curl "http://localhost:8765/api/directory?path=/path/to/project"
```

### GET /
Dashboard web interface:

```bash
# Open in browser
open http://localhost:8765/
```

**Note**: Claude Code hook events are automatically sent via EventBus integration - no manual API calls needed.

### WebSocket Events

Connect via Socket.IO client to receive real-time events:

```javascript
const socket = io('http://localhost:8765');

socket.on('connect', () => {
  console.log('Connected to monitor');
});

socket.on('hook.pre_tool', (data) => {
  console.log('Tool execution:', data);
});
```

## Troubleshooting

### Events Not Appearing

1. **Check monitor daemon is running**:
   ```bash
   claude-mpm monitor status
   ```

2. **Start the monitor daemon if not running**:
   ```bash
   claude-mpm monitor start
   ```

3. **Check Claude Code hooks are working**:
   ```bash
   # Check hook error log for recent events
   tail -f /tmp/claude-mpm-hook-error.log

   # Look for:
   # ✅ Published to EventBus: hook.pre_tool
   # ✅ HTTP POST returned status 200
   ```

4. **Verify EventBus integration**:
   - Monitor daemon logs should show "EventBus integration setup complete"
   - Hook events should appear as "Published to EventBus: hook.{event_type}"

### Port Conflicts

If port 8765 is in use:

```bash
# Find process using port
lsof -i :8765

# Kill process if needed
kill -9 <PID>

# Or use a different port
python -m claude_mpm dashboard start --port 8766
```

### Source Viewer Issues

The source viewer uses syntax highlighting for code display. If you see escaped HTML tags, clear your browser cache and reload the page.

## Development

### File Locations

- **Unified Monitor Daemon**: `src/claude_mpm/services/monitor/`
- **Monitor Server**: `src/claude_mpm/services/monitor/server.py`
- **Event Handlers**: `src/claude_mpm/services/monitor/handlers/`
- **Frontend Assets**: `src/claude_mpm/dashboard/static/`
- **CLI Commands**: `src/claude_mpm/cli/commands/monitor.py`

### Architecture Components

- **UnifiedMonitorDaemon**: Main daemon class with lifecycle management
- **UnifiedMonitorServer**: HTTP + Socket.IO server with EventBus integration
- **Event Handlers**: Code analysis, dashboard, and hook event processing
- **SocketIORelay**: Bridges EventBus events to Socket.IO clients

### Testing

```bash
# Test monitor daemon
claude-mpm monitor start
curl http://localhost:8765/health

# Test Claude Code hook integration
tail -f /tmp/claude-mpm-hook-error.log

# Run monitor tests
pytest tests/services/monitor/
```

## Related Documentation

- [Main Documentation](README.md) - Project overview
- [Development Guide](../CLAUDE.md) - Development guidelines and setup
- [Architecture](ARCHITECTURE.md) - System architecture details
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## Important Notes

- **Single Process**: The unified monitor daemon is the ONLY monitoring process needed
- **Automatic Integration**: Claude Code hooks automatically connect via EventBus - no configuration needed
- **Real AST Analysis**: Uses actual CodeTreeAnalyzer instead of mock data
- **Stable Foundation**: Built on proven aiohttp + Socket.IO architecture
- **Dashboard Ready**: Modern web browser with WebSocket support required
- **Always-On**: Can run continuously for monitoring multiple Claude sessions
- **Port 8765**: Single stable port for all monitoring functionality

## Migration from Legacy Commands

If you were using old commands, migrate to the unified daemon:

```bash
# OLD (deprecated):
python -m claude_mpm dashboard start
python -m claude_mpm socketio start

# NEW (unified):
claude-mpm monitor start
```