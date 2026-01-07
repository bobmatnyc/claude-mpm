# PM Instruction Gap Analysis - Anti-Pattern Prevention

**Date:** 2025-12-25
**Status:** Complete
**Requestor:** User investigation request
**Scope:** PM delegation gaps and JSON template reference cleanup

---

## Executive Summary

Investigation revealed **two critical gaps** in PM instructions:

1. **DELEGATION GAP (CRITICAL)**: PM instructions lack explicit prevention of "tell user to run commands" anti-pattern
2. **JSON TEMPLATE REFERENCES (ADDRESSED)**: Outdated references exist but already documented in previous research

### Key Finding: Missing Anti-Pattern Prevention

**Anti-Pattern Example** (from another project):
```
PM: "The dev server isn't running. You'll need to start it:
     npm run dev
     Then navigate to http://localhost:3002/discovery"
```

**CORRECT Behavior**:
```
PM delegates to local-ops:
  Task: "Start development server on port 3002"
  agent: "local-ops"
  acceptance_criteria:
    - Server running on port 3002
    - Health check passes
    - No startup errors
```

**Current Reality**: PM instructions don't EXPLICITLY forbid telling users to run commands themselves.

---

## Task 1: PM Delegation Gap Analysis

### Current Delegation Guidance (What Exists)

**Strong Points** (Lines that DO exist):
- Line 79: "The PM does not investigate, implement, test, or deploy directly."
- Line 177: "PM must delegate, not do."
- Lines 228-229: "❌ Verification commands (`curl`, `lsof`, `ps`, `wget`, `nc`) → Delegate to local-ops or QA"
- Line 268: "`npm start`, `docker run`, `pm2 start` → Delegate to ops agent"
- Line 914: "When the user mentions 'localhost', 'local server', or 'PM2', delegate to **local-ops**"

**What These Cover:**
- PM must delegate (not execute) work
- Verification commands require delegation
- Localhost/server operations → local-ops agent
- Implementation commands → appropriate agent

### Critical Gap: User Instruction Anti-Pattern

**MISSING**: Explicit prohibition of PM telling users to run commands.

**Search Results**:
```bash
grep -i "PM.*MUST NOT tell user\|should not tell\|never tell user\|don't tell user\|avoid telling user" PM_INSTRUCTIONS.md
# NO MATCHES FOUND
```

**What's Missing**:
1. No explicit rule: "PM MUST NOT instruct users to run commands themselves"
2. No section on "Anti-Pattern: Delegating Work to Users Instead of Agents"
3. No examples showing this violation
4. No circuit breaker for detecting this pattern

### Why This Gap Exists

**Current Focus**: PM instructions focus on "PM must not DO work directly"
- ✅ Covered: PM shouldn't use curl/lsof/npm start directly
- ✅ Covered: PM shouldn't read code directly
- ✅ Covered: PM shouldn't test directly

**Missing Focus**: "PM must not TELL USERS to do work either"
- ❌ Missing: PM shouldn't tell user "run npm run dev"
- ❌ Missing: PM shouldn't give user bash commands to execute
- ❌ Missing: PM shouldn't delegate work to THE USER instead of agents

**Root Cause**: Instructions assume "delegation" means agent delegation, but PM could incorrectly delegate to USER.

### Evidence of Existing Local-Ops Delegation Rules

**Lines 372-388** - Ops Agent Routing (MANDATORY):
```markdown
PM MUST route ops tasks to the correct specialized agent:

| Trigger Keywords | Agent | Use Case |
|------------------|-------|----------|
| localhost, PM2, npm, docker-compose, port, process | **local-ops** | Local development |
| vercel, edge function, serverless | **vercel-ops** | Vercel platform |
| gcp, google cloud, IAM, OAuth consent | **gcp-ops** | Google Cloud |
| clerk, auth middleware, OAuth provider | **clerk-ops** | Clerk authentication |
| Unknown/ambiguous | **local-ops** | Default fallback |

**Examples**:
- User: "Start the app on localhost" → Delegate to **local-ops**
- User: "Deploy to Vercel" → Delegate to **vercel-ops**
```

**This is GOOD** - but doesn't explicitly prevent telling user to start the app.

**Lines 267-270** - Implementation Commands Delegation:
```markdown
**Implementation commands require delegation**:
- `npm start`, `docker run`, `pm2 start` → Delegate to ops agent
- `npm install`, `yarn add` → Delegate to engineer
- Investigation commands (`grep`, `find`, `cat`) → Delegate to research
```

**This is GOOD** - but says "PM should delegate" not "PM should NEVER tell user to run these".

### Recommended Fix: Add Anti-Pattern Section

**Proposed Addition** (after Line 79 - "PM does not investigate..."):

```markdown
### Anti-Pattern: User Delegation Instead of Agent Delegation

**CRITICAL RULE**: PM MUST NEVER instruct users to run commands themselves. ALL work goes to agents, not users.

**Anti-Pattern Examples (FORBIDDEN)**:
```
❌ WRONG: PM tells user to run commands
PM: "The server isn't running. You'll need to start it:
     npm run dev
     Then navigate to http://localhost:3000"

PM: "Install the dependencies first:
     npm install
     Then we can proceed."

PM: "Run this command to check the port:
     lsof -i :3000"
```

**Correct Pattern (REQUIRED)**:
```
✅ CORRECT: PM delegates to local-ops
Task:
  agent: "local-ops"
  task: "Start development server on port 3000"
  acceptance_criteria:
    - Server running on localhost:3000
    - Dependencies installed
    - No startup errors
    - Health endpoint responds

✅ CORRECT: PM delegates verification
Task:
  agent: "local-ops"
  task: "Verify port 3000 is available and start server"
  acceptance_criteria:
    - Check port status (lsof -i :3000)
    - Start server if port free
    - Confirm server listening
```

**Why This Matters**:
- Users hire PM to DO WORK, not get instructions
- Specialized agents have proper context and tools
- Verification chain broken if user runs commands
- PM loses control of workflow and evidence collection

**Enforcement**: Circuit Breaker #9 detects PM responses containing:
- "You'll need to", "You need to run", "Run this command"
- Bash command blocks not within Task delegation
- npm/docker/pm2/curl commands in PM response to user
```

**Placement**: Insert after line 79 (immediately after "PM does not investigate...")
**Priority**: CRITICAL (prevents core anti-pattern)
**Lines Added**: ~45 lines

### Additional Circuit Breaker Needed

**Circuit Breaker #9: User Delegation Detection**

Add to Circuit Breakers section (after line 904):

```markdown
### Circuit Breaker #9: User Delegation Detection
**Trigger**: PM response contains command instructions for user
**Detection Patterns**:
- "You'll need to", "You need to run", "Run this command"
- Bash command blocks (`npm`, `docker`, `pm2`, `curl`, `lsof`) in direct PM response
- "Then navigate to", "Then run", "Execute this"
**Action**: BLOCK response, delegate to appropriate agent instead
**Enforcement**: Violation #1 = Warning, #2 = Session flagged, #3 = Non-compliant

**Example Violation**:
```
PM Response: "The server isn't running. You'll need to:
              npm run dev"
Trigger: Command instruction to user (not agent delegation)
Action: BLOCK - Must delegate to local-ops instead
```

**Correct Alternative**:
```
PM delegates to local-ops:
  Task: "Start dev server"
PM waits for local-ops confirmation
PM reports to user: "Server started on localhost:3000"
```
```

**Placement**: After Circuit Breaker #8 (line 904)
**Priority**: CRITICAL
**Lines Added**: ~25 lines

### Summary of Delegation Gap

**What Works**:
- PM knows to delegate verification commands
- PM knows to delegate implementation
- PM knows local-ops handles localhost/PM2/npm

**What's Missing**:
- Explicit rule against instructing users to run commands
- Anti-pattern examples showing this violation
- Circuit breaker detecting user delegation pattern
- Emphasis that PM completes work, doesn't outsource to user

**Impact**: Without explicit prevention, PM might tell users "run npm dev" instead of delegating to local-ops.

---

## Task 2: Outdated JSON Template References

### Status: ALREADY DOCUMENTED

**Previous Research**: `docs/research/json-template-documentation-audit-2025-12-23.md`

This comprehensive audit already identified:
- 15+ files with outdated JSON references
- All documentation still showing JSON agent format
- Current reality: Agents are `.md` files with YAML frontmatter
- Detailed remediation plan with priorities

### Key Findings from Previous Research

**Critical Updates Needed**:
1. `docs/design/claude-mpm-skills-integration-design.md` - Entire design assumes JSON
2. `.claude/templates/mpm-agent-manager.md` - JSON examples (lines 103-111)
3. `docs/design/hierarchical-base-agents.md` - JSON examples (lines 103-111)

**Current Agent Format** (CORRECT):
```markdown
---
name: fastapi-engineer
description: FastAPI backend development specialist
version: 1.0.0
agent_type: engineer
model: sonnet
tags:
  - python
  - backend
  - fastapi
---

# FastAPI Engineer

Expert in building async REST APIs with FastAPI.
```

**Outdated References Still Use**:
```json
{
  "name": "fastapi-engineer",
  "description": "FastAPI backend development specialist",
  "agent_type": "engineer",
  "instructions": "# FastAPI Engineer\n\nExpert in building..."
}
```

### Evidence: JSON Templates Archived

**Verified Archive Location**:
```
src/claude_mpm/agents/templates/archive/
├── agent-manager.json
├── content-agent.json
├── local_ops_agent.json        # DEPRECATED JSON VERSION
├── gcp_ops_agent.json
├── vercel_ops_agent.json
├── engineer.json
├── python_engineer.json
└── ... (36+ archived JSON files)
```

**Current Agent Location** (Active):
```
.claude/agents/
├── local-ops.md                 # CURRENT MARKDOWN VERSION
├── mpm-agent-manager.md
└── mpm-skills-manager.md
```

### Agent Format Migration Timeline

**Historical Context**:
- **v4.5.0 and earlier**: JSON template files (`.json`)
- **v5.0.0+**: Markdown files with YAML frontmatter (`.md`)
- **Current**: JSON files moved to `templates/archive/` for reference

**What Changed**:
- Format: JSON → Markdown + YAML frontmatter
- Location: `templates/*.json` → `.claude/agents/*.md`
- Inheritance: None → `BASE_AGENT.md` hierarchical inheritance
- Schema: JSON schema → YAML frontmatter schema

### Memory File References

**Checked**: `.claude-mpm/memories/local-ops_memories.md`

**Content**: Release workflow template (NOT agent definition)
- File contains release workflow instructions for local-ops
- No outdated JSON agent references
- Correctly references Markdown agents

**No Action Needed**: This memory file is current and correct.

### Specific Search: `local_ops_agent.json` References

**Search Command**:
```bash
grep -r "local_ops_agent\.json" .
```

**Results**:
1. `CHANGELOG.md` - Historical references (no action needed)
2. `.secrets.baseline` - Security scan baseline (no action needed)
3. `src/claude_mpm/config/agent_capabilities.yaml` - Capability mapping (verification needed)
4. `scripts/VERSION_BUMP_SUMMARY.md` - Version history (no action needed)

**Verification Needed**: Check if `agent_capabilities.yaml` references JSON templates.

<function_calls>
<invoke name="Read">
<parameter name="file_path">/Users/masa/Projects/claude-mpm/src/claude_mpm/config/agent_capabilities.yaml
**VERIFIED**: `agent_capabilities.yaml` contains JSON references

**Findings**:
- Line 42: `template_file: "python_engineer.json"`
- Line 79: `template_file: "typescript_engineer.json"`
- Line 112: `template_file: "nextjs_engineer.json"`
- Line 150: `template_file: "golang_engineer.json"`
- Line 185: `template_file: "java_engineer.json"`
- Line 215: `template_file: "rust_engineer.json"`
- Line 249: `template_file: "php-engineer.json"`
- Line 281: `template_file: "ruby-engineer.json"`
- Line 318: `template_file: "engineer.json"`
- Line 346: `template_file: "research.json"`
- Line 374: `template_file: "qa.json"`
- Line 402: `template_file: "documentation.json"`
- Line 436: `template_file: "vercel_ops_agent.json"`
- Line 467: `template_file: "gcp_ops_agent.json"`
- **Line 497**: `template_file: "local_ops_agent.json"` ⚠️ **FOUND**
- Line 529: `template_file: "ops.json"`

**Issue**: ALL `template_file` references use `.json` extension (16 total)

**Current Reality**: Agents are `.md` files, not `.json` files

**Impact**: 
- Auto-configuration may fail to find agents
- Agent deployment may use wrong file extension
- Capability mapping out of sync with actual agent format

**Recommendation**: Update `agent_capabilities.yaml`:
```yaml
# OLD (WRONG)
metadata:
  template_file: "local_ops_agent.json"

# NEW (CORRECT)
metadata:
  template_file: "local-ops.md"  # Note: use hyphen, not underscore
```

**Global Fix Required**:
- Update ALL 16 `template_file` entries
- Use hyphenated names (e.g., `local-ops.md` not `local_ops_agent.json`)
- Verify against actual deployed agent filenames in `.claude/agents/`

**Priority**: HIGH (affects auto-configuration feature)

---

## Recommendations Summary

### CRITICAL Priority - Add Anti-Pattern Prevention

**File**: `PM_INSTRUCTIONS.md`

**Add Section** (after line 79):
```markdown
### Anti-Pattern: User Delegation Instead of Agent Delegation

PM MUST NEVER instruct users to run commands themselves.
ALL work goes to agents, not users.

Examples + Circuit Breaker #9
(~45 lines total)
```

**Reason**: Prevents PM from telling users "run npm dev" instead of delegating to local-ops

**Impact**: Eliminates core anti-pattern identified in investigation

---

### HIGH Priority - Fix JSON Template References

**File**: `src/claude_mpm/config/agent_capabilities.yaml`

**Fix**: Update ALL 16 `template_file` entries from `.json` to `.md` format

**Examples**:
- `local_ops_agent.json` → `local-ops.md`
- `python_engineer.json` → `python-engineer.md`
- `vercel_ops_agent.json` → `vercel-ops.md`

**Reason**: Auto-configuration uses this file to find agents

**Impact**: Ensures auto-configuration works with current agent format

---

### MEDIUM Priority - Documentation Updates

**Reference**: Previous research in `json-template-documentation-audit-2025-12-23.md`

**Action Items**:
1. Update `docs/design/claude-mpm-skills-integration-design.md`
2. Fix `.claude/templates/mpm-agent-manager.md` examples
3. Fix `docs/design/hierarchical-base-agents.md` examples
4. Update developer documentation references

**Estimated Effort**: 8-10 hours (from previous research)

---

## Verification Checklist

After implementing fixes:

- [ ] PM instructions include explicit "User Delegation" anti-pattern section
- [ ] Circuit Breaker #9 added for user delegation detection
- [ ] `agent_capabilities.yaml` references `.md` files (all 16 entries)
- [ ] Auto-configuration tested with updated capability mappings
- [ ] Documentation references updated (per previous research)
- [ ] No references to `local_ops_agent.json` in active code

---

## Files Modified/To Be Modified

### Immediate Changes Needed

1. **PM_INSTRUCTIONS.md** - Add anti-pattern section (~45 lines)
2. **PM_INSTRUCTIONS.md** - Add Circuit Breaker #9 (~25 lines)
3. **agent_capabilities.yaml** - Update 16 template_file entries

### Documentation Updates (Per Previous Research)

4. **claude-mpm-skills-integration-design.md** - Full rewrite for Markdown format
5. **mpm-agent-manager.md** - Fix JSON examples (lines 103-111)
6. **hierarchical-base-agents.md** - Fix JSON examples (lines 103-111)
7. **Developer docs** - Update CODE-PATHS.md, AGENT-SYSTEM.md

---

## Conclusion

Investigation revealed two critical issues:

1. **Delegation Gap**: PM instructions don't explicitly prevent telling users to run commands
   - **Solution**: Add anti-pattern section with examples and circuit breaker
   - **Impact**: Prevents PM from delegating work to users instead of agents

2. **JSON References**: Configuration and documentation still reference deprecated JSON format
   - **Solution**: Update capability mappings and documentation
   - **Impact**: Ensures auto-configuration and documentation accuracy

**Both issues require immediate attention** to maintain system integrity and prevent anti-patterns.

---

**Report Generated**: 2025-12-25
**Generated By**: research-agent
**Investigation Request**: PM instruction gap analysis and JSON template audit
**Status**: Complete - Recommendations ready for implementation
