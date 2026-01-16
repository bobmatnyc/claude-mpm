# MPM Commander Usage Guide

Complete guide to using MPM Commander for autonomous multi-project AI orchestration.

## Table of Contents

- [Getting Started](#getting-started)
- [CLI Commands](#cli-commands)
- [API Reference](#api-reference)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Installation

MPM Commander is included with the `claude-mpm` package:

```bash
pip install claude-mpm
```

### Basic Setup

1. **Start the Commander daemon:**

```bash
python -m claude_mpm.commander.daemon
```

The daemon will:
- Start on `http://127.0.0.1:8765` (default)
- Create state directory at `~/.claude-mpm/commander`
- Initialize tmux session for project management

2. **Verify daemon is running:**

```bash
curl http://127.0.0.1:8765/api/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Configuration

Create a custom configuration:

```python
from claude_mpm.commander.config import DaemonConfig

config = DaemonConfig(
    host="127.0.0.1",
    port=8765,
    log_level="INFO",
    state_dir=Path("~/.claude-mpm/commander"),
    max_projects=10,
    poll_interval=2.0,
    save_interval=30,
)
```

## CLI Commands

### Starting the Daemon

```bash
# Default configuration
python -m claude_mpm.commander.daemon

# With custom port
python -m claude_mpm.commander.daemon --port 9000

# With debug logging
python -m claude_mpm.commander.daemon --log-level DEBUG
```

### Stopping the Daemon

The daemon responds to graceful shutdown signals:

```bash
# Send SIGTERM for graceful shutdown
kill -TERM <daemon_pid>

# Or use Ctrl+C
# The daemon will:
# - Stop all active sessions
# - Persist state to disk
# - Clean up resources
```

## API Reference

### Base URL

```
http://127.0.0.1:8765/api
```

### Health Check

**GET** `/api/health`

Check daemon health status.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Projects

#### Register Project

**POST** `/api/projects`

```json
{
  "path": "/path/to/project",
  "name": "My Project"
}
```

**Response:**
```json
{
  "id": "project-abc123",
  "path": "/path/to/project",
  "name": "My Project",
  "state": "idle"
}
```

#### List Projects

**GET** `/api/projects`

**Response:**
```json
{
  "projects": [
    {
      "id": "project-abc123",
      "name": "My Project",
      "state": "idle"
    }
  ]
}
```

#### Get Project

**GET** `/api/projects/{project_id}`

**Response:**
```json
{
  "id": "project-abc123",
  "path": "/path/to/project",
  "name": "My Project",
  "state": "idle",
  "state_reason": null
}
```

#### Unregister Project

**DELETE** `/api/projects/{project_id}`

### Sessions

#### Create Session

**POST** `/api/sessions`

```json
{
  "project_id": "project-abc123"
}
```

#### Start Session

**POST** `/api/sessions/{project_id}/start`

Starts Claude Code runtime for the project.

#### Stop Session

**POST** `/api/sessions/{project_id}/stop`

Stops the active runtime and cleans up resources.

### Work Queue

#### Add Work Item

**POST** `/api/work`

```json
{
  "project_id": "project-abc123",
  "content": "Implement feature X",
  "priority": "high"
}
```

Priorities: `low`, `medium`, `high`, `critical`

#### List Work Items

**GET** `/api/work?project_id={project_id}`

Optional filters:
- `state`: Filter by state (`queued`, `in_progress`, `completed`, `failed`)
- `priority`: Filter by priority

#### Get Work Item

**GET** `/api/work/{work_id}`

#### Complete Work Item

**POST** `/api/work/{work_id}/complete`

```json
{
  "result": "Feature implemented successfully"
}
```

### Events

#### Get Pending Events

**GET** `/api/events/pending`

Optional filter:
- `project_id`: Show events for specific project

#### Resolve Event

**POST** `/api/events/{event_id}/resolve`

```json
{
  "resolution": "User confirmed action"
}
```

### Inbox

#### Submit Message

**POST** `/api/inbox`

```json
{
  "project_id": "project-abc123",
  "content": "User feedback: UI looks great!",
  "priority": "normal"
}
```

## Common Workflows

### 1. Start a New Project

```bash
# 1. Start daemon (if not running)
python -m claude_mpm.commander.daemon &

# 2. Register project via API
curl -X POST http://127.0.0.1:8765/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/project",
    "name": "My Project"
  }'

# 3. Create session
curl -X POST http://127.0.0.1:8765/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"project_id": "project-abc123"}'

# 4. Add work items
curl -X POST http://127.0.0.1:8765/api/work \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-abc123",
    "content": "Set up project structure",
    "priority": "high"
  }'
```

### 2. Handle Blocking Events

When a blocking event occurs:

```bash
# 1. Check pending events
curl http://127.0.0.1:8765/api/events/pending

# 2. Review event details
# Event will show:
# - title: What input is needed
# - content: Detailed context
# - project_id: Which project is affected

# 3. Resolve the event
curl -X POST http://127.0.0.1:8765/api/events/event-abc123/resolve \
  -H "Content-Type: application/json" \
  -d '{"resolution": "User approved action"}'

# 4. Execution automatically resumes
```

### 3. Monitor Project Progress

```bash
# Check work queue status
curl "http://127.0.0.1:8765/api/work?project_id=project-abc123"

# Check for pending events
curl "http://127.0.0.1:8765/api/events/pending?project_id=project-abc123"

# View inbox messages
curl "http://127.0.0.1:8765/api/inbox?project_id=project-abc123"
```

### 4. Graceful Shutdown and Restart

```bash
# 1. Stop daemon gracefully
kill -TERM $(pgrep -f "commander.daemon")

# Daemon will:
# - Stop all active sessions
# - Save state to ~/.claude-mpm/commander/
# - Exit cleanly

# 2. Restart daemon
python -m claude_mpm.commander.daemon

# 3. State automatically recovered:
# - All registered projects
# - Active sessions
# - Pending events
# - Work queue state
```

### 5. Working with Multiple Projects

```python
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.config import DaemonConfig

# Start daemon
config = DaemonConfig()
daemon = CommanderDaemon(config)
await daemon.start()

# Register multiple projects
project1 = daemon.registry.register("/path/to/project1", "Project 1")
project2 = daemon.registry.register("/path/to/project2", "Project 2")
project3 = daemon.registry.register("/path/to/project3", "Project 3")

# Create sessions for each
session1 = daemon.get_or_create_session(project1.id)
session2 = daemon.get_or_create_session(project2.id)
session3 = daemon.get_or_create_session(project3.id)

# Projects execute independently
# Events and work queues are isolated per project
```

## Troubleshooting

### Daemon Won't Start

**Problem:** Daemon fails to start or crashes immediately.

**Solutions:**

1. Check if port is already in use:
```bash
lsof -i :8765
```

2. Use a different port:
```bash
python -m claude_mpm.commander.daemon --port 9000
```

3. Check logs for errors:
```bash
python -m claude_mpm.commander.daemon --log-level DEBUG
```

4. Verify state directory permissions:
```bash
ls -la ~/.claude-mpm/commander/
```

### State Not Persisting

**Problem:** Projects/sessions lost after restart.

**Solutions:**

1. Verify state files exist:
```bash
ls -la ~/.claude-mpm/commander/
# Should see: projects.json, sessions.json, events.json
```

2. Check file permissions:
```bash
chmod 644 ~/.claude-mpm/commander/*.json
```

3. Enable debug logging to see save operations:
```bash
python -m claude_mpm.commander.daemon --log-level DEBUG
```

### Corrupt State Files

**Problem:** Daemon won't start, corrupt JSON errors.

**Solutions:**

1. Backup and remove corrupt files:
```bash
cd ~/.claude-mpm/commander/
mkdir backup_$(date +%s)
mv *.json backup_*/
```

2. Restart daemon (will create fresh state)

3. Re-register projects manually

### tmux Session Issues

**Problem:** Projects won't start, tmux errors.

**Solutions:**

1. Verify tmux is installed:
```bash
tmux -V
```

2. Check for orphaned sessions:
```bash
tmux list-sessions
```

3. Kill orphaned Commander sessions:
```bash
tmux kill-session -t commander
```

4. Restart daemon

### API Returns 500 Errors

**Problem:** API endpoints returning internal server errors.

**Solutions:**

1. Check daemon logs for stack traces

2. Verify request format matches API documentation

3. Test with health endpoint first:
```bash
curl http://127.0.0.1:8765/api/health
```

4. Try with debug logging enabled

### Work Items Not Executing

**Problem:** Work sits in queue but never starts.

**Solutions:**

1. Check session state:
```bash
curl http://127.0.0.1:8765/api/sessions/{project_id}
```

2. Verify no blocking events:
```bash
curl http://127.0.0.1:8765/api/events/pending
```

3. Check work item dependencies:
```bash
curl http://127.0.0.1:8765/api/work/{work_id}
```

4. Ensure session is running:
```bash
curl -X POST http://127.0.0.1:8765/api/sessions/{project_id}/start
```

### High Memory Usage

**Problem:** Daemon consuming excessive memory.

**Solutions:**

1. Reduce poll interval:
```python
config = DaemonConfig(poll_interval=5.0)  # Slower polling
```

2. Limit concurrent projects:
```python
config = DaemonConfig(max_projects=5)
```

3. Clean up completed work items periodically

4. Restart daemon regularly in production

## Advanced Configuration

### Custom State Directory

```python
config = DaemonConfig(
    state_dir=Path("/custom/path/to/state")
)
```

### Production Settings

```python
config = DaemonConfig(
    host="0.0.0.0",  # Accept external connections
    port=8765,
    log_level="WARNING",  # Less verbose logging
    save_interval=60,  # Save less frequently
    poll_interval=5.0,  # Slower polling
    max_projects=20,  # More concurrent projects
)
```

### Development Settings

```python
config = DaemonConfig(
    log_level="DEBUG",  # Verbose logging
    save_interval=5,  # Frequent saves
    poll_interval=0.5,  # Fast polling
    max_projects=3,  # Limited concurrency
)
```

## Next Steps

- See [API Reference](api-reference.md) for complete endpoint documentation
- See [Architecture](architecture.md) for system design details
- See [examples/](../../examples/) for code examples
- See [Testing Guide](testing-guide.md) for testing best practices
