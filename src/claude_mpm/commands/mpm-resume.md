# /mpm-resume - Automatic Session Pause

Create comprehensive session resume files for easy work resumption.

## Usage

```
/mpm-resume
```

## Description

This slash command **automatically generates session resume files** that capture your current work state, making it easy to pause and resume development sessions.

Unlike `/mpm-init pause` which integrates with Claude CLI, this command simply creates two resume files:
1. **Comprehensive Resume**: `.claude-mpm/sessions/session-resume-{timestamp}.md` - Full session context
2. **Quick Summary**: `SESSION_SUMMARY.md` - Quick reference in project root

The PM agent will:
1. Capture current todos from TodoWrite state
2. Gather recent git commits and working directory status
3. Calculate context usage percentage
4. Generate both resume files
5. Provide clear instructions for resuming work

## What Gets Captured

### Comprehensive Resume File
- **Session Summary**
  - Context usage (tokens used / total tokens)
  - Current branch and git status
  - Last commit information
  - Timestamp

- **Current Todos**
  - All pending, in-progress, and completed todos
  - Organized by status

- **Recent Commits**
  - Last 10 commits with SHAs and messages
  - Provides git context for resumption

- **Next Recommended Tasks**
  - Pending todos or user-specified next steps
  - Priority order for resumption

- **Quick Start Commands**
  - Git status verification
  - Log review commands
  - Todo checking commands

### Quick Summary File (Root Directory)
- **Completed Today**: List of finished tasks
- **Next Task**: The immediate next priority
- **Resume Instructions**: How to read the full resume file
- **Key Metrics**: Context usage, directory status

## Files Created

```
.claude-mpm/sessions/session-resume-2025-11-09-143000.md
SESSION_SUMMARY.md
```

## Use Cases

- **Context Limit Approaching**: Pause before hitting token limits
- **End of Work Session**: Save progress before closing
- **Task Switching**: Document current state before switching projects
- **Collaboration Handoff**: Provide clear context for team members
- **Emergency Interruption**: Quick capture of current state

## Example Session Resume Output

```markdown
# Session Resume: 2025-11-09 14:30

## Session Summary

### Current Context
- **Context Used**: 68% (136,000/200,000 tokens)
- **Branch**: main
- **Working Directory**: Clean
- **Last Commit**: 9bd9f8b2 (docs: add comprehensive session resume)

### Current Todos

#### In Progress
- [Engineer] Create /mpm-resume slash command markdown file

#### Pending
- [Engineer] Test command deployment to ~/.claude/commands/
- [Engineer] Update mpm-help.md to include new command
- [Engineer] Update mpm.md to include new command
- [Engineer] Create example test output demonstrating usage

#### Completed
- [Engineer] Research existing slash command infrastructure
- [Engineer] Analyze mpm-init.md for reference patterns

### Recent Commits (Last 10)
9bd9f8b2 docs: add comprehensive session resume for 2025-11-09
951c5896 refactor(mpm-init): modularize 2,093-line file into focused components
0f6cf3b7 fix: redirect MCP print statements to stderr
ff7e579c docs: add comprehensive code review and refactoring session
adf5be50 fix: replace wildcard imports with explicit imports

### Next Recommended Tasks
1. Test command deployment to ~/.claude/commands/
2. Update mpm-help.md to include new command
3. Update mpm.md to include new command

## Quick Start Commands

\```bash
# Verify current state
git status
git log --oneline -5

# Check pending todos
# Todos preserved in next session via TodoWrite
\```

## Git Context
Branch: main
Status: Clean working directory
Remote: origin/main (up to date)

---

**Session Created**: 2025-11-09 14:30:00
**Ready for**: Testing command deployment
```

## Example Quick Summary Output

```markdown
# Quick Session Summary - 2025-11-09 14:30

## ✅ Completed Today
- Research existing slash command infrastructure
- Analyze mpm-init.md for reference patterns
- Create /mpm-resume slash command markdown file

## ⏳ Next Task
Test command deployment to ~/.claude/commands/

## 📖 Resume Instructions
\```bash
cat .claude-mpm/sessions/session-resume-2025-11-09-143000.md
\```

## 📊 Key Metrics
- Context Used: 68% (136,000/200,000 tokens)
- Working Directory: Clean
- Branch: main

---
**Created**: 2025-11-09 14:30:00
```

## Implementation

When you run `/mpm-resume`, the PM agent will:

1. **Gather Current State**
   ```bash
   # Get git context
   git status
   git log --oneline -10
   git branch --show-current

   # Get context usage (from API or estimate)
   # Extract todos from TodoWrite state
   ```

2. **Create Session Directory**
   ```bash
   mkdir -p .claude-mpm/sessions
   ```

3. **Generate Resume Files**
   - Create timestamped comprehensive resume
   - Create/overwrite quick summary in root

4. **Display Confirmation**
   ```
   ✅ Session resume files created:

   📄 Comprehensive: .claude-mpm/sessions/session-resume-2025-11-09-143000.md
   📄 Quick Summary: SESSION_SUMMARY.md

   To resume this session:
   cat .claude-mpm/sessions/session-resume-2025-11-09-143000.md

   Context Usage: 68% (136,000/200,000 tokens)
   ```

## Differences from /mpm-init pause

| Feature | /mpm-resume | /mpm-init pause |
|---------|-------------|-----------------|
| **Purpose** | Create resume files | Pause entire CLI session |
| **Integration** | Standalone | Requires Claude CLI |
| **Files** | 2 markdown files | CLI state + files |
| **Speed** | Instant | Requires CLI coordination |
| **Use Case** | Quick checkpoint | Full session save |

## Benefits

- **Fast**: No CLI integration required
- **Simple**: Just creates markdown files
- **Portable**: Files can be committed to git
- **Readable**: Plain markdown for easy review
- **Shareable**: Can be sent to team members

## Related Commands

- `/mpm-init context`: Analyze git history for intelligent resumption
- `/mpm-init resume`: Resume from stop event logs
- `/mpm-init catchup`: Quick git history display
- `/mpm-status`: Check current MPM status

## Notes

- Session files are timestamped: `session-resume-{YYYY-MM-DD-HHMMSS}.md`
- Quick summary is always `SESSION_SUMMARY.md` (overwrites previous)
- Todos are captured from TodoWrite state (not recreated)
- Git context is gathered but not modified
- Context usage may be estimated if API unavailable
- Files are plain markdown for version control
