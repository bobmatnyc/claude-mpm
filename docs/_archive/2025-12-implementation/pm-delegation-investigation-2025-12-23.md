# PM Delegation Investigation - Why Claude May Not Follow Instructions

**Date**: 2025-12-23
**Context**: User reported Claude directly investigating issues instead of delegating to Research agent
**Ticket**: Investigation requested to understand PM instruction loading

---

## Executive Summary

**CRITICAL FINDING**: PM instructions are NOT automatically loaded in all Claude Code sessions. The system relies on:
1. Cached instruction files in `.claude-mpm/PM_INSTRUCTIONS.md`
2. Manual loading mechanism (not automatic)
3. No visible integration with Claude Code's customInstructions system

**ROOT CAUSE**: PM instructions are project-specific and stored in `.claude-mpm/` but there's no automatic mechanism to inject them into Claude Code's system prompt in other projects.

---

## Investigation Findings

### 1. PM Instruction Storage Architecture

**Source Files** (in `claude-mpm` framework):
- `/src/claude_mpm/agents/PM_INSTRUCTIONS.md` (1,175 lines - comprehensive delegation rules)
- `/src/claude_mpm/agents/WORKFLOW.md` (workflow templates)
- `/src/claude_mpm/agents/MEMORY.md` (memory management)

**Deployment Location** (project-specific):
- `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (merged content)
- `.claude-mpm/PM_INSTRUCTIONS.md` (cached assembled instructions)
- `.claude-mpm/PM_INSTRUCTIONS.md.meta` (metadata file)

**Key Evidence**:
```bash
$ cat .claude-mpm/PM_INSTRUCTIONS.md
System instructions  # Only 19 bytes - placeholder!

$ cat .claude-mpm/PM_INSTRUCTIONS.md.meta
{
  "version": "1.0",
  "content_type": "assembled_instruction",
  "components": [
    "BASE_PM.md",
    "PM_INSTRUCTIONS.md",
    "WORKFLOW.md",
    "agent_capabilities",
    "temporal_context"
  ],
  "content_hash": "f83a6ca776ccb71c9ac9a4ca8f290465266c2fac7ee58f3292defa2e15856717",
  "content_size_bytes": 19,
  "cached_at": "2025-12-23T23:45:44.518285+00:00"
}
```

**Analysis**: The cached file is only 19 bytes ("System instructions") - this is a **placeholder**, not the actual assembled instructions.

---

### 2. Instruction Assembly System

**Service**: `InstructionCacheService` (`src/claude_mpm/services/instructions/instruction_cache_service.py`)

**Purpose**: Cache assembled PM instructions to avoid Linux ARG_MAX limits (~128-256KB)

**Design**:
- Accepts pre-assembled instruction content from caller
- Uses SHA-256 hash-based invalidation
- Atomic writes via temp file strategy
- Stores metadata separately

**Problem Identified**:
The cache service is designed to STORE assembled instructions, but there's no visible mechanism to:
1. Assemble the full instructions automatically
2. Inject them into Claude Code's system prompt
3. Load them in projects outside the `claude-mpm` repository

---

### 3. Claude Code Integration Gap

**Checked Locations**:
- `.claude/settings.local.json` - Only has hooks configuration (KuzuMemory)
- `.claude/*.md` - Only has `MEMORY.md` and `WORKFLOW.md` (not PM instructions)
- No `customInstructions` field in settings
- No visible PM instruction loading mechanism

**Missing Link**:
There's no evidence of how PM instructions get from `.claude-mpm/PM_INSTRUCTIONS.md` into Claude Code's context in:
1. Projects outside the `claude-mpm` repository
2. Fresh sessions in new projects
3. Claude Code startup sequence

---

### 4. PM Instruction Content Analysis

**Key Delegation Rules** (from PM_INSTRUCTIONS.md):

```markdown
## Core Workflow: Do the Work, Then Report
Once a user requests work, the PM's job is to complete it through delegation.

### Delegation-First Thinking
When receiving a user request, the PM's first consideration is:
"Which specialized agent has the expertise and tools to handle this effectively?"

## Tool Usage Guide
### Read Tool Usage (Strict Hierarchy)
**DEFAULT**: Zero reads - delegate to Research instead.
**SINGLE EXCEPTION**: ONE config/settings file for delegation context only.

**Rules**:
- ✅ Allowed: ONE file (package.json, pyproject.toml, settings.json, .env.example)
- ❌ Forbidden: Source code (.py, .js, .ts, .tsx, .go, .rs)
- ❌ Forbidden: Multiple files OR investigation keywords
- **Rationale**: Reading leads to investigating. PM must delegate, not do.

## When to Delegate to Each Agent
| Agent | Delegate When | Key Capabilities |
|-------|---------------|------------------|
| Research | Understanding codebase, investigating approaches | Grep, Glob, Read multiple files, WebSearch |
| Engineer | Writing/modifying code | Edit, Write, codebase knowledge |
| QA | Testing implementations, verifying deployments | Testing frameworks, verification protocols |
```

**Circuit Breakers**: The instructions include 8 circuit breakers to detect and prevent PM violations:
- Circuit Breaker #6: Ticketing tool detection
- Circuit Breaker #7: Verification command detection
- Circuit Breaker #8: QA verification gate

---

## Root Cause Analysis

### Why Delegation May Not Happen

**Hypothesis 1: Instructions Not Loaded** (Most Likely)
- PM instructions are cached in `.claude-mpm/PM_INSTRUCTIONS.md`
- But there's no automatic loading mechanism in Claude Code
- Other projects don't have access to these instructions
- Claude falls back to default "helpful assistant" behavior

**Evidence**:
- No `customInstructions` in `.claude/settings.local.json`
- No visible injection mechanism in Claude Code startup
- Instructions are project-specific (`.claude-mpm/`) not global

**Hypothesis 2: Instructions Truncated/Ignored**
- PM_INSTRUCTIONS.md is 1,175 lines (~68KB merged)
- May exceed token limits for system prompts
- Claude Code might truncate or skip long instructions

**Evidence**:
- Instruction cache uses hash-based validation
- Designed to handle large content (up to 450KB mentioned)
- But actual cache file is only 19 bytes (placeholder)

**Hypothesis 3: Conflicting Instructions**
- Project-specific CLAUDE.md may override PM instructions
- Multiple instruction sources create conflicts
- Claude Code prioritizes certain instruction sources over others

**Evidence**:
- CLAUDE.md exists in project root (KuzuMemory config)
- Multiple instruction files (MEMORY.md, WORKFLOW.md in `.claude/`)
- No clear precedence rules

---

## Deployment Verification

### How Agents Are Deployed

**Agent Discovery Priority**:
1. Project-level: `.claude/agents/` in current project
2. User overrides: `~/.claude-mpm/agents/`
3. Cached remote: `~/.claude-mpm/cache/agents/`

**Deployed Agents** (in `claude-mpm` project):
```bash
$ ls .claude/agents/ | wc -l
47  # 43 deployed agents + metadata files

$ ls .claude/agents/ | grep -i pm
# No PM agent - PM is NOT an agent, it's the base behavior
```

**Key Finding**: PM is not a deployed agent - it's supposed to be the DEFAULT behavior for Claude Code when working with claude-mpm projects.

---

## How PM Instructions SHOULD Work

### Intended Flow

1. **Project Initialization**:
   - `mpm init` creates `.claude-mpm/` directory
   - Deploys PM instructions to `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`
   - Creates cache at `.claude-mpm/PM_INSTRUCTIONS.md`

2. **Session Start**:
   - Claude Code should load PM instructions from cache
   - Instructions become part of system prompt
   - PM behavior is active by default

3. **Agent Delegation**:
   - PM uses Task tool to delegate to specialized agents
   - Research, Engineer, QA, Ops agents handle specific tasks
   - PM coordinates and verifies, never investigates directly

### What's Missing

**No Automatic Loading**: There's no visible mechanism for Claude Code to:
1. Detect `.claude-mpm/PM_INSTRUCTIONS.md` at session start
2. Load and inject instructions into system prompt
3. Apply PM behavior in projects outside `claude-mpm` repo

**Possible Solutions**:
1. **Hook-based injection**: Use SessionStart hook to inject PM instructions
2. **Settings integration**: Add PM instructions to `.claude/settings.local.json`
3. **CLAUDE.md reference**: Reference PM instructions from CLAUDE.md
4. **Automatic agent**: Create a PM agent that's auto-deployed in all projects

---

## Recommendations

### Immediate Actions

1. **Verify Instruction Assembly**:
   - Check if `.claude-mpm/PM_INSTRUCTIONS.md` contains full instructions (not just placeholder)
   - Run instruction cache update manually to verify assembly works
   - Inspect assembled content size and components

2. **Test Instruction Loading**:
   - Create test project with `mpm init`
   - Start Claude Code session
   - Verify PM delegation behavior
   - Check if instructions are in context

3. **Document Loading Mechanism**:
   - Identify exact mechanism for PM instruction loading
   - Document required setup steps for users
   - Create troubleshooting guide for delegation issues

### Architectural Improvements

1. **Explicit Loading Mechanism**:
   ```json
   // .claude/settings.local.json
   {
     "customInstructions": {
       "file": ".claude-mpm/PM_INSTRUCTIONS.md"
     }
   }
   ```

2. **Session Start Hook**:
   ```json
   {
     "hooks": {
       "SessionStart": [
         {
           "type": "command",
           "command": "claude-mpm load-pm-instructions"
         }
       ]
     }
   }
   ```

3. **Verification Command**:
   - Add `/mpm-verify-pm` command to check if PM instructions are loaded
   - Display instruction status and loading errors
   - Provide remediation steps

---

## Next Steps

### Investigation Tasks

- [ ] Trace instruction assembly flow in `InstructionCacheService`
- [ ] Identify where assembled instructions should be injected
- [ ] Check if Claude Code has file-based instruction loading
- [ ] Test PM behavior in clean project (no cached instructions)
- [ ] Compare behavior with/without PM instructions loaded

### Documentation Tasks

- [ ] Document PM instruction loading mechanism
- [ ] Create user guide for enabling PM delegation
- [ ] Add troubleshooting section for delegation issues
- [ ] Update README with PM setup requirements

### Code Tasks

- [ ] Add verification to `mpm init` that PM instructions loaded correctly
- [ ] Create diagnostic command to check PM instruction status
- [ ] Implement automatic instruction loading if missing
- [ ] Add circuit breaker logging to detect PM violations

---

## Files Checked

### Framework Files
- `/src/claude_mpm/agents/PM_INSTRUCTIONS.md` (1,175 lines)
- `/src/claude_mpm/agents/WORKFLOW.md`
- `/src/claude_mpm/agents/MEMORY.md`
- `/src/claude_mpm/services/instructions/instruction_cache_service.py`
- `/src/claude_mpm/services/agents/deployment/system_instructions_deployer.py`

### Project Files
- `.claude-mpm/PM_INSTRUCTIONS.md` (placeholder - 19 bytes)
- `.claude-mpm/PM_INSTRUCTIONS.md.meta` (metadata)
- `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (68KB merged file)
- `.claude/settings.local.json` (no PM instruction references)
- `CLAUDE.md` (only KuzuMemory config)

### Deployment Files
- `.claude/agents/` (43 deployed agents, no PM agent)
- `.claude-mpm/agent_states.json`
- `.claude-mpm/configuration.yaml`

---

## Critical Discovery: Agent Context vs PM Context

**BREAKTHROUGH FINDING**: The current session is running as the **Research agent**, NOT as the PM!

### Evidence

1. **Agent Metadata in Current Session**:
   ```yaml
   ---
   name: research
   description: "Use this agent when you need to investigate codebases..."
   model: sonnet
   type: research
   version: "4.9.0"
   ---
   You are an expert research analyst...
   ```

2. **No PM Agent Deployed**:
   - PM is NOT a deployable agent in `.claude/agents/`
   - PM is supposed to be the **base behavior** when no specific agent is active
   - Current session loaded Research agent instructions instead

3. **Project CLAUDE.md**:
   - Only contains KuzuMemory configuration
   - No PM instructions referenced
   - No delegation instructions present

### Why This Explains the Behavior

**In the other project**, Claude was likely acting as the **base/default agent** (not Research agent), which means:
- No PM instructions were loaded
- No Research agent instructions were loaded
- Claude fell back to **default helpful assistant behavior**
- Default behavior = investigate directly instead of delegating

**In THIS project (claude-mpm)**, Claude is running as the **Research agent**:
- Research agent has clear instructions about investigation
- Research agent knows about ticketing integration
- Research agent behavior is correctly following its instructions
- But Research agent is NOT the PM - it doesn't have PM delegation rules

### The Missing Link

**PM instructions are never loaded into Claude Code's system prompt** in any project because:

1. **No PM Agent**: PM is not a deployable agent (by design - it's supposed to be base behavior)
2. **No CLAUDE.md Integration**: PM instructions not referenced in project CLAUDE.md
3. **No Settings Integration**: PM instructions not in `.claude/settings.local.json`
4. **Cached File Not Used**: `.claude-mpm/PM_INSTRUCTIONS.md` exists but Claude Code doesn't load it

**Current Architecture Assumption**:
- Framework assumes PM behavior is "natural" to Claude when working with projects
- Framework provides PM_INSTRUCTIONS.md for reference, not for injection
- Agents (like Research) are deployed, but PM role is assumed implicit

**Reality**:
- Claude Code doesn't have built-in PM delegation behavior
- Without explicit PM instructions, Claude acts as helpful assistant
- In projects with deployed agents, Claude runs as that agent (e.g., Research)
- PM delegation only works if explicitly instructed via prompt or CLAUDE.md

---

## Conclusion

The PM delegation failure is caused by **architectural mismatch between framework assumptions and Claude Code behavior**.

**Root Cause**: The framework assumes PM behavior is natural/implicit, but Claude Code has no mechanism to load or enforce PM delegation rules. Projects either:
1. Run with a specific agent (e.g., Research) that lacks PM delegation rules
2. Run with no agent (default behavior) that doesn't know about PM delegation

**Priority**: CRITICAL - This is a fundamental gap in the framework architecture.

**Impact**:
- Users NEVER get PM delegation behavior in projects outside `claude-mpm`
- Claude investigates/implements directly instead of coordinating agents
- Multi-agent workflow doesn't work as designed

**Solutions** (ranked by viability):

1. **Add PM Instructions to CLAUDE.md** (Immediate Fix)
   - Reference `.claude-mpm/PM_INSTRUCTIONS.md` from CLAUDE.md
   - Make PM delegation explicit in project instructions
   - Works with current Claude Code capabilities

2. **Create PM Agent** (Medium-term)
   - Deploy PM as actual agent in `.claude/agents/pm.md`
   - User explicitly switches to PM agent for coordination
   - Maintains separation of concerns

3. **Hook-Based Injection** (Complex)
   - Use SessionStart hook to inject PM instructions
   - Modify user prompts to include PM context
   - Requires careful implementation to avoid conflicts

4. **Settings Integration** (Requires Claude Code Support)
   - Add `customInstructions.file` to settings.json
   - Claude Code loads instructions from file
   - Most elegant but requires Claude Code feature

**Recommended Immediate Action**:
Add PM instructions to CLAUDE.md in `mpm init` template, so all initialized projects get PM delegation behavior by default.
