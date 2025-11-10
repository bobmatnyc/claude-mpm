# /mpm-resume - Load Previous Session

Load and display context from the most recent paused session to seamlessly continue your work.

## Usage

```
/mpm-resume
```

## Description

This command **loads and displays** the most recent paused session from automatic session saves, allowing you to resume work with full context restoration.

Unlike `/mpm-init pause` which *creates* a new session save, this command *loads* existing session data that was automatically created when context usage reached 70% (140k/200k tokens).

**Key Points:**
- Reads from `.claude-mpm/sessions/` directory (automatically created at 70% context)
- Displays up to ~40,000 tokens (~20% of 200k context budget)
- Shows session summary, completed work, in-progress tasks, and git context
- Does NOT create any new files - only reads and displays

## What Gets Displayed

When you run `/mpm-resume`, PM will display:

### Session Summary
- **Time Elapsed**: How long ago the session was paused
- **Context Usage**: Token usage at time of pause (e.g., "67.6% - 135,259/200,000 tokens")
- **Working On**: What you were working on when paused
- **Session Duration**: How long the previous session lasted

### Completed Work
- List of accomplishments from the paused session
- What was delivered and committed
- Key milestones achieved

### Current Tasks
- **In Progress**: Tasks that were being worked on
- **Pending**: Tasks that were planned but not started
- **Completed**: Recently finished tasks for context

### Git Context
- **Branch**: Current branch name
- **Recent Commits**: Last 5-10 commits with SHAs and messages
- **Status**: Clean/dirty working directory
- **Changes Since Pause**: New commits made since session was saved

### Next Recommended Actions
- Priority-ordered list of next steps
- Estimated time for each task
- Status and blockers for pending work

## Session Storage Location

Sessions are automatically saved to:
```
<project-root>/.claude-mpm/sessions/session-YYYYMMDD-HHMMSS.json
```

**Legacy location** (backward compatible):
```
<project-root>/.claude-mpm/sessions/pause/session-YYYYMMDD-HHMMSS.json
```

The system automatically checks both locations and uses the most recent session.

## Example Output

```
================================================================================
📋 PAUSED SESSION FOUND
================================================================================

Paused: 2 hours ago

Last working on: Week 2 Skills Integration - Content Preparation

Completed:
  ✓ Week 1: Complete infrastructure - 8,900 lines of production-ready code
  ✓ Week 1: Skills loading system with automatic progressive disclosure
  ✓ Week 2: 15 of 23 skills downloaded (65% complete)
  ✓ Week 2: 2 Tier 1 skills refactored to progressive disclosure
  ✓ Code quality: All CRITICAL and HIGH issues resolved

Next steps:
  • Refactor Tier 2 skills (verification-before-completion, webapp-testing)
  • Download remaining 8 skills from community repositories
  • Refactor remaining 13 skills to progressive disclosure
  • Generate license attributions for all bundled skills

Git changes since pause: 3 commits

Recent commits:
  ac765731 - feat(skills): Week 2 progress - 15 skills downloaded (Bob Matsuoka)
  205e532e - fix(skills): address CRITICAL and HIGH priority issues (Bob Matsuoka)
  06a6d6a0 - feat: add automated pre-publish cleanup to release (Bob Matsuoka)

Context Usage: 67.6% (135,259/200,000 tokens)
Session Duration: 12 hours

================================================================================
Use this context to resume work, or start fresh if not relevant.
================================================================================
```

## Implementation

When PM receives `/mpm-resume`, it should:

1. **Check for Sessions**
   ```python
   from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

   helper = SessionResumeHelper()
   if not helper.has_paused_sessions():
       return "No paused sessions found"
   ```

2. **Load Most Recent Session**
   ```python
   session_data = helper.get_most_recent_session()
   if not session_data:
       return "Failed to load session data"
   ```

3. **Format and Display Context**
   ```python
   # Extract key information
   conversation = session_data.get("conversation", {})
   git_context = session_data.get("git_context", {})
   context_usage = session_data.get("context_usage", {})
   todos = session_data.get("todos", {})

   # Display formatted output (see Example Output above)
   ```

4. **Calculate Git Changes**
   ```python
   # Get commits since pause
   paused_at = session_data.get("paused_at")
   new_commits = helper.get_git_changes_since_pause(paused_at, [])
   ```

5. **Limit Output to ~40k Tokens**
   - Session summary: ~2k tokens
   - Accomplishments (first 10): ~3k tokens
   - Next steps (first 10): ~3k tokens
   - Git context: ~5k tokens
   - Todos: ~2k tokens
   - Recent commits (up to 10): ~5k tokens
   - **Total**: ~20k tokens (well under 40k limit)

## Token Budget Management

**Context Budget**: 200,000 tokens total
**Resume Load**: ~20,000-40,000 tokens (10-20% of context)

This leaves 160,000+ tokens for actual work after loading session context.

## Session Data Format

Sessions are stored as JSON with this structure:

```json
{
  "session_id": "session-YYYYMMDD-HHMMSS",
  "paused_at": "ISO-8601 timestamp",
  "duration_hours": 12,
  "context_usage": {
    "tokens_used": 135259,
    "tokens_total": 200000,
    "percentage": 67.6
  },
  "conversation": {
    "primary_task": "What user was working on",
    "current_phase": "Current phase of work",
    "summary": "Brief summary",
    "accomplishments": ["list of completed items"],
    "next_steps": [
      {
        "priority": 1,
        "task": "Task description",
        "estimated_hours": "8-12",
        "status": "ready"
      }
    ]
  },
  "git_context": {
    "branch": "main",
    "recent_commits": [...],
    "status": {...}
  },
  "todos": {
    "active": [...],
    "completed": [...]
  }
}
```

## When to Use This Command

Use `/mpm-resume` when:
- **Starting a new session**: After closing and reopening Claude CLI
- **Context unclear**: You need to remember what you were working on
- **After a break**: Coming back after hours or days
- **Team handoff**: Another developer wants to understand current state
- **Lost context**: Accidentally closed CLI and need to recover

## Differences from Automatic Resume

| Feature | Automatic Resume (70% context) | /mpm-resume Command |
|---------|-------------------------------|---------------------|
| **Trigger** | Automatic at 70% context | Manual user command |
| **When** | PM startup (if session exists) | Anytime during session |
| **Creates Files** | No (reads existing) | No (reads existing) |
| **Session Source** | Same (`.claude-mpm/sessions/`) | Same (`.claude-mpm/sessions/`) |
| **Display Format** | Identical | Identical |
| **Token Usage** | ~20-40k tokens | ~20-40k tokens |

Both features use the **same underlying system** (`SessionResumeHelper`), just triggered differently.

## No Files Created

**IMPORTANT**: This command does NOT create any new files.

It ONLY reads from existing session files that were automatically created by the system at 70% context usage.

If you want to manually create a session save (for example, at 50% context before hitting 70%), use a different workflow or wait for automatic save at 70%.

## Related Features

- **Automatic Session Save**: System creates sessions at 70% context automatically
- **Automatic Session Resume**: PM startup hook displays sessions automatically
- `/mpm-init pause`: Manual session pause workflow (if available)
- `/mpm-init context`: Analyze git history for intelligent resumption
- `/mpm-status`: Check current MPM status

## Error Handling

### No Sessions Found
```
No paused sessions found in .claude-mpm/sessions/

To create a session save, continue working until context reaches 70% (140k tokens),
at which point the system will automatically save your session state.
```

### Failed to Load Session
```
Paused session file found but failed to load.

File: .claude-mpm/sessions/session-20251107-152740.json
Error: Invalid JSON format

You may need to manually inspect or delete this file.
```

### Invalid Session Format
```
Session file loaded but missing required fields.

The session file may be corrupted or from an older version.
Consider running /mpm-doctor to check system health.
```

## Benefits

- **Instant Context**: Get full context in seconds without reading git logs
- **No Mental Load**: Don't need to remember what you were doing
- **Zero File Creation**: Pure read operation, no side effects
- **Team Collaboration**: Share context with team members
- **Graceful Recovery**: Recover from accidental CLI closures
- **Smart Filtering**: Only shows relevant information (~20k tokens)
- **Git Awareness**: See what changed since pause

## Best Practices

1. **Use Early**: Run `/mpm-resume` at start of each session if sessions exist
2. **Check Git Changes**: Pay attention to commits made since pause
3. **Validate Context**: Verify the session is still relevant before continuing
4. **Clear Old Sessions**: Periodically clean up old session files
5. **Combine with Git**: Use alongside `git log` for complete picture

## Technical Details

**Implementation Files:**
- Service: `/src/claude_mpm/services/cli/session_resume_helper.py`
- Hook: `/src/claude_mpm/hooks/session_resume_hook.py`
- Command: This file

**Key Functions:**
- `SessionResumeHelper.has_paused_sessions()` - Check if sessions exist
- `SessionResumeHelper.get_most_recent_session()` - Load latest session
- `SessionResumeHelper.format_resume_prompt()` - Format display output
- `SessionResumeHelper.get_git_changes_since_pause()` - Calculate git delta

**Token Estimation:**
- Session metadata: 1-2k tokens
- Accomplishments (10 items): 2-4k tokens
- Next steps (10 items): 2-4k tokens
- Git commits (10 commits): 3-5k tokens
- Todos (20 items): 2-3k tokens
- Formatting/structure: 1-2k tokens
- **Total**: 11-20k tokens (safely under 40k limit)

## Troubleshooting

### Session Not Found
**Problem**: Command reports no sessions exist

**Solutions:**
1. Check directory exists: `ls .claude-mpm/sessions/`
2. Check for legacy location: `ls .claude-mpm/sessions/pause/`
3. Verify session files: `ls .claude-mpm/sessions/session-*.json`
4. Session auto-saves at 70% context - may not exist yet

### Git Changes Not Showing
**Problem**: "No git changes since pause" but commits were made

**Solutions:**
1. Verify git repository: `git status`
2. Check commit timestamps: `git log --since="<pause_time>"`
3. Ensure session timestamp is correct
4. Check timezone issues

### Display Too Large
**Problem**: Session context exceeds token budget

**Solutions:**
1. System automatically limits to first 10 items
2. Full session details available in JSON file
3. Use `cat .claude-mpm/sessions/session-*.json` for complete data
4. Summary is optimized for 20k tokens max

## Example Session Resume Workflow

```bash
# User starts new Claude CLI session
$ claude-code

# PM automatically checks for sessions on startup
# (Automatic resume hook displays session if found)

# OR user manually requests resume
User: "/mpm-resume"

# PM loads and displays session context
PM: [Displays formatted session context as shown in Example Output]

# User decides to continue work
User: "Let's continue with the next priority task"

# PM uses session context to understand what to do next
PM: "Based on the paused session, the next priority is to refactor
     the verification-before-completion skill. I'll delegate this to Engineer..."
```

## Version History

- **v4.21.1**: Fixed command behavior - now loads sessions instead of creating files
- **v4.21.0**: Added `/mpm-resume` command (incorrect behavior - created files)
- **v4.19.0**: Automatic session resume infrastructure implemented
- **v4.18.x**: Session pause/resume foundation

## Support

For issues or questions:
- Run `/mpm-doctor` to check system health
- Check logs: `.claude-mpm/logs/claude-mpm.log`
- Verify session files: `ls -la .claude-mpm/sessions/`
- Review documentation: `/docs/features/session-auto-resume.md`
