# Claude MPM WebSocket API Design

## Overview

The WebSocket API provides real-time monitoring of Claude MPM sessions, including:
- Claude process status
- Agent delegation events
- Todo list updates
- Ticket creation/updates
- System events and metrics

## Architecture

```
claude-mpm (client)
    ↓
[WebSocket Server :8765]
    ↓
Web Dashboard (browser)
```

## WebSocket Messages

### Message Format
All messages use JSON with this structure:
```json
{
  "type": "event_type",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": { ... }
}
```

### Event Types

#### 1. Session Events
```json
{
  "type": "session.start",
  "data": {
    "session_id": "uuid",
    "start_time": "timestamp",
    "launch_method": "exec|subprocess",
    "working_directory": "/path/to/project"
  }
}

{
  "type": "session.end",
  "data": {
    "session_id": "uuid",
    "end_time": "timestamp",
    "duration_seconds": 120
  }
}
```

#### 2. Claude Process Events
```json
{
  "type": "claude.status",
  "data": {
    "status": "starting|running|stopped|error",
    "pid": 12345,
    "message": "Claude is running"
  }
}

{
  "type": "claude.output",
  "data": {
    "content": "Claude output line",
    "stream": "stdout|stderr"
  }
}
```

#### 3. Agent Events
```json
{
  "type": "agent.delegation",
  "data": {
    "agent": "engineer",
    "task": "Implement feature X",
    "status": "started|completed|failed",
    "duration_ms": 5000
  }
}

{
  "type": "agent.status",
  "data": {
    "active_agents": ["engineer", "qa"],
    "agent_stats": {
      "engineer": { "tasks": 5, "avg_duration_ms": 3000 },
      "qa": { "tasks": 3, "avg_duration_ms": 2000 }
    }
  }
}
```

#### 4. Todo Events
```json
{
  "type": "todo.update",
  "data": {
    "todos": [
      {
        "id": "1",
        "content": "[Engineer] Implement WebSocket server",
        "status": "in_progress",
        "priority": "high",
        "created_at": "timestamp"
      }
    ],
    "stats": {
      "total": 10,
      "completed": 3,
      "in_progress": 2,
      "pending": 5
    }
  }
}
```

#### 5. Ticket Events
```json
{
  "type": "ticket.created",
  "data": {
    "id": "TICKET-123",
    "title": "Add WebSocket monitoring",
    "priority": "high",
    "assigned_to": "engineer"
  }
}
```

#### 6. System Events
```json
{
  "type": "system.stats",
  "data": {
    "memory_usage_mb": 256,
    "cpu_percent": 15.5,
    "uptime_seconds": 3600
  }
}

{
  "type": "system.error",
  "data": {
    "error": "Connection lost",
    "component": "hook_service",
    "severity": "warning"
  }
}
```

## Client Commands

Clients can send commands to the server:

```json
{
  "command": "subscribe",
  "channels": ["claude.output", "agent.*", "todo.*"]
}

{
  "command": "get_status"
}

{
  "command": "get_history",
  "params": {
    "event_types": ["agent.delegation"],
    "limit": 100
  }
}
```

## Implementation Plan

1. **WebSocket Server** (`src/claude_mpm/services/websocket_server.py`)
   - Uses `websockets` library
   - Runs on separate thread/process
   - Manages client connections
   - Broadcasts events

2. **Event Emitters** 
   - Integrate with ClaudeRunner
   - Hook into agent delegation
   - Monitor todo updates
   - Track ticket creation

3. **Message Queue**
   - Buffer events when no clients connected
   - Replay recent events on connection
   - Prevent memory overflow

4. **Security**
   - Optional authentication token
   - Local connections only by default
   - Rate limiting