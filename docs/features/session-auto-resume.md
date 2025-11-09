# Automatic Session Resume

## Overview

Claude MPM automatically manages session continuity through two key features:

1. **Automatic Session Creation**: When context usage reaches 70% (140k/200k tokens), the system automatically creates a session resume file to preserve your work context
2. **Automatic Session Detection**: When PM starts, it detects and displays paused sessions, helping you seamlessly continue your work with full context restoration

This ensures you never lose progress and can work across multiple sessions without missing a beat.

## How It Works

### 1. Automatic Session Creation

**NEW**: Sessions are now automatically created when context usage reaches **70% (140k/200k tokens)**.

The system monitors token usage and:
- **At 70%**: Automatically creates a session resume file and prompts you to review
- **At 85%**: Blocks new work until session is managed
- **At 95%**: Emergency threshold - requires immediate action

This ensures you never lose context and can seamlessly resume work across sessions.

### 2. Session Detection

When PM starts, the system automatically:
- Checks for paused sessions in `<project>/.claude-mpm/sessions/` (also checks legacy sessions/pause/ location for backward compatibility)
- Identifies the most recent paused session
- Calculates git changes since the session was paused
- Displays resume context to the user

### 3. Resume Context Display

The auto-resume prompt shows:
- **Time elapsed**: How long ago the session was paused
- **Work summary**: What you were working on
- **Accomplishments**: What was completed in that session
- **Next steps**: Planned actions from the paused session
- **Git changes**: Commits made since the session was paused
- **Time context**: When the session was paused

### 4. Example Display

```
================================================================================
📋 PAUSED SESSION FOUND
================================================================================

Paused: 2 hours ago

Last working on: Implementing automatic session resume functionality

Completed:
  ✓ Created SessionResumeHelper service
  ✓ Enhanced git change detection
  ✓ Added auto-resume to PM startup

Next steps:
  • Test auto-resume with real session data
  • Update documentation

Git changes since pause: 3 commits

Recent commits:
  a1b2c3d - feat: add SessionResumeHelper service (Engineer)
  e4f5g6h - test: add session resume tests (QA)
  i7j8k9l - docs: update PM_INSTRUCTIONS.md (Documentation)

================================================================================
Use this context to resume work, or start fresh if not relevant.
================================================================================
```

## Features

### Git Change Detection

The system automatically:
- Compares current git state with paused session state
- Counts new commits since pause
- Displays recent commit summaries
- Shows author and timestamp information

### Time Calculation

Human-readable time elapsed:
- "just now" - less than 1 minute
- "5 minutes ago" - less than 1 hour
- "2 hours ago" - less than 1 day
- "3 days ago" - more than 1 day

### Smart Session Selection

When multiple paused sessions exist:
- Most recent session is selected
- Based on file modification time
- Ensures latest context is presented

## Session Pause Document Format

Sessions are stored in `<project>/.claude-mpm/sessions/session-YYYYMMDD-HHMMSS.json`:

```json
{
  "session_id": "session-YYYYMMDD-HHMMSS",
  "paused_at": "ISO-8601 timestamp",
  "conversation": {
    "summary": "What user was working on",
    "accomplishments": ["list of completed items"],
    "next_steps": ["list of planned next actions"]
  },
  "git_context": {
    "is_git_repo": true,
    "branch": "current branch name",
    "recent_commits": [
      {
        "sha": "commit hash",
        "author": "author name",
        "timestamp": "commit timestamp",
        "message": "commit message"
      }
    ],
    "status": {
      "clean": true,
      "modified_files": [],
      "untracked_files": []
    }
  },
  "todos": {
    "active": [{"status": "in_progress", "content": "task", "activeForm": "doing task"}],
    "completed": [{"status": "completed", "content": "done task"}]
  },
  "version": "claude-mpm version",
  "build": "build number",
  "project_path": "absolute path"
}
```

## Storage Location

### Project-Specific Sessions

Sessions are stored per-project in:
```
<project-root>/.claude-mpm/sessions/
```

This ensures:
- ✓ Sessions are project-specific
- ✓ No cross-project contamination
- ✓ Easy cleanup (delete .claude-mpm directory)
- ✓ Git-ignorable by default

**Note**: The system also checks the legacy `sessions/pause/` location for backward compatibility with older session files.

### File Permissions

Session files are created with `0600` permissions (user read/write only) for security.

## Integration Points

### PM Startup Hook

The auto-resume functionality integrates with PM startup via:

```python
from claude_mpm.hooks import trigger_session_resume_check

# In PM startup sequence
session_data = trigger_session_resume_check()
if session_data:
    # Session context has been displayed to user
    # Continue with normal PM startup
```

### Manual Session Check

You can also manually check for sessions:

```python
from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

helper = SessionResumeHelper()

# Check if sessions exist
if helper.has_paused_sessions():
    # Get session count
    count = helper.get_session_count()

    # Get most recent session
    session = helper.get_most_recent_session()

    # Display resume prompt
    helper.check_and_display_resume_prompt()
```

## Commands

### Pause Current Session

Use `/mpm-init pause` (if implemented in your version) or manually:

```bash
# Create pause session manually
python -c "
from claude_mpm.services.cli.session_pause_manager import SessionPauseManager
manager = SessionPauseManager()
manager.pause_session('Working on feature X')
"
```

### List Paused Sessions

```bash
ls -la .claude-mpm/sessions/
```

### Clear Paused Sessions

```bash
# Remove all paused sessions
rm .claude-mpm/sessions/session-*.json
```

### Clear Specific Session

```python
from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

helper = SessionResumeHelper()
session = helper.get_most_recent_session()

if session:
    helper.clear_session(session)
```

## Benefits

### 1. Seamless Work Continuation

- **Context restoration**: Immediately understand where you left off
- **Git awareness**: See what changed while you were away
- **Next steps clarity**: Know what to work on next

### 2. Team Collaboration

- **Handoff support**: Team members can see what was being worked on
- **Progress tracking**: Clear record of accomplishments
- **Work stream visibility**: Git changes show team activity

### 3. Long Breaks

- **Memory aid**: Recall context after days or weeks
- **Work reconstruction**: Understand project state evolution
- **Decision tracking**: See what decisions were made

## Technical Details

### Implementation Files

**Core Service**:
- `/src/claude_mpm/services/cli/session_resume_helper.py` - Main resume logic

**Hook Integration**:
- `/src/claude_mpm/hooks/session_resume_hook.py` - PM startup hook

**Documentation**:
- `/src/claude_mpm/agents/PM_INSTRUCTIONS.md` - PM behavior updates

### Key Functions

**SessionResumeHelper**:
- `has_paused_sessions()` - Check if sessions exist
- `get_most_recent_session()` - Get latest session
- `get_git_changes_since_pause()` - Calculate git delta
- `format_resume_prompt()` - Format display
- `check_and_display_resume_prompt()` - Main entry point

**SessionResumeStartupHook**:
- `on_pm_startup()` - Execute on PM start
- `get_session_count()` - Count sessions
- `clear_displayed_session()` - Clean up after display

### Error Handling

The system gracefully degrades:
- Non-blocking: PM starts even if check fails
- Logging: Errors logged but not displayed
- Fallback: Missing data shows as "unknown" or "N/A"
- Safe defaults: Empty lists, zero counts, etc.

## Testing

### Manual Testing

1. Create a test session:
   ```bash
   mkdir -p .claude-mpm/sessions
   # Copy an existing session or create manually
   ```

2. Run test script:
   ```python
   from claude_mpm.hooks import trigger_session_resume_check
   trigger_session_resume_check()
   ```

3. Verify output shows session context

### Integration Testing

1. Start PM normally
2. Check for auto-resume prompt
3. Verify git changes are calculated
4. Confirm time elapsed is accurate

## Future Enhancements

Potential improvements:
- [ ] Interactive session selection (if multiple exist)
- [ ] Session archiving after successful resume
- [ ] Resume metrics tracking
- [ ] Session comparison (what changed between sessions)
- [ ] AI-powered session summarization
- [ ] Cloud session sync (for team sharing)

## Related Features

- **Session Pause**: Create paused sessions manually
- **Git Context Check**: PM startup git history review
- **Resume Logs**: Token limit resume functionality
- **Session Management**: General session lifecycle

## Troubleshooting

### Session Not Detected

**Problem**: No resume prompt appears despite paused sessions existing

**Solutions**:
1. Check session directory exists: `ls .claude-mpm/sessions/`
2. Verify JSON files are valid: `python -m json.tool .claude-mpm/sessions/session-*.json`
3. Check file permissions: `ls -la .claude-mpm/sessions/`
4. Review logs: `tail -f .claude-mpm/logs/claude-mpm.log`

### Git Changes Not Showing

**Problem**: Git changes since pause shows 0 commits

**Solutions**:
1. Verify git repository: `git status`
2. Check pause timestamp: Look at `paused_at` in session JSON
3. Ensure commits are after pause time
4. Check git log: `git log --since="<pause_timestamp>"`

### Incorrect Time Elapsed

**Problem**: Time elapsed shows wrong value

**Solutions**:
1. Check system timezone configuration
2. Verify `paused_at` timestamp format (ISO-8601)
3. Ensure timezone information is included
4. Review server time vs local time

## Configuration

Currently auto-resume is always enabled. Future versions may include:

```yaml
# config.yml (future)
session:
  auto_resume:
    enabled: true
    max_sessions_to_check: 5
    display_timeout_days: 30
    auto_clear_after_display: false
```

## Best Practices

### 1. Regular Session Pauses

- Pause before long breaks
- Pause at natural stopping points
- Include detailed summary and next steps

### 2. Session Cleanup

- Clear old sessions periodically
- Archive important sessions
- Keep pause directory under 10 sessions

### 3. Meaningful Summaries

- Write clear, concise summaries
- Include context for future you
- List actual accomplishments
- Define specific next steps

### 4. Git Hygiene

- Commit regularly during sessions
- Use conventional commit messages
- Push changes before pausing
- Clean working directory before pause

## Security Considerations

### File Permissions

Session files contain project context and should be protected:
- Files created with `0600` permissions
- Only user can read/write
- Not accessible to other users
- Excluded from git by default

### Sensitive Information

Avoid including in session data:
- API keys or credentials
- Personal information
- Proprietary code snippets
- Database connection strings

### Project Isolation

Sessions are project-specific:
- Stored in project directory
- No cross-project access
- Isolated file permissions
- Separate session namespaces

## Credits

**Designed and Implemented**: Claude MPM Engineering Team
**Testing**: QA Team
**Documentation**: Documentation Team
**Feature Request**: Community feedback

## Version History

- **v4.19.0**: Initial release of auto-resume functionality
- **v4.18.x**: Session pause/resume foundation
- **v4.17.x**: Resume log generation (token limit)

## Support

For issues or questions:
- GitHub Issues: [claude-mpm/issues](https://github.com/your-org/claude-mpm/issues)
- Documentation: [claude-mpm/docs](https://github.com/your-org/claude-mpm/docs)
- Discord: [claude-mpm community](https://discord.gg/claude-mpm)
