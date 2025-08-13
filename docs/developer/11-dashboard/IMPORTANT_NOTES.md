# Important Notes - Socket.IO Dashboard

This document contains critical information to prevent confusion between different dashboard implementations and ensure proper understanding of the Socket.IO dashboard architecture.

## CRITICAL: This is the LIVE Socket.IO Dashboard

### What This IS

✅ **Production Socket.IO Dashboard**
- Real-time monitoring system using Socket.IO protocol
- Integrated with Claude Code hook system
- Browser-based interface at http://localhost:8765
- Static HTML/CSS/JavaScript files (no web server needed)
- Event-driven architecture with WebSocket communication

✅ **Current Active Implementation**
- Used by `./claude-mpm --monitor` command
- Connected to actual Claude Code sessions
- Processes real tool events and file operations
- Supports multiple concurrent dashboard connections

✅ **Mature Feature Set**
- File operation tracking (Files tab)
- Tool execution monitoring (Tools tab)
- Agent activity visualization (Agents tab)
- Real-time event streaming (Events tab)
- Automatic reconnection handling
- Session-based event filtering

### What This is NOT

❌ **Not a Prototype**
- This is not experimental or proof-of-concept code
- Not a temporary or testing implementation
- Not superseded by other dashboard implementations

❌ **Not WebSocket-only**
- Uses Socket.IO protocol (which includes WebSocket but adds features)
- Not a raw WebSocket implementation
- Not limited to WebSocket transport only

❌ **Not a Configuration Dashboard**
- This is not the configuration management UI (ConfigScreenV2)
- Not for editing agent configurations or project settings
- Not the MPM Manager App terminal interface

## Architectural Distinctions

### Socket.IO Dashboard vs Other Implementations

| Feature | Socket.IO Dashboard | Config Dashboard | Terminal UI |
|---------|-------------------|------------------|-------------|
| **Purpose** | Real-time monitoring | Configuration management | CLI interaction |
| **Protocol** | Socket.IO/WebSocket | Local IPC | Terminal I/O |
| **Interface** | Web browser | GUI application | Command line |
| **Data Source** | Claude Code hooks | Project files | User input |
| **Use Case** | Monitoring sessions | Managing projects | Running commands |

### File Location Clarity

**Socket.IO Dashboard Files**:
```
src/claude_mpm/dashboard/
├── templates/index.html          # Main dashboard page
├── static/js/dashboard.js         # Main dashboard logic
├── static/js/components/
│   ├── file-tool-tracker.js      # File operation tracking
│   ├── event-processor.js        # Event correlation
│   └── agent-inference.js        # Agent identification
└── static/css/                   # Dashboard styling
```

**NOT the Configuration Dashboard**:
```
src/claude_mpm/ui/
└── config_screen_v2.py           # Configuration management UI
```

## Event Flow Specifics

### Claude Code Hook Integration

The Socket.IO dashboard depends entirely on Claude Code hooks:

```
Claude Code Tool Execution
    ↓
Hook Triggers (UserPromptSubmit, PreToolUse, PostToolUse)
    ↓
hook_wrapper.sh processes event
    ↓
Event sent to Socket.IO server (port 8765)
    ↓
Server broadcasts to connected dashboard clients
    ↓
Dashboard updates UI in real-time
```

**Key Point**: Without Claude Code hooks configured, the dashboard will show no events.

### Supported Event Types

The dashboard processes these specific event types:

**Hook Events**:
- `UserPromptSubmit`: User enters prompt in Claude
- `PreToolUse`: Before tool execution
- `PostToolUse`: After tool completion
- `SubagentStop`: Agent task completion

**Tool Events**:
- File operations: Read, Write, Edit, MultiEdit, NotebookEdit
- Search operations: Grep, Glob
- System operations: LS, Bash
- **Case insensitive**: Handles both "Read" and "read"

**Session Events**:
- Session start/stop
- Status changes
- Error conditions

### File Operations Dependency

File operations in the Files tab depend on:

1. **Tool Events**: Must have `tool_name` field
2. **File Parameters**: Must contain file path in `tool_parameters`
3. **Event Pairing**: Pre/post events must correlate properly
4. **Case Handling**: Tool names processed case-insensitively

## Server Modes and Deployment

### Two Operational Modes

#### 1. Direct Mode (Default)
```bash
./claude-mpm --monitor
```
- Socket.IO server runs in same process
- Dashboard opens automatically
- Server stops when Claude MPM exits

#### 2. Exec Mode (Advanced)
```bash
# Start persistent server
./scripts/socketio_server_manager.py

# Connect Claude sessions
./claude-mpm run -i "prompt" --exec
```
- Persistent server in separate process
- Multiple Claude sessions can connect
- Server persists between sessions

### Port and Connectivity

**Default Configuration**:
- **Port**: 8765
- **Host**: 127.0.0.1 (localhost only)
- **Protocol**: HTTP with Socket.IO upgrade to WebSocket
- **Security**: Local access only, no external network exposure

**URL Access**:
- Main dashboard: http://localhost:8765
- Socket.IO endpoint: http://localhost:8765/socket.io/
- Static assets: http://localhost:8765/static/

## Critical Dependencies

### Required Python Packages

```bash
# Essential for Socket.IO functionality
pip install python-socketio>=5.8.0
pip install aiohttp>=3.8.0

# Or install with monitoring extras
pip install -e ".[monitor]"
```

**Without these packages**: Socket.IO dashboard will not function.

### Browser Requirements

**Supported Browsers**:
- Chrome 120+ ✅
- Firefox 115+ ✅ 
- Safari 16+ ✅
- Edge 120+ ✅

**Required Browser Features**:
- WebSocket support
- JavaScript ES6+
- Local Storage API
- Modern CSS Grid/Flexbox

### Claude Code Integration Requirements

**Hook Configuration**: Must have properly configured hooks in `.claude/settings.json`:

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

**Hook Script**: The `hook_wrapper.sh` must be executable and properly configured to forward events to Socket.IO server.

## Performance Characteristics

### Latency Expectations

- **Hook Processing**: <1ms additional latency per Claude operation
- **Event Transmission**: <5ms from hook to dashboard
- **UI Updates**: <10ms from event receipt to display
- **Memory Usage**: ~10MB for dashboard server process

### Scalability Limits

- **Concurrent Dashboards**: 10-20 simultaneous browser connections
- **Event Rate**: 1000+ events/second sustained
- **Session Duration**: Tested up to 8+ hours continuous operation
- **Event History**: Cleared on restart (no persistent storage)

### Resource Impact

**On Claude Code Performance**:
- Negligible impact on tool execution speed
- <1% additional CPU usage
- No blocking of Claude operations

**Browser Resource Usage**:
- ~50MB memory for dashboard page
- Minimal CPU usage during idle
- Network usage only for event data (very low bandwidth)

## Debugging and Development Notes

### Common Development Pitfalls

❌ **Don't Assume WebSocket-only**: This is Socket.IO, which provides additional features over raw WebSocket

❌ **Don't Ignore Case Sensitivity**: Tool names can be "Read" or "read" - handle both

❌ **Don't Expect Persistent Storage**: Events are cleared on restart

❌ **Don't Mix with Other Dashboards**: This is specifically the Socket.IO real-time monitoring dashboard

### Debug Mode Activation

```bash
# Enable comprehensive debug logging
export CLAUDE_MPM_HOOK_DEBUG=true
export SOCKETIO_DEBUG=true
./claude-mpm --monitor
```

### Log Interpretation

**Successful Operation Indicators**:
```
✅ "Socket.IO server started on port 8765"
✅ "Client connected: <client_id>"  
✅ "Event forwarded to dashboard"
✅ "Broadcasting event to N clients"
```

**Problem Indicators**:
```
❌ "Port 8765 already in use"
❌ "Failed to connect to Socket.IO server"
❌ "Hook execution failed"
❌ "No clients connected for event broadcast"
```

## Integration Guidelines

### When to Use This Dashboard

✅ **Use for**:
- Real-time monitoring of Claude Code sessions
- Debugging tool execution and file operations
- Understanding agent activity patterns
- Performance analysis of Claude operations
- Development and testing of Claude Code workflows

❌ **Don't Use for**:
- Configuring agents or projects (use ConfigScreenV2)
- Managing MPM installations (use terminal UI)
- Persistent logging or analytics (use dedicated logging)
- Production monitoring (this is for development/debugging)

### Integration with Other Components

**Works With**:
- Claude Code desktop application
- Claude MPM command-line interface
- Hook system and event processing
- Agent inference and memory systems

**Independent Of**:
- Configuration management UI
- Terminal-based interfaces  
- Project file management
- Version control operations

## Testing and Validation

### Verification Steps

1. **Server Startup**: Verify Socket.IO server starts on port 8765
2. **Dashboard Access**: Confirm browser can load http://localhost:8765
3. **Event Flow**: Use test script to validate event processing
4. **File Operations**: Verify Files tab shows file operations correctly
5. **Real Integration**: Test with actual Claude Code session

### Test Script Usage

```bash
# Always test with provided script first
python scripts/test_dashboard_file_viewer.py

# Expected: 8 file operations in Files tab
# Expected: 16 events total (8 pre + 8 post)
# Expected: No JavaScript errors in browser console
```

### Troubleshooting Checklist

Before reporting issues:

1. ✅ Socket.IO dependencies installed
2. ✅ Port 8765 available
3. ✅ Claude Code hooks configured
4. ✅ Dashboard accessible in browser
5. ✅ Test script produces expected results
6. ✅ Browser console shows no JavaScript errors

## Future Development Considerations

### Planned Enhancements

- **Event Persistence**: Optional storage of event history
- **Advanced Filtering**: More sophisticated event filtering
- **Performance Metrics**: Detailed timing and performance analysis
- **Export Functionality**: Save event data for offline analysis

### API Stability

The Socket.IO dashboard API is considered stable for:
- Event format structure
- Socket.IO endpoint URLs
- JavaScript component interfaces
- Basic dashboard functionality

### Backward Compatibility

Future versions will maintain compatibility with:
- Existing hook event formats
- Browser client connections
- Basic dashboard functionality
- File operation tracking

## Documentation References

- **[Architecture Overview](./SOCKETIO_ARCHITECTURE.md)**: Technical architecture details
- **[File Viewer Implementation](./FILE_VIEWER_IMPLEMENTATION.md)**: File tracking specifics
- **[Troubleshooting](./TROUBLESHOOTING.md)**: Problem resolution
- **[Testing & Debugging](./TESTING_DEBUGGING.md)**: Validation procedures
- **[Main Dashboard README](./README.md)**: User-focused documentation