---
description: Send cross-project messages to other Claude MPM instances
triggers:
  - /mpm-message
  - send message to
  - notify other project
  - cross-project communication
version: 1.0.0
author: Claude MPM Team
---

# Cross-Project Messaging

Send asynchronous messages to other Claude MPM instances running in different projects.

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

| Type | Use Case | Auto-Create Task |
|------|----------|------------------|
| **task** | Delegate work to another project | Yes (if enabled) |
| **request** | Ask for information or assistance | No |
| **notification** | Share status updates | No |
| **reply** | Respond to received messages | No |

## Priority Levels

- **urgent** 🔴 - Critical, immediate attention needed
- **high** 🟠 - Important, should be addressed soon
- **normal** 🟡 - Standard priority (default)
- **low** 🟢 - Can be addressed when convenient

## Receiving Messages

Messages are automatically checked and displayed in the recipient project via hook:
- ✅ Session start (always)
- ✅ Every 10 commands (configurable)
- ✅ Every 30 minutes (configurable)

### Manual Check
```bash
# Quick status
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

## Implementation Details

When you use `/mpm-message`, the PM will:

1. **Validate project path** - Ensure target project exists
2. **Send message** - Create message in target project's inbox
3. **Confirm delivery** - Report message ID and status
4. **Track in outbox** - Save copy in sender's outbox

### Python API (for direct use in code)

```python
from pathlib import Path
from claude_mpm.services.communication.message_service import MessageService

# Initialize service
project_root = Path.cwd()
service = MessageService(project_root)

# Send message
message = service.send_message(
    to_project="/Users/masa/Projects/web-app",
    to_agent="engineer",
    message_type="task",
    subject="Feature Request",
    body="Please implement OAuth2 authentication",
    priority="high",
    from_agent="pm"
)

print(f"Message sent: {message.id}")

# List unread messages
unread = service.list_messages(status="unread")
for msg in unread:
    print(f"{msg.priority}: {msg.subject}")

# Read and reply
message = service.read_message("msg-20260220-abc123")
reply = service.reply_to_message(
    original_message_id=message.id,
    subject="Re: Your request",
    body="Completed the implementation"
)
```

## Message Storage

Messages are stored as markdown files with YAML frontmatter:

**Location:**
- Inbox: `.claude-mpm/inbox/msg-*.md`
- Outbox: `.claude-mpm/outbox/msg-*.md`
- Archive: `.claude-mpm/inbox/.archive/msg-*.md`

**Format:**
```markdown
---
id: msg-20260220-abc123
from_project: /Users/masa/Projects/api-service
from_agent: pm
to_project: /Users/masa/Projects/web-app
to_agent: engineer
type: task
priority: high
created_at: 2026-02-20T20:15:00Z
status: unread
---

# Feature Request: OAuth2 Authentication

Please implement OAuth2 authentication using the authorization code flow.

Requirements:
- Google OAuth provider
- Secure token storage
- Refresh token handling
```

## Configuration

Customize messaging behavior in `.claude-mpm/config.yaml`:

```yaml
messaging:
  enabled: true                        # Enable/disable messaging system
  check_on_startup: true               # Check messages on session start
  command_threshold: 10                # Check every N commands
  time_threshold: 30                   # Check every N minutes
  auto_create_tasks: false             # Auto-create tasks from task messages
  notify_priority: ["high", "urgent"]  # Priority levels that trigger notifications
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

## Tips

1. **Use descriptive subjects** - Recipients see subject in notification
2. **Include context** - Assume recipient has no prior knowledge
3. **Specify priority appropriately** - High/urgent trigger immediate notifications
4. **Target specific agents** - Use `--to-agent` to direct work to right agent type
5. **Archive after handling** - Keep inbox clean with `claude-mpm message archive <id>`

## Troubleshooting

### Message not received?
- Verify target project path exists
- Check target project has `.claude-mpm/` directory
- Ensure recipient project has messaging enabled in config

### Not seeing notifications?
- Check configuration: `messaging.enabled: true`
- Verify notification priorities in config
- Check command/time thresholds

### Want immediate notification?
- Use `--priority urgent` when sending
- Configure `notify_priority: ["urgent", "high", "normal"]` to show all

## Example Workflow

```bash
# Project A sends task to Project B
cd /Users/masa/Projects/project-a
/mpm-message /Users/masa/Projects/project-b "Implement user registration API"

# Project B receives on next session start
cd /Users/masa/Projects/project-b
# [Claude Code session starts]
# 📬 Incoming Messages
# 1. 🔴 📋 Implement user registration API from project-a (pm)

# Project B reads and works on it
claude-mpm message read msg-20260220-abc123
# [PM delegates to engineer, work completed]

# Project B replies when done
claude-mpm message reply msg-20260220-abc123 --body "User registration API complete at /api/register"

# Project A receives notification
# 📬 Incoming Messages
# 1. 🟡 💬 Re: Implement user registration API from project-b (pm)
```

## Advanced: Auto-Task Creation

Enable automatic task creation from task messages:

```yaml
messaging:
  auto_create_tasks: true
```

When enabled:
1. Task-type messages automatically create tasks for target agent
2. PM can view tasks with `/tasks` or `TaskList`
3. Tasks include message context and sender information
4. Completing task sends automatic reply to sender

## Security Notes

- Messages are **local filesystem only** (no network transmission)
- Project paths must be **absolute paths**
- No authentication/encryption (messages are plaintext markdown)
- Suitable for **same-user cross-project communication**
- Not designed for **multi-user or remote communication**

## When to Use

✅ **Good use cases:**
- Coordinating work across multiple local projects
- Notifying dependent projects of changes
- Delegating tasks between microservices in development
- Sharing status updates across project boundaries

❌ **Not suitable for:**
- Remote/networked communication (use proper message queue)
- Multi-user collaboration (use project management tools)
- Production deployment coordination (use CI/CD)
- Secure/encrypted communication (no encryption support)

---

**Version**: 5.9.21-alpha.1
**Status**: Alpha - Feature branch testing
**Feedback**: Report issues to claude-mpm GitHub
