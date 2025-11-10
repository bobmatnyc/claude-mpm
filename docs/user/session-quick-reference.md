# Session Management Quick Reference

## Overview

Claude MPM automatically manages your work sessions through intelligent context monitoring and session preservation.

## Automatic Session Creation

### Context Thresholds

The system monitors token usage and takes action at specific thresholds:

| Threshold | Action | Description |
|-----------|--------|-------------|
| **70%** (140k tokens) | **Auto-create + Prompt** | Session file automatically created, user prompted to review |
| **85%** (170k tokens) | **Block Work** | New work blocked until session is managed |
| **95%** (190k tokens) | **Emergency** | Requires immediate action to prevent context loss |

### What Happens at 70%

When you reach 70% context usage:
1. ✅ Session resume file automatically created
2. 📋 You receive a prompt to review the session
3. 💾 All context preserved in `.claude-mpm/sessions/`
4. 🔄 Work can continue or you can start a new session

## Session Files

### Location

```bash
<project-root>/.claude-mpm/sessions/
```

**Legacy location** (still checked for backward compatibility):
```bash
<project-root>/.claude-mpm/sessions/pause/  # Old location
```

### File Format

```
session-YYYYMMDD-HHMMSS.json
```

Example: `session-20251109-143022.json`

## Common Commands

### List Sessions

```bash
# List all sessions
ls -la .claude-mpm/sessions/

# List with sizes and dates
ls -lh .claude-mpm/sessions/
```

### View Session Content

```bash
# View session JSON
cat .claude-mpm/sessions/session-20251109-143022.json

# Pretty print JSON
python -m json.tool .claude-mpm/sessions/session-20251109-143022.json
```

### Clear Sessions

```bash
# Remove all sessions
rm .claude-mpm/sessions/session-*.json

# Remove specific session
rm .claude-mpm/sessions/session-20251109-143022.json

# Keep only recent sessions (last 7 days)
find .claude-mpm/sessions -name "session-*.json" -mtime +7 -delete
```

### Manual Pause

```bash
# Create manual pause point
/mpm-init pause
```

## Session Resume on Startup

When PM starts, it automatically:
1. 🔍 Checks for paused sessions
2. 📊 Identifies most recent session
3. 📈 Calculates git changes since pause
4. 💬 Displays resume context to you

### Example Resume Display

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

## Session Content

Each session file contains:

- **Summary**: What you were working on
- **Accomplishments**: Completed items
- **Next Steps**: Planned actions
- **Git Context**: Repository state, recent commits
- **Todos**: Active and completed tasks
- **Metadata**: Timestamp, project path, version

## Best Practices

### 1. Trust Automatic Creation

- ✅ System creates sessions at 70% threshold
- ✅ No manual intervention needed
- ✅ Context automatically preserved

### 2. Review Resume Prompts

- 📋 Check the resume context when starting PM
- 🤔 Decide if context is still relevant
- 🔄 Resume work or start fresh

### 3. Regular Cleanup

```bash
# Weekly: Remove sessions older than 30 days
find .claude-mpm/sessions -name "session-*.json" -mtime +30 -delete
```

### 4. Pre-Break Pauses

```bash
# Before long breaks, create explicit pause point
/mpm-init pause
```

## Troubleshooting

### Session Not Detected

```bash
# Check sessions exist
ls .claude-mpm/sessions/

# Verify JSON validity
python -m json.tool .claude-mpm/sessions/session-*.json

# Check file permissions
ls -la .claude-mpm/sessions/
```

### Missing Context

```bash
# View session content
cat .claude-mpm/sessions/<session-file>.json

# Check git state
git status
git log --oneline -10
```

### Too Many Sessions

```bash
# Count sessions
ls .claude-mpm/sessions/session-*.json | wc -l

# Remove old sessions (older than 14 days)
find .claude-mpm/sessions -name "session-*.json" -mtime +14 -delete
```

## Context Threshold Workflow

```
Token Usage    Action
───────────────────────────────────────────────────
0%  ──────→   Normal work continues

70% ──────→   🔔 AUTOMATIC SESSION CREATED
              ├─ Session file saved
              ├─ User prompted
              └─ Work can continue

85% ──────→   🚫 NEW WORK BLOCKED
              ├─ Must review session
              └─ Decide: continue or start fresh

95% ──────→   🆘 EMERGENCY
              └─ Immediate action required
```

## Configuration

Session behavior is controlled by PM agent configuration:

```yaml
# Context monitoring (automatic)
context_thresholds:
  warning: 0.70      # 140k tokens - auto-create session
  block: 0.85        # 170k tokens - block new work
  emergency: 0.95    # 190k tokens - emergency state
```

## File Permissions

Session files are created with `0600` permissions (user read/write only) for security.

```bash
# Verify permissions
ls -l .claude-mpm/sessions/

# Should show: -rw-------  (600)
```

## Migration from Legacy Location

If you have old session files in `sessions/pause/`:

```bash
# Sessions are automatically detected in legacy location
# No migration needed - backward compatibility maintained

# Optional: Move to new location
mv .claude-mpm/sessions/pause/*.json .claude-mpm/sessions/
rmdir .claude-mpm/sessions/pause
```

## Related Documentation

- **Session Auto-Resume**: [docs/user/resume-logs.md](resume-logs.md) - Session Auto-Resume on Startup section
- **Design Document**: [docs/design/session-resume-implementation.md](../design/session-resume-implementation.md)
- **User Guide**: [docs/user/user-guide.md](user-guide.md) - Session Management section
- **Troubleshooting**: [docs/user/troubleshooting.md](troubleshooting.md)

## Quick Tips

💡 **Tip 1**: Let the system handle sessions automatically - intervention only needed at 85%

💡 **Tip 2**: Review resume prompts on PM startup to decide continuation strategy

💡 **Tip 3**: Clean up old sessions monthly to keep directory manageable

💡 **Tip 4**: Use `/mpm-init pause` before long breaks for explicit save points

💡 **Tip 5**: Session files are JSON - easy to inspect and debug if needed

## Support

For issues:
- Check troubleshooting guide: [docs/user/troubleshooting.md](troubleshooting.md)
- Review logs: `.claude-mpm/logs/claude-mpm.log`
- GitHub Issues: Report session management issues
