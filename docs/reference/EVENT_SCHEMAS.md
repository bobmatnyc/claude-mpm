# Claude MPM Event Schemas Reference

## Overview

This document defines the event schemas used throughout the Claude MPM Socket.IO and Hook system. All events must conform to these schemas for proper processing and validation.

## Base Event Schema

All events share a common base structure:

```json
{
  "source": "string",      // Required: Event source identifier
  "type": "string",        // Required: Event type category
  "subtype": "string",     // Required: Specific event subtype
  "timestamp": "string",   // Required: ISO 8601 timestamp
  "data": {},              // Required: Event-specific data payload
  "event": "string",       // Optional: Legacy event name
  "session_id": "string"   // Optional: Session identifier
}
```

### Field Descriptions

- **source**: Identifies where the event originated (e.g., "claude_code", "hook_handler", "dashboard")
- **type**: High-level event category (e.g., "tool", "subagent", "connection", "system")
- **subtype**: Specific event type within category (e.g., "start", "stop", "error")
- **timestamp**: UTC timestamp in ISO 8601 format (e.g., "2025-01-15T10:30:45.123Z")
- **data**: Event-specific payload containing relevant information
- **event**: Legacy field for backward compatibility
- **session_id**: Groups related events together (e.g., single Claude Code session)

## Tool Events

Tool events are generated when Claude Code executes tools like Read, Write, Edit, etc.

### Tool Start Event

```json
{
  "source": "claude_code",
  "type": "tool",
  "subtype": "start",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "session_id": "session_abc123",
  "data": {
    "tool_name": "Read",
    "parameters": {
      "file_path": "/path/to/file.py",
      "limit": 100
    },
    "tool_id": "tool_001",
    "execution_context": {
      "working_directory": "/Users/user/project",
      "environment": "development"
    }
  }
}
```

### Tool Stop Event

```json
{
  "source": "claude_code",
  "type": "tool",
  "subtype": "stop",
  "timestamp": "2025-01-15T10:30:47.456Z",
  "session_id": "session_abc123",
  "data": {
    "tool_name": "Read",
    "tool_id": "tool_001",
    "execution_time_ms": 234,
    "success": true,
    "result": {
      "lines_read": 50,
      "file_size": 1024
    },
    "error": null
  }
}
```

### Tool Error Event

```json
{
  "source": "claude_code",
  "type": "tool",
  "subtype": "error",
  "timestamp": "2025-01-15T10:30:47.789Z",
  "session_id": "session_abc123",
  "data": {
    "tool_name": "Edit",
    "tool_id": "tool_002",
    "error": {
      "type": "FileNotFoundError",
      "message": "File '/path/to/nonexistent.py' not found",
      "code": "ENOENT",
      "stack_trace": "..."
    },
    "parameters": {
      "file_path": "/path/to/nonexistent.py",
      "old_string": "original text",
      "new_string": "modified text"
    }
  }
}
```

## Subagent Events

Subagent events track the lifecycle of subagent invocations within Claude Code sessions.

### Subagent Start Event

```json
{
  "source": "claude_code",
  "type": "subagent",
  "subtype": "start",
  "timestamp": "2025-01-15T10:31:00.123Z",
  "session_id": "session_abc123",
  "data": {
    "subagent_name": "Research Agent",
    "subagent_id": "subagent_001",
    "parent_session": "session_abc123",
    "task_description": "Research Python testing frameworks",
    "parameters": {
      "topic": "pytest vs unittest",
      "depth": "comprehensive"
    },
    "context": {
      "working_directory": "/Users/user/project",
      "files_available": ["/path/to/test_file.py"]
    }
  }
}
```

### Subagent Stop Event

```json
{
  "source": "claude_code",
  "type": "subagent",
  "subtype": "stop",
  "timestamp": "2025-01-15T10:33:15.456Z",
  "session_id": "session_abc123",
  "data": {
    "subagent_id": "subagent_001",
    "subagent_name": "Research Agent",
    "execution_time_ms": 135333,
    "success": true,
    "result": {
      "response_length": 2048,
      "tools_used": ["WebSearch", "Read"],
      "files_analyzed": 3
    },
    "performance_metrics": {
      "memory_usage_mb": 45,
      "cpu_time_ms": 1200
    }
  }
}
```

### Subagent Error Event

```json
{
  "source": "claude_code",
  "type": "subagent",
  "subtype": "error",
  "timestamp": "2025-01-15T10:32:30.789Z",
  "session_id": "session_abc123",
  "data": {
    "subagent_id": "subagent_002",
    "subagent_name": "Code Analyzer",
    "error": {
      "type": "TimeoutError",
      "message": "Subagent execution timed out after 30 seconds",
      "code": "TIMEOUT",
      "timeout_duration_ms": 30000
    },
    "partial_results": {
      "tools_completed": 2,
      "tools_remaining": 1
    }
  }
}
```

## Connection Events

Connection events track Socket.IO client connections and disconnections.

### Connection Established

```json
{
  "source": "socketio_server",
  "type": "connection",
  "subtype": "connect",
  "timestamp": "2025-01-15T10:25:00.123Z",
  "data": {
    "client_id": "client_xyz789",
    "client_ip": "127.0.0.1",
    "user_agent": "Mozilla/5.0 (Dashboard Client)",
    "connection_type": "websocket",
    "session_info": {
      "transport": "websocket",
      "upgrade": true,
      "compressed": false
    }
  }
}
```

### Connection Lost

```json
{
  "source": "socketio_server",
  "type": "connection",
  "subtype": "disconnect",
  "timestamp": "2025-01-15T10:45:30.456Z",
  "data": {
    "client_id": "client_xyz789",
    "disconnect_reason": "client namespace disconnect",
    "connection_duration_ms": 1230333,
    "events_received": 45,
    "events_sent": 123,
    "last_activity": "2025-01-15T10:45:25.000Z"
  }
}
```

### Connection Error

```json
{
  "source": "socketio_server",
  "type": "connection",
  "subtype": "error",
  "timestamp": "2025-01-15T10:25:05.789Z",
  "data": {
    "client_id": "client_abc456",
    "error": {
      "type": "ConnectionError",
      "message": "WebSocket connection failed",
      "code": "WS_CONNECT_FAILED"
    },
    "attempt_number": 3,
    "retry_delay_ms": 4000
  }
}
```

## System Events

System events track server status, configuration changes, and health monitoring.

### Server Status

```json
{
  "source": "socketio_server",
  "type": "system",
  "subtype": "status",
  "timestamp": "2025-01-15T10:30:00.000Z",
  "data": {
    "server_status": "healthy",
    "uptime_ms": 1800000,
    "active_connections": 3,
    "events_processed": 1543,
    "memory_usage_mb": 28,
    "cpu_usage_percent": 2.1,
    "event_queue_size": 0,
    "health_score": 0.98
  }
}
```

### Configuration Change

```json
{
  "source": "hook_handler",
  "type": "system",
  "subtype": "config_change",
  "timestamp": "2025-01-15T10:35:00.123Z",
  "data": {
    "config_type": "debug_mode",
    "old_value": false,
    "new_value": true,
    "changed_by": "user",
    "config_path": "CLAUDE_MPM_HOOK_DEBUG",
    "restart_required": false
  }
}
```

### Health Check

```json
{
  "source": "socketio_server",
  "type": "system",
  "subtype": "health_check",
  "timestamp": "2025-01-15T10:30:45.000Z",
  "data": {
    "check_type": "ping_pong",
    "status": "pass",
    "response_time_ms": 5,
    "details": {
      "last_ping": "2025-01-15T10:30:40.000Z",
      "last_pong": "2025-01-15T10:30:40.005Z",
      "ping_interval_ms": 45000,
      "timeout_threshold_ms": 20000
    }
  }
}
```

## File Operation Events

File operation events track file system modifications by Claude Code tools.

### File Modified

```json
{
  "source": "claude_code",
  "type": "file",
  "subtype": "modified",
  "timestamp": "2025-01-15T10:31:15.123Z",
  "session_id": "session_abc123",
  "data": {
    "file_path": "/path/to/modified_file.py",
    "operation": "edit",
    "tool_name": "Edit",
    "changes": {
      "lines_added": 5,
      "lines_removed": 2,
      "lines_modified": 3
    },
    "file_info": {
      "size_bytes": 2048,
      "permissions": "644",
      "last_modified": "2025-01-15T10:31:15.120Z"
    }
  }
}
```

### File Created

```json
{
  "source": "claude_code",
  "type": "file",
  "subtype": "created",
  "timestamp": "2025-01-15T10:32:00.456Z",
  "session_id": "session_abc123",
  "data": {
    "file_path": "/path/to/new_file.py",
    "tool_name": "Write",
    "content_length": 512,
    "file_type": "python",
    "encoding": "utf-8"
  }
}
```

## Memory Events

Memory events track agent memory system operations.

### Memory Updated

```json
{
  "source": "memory_system",
  "type": "memory",
  "subtype": "updated",
  "timestamp": "2025-01-15T10:33:00.123Z",
  "session_id": "session_abc123",
  "data": {
    "memory_type": "project_context",
    "key": "architecture_notes",
    "operation": "append",
    "data_size": 256,
    "total_memory_size": 1024,
    "retention_policy": "session"
  }
}
```

## Error Events

Generic error events for system-wide error reporting.

### Processing Error

```json
{
  "source": "hook_handler",
  "type": "error",
  "subtype": "processing",
  "timestamp": "2025-01-15T10:34:00.789Z",
  "session_id": "session_abc123",
  "data": {
    "error": {
      "type": "ValidationError",
      "message": "Event schema validation failed",
      "code": "INVALID_SCHEMA",
      "details": {
        "missing_fields": ["timestamp"],
        "invalid_fields": ["type"]
      }
    },
    "original_event": {
      "source": "unknown",
      "type": 123,
      "data": {}
    },
    "recovery_action": "event_discarded"
  }
}
```

## Validation Rules

### Required Field Validation

All events MUST include:
- `source`: Non-empty string
- `type`: Non-empty string from allowed types
- `subtype`: Non-empty string from allowed subtypes
- `timestamp`: Valid ISO 8601 timestamp
- `data`: Valid JSON object (may be empty)

### Optional Field Validation

- `event`: String (legacy compatibility)
- `session_id`: String matching pattern `^session_[a-zA-Z0-9]+$`

### Data Payload Validation

The `data` field validation depends on event type:

#### Tool Events
- `tool_name`: Required string
- `tool_id`: Optional string
- `parameters`: Optional object
- `execution_time_ms`: Required for stop events
- `success`: Required boolean for stop events
- `error`: Required object for error events

#### Subagent Events
- `subagent_name`: Required string
- `subagent_id`: Required string
- `parent_session`: Optional string
- `execution_time_ms`: Required for stop events
- `success`: Required boolean for stop events

#### Connection Events
- `client_id`: Required string
- `client_ip`: Optional string (should be 127.0.0.1)
- `connection_type`: Optional string

#### System Events
- `server_status`: Required for status events
- `config_type`: Required for config_change events
- `check_type`: Required for health_check events

### Schema Validation Examples

#### Valid Event
```json
{
  "source": "claude_code",
  "type": "tool",
  "subtype": "start",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "session_id": "session_abc123",
  "data": {
    "tool_name": "Read",
    "parameters": {
      "file_path": "/path/to/file.py"
    }
  }
}
```

#### Invalid Event Examples

**Missing required fields:**
```json
{
  "source": "claude_code",
  "type": "tool"
  // Missing: subtype, timestamp, data
}
```

**Invalid timestamp format:**
```json
{
  "source": "claude_code",
  "type": "tool",
  "subtype": "start",
  "timestamp": "2025-01-15 10:30:45",  // Invalid format
  "data": {}
}
```

**Invalid type:**
```json
{
  "source": "claude_code",
  "type": "invalid_type",  // Not in allowed types
  "subtype": "start",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "data": {}
}
```

## Event Processing Pipeline

### 1. Event Generation
Events are generated by Claude Code during tool execution and subagent operations.

### 2. Hook Handler Validation
The hook handler validates events against schema:
```python
def validate_event(event):
    # Check required fields
    required = ['source', 'type', 'subtype', 'timestamp', 'data']
    for field in required:
        if field not in event:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate timestamp format
    try:
        datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
    except ValueError:
        raise ValidationError("Invalid timestamp format")
    
    # Validate type/subtype combinations
    if not is_valid_type_subtype(event['type'], event['subtype']):
        raise ValidationError("Invalid type/subtype combination")
```

### 3. Event Enrichment
Hook handler enriches events with additional metadata:
- Session ID assignment
- Processing timestamps
- Sequence numbers
- Context information

### 4. Socket.IO Broadcasting
Validated and enriched events are broadcast to connected dashboard clients.

### 5. Client-Side Processing
Dashboard clients validate received events and update UI state accordingly.

## Error Handling

### Validation Errors
Invalid events are logged and discarded:
```json
{
  "source": "hook_handler",
  "type": "error",
  "subtype": "validation",
  "timestamp": "2025-01-15T10:35:00.000Z",
  "data": {
    "error": "ValidationError: Missing required field: timestamp",
    "original_event": "...",
    "action": "discarded"
  }
}
```

### Processing Errors
Errors during event processing are captured:
```json
{
  "source": "socketio_server",
  "type": "error",
  "subtype": "processing",
  "timestamp": "2025-01-15T10:35:30.000Z",
  "data": {
    "error": "Failed to broadcast event to client_xyz789",
    "client_id": "client_xyz789",
    "event_type": "tool.start",
    "retry_attempted": true
  }
}
```

## Best Practices

### Event Generation
1. **Include all required fields** in every event
2. **Use consistent timestamps** in UTC ISO 8601 format
3. **Provide meaningful data payloads** with relevant context
4. **Use appropriate type/subtype combinations**
5. **Include session IDs** for event correlation

### Event Processing
1. **Validate events early** in the processing pipeline
2. **Handle validation errors gracefully** without crashing
3. **Log invalid events** for debugging and analysis
4. **Maintain event ordering** within sessions
5. **Implement proper error recovery**

### Client Handling
1. **Validate received events** before processing
2. **Handle missing or malformed events** gracefully
3. **Maintain local event history** for user experience
4. **Implement proper error display** for debugging
5. **Queue events during disconnections**

## Schema Evolution

### Versioning Strategy
Event schemas use semantic versioning:
- **Major**: Breaking changes to required fields
- **Minor**: New optional fields or event types
- **Patch**: Documentation or validation improvements

### Backward Compatibility
- New optional fields may be added without version bump
- Required fields cannot be removed or renamed
- Type/subtype values cannot be changed
- Data payload structure should remain stable

### Migration Guidelines
1. **Deprecate old formats** before removing support
2. **Provide migration tools** for existing events
3. **Document breaking changes** clearly
4. **Test compatibility** with existing clients
5. **Implement gradual rollout** for changes

## Testing

### Schema Validation Tests
```python
def test_valid_tool_start_event():
    event = {
        "source": "claude_code",
        "type": "tool", 
        "subtype": "start",
        "timestamp": "2025-01-15T10:30:45.123Z",
        "data": {"tool_name": "Read"}
    }
    assert validate_event(event) == True

def test_missing_required_field():
    event = {
        "source": "claude_code",
        "type": "tool"
        # Missing subtype, timestamp, data
    }
    with pytest.raises(ValidationError):
        validate_event(event)
```

### End-to-End Tests
```javascript
// Dashboard client test
describe('Event Processing', () => {
    it('should handle valid tool events', async () => {
        const event = {
            source: 'claude_code',
            type: 'tool',
            subtype: 'start',
            timestamp: new Date().toISOString(),
            data: { tool_name: 'Read' }
        };
        
        const result = await processEvent(event);
        expect(result.valid).toBe(true);
    });
});
```

This schema reference provides a comprehensive guide for all event types used in the Claude MPM system, ensuring consistent data flow and reliable event processing across all components.