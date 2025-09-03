# Claude MPM Monitor & Dashboard System

## Overview

The Claude MPM Monitor provides real-time event tracking and visualization for Claude sessions. It consists of a unified server that handles both the web dashboard UI and Socket.IO event monitoring on port 8765.

## Quick Start

### Starting the Dashboard

```bash
# Start the dashboard server (includes monitoring)
python -m claude_mpm dashboard start

# The dashboard will be available at:
# http://localhost:8765/
```

### Enabling Event Monitoring in Claude Sessions

To receive events in the dashboard, start Claude MPM with the `--monitor` flag:

```bash
# Start Claude with monitoring enabled
claude-mpm run --monitor

# Or specify a custom port
claude-mpm run --monitor --websocket-port 8765
```

## Architecture

### Unified Server (Port 8765)

The dashboard service provides:
- **Web UI**: Interactive dashboard for visualizing events
- **Socket.IO Server**: Real-time event streaming
- **HTTP API**: RESTful endpoints for event submission
- **Static Assets**: JavaScript, CSS, and HTML files

### Event Flow

1. **Claude Session** → Hook Service → Monitor API → Dashboard UI
2. Events are captured by hooks during Claude operations
3. When `--monitor` is enabled, events are forwarded to port 8765
4. The dashboard receives and displays events in real-time

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

### Dashboard Commands

```bash
# Start the dashboard
python -m claude_mpm dashboard start

# Stop the dashboard
python -m claude_mpm dashboard stop

# Check dashboard status
python -m claude_mpm dashboard status

# Open dashboard in browser (starts if needed)
python -m claude_mpm dashboard open
```

### Monitor Commands (Legacy)

Note: The `monitor` command starts a lightweight Socket.IO server without the UI. Use `dashboard` instead for full functionality.

```bash
# Start monitor on specific port
python -m claude_mpm monitor port 8765

# Check monitor status
python -m claude_mpm monitor status
```

## API Endpoints

### POST /api/events
Submit events to the dashboard:

```bash
curl -X POST http://localhost:8765/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event": "hook.pre_tool",
    "data": {
      "tool": "bash",
      "params": {"command": "ls -la"},
      "timestamp": "2025-01-03T12:00:00Z"
    }
  }'
```

### GET /api/directory/list
List directory contents for code tree:

```bash
curl "http://localhost:8765/api/directory/list?path=/path/to/project"
```

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

1. **Check Claude was started with monitoring**:
   ```bash
   # This WON'T send events:
   claude-mpm run
   
   # This WILL send events:
   claude-mpm run --monitor
   ```

2. **Verify dashboard is running**:
   ```bash
   python -m claude_mpm dashboard status
   ```

3. **Test event submission manually**:
   ```bash
   curl -X POST http://localhost:8765/api/events \
     -H "Content-Type: application/json" \
     -d '{"event": "test", "data": {"message": "Test event"}}'
   ```

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

- **Dashboard Server**: `src/claude_mpm/services/dashboard/`
- **Socket.IO Server**: `src/claude_mpm/services/socketio/`
- **Frontend Assets**: `src/claude_mpm/dashboard/static/`
- **Event Handlers**: `src/claude_mpm/services/socketio/handlers/`

### Adding New Event Types

1. Define event in `src/claude_mpm/services/events/types.py`
2. Create handler in `src/claude_mpm/services/socketio/handlers/`
3. Register handler in `src/claude_mpm/services/socketio/server/main.py`

### Testing

```bash
# Run monitor tests
pytest tests/services/dashboard/
pytest tests/services/socketio/

# Test Socket.IO connection
python scripts/test-dashboard-connection.py
```

## Related Documentation

- [Main Documentation](README.md) - Project overview
- [Development Guide](../CLAUDE.md) - Development guidelines and setup
- [Architecture](ARCHITECTURE.md) - System architecture details
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## Important Notes

- The dashboard requires a modern web browser with WebSocket support
- Events are buffered in memory (default: 2000 events)
- The monitor runs independently from Claude sessions
- Multiple Claude sessions can connect to the same monitor
- The dashboard can be left running continuously for monitoring multiple sessions