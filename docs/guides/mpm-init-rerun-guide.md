# Re-Running /mpm-init: Keep Your Documentation Fresh

**Complete guide to updating your project instructions as your codebase evolves**

## Table of Contents

- [Why Re-Run /mpm-init?](#why-re-run-mpm-init)
- [Quick Start](#quick-start)
- [How Re-Running Works](#how-re-running-works)
- [When to Re-Run](#when-to-re-run)
- [Available Update Modes](#available-update-modes)
- [Common Re-Run Scenarios](#common-re-run-scenarios)
- [Safety Features](#safety-features)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Why Re-Run /mpm-init?

Your project documentation should evolve with your codebase. The `/mpm-init` command is designed to be **re-run safely** throughout your project's lifecycle to keep your AI instructions accurate and up-to-date.

**The Problem Without Regular Updates**:
- AI agents follow outdated build commands
- New frameworks aren't documented
- Old workflows cause confusion
- Security updates get missed
- Team onboarding becomes harder

**The Solution**:
Re-run `/mpm-init` regularly to automatically extract knowledge from:
- ✅ Git commit history (architectural decisions)
- ✅ Session logs (learned patterns)
- ✅ Memory files (accumulated wisdom)
- ✅ Project changes (new dependencies, frameworks)

## Quick Start

### Your First Re-Run

```bash
# Navigate to your project
cd my-project

# Re-run initialization
/mpm-init
```

**You'll see**:
```bash
⚠️  Project already has CLAUDE.md file.

Current Documentation Analysis:
  Size: 15.2 KB
  Sections: 12
  Custom Content: 3 sections

How would you like to proceed?
  [1] Update existing CLAUDE.md (preserves custom content)  ← Recommended
  [2] Recreate CLAUDE.md from scratch
  [3] Review project state without changes
  [4] Cancel operation
```

**Choose Option 1** for intelligent updates that preserve your customizations.

### Quick Update (Weekly)

```bash
# Lightweight update with last 30 days of changes
/mpm-init update
```

**Takes seconds**, perfect for frequent updates.

### Context Analysis (Daily)

```bash
# Get intelligent analysis of recent work
/mpm-init context --days 7
```

**Use this** when resuming work or need project context.

## How Re-Running Works

### Intelligent Update Process

When you re-run `/mpm-init` on an existing project, it:

**1. Detects Your Project State**
```bash
✓ Found existing CLAUDE.md (15.2 KB)
✓ Detected .claude-mpm/ directory
✓ Activating enhanced update mode
```

**2. Extracts Project Knowledge**
```bash
✓ Analyzing git history (last 90 days)...
  - Found 15 architectural decisions
  - Detected 8 workflow patterns
  - Identified 3 tech stack changes

✓ Analyzing session logs...
  - Found 42 learning entries
  - Extracted common patterns

✓ Analyzing memory files...
  - Found 67 accumulated insights
```

**3. Preserves Your Custom Content**
- Identifies sections you added manually
- Archives existing CLAUDE.md for safety
- Merges updates intelligently

**4. Enhances Documentation**
- Adds new architectural decisions from commits
- Updates build/test/deploy workflows
- Incorporates learned patterns
- Maintains priority organization (🔴🟡🟢⚪)

**5. Validates and Deploys**
```bash
✓ Update complete
✓ Deployed 5 PM skills
✓ CLAUDE.md optimization complete (18% token reduction)
```

### What Gets Extracted?

**From Git History**:
- Architectural decisions (refactoring, migrations)
- Tech stack changes (new dependencies, removals)
- Workflow patterns (CI/CD configs)
- Hot files (frequently modified code)
- Security concerns (CVEs, auth changes)

**From Session Logs**:
- Learned patterns from AI interactions
- Common operations and solutions
- File change patterns

**From Memory Files**:
- Architectural knowledge
- Implementation guidelines
- Common mistakes and solutions
- Technical context

## When to Re-Run

### Critical Triggers (Run Immediately)

**1. New Frameworks or Dependencies**
```bash
# Example: Added React
npm install react react-dom
/mpm-init --update
```

**Why**: AI needs to know about new tooling and patterns.

**2. Architectural Changes**
```bash
# Example: Refactored to microservices
git commit -m "refactor: migrate to microservices architecture"
/mpm-init --update
```

**Why**: Major structural changes need documentation updates.

**3. Build/Test/Deploy Workflow Changes**
```bash
# Example: Migrated from Webpack to Vite
npm remove webpack && npm install vite
/mpm-init --update
```

**Why**: AI agents need current build commands.

**4. Security or Compliance Updates**
```bash
# Example: Added GDPR compliance
git commit -m "feat: add GDPR data handling"
/mpm-init --update
```

**Why**: Critical policies must be documented.

**5. Project Type Evolution**
```bash
# Example: CLI tool → Web API
# Project scope expanded significantly
/mpm-init --update
```

**Why**: Fundamental project changes need full documentation refresh.

### Recommended Schedule

**Weekly** (Lightweight):
```bash
/mpm-init update
```
Quick 30-day history update, takes seconds.

**Monthly** (Full Update):
```bash
/mpm-init --update
```
Comprehensive 90-day analysis with knowledge extraction.

**Quarterly** (Maintenance):
```bash
/mpm-init --review       # Check current state
/mpm-init --update       # Full refresh
```
Ensure documentation quality and completeness.

**Daily** (Context):
```bash
/mpm-init context --days 7    # Smart analysis
# OR
/mpm-init catchup             # Quick commit list
```
Get project context when starting work.

## Available Update Modes

### 1. Standard Update (Default)

**Command**: `/mpm-init` → Choose "Update"
**Or**: `/mpm-init --update`

**Best for**:
- Regular maintenance updates
- After significant changes
- Monthly refresh

**What it does**:
- Analyzes last 90 days of git history
- Extracts knowledge from logs and memory
- Preserves custom sections
- Archives existing CLAUDE.md
- Smart merges new content

**Example**:
```bash
/mpm-init --update

# Output:
# ✓ Analyzing git history (90 days)...
#   - Found: Framework migration (Webpack → Vite)
#   - Added: New build commands
#   - Updated: Development workflows
# ✓ Custom sections preserved (3 found)
# ✓ Update complete
```

### 2. Quick Update

**Command**: `/mpm-init update`

**Best for**:
- Weekly updates
- Quick refreshes
- Minimal time investment

**What it does**:
- Analyzes last 30 days (faster)
- Basic workflow updates
- Preserves custom content
- No extensive knowledge extraction

**Example**:
```bash
/mpm-init update

# Fast execution (5-10 seconds)
# Updates recent changes only
```

### 3. Context Analysis

**Command**: `/mpm-init context --days 7`

**Best for**:
- Starting work sessions
- Understanding recent changes
- Strategic planning

**What it does**:
- Intelligent git analysis
- Active work streams identification
- Risk and blocker detection
- Recommended next actions

**Example**:
```bash
/mpm-init context --days 7

# Delegates to Research agent
# Output includes:
#   - Active work streams
#   - Recent architectural changes
#   - Identified risks
#   - Recommended actions
```

### 4. Quick Catchup

**Command**: `/mpm-init catchup`

**Best for**:
- Instant project overview
- PM context without analysis
- Quick commit history

**What it does**:
- Shows last 25 commits
- All branches included
- Instant display (no analysis)

**Example**:
```bash
/mpm-init catchup

# Displays commit history immediately
# No processing, instant results
```

### 5. Review Mode

**Command**: `/mpm-init --review`

**Best for**:
- Checking current state
- Pre-update analysis
- Health check

**What it does**:
- Analyzes documentation quality
- Validates project structure
- Shows git history summary
- Provides recommendations
- **Makes no changes**

**Example**:
```bash
/mpm-init --review

# Analysis:
#   ✓ CLAUDE.md: 15.2 KB, 12 sections
#   ✓ Git activity: 145 commits (30 days)
#   ✓ Custom sections: 3 found
#   ⚠️ Recommendation: Update suggested (45 days old)
```

### 6. Recreate Mode

**Command**: `/mpm-init --force`
**Or**: `/mpm-init` → Choose "Recreate"

**Best for**:
- Starting completely fresh
- Corrupted documentation
- Major project overhauls

**What it does**:
- Archives existing CLAUDE.md
- Creates new documentation from scratch
- Bypasses update logic
- No knowledge extraction

**Warning**: Loses customizations unless manually restored from archive.

**Example**:
```bash
/mpm-init --force

# Archives existing CLAUDE.md
# Creates fresh documentation
# Use only when necessary
```

### 7. Dry-Run Mode

**Command**: `/mpm-init --dry-run`

**Best for**:
- Previewing changes
- Understanding impact
- Safe exploration

**What it does**:
- Shows planned changes
- Preview of updates
- Structure validation
- **Makes no changes**

**Example**:
```bash
/mpm-init --dry-run

# Shows what would be created/updated
# Files that would change
# No actual modifications
```

## Common Re-Run Scenarios

### Scenario 1: Framework Migration

**Situation**: Migrated from Webpack to Vite

```bash
# After migration commits
/mpm-init --update

# Output:
# ✓ Detected tech stack change:
#   - Added: vite@5.0.0
#   - Removed: webpack@5.88.0
# ✓ Updated build command: "vite build"
# ✓ Updated dev server: "vite dev"
# ✓ Architectural decision documented
```

**What changed in CLAUDE.md**:
- Build commands updated
- Development server instructions
- New framework patterns added
- Migration rationale documented

### Scenario 2: New Authentication System

**Situation**: Added OAuth2 authentication

```bash
# After auth implementation
/mpm-init --update

# Output:
# ✓ Found security-related commits (8)
# ✓ Added CRITICAL priority section:
#   "🔴 CRITICAL: OAuth2 Authentication"
# ✓ Updated security guidelines
# ✓ Documented auth workflows
```

**What changed in CLAUDE.md**:
- New authentication patterns
- Security best practices
- OAuth2 configuration
- Critical priority marking

### Scenario 3: Quarterly Maintenance

**Situation**: 3 months since last update

```bash
# Before starting new quarter
/mpm-init --review

# Recommendation: Update suggested (91 days old)

/mpm-init --update

# Output:
# ✓ Analyzing 90 days of history...
#   - 245 commits analyzed
#   - 15 architectural decisions found
#   - 8 workflow changes detected
# ✓ Knowledge extraction complete
# ✓ Documentation updated with insights
```

**What changed in CLAUDE.md**:
- Accumulated decisions documented
- Workflow refinements
- Hot files identified
- Priority reorganization

### Scenario 4: Daily Context

**Situation**: Resuming work after weekend

```bash
# Start of work session
/mpm-init context --days 7

# Output:
# Active Work Streams:
#   1. User authentication (5 commits)
#   2. API refactoring (3 commits)
#
# Recent Architectural Changes:
#   - Database migration to PostgreSQL
#   - REST → GraphQL transition
#
# Recommended Next Actions:
#   1. Complete auth integration tests
#   2. Update API documentation
```

### Scenario 5: Quick Weekly Update

**Situation**: Weekly team sync

```bash
# Every Monday
/mpm-init update

# Fast execution (10 seconds)
# Recent changes incorporated
# Ready for new sprint
```

### Scenario 6: New Team Member Onboarding

**Situation**: Developer joining team

```bash
# Before onboarding session
/mpm-init --update

# Ensures documentation is current
# New team member gets accurate instructions
# Reduces onboarding friction
```

## Safety Features

### 1. Automatic Archiving

**Every update automatically archives existing CLAUDE.md**:

```bash
# Before update
CLAUDE.md

# After update
CLAUDE.md                                    # Updated version
docs/_archive/CLAUDE-2026-01-07-14-30-15.md # Archived original
```

**Archive location**: `docs/_archive/CLAUDE-[timestamp].md`

**Benefits**:
- Safe rollback if needed
- Change history tracking
- Zero risk of data loss

### 2. Custom Content Preservation

**Update mode automatically preserves**:
- ✅ Custom sections you added
- ✅ User-added instructions
- ✅ Project-specific notes
- ✅ Manual annotations

**Example**:
```markdown
## My Custom Section

This section was added manually and will be preserved.
```

**Controlled by**: `--preserve-custom` flag (default: **True**)

**To disable** (not recommended):
```bash
/mpm-init --update --no-preserve-custom
```

### 3. Interactive Confirmation

**When existing CLAUDE.md detected**:

```bash
⚠️  Project already has CLAUDE.md file.

Current Documentation Analysis:
  Size: 15.2 KB
  Sections: 12
  Custom Content: 3 sections
  Last Modified: 45 days ago

How would you like to proceed?
  [1] Update existing CLAUDE.md (preserves custom content)  ← Safe default
  [2] Recreate CLAUDE.md from scratch
  [3] Review project state without changes
  [4] Cancel operation

Choice: _
```

**You explicitly choose** what happens - no surprises.

### 4. Dry-Run Preview

**See changes before applying**:

```bash
/mpm-init --dry-run

# Shows:
# Would update: CLAUDE.md
# Would create: DEVELOPER.md
# Would archive: CLAUDE.md → docs/_archive/
# Would preserve: 3 custom sections
#
# No changes made - preview only
```

### 5. Review Without Changes

**Analyze project state safely**:

```bash
/mpm-init --review

# Complete analysis
# Recommendations provided
# Zero modifications
# Safe exploration
```

## Best Practices

### 1. Regular Update Schedule

**Establish a routine**:

```bash
# Weekly (lightweight)
Monday morning: /mpm-init update

# Monthly (comprehensive)
First of month: /mpm-init --update

# Quarterly (maintenance)
End of quarter: /mpm-init --review && /mpm-init --update
```

### 2. Update After Major Changes

**Immediate re-run triggers**:
- ✅ New framework or library added
- ✅ Architecture refactored
- ✅ CI/CD workflow changed
- ✅ Security updates applied
- ✅ Migration completed

```bash
# Right after significant changes
git commit -m "feat: migrate to TypeScript"
/mpm-init --update
```

### 3. Use Context for Daily Work

**Start each work session**:

```bash
# Get oriented
/mpm-init context --days 7

# Or quick overview
/mpm-init catchup

# Then start coding
```

### 4. Review Before Updating

**Check before major updates**:

```bash
# See current state
/mpm-init --review

# Understand recommendations
# Then update
/mpm-init --update
```

### 5. Trust the Safety Features

**Don't fear re-running**:
- Archives protect your work
- Custom content is preserved
- Review mode lets you preview
- Dry-run shows changes
- Interactive prompts give control

**Just run it regularly**!

### 6. Organize Custom Content

**For best preservation**:

```markdown
## Project-Specific Guidelines

Custom instructions here.

## Custom Workflow

Your workflow here.
```

**Tips**:
- Use clear section headers
- Don't modify standard priority markers (🔴🟡🟢⚪)
- Place custom content in dedicated sections
- Keep sections organized

### 7. Use Quick Update for Speed

**When time is limited**:

```bash
# 10-second update
/mpm-init update

# Instead of comprehensive
# /mpm-init --update  (slower, more thorough)
```

### 8. Combine with Doctor Command

**Validate after updates**:

```bash
# Update documentation
/mpm-init --update

# Verify system health
claude-mpm doctor
```

## Troubleshooting

### Issue: Update Seems to Overwrite Custom Content

**Expected Behavior**: Custom content should be preserved by default.

**Check**:
```bash
# Verify preservation flag
/mpm-init --update --preserve-custom  # Should be default

# Check archive for content
ls docs/_archive/CLAUDE-*.md
```

**Solution**:
1. Check archived version: `docs/_archive/CLAUDE-[timestamp].md`
2. Manually restore lost sections if needed
3. File bug report if preservation failed
4. Use clear section headers for better detection

### Issue: Enhanced Update Mode Not Triggered

**Symptoms**: No "Detected initialized project" message, no knowledge extraction.

**Cause**: `.claude-mpm/` directory doesn't exist.

**Check**:
```bash
# Verify directory exists
ls -la .claude-mpm/

# Check project state
/mpm-init --review
```

**Solution**:
```bash
# Initialize properly on first run
/mpm-init  # Choose create/update

# Or run once to create directory
claude-mpm run --non-interactive -i "Initialize project"
```

### Issue: Update Takes Too Long

**Symptoms**: 90-day git analysis is slow on large repos.

**Cause**: Comprehensive analysis of large git history.

**Solutions**:

**Option 1: Quick Update** (recommended for frequent runs)
```bash
/mpm-init update
# 30 days, much faster
```

**Option 2: Reduce Analysis Window**
```bash
/mpm-init context --days 30
# Fewer days = faster
```

**Option 3: Use Catchup**
```bash
/mpm-init catchup
# Instant, no analysis
```

**Option 4: Skip Non-Essential**
```bash
# Just check state
/mpm-init --review

# Then quick update
/mpm-init update
```

### Issue: Want to Start Fresh

**Symptoms**: Documentation is corrupted or extremely outdated.

**Solution**:

**Option 1: Interactive**
```bash
/mpm-init
# Choose [2] Recreate from scratch
```

**Option 2: Force Flag**
```bash
/mpm-init --force
# Recreates immediately
```

**Note**: Existing CLAUDE.md will be archived, so you can recover content if needed.

### Issue: Lost Track of Changes

**Symptoms**: Don't know what changed in update.

**Solution**:

**Check Archive**:
```bash
# Compare current with archived
diff CLAUDE.md docs/_archive/CLAUDE-[latest].md
```

**Use Dry-Run Next Time**:
```bash
/mpm-init --dry-run
# Preview changes first
```

### Issue: Git Repository Required Error

**Symptoms**: "Git repository not found" error during update.

**Cause**: Knowledge extraction requires git history.

**Solution**:
```bash
# Initialize git if needed
git init

# Or skip git-based features
# (basic update will still work)
```

### Issue: Want Different Update Frequency

**Symptoms**: Default 90 days too much/little.

**Solution**:

**More frequent, less data**:
```bash
/mpm-init update           # 30 days
/mpm-init context --days 7 # 7 days
```

**Less frequent, more data**:
```bash
/mpm-init --update         # 90 days (default)
```

**Customize**:
```bash
/mpm-init context --days 60  # Custom range
```

## Summary

### Key Takeaways

✅ **Re-running /mpm-init is SAFE**
Automatic archiving and custom content preservation protect your work.

✅ **Re-running is CRITICAL**
Essential as projects evolve - keeps AI instructions accurate.

✅ **Intelligent by Default**
Enhanced update mode extracts project knowledge automatically.

✅ **Multiple Modes Available**
Choose update speed and depth based on needs.

✅ **Evidence-Based Updates**
Uses actual git history and session logs, not assumptions.

✅ **Non-Destructive Preview**
Review and dry-run modes show changes without applying.

### Quick Command Reference

```bash
# First run or interactive update
/mpm-init

# Full update (90 days)
/mpm-init --update

# Quick update (30 days)
/mpm-init update

# Daily context
/mpm-init context --days 7

# Quick overview
/mpm-init catchup

# Review without changes
/mpm-init --review

# Preview changes
/mpm-init --dry-run

# Start fresh
/mpm-init --force
```

### When to Use Each

| Command | Frequency | Use Case |
|---------|-----------|----------|
| `/mpm-init update` | Weekly | Routine updates |
| `/mpm-init --update` | Monthly | Comprehensive refresh |
| `/mpm-init context --days 7` | Daily | Work session start |
| `/mpm-init catchup` | Daily | Quick overview |
| `/mpm-init --review` | As needed | Check health |
| `/mpm-init --force` | Rarely | Fresh start |

### Remember

🔄 **Update regularly** - Weekly or after major changes
🛡️ **Trust the safety** - Archives protect you
📊 **Use context daily** - Stay oriented
⚡ **Quick update for speed** - Use `/mpm-init update` for frequent runs
🔍 **Review before big changes** - Check state first

---

**Related Documentation**:
- [Doctor Command Guide](./doctor-command.md) - System health checks
- [CLI Reference](../reference/slash-commands.md) - All commands
- [Getting Started](../getting-started/) - Initial setup

**Need Help?**
Run `/mpm-help mpm-init` for command-specific help or check [Troubleshooting Guide](../user/troubleshooting.md).
