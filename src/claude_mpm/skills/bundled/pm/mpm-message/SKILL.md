---
description: Send cross-project messages to other Claude MPM instances
triggers:
  - /mpm-message
  - send message to
  - notify other project
  - cross-project communication
version: 3.0.0
author: Claude MPM Team
---

# Cross-Project Messaging

Send asynchronous messages to other Claude MPM instances running in different projects.

> **Version note**: The `claude-mpm message` CLI is available in **v5.9.21-beta.8+**.
> On older versions, use the **Python API fallback** below.
> Check your version: `claude-mpm --version`

## How It Works

1. **Send**: Message written to shared SQLite database (`~/.claude-mpm/messaging.db`)
2. **Detect**: Target project's message check hook detects unread messages periodically
3. **Read**: PM reads message and decides what local tasks to create
4. **Reply**: PM sends reply back to originating project

All messages flow through a **single shared database** at `~/.claude-mpm/messaging.db`. No per-project databases.

## Usage

### Quick Send (Skill Syntax)
```
/mpm-message <project-path> <message>
```

### CLI (v5.9.21-beta.8+)
```bash
claude-mpm message send <project-path> \
  --body "message content" \
  --subject "message subject" \
  --type [task|request|notification|reply] \
  --priority [low|normal|high|urgent] \
  --to-agent [pm|engineer|qa|ops|etc]

claude-mpm message list
claude-mpm message read <message-id>
claude-mpm message reply <message-id> --body "response"
claude-mpm message archive <message-id>
```

### Python API (PREFERRED fallback for all versions)
```python
from pathlib import Path
from claude_mpm.services.communication.message_service import MessageService

service = MessageService(Path.cwd())
msg = service.send_message(
    to_project='/path/to/target/project',
    to_agent='pm',
    message_type='notification',  # task | request | notification | reply
    subject='Subject here',
    body='Body content here',
    priority='high',              # urgent | high | normal | low
    from_agent='pm',
)
print(f"Sent: {msg.id}")

# List unread
unread = service.list_messages(status="unread")
for m in unread:
    print(f"[{m.priority}] {m.subject}")

# Read and reply
message = service.read_message("msg-id-here")
reply = service.reply_to_message("msg-id-here", subject="Re: ...", body="Done!")
```

> **Note**: `send_message()` takes `message_type=` (not `type=`) — this matches the DB schema column name.

## ⚠️ Anti-Pattern: Never Write Directly to messaging.db

Do NOT use raw SQLite INSERT statements to send messages. This bypasses the abstraction layer and **will break** when the Huey message bus migration lands (#311).

**Wrong:**
```python
# ❌ NEVER DO THIS
conn.execute("INSERT INTO messages (type, ...) VALUES ...")
```

**Right:**
```python
# ✅ ALWAYS USE MessageService
service = MessageService(Path.cwd())
service.send_message(to_project=..., message_type=..., ...)
```

The DB column is `message_type`, not `type` — direct writes get this wrong and create schema-mismatched records.

## Message Types

| Type | Use Case |
|------|----------|
| **task** | Delegate work to another project |
| **request** | Ask for information or assistance |
| **notification** | Share status updates |
| **reply** | Respond to received messages |

## Priority Levels

- **urgent** - Critical, immediate attention
- **high** - Important, should be addressed soon
- **normal** - Standard priority (default)
- **low** - Address when convenient

## Receiving Messages

### Automatic Detection (via Hook)
- Session start (always)
- Every 10 commands (configurable)
- Every 30 minutes (configurable)

### Reading Messages (from SQLite)
If the hook hasn't fired, check directly:
```bash
sqlite3 ~/.claude-mpm/messaging.db \
  "SELECT id, subject, priority, status FROM messages WHERE to_project='$(pwd)' AND status='unread'"
```

## Message Storage

**Single shared database**: `~/.claude-mpm/messaging.db`

All projects read from and write to the same database. Messages are filtered by `to_project` on read.

## Configuration

```yaml
messaging:
  enabled: true
  check_on_startup: true
  command_threshold: 10
  time_threshold: 30
  auto_create_tasks: true
  task_priority_filter: ["urgent", "high"]
```

## Architecture: Messages ≠ Tasks

**Messages** are just messages — peer-to-peer communication.
**Tasks** are local decisions. When PM reads a message, the **local PM** decides what tasks to create based on its own context.

The sending project should NOT inject tasks — it doesn't have the recipient's context.

## Limitations

- **Not real-time** — Checked periodically (every 10 commands / 30 minutes)
- **Local filesystem only** — Same user, same machine
- **No encryption** — Plaintext SQLite storage

## Forward Compatibility

The current implementation uses SQLite directly. A Huey-based message bus migration is planned (#311). **Always use `MessageService`** to ensure your code works after the migration. Do not write to `messaging.db` directly.

---

**Version**: 5.9.21-beta.9+
**Status**: Beta
**Issues**: #305, #310, #311, #312
