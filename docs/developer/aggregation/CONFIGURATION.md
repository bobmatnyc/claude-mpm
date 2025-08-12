# Event Aggregator Configuration

## Configuration File

The event aggregator is configured through `.claude-mpm/configuration.yaml`.

## Complete Configuration Example

```yaml
# Event Aggregator configuration
event_aggregator:
  # Master enable switch
  enabled: true
  
  # Directory to store activity logs
  activity_directory: ".claude-mpm/activity"
  
  # Socket.IO dashboard port to connect to
  dashboard_port: 8765
  
  # Auto-start with claude-mpm (future feature)
  auto_start: false
  
  # Session tracking
  session_timeout_minutes: 60
  
  # File format for activity logs
  file_format: "{date}_{session_id}.json"
  
  # Compression for saved sessions
  compress_sessions: false
  
  # Auto-cleanup old sessions
  auto_cleanup_days: 30
  
  # What to capture
  capture:
    user_prompts: true
    agent_delegations: true
    tool_operations: true
    file_operations: true
    todo_updates: true
    responses: true
    memory_events: true
```

## Configuration Options

### Core Settings

#### `enabled`
- **Type**: boolean
- **Default**: `true`
- **Description**: Master switch to enable/disable the event aggregator

#### `activity_directory`
- **Type**: string
- **Default**: `".claude-mpm/activity"`
- **Description**: Directory where activity JSON files are saved
- **Notes**: Can be absolute or relative path

#### `dashboard_port`
- **Type**: integer
- **Default**: `8765`
- **Description**: Port number of the Socket.IO dashboard server
- **Notes**: Must match dashboard server configuration

### Session Management

#### `session_timeout_minutes`
- **Type**: integer
- **Default**: `60`
- **Description**: Minutes of inactivity before a session is considered complete
- **Notes**: Prevents memory buildup from abandoned sessions

#### `file_format`
- **Type**: string
- **Default**: `"{date}_{session_id}.json"`
- **Description**: Template for activity file naming
- **Variables**:
  - `{date}` - Timestamp in YYYYMMDD_HHMMSS format
  - `{session_id}` - Unique session identifier

#### `compress_sessions`
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable gzip compression for saved sessions
- **Notes**: Reduces disk usage but adds CPU overhead

#### `auto_cleanup_days`
- **Type**: integer
- **Default**: `30`
- **Description**: Days to keep activity files before automatic deletion
- **Notes**: Set to 0 to disable auto-cleanup

### Capture Filters

Control what types of events are captured:

#### `capture.user_prompts`
- **Type**: boolean
- **Default**: `true`
- **Description**: Capture user input prompts

#### `capture.agent_delegations`
- **Type**: boolean
- **Default**: `true`
- **Description**: Capture Task tool delegations to agents

#### `capture.tool_operations`
- **Type**: boolean
- **Default**: `true`
- **Description**: Capture all tool operations (Read, Write, Edit, etc.)

#### `capture.file_operations`
- **Type**: boolean
- **Default**: `true`
- **Description**: Capture file-specific operations

#### `capture.todo_updates`
- **Type**: boolean
- **Default**: `true`
- **Description**: Capture TodoWrite operations

#### `capture.responses`
- **Type**: boolean
- **Default**: `true`
- **Description**: Capture agent responses and completions

#### `capture.memory_events`
- **Type**: boolean
- **Default**: `true`
- **Description**: Capture memory system operations

## Environment Variables

Environment variables can override configuration:

```bash
# Override dashboard port
export CLAUDE_MPM_DASHBOARD_PORT=8766

# Override activity directory
export CLAUDE_MPM_ACTIVITY_DIR=/custom/path/activity

# Debug mode
export CLAUDE_MPM_AGGREGATOR_DEBUG=true
```

## Disabling Response Logging

When using the event aggregator, disable the old response logging system:

```yaml
# Disable old response logging
response_logging:
  enabled: false
  
response_tracking:
  enabled: false
```

## Migration Configuration

If migrating from response logging to event aggregator:

```yaml
# Step 1: Disable old system
response_logging:
  enabled: false
response_tracking:
  enabled: false

# Step 2: Enable new system
event_aggregator:
  enabled: true
  activity_directory: ".claude-mpm/activity"  # Different from old .claude-mpm/responses
```

## Performance Tuning

### High-Volume Configuration

For high-volume environments:

```yaml
event_aggregator:
  session_timeout_minutes: 30  # Shorter timeout
  compress_sessions: true      # Save disk space
  auto_cleanup_days: 7         # More aggressive cleanup
  capture:
    memory_events: false      # Reduce noise
```

### Development Configuration

For development and debugging:

```yaml
event_aggregator:
  enabled: true
  session_timeout_minutes: 120  # Longer timeout
  compress_sessions: false      # Easier to inspect
  auto_cleanup_days: 0          # Keep everything
  capture:
    user_prompts: true
    agent_delegations: true
    tool_operations: true
    file_operations: true
    todo_updates: true
    responses: true
    memory_events: true        # Capture everything
```

### Minimal Configuration

Minimal required configuration:

```yaml
event_aggregator:
  enabled: true
```

All other values will use defaults.

## Validation

Validate your configuration:

```bash
# Check configuration
claude-mpm config validate

# View current settings
claude-mpm config view --section event_aggregator
```

## Troubleshooting Configuration

### Common Issues

1. **Aggregator not starting**
   - Check `enabled: true`
   - Verify dashboard is running on configured port
   - Check directory permissions

2. **No activity files created**
   - Verify `activity_directory` exists and is writable
   - Check capture filters aren't all disabled
   - Ensure Socket.IO connection successful

3. **Sessions never complete**
   - Reduce `session_timeout_minutes`
   - Check for Stop events being sent

4. **Disk space issues**
   - Enable `compress_sessions`
   - Reduce `auto_cleanup_days`
   - Use absolute path for `activity_directory`

## Configuration Precedence

Configuration is loaded in this order (highest precedence first):

1. Command-line arguments
2. Environment variables
3. Configuration file (`.claude-mpm/configuration.yaml`)
4. Default values

## Best Practices

1. **Use relative paths** for portability
2. **Enable compression** for production
3. **Set appropriate cleanup** periods
4. **Disable unused capture filters** to reduce noise
5. **Monitor disk usage** regularly
6. **Backup activity files** before cleanup