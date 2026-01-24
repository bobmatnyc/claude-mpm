# TaskList Session Integration

## Overview

TaskList state is automatically captured when sessions are paused and displayed on resume. This feature provides seamless task continuity across Claude Code sessions, ensuring no work is lost during context switches or session breaks.

When a session is paused (manually or via auto-pause at 70% context), any pending or in-progress tasks from Claude Code's `~/.claude/tasks/` directory are captured and stored in the session files. On resume, these tasks are displayed to help users quickly understand what work was in progress.

## How It Works

### Session Pause (Capture)

When a session is paused via `/mpm-session-pause`, the `SessionPauseManager` captures TaskList state:

```
SessionPauseManager.create_pause_session()
    └── _capture_task_list_state()
            │
            ├── Reads ~/.claude/tasks/*.json files
            ├── Categorizes tasks by status:
            │   - pending_tasks: tasks with status "pending" or "todo"
            │   - in_progress_tasks: tasks with status "in_progress"
            │   - completed_count: count of "completed" or "done" tasks
            │
            └── Stores under "task_list" key in session JSON/YAML/MD
```

**Task data captured per task:**
- `id` - Task identifier
- `title` - Task title
- `description` - Task description
- `priority` - Task priority level
- `created_at` - Creation timestamp
- `file` - Source file path

### Session Resume (Display)

When a session resumes, the `SessionResumeStartupHook` displays task status:

```
SessionResumeStartupHook.on_pm_startup()
    │
    ├── check_for_active_pause()
    │   └── Reads ACTIVE-PAUSE.jsonl for auto-pause sessions
    │       └── Extracts task_list from last action
    │
    └── _format_task_list_summary()
            │
            └── Formats output:
                  Pending Tasks:
                    - [task-1] Task title here
                    - [task-2] Another task
                  In Progress:
                    - [task-3] Current work
```

### SessionStart Event Data

The `SessionStart` hook event includes task information for dashboard integration:

```python
session_start_data = {
    "session_id": "...",
    "has_pending_tasks": True,   # Boolean flag
    "pending_task_count": 3,     # Total pending + in_progress
    ...
}
```

This is populated by `_check_paused_session_tasks()` in `event_handlers.py`, which:
1. Checks `ACTIVE-PAUSE.jsonl` for incremental auto-pause sessions
2. Falls back to `LATEST-SESSION.txt` for regular paused sessions
3. Extracts and counts pending/in-progress tasks

## Session File Structure

Tasks are stored in the session JSON under the `task_list` key:

```json
{
  "session_id": "session-20260124-103045",
  "paused_at": "2026-01-24T10:30:45Z",
  "task_list": {
    "pending_tasks": [
      {
        "id": "task-1",
        "title": "Implement authentication",
        "description": "Add OAuth2 flow",
        "priority": "high",
        "created_at": "2026-01-24T09:00:00Z",
        "file": "/Users/user/.claude/tasks/task-1.json"
      }
    ],
    "in_progress_tasks": [
      {
        "id": "task-2",
        "title": "Fix database connection",
        "description": "Handle reconnection on timeout",
        "priority": "medium",
        "created_at": "2026-01-24T09:30:00Z",
        "file": "/Users/user/.claude/tasks/task-2.json"
      }
    ],
    "completed_count": 5
  },
  ...
}
```

## Benefits

- **Seamless continuity**: Resume work exactly where you left off
- **Task visibility**: See pending tasks immediately on session start
- **Progress tracking**: Know how many tasks were completed before pause
- **Dashboard integration**: `has_pending_tasks` flag enables UI notifications
- **Auto-pause support**: Works with both manual and automatic pause (70% context)

## Configuration

**No configuration required.** The feature is automatic when using:
- `/mpm-session-pause` - Manual session pause
- Auto-pause at 70% context threshold
- `/mpm-session-resume` - Session resume

Task capture only occurs if:
1. The `~/.claude/tasks/` directory exists
2. Valid JSON task files are present

If no tasks directory exists, `task_list` will have empty arrays and zero counts.

## Code Locations

| Component | File |
|-----------|------|
| Task capture on pause | `src/claude_mpm/services/cli/session_pause_manager.py` |
| Task display on resume | `src/claude_mpm/hooks/session_resume_hook.py` |
| SessionStart event enrichment | `src/claude_mpm/hooks/claude_hooks/event_handlers.py` |

**Key methods:**
- `SessionPauseManager._capture_task_list_state()` - Reads and categorizes tasks
- `SessionResumeStartupHook._format_task_list_summary()` - Formats display output
- `EventHandlers._check_paused_session_tasks()` - Enriches SessionStart events

## Related

- **Skills**: `/mpm-session-pause`, `/mpm-session-resume`
- **Issue**: #245 (TaskList Session Integration)
- **Auto-pause**: See `docs/incremental-pause-workflow.md`
- **Session files**: `.claude-mpm/sessions/`
