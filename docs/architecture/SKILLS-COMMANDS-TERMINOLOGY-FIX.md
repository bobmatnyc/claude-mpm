# Skills vs. Commands: Terminology Fix Summary

**Date:** 2026-01-07
**Status:** Completed
**Issue:** PM was confusing "framework skills" with "user slash commands"

## Problem Statement

When asked about "mpm skills", the PM listed slash commands like `/mpm-init`, `/mpm-status` as if they were "skills" it could invoke. This caused confusion because:

1. **Framework Skills** = Knowledge/instructions loaded into context (e.g., `systematic-debugging`)
2. **User Slash Commands** = User-invokable commands (e.g., `/mpm-init`)

The PM should:
- **USE** framework skills (they're loaded context)
- **DESCRIBE** slash commands (users must invoke them)
- **NEVER** try to "invoke" a slash command

## Root Cause

The `Skill` tool in the system prompt shows `/mpm-*` commands in `<available_skills>`, making them appear as skills the PM can invoke. This is architecturally correct (they ARE user-level skills), but semantically confusing.

## Solution Implemented

### 1. Updated PM Instructions

**File:** `.claude/WORKFLOW.md`
**Section Added:** "Understanding Skills vs. Slash Commands"

**Key clarifications:**
- Framework skills are loaded context, not invokable tools
- Slash commands are user operations, not PM capabilities
- Clear examples of correct vs. incorrect responses
- 5 key rules for handling skill vs. command questions

### 2. Created Architecture Documentation

**File:** `docs/architecture/skills-vs-commands-clarification.md`

**Contents:**
- Detailed terminology definitions
- Correct PM behavior examples
- Required changes roadmap
- Testing scenarios

## Changes Made

### Modified Files

1. **`.claude/WORKFLOW.md`**
   - Added 80-line section explaining distinction
   - Provides correct response templates
   - Lists key rules for PM behavior

2. **`docs/architecture/skills-vs-commands-clarification.md`**
   - Comprehensive architectural documentation
   - Migration guide for updating instructions
   - Testing checklist

3. **`docs/architecture/SKILLS-COMMANDS-TERMINOLOGY-FIX.md`** (this file)
   - Summary of changes
   - Implementation notes

### Not Yet Modified (Future Work)

1. **Skill Tool Description** (in system prompt)
   - Requires framework-level change
   - Would update `<available_skills>` description
   - Clarify that listed skills are USER commands

2. **Additional Documentation**
   - `docs/guides/skills-system.md` - Add "Skills vs. Commands" section
   - `docs/user/skills-guide.md` - Clarify terminology

## Correct PM Behavior (Examples)

### Example 1: User Asks "What skills do you have?"

✅ **Correct Response:**
```
I have access to several framework skills that enhance my capabilities:

**Project Management:**
- mpm-delegation-patterns - How to delegate to specialized agents
- mpm-pr-workflow - Branch protection and PR creation
- mpm-verification-protocols - QA verification requirements

**Development:**
- systematic-debugging - Root cause analysis methodology
- git-workflow - Essential Git patterns
- test-driven-development - TDD workflows

These skills are loaded into my context automatically and guide how I approach tasks.

Additionally, you can invoke these slash commands:
- /mpm-init - Initialize or update project
- /mpm-status - Show system status
- /mpm-doctor - Run diagnostic checks
- /mpm-configure - Interactive configuration

Type any /mpm-* command to use Claude MPM features.
```

❌ **Incorrect Response:**
```
Available skills:
- /mpm-init
- /mpm-status
- /mpm-doctor
[...]
```

### Example 2: User Asks "What does /mpm-init do?"

✅ **Correct Response:**
```
The /mpm-init command initializes or updates your project for Claude Code and MPM.

Main modes:
- Project setup: Creates CLAUDE.md, tool configs, memory system
- Context analysis: Analyzes git history for current work
- Resume: Shows previous session from logs

To use it:
/mpm-init                # Auto-detect mode
/mpm-init update         # Quick update
/mpm-init context        # Analyze git history

Type /mpm-init to run it.
```

❌ **Incorrect Response:**
```
I'll invoke the /mpm-init skill for you.
[attempts to call Skill tool]
```

## Key Rules for PM

1. **Never** try to "invoke" a slash command via the Skill tool
2. **Always** DESCRIBE what slash commands do when asked
3. **Always** tell users to TYPE the command themselves
4. **Framework skills** are YOUR context, not commands you invoke
5. **Slash commands** are USER operations, not your tools

## Testing Checklist

After implementing these changes, verify PM behavior:

- [ ] User: "What skills do you have?"
  - PM lists framework skills first
  - PM mentions slash commands separately
  - PM does NOT list `/mpm-*` as "skills it can invoke"

- [ ] User: "What is /mpm-init?"
  - PM describes the command
  - PM explains how to use it
  - PM does NOT try to invoke it

- [ ] User: "Run /mpm-init for me"
  - PM explains user must type the command
  - PM does NOT call Skill tool
  - PM provides usage instructions

- [ ] User: "Show me mpm-delegation-patterns"
  - PM describes the skill content (if loaded)
  - PM explains it's part of PM's knowledge
  - PM does NOT try to "invoke" it

## Implementation Status

### ✅ Completed

1. Updated PM instructions in `.claude/WORKFLOW.md`
2. Created comprehensive architecture documentation
3. Documented correct PM behavior with examples
4. Created testing checklist

### 🔄 Future Work (Optional)

1. Update Skill tool description in system prompt (framework-level)
2. Update `docs/guides/skills-system.md` with terminology section
3. Update `docs/user/skills-guide.md` for clarity
4. Add automated testing for PM responses

## Impact

**Immediate:**
- PM will correctly distinguish framework skills from slash commands
- Users will understand which commands they need to type
- Reduced confusion about what PM can "invoke"

**Long-term:**
- Clearer mental model for users
- Better documentation consistency
- Foundation for future skill system improvements

## References

**Skills Locations:**
- Framework skills: `.claude/skills/` or `src/claude_mpm/skills/bundled/`
- User commands: `src/claude_mpm/commands/*.md`

**Key Files:**
- PM Instructions: `.claude/WORKFLOW.md`
- Skills Registry: `src/claude_mpm/skills/registry.py`
- Command Routing: `src/claude_mpm/cli/commands/`

**Documentation:**
- Architecture: `docs/architecture/skills-vs-commands-clarification.md`
- User Guide: `docs/user/skills-guide.md` (to be updated)
- System Guide: `docs/guides/skills-system.md` (to be updated)
