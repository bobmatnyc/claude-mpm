---
name: mpm-message
description: Send cross-project messages to other Claude MPM instances
user-invocable: true
version: "3.0.0"
category: mpm-command
tags: [mpm-command, communication, pm-required]
effort: low
---

# Cross-Project Messaging

Send asynchronous messages to other Claude MPM instances running in different projects.

> **Important**: Always use `claude-mpm message` CLI commands or the `MessageService` Python API.
> Never query `messaging.db` directly — the database location is an implementation detail.

## ⚠️ Common Traps

### Attribute name: `msg.type` NOT `msg.message_type`
When **reading** a returned `Message` object, the field is `msg.type`.
When **sending**, the parameter is `message_type=` (matches DB column).
Confusing these causes `AttributeError: 'Message' object has no attribute 'message_type'`.

```python
# WRONG — causes AttributeError
print(msg.message_type)

# CORRECT
print(msg.type)
```

### Use the CLI or MessageService — never raw SQL or direct DB access
The PM must NEVER access `messaging.db` directly with sqlite3 or raw Python one-liners.
Always use:
- CLI: `claude-mpm message list / read / send / reply`
- Python: `MessageService(Path.cwd())` — see API reference below

### CLI Quick Reference
```bash
claude-mpm message list                          # all messages
claude-mpm message list --status unread          # unread only
claude-mpm message read <message-id>             # read + mark as read
claude-mpm message send /path/to/project \
  --subject "Subject" --body "Body" \
  --type task --priority high --to-agent pm
claude-mpm message reply <message-id> --body "Response"
claude-mpm message archive <message-id>
```

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

### CLI
```bash
# Send a message
claude-mpm message send <project-path> \
  --body "message content" \
  --subject "message subject" \
  --type [task|request|notification|reply] \
  --priority [low|normal|high|urgent] \
  --to-agent [pm|engineer|qa|ops|etc]

# For complex bodies with quotes, use --body-file
claude-mpm message send <project-path> --body-file message.txt --subject "subject"
echo "body text" | claude-mpm message send <project-path> --body-file - --subject "subject"

# Inbox operations
claude-mpm message check                          # Quick unread count
claude-mpm message list                            # List all messages
claude-mpm message list --status unread            # List unread only
claude-mpm message read <message-id>               # Read a message
claude-mpm message reply <message-id> --body "response"
claude-mpm message reply <message-id> --body-file reply.txt  # From file
claude-mpm message archive <message-id>
claude-mpm message sessions                        # List active sessions
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

### Reading Messages (CLI)
Always use the CLI to check messages — never query the database directly:
```bash
# Quick unread count
claude-mpm message check

# List unread messages
claude-mpm message list --status unread

# Read a specific message
claude-mpm message read <message-id>
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

**Version**: 5.9.27+
**Status**: Stable
**Issues**: #305, #310, #311, #312
