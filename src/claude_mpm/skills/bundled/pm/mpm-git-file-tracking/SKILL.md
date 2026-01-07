---
name: pm-git-file-tracking
version: "1.0.0"
description: Protocol for tracking files immediately after agent creation
when_to_use: after agent creates files, before marking todo complete, git operations
category: pm-workflow
tags: [git, file-tracking, workflow, pm-required]
---

# Git File Tracking Protocol

**Critical Principle**: Track files IMMEDIATELY after an agent creates them, not at session end.

## File Tracking Decision Flow

```
Agent completes work and returns to PM
    ↓
Did agent create files? → NO → Mark todo complete, continue
    ↓ YES
MANDATORY FILE TRACKING (BLOCKING)
    ↓
Step 1: Run `git status` to see new files
Step 2: Check decision matrix (deliverable vs temp/ignored)
Step 3: Run `git add <files>` for all deliverables
Step 4: Run `git commit -m "..."` with proper context
Step 5: Verify tracking with `git status`
    ↓
ONLY NOW: Mark todo as completed
```

**BLOCKING REQUIREMENT**: PM cannot mark todo complete until files are tracked.

## Decision Matrix: When to Track Files

| File Type | Track? | Reason |
|-----------|--------|--------|
| New source files (`.py`, `.js`, etc.) | ✅ YES | Production code must be versioned |
| New config files (`.json`, `.yaml`, etc.) | ✅ YES | Configuration changes must be tracked |
| New documentation (`.md` in `/docs/`) | ✅ YES | Documentation is part of deliverables |
| Documentation in project root (`.md`) | ❌ NO | Only core docs allowed (README, CHANGELOG, CONTRIBUTING) |
| New test files (`test_*.py`, `*.test.js`) | ✅ YES | Tests are critical artifacts |
| New scripts (`.sh`, `.py` in `/scripts/`) | ✅ YES | Automation must be versioned |
| Files in `/tmp/` directory | ❌ NO | Temporary by design (gitignored) |
| Files in `.gitignore` | ❌ NO | Intentionally excluded |
| Build artifacts (`dist/`, `build/`) | ❌ NO | Generated, not source |
| Virtual environments (`venv/`, `node_modules/`) | ❌ NO | Dependencies, not source |

## Commit Message Format

```bash
git commit -m "feat: add {description}

- Created {file_type} for {purpose}
- Includes {key_features}
- Part of {initiative}

🤖 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Before Ending Any Session

**Final verification checklist**:

```bash
# 1. Check for untracked files
git status

# 2. If any deliverable files found (should be rare):
git add <files>
git commit -m "feat: final session deliverables..."

# 3. Verify tracking complete
git status  # Should show "nothing to commit, working tree clean"
```

**Ideal State**: `git status` shows NO untracked deliverable files because PM tracked them immediately after each agent.

## Example Workflow

```bash
# After Engineer creates new OAuth files
git status
# Shows: src/auth/oauth2.js (untracked)
#        src/routes/auth.js (untracked)

git add src/auth/oauth2.js src/routes/auth.js

git commit -m "feat: add OAuth2 authentication

- Created OAuth2 authentication module
- Added authentication routes
- Part of user login feature

🤖 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Verify tracking complete
git status  # Should show clean working tree
```

## Integration with Todo Workflow

**BLOCKING SEQUENCE**:
1. Agent completes task and returns to PM
2. PM checks if files were created
3. If YES → Run file tracking protocol (cannot proceed until complete)
4. Only after tracking verified → Mark todo as completed

This ensures no deliverables are lost between agent completion and session end.
