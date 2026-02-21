# Task Injection for Cross-Project Messages

## Overview

The TaskInjector module enables cross-project messages to automatically appear as tasks in Claude Code's native task system. When messages arrive from other Claude MPM instances, they can be injected as tasks that the PM agent will see and process.

## How It Works

1. **Messages arrive** in a project's inbox (`.claude-mpm/inbox/`)
2. **Message check hook** detects unread messages (runs every 10 commands or 30 minutes)
3. **TaskInjector** creates JSON task files in `~/.claude/tasks/`
4. **Claude Code** picks up these tasks via its built-in TaskList tool
5. **PM agent** sees and processes the message tasks

## Architecture

```
Project A                   Project B                    Claude Code
---------                   ---------                    -----------
Send message      →         Receive in inbox
                           ↓
                           Message check hook runs
                           ↓
                           TaskInjector.inject_message_task()
                           ↓
                           Creates ~/.claude/tasks/msg-*.json
                                                        ↓
                                                        TaskList reads JSON
                                                        ↓
                                                        PM sees task
```

## Configuration

In your `config.yml`:

```yaml
messaging:
  enabled: true
  auto_create_tasks: true      # Enable task injection
  notify_priority:              # Only inject these priorities as tasks
    - urgent
    - high
  command_threshold: 10         # Check messages every N commands
  time_threshold: 30            # Check messages every N minutes
```

## Task Format

Messages are converted to tasks with:

- **ID**: `msg-{message-id}` - Prefixed to identify message tasks
- **Title**: `📬 Message from {project}: {subject}`
- **Priority Mapping**:
  - `urgent` → `high`
  - `high` → `high`
  - `normal` → `medium`
  - `low` → `low`
- **Status**: Always starts as `pending`
- **Description**: Full message details with handling instructions

## Usage

### Automatic Injection

When `auto_create_tasks` is enabled, high-priority messages automatically become tasks:

```python
# This happens automatically in message_check_hook
from claude_mpm.services.communication.task_injector import TaskInjector

injector = TaskInjector()

# Check if task already exists (deduplication)
if not injector.task_exists(message.id):
    # Inject as task
    injector.inject_message_task(
        message_id=message.id,
        from_project=message.from_project,
        subject=message.subject,
        body=message.body,
        priority=message.priority,
        from_agent=message.from_agent,
        message_type=message.type
    )
```

### Manual Injection

You can also manually inject messages as tasks:

```python
from claude_mpm.services.communication.task_injector import TaskInjector

injector = TaskInjector()

# Inject a specific message
task_file = injector.inject_message_task(
    message_id="msg-123",
    from_project="/home/user/other-project",
    subject="Review pull request",
    body="Please review PR #456 for the auth feature",
    priority="high",
    from_agent="engineer",
    message_type="request"
)

print(f"Created task: {task_file}")
```

### Task Management

```python
# Check if task exists
if injector.task_exists("msg-123"):
    print("Task already created for this message")

# List all message tasks
tasks = injector.list_message_tasks()
for task in tasks:
    print(f"{task['id']}: {task['title']}")

# Remove task (e.g., when message is archived)
injector.remove_task("msg-123")

# Clean up completed tasks
removed_count = injector.cleanup_completed_tasks()
print(f"Removed {removed_count} completed tasks")
```

## Task Lifecycle

1. **Created**: Message arrives, task injected as `pending`
2. **Seen**: PM agent sees task in TaskList
3. **Processing**: PM reads message, takes action
4. **Completed**: PM marks task as `completed` after handling
5. **Cleaned**: Periodic cleanup removes old completed tasks

## Benefits

✅ **Native Integration**: Uses Claude's built-in task system
✅ **Visible to PM**: Tasks appear automatically in TaskList
✅ **Prioritization**: Urgent messages become high-priority tasks
✅ **Trackable**: Task status tracks message handling
✅ **Simple**: Just JSON file writes
✅ **Reliable**: File system is the queue

## Limitations

- **Notification delay**: Tasks only created when hook runs (not real-time)
- **Task list clutter**: Many messages = many tasks (use priority filter)
- **Manual completion**: PM must mark task complete after handling

## Testing

Run the test suite:

```bash
# Unit tests
pytest tests/services/communication/test_task_injector.py

# Integration tests
pytest tests/integration/test_message_task_integration.py

# Demo script
python scripts/demo_task_injection.py
```

## Implementation Files

- **Module**: `src/claude_mpm/services/communication/task_injector.py`
- **Integration**: `src/claude_mpm/hooks/message_check_hook.py`
- **Tests**: `tests/services/communication/test_task_injector.py`
- **Demo**: `scripts/demo_task_injection.py`