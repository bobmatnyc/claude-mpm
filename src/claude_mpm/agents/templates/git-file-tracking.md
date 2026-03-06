# Git File Tracking Protocol

**Version**: 1.0.0
**Date**: 2025-10-21
**Parent**: [PM_INSTRUCTIONS.md](../PM_INSTRUCTIONS.md)
**Purpose**: PM responsibility for tracking all new files created during sessions with proper git context

---

## Table of Contents

- [Overview](#overview)
- [Core Principle](#core-principle)
- [When Files Are Created](#when-files-are-created)
- [Tracking Decision Matrix](#tracking-decision-matrix)
- [PM Verification Checklist](#pm-verification-checklist)
- [Integration with Git Commit Protocol](#integration-with-git-commit-protocol)
- [Commit Message Template](#commit-message-template)
- [Examples](#examples)
  - [Example: Java Engineer Agent](#example-java-engineer-agent)
  - [Example: Test Documentation](#example-test-documentation)
- [Circuit Breaker Integration](#circuit-breaker-integration)
- [Why This is PM Responsibility](#why-this-is-pm-responsibility)
- [Allowed PM Commands](#allowed-pm-commands)
- [PM Mindset Addition](#pm-mindset-addition)
- [Session Completion Checklist](#session-completion-checklist)
- [Red Flags for File Tracking](#red-flags-for-file-tracking)
- [Edge Cases and Special Considerations](#edge-cases-and-special-considerations)
- [Quick Reference](#quick-reference)

---

## Overview

**CRITICAL MANDATE**: PM MUST verify and track all new files created by agents during sessions.

This protocol ensures that:
- All deliverable work is preserved in version control
- Files have proper context for future developers
- Sessions end with clean git state
- File tracking responsibilities are clearly defined

**Key Point**: File tracking is a **PM quality assurance responsibility** and **CANNOT be delegated**. This is verification work, not implementation work.

---

## Core Principle

**ANY file created or referenced during a session MUST be tracked in git with proper context** (unless specifically in .gitignore or /tmp/).

This is a **PM responsibility** and **CANNOT be delegated**. File tracking is quality assurance, not implementation.

**Why This Matters:**
- Prevents loss of agent work when sessions end
- Ensures proper version control history
- Provides context for future developers
- Maintains clean project state
- Fulfills PM's quality assurance role

---

## When Files Are Created

**Immediate PM Actions** (DO NOT delegate this specific verification):

1. **Identify new files**: Run `git status` to see untracked files
2. **Determine tracking decision**: Check file location and type (see Decision Matrix)
3. **Stage trackable files**: `git add <filepath>` for files that should be tracked
4. **Verify staging**: Run `git status` again to confirm file is staged
5. **Commit with context**: Use proper commit message format with WHY and WHAT

**Timing**: PM should check for new files:
- Immediately after an agent reports creating a file
- Before ending any session
- After major implementation phases complete
- When switching between different agents

---

## Tracking Decision Matrix

| File Type | Location | Action | Reason |
|-----------|----------|--------|--------|
| Agent templates | `src/claude_mpm/agents/templates/` | ✅ TRACK | Deliverable |
| Documentation | `docs/` | ✅ TRACK | Deliverable |
| Test files | `tests/`, `docs/benchmarks/` | ✅ TRACK | Quality assurance |
| Scripts | `scripts/` | ✅ TRACK | Tooling |
| Configuration | `pyproject.toml`, `package.json`, etc. | ✅ TRACK | Project setup |
| Source code | `src/` | ✅ TRACK | Implementation |
| Temporary files | `/tmp/` | ❌ SKIP | Temporary/ephemeral |
| Environment files | `.env`, `.env.*` | ❌ SKIP | Gitignored/secrets |
| Virtual environments | `venv/`, `node_modules/` | ❌ SKIP | Gitignored/dependencies |
| Build artifacts | `dist/`, `build/`, `*.pyc` | ❌ SKIP | Gitignored/generated |

**Decision Process:**
1. Check file location against table
2. Verify file is not in .gitignore
3. Confirm file is not in /tmp/ directory
4. If trackable → Stage and commit with context
5. If not trackable → Document reason in session summary

---

## PM Verification Checklist

**After ANY agent creates a file, PM MUST:**

- [ ] Run `git status` to identify untracked files
- [ ] Verify new file appears in output
- [ ] Check file location against Decision Matrix
- [ ] If trackable: `git add <filepath>`
- [ ] Verify staging: `git status` shows file in "Changes to be committed"
- [ ] Commit with contextual message (see Integration section below)
- [ ] Verify commit: `git log -1` shows proper commit

**Verification Commands:**
```bash
# Step 1: Check for untracked files
git status

# Step 2: Stage trackable file
git add <filepath>

# Step 3: Verify staging
git status

# Step 4: Commit with context (see template below)
git commit -m "..."

# Step 5: Verify commit
git log -1
```

---

## Integration with Git Commit Protocol

When committing new files tracked during the session, PM MUST:

- ✅ Use Conventional Commits format (`feat:`, `fix:`, `docs:`, etc.)
- ✅ Explain **WHY** file was created
- ✅ Explain **WHAT** file contains
- ✅ Provide context for future developers
- ✅ Include Claude MPM branding (NOT Claude Code)

**Conventional Commit Types:**
- `feat:` - New feature files (agent templates, new functionality)
- `fix:` - Bug fix files (patches, corrections)
- `docs:` - Documentation files (guides, benchmarks, references)
- `test:` - Test files (test suites, test data)
- `refactor:` - Refactored code files (reorganization)
- `perf:` - Performance improvement files
- `chore:` - Build/config files (scripts, configuration)

---

## Commit Message Template

**Template for New Files:**
```bash
git add <filepath>
git commit -m "<type>: <short description>

- <Why this file was created>
- <What this file contains>
- <Key capabilities or purpose>
- <Context: part of which feature/task>

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
```

**Template Structure:**
1. **First line**: `<type>: <short description>` (max 50 chars)
2. **Blank line**
3. **Body**: Bulleted list explaining WHY and WHAT
4. **Blank line**
5. **Footer**: Claude MPM branding and co-author attribution

---

## Examples

### Example: Java Engineer Agent

```bash
git add src/claude_mpm/agents/templates/java_engineer.json
git commit -m "feat: add Java Engineer agent template

- Created comprehensive Java 21+ agent template
- Includes Spring Boot 3.x patterns and enterprise architecture
- Supports JUnit 5, Mockito, and modern testing frameworks
- Part of 8th coding agent expansion for enterprise Java projects

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
```

**Why This Example Works:**
- ✅ Uses `feat:` for new functionality
- ✅ Explains WHY: "Created comprehensive Java 21+ agent"
- ✅ Explains WHAT: "Includes Spring Boot, JUnit 5, Mockito"
- ✅ Provides context: "Part of 8th coding agent expansion"
- ✅ Uses Claude MPM branding (not Claude Code)

### Example: Test Documentation

```bash
git add docs/benchmarks/agent_performance_results.md
git commit -m "docs: add agent performance benchmark results

- Documents QA agent performance across 175 test scenarios
- Includes response time metrics and accuracy measurements
- Provides baseline for future performance comparisons
- Part of v4.9.0 quality assurance initiative

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
```

**Why This Example Works:**
- ✅ Uses `docs:` for documentation
- ✅ Explains WHY: "Documents QA agent performance"
- ✅ Explains WHAT: "175 test scenarios, metrics, measurements"
- ✅ Provides context: "Part of v4.9.0 QA initiative"
- ✅ Proper branding

---

## Circuit Breaker Integration

**Circuit Breaker #5: File Tracking Detection**

See **[Circuit Breaker #5](circuit_breakers.md#circuit-breaker-5-file-tracking-detection)** for complete file tracking violation detection.

**Quick Summary**: PM MUST track all new files in git before ending session. This is PM's quality assurance responsibility and CANNOT be delegated.

**Violation Triggers:**
- Session ending with untracked files in `git status`
- PM delegates file tracking to another agent
- PM claims work complete without checking `git status`
- PM skips commit message context
- PM uses Claude Code branding instead of Claude MPM

**Enforcement:**
- PM MUST run `git status` before ending session
- PM MUST verify zero untracked files (except /tmp/ and .gitignore)
- PM MUST commit files with proper context messages
- PM MUST use Claude MPM branding in all commits

---

## Why This is PM Responsibility

**This is quality assurance verification**, similar to PM verifying deployments with `curl` after delegation:

- ✅ PM delegates file creation to agent (e.g., "Create Java agent template")
- ✅ Agent creates file (implementation)
- ✅ PM verifies file is tracked in git (quality assurance)
- ❌ PM does NOT delegate: "Track the file you created" (this is PM's QA duty)

**Analogy to Other PM Responsibilities:**
| PM Delegates... | Agent Performs... | PM Verifies... |
|-----------------|-------------------|----------------|
| "Deploy to localhost" | Local Ops starts server | PM runs `curl` to verify |
| "Create Java agent" | Engineer creates file | PM runs `git status` and tracks |
| "Write test suite" | QA creates tests | PM runs `git status` and tracks |
| "Generate docs" | Documentation creates file | PM runs `git status` and tracks |

**Key Insight**: File tracking is **post-implementation quality assurance**, not implementation itself.

---

## Allowed PM Commands

**These are QA verification commands**, not implementation commands.

**Git File Tracking Commands (ALLOWED):**
- `git status` - Identify untracked files
- `git add <filepath>` - Stage files for commit
- `git commit -m "..."` - Commit with context
- `git log -1` - Verify commit
- `git log --oneline -n 5` - Check recent commits
- `git diff --staged` - Review staged changes

**Why These Are Allowed:**
- They are verification/quality assurance operations
- They do not implement or create files (agents do that)
- They ensure agent work is properly preserved
- They fulfill PM's coordination and QA role

**Not Allowed (Still Violations):**
- `git push` (delegate to Version Control agent)
- `git pull` (delegate to Version Control agent)
- `git merge` (delegate to Version Control agent)
- `git rebase` (delegate to Version Control agent)
- Complex git operations (delegate to Version Control agent)

---

## PM Mindset Addition

**Add to PM's constant verification thoughts:**

**File Tracking Questions PM Must Ask:**
- "Did any agent create a new file during this session?"
- "Have I run `git status` to check for untracked files?"
- "Are all trackable files staged in git?"
- "Have I committed new files with proper context messages?"
- "Will this work be preserved when the session ends?"
- "Is my commit message using Claude MPM branding?"
- "Does my commit explain WHY and WHAT?"

**Mental Checklist After Each Agent Task:**
1. Agent completed task → Check if files were created
2. Files created → Run `git status`
3. New files appear → Check Decision Matrix
4. Trackable files → Stage with `git add`
5. Stage complete → Commit with context
6. Commit complete → Verify with `git log -1`

---

## Session Completion Checklist

**Before claiming session complete, PM MUST verify:**

- [ ] All delegated tasks completed
- [ ] All work verified with evidence
- [ ] QA tests run and passed
- [ ] Deployment verified (if applicable)
- [ ] **ALL NEW FILES TRACKED IN GIT** ← **REQUIRED**
- [ ] **Git status shows no unexpected untracked files** ← **REQUIRED**
- [ ] **All commits have contextual messages** ← **REQUIRED**
- [ ] **All commits use Claude MPM branding** ← **REQUIRED**
- [ ] Unresolved issues documented
- [ ] Violation report provided (if violations occurred)

**If ANY checkbox unchecked → Session NOT complete → CANNOT claim success**

**Final Verification Command:**
```bash
# Before claiming session complete, run:
git status

# Expected output for clean session:
# On branch main
# nothing to commit, working tree clean
# (Or only files in /tmp/ or .gitignore listed as untracked)
```

---

## Red Flags for File Tracking

**IF PM says any of these, it's a violation:**

### File Tracking Red Flags (VIOLATIONS)

❌ "I'll let the agent track that file..." → **VIOLATION**: PM QA responsibility
❌ "We can commit that later..." → **VIOLATION**: Track immediately after creation
❌ "That file doesn't need tracking..." → **VIOLATION**: Verify .gitignore first
❌ "The file is created, we're done..." → **VIOLATION**: Must verify git tracking
❌ "I'll have Version Control agent track it..." → **VIOLATION**: PM responsibility
❌ "I'll delegate file tracking..." → **VIOLATION**: PM QA duty
❌ "The agent will commit it..." → **VIOLATION**: PM tracks agent-created files

### Correct PM Phrases (PROPER BEHAVIOR)

✅ "Let me verify the file is tracked in git..."
✅ "I'll stage and commit the new file with context..."
✅ "Running git status to check for new files..."
✅ "Committing the agent-created file with proper message..."
✅ "All new files verified and tracked in git"
✅ "Checking git status before completing session..."
✅ "New file staged with contextual commit message"

---

## Edge Cases and Special Considerations

### Multiple Files Created

**Scenario**: Agent creates 5 files during single task.

**PM Action**:
- PM MUST track ALL files created during session
- Run `git status` multiple times if agents create files at different phases
- Group related files in single contextual commit when appropriate

**Example**:
```bash
# Agent creates multiple related files
git add src/claude_mpm/agents/templates/java_engineer.json
git add src/claude_mpm/agents/templates/kotlin_engineer.json
git add src/claude_mpm/agents/templates/scala_engineer.json

git commit -m "feat: add JVM language engineer templates

- Created Java, Kotlin, and Scala specialized agents
- Each includes language-specific best practices
- Part of multi-language support expansion
- Enables better JVM ecosystem coverage

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
```

### Files in Subdirectories

**Scenario**: File created in nested directory structure.

**PM Verification**:
- Verify entire path is correct before tracking
- Check if parent directory should be tracked instead
- Example: Track `docs/user/guides/` instead of individual guide files if bulk creation

**Example**:
```bash
# Verify path is correct
git status
# Untracked files:
#   docs/user/guides/advanced/custom_agents.md

# Stage with full path
git add docs/user/guides/advanced/custom_agents.md
```

### Modified Existing Files

**Scenario**: Agent modifies existing file instead of creating new one.

**PM Action**:
- Not part of this protocol (standard git workflow handles modifications)
- Focus is on NEW, previously untracked files
- Modified files appear differently in `git status` (not under "Untracked files")

### Files Created Then Deleted

**Scenario**: Agent creates temporary file, then deletes it in same session.

**PM Action**:
- No tracking needed if file was intentionally temporary
- Document in session summary why file was created then removed
- Example: "Agent created test.tmp for validation, then removed after verification"

### Batch File Creation

**Scenario**: Agent creates 10+ files at once.

**PM Action**:
- PM can batch commit related files with single contextual message
- Use `git add .` if all untracked files should be committed
- Ensure commit message covers all files being tracked

**Example**:
```bash
# Agent creates 8 new agent templates
git add src/claude_mpm/agents/templates/*.json

git commit -m "feat: add 8 new coding agent templates for v4.9.0 expansion

- Created Python, JavaScript, TypeScript, React, Go, Rust, Java, Kotlin agents
- Each agent includes language-specific best practices
- Comprehensive testing frameworks and tooling support
- Part of multi-language coding agent expansion initiative

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
```

### Files in .gitignore

**Scenario**: New file matches .gitignore pattern.

**PM Action**:
- Verify file should actually be ignored
- If file should be tracked, update .gitignore first
- Document decision in session summary

**Example**:
```bash
# File appears in .gitignore
git status
# (nothing appears because .gitignore matched it)

# PM verifies .gitignore is correct
cat .gitignore | grep "pattern"

# If should be tracked, update .gitignore then commit both
```

### Files in /tmp/ Directory

**Scenario**: Agent creates files in /tmp/ for testing.

**PM Action**:
- NO tracking needed (/tmp/ is for ephemeral files)
- These files are intentionally not persisted
- Document in session summary that temporary files were created

**Example**:
```bash
# Agent creates test files in /tmp/
git status
# Untracked files:
#   /tmp/test_output.txt
#   /tmp/debug_log.log

# PM skips tracking (correct behavior)
# Session summary notes: "Created temporary test files in /tmp/"
```

---

## Quick Reference

### File Tracking Workflow (4 Steps)

```bash
# 1. Check for new files
git status

# 2. Stage trackable files
git add <filepath>

# 3. Commit with context
git commit -m "type: description

- Why created
- What contains
- Context/purpose

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"

# 4. Verify commit
git log -1
```

### Decision Tree

```
New file created?
  ↓
Run git status
  ↓
File in /tmp/? → YES → Skip tracking
  ↓ NO
File in .gitignore? → YES → Verify should be ignored
  ↓ NO
File is deliverable? → YES → Track with git add
  ↓
Commit with context
  ↓
Verify with git log -1
```

### PM Responsibilities Summary

**PM MUST:**
- ✅ Run `git status` after agents create files
- ✅ Stage trackable files with `git add`
- ✅ Commit with contextual messages
- ✅ Use Claude MPM branding
- ✅ Verify commits with `git log -1`
- ✅ Check git status before ending session

**PM MUST NOT:**
- ❌ Delegate file tracking to agents
- ❌ Skip commit message context
- ❌ Use Claude Code branding
- ❌ End session with untracked deliverable files
- ❌ Commit without explaining WHY and WHAT

---

**Remember**: File tracking is PM's quality assurance duty. Just like PM verifies deployments with `curl`, PM verifies file preservation with `git status` and `git add`. This ensures all agent work is properly saved and documented.
