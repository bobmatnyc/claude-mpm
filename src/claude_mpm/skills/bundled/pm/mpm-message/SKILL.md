---
description: Send cross-project messages to other Claude MPM instances
triggers:
  - /mpm-message
  - send message to
  - notify other project
  - cross-project communication
version: 2.0.0
author: Claude MPM Team
---

# Cross-Project Messaging

Send asynchronous messages to other Claude MPM instances running in different projects. Messages are stored in SQLite databases and high-priority messages are automatically injected as tasks into Claude Code's native task system.

## How It Works

1. **Send**: You send a message to another project using `/mpm-message`
2. **Store**: Message is written to the target project's SQLite inbox (`.claude-mpm/messaging.db`)
3. **Detect**: Target project's message check hook detects unread messages periodically
4. **Inject**: High-priority messages are injected as tasks to `~/.claude/tasks/` (Claude Code native)
5. **Act**: PM sees the task in `TaskList` and processes it like any other task
6. **Reply**: PM sends reply back to the originating project

## Usage

### Quick Send (Skill Syntax)
```
/mpm-message <project-path> <message>
```

**Example:**
```
/mpm-message /Users/masa/Projects/web-app "Please implement user authentication feature"
```

### Full Command Syntax
```bash
claude-mpm message send <project-path> \
  --body "message content" \
  --subject "message subject" \
  --type [task|request|notification|reply] \
  --priority [low|normal|high|urgent] \
  --to-agent [pm|engineer|qa|ops|etc] \
  --from-agent [pm|engineer|qa|etc]
```

## Message Types

| Type | Use Case | Auto-Inject Task |
|------|----------|-----------------|
| **task** | Delegate work to another project | Yes (urgent/high priority) |
| **request** | Ask for information or assistance | Yes (urgent/high priority) |
| **notification** | Share status updates | No (notification only) |
| **reply** | Respond to received messages | No (notification only) |

## Priority Levels

- **urgent** - Critical, auto-injected as high-priority task
- **high** - Important, auto-injected as high-priority task
- **normal** - Standard priority, notification only (default)
- **low** - Can be addressed when convenient, notification only

## Receiving Messages

### Automatic Detection (via Hook)
Messages are checked periodically:
- Session start (always)
- Every 10 commands (configurable)
- Every 30 minutes (configurable)

When detected:
- **Urgent/High priority**: Automatically injected as task in `TaskList`
- **Normal/Low priority**: Shown as notification in PM context

### Task Injection
High-priority messages appear as tasks with `msg-` prefix:
```
TaskList shows:
  📬 Message from web-app: Implement /auth endpoint (high priority)
```

The task description contains the full message and instructions for handling.

### Manual Commands
```bash
# Quick status check
claude-mpm message check

# List all messages
claude-mpm message list

# Filter by status
claude-mpm message list --status unread

# Read specific message
claude-mpm message read <message-id>
```

## Reply to Messages

```bash
# Reply to a received message
claude-mpm message reply <message-id> --body "your reply"
```

## Session Registry

Active Claude MPM sessions register themselves for peer discovery:

```bash
# List active peer sessions
claude-mpm message sessions

# Session registry location: ~/.claude-mpm/session-registry.db
```

Sessions register on start, heartbeat periodically, and deregister on exit.

## Message Storage

Messages are stored in SQLite databases:

**Location:**
- Per-project inbox/outbox: `.claude-mpm/messaging.db`
- Global session registry: `~/.claude-mpm/session-registry.db`
- Injected tasks: `~/.claude/tasks/msg-*.json`

**Database Tables:**
- `messages` — All message data with status tracking
- `sessions` — Session registry with heartbeat

## Configuration

Customize messaging behavior in `.claude-mpm/config.yaml`:

```yaml
messaging:
  enabled: true                              # Enable/disable messaging system
  check_on_startup: true                     # Check messages on session start
  command_threshold: 10                      # Check every N commands
  time_threshold: 30                         # Check every N minutes
  auto_create_tasks: true                    # Inject messages as Claude Code tasks
  task_priority_filter: ["urgent", "high"]   # Which priorities trigger task injection
```

## Use Cases

### 1. Coordinated Feature Development
```
Project A (API): /mpm-message /path/to/project-b "API endpoints ready for /auth and /user"
Project B (Web): Receives notification, implements frontend
Project B (Web): /mpm-message /path/to/project-a "Frontend complete, ready for testing"
```

### 2. Cross-Team Notifications
```
Backend Team: /mpm-message /path/to/frontend "Database schema updated, see migration guide"
```

### 3. Dependency Updates
```
Library Project: /mpm-message /path/to/app "New version 2.0 released with breaking changes"
```

### 4. Task Delegation
```
Main Project: /mpm-message /path/to/microservice "Scale up worker pool, traffic spike expected"
```

## Example Workflow

```bash
# Project A sends task to Project B
/mpm-message /Users/masa/Projects/project-b "Implement user registration API"

# Project B session detects message via hook
# High priority → task injected to ~/.claude/tasks/
# PM sees in TaskList:
#   📬 Message from project-a: Implement user registration API

# PM processes task, delegates to engineer
# Engineer implements the feature

# PM replies when done
claude-mpm message reply msg-20260220-abc123 --body "User registration API complete at /api/register"

# Project A receives reply notification on next hook check
```

## Handling Messages as PM

When you see `📬` tasks in your task list:

1. **Read the task description** — Contains full message details
2. **Delegate appropriately** — Task type messages should be delegated to the right agent
3. **Reply when complete** — Use `claude-mpm message reply` to notify sender
4. **Archive when done** — `claude-mpm message archive <id>` to clean up

## Troubleshooting

### Message not received?
- Verify target project path exists and is absolute
- Check target project has `.claude-mpm/` directory
- Ensure messaging is enabled in recipient's config

### Not seeing task injections?
- Check `auto_create_tasks: true` in config
- Verify message priority is in `task_priority_filter`
- Check `~/.claude/tasks/` directory exists

### Not seeing notifications?
- Check `messaging.enabled: true`
- Verify hook thresholds (command_threshold, time_threshold)

## Limitations

- **Not real-time** — Messages checked periodically (every 10 commands / 30 minutes)
- **Local filesystem only** — Same user, same machine (no network)
- **No encryption** — Messages stored as plaintext in SQLite
- **Notification-based** — PM must be active in session to process messages

## Security Notes

- Messages are **local filesystem only** (no network transmission)
- Project paths must be **absolute paths**
- No authentication/encryption (plaintext SQLite storage)
- Suitable for **same-user cross-project communication**
- Not designed for **multi-user or remote communication**

---

**Version**: 5.9.21-alpha.1
**Status**: Alpha - Feature branch testing
**Issues**: #305, #306, #307, #308
