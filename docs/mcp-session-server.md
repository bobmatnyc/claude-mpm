# MCP Session Server

The MCP Session Server (`mpm-session-server`) wraps claude-mpm headless mode with stateful session management, enabling programmatic orchestration of Claude Code sessions through the Model Context Protocol (MCP).

## Overview

The MCP Session Server provides:

- **Stateful Session Management**: Create, continue, monitor, and stop Claude Code sessions programmatically
- **Concurrent Session Support**: Run multiple sessions simultaneously with configurable limits
- **Context Preservation**: Resume sessions using Claude Code's native `--resume` functionality
- **Session Forking**: Branch conversations to explore different approaches

### Use Cases

- **Programmatic claude-mpm**: Automate development workflows through MCP tool calls
- **IDE Integration**: Integrate Claude Code sessions into your development environment
- **Orchestration Platforms**: Coordinate multiple AI development sessions (e.g., Vibe Kanban)
- **Multi-Project Workflows**: Manage sessions across different codebases

## Installation

### Prerequisites

1. **claude-mpm installed** (v5.0+)
2. **ANTHROPIC_API_KEY** environment variable set
3. **Claude Code CLI** (v2.1.3+) installed

### Entry Point

The server is installed as part of claude-mpm:

```bash
# Verify installation
which mpm-session-server

# Or run directly
mpm-session-server --help
```

## Configuration for Claude Desktop

Add the MCP Session Server to your `.mcp.json` configuration file:

```json
{
  "mcpServers": {
    "mpm-session": {
      "command": "mpm-session-server",
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    }
  }
}
```

### Configuration Options

The server accepts the following command-line arguments:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--max-concurrent` | int | 5 | Maximum number of concurrent sessions |

Example with custom settings:

```json
{
  "mcpServers": {
    "mpm-session": {
      "command": "mpm-session-server",
      "args": ["--max-concurrent", "10"],
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "CLAUDE_MPM_USER_PWD": "/path/to/default/project"
      }
    }
  }
}
```

## MCP Tools Reference

The server exposes 5 tools for session management:

### mpm_session_start

Start a new claude-mpm headless session with a prompt.

**Input Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | The prompt to send to claude-mpm |
| `working_directory` | string | No | Current dir | Working directory for the session |
| `no_hooks` | boolean | No | false | Disable hooks in claude-mpm |
| `no_tickets` | boolean | No | false | Disable ticket tracking |
| `timeout` | number | No | Server default | Timeout in seconds |

**Return Schema:**

```json
{
  "success": true,
  "session_id": "abc123",
  "output": "Claude's response...",
  "error": null,
  "messages": [...]
}
```

**Example Usage:**

```json
{
  "name": "mpm_session_start",
  "arguments": {
    "prompt": "Review the authentication module and suggest improvements",
    "working_directory": "/Users/dev/myproject",
    "no_hooks": false,
    "no_tickets": true
  }
}
```

---

### mpm_session_continue

Continue an existing claude-mpm session with a new prompt.

**Input Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | Yes | - | The session ID to continue |
| `prompt` | string | Yes | - | The prompt to send |
| `fork` | boolean | No | false | Fork the session (creates a new branch) |
| `timeout` | number | No | Server default | Timeout in seconds |

**Return Schema:**

```json
{
  "success": true,
  "session_id": "abc123",
  "output": "Claude's continued response...",
  "error": null,
  "messages": [...]
}
```

**Example Usage:**

```json
{
  "name": "mpm_session_continue",
  "arguments": {
    "session_id": "abc123",
    "prompt": "Now implement the changes you suggested",
    "fork": false
  }
}
```

---

### mpm_session_status

Get the status of a specific claude-mpm session.

**Input Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | The session ID to query |

**Return Schema (found):**

```json
{
  "found": true,
  "session_id": "abc123",
  "status": "active",
  "start_time": "2025-01-01T00:00:00Z",
  "working_directory": "/Users/dev/myproject",
  "last_activity": "2025-01-01T00:05:00Z",
  "message_count": 3,
  "last_output": "Latest response..."
}
```

**Return Schema (not found):**

```json
{
  "found": false,
  "session_id": "abc123",
  "error": "Session not found: abc123"
}
```

---

### mpm_session_list

List all tracked claude-mpm sessions.

**Input Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | - | Filter by status (see Session Status values) |

**Return Schema:**

```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "status": "active",
      "start_time": "2025-01-01T00:00:00Z",
      "working_directory": "/Users/dev/myproject",
      "last_activity": "2025-01-01T00:05:00Z",
      "message_count": 3,
      "last_output": "..."
    }
  ],
  "count": 1,
  "active_count": 1
}
```

**Example Usage:**

```json
{
  "name": "mpm_session_list",
  "arguments": {
    "status": "active"
  }
}
```

---

### mpm_session_stop

Stop a running claude-mpm session.

**Input Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | Yes | - | The session ID to stop |
| `force` | boolean | No | false | Forcefully kill the process |

**Return Schema:**

```json
{
  "session_id": "abc123",
  "stopped": true,
  "force": false
}
```

## Session Lifecycle

### State Diagram

```
                    +------------+
                    |  STARTING  |
                    +-----+------+
                          |
                          v
+----------+        +-----+------+        +-----------+
|  STOPPED |<-------+   ACTIVE   +------->| COMPLETED |
+----------+        +-----+------+        +-----------+
     ^                    |
     |                    v
     |              +-----+------+
     +--------------+   ERROR    |
                    +------------+
```

### Session Status Values

| Status | Description |
|--------|-------------|
| `starting` | Session is initializing |
| `active` | Session is running and processing |
| `completed` | Session finished successfully |
| `error` | Session encountered an error |
| `stopped` | Session was manually stopped |

### Session Persistence

Sessions leverage Claude Code's native `--resume` functionality:

- **Session ID**: Extracted from the NDJSON output stream during session start
- **Context Preservation**: Full conversation history maintained across tool calls
- **Resume Support**: Continue any previously started session using its ID

### Forking Sessions

Use the `fork` parameter in `mpm_session_continue` to create a new branch:

```json
{
  "name": "mpm_session_continue",
  "arguments": {
    "session_id": "abc123",
    "prompt": "Try an alternative implementation approach",
    "fork": true
  }
}
```

Forking creates a new session that branches from the original conversation history, allowing exploration of different solutions while preserving the original conversation.

## Concurrency and Limits

### Semaphore Behavior

The server uses an `asyncio.Semaphore` to limit concurrent sessions:

- **Default limit**: 5 concurrent sessions
- **Configurable**: Use `--max-concurrent` flag
- **Blocking behavior**: New session requests wait when limit is reached
- **Fair queuing**: Sessions are started in request order

### Resource Considerations

Each active session:
- Spawns a subprocess running `claude` CLI
- Maintains NDJSON stream parsing
- Tracks session state in memory

**Recommendations:**
- Start with 3-5 concurrent sessions for typical workloads
- Increase limit only if your system has sufficient resources
- Monitor memory usage with many concurrent sessions

## Error Handling

### SessionError Types

| Error Type | Description | Retry Behavior |
|------------|-------------|----------------|
| `SessionError` | Base error for session operations | Depends on cause |
| `RateLimitError` | API rate limit exceeded | Retry after `retry_after` seconds |
| `ContextWindowError` | Context window exceeded | Cannot retry, start new session |
| `APIError` | Claude API error | Check error message |

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": "Error message description",
  "error_type": "SessionError",
  "session_id": "abc123"
}
```

For rate limit errors:

```json
{
  "error": "Rate limit exceeded",
  "error_type": "SessionError",
  "session_id": "abc123",
  "retry_after": 60
}
```

### Handling Timeouts

If a session times out:

1. The subprocess is terminated
2. Session status is updated to `ERROR`
3. A `SessionError` with timeout message is returned

Specify explicit timeouts for long-running operations:

```json
{
  "name": "mpm_session_start",
  "arguments": {
    "prompt": "Refactor the entire codebase",
    "timeout": 600
  }
}
```

## Examples

### Basic Session Workflow

1. **Start a session**:
```json
{
  "name": "mpm_session_start",
  "arguments": {
    "prompt": "Analyze the project structure and identify code quality issues",
    "working_directory": "/Users/dev/myproject"
  }
}
```

2. **Continue with follow-up**:
```json
{
  "name": "mpm_session_continue",
  "arguments": {
    "session_id": "abc123",
    "prompt": "Fix the most critical issue you identified"
  }
}
```

3. **Check status**:
```json
{
  "name": "mpm_session_status",
  "arguments": {
    "session_id": "abc123"
  }
}
```

4. **Stop when done**:
```json
{
  "name": "mpm_session_stop",
  "arguments": {
    "session_id": "abc123"
  }
}
```

### Multi-Turn Conversation

```json
// Turn 1: Analysis
{
  "name": "mpm_session_start",
  "arguments": {
    "prompt": "Review the authentication module security"
  }
}
// Response: session_id = "auth-review-001"

// Turn 2: Clarification
{
  "name": "mpm_session_continue",
  "arguments": {
    "session_id": "auth-review-001",
    "prompt": "What specific vulnerabilities did you find in the token validation?"
  }
}

// Turn 3: Implementation
{
  "name": "mpm_session_continue",
  "arguments": {
    "session_id": "auth-review-001",
    "prompt": "Implement the fix for the JWT expiration issue"
  }
}
```

### Parallel Sessions

Run multiple independent sessions simultaneously:

```json
// Session 1: Backend work
{
  "name": "mpm_session_start",
  "arguments": {
    "prompt": "Implement the user service API endpoints",
    "working_directory": "/Users/dev/backend"
  }
}

// Session 2: Frontend work (concurrent)
{
  "name": "mpm_session_start",
  "arguments": {
    "prompt": "Create React components for user management",
    "working_directory": "/Users/dev/frontend"
  }
}

// Monitor both sessions
{
  "name": "mpm_session_list",
  "arguments": {}
}
```

### Using Session Forking

```json
// Start initial session
{
  "name": "mpm_session_start",
  "arguments": {
    "prompt": "Design a caching strategy for the API"
  }
}
// Response: session_id = "cache-design-001"

// Fork to explore Redis approach
{
  "name": "mpm_session_continue",
  "arguments": {
    "session_id": "cache-design-001",
    "prompt": "Implement using Redis",
    "fork": true
  }
}
// Response: new session created

// Fork original to explore Memcached approach
{
  "name": "mpm_session_continue",
  "arguments": {
    "session_id": "cache-design-001",
    "prompt": "Implement using Memcached",
    "fork": true
  }
}
// Response: another new session created
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client                           │
│              (Claude Desktop, IDE, etc.)                │
└────────────────────────┬────────────────────────────────┘
                         │ MCP Protocol (stdio)
                         v
┌─────────────────────────────────────────────────────────┐
│                  SessionServer                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │                 MCP Tool Handlers                 │  │
│  │  • mpm_session_start    • mpm_session_status     │  │
│  │  • mpm_session_continue • mpm_session_list       │  │
│  │  • mpm_session_stop                              │  │
│  └───────────────────────────────────────────────────┘  │
│                           │                             │
│                           v                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │               SessionManager                      │  │
│  │  • Concurrency control (Semaphore)               │  │
│  │  • Session state tracking                        │  │
│  │  • Lifecycle management                          │  │
│  └───────────────────────────────────────────────────┘  │
│                           │                             │
│                           v                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │           ClaudeMPMSubprocess                    │  │
│  │  • Async subprocess execution                    │  │
│  │  • NDJSON stream parsing                         │  │
│  │  • Process lifecycle management                  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────┐
│              claude CLI (headless mode)                 │
│          claude-mpm run --headless -i "prompt"          │
└─────────────────────────────────────────────────────────┘
```

### File Structure

```
src/claude_mpm/mcp/
├── __init__.py
├── session_server.py      # MCP server + tool handlers
├── session_manager.py     # Session lifecycle management
├── subprocess_wrapper.py  # Async subprocess for claude-mpm
├── ndjson_parser.py       # NDJSON stream parsing
├── models.py              # SessionInfo, SessionResult, SessionStatus
└── errors.py              # SessionError, RateLimitError, etc.
```

## Troubleshooting

### Common Issues

**Session fails to start:**
- Verify `ANTHROPIC_API_KEY` is set correctly
- Check that `claude` CLI is accessible in PATH
- Ensure working directory exists and is accessible

**Sessions timing out:**
- Increase timeout parameter for complex prompts
- Check API rate limits
- Verify network connectivity

**Maximum sessions reached:**
- Use `mpm_session_list` to view active sessions
- Stop unused sessions with `mpm_session_stop`
- Increase `--max-concurrent` if needed

### Debug Mode

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
mpm-session-server
```

## Related Documentation

- [Headless Mode Guide](guides/headless-mode.md) - Detailed headless mode documentation
- [MCP Integration](developer/13-mcp-gateway/README.md) - MCP protocol overview
- [Session Management Skills](user/skills-guide.md) - Skills for session workflows
