# Manage Socket.IO monitoring server

Control the Claude MPM monitoring server that powers the real-time dashboard interface for event tracking and project visualization.

## Usage

```
/mpm-monitor [subcommand] [options]
```

## Description

This slash command manages the Socket.IO monitoring server that provides real-time event tracking and visualization through a web-based dashboard. The monitoring server listens for events from the Claude MPM framework and displays them in an interactive interface accessible via web browser.

The monitoring server typically runs on port 8765 (or auto-selects an available port in the range 8765-8785) and provides a real-time dashboard at `http://localhost:8765`.

## Available Subcommands

### Start Monitoring Server
Start the Socket.IO monitoring server to enable real-time event tracking.

```
/mpm-monitor start [--port PORT] [--host HOST] [--dashboard] [--dashboard-port PORT] [--foreground] [--background] [--force] [--no-reclaim]
```

**Options:**
- `--port PORT`: Specific port to start server on (auto-selects if not specified, range: 8765-8785)
- `--host HOST`: Host to bind to (default: localhost)
- `--dashboard`: Enable web dashboard interface (enabled by default)
- `--dashboard-port PORT`: Dashboard port number (default: 8766)
- `--foreground`: Run server in foreground mode (blocks terminal)
- `--background`: Run server in background/daemon mode (default behavior)
- `--force`: Force kill daemon processes to reclaim ports (use with caution)
- `--no-reclaim`: Don't automatically reclaim ports from debug scripts

**Examples:**
```
/mpm-monitor start
/mpm-monitor start --port 8765
/mpm-monitor start --port 8770 --dashboard --dashboard-port 8771
/mpm-monitor start --foreground
/mpm-monitor start --force --port 8765
```

**Default Behavior:**
- Runs in background/daemon mode
- Auto-selects first available port in range 8765-8785
- Enables web dashboard on port 8766
- Gracefully reclaims ports from debug scripts (not daemons)

### Stop Monitoring Server
Stop a running monitoring server instance.

```
/mpm-monitor stop [--port PORT] [--force]
```

**Options:**
- `--port PORT`: Port of server to stop (stops all instances if not specified)
- `--force`: Force stop even if clients are connected

**Examples:**
```
/mpm-monitor stop
/mpm-monitor stop --port 8765
/mpm-monitor stop --force
```

**Behavior:**
- Without `--port`: Stops all running monitoring server instances
- With `--port`: Stops only the server on specified port
- Without `--force`: Gracefully disconnects clients before stopping
- With `--force`: Immediately stops server regardless of client connections

### Restart Monitoring Server
Restart the monitoring server (stop and start in one operation).

```
/mpm-monitor restart [--port PORT] [--host HOST]
```

**Options:**
- `--port PORT`: Port to restart on (uses previous port if not specified)
- `--host HOST`: Host to bind to (default: localhost)

**Examples:**
```
/mpm-monitor restart
/mpm-monitor restart --port 8770
/mpm-monitor restart --port 8765 --host 0.0.0.0
```

**Behavior:**
- Stops existing server instance
- Starts new instance with same or updated configuration
- Preserves client connections where possible

### Check Server Status
Display status information about running monitoring servers.

```
/mpm-monitor status [--verbose] [--show-ports]
```

**Options:**
- `--verbose`: Show detailed status information (process IDs, uptime, connections)
- `--show-ports`: Show status of all ports in the range (8765-8785)

**Examples:**
```
/mpm-monitor status
/mpm-monitor status --verbose
/mpm-monitor status --show-ports
```

**Status Information:**
- Running server instances and their ports
- Process IDs and uptime
- Number of connected clients
- Dashboard URLs
- Port availability status (with --show-ports)

### Start on Specific Port
Start or restart monitoring server on a specific port (convenience command).

```
/mpm-monitor port <PORT> [--host HOST] [--force] [--no-reclaim]
```

**Arguments:**
- `PORT`: Port number to use (required)

**Options:**
- `--host HOST`: Host to bind to (default: localhost)
- `--force`: Force kill daemon processes to reclaim port (use with caution)
- `--no-reclaim`: Don't automatically reclaim port from debug scripts

**Examples:**
```
/mpm-monitor port 8765
/mpm-monitor port 8770 --host 0.0.0.0
/mpm-monitor port 8765 --force
```

**Behavior:**
- If server already running on port: restarts it
- If port is in use by another process: fails (unless --force)
- Auto-reclaims ports from debug scripts (unless --no-reclaim)

## Implementation

This command executes:
```bash
claude-mpm monitor [subcommand] [options]
```

The slash command passes through to the actual CLI monitoring system, which manages Socket.IO server processes.

## Monitoring Features

### Real-Time Event Tracking
The monitoring server captures and displays:
- **Agent Events**: Task delegation, completion, errors
- **Tool Usage**: File operations, bash commands, API calls
- **System Events**: Server startup/shutdown, configuration changes
- **Project Events**: File changes, git operations, test results
- **Memory Operations**: Knowledge persistence, context updates
- **WebSocket Events**: Client connections, disconnections, errors

### Web Dashboard
The dashboard interface provides:
- **Live Event Stream**: Real-time event feed with filtering
- **Project Overview**: Active agents, current tasks, system status
- **Performance Metrics**: Event rates, processing times, error counts
- **Event History**: Searchable log of past events
- **Connection Status**: Client connections, server health
- **Visualization**: Event timelines, agent activity graphs

### Port Management
The monitoring server implements smart port selection:
- **Auto-Selection**: Finds first available port in range 8765-8785
- **Port Reclamation**: Gracefully reclaims ports from debug scripts
- **Conflict Resolution**: Detects and handles port conflicts
- **Multi-Instance**: Supports multiple servers on different ports

## Expected Output

### Start Command Output
```
Starting Socket.IO monitoring server...

✓ Server started successfully
  - Server URL: http://localhost:8765
  - Dashboard URL: http://localhost:8766
  - Process ID: 12345
  - Mode: background

Monitoring server is ready for connections.
Open http://localhost:8766 in your browser to view the dashboard.
```

### Stop Command Output
```
Stopping monitoring server...

✓ Server on port 8765 stopped successfully
  - Disconnected 3 clients gracefully
  - Process 12345 terminated

Monitoring server stopped.
```

### Status Command Output
```
Monitoring Server Status
========================

Active Servers: 1

Server 1:
  - Port: 8765
  - Dashboard: http://localhost:8766
  - Process ID: 12345
  - Uptime: 2h 15m 30s
  - Connected Clients: 3
  - Status: Running

Dashboard accessible at: http://localhost:8766
```

### Status with --verbose Output
```
Monitoring Server Status (Detailed)
====================================

Active Servers: 1

Server 1:
  - Port: 8765
  - Host: localhost
  - Dashboard: http://localhost:8766
  - Dashboard Port: 8766
  - Process ID: 12345
  - Started: 2025-01-08 14:30:15
  - Uptime: 2h 15m 30s
  - Connected Clients: 3
  - Events Processed: 1,247
  - Average Event Rate: 0.17/sec
  - Status: Running (Healthy)

Client Connections:
  1. Browser (127.0.0.1:54321) - Connected 2h 10m ago
  2. CLI Monitor (127.0.0.1:54322) - Connected 1h 45m ago
  3. External Tool (127.0.0.1:54323) - Connected 30m ago

Dashboard accessible at: http://localhost:8766
```

### Status with --show-ports Output
```
Monitoring Server Status
========================

Active Servers: 1
Available Ports: 19

Port Status (8765-8785):
  8765: ✓ RUNNING (PID 12345, 3 clients)
  8766: • IN USE (Dashboard for 8765)
  8767: ○ AVAILABLE
  8768: ○ AVAILABLE
  8769: ○ AVAILABLE
  8770: ○ AVAILABLE
  ... (additional ports)
  8785: ○ AVAILABLE

Legend:
  ✓ RUNNING - Monitor server active
  • IN USE - Used by another process
  ○ AVAILABLE - Ready for use

Dashboard accessible at: http://localhost:8766
```

### Error Output Examples
```
Error: Port 8765 is already in use by another process
Suggestion: Use --port to specify a different port or --force to reclaim

Error: Failed to start monitoring server
Reason: Permission denied on port 8765
Suggestion: Try a port > 1024 or run with appropriate permissions

Error: Server on port 8765 is not running
Suggestion: Use '/mpm-monitor start' to start the server
```

## Use Cases

### Development Workflow
1. **Start monitoring** before beginning development session
2. **View dashboard** to track agent activity and events in real-time
3. **Monitor errors** to catch issues as they occur
4. **Stop monitoring** when done or to free resources

### Debugging
1. **Start with --verbose** to see detailed process information
2. **Check status** to verify server is running and clients are connected
3. **Review dashboard** to examine event history and error patterns
4. **Restart** if server becomes unresponsive

### Multiple Projects
1. **Use --port** to run separate monitors for different projects
2. **Check --show-ports** to see which ports are available
3. **Manage multiple instances** independently

### Production Monitoring
1. **Start with --background** to run as daemon (default)
2. **Configure --host 0.0.0.0** to allow remote access
3. **Check status regularly** to ensure server health
4. **Use --force carefully** only when necessary to reclaim ports

## Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
/mpm-monitor status --show-ports

# Start on a different port
/mpm-monitor start --port 8770

# Or force reclaim (use cautiously)
/mpm-monitor start --port 8765 --force
```

### Server Won't Start
```bash
# Check detailed status
/mpm-monitor status --verbose

# Try manual restart
/mpm-monitor stop --force
/mpm-monitor start
```

### Dashboard Not Accessible
```bash
# Verify server is running
/mpm-monitor status

# Check dashboard port
/mpm-monitor status --verbose

# Restart with specific dashboard port
/mpm-monitor restart --dashboard-port 8766
```

### Multiple Servers Running
```bash
# Check all running servers
/mpm-monitor status --show-ports

# Stop all servers
/mpm-monitor stop

# Start single server
/mpm-monitor start
```

## Related Commands

- `/mpm-status`: Show overall system status including monitoring server
- `/mpm-doctor`: Diagnose monitoring and server issues
- `/mpm-config`: Configure monitoring server settings
- `/mpm-init`: Initialize project with monitoring configuration

## Notes

- **Default Mode**: Server runs in background/daemon mode by default
- **Port Range**: Auto-selects from 8765-8785 if not specified
- **Dashboard**: Web interface is enabled by default on port 8766
- **Graceful Shutdown**: Server attempts to disconnect clients gracefully on stop
- **Force Reclaim**: The `--force` option should be used with caution as it kills processes
- **Debug Scripts**: Ports are automatically reclaimed from debug scripts (not daemons) unless `--no-reclaim` is specified
- **Multiple Instances**: You can run multiple monitoring servers on different ports for different projects
- **Security**: By default, server only binds to localhost. Use `--host 0.0.0.0` for remote access (consider security implications)

## Technical Details

### Socket.IO Server
- **Protocol**: Socket.IO 4.x with WebSocket transport
- **Port Range**: 8765-8785 (auto-selection)
- **Dashboard**: Static web application served on separate port
- **Events**: Real-time bidirectional event streaming
- **Clients**: Supports multiple simultaneous client connections

### Process Management
- **Daemon Mode**: Background process with PID tracking
- **Foreground Mode**: Blocking process (useful for debugging)
- **Health Checks**: Automatic health monitoring
- **Graceful Shutdown**: Clean client disconnection on stop

### Port Allocation Strategy
1. Check if requested port is available
2. If not specified, scan range 8765-8785
3. Detect port conflicts with existing processes
4. Optionally reclaim ports from debug scripts (not daemons)
5. Fail gracefully if no ports available
