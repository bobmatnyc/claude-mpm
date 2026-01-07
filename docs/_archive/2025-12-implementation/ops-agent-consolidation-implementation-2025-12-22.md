# Ops Agent Consolidation - Implementation Summary

**Date**: 2025-12-22
**Status**: ✅ Completed
**Related Research**: [ops-agent-consolidation-analysis-2025-12-22.md](./ops-agent-consolidation-analysis-2025-12-22.md)

## Changes Implemented

### 1. PM Instructions Updated

**File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`

#### A. Bash Tool Restrictions
Changed from:
```
Allowed Uses:
- Navigation: ls, pwd, cd
- Verification: curl, lsof, ps (checking deployments)
- Git tracking: git status, git add, git commit
```

To:
```
Allowed Uses:
- Navigation: ls, pwd, cd (understanding project structure)
- Git tracking: git status, git add, git commit (file management)

FORBIDDEN Uses (MUST delegate instead):
- Verification commands (curl, lsof, ps, wget, nc) → Delegate to local-ops or QA
- Browser testing tools → Delegate to web-qa
```

**Impact**: PM can no longer run verification commands directly. Must delegate to appropriate agents.

#### B. Ops Agent Routing Matrix (NEW)
Added mandatory routing table:

| Trigger Keywords | Agent | Use Case |
|------------------|-------|----------|
| localhost, PM2, npm, docker-compose, port, process | **local-ops** | Local development |
| vercel, edge function, serverless | **vercel-ops** | Vercel platform |
| gcp, google cloud, IAM, OAuth consent | **gcp-ops** | Google Cloud |
| clerk, auth middleware, OAuth provider | **clerk-ops** | Clerk authentication |
| Unknown/ambiguous | **local-ops** | Default fallback |

**Note**: Generic `ops` agent is DEPRECATED.

#### C. Circuit Breaker #7: Verification Command Detection (NEW)

**Trigger**: PM using verification commands instead of delegating

**Detection Patterns**:
- PM runs `curl`, `lsof`, `ps`, `wget`, `nc`, `netcat`
- PM checks ports, processes, or HTTP endpoints directly
- PM performs any verification that should be delegated

**Correct Action**:
- Delegate to **local-ops** for local verification (ports, processes, localhost endpoints)
- Delegate to **QA agents** for HTTP/API testing (deployed endpoints)
- Delegate to appropriate platform ops agent (vercel-ops, gcp-ops, etc.)

**Examples**:

❌ **VIOLATION**: PM runs verification directly
```bash
PM: curl http://localhost:3000
PM: lsof -i :3000
PM: ps aux | grep node
```

✅ **CORRECT**: PM delegates verification
```
Task:
  agent: "local-ops"
  task: "Verify app is running on localhost:3000"
  acceptance_criteria:
    - Check port is listening (lsof)
    - Test HTTP endpoint (curl)
    - Check for errors in logs
```

**Enforcement**:
- Violation #1: ⚠️ WARNING - PM must delegate to local-ops or QA
- Violation #2: 🚨 ESCALATION - Flag for review
- Violation #3: ❌ FAILURE - Session non-compliant

#### D. Updated Common User Request Patterns
Added:
```
When the user mentions "verify running", "check port", or requests verification
of deployments, delegate to local-ops for local verification or QA agents for
deployed endpoints.
```

### 2. Generic Ops Agent Deprecated

**File**: `.claude/agents/ops.md`

#### Changes:
- Added deprecation notice in YAML frontmatter:
  ```yaml
  version: "2.2.5-deprecated"
  deprecated: true
  replacement: "local-ops (default), vercel-ops, gcp-ops, clerk-ops"
  ```

- Updated description to warn users
- Added prominent deprecation header
- Listed replacement agents with use cases
- Referenced PM_INSTRUCTIONS.md for routing guidance
- Kept original documentation for reference

**Note**: This file is in `.claude/agents/` (gitignored), so changes only affect local environment.

## Rationale

### Why Remove Verification Commands from PM?

1. **Separation of Concerns**: PM orchestrates, specialized agents execute
2. **Expertise**: local-ops has domain knowledge for local dev environments
3. **Verification Chain**: Independent verification prevents blind spots
4. **Consistency**: All verification goes through same agents for reproducible results

### Why Deprecate Generic Ops?

1. **Platform Specialization**: Each platform (Vercel, GCP, local) has unique tooling
2. **Better Routing**: Explicit keywords (localhost, vercel, gcp) route to right agent
3. **Reduced Ambiguity**: Platform-specific agents have focused responsibilities
4. **Default Fallback**: local-ops serves as safe default for ambiguous requests

## Testing Checklist

After implementation, verify:
- [ ] PM instructions compile/parse correctly
- [ ] No broken references to generic `ops` in PM instructions
- [ ] `local-ops` is reachable as default fallback
- [ ] Circuit Breaker #7 enforcement works (PM can't run curl/lsof)
- [ ] Ops routing matrix is clear and actionable
- [ ] Deprecation notice appears when using generic `ops` agent

## Migration Path for Users

### Old Pattern (DEPRECATED)
```
User: "Check if the app is running on localhost:3000"
PM: curl http://localhost:3000  # VIOLATION
```

### New Pattern (CORRECT)
```
User: "Check if the app is running on localhost:3000"
PM: Task(agent="local-ops", task="Verify app is running on localhost:3000",
         acceptance_criteria=[...])
local-ops: Runs lsof, curl, checks logs
local-ops: Returns evidence to PM
PM: Reports verification results to user
```

## Files Modified

1. **PM Instructions** (tracked in git):
   - `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
   - Commit: `feat(pm): implement ops agent consolidation and verification delegation`

2. **Generic Ops Agent** (gitignored, local only):
   - `/Users/masa/Projects/claude-mpm/.claude/agents/ops.md`
   - Changes not tracked in git

## Related Tickets

- Research: [ops-agent-consolidation-analysis-2025-12-22.md](./ops-agent-consolidation-analysis-2025-12-22.md)
- Circuit Breaker enforcement: PM_INSTRUCTIONS.md line 462+

## Future Enhancements

1. **Automated Detection**: Could add tooling to detect PM verification violations
2. **Metrics Tracking**: Track how often PM delegates to local-ops vs other ops agents
3. **Template Expansion**: Add more platform-specific ops agents as needed (aws-ops, railway-ops, etc.)
4. **Circuit Breaker Testing**: Add automated tests for Circuit Breaker #7 violations

## Summary

This implementation successfully consolidates ops agent responsibilities and enforces proper delegation from PM to specialized ops agents. The generic `ops` agent is deprecated in favor of platform-specific agents with `local-ops` as the default fallback. Circuit Breaker #7 ensures PM cannot bypass verification delegation.

**Key Principle**: PM orchestrates, specialized agents execute. Verification is a specialized responsibility, not a PM capability.
