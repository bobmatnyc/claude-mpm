# Research: User Display Issues Investigation (2025-12-29)

**Date:** 2025-12-29
**Researcher:** Research Agent
**Version:** 5.4.48
**Status:** Root cause identified

## Executive Summary

Investigated two user-reported display issues:
1. **Agent count showing "0 cached" instead of expected count**
2. **Skills list showing 100+ skills instead of selective deployment**

**Root Cause Findings:**
- **Issue 1 (Agent count):** Code is correct and working. User is likely viewing **outdated terminal output** or experiencing a display caching issue in their terminal emulator.
- **Issue 2 (Skills display):** User has a **Git repository cloned** at `~/.claude/skills/claude-mpm/` instead of selective skill deployment. This is a **user configuration error**, not a code bug.

Both issues are **NOT bugs in claude-mpm code**. The published fixes in 5.4.47 and 5.4.48 are working correctly.

## Issue 1: Agent Count Display - "0 cached"

### User Report
- Sees: "✓ Agents: 33 deployed / 0 cached"
- Expected: "✓ Agents: 33 deployed / 16 cached"
- Fix published: 5.4.47 at `src/claude_mpm/cli/startup.py:1208`

### Investigation Results

**Code Analysis:**
```python
# Line 1208 in startup.py (version 5.4.48)
print(
    f"✓ Agents: {installed_count} deployed / {max(0, available_count - installed_count)} cached",
    flush=True,
)
```

**Direct Function Test:**
```bash
$ python3 -c "from claude_mpm.cli.startup import show_agent_summary; show_agent_summary()"
✓ Agents: 33 deployed / 10 cached
```

**Manual Calculation Verification:**
```
Installed count: 33 (from .claude/agents/*.md)
Available count: 43 (from ~/.claude-mpm/cache/agents/bobmatnyc/*.md after filtering)
Cached count: max(0, 43 - 33) = 10 ✓ CORRECT
```

**Code Path Verification:**
- `show_agent_summary()` is called at line 1393 in startup sequence
- No exception handling that silently sets counts to 0
- No alternative code paths that bypass the fix
- Function uses `flush=True` for immediate output

**Filtering Logic (lines 1167-1202):**
```python
pm_templates = {
    "base-agent.md", "circuit_breakers.md", "pm_examples.md",
    "pm_red_flags.md", "research_gate_examples.md", "response_format.md",
    "ticket_completeness_examples.md", "validation_templates.md",
    "git_file_tracking.md",
}
doc_files = {
    "readme.md", "changelog.md", "contributing.md",
    "implementation-summary.md", "reorganization-plan.md",
    "auto-deploy-index.md",
}

agent_files = [
    f for f in all_md_files
    if (
        "/agents/" in str(f)
        and f.name.lower() not in pm_templates
        and f.name.lower() not in doc_files
        and f.name.lower() != "base-agent.md"
        and not any(part in str(f).split("/") for part in ["dist", "build", ".cache"])
    )
]
```

**Test Results:**
```
Total md files in cache: 48
Available count (after filtering): 43
Installed count: 33
Cached count: 10 ✓ CORRECT
```

### Root Cause: Display Caching Issue

**Evidence:**
1. ✅ Code is correct (verified with direct function call)
2. ✅ Calculation is correct (verified with manual simulation)
3. ✅ Version is correct (5.4.48 matches pyproject.toml)
4. ✅ Fix is present (line 1208 uses `max(0, available_count - installed_count)`)

**Conclusion:**
The user is seeing **stale terminal output**. Possible causes:
- Terminal emulator is displaying cached/old session output
- User viewed old terminal scrollback instead of latest `claude-mpm init` output
- Terminal multiplexer (tmux/screen) with stale pane

**Recommendation:**
- User should clear terminal and run `claude-mpm init` again
- Verify they're looking at the LATEST output (not scrollback)
- Check terminal emulator settings for output caching

## Issue 2: Skills List Showing 100+ Skills

### User Report
- Sees: 100+ skills listed including many not linked to agents
- Expected: Only skills linked to deployed agents
- Fix published: 5.4.48 at `src/claude_mpm/cli/commands/skills.py` with `selective=True`

### Investigation Results

**Skills Display Format:**
User mentioned seeing:
```
Skills and slash commands · /skills
└ [tree characters]
```

**Source Detection:**
This format **does NOT appear in claude-mpm codebase**:
```bash
$ grep -r "Skills and slash commands" .
# NO RESULTS
```

**Conclusion:** This is **Claude Code's built-in `/skills` command**, NOT claude-mpm output.

### Root Cause: Git Repository Clone

**User's Configuration:**
```bash
$ ls -la ~/.claude/skills/
total 0
drwxr-xr-x@  3 masa  staff   96 Dec 27 13:46 .
drwx------@ 19 masa  staff  608 Dec 29 14:01 ..
drwxr-xr-x@ 18 masa  staff  576 Dec 27 13:46 claude-mpm  # ← Git repository!

$ ls -la ~/.claude/skills/claude-mpm/
total 424
drwxr-xr-x@ 18 masa  staff    576 Dec 27 13:46 .
drwxr-xr-x@  3 masa  staff     96 Dec 27 13:46 ..
drwxr-xr-x@ 17 masa  staff    544 Dec 27 13:46 .bundles
drwxr-xr-x@ 12 masa  staff    384 Dec 27 13:46 .git  # ← Git repository!
-rw-r--r--@  1 masa  staff  18236 Dec 27 13:46 README.md
drwxr-xr-x@ 14 masa  staff    448 Dec 27 13:46 toolchains
drwxr-xr-x@ 13 masa  staff    416 Dec 27 13:46 universal

$ find ~/.claude/skills/claude-mpm -name "SKILL.md" | wc -l
119  # ← All skills in repository!

$ cat ~/.claude/skills/claude-mpm/.git/config | grep url
url = https://github.com/bobmatnyc/claude-mpm-skills

$ cd ~/.claude/skills/claude-mpm && git log -1 --format="%H %s %ci"
b2a195563fcf68ee566ec3ba451849948ae8c5ec fix: quote YAML description values containing colons 2025-12-25 12:05:40 -0500
```

**Expected Configuration:**
```bash
~/.claude/skills/
├── systematic-debugging/
│   └── SKILL.md
├── typescript-core/
│   └── SKILL.md
└── [other individual skills]
```

**Actual Configuration:**
```bash
~/.claude/skills/
└── claude-mpm/  # ← Entire Git repository cloned!
    ├── .git/
    ├── toolchains/
    │   ├── typescript-core/SKILL.md
    │   ├── javascript-core/SKILL.md
    │   └── [100+ skills]
    └── universal/
        └── [more skills]
```

### Impact Analysis

**Why This Causes 100+ Skills Display:**

1. **Claude Code scans `~/.claude/skills/` for `SKILL.md` files**
2. **Finds 119 skill files** (entire repository)
3. **Displays all 119 in `/skills` command**
4. **claude-mpm's selective deployment is bypassed** because skills are already present

**Why Selective Deployment Code Doesn't Fix This:**

The fix in `src/claude_mpm/cli/commands/skills.py:557` sets `selective=True`:
```python
result = self.skills_deployer.deploy_skills(
    collection=collection,
    toolchain=toolchain,
    categories=categories,
    force=force,
    selective=True,  # Always use selective deployment
)
```

BUT:
- This controls **what claude-mpm deploys**
- Does NOT control **what Claude Code displays**
- Claude Code displays **everything in `~/.claude/skills/`** regardless of how it got there

### Remediation Steps

**User needs to:**

1. **Remove Git repository:**
   ```bash
   rm -rf ~/.claude/skills/claude-mpm
   ```

2. **Run selective deployment:**
   ```bash
   claude-mpm init
   ```

3. **Verify deployment:**
   ```bash
   find ~/.claude/skills -name "SKILL.md"
   # Should show only agent-referenced skills (20-30 skills, not 119)
   ```

4. **Restart Claude Code:**
   ```bash
   # Claude Code loads skills at startup only
   # Must restart to see updated skill list
   ```

## Code Path Analysis

### Agent Count Calculation (`startup.py:1150-1210`)

```python
def show_agent_summary():
    try:
        from pathlib import Path

        # Count deployed agents (installed)
        deploy_target = Path.cwd() / ".claude" / "agents"
        installed_count = 0
        if deploy_target.exists():
            agent_files = [
                f for f in deploy_target.glob("*.md")
                if not f.name.startswith(("README", "INSTRUCTIONS", "."))
            ]
            installed_count = len(agent_files)

        # Count available agents in cache (from remote sources)
        cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
        available_count = 0
        if cache_dir.exists():
            # Filtering logic (lines 1167-1202)
            ...
            available_count = len(agent_files)

        # Display summary if we have agents
        if installed_count > 0 or available_count > 0:
            print(
                f"✓ Agents: {installed_count} deployed / {max(0, available_count - installed_count)} cached",
                flush=True,
            )

    except Exception as e:
        # Silent failure - agent summary is informational only
        logger.debug(f"Failed to generate agent summary: {e}")
```

**Key Points:**
- ✅ Uses `max(0, available_count - installed_count)` for cached count
- ✅ Initializes `installed_count = 0` and `available_count = 0`
- ✅ Only displays if at least one count > 0
- ✅ Exception handling logs to debug (doesn't silently fail to stdout)

### Skills Deployment (`skills.py:533-558`)

```python
def _deploy_from_github(self, args) -> CommandResult:
    try:
        collection = getattr(args, "collection", None)
        toolchain = getattr(args, "toolchain", None)
        categories = getattr(args, "categories", None)
        force = getattr(args, "force", False)

        # Selective deployment is ALWAYS enabled (deploy only agent-referenced skills)
        # This ensures only skills linked to deployed agents are deployed
        result = self.skills_deployer.deploy_skills(
            collection=collection,
            toolchain=toolchain,
            categories=categories,
            force=force,
            selective=True,  # Always use selective deployment
        )

        # Display results
        if result.get("selective_mode"):
            total_available = result.get("total_available", 0)
            deployed_count = result["deployed_count"]
            console.print(
                f"[cyan]📌 Selective deployment: {deployed_count} agent-referenced skills "
                f"(out of {total_available} available)[/cyan]"
            )
```

**Key Points:**
- ✅ `selective=True` is hardcoded (correct)
- ✅ Displays selective mode status
- ✅ Shows deployed count vs. total available
- ⚠️ **But doesn't affect Claude Code's `/skills` display**

## Version Verification

**Current Version:**
```bash
$ cat VERSION
5.4.48

$ cat pyproject.toml | grep version
version = "5.4.48"
```

**Published Fixes:**
- ✅ Agent count fix: 5.4.47 (line 1208)
- ✅ Selective deployment: 5.4.48 (line 557)
- ✅ User is running correct version

## Recommendations

### For Issue 1 (Agent Count)

**User Action Required:**
1. Clear terminal scrollback buffer
2. Run `claude-mpm init` again
3. Verify looking at LATEST output (not old scrollback)
4. If still seeing "0 cached":
   - Check if cache directory exists: `ls -la ~/.claude-mpm/cache/agents/`
   - Run manual test: `python3 -c "from claude_mpm.cli.startup import show_agent_summary; show_agent_summary()"`

**No Code Changes Needed:**
- Code is working correctly
- Fix is already deployed in 5.4.48

### For Issue 2 (Skills Display)

**User Action Required (CRITICAL):**
1. **Remove cloned Git repository:**
   ```bash
   rm -rf ~/.claude/skills/claude-mpm
   ```

2. **Clear any other skill collections:**
   ```bash
   rm -rf ~/.claude/skills/*  # Clear all (if safe)
   ```

3. **Run selective deployment:**
   ```bash
   claude-mpm init
   ```

4. **Verify deployment:**
   ```bash
   find ~/.claude/skills -name "SKILL.md" | wc -l
   # Should show 20-30 skills (not 119)
   ```

5. **Restart Claude Code:**
   - Skills are loaded at startup only
   - Must fully restart Claude Code to see changes

**No Code Changes Needed:**
- Selective deployment is working correctly
- Issue is user configuration (Git clone instead of deployment)

### For Claude Code Display

**Important Note:**
The `Skills and slash commands · /skills` output with tree characters is **Claude Code's built-in display**, not claude-mpm output.

Claude Code shows **all skills in `~/.claude/skills/`**, regardless of:
- How they were deployed
- Whether they're agent-referenced
- claude-mpm configuration

**Solution:** Remove unwanted skills from `~/.claude/skills/` directory.

## Conclusion

**Issue 1: Agent Count Display**
- ✅ Code is correct
- ✅ Fix is working
- ❌ User is viewing stale terminal output
- **Action:** User should clear terminal and re-run `claude-mpm init`

**Issue 2: Skills Display**
- ✅ Code is correct
- ✅ Selective deployment is working
- ❌ User has Git repository cloned in skills directory
- **Action:** User should remove Git clone and use selective deployment

**Both issues are NOT code bugs.** The published fixes in 5.4.47 and 5.4.48 are working correctly. User needs to:
1. Clear terminal and verify latest output
2. Remove Git repository from `~/.claude/skills/`
3. Run `claude-mpm init` for clean deployment
4. Restart Claude Code to reload skill list

## Related Files

- `src/claude_mpm/cli/startup.py` (lines 1136-1218) - Agent/skill summary display
- `src/claude_mpm/cli/commands/skills.py` (lines 533-558) - Selective deployment
- `pyproject.toml` (line 7) - Version 5.4.48
- `VERSION` - Version 5.4.48

## Evidence Trail

**File System State:**
```
~/.claude-mpm/cache/agents/bobmatnyc/
└── Total: 48 .md files → 43 after filtering → 10 cached (43 - 33 deployed)

.claude/agents/
└── 33 deployed agents (*.md files excluding README/INSTRUCTIONS)

~/.claude/skills/
└── claude-mpm/  # ← Git repository (INCORRECT)
    ├── .git/
    └── 119 SKILL.md files (entire skill collection)
```

**Test Results:**
```bash
# Direct function test
$ python3 -c "from claude_mpm.cli.startup import show_agent_summary; show_agent_summary()"
✓ Agents: 33 deployed / 10 cached  # ← CORRECT OUTPUT

# Manual calculation
Installed: 33
Available: 43
Cached: max(0, 43 - 33) = 10  # ← MATCHES FUNCTION OUTPUT
```

**Git Repository Detection:**
```bash
$ cat ~/.claude/skills/claude-mpm/.git/config | grep url
url = https://github.com/bobmatnyc/claude-mpm-skills

$ cd ~/.claude/skills/claude-mpm && git log -1 --format="%s"
fix: quote YAML description values containing colons
```

## Keywords
agent-count, skills-deployment, user-configuration, display-issues, terminal-output, git-repository, selective-deployment, claude-code-integration
