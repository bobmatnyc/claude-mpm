# /mpm-resume Command Demonstration

## Overview

The `/mpm-resume` slash command provides a simple, fast way to create session resume files for pausing and resuming work sessions.

## Command Files Created

### 1. Source Command Definition
**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm-resume.md`
- 6.3 KB markdown file
- Contains complete command documentation
- Includes usage examples and templates

### 2. Deployed Command
**Location**: `~/.claude/commands/mpm-resume.md`
- Deployed to user's Claude commands directory
- Available immediately in Claude CLI
- Auto-discovered by Claude Code

### 3. Updated Command Lists
- **mpm-help.md**: Added `/mpm-resume` to command list
- **mpm.md**: Added to main MPM command menu

## How to Use

### Simple Usage
```bash
# In Claude conversation
/mpm-resume
```

### What Happens
When the PM agent receives `/mpm-resume`, it will:

1. **Gather Current State**
   - Extract todos from TodoWrite state
   - Run `git status`, `git log --oneline -10`, `git branch`
   - Calculate context usage (tokens used / total)

2. **Create Session Directory**
   ```bash
   mkdir -p .claude-mpm/sessions
   ```

3. **Generate Comprehensive Resume File**
   ```
   .claude-mpm/sessions/session-resume-2025-11-09-134000.md
   ```

4. **Generate Quick Summary File**
   ```
   SESSION_SUMMARY.md  # In project root
   ```

5. **Display Confirmation**
   ```
   ✅ Session resume files created:

   📄 Comprehensive: .claude-mpm/sessions/session-resume-2025-11-09-134000.md
   📄 Quick Summary: SESSION_SUMMARY.md

   To resume this session:
   cat .claude-mpm/sessions/session-resume-2025-11-09-134000.md

   Context Usage: 68% (136,000/200,000 tokens)
   ```

## Example Output Files

### Comprehensive Resume File
**File**: `.claude-mpm/sessions/session-resume-2025-11-09-134000.md`

```markdown
# Session Resume: 2025-11-09 13:40

## Session Summary

### Current Context
- **Context Used**: 68% (136,000/200,000 tokens)
- **Branch**: main
- **Working Directory**: Modified (1 file)
- **Last Commit**: 9bd9f8b2 (docs: add comprehensive session resume for 2025-11-09)

### Current Todos

#### In Progress
- [Engineer] Create example test output demonstrating usage

#### Pending
None

#### Completed
- [Engineer] Create /mpm-resume slash command markdown file
- [Engineer] Test command deployment to ~/.claude/commands/
- [Engineer] Update mpm-help.md to include new command
- [Engineer] Update mpm.md to include new command

### Recent Commits (Last 10)
9bd9f8b2 docs: add comprehensive session resume for 2025-11-09
951c5896 refactor(mpm-init): modularize 2,093-line file into focused components
0f6cf3b7 fix: redirect MCP print statements to stderr to prevent protocol pollution
ff7e579c docs: add comprehensive code review and refactoring session documentation
adf5be50 fix: replace wildcard imports with explicit imports and add backward compatibility
85f5b3c1 refactor: consolidate memory system initialization
7a2e4f89 feat: add session state tracking
b4c9d7e2 fix: improve error handling in resume service
c3f8a6d1 docs: update mpm-init documentation
d5e7b9f2 test: add comprehensive tests for command deployment

### Next Recommended Tasks
1. Create example test output demonstrating usage
2. Commit changes to git
3. Test the `/mpm-resume` command in a real session

## Quick Start Commands

\```bash
# Verify current state
git status
git log --oneline -5

# Check pending todos (preserved in next session)
\```

## Git Context
Branch: main
Status: Modified files:
  M src/claude_mpm/commands/mpm-init.md

Remote: origin/main (up to date)

---

**Session Created**: 2025-11-09 13:40:00
**Ready for**: Creating example test output
```

### Quick Summary File
**File**: `SESSION_SUMMARY.md` (project root)

```markdown
# Quick Session Summary - 2025-11-09 13:40

## ✅ Completed Today
- Create /mpm-resume slash command markdown file
- Test command deployment to ~/.claude/commands/
- Update mpm-help.md to include new command
- Update mpm.md to include new command

## ⏳ Next Task
Create example test output demonstrating usage

## 📖 Resume Instructions
\```bash
cat .claude-mpm/sessions/session-resume-2025-11-09-134000.md
\```

## 📊 Key Metrics
- Context Used: 68% (136,000/200,000 tokens)
- Working Directory: 1 modified file
- Branch: main

---
**Created**: 2025-11-09 13:40:00
```

## Resuming a Session

### Option 1: Read Comprehensive Resume
```bash
cat .claude-mpm/sessions/session-resume-2025-11-09-134000.md
```

This shows:
- Full context and todos
- Recent commit history
- Recommended next tasks
- Git status at pause time

### Option 2: Quick Summary
```bash
cat SESSION_SUMMARY.md
```

This shows:
- What was completed
- Next immediate task
- Key metrics

### Option 3: In Claude Conversation
Simply paste the resume file content into a new Claude conversation:

```
I'm resuming from this session:

[paste session-resume file content]

Please continue where we left off.
```

## Benefits

### 1. **Speed**
- Creates files in <1 second
- No CLI integration required
- Instant availability

### 2. **Portability**
- Plain markdown files
- Can be committed to git
- Shareable with team members
- Readable in any text editor

### 3. **Simplicity**
- Single command: `/mpm-resume`
- No arguments or flags
- No configuration needed

### 4. **Completeness**
- Captures todos from TodoWrite
- Includes git context
- Shows context usage
- Lists recent commits

### 5. **Version Control Friendly**
- Timestamped session files (won't conflict)
- Quick summary overwrites (always current)
- Can track session history in git

## Use Cases

### 1. Context Limit Approaching
```
Current usage: 85% (170,000/200,000 tokens)

Run /mpm-resume to save state before limit
```

### 2. End of Work Day
```
Completed several tasks today
Run /mpm-resume to document progress
```

### 3. Task Switching
```
Need to switch to urgent bug fix
Run /mpm-resume to save feature work
```

### 4. Collaboration Handoff
```
Pair programming session ending
Run /mpm-resume to handoff to teammate
```

### 5. Emergency Interruption
```
Unexpected meeting starting
Quick /mpm-resume to capture current state
```

## Integration with Other Commands

### Related Commands

#### /mpm-init context
```bash
/mpm-init context --days 7
```
- Analyzes git history (intelligent)
- Provides work stream analysis
- Recommends next actions
- Takes 10-30 seconds

**vs /mpm-resume**:
- Creates resume files (instant)
- Captures current todos
- Simple checkpoint
- Takes <1 second

#### /mpm-init resume
```bash
/mpm-init resume
```
- Reads stop event logs
- Shows previous session context
- Historical view

**vs /mpm-resume**:
- Creates new resume files
- Current session snapshot
- Forward-looking

#### /mpm-status
```bash
/mpm-status
```
- Shows MPM system status
- Services, agents, config
- System-level view

**vs /mpm-resume**:
- Shows work session status
- Todos, git, context
- Project-level view

## File Structure

After running `/mpm-resume`:

```
project-root/
├── SESSION_SUMMARY.md              # Quick summary (overwrites)
├── .claude-mpm/
│   ├── sessions/
│   │   ├── session-resume-2025-11-09-134000.md
│   │   ├── session-resume-2025-11-09-110000.md
│   │   └── session-resume-2025-11-08-163000.md
│   ├── memories/
│   └── responses/
└── ...
```

### Session Files
- **Naming**: `session-resume-{YYYY-MM-DD-HHMMSS}.md`
- **Location**: `.claude-mpm/sessions/`
- **Lifetime**: Permanent (manual cleanup)
- **Purpose**: Historical session records

### Quick Summary
- **Naming**: `SESSION_SUMMARY.md` (fixed)
- **Location**: Project root
- **Lifetime**: Overwritten each time
- **Purpose**: Always shows latest session

## Testing the Command

### 1. Verify Command is Deployed
```bash
ls -lh ~/.claude/commands/mpm-resume.md
# Should show: 6.3K file
```

### 2. Check Command in Help
```bash
/mpm-help
# Should list /mpm-resume
```

### 3. Run the Command
```bash
/mpm-resume
```

Expected PM response:
```
I'll create session resume files for you.

[PM gathers state...]

✅ Session resume files created:

📄 Comprehensive: .claude-mpm/sessions/session-resume-2025-11-09-134500.md
📄 Quick Summary: SESSION_SUMMARY.md

To resume this session:
cat .claude-mpm/sessions/session-resume-2025-11-09-134500.md

Context Usage: 72% (144,000/200,000 tokens)
```

### 4. Verify Files Created
```bash
# Check session file
cat .claude-mpm/sessions/session-resume-*.md | head -20

# Check summary
cat SESSION_SUMMARY.md
```

### 5. Test Resume
Start new conversation:
```
I'm resuming from this session:

[paste session-resume content]

Please continue where we left off.
```

## Implementation Notes

### PM Agent Responsibilities
When handling `/mpm-resume`, the PM should:

1. **Create sessions directory**
   ```python
   Path(".claude-mpm/sessions").mkdir(parents=True, exist_ok=True)
   ```

2. **Gather current state**
   ```python
   # Git context
   branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True)
   status = subprocess.run(["git", "status", "--short"], capture_output=True)
   log = subprocess.run(["git", "log", "--oneline", "-10"], capture_output=True)

   # Todos (from TodoWrite state)
   todos = get_current_todos()

   # Context (from API or estimate)
   context_usage = get_context_usage()
   ```

3. **Generate timestamp**
   ```python
   from datetime import datetime
   timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
   readable_time = datetime.now().strftime("%Y-%m-%d %H:%M")
   ```

4. **Create comprehensive resume**
   ```python
   resume_path = f".claude-mpm/sessions/session-resume-{timestamp}.md"
   # Fill template with gathered data
   ```

5. **Create quick summary**
   ```python
   summary_path = "SESSION_SUMMARY.md"
   # Fill template with key highlights
   ```

6. **Display confirmation**
   ```python
   print(f"✅ Session resume files created:")
   print(f"\n📄 Comprehensive: {resume_path}")
   print(f"📄 Quick Summary: {summary_path}")
   print(f"\nTo resume this session:")
   print(f"cat {resume_path}")
   print(f"\nContext Usage: {usage_pct}% ({used}/{total} tokens)")
   ```

### Template Variables

**session-resume-{timestamp}.md**:
- `{date}`: Readable date (2025-11-09 13:40)
- `{context_pct}`: Usage percentage (68%)
- `{tokens_used}`: Tokens consumed (136,000)
- `{total_tokens}`: Total available (200,000)
- `{branch_name}`: Current git branch
- `{git_status}`: Working directory status
- `{commit_sha}`: Last commit hash
- `{commit_message}`: Last commit message
- `{todos_in_progress}`: Current in-progress todos
- `{todos_pending}`: Pending todos
- `{todos_completed}`: Completed todos
- `{git_log}`: Recent commits (10)
- `{next_tasks}`: Recommended next steps
- `{timestamp}`: Full timestamp

**SESSION_SUMMARY.md**:
- `{date}`: Readable date
- `{completed_today}`: List of completed todos
- `{next_task}`: Next pending todo
- `{resume_file}`: Path to comprehensive resume
- `{context_pct}`: Usage percentage
- `{tokens_used}/{total_tokens}`: Token usage
- `{git_status}`: Working directory status
- `{branch}`: Current branch
- `{timestamp}`: Creation timestamp

## Success Metrics

### ✅ Command Created
- [x] Source file: `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm-resume.md` (6.3 KB)
- [x] Deployed to: `~/.claude/commands/mpm-resume.md`
- [x] Added to: `mpm-help.md`
- [x] Added to: `mpm.md`

### ✅ Documentation Complete
- [x] Full command documentation in markdown
- [x] Usage examples included
- [x] Template examples provided
- [x] Integration notes documented

### ✅ Files Modified
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm-resume.md` (created)
2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm-help.md` (updated)
3. `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm.md` (updated)

### 📋 Ready for Testing
The command is now available for the PM agent to implement the actual file generation logic.

## Next Steps

### For PM Agent Implementation
1. Detect `/mpm-resume` command
2. Implement state gathering logic
3. Generate session files using templates
4. Display confirmation to user

### For User Testing
1. Run `/mpm-resume` in a Claude conversation
2. Verify files are created
3. Test resuming from generated files
4. Provide feedback on format/content

### For Future Enhancements
1. Auto-pause at context thresholds (e.g., 85%)
2. Session history browsing (`/mpm-resume --list`)
3. Session diff comparison
4. Integration with `/mpm-init context`
5. Git commit integration (auto-commit session files)

---

**Command Status**: ✅ Deployed and Ready
**Documentation**: ✅ Complete
**Testing**: 🔄 Awaiting PM implementation
**Availability**: ✅ Available in Claude CLI immediately
