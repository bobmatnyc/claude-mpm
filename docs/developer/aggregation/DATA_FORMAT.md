# Event Aggregator Data Format

## Session JSON Schema

Each captured session is saved as a JSON file with the following structure:

### Top-Level Structure

```json
{
  "session_id": "string",           // Unique session identifier
  "start_time": "datetime",         // ISO 8601 timestamp
  "end_time": "datetime|null",      // ISO 8601 timestamp or null if active
  "working_directory": "string",     // Working directory path
  "git_branch": "string|null",      // Git branch name if in repo
  "launch_method": "string",         // How session was started (cli, api, etc.)
  "initial_prompt": "string|null",  // First user prompt
  "final_response": "string|null",  // Final response before completion
  "events": [...],                  // Array of all events
  "delegations": [...],             // Array of agent delegations
  "metrics": {...}                  // Session metrics and statistics
}
```

## Event Structure

Each event in the `events` array has this structure:

```json
{
  "timestamp": "2025-08-12T14:30:22.123Z",
  "event_type": "string",           // Event type (e.g., "UserPromptSubmit")
  "category": "string",             // Category (prompt, tool, delegation, etc.)
  "data": {...},                    // Event-specific data
  "session_id": "string",           // Session identifier
  "correlation_id": "string|null"   // For correlating related events
}
```

### Event Categories

- **prompt** - User input events
- **delegation** - Agent Task delegations
- **tool** - Tool operations (Read, Write, etc.)
- **file** - File-specific operations
- **response** - Agent/session responses
- **memory** - Memory system events
- **meta** - Session metadata events

### Common Event Types

#### UserPromptSubmit
```json
{
  "event_type": "UserPromptSubmit",
  "category": "prompt",
  "data": {
    "prompt": "Help me implement a new feature",
    "prompt_length": 31,
    "working_directory": "/project",
    "git_branch": "main"
  }
}
```

#### Task Delegation (PreToolUse)
```json
{
  "event_type": "PreToolUse",
  "category": "delegation",
  "data": {
    "tool_name": "Task",
    "tool_input": {
      "subagent_type": "engineer",
      "prompt": "Implement the user authentication module",
      "description": "Create login and registration"
    },
    "agent_type": "engineer"
  }
}
```

#### File Operation
```json
{
  "event_type": "PreToolUse",
  "category": "file",
  "data": {
    "tool_name": "Write",
    "tool_input": {
      "file_path": "/src/auth.py",
      "content": "..."
    },
    "operation": "write",
    "file_path": "/src/auth.py"
  }
}
```

#### Agent Response (SubagentStop)
```json
{
  "event_type": "SubagentStop",
  "category": "response",
  "data": {
    "agent_type": "engineer",
    "reason": "completed",
    "output": "I've successfully implemented...",
    "success": true,
    "duration_ms": 45000
  }
}
```

## Delegation Structure

Each delegation in the `delegations` array:

```json
{
  "agent_type": "engineer",
  "start_time": "2025-08-12T14:30:25.456Z",
  "end_time": "2025-08-12T14:33:45.789Z",
  "instructions": "Implement the user authentication module",
  "event_count": 23,
  "tool_operations": ["Write", "Edit", "Read", "Bash"],
  "files_modified": [
    "/src/auth.py",
    "/src/models/user.py",
    "/tests/test_auth.py"
  ],
  "success": true,
  "response_preview": "I've successfully implemented the authentication..."
}
```

## Metrics Structure

The `metrics` object contains session statistics:

```json
{
  "total_events": 152,
  "session_duration_ms": 205000,
  "event_breakdown": {
    "prompt": 1,
    "delegation": 2,
    "tool": 89,
    "file": 45,
    "response": 3,
    "memory": 5,
    "meta": 7
  },
  "agents_used": ["research", "engineer", "qa"],
  "tools_used": ["Task", "Read", "Write", "Edit", "Bash", "TodoWrite"],
  "files_modified": [
    "/src/auth.py",
    "/src/models/user.py",
    "/tests/test_auth.py"
  ],
  "total_delegations": 3,
  "successful_delegations": 3,
  "failed_delegations": 0
}
```

## File Naming Convention

Activity files are named using this pattern:

```
session_{session_id}_{timestamp}.json
```

Example:
```
session_5283b66c-2b29-4ee0-9698-f410f3a393fd_20250812_141530.json
```

Where:
- `session_` - Fixed prefix
- `{session_id}` - First part of UUID session ID
- `{timestamp}` - YYYYMMDD_HHMMSS format

## Complete Example

```json
{
  "session_id": "5283b66c-2b29-4ee0-9698-f410f3a393fd",
  "start_time": "2025-08-12T14:15:30.123Z",
  "end_time": "2025-08-12T14:18:55.456Z",
  "working_directory": "/Users/masa/Projects/myapp",
  "git_branch": "feature/auth",
  "launch_method": "cli",
  "initial_prompt": "Help me implement user authentication",
  "final_response": "I've successfully implemented the authentication module...",
  
  "events": [
    {
      "timestamp": "2025-08-12T14:15:30.123Z",
      "event_type": "UserPromptSubmit",
      "category": "prompt",
      "data": {
        "prompt": "Help me implement user authentication",
        "prompt_length": 37
      },
      "session_id": "5283b66c-2b29-4ee0-9698-f410f3a393fd"
    },
    {
      "timestamp": "2025-08-12T14:15:32.456Z",
      "event_type": "PreToolUse",
      "category": "delegation",
      "data": {
        "tool_name": "Task",
        "tool_input": {
          "subagent_type": "research",
          "prompt": "Analyze the current authentication setup"
        }
      },
      "session_id": "5283b66c-2b29-4ee0-9698-f410f3a393fd"
    }
  ],
  
  "delegations": [
    {
      "agent_type": "research",
      "start_time": "2025-08-12T14:15:32.456Z",
      "end_time": "2025-08-12T14:16:45.789Z",
      "instructions": "Analyze the current authentication setup",
      "event_count": 15,
      "tool_operations": ["Read", "Grep"],
      "files_modified": [],
      "success": true,
      "response_preview": "I've analyzed the codebase..."
    },
    {
      "agent_type": "engineer",
      "start_time": "2025-08-12T14:16:50.123Z",
      "end_time": "2025-08-12T14:18:30.456Z",
      "instructions": "Implement JWT authentication",
      "event_count": 45,
      "tool_operations": ["Write", "Edit", "Bash"],
      "files_modified": [
        "/src/auth.py",
        "/src/middleware/jwt.py"
      ],
      "success": true,
      "response_preview": "I've implemented JWT authentication..."
    }
  ],
  
  "metrics": {
    "total_events": 74,
    "session_duration_ms": 205333,
    "event_breakdown": {
      "prompt": 1,
      "delegation": 2,
      "tool": 60,
      "file": 8,
      "response": 2,
      "meta": 1
    },
    "agents_used": ["research", "engineer"],
    "tools_used": ["Task", "Read", "Grep", "Write", "Edit", "Bash"],
    "files_modified": [
      "/src/auth.py",
      "/src/middleware/jwt.py"
    ],
    "total_delegations": 2,
    "successful_delegations": 2,
    "failed_delegations": 0
  }
}
```

## Data Types

### Timestamps
All timestamps use ISO 8601 format with millisecond precision:
```
2025-08-12T14:15:30.123Z
```

### Session IDs
UUIDs in standard format:
```
5283b66c-2b29-4ee0-9698-f410f3a393fd
```

### File Paths
Absolute paths from the working directory:
```
/Users/masa/Projects/myapp/src/auth.py
```

### Agent Types
Lowercase, hyphen-separated:
```
research
engineer
qa
data-engineer
version-control
```

### Tool Names
PascalCase as used in Claude:
```
Task
Read
Write
Edit
MultiEdit
Bash
TodoWrite
```

## Validation

### JSON Schema Validation

You can validate session files against the schema:

```python
import json
import jsonschema

# Load schema
with open('session_schema.json') as f:
    schema = json.load(f)

# Load session
with open('.claude-mpm/activity/session_abc.json') as f:
    session = json.load(f)

# Validate
jsonschema.validate(session, schema)
```

### Required Fields

Minimum required fields for a valid session:
- `session_id`
- `start_time`
- `events` (can be empty array)
- `metrics.total_events`

## Compression

When `compress_sessions: true` is configured, files are gzipped:

```bash
# Compressed file
session_5283b66c_20250812_141530.json.gz

# Read compressed file
zcat session_5283b66c_20250812_141530.json.gz | jq .

# Or in Python
import gzip
import json

with gzip.open('session_5283b66c_20250812_141530.json.gz', 'rt') as f:
    session = json.load(f)
```

## Query Examples

### Using jq

```bash
# Get all engineer delegations
jq '.delegations[] | select(.agent_type == "engineer")' session_*.json

# Find sessions longer than 5 minutes
jq 'select(.metrics.session_duration_ms > 300000) | .session_id' session_*.json

# Count tool usage across all sessions
jq '.metrics.tools_used[]' session_*.json | sort | uniq -c

# Extract all modified files
jq '.metrics.files_modified[]' session_*.json | sort -u
```

### Using Python

```python
import json
from pathlib import Path
from datetime import datetime

# Load all sessions
sessions = []
for file in Path('.claude-mpm/activity').glob('session_*.json'):
    with open(file) as f:
        sessions.append(json.load(f))

# Find longest session
longest = max(sessions, key=lambda s: s['metrics']['session_duration_ms'])
print(f"Longest session: {longest['session_id']}")
print(f"Duration: {longest['metrics']['session_duration_ms']/1000:.1f}s")

# Find most active agent
from collections import Counter
agent_usage = Counter()
for session in sessions:
    for agent in session['metrics'].get('agents_used', []):
        agent_usage[agent] += 1

print("Agent usage:", agent_usage.most_common())
```