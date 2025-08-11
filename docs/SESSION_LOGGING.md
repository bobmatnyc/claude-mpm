# Session Response Logging

## Overview

The Claude MPM session logging system provides a simplified way to log responses using Claude Code session IDs. It automatically organizes responses by session, making it easy to track and review interactions.

## Features

- **Automatic Session Detection**: Automatically detects Claude Code session IDs from environment variables
- **Simple File Structure**: Organized as `.claude-mpm/responses/{session-id}/response_001.json`
- **Lightweight**: Minimal performance impact with optional enable/disable
- **Clean Naming**: Sequential numbering (response_001.json, response_002.json, etc.)

## Directory Structure

```
.claude-mpm/responses/
├── {session-id-1}/
│   ├── response_001.json
│   ├── response_002.json
│   └── response_003.json
└── {session-id-2}/
    ├── response_001.json
    └── response_002.json
```

## Usage

### Automatic Logging via Hooks

The session response logger hook automatically captures agent responses:

```python
# Enabled by default in .claude-mpm/config/hooks.json
{
  "session_response_logger": {
    "enabled": true,
    "config": {
      "log_all_agents": true,
      "min_response_length": 50
    }
  }
}
```

### Programmatic Usage

```python
from claude_mpm.utils.session_logging import (
    log_agent_response,
    get_current_session_id,
    is_session_logging_enabled
)

# Check if logging is enabled
if is_session_logging_enabled():
    # Log a response
    log_agent_response(
        agent_name="research",
        request="Analyze the codebase",
        response="The codebase analysis shows...",
        metadata={"model": "claude-3", "tokens": 500}
    )
    
    # Get current session ID
    session_id = get_current_session_id()
    print(f"Current session: {session_id}")
```

### Direct Usage

```python
from claude_mpm.services.claude_session_logger import get_session_logger

# Get the logger instance
logger = get_session_logger()

# Log a response
logger.log_response(
    request_summary="Test request",
    response_content="This is the response content",
    metadata={"agent": "test"}
)
```

## Configuration

### Environment Variables

- `CLAUDE_SESSION_ID`: Primary session ID from Claude Code
- `ANTHROPIC_SESSION_ID`: Alternative session ID
- `SESSION_ID`: Generic session ID fallback
- `CLAUDE_MPM_NO_SESSION_LOGGING`: Set to `1` to disable logging

### Hook Configuration

Edit `.claude-mpm/config/hooks.json`:

```json
{
  "session_response_logger": {
    "enabled": true,
    "config": {
      "log_all_agents": true,
      "logged_agents": ["research", "engineer"],
      "excluded_agents": ["test"],
      "min_response_length": 50
    }
  }
}
```

## Response File Format

Each response is saved as a JSON file with the following structure:

```json
{
  "timestamp": "2024-01-10T14:30:00",
  "session_id": "session-abc123",
  "request_summary": "Brief summary of the request",
  "response": "Full response content...",
  "metadata": {
    "agent": "research",
    "model": "claude-3",
    "tokens": 1500,
    "tools_used": ["grep", "read"]
  }
}
```

## Testing

Run the test script to verify the logging system:

```bash
python scripts/test_session_logger.py
```

This will:
- Test basic logging functionality
- Test environment variable session IDs
- Verify singleton pattern
- List existing sessions

## Disabling Logging

To disable session logging:

1. **Via Environment Variable**:
   ```bash
   export CLAUDE_MPM_NO_SESSION_LOGGING=1
   ```

2. **Via Hook Configuration**:
   ```json
   {
     "session_response_logger": {
       "enabled": false
     }
   }
   ```

3. **Programmatically**:
   ```python
   from claude_mpm.utils.session_logging import disable_session_logging
   disable_session_logging()
   ```

## Session Management

### Viewing Sessions

```bash
# List all sessions
ls .claude-mpm/responses/

# View responses in a session
ls .claude-mpm/responses/{session-id}/

# Read a specific response
cat .claude-mpm/responses/{session-id}/response_001.json
```

### Cleaning Up Old Sessions

Sessions are stored locally and can be manually deleted when no longer needed:

```bash
# Remove a specific session
rm -rf .claude-mpm/responses/{session-id}

# Remove all sessions older than 7 days
find .claude-mpm/responses -type d -mtime +7 -exec rm -rf {} +
```

## Integration Points

The session logger integrates with:

1. **Hook System**: Via `session_response_logger_hook.py`
2. **Agent System**: Automatically captures agent responses
3. **CLI Commands**: Can be enabled/disabled via command flags
4. **Service Layer**: Direct integration for custom logging needs

## Performance Considerations

- Logging is asynchronous and non-blocking
- Minimal memory footprint
- Files are written incrementally (not held in memory)
- Can be disabled entirely with zero overhead

## Troubleshooting

### No Session ID Available

If no Claude Code session ID is detected, the system will generate a timestamp-based session ID (e.g., `session_20240110_143000`).

### Logging Not Working

1. Check if logging is enabled:
   ```python
   from claude_mpm.utils.session_logging import is_session_logging_enabled
   print(is_session_logging_enabled())
   ```

2. Verify session ID is available:
   ```python
   from claude_mpm.utils.session_logging import get_current_session_id
   print(get_current_session_id())
   ```

3. Check environment variables:
   ```bash
   env | grep -E "(CLAUDE|SESSION|ANTHROPIC)"
   ```

### Permission Issues

Ensure the `.claude-mpm/responses/` directory is writable:

```bash
chmod -R 755 .claude-mpm/responses/
```