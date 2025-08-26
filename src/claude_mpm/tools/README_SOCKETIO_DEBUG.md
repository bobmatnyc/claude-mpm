# SocketIO Debug Tool

A professional debugging tool for monitoring and analyzing SocketIO events in the claude-mpm dashboard.

## Overview

The SocketIO debug tool is an essential utility for developers working on the claude-mpm dashboard. It provides real-time monitoring, filtering, and analysis of all SocketIO events flowing through the system.

## Features

### 🔍 Real-Time Event Monitoring
- Live streaming of all SocketIO events
- Color-coded output with event type icons
- Automatic reconnection with exponential backoff
- Connection health monitoring with latency tracking

### 📊 Event Analysis
- Aggregated statistics and summaries
- Event rate calculation (events/second)
- Tool usage tracking
- Session monitoring and tracking
- Pattern detection for event bursts and gaps

### 🎯 Flexible Display Modes
- **Live Mode** (default): Real-time scrolling event display
- **Summary Mode**: Aggregated statistics and counts
- **Raw Mode**: Unformatted JSON output for debugging
- **Pretty Mode**: Enhanced formatting with colors and icons
- **Filtered Mode**: Show only specific event types

### 💾 Data Export
- Save events to JSONL format for analysis
- Quiet mode for background logging
- Configurable output paths

## Installation

The tool is included with claude-mpm and requires no additional installation.

## Usage

### Basic Commands

```bash
# Monitor all events in real-time
claude-mpm debug socketio

# Show event summary statistics
claude-mpm debug socketio --summary

# Filter specific event types
claude-mpm debug socketio --filter PreToolUse PostToolUse

# Save events to file
claude-mpm debug socketio --output events.jsonl

# Quiet mode for scripts
claude-mpm debug socketio --quiet --output events.jsonl
```

### Connection Options

```bash
# Connect to specific server
claude-mpm debug socketio --host localhost --port 8765

# Configure reconnection
claude-mpm debug socketio --max-reconnect 20 --reconnect-delay 2.0
```

### Display Modes

```bash
# Live monitoring (default)
claude-mpm debug socketio --live

# Statistical summary
claude-mpm debug socketio --summary

# Raw JSON output
claude-mpm debug socketio --raw

# Enhanced pretty output
claude-mpm debug socketio --pretty
```

## Output Format Examples

### Live Mode Output
```
╭─────────────────────────────────────────╮
│     SocketIO Event Monitor v1.0         │
├─────────────────────────────────────────┤
│ Server: localhost:8765                  │
│ Status: ✅ Connected                    │
│ Latency: 12ms                          │
│ Uptime: 00:05:42                       │
╰─────────────────────────────────────────╯

[14:23:45.123] 🔧 PreToolUse
├─ Tool: Read
├─ Session: abc-123-def
└─ Args: {"file_path": "README.md"}

[14:23:46.456] ✅ PostToolUse  
├─ Tool: Read
├─ Duration: 1.33s
└─ Success: true
```

### Summary Mode Output
```
SOCKETIO EVENT MONITOR SUMMARY
=====================================
Server: localhost:8765
Status: ✅ Connected
Latency: 15ms
Uptime: 00:10:23
-------------------------------------
Total Events: 147
Events/Second: 2.4
Active Sessions: 3
-------------------------------------
Event Types:
  PreToolUse: 42
  PostToolUse: 41
  SubagentStart: 18
  SubagentStop: 17
-------------------------------------
Tool Usage:
  Read: 31
  Write: 22
  Edit: 18
  Task: 15
```

## Event Types

Common event types you'll encounter:

- **Start/Stop**: Main session lifecycle events
- **SubagentStart/SubagentStop**: Subagent delegation events
- **PreToolUse/PostToolUse**: Tool invocation tracking
- **MemoryUpdate**: Memory system changes
- **ConfigChange**: Configuration updates
- **Error/Warning**: System issues and alerts

## Integration with Dashboard

The debug tool connects to the same SocketIO server as the dashboard, allowing you to:

1. Monitor events while using the dashboard
2. Debug event flow issues
3. Verify event data structure
4. Track performance metrics

## Advanced Usage

### Filtering Multiple Event Types
```bash
claude-mpm debug socketio --filter Start Stop SubagentStart SubagentStop
```

### Combining with Other Tools
```bash
# Monitor and analyze with jq
claude-mpm debug socketio --raw | jq '.data.tool'

# Save and analyze offline
claude-mpm debug socketio --output events.jsonl
cat events.jsonl | jq 'select(.type == "PreToolUse")'
```

### Background Monitoring
```bash
# Run in background with output
nohup claude-mpm debug socketio --quiet --output /var/log/claude-events.jsonl &
```

## Troubleshooting

### Connection Issues
- Ensure SocketIO server is running: `claude-mpm monitor status`
- Check port availability: `claude-mpm debug connections`
- Verify firewall settings for localhost connections

### No Events Appearing
- Start a Claude session in another terminal: `claude-mpm run`
- Check server health: `claude-mpm debug connections --check-health`
- Verify event broadcasting is enabled

### Performance Impact
The debug tool has minimal performance impact:
- Passive event listening only
- Efficient event processing
- Optional file writing in separate thread

## Development

### Extending the Tool

The tool is designed to be extensible. Key files:

- `/src/claude_mpm/tools/socketio_debug.py` - Main tool implementation
- `/src/claude_mpm/cli/commands/debug.py` - CLI command integration
- `/src/claude_mpm/cli/parsers/debug_parser.py` - Argument parsing

### Adding New Features

1. Event filtering by regex patterns
2. Event replay from saved files
3. Performance profiling integration
4. Custom event handlers

## Related Commands

- `claude-mpm monitor status` - Check SocketIO server status
- `claude-mpm monitor start` - Start SocketIO server
- `claude-mpm debug connections` - Show active connections
- `claude-mpm run --websocket` - Run with SocketIO enabled

## Support

For issues or feature requests, please refer to the main claude-mpm documentation or submit an issue on the project repository.