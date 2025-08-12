# Event Aggregation System

## Overview

The Event Aggregation system captures comprehensive agent activity from Claude MPM sessions by connecting to the Socket.IO dashboard and saving structured JSON documents. This replaces the older hook-based response logging with a more reliable and complete solution.

## Table of Contents

- [Architecture](ARCHITECTURE.md) - System design and components
- [Configuration](CONFIGURATION.md) - Setup and configuration options
- [Usage Guide](USAGE.md) - How to use the aggregation system
- [Data Format](DATA_FORMAT.md) - JSON schema and structure
- [API Reference](API_REFERENCE.md) - Programming interfaces

## Quick Start

### Enable Activity Logging

1. **Configuration** (`.claude-mpm/configuration.yaml`):
```yaml
# Disable old response logging
response_logging:
  enabled: false

# Enable event aggregator
event_aggregator:
  enabled: true
  activity_directory: ".claude-mpm/activity"
  dashboard_port: 8765
```

2. **Start the Aggregator**:
```bash
# Using CLI
claude-mpm aggregate start

# Check status
claude-mpm aggregate status

# List sessions
claude-mpm aggregate sessions
```

3. **View Captured Activity**:
```bash
# View specific session
claude-mpm aggregate view <session_id>

# Export session data
claude-mpm aggregate export <session_id> --output session.json
```

## Key Features

### Complete Session Capture
- User prompts and responses
- Agent delegations with full context
- Tool operations (Read, Write, Edit, etc.)
- File modifications tracking
- Todo list updates
- Memory operations
- Session metrics and timing

### Real-time Processing
- Connects to Socket.IO dashboard (port 8765)
- Processes events as they arrive
- Correlates related events by session ID
- Handles concurrent sessions

### Structured Storage
- Saves to `.claude-mpm/activity/` directory
- JSON format for easy analysis
- Timestamp-based file naming
- Session metadata included

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude MPM    │    │ Socket.IO       │    │ Event           │
│   Session       │───►│ Dashboard       │───►│ Aggregator      │
│                 │    │ (Port 8765)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │ Activity Files  │
                                              │ (.claude-mpm/   │
                                              │  activity/)     │
                                              └─────────────────┘
```

## Benefits Over Response Logging

| Feature | Response Logging | Event Aggregator |
|---------|-----------------|------------------|
| **Capture Method** | Hook-based | Socket.IO events |
| **Reliability** | Session ID correlation issues | Direct event stream |
| **Coverage** | Task delegations only | All agent activity |
| **Real-time** | Post-processing | Live capture |
| **Correlation** | Manual matching | Automatic |
| **Storage** | Fragmented files | Complete sessions |

## Migration from Response Logging

If you're migrating from the old response logging system:

1. **Disable Response Logging**:
   - Set `response_logging.enabled: false`
   - Set `response_tracking.enabled: false`

2. **Enable Event Aggregator**:
   - Set `event_aggregator.enabled: true`
   - Configure `activity_directory`

3. **Start Using New Commands**:
   - Replace manual response file checking with `aggregate` commands
   - Use `aggregate sessions` to list captured activity
   - Use `aggregate view` to examine sessions

## Directory Structure

```
.claude-mpm/
└── activity/                    # Activity logs directory
    ├── session_abc123_20250812_141500.json
    ├── session_def456_20250812_142000.json
    └── session_ghi789_20250812_143000.json
```

## Related Documentation

- [Socket.IO Dashboard](../dashboard/README.md) - Dashboard system documentation
- [Hook System](../hooks/README.md) - Hook architecture (legacy)
- [Agent Sessions](../models/agent_session.md) - Session data model
- [Configuration Guide](../../CONFIGURATION.md) - General configuration