# Startup Display Bug Investigation

**Date**: 2025-12-29
**Investigator**: Research Agent
**Version**: claude-mpm 5.4.48-build.592
**Status**: Investigation Complete

## Executive Summary

Investigation of two reported issues after upgrade:
1. **Agent count showing "0 cached"** - should show "10 cached" ✅ CODE IS CORRECT
2. **100+ skills being deployed** - should only deploy agent-referenced skills ✅ CODE IS CORRECT

**Key Finding**: The fixes ARE in place and working correctly. The issue is likely:
- User output is from an OLD session before the fixes were deployed
- OR Python bytecode cache corruption
- OR user is running an older installed version

## Issue 1: Agent Count Display

### Reported Issue
```
✓ Agents: 33 deployed / 0 cached
```

Should show: `33 deployed / 10 cached` (or 16 cached based on user's math)

### Investigation Results

**Code Analysis**:
- File: `src/claude_mpm/cli/startup.py` line 1208
- Fix IS in place: `max(0, available_count - installed_count)`
- Bytecode is up-to-date (compiled AFTER source modification)

**Environment Testing**:
```python
Installed: 33 agents
Available in cache: 43 agents
Cached display: max(0, 43 - 33) = 10

Would display: "33 deployed / 10 cached"
```

**File Locations**:
- Deployed agents: `/Users/masa/Projects/claude-mpm/.claude/agents/` (33 files)
- Cached agents: `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/` (43 files, 5 filtered as BASE-AGENT.md)

**Verification**:
```bash
$ python3 -c "from src.claude_mpm.cli.startup import show_agent_summary; import inspect; print(inspect.getsource(show_agent_summary))" | grep "available_count - installed_count"

# Result: Code is correct
f"✓ Agents: {installed_count} deployed / {max(0, available_count - installed_count)} cached",
```

### Root Cause Analysis

**The code is CORRECT**. Possible explanations for user seeing "0 cached":

1. **Stale Session**: User's terminal output is from BEFORE the fix was deployed
2. **Bytecode Cache**: Python cached an older version (though timestamps show current)
3. **Different Installation**: User might have `claude-mpm` installed globally via pip/pipx that's older than the local dev version
4. **Exception Handling**: The `show_agent_summary()` function silently catches exceptions (line 1212-1217), so if cache counting failed, it would show 0

**Exception Handling Code**:
```python
except Exception as e:
    # Silent failure - agent summary is informational only
    from ..core.logger import get_logger
    logger = get_logger("cli")
    logger.debug(f"Failed to generate agent summary: {e}")
```

**Most Likely**: Silent exception during cache counting, OR user output is stale.

## Issue 2: Skills Deployment

### Reported Issue

User sees 100+ skills deployed despite selective deployment being default.

### Investigation Results

**Code Analysis**:
- File: `src/claude_mpm/cli/commands/skills.py` line 557
- Fix IS in place: `selective=True  # Always use selective deployment`
- Default behavior: Only deploy agent-referenced skills

**Environment Testing**:
```python
Installed skills: 0 (no skills with SKILL.md but without .git)
Available in collections: 117 skills

Would display: "0 installed (117 available)"
```

**Skills Directory Structure**:
```
~/.claude/skills/
├── claude-mpm/  (collection with .git, 117 SKILL.md files)
    ├── .git/
    ├── toolchains/
    ├── universal/
    └── ... (skills nested in subdirectories)
```

**Key Finding**: Skills ARE in a collection repo (has `.git`), so they're counted as "available" but NOT "installed".

### Skills Display Logic

**From `show_skill_summary()` in startup.py**:

```python
# Count deployed skills (installed)
skill_dirs = [
    d for d in skills_dir.iterdir()
    if d.is_dir()
    and (d / "SKILL.md").exists()
    and not (d / ".git").exists()  # Exclude collection repos
]
installed_count = len(skill_dirs)  # Result: 0

# Count available skills in collections
for collection_dir in skills_dir.iterdir():
    if not collection_dir.is_dir() or not (collection_dir / ".git").exists():
        continue
    # ... scan for SKILL.md files
available_count += 1  # Result: 117
```

**Expected Display**: `✓ Skills: 0 installed (117 available)`

### Root Cause Analysis

**The code is CORRECT**. User is seeing either:

1. **Old Output**: Terminal output from before selective deployment was made default
2. **Deployment in Progress**: User ran `/skills deploy` explicitly (which shows different output)
3. **Different Code Path**: The skills list the user is seeing might be from a DIFFERENT display function (not startup.py)

**Evidence**: The `/skills deploy` command DOES deploy skills, but it's configured for selective deployment:
```python
selective=True,  # Always use selective deployment
```

## Code Path Analysis

### Agent Count Display Path

**Startup Flow**:
1. `src/claude_mpm/cli/startup.py` → `show_agent_summary()` (line 1136)
2. Counts deployed agents from `.claude/agents/` (line 1151)
3. Counts available agents from `~/.claude-mpm/cache/agents/` (line 1163)
4. Displays: `✓ Agents: {installed} deployed / {max(0, available - installed)} cached` (line 1208)

**No Alternative Display Functions Found**: This is the ONLY place where agent count is displayed.

### Skills Count Display Path

**Startup Flow**:
1. `src/claude_mpm/cli/startup.py` → `show_skill_summary()` (line 1220)
2. Counts installed skills (no .git) from `~/.claude/skills/` (line 1234)
3. Counts available skills (with .git) from collections (line 1250)
4. Displays: `✓ Skills: {installed} installed ({available} available)` (line 1279)

**Alternative Display**: The `/skills deploy` command has ITS OWN display (line 566):
```python
console.print(
    f"[cyan]📌 Selective deployment: {deployed_count} agent-referenced skills "
    f"(out of {total_available} available)[/cyan]"
)
```

## File Timestamps

```
Source file:    Dec 29 13:32  startup.py
Bytecode:       Dec 29 13:40  startup.cpython-311.pyc (8 minutes AFTER source)
```

**Bytecode is UP-TO-DATE** - Python has recompiled the module after the fix.

## Environment Details

**Python Version**: 3.11
**MPM Version**: 5.4.48-build.592
**Running from**: Local dev environment (uv run)
**Not installed via pip**: No global installation found

**Agent Locations**:
- Project agents: `/Users/masa/Projects/claude-mpm/.claude/agents/` (33 files)
- User agents: `~/.claude/agents/` (0 files)
- Cache: `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/` (48 total, 43 after filters)

**Skill Locations**:
- Skills dir: `~/.claude/skills/`
- Collection: `~/.claude/skills/claude-mpm/` (has .git, 117 skills)
- Installed: 0 (no standalone skills without .git)

## Conclusions

### Issue 1: Agent Count "0 cached"

**Status**: ✅ Code is correct, fix is in place

**Evidence**:
- Code shows correct formula: `max(0, 43 - 33) = 10`
- Bytecode is current (compiled after source modification)
- Environment testing confirms: "33 deployed / 10 cached"

**Likely Explanation**:
1. User's terminal output is STALE (from before fix)
2. Silent exception during cache counting (debug logs would show this)
3. User running different installation (global pip vs local dev)

**Recommended Actions**:
1. Ask user to restart Claude Code completely (reload window)
2. Ask user to clear Python bytecode cache: `find . -name "*.pyc" -delete`
3. Check debug logs for exceptions: Look for "Failed to generate agent summary"
4. Verify user is running local dev version: `python -m claude_mpm --version` should show build number

### Issue 2: Skills "100+ deployed"

**Status**: ✅ Code is correct, selective deployment is default

**Evidence**:
- Code shows: `selective=True  # Always use selective deployment`
- Environment testing confirms: "0 installed (117 available)"
- Skills are in collection repo (not deployed as standalone)

**Likely Explanation**:
1. User's output is STALE (from before selective deployment)
2. User is looking at DIFFERENT output (not startup.py display)
3. User ran `/skills deploy` which shows "117 available" (NOT "117 deployed")

**Recommended Actions**:
1. Ask user to show CURRENT output (restart Claude Code)
2. Clarify which display they're seeing:
   - Startup display: `✓ Skills: X installed (Y available)`
   - Deploy command: `📌 Selective deployment: X agent-referenced skills (out of Y available)`
3. Verify understanding: "available" ≠ "deployed"

## Testing Commands

To reproduce the correct behavior:

```bash
# Test agent counting
python3 -c "
from pathlib import Path
deploy_target = Path.cwd() / '.claude' / 'agents'
cache_dir = Path.home() / '.claude-mpm' / 'cache' / 'agents'

installed = len([f for f in deploy_target.glob('*.md') if not f.name.startswith(('README', 'INSTRUCTIONS', '.'))])
available = len([f for f in cache_dir.rglob('*.md') if '/agents/' in str(f) and f.name.lower() not in {'base-agent.md', 'readme.md'}])

print(f'{installed} deployed / {max(0, available - installed)} cached')
"

# Test skill counting
python3 -c "
from pathlib import Path
import os

skills_dir = Path.home() / '.claude' / 'skills'
installed = len([d for d in skills_dir.iterdir() if d.is_dir() and (d / 'SKILL.md').exists() and not (d / '.git').exists()])

available = 0
for coll in skills_dir.iterdir():
    if coll.is_dir() and (coll / '.git').exists():
        for root, dirs, files in os.walk(coll):
            if 'SKILL.md' in files:
                available += 1

print(f'{installed} installed ({available} available)')
"
```

## Next Steps

1. **User Verification**: Ask user to provide FRESH output after Claude Code restart
2. **Log Analysis**: Check `~/.claude-mpm/logs/` for exceptions during summary generation
3. **Version Check**: Confirm user is running latest build with `python -m claude_mpm --version`
4. **Bytecode Clear**: Have user clear Python cache if issue persists

## Related Files

- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py` (lines 1136-1289)
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/skills.py` (line 557)
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills_deployer.py`

## Appendix: Filter Logic

**PM Template Files (excluded from agent count)**:
- base-agent.md
- circuit_breakers.md
- pm_examples.md
- pm_red_flags.md
- research_gate_examples.md
- response_format.md
- ticket_completeness_examples.md
- validation_templates.md
- git_file_tracking.md

**Doc Files (excluded from agent count)**:
- readme.md
- changelog.md
- contributing.md
- implementation-summary.md
- reorganization-plan.md
- auto-deploy-index.md

**Path Exclusions**:
- dist/
- build/
- .cache/
- Files starting with . (hidden)
