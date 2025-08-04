# Claude MPM Monitoring Dashboard

The monitoring dashboard provides real-time visibility into Claude MPM's multi-agent system.

## Overview

The Socket.IO-based monitoring dashboard allows you to:
- Track agent activity in real-time
- View file operations and changes
- Monitor tool usage
- Manage sessions
- Inspect git diffs for code changes

## Starting the Monitor

### Basic Usage
```bash
claude-mpm run --monitor
```

This will:
1. Start the Socket.IO server on port 8765
2. Open the dashboard in your browser
3. Begin streaming events in real-time

### Custom Port
```bash
claude-mpm run --monitor --websocket-port 8080
```

## Dashboard Features

### 1. Connection Status
- Shows real-time connection status
- Displays connected clients count
- Auto-reconnects on connection loss

### 2. Session Management
- **Session Dropdown**: Select and filter by session
- **Working Directory**: Set per-session working directories
- **Git Branch Display**: Shows current branch for working directory

### 3. Event Tabs

#### Events Tab
- Real-time event stream
- Filter by event type (session, claude, agent, hook, todo, memory, log)
- Search functionality
- Color-coded by event type

#### Agents Tab
- Track agent delegations
- View agent task details
- See agent performance metrics

#### Tools Tab
- Monitor tool usage (Read, Write, Edit, Bash, etc.)
- View tool parameters and results
- Track tool execution time

#### Files Tab
- Track all file operations
- View git diffs for changes
- Filter by operation type
- Session-aware file tracking

### 4. Detail Views
Click any event, agent, tool, or file to see detailed information including:
- Full event data
- Structured view
- Raw JSON data
- Git diffs (for file operations)

## Working Directory Management

### Per-Session Directories
Each session can have its own working directory:

1. **Set Directory**: Click the 📁 button next to the directory path
2. **Auto-sync**: Directory updates when switching sessions
3. **Persistence**: Directories are saved per session

### Git Integration
- Git branch is automatically detected and displayed
- Git diffs work across different project directories
- File paths are resolved relative to session directory

## Git Diff Viewer

### Features
- Syntax highlighting for diff output
- Shows commit information
- Displays change metadata
- Copy diff to clipboard

### Supported Operations
- View diffs for Write operations
- View diffs for Edit operations
- Works with timestamp-based lookups
- Handles cross-repository files

## Advanced Features

### Keyboard Navigation
- **Up/Down arrows**: Navigate through items
- **Enter**: Select item
- **Escape**: Clear selection

### Export Functionality
Export session data for analysis:
```javascript
// In browser console
dashboard.exportEvents()
```

### Real-time Metrics
- Events per minute
- Total event count
- Unique event types
- Error count

## Architecture

### Components
- **Socket.IO Server**: Handles real-time communication
- **Event Store**: In-memory event storage
- **Session Manager**: Tracks and manages sessions
- **File Watcher**: Monitors file operations

### Event Flow
1. Claude/Agents emit events via hooks
2. Hook handler sends to Socket.IO server
3. Server broadcasts to connected clients
4. Dashboard updates in real-time

## Troubleshooting

### Connection Issues
- **Port conflicts**: Try different port with `--websocket-port`
- **Firewall**: Ensure port is not blocked
- **CORS**: Dashboard must be accessed via http://localhost

### Performance
- **Large sessions**: Filter by event type to improve performance
- **Memory usage**: Server stores last 10,000 events
- **Browser slowdown**: Clear events with refresh

### Git Diff Issues
- **No git history**: Ensure file is in a git repository
- **Wrong directory**: Check session working directory
- **Timestamp mismatch**: Diff uses closest commit to timestamp

## Configuration

### Environment Variables
```bash
# Custom default port
export CLAUDE_MPM_MONITOR_PORT=9000

# Disable auto-browser opening
export CLAUDE_MPM_NO_BROWSER=1
```

### Settings
Configure in `~/.claude-mpm/settings.json`:
```json
{
  "monitor": {
    "port": 8765,
    "auto_open": true,
    "event_limit": 10000
  }
}
```

## Security Considerations

- Dashboard binds to localhost only
- No authentication (local use only)
- Events may contain sensitive data
- Use in trusted environments only

## API Reference

### Socket.IO Events

#### Client -> Server
- `get_status`: Request server status
- `get_history`: Request event history
- `get_git_branch`: Get git branch for directory

#### Server -> Client
- `claude_event`: New event broadcast
- `status`: Server status update
- `git_branch_response`: Git branch result
- `history`: Historical events

### REST Endpoints
- `GET /health`: Health check
- `GET /status`: Server status
- `GET /api/git-diff`: Git diff for file