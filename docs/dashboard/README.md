# Claude MPM Dashboard and Monitoring System

The Claude MPM Dashboard provides real-time monitoring and visualization of your Claude sessions, offering comprehensive insights into agent behaviors, tool usage, file operations, and system events.

## Quick Start

### Starting the Dashboard

The easiest way to start monitoring your Claude sessions:

```bash
# Start Claude MPM with monitoring enabled
./claude-mpm --monitor

# This automatically:
# 1. Starts the Socket.IO server on port 8765
# 2. Opens the dashboard in your browser
# 3. Begins monitoring all Claude events
```

### Accessing the Dashboard

Once started, the dashboard is available at:
- **Primary Interface**: http://localhost:8765 (static files, no web server needed)
- **File Location**: `/src/claude_mpm/web/templates/index.html`

## Dashboard Features

### Real-Time Event Monitoring

The dashboard displays live events across four main tabs:

#### 📊 Events Tab
- **Hook Events**: User prompts, tool usage, responses
- **System Events**: Session start/stop, status changes
- **Agent Events**: Delegations, task completions
- **Memory Events**: Learning updates, context injections

#### 🤖 Agents Tab
- Active agent delegations
- Agent type classification (pm, researcher, ops, etc.)
- Task progress and status
- Agent memory operations

#### 🔧 Tools Tab
- Tool execution events
- File operations (Read, Write, Edit, etc.)
- Command executions
- Performance metrics

#### 📁 Files Tab
- Real-time file operations
- File paths and timestamps
- Operation types and summaries
- File access patterns

### Key Capabilities

- **Zero Latency**: Optimized hook handling ensures no impact on Claude responsiveness
- **Auto-Reconnection**: Dashboard automatically reconnects if connection is lost
- **Event Filtering**: Search and filter events by type, content, or timestamp
- **Session Isolation**: Filter events to specific Claude sessions
- **Export Functions**: Save event data for analysis
- **Live Statistics**: Real-time counters and metrics

## Architecture Overview

### Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude MPM    │───▶│   Hook Handler   │───▶│  Socket.IO      │
│    Session      │    │  (Optimized)     │    │   Server        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   Dashboard     │
                                                │   (Static)      │
                                                └─────────────────┘
```

### Key Files

- **Dashboard**: `/src/claude_mpm/web/templates/index.html`
- **Socket.IO Server**: `/src/claude_mpm/services/socketio_server.py`
- **Hook Handler**: `/src/claude_mpm/hooks/claude_hooks/hook_handler.py`
- **Static Assets**: `/src/claude_mpm/web/static/`

### Connection Flow

1. **Claude Session**: User starts Claude with `--monitor` flag
2. **Hook Registration**: Hook handler registers for Claude events
3. **Server Start**: Socket.IO server starts on port 8765
4. **Dashboard Connect**: Browser connects to Socket.IO server
5. **Event Flow**: Real-time events stream from Claude to dashboard

## Usage Examples

### Basic Monitoring

```bash
# Start monitoring a new session
./claude-mpm --monitor

# The dashboard opens automatically
# Navigate to different tabs to see various event types
```

### Session-Specific Filtering

```bash
# Filter dashboard to specific session
# Add ?session=SESSION_ID to the URL
http://localhost:8765?session=claude-session-abc123
```

### Advanced Filtering

In the dashboard interface:
- Use the search box to filter events by content
- Click event type badges to filter by category
- Use timestamp controls for time-based filtering

## Event Types

### Core Events

- **claude.hook.UserPromptSubmit**: User submits a prompt
- **claude.hook.PreToolUse**: Before tool execution
- **claude.hook.PostToolUse**: After tool completion
- **session.start**: New Claude session begins
- **session.end**: Claude session ends

### Agent Events

- **agent.delegation**: Agent receives a task
- **agent.completion**: Agent completes a task
- **agent.status**: Agent status changes

### Memory Events

- **memory:loaded**: Agent memory loaded from file
- **memory:created**: New agent memory created
- **memory:updated**: Learning added to memory
- **memory:injected**: Memory injected into context

### Tool Events

- **tool.execution**: Tool usage tracking
- **file.read**: File read operations
- **file.write**: File write operations
- **file.edit**: File edit operations

## Configuration

### Environment Variables

```bash
# Enable detailed logging (impacts performance)
export CLAUDE_MPM_HOOK_DEBUG=true

# Customize Socket.IO server port
export SOCKETIO_PORT=8765

# Override dashboard host
export DASHBOARD_HOST=localhost
```

### Hook Configuration

Hooks are automatically configured when using the `--monitor` flag. Manual configuration in `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "/path/to/hook_wrapper.sh"
      }]
    }]
  }
}
```

## Performance

### Optimizations

- **Connection Pooling**: Reuses Socket.IO connections
- **Micro-batching**: Groups high-frequency events
- **Circuit Breaker**: Graceful degradation during outages
- **Async Processing**: Non-blocking event handling

### Performance Impact

- **Hook Latency**: < 1ms additional latency per event
- **Memory Usage**: ~10MB for dashboard server
- **CPU Impact**: < 1% additional CPU usage
- **Network**: Minimal bandwidth usage for events

## Browser Compatibility

- **Chrome**: Full support (recommended)
- **Firefox**: Full support
- **Safari**: Full support
- **Edge**: Full support
- **Mobile**: Responsive design works on tablets

## Security Notes

- Dashboard runs locally only (localhost)
- No external network access required
- Event data stays on your machine
- Socket.IO uses standard web security practices

## Quick Tips

1. **Keyboard Shortcuts**:
   - `Ctrl+K`: Open search
   - `Ctrl+E`: Export events
   - `Ctrl+R`: Clear events

2. **Performance**:
   - Disable debug mode for production use
   - Clear events periodically for better performance
   - Use session filtering for focused monitoring

3. **Troubleshooting**:
   - Check browser console for connection errors
   - Verify port 8765 is available
   - Restart with `--monitor` flag if dashboard doesn't open

## Next Steps

- **User Guide**: See [USER_GUIDE.md](./USER_GUIDE.md) for detailed usage instructions
- **Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details
- **Development**: See [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) for customization
- **Troubleshooting**: See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- **Event Reference**: See [EVENT_REFERENCE.md](./EVENT_REFERENCE.md) for all event types

## Support

For issues or questions:
1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) first
2. Enable debug mode: `export CLAUDE_MPM_HOOK_DEBUG=true`
3. Check server logs for detailed error information
4. Verify network connectivity and port availability