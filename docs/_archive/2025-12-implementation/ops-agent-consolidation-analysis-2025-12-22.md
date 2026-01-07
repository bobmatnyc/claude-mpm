# Ops Agent Consolidation Analysis

**Date**: 2025-12-22
**Researcher**: Research Agent
**Status**: Investigation Complete

---

## Executive Summary

Investigated the current ops agent structure to identify redundancy and propose consolidation. Found 5 ops agents with significant overlap in base functionality but specialized in platform-specific operations. Current PM tool restrictions allow Bash for "navigation and verification" which creates ambiguity about when to delegate vs execute directly.

**Key Recommendation**: Maintain specialized platform ops agents but clarify PM-to-ops delegation boundaries. Remove generic `ops` agent in favor of `local-ops` as default.

---

## 1. Current State: What Ops Agents Exist?

### Active Ops Agents (`.claude/agents/`)

| Agent | Version | Focus | Type | Lines |
|-------|---------|-------|------|-------|
| **ops** | 2.2.4 | Generic infrastructure/DevOps | ops | 831 |
| **local-ops** | 2.0.1 | Local dev environments (PM2/Docker) | specialized | 616 |
| **vercel-ops** | 2.0.1 | Vercel platform deployments | ops | 983 |
| **gcp-ops** | 1.0.2 | Google Cloud Platform | ops | 718 |
| **clerk-ops** | 1.1.1 | Clerk authentication service | ops | 914 |

**All agents inherit**: `BASE_OPS.md` (520 lines) + `BASE_AGENT_TEMPLATE.md` (232 lines)

---

## 2. Agent Purpose Analysis

### Generic `ops` Agent

**Focus**: Infrastructure automation and system operations
- Infrastructure management (servers, containers, orchestration)
- Deployment (CI/CD pipelines, release management)
- Monitoring (logs, metrics, alerts)
- Security (access control, secrets management)

**Capabilities**:
- Docker operations
- Kubernetes operations (if applicable)
- CI/CD pipeline management
- Security scanning
- Git commit authority with mandatory security verification

**Problem**: Very broad scope with no specific platform expertise. Overlaps significantly with specialized agents.

### `local-ops` Agent

**Focus**: Local development environments, process supervision (PM2/Docker), and service health

**Responsibilities**:
- Manage local dev environments
- Process supervision (PM2/Docker)
- Service health verification
- Database lifecycle (create/migrate/seed/rollback)
- Quality gates before deployment (lint/test/security)
- Port management and process coordination

**Workflows**:
- Setup: Install dependencies, start services (docker-compose/PM2)
- Deploy locally: Build artifacts, run smoke tests, verify logs/ports
- Rollback/cleanup: Stop services, prune containers

**Key Differentiator**: Specializes in localhost operations, PM2, docker-compose, and local development workflows.

### Platform-Specific Ops Agents

#### `vercel-ops`
- Vercel platform deployment, edge functions, serverless architecture
- Environment variable management (security-first with `--sensitive` flag)
- Advanced deployment strategies
- Performance monitoring and cost optimization
- **Unique Feature**: Deep Vercel CLI integration, branch-specific environments

#### `gcp-ops`
- Google Cloud Platform authentication and resource management
- OAuth 2.0 configuration and service account management
- gcloud CLI operations (compute, run, container, sql, storage)
- IAM policy management
- **Unique Feature**: OAuth consent screen configuration, Workload Identity for GKE

#### `clerk-ops`
- Clerk authentication setup, configuration, and troubleshooting
- Dynamic port configuration patterns for localhost development
- Middleware configuration expertise (`clerkMiddleware`)
- OAuth provider setup (Google, GitHub)
- **Unique Feature**: Development vs production architecture understanding, infinite redirect loop resolution

---

## 3. Overlap/Redundancy Analysis

### Common Responsibilities (All Agents)

From `BASE_OPS.md` (shared across all ops agents):
- Infrastructure as Code (IaC) principles
- Deployment philosophy (automated, reversible, gradual, monitored, verified)
- Deployment verification requirements
- Security scanning (pre-push security checks)
- Container management (Docker best practices)
- Monitoring & observability
- CI/CD pipeline stages
- Resource optimization
- Version control for ops
- Database migration workflows
- API development standards

**Observation**: 520 lines of shared base instructions create significant redundancy.

### Unique Capabilities

| Agent | Unique Responsibilities |
|-------|------------------------|
| **ops** | None (all capabilities present in specialized agents) |
| **local-ops** | PM2 management, local port coordination, docker-compose workflows |
| **vercel-ops** | Vercel CLI, edge function optimization, environment variable encryption |
| **gcp-ops** | gcloud CLI, OAuth consent screens, IAM policies, Workload Identity |
| **clerk-ops** | ClerkProvider configuration, middleware patterns, infinite redirect fixes |

**Finding**: Generic `ops` agent has NO unique capabilities not covered by specialized agents.

---

## 4. PM Tool Restrictions (Current State)

From `PM_INSTRUCTIONS.md` (lines 292-340):

### Bash Tool (Verification and File Tracking)

**Allowed Uses**:
- Navigation: `ls`, `pwd`, `cd` (understanding project structure)
- Verification: `curl`, `lsof`, `ps` (checking deployments)
- Git tracking: `git status`, `git add`, `git commit` (file management)

**FORBIDDEN Uses**:
- ❌ Browser testing tools → Delegate to web-qa (use Playwright via web-qa agent)

**Implementation Commands Require Delegation**:
- `npm start`, `docker run`, `pm2 start` → Delegate to ops agent
- `npm install`, `yarn add` → Delegate to engineer
- Investigation commands (`grep`, `find`, `cat`) → Delegate to research

### Current Ambiguity

**Problem**: PM can use `curl`, `lsof`, `ps` for "verification" but must delegate `npm start`, `docker run` to ops.

**Questions**:
- When does "verification" end and "implementation" begin?
- Should PM be able to check `lsof -i :3000` but not start the server?
- Does PM need direct verification, or should ops agent verify and report?

---

## 5. Usage Analysis: Generic vs Specialized

### When is Generic `ops` Used vs `local-ops`?

**From PM Instructions (lines 481-491)**:
> Delegate when work involves:
> - Deploying applications or services
> - Managing infrastructure or environments
> - Starting/stopping servers or containers
> - Port management or process management
>
> **Important**: For localhost/PM2/local development work, use `local-ops-agent` as primary choice. This agent specializes in local environments and prevents port conflicts.

**Observation**: PM instructions explicitly prefer `local-ops` for local development. Generic `ops` lacks a clear use case.

### Platform-Specific Routing (From PM Instructions)

**Line 482**: "For localhost/PM2/local development work, use `local-ops-agent` as primary choice."

**Line 458-527**: Delegation guidance shows:
- Ops Agent (Local-Ops for Local Development)
- Platform-specific agents (Vercel, GCP, Clerk) for their respective platforms

**Pattern**: PM already routes to specialized agents. Generic `ops` is redundant.

---

## 6. Proposed Consolidation Structure

### Option A: Remove Generic `ops` (Recommended)

**Hierarchy**:
```
local-ops      → Default for local dev: npm, pm2, docker-compose, ports, processes
vercel-ops     → Vercel deployments (edge functions, environment management)
gcp-ops        → Google Cloud Platform (gcloud CLI, IAM, OAuth)
clerk-ops      → Clerk authentication (middleware, OAuth providers)
railway-ops    → Railway deployments (if needed - not currently deployed)
```

**Rationale**:
- `local-ops` covers 90% of development workflow needs
- Platform-specific agents handle production deployments
- No overlap: Each agent has distinct platform/service expertise
- Clear routing: PM checks target platform → delegates to specific agent

**Pros**:
- ✅ Eliminates redundancy (remove 831-line generic agent)
- ✅ Forces explicit platform selection (clearer intent)
- ✅ Each agent has well-defined scope
- ✅ Better logging/tracking (agent name shows platform)

**Cons**:
- ❌ No fallback for unknown platforms (could add later if needed)
- ❌ Requires PM to make platform decision (but PM already does this)

### Option B: Keep Generic `ops` as Fallback

**Hierarchy**:
```
local-ops      → Local dev (default)
vercel-ops     → Vercel (explicit)
gcp-ops        → GCP (explicit)
clerk-ops      → Clerk (explicit)
ops            → Fallback for unknown platforms
```

**Rationale**: Provides safety net for edge cases.

**Pros**:
- ✅ Handles unknown platforms gracefully
- ✅ Maintains backward compatibility

**Cons**:
- ❌ Keeps 831 lines of redundant agent code
- ❌ Ambiguous when to use generic vs specialized
- ❌ PM may default to generic instead of specialized (worse routing)
- ❌ Generic agent lacks platform-specific expertise (worse quality)

---

## 7. PM Tool Restrictions: Proposed Changes

### Current Problem

**PM Allowed**:
- ✅ `curl`, `lsof`, `ps` (verification)
- ✅ `ls`, `pwd`, `cd` (navigation)
- ✅ `git status`, `git add`, `git commit` (git tracking)

**PM Forbidden**:
- ❌ `npm start`, `docker run`, `pm2 start` (delegate to ops)
- ❌ `grep`, `find`, `cat` (delegate to research)

**Ambiguity**: Where is the line between "verification" and "implementation"?

### Option 1: Remove PM Bash Entirely (Strictest)

**Proposal**: PM delegates ALL commands to specialized agents.

**Changes**:
- ❌ Remove `curl`, `lsof`, `ps` from PM
- ❌ Remove `ls`, `pwd`, `cd` from PM
- ✅ Keep `git status`, `git add`, `git commit` (file tracking responsibility)

**Rationale**:
- Navigation: Research/Engineer can provide file listings
- Verification: Ops/QA agents should verify and report (not PM)
- Git tracking: PM's core responsibility (must retain)

**Workflow**:
```
User: "Check if app is running"
PM → local-ops: "Verify app is running on port 3000"
local-ops: "lsof -i :3000 shows app is listening, curl returns HTTP 200"
PM → User: "local-ops verified app is running (port 3000 listening, HTTP 200)"
```

**Pros**:
- ✅ Clearest separation of concerns
- ✅ All execution goes through specialized agents
- ✅ Better logging/tracking (agent captures all commands)
- ✅ Forces PM to collect evidence from agents (better verification)

**Cons**:
- ❌ Overhead for simple `ls` or `pwd` (roundtrip to agent)
- ❌ Verification requires agent delegation (more steps)
- ❌ PM cannot quickly check git status without full command (but still has git tracking)

### Option 2: Keep Navigation, Remove Verification (Moderate)

**Proposal**: PM keeps navigation for orientation, delegates verification to ops.

**Changes**:
- ❌ Remove `curl`, `lsof`, `ps` from PM
- ✅ Keep `ls`, `pwd`, `cd` (navigation)
- ✅ Keep `git status`, `git add`, `git commit` (git tracking)

**Rationale**:
- Navigation helps PM understand project structure (minimal cost)
- Verification is ops domain (should be delegated)
- Git tracking is PM's core responsibility

**Pros**:
- ✅ PM can orient itself (`ls`, `pwd`) without delegation
- ✅ Verification delegated to specialists (better quality)
- ✅ Less overhead than full delegation
- ✅ Clear distinction: navigation vs verification

**Cons**:
- ❌ Still allows some Bash usage (less clean separation)
- ❌ PM might rely on navigation instead of delegating investigation

### Option 3: Keep Current Bash Access (Status Quo)

**Proposal**: No changes to PM Bash usage.

**Pros**:
- ✅ No migration needed
- ✅ PM can verify quickly without delegation overhead

**Cons**:
- ❌ Ambiguous boundary (verification vs implementation)
- ❌ PM bypasses agent expertise for verification
- ❌ Less comprehensive logging (PM commands not tracked by agents)

---

## 8. Recommendations

### Primary Recommendation: Hybrid Approach

**1. Agent Structure**:
- ✅ Remove generic `ops` agent
- ✅ Make `local-ops` the default for local development
- ✅ Keep platform-specific agents (vercel-ops, gcp-ops, clerk-ops)
- ✅ Add new platform agents as needed (e.g., railway-ops, aws-ops)

**2. PM Tool Restrictions**:
- ✅ **Keep navigation**: `ls`, `pwd`, `cd` (helps PM understand structure)
- ❌ **Remove verification**: `curl`, `lsof`, `ps` (delegate to ops/qa)
- ✅ **Keep git tracking**: `git status`, `git add`, `git commit` (PM responsibility)

**3. Delegation Routing**:

Update PM instructions with clear platform routing:
```
User request contains:
- "localhost", "PM2", "docker-compose", "local dev" → local-ops
- "vercel", "edge function", "serverless" → vercel-ops
- "gcp", "google cloud", "gcloud" → gcp-ops
- "clerk", "authentication", "oauth consent" → clerk-ops
- "railway", "railway.app" → railway-ops (if deployed)
- Unknown platform → Ask user OR use local-ops as fallback
```

**4. PM Verification Protocol**:

Instead of PM using `curl`/`lsof` directly:
```
PM delegates verification to appropriate ops agent:
  Task:
    agent: "local-ops"
    task: "Verify app is running on localhost:3000"
    acceptance_criteria:
      - Port 3000 is listening (lsof)
      - HTTP endpoint responds (curl)
      - Logs show no errors
      - Process is healthy
```

### Migration Path

**Phase 1: Documentation Updates**
1. Update PM instructions to remove `curl`, `lsof`, `ps` from allowed Bash usage
2. Add platform routing decision tree to PM instructions
3. Clarify that verification is delegated to ops agents

**Phase 2: Agent Deprecation**
1. Mark generic `ops` agent as deprecated
2. Add deprecation notice to ops agent description
3. Update PM instructions to prefer `local-ops` for all local work

**Phase 3: Removal** (Optional)
1. Remove generic `ops` agent from `.claude/agents/`
2. Remove `ops.json` from templates archive
3. Update any hardcoded references to `ops` agent in codebase

---

## 9. Implementation Considerations

### Backward Compatibility

**Concern**: Existing users may have workflows referencing generic `ops` agent.

**Solution**: Deprecation path with clear migration guide:
```markdown
# Migration: ops → local-ops

The generic `ops` agent has been deprecated in favor of specialized agents.

Old:
  PM → ops → "Deploy to localhost"

New:
  PM → local-ops → "Deploy to localhost"  (local development)
  PM → vercel-ops → "Deploy to Vercel"   (Vercel platform)
  PM → gcp-ops → "Deploy to GCP"          (Google Cloud)
```

### PM Tool Consistency

**Current**: PM has Read (1 file max), Bash (navigation + verification + git), Task (delegation)

**Proposed**: PM has Read (1 file max), Bash (navigation + git only), Task (delegation)

**Change**: PM must delegate verification commands to ops/qa agents instead of executing directly.

**Example**:
```
Before:
  PM: curl http://localhost:3000  # Direct verification

After:
  PM → local-ops: "Verify http://localhost:3000 is accessible"
  local-ops: "curl returned HTTP 200, app is running"
  PM → User: "local-ops verified app is accessible (HTTP 200)"
```

### Circuit Breaker Integration

**Existing**: Circuit Breaker #2 blocks PM Read usage beyond 1 file
**Proposed**: Circuit Breaker #7 blocks PM verification Bash commands (curl, lsof, ps)

**Enforcement**:
- PM attempts `curl` → Blocked → Must delegate to ops agent
- PM attempts `lsof` → Blocked → Must delegate to ops agent
- PM attempts `ps` → Blocked → Must delegate to ops agent

---

## 10. Alternative Approaches Considered

### Alternative 1: Merge All Ops into Single Agent

**Proposal**: Single `ops` agent with platform detection logic.

**Rejected Because**:
- ❌ Loses platform-specific expertise (1000+ lines per platform)
- ❌ Agent becomes too large (4000+ lines)
- ❌ Harder to maintain (all platforms in one file)
- ❌ Less clear intent (agent name doesn't show platform)

### Alternative 2: Keep All Agents Including Generic

**Proposal**: Maintain status quo with all 5 agents.

**Rejected Because**:
- ❌ Generic `ops` has no unique capabilities
- ❌ Redundancy creates confusion (which ops to use?)
- ❌ Wastes 831 lines of agent instructions
- ❌ PM routing becomes ambiguous

### Alternative 3: Ops as Router Only

**Proposal**: Generic `ops` becomes a router that delegates to platform-specific agents.

**Rejected Because**:
- ❌ Adds extra delegation layer (PM → ops → platform-ops)
- ❌ PM already has platform routing logic
- ❌ No benefit over PM routing directly

---

## 11. Metrics for Success

### Agent Usage Metrics
- Track how often `local-ops` is delegated to (should be majority)
- Track platform-specific agent usage (vercel-ops, gcp-ops, etc.)
- Monitor deprecated `ops` agent usage (should decline to zero)

### PM Tool Usage Metrics
- Track PM Bash commands (should see no verification commands after migration)
- Track Task delegations to ops agents (should increase for verification)
- Monitor circuit breaker triggers for verification Bash usage

### Quality Metrics
- Deployment verification completeness (ops agent verification rate)
- Evidence collection quality (ops agent reports with curl/lsof/ps output)
- User satisfaction with ops delegation (fewer ambiguous failures)

---

## 12. Open Questions

### Q1: Should PM Be Able to Run ANY Bash Commands?

**Current Constraint**: PM can run navigation (`ls`, `pwd`) and verification (`curl`, `lsof`, `ps`).

**Alternative**: PM has NO Bash access except git commands.

**Trade-off**: Convenience vs separation of concerns.

**Recommendation**: Remove verification Bash, keep navigation + git.

### Q2: Is Generic `ops` Needed for Unknown Platforms?

**Scenario**: User deploys to platform not covered by existing agents (e.g., DigitalOcean, Heroku, Render).

**Options**:
1. Fallback to `local-ops` (most deployments are similar to local)
2. Fallback to generic `ops` (dedicated agent for unknown platforms)
3. Ask user to specify platform (PM clarifies before delegation)

**Recommendation**: Option 3 (PM asks user for platform) + Option 1 fallback (local-ops for unknown).

### Q3: Should PM Verification Require Ops Agent Delegation?

**Current**: PM can run `curl http://localhost:3000` directly.

**Proposed**: PM delegates to ops agent for verification.

**User Impact**: Extra delegation step for simple checks.

**Recommendation**: Yes, delegate verification to ops agents (better evidence, consistent logging).

---

## 13. Related Documentation

### Files to Update

1. `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
   - Remove `curl`, `lsof`, `ps` from Bash allowed commands
   - Add platform routing decision tree
   - Clarify verification delegation protocol

2. `.claude/agents/ops.md`
   - Add deprecation notice
   - Redirect to specialized agents

3. `.claude/agents/local-ops.md`
   - Emphasize as default for local development
   - Document verification protocols

4. Platform-specific agent docs (vercel-ops.md, gcp-ops.md, clerk-ops.md)
   - No changes needed (already well-scoped)

### New Documentation Needed

1. `docs/ops-agent-migration-guide.md`
   - Migration from generic `ops` to specialized agents
   - Examples of platform routing
   - Verification delegation patterns

2. `docs/pm-tool-restrictions.md`
   - Complete reference of PM allowed vs forbidden tools
   - Rationale for each restriction
   - Examples of correct delegation

---

## Appendices

### Appendix A: Agent Line Counts

| Component | Lines | Notes |
|-----------|-------|-------|
| BASE_OPS.md | 520 | Shared across all ops agents |
| BASE_AGENT_TEMPLATE.md | 232 | Shared across ALL agents |
| ops.md (agent-specific) | 79 | Minimal unique content |
| local-ops.md (agent-specific) | 24 | Minimal unique content |
| vercel-ops.md (agent-specific) | 231 | Substantial Vercel expertise |
| gcp-ops.md (agent-specific) | 126 | GCP-specific knowledge |
| clerk-ops.md (agent-specific) | 162 | Clerk authentication patterns |

**Finding**: Generic `ops` has only 79 lines of unique content vs 520 lines of shared base.

### Appendix B: PM Bash Command Analysis

**From PM_INSTRUCTIONS.md** (lines 292-340):

**Currently Allowed**:
- Navigation: `ls`, `pwd`, `cd`
- Verification: `curl`, `lsof`, `ps`
- Git tracking: `git status`, `git add`, `git commit`

**Currently Forbidden**:
- Implementation: `npm start`, `docker run`, `pm2 start`
- Investigation: `grep`, `find`, `cat`
- Browser testing: All `mcp__chrome-devtools__*` tools

**Proposed Changes**:
- ✅ Keep: `ls`, `pwd`, `cd` (navigation)
- ❌ Remove: `curl`, `lsof`, `ps` (delegate to ops)
- ✅ Keep: `git status`, `git add`, `git commit` (git tracking)
- ❌ Keep Forbidden: All implementation and investigation commands

### Appendix C: Platform Routing Examples

```
User: "Deploy to localhost:3000"
PM detects: "localhost" → Delegate to local-ops

User: "Deploy to Vercel"
PM detects: "vercel" → Delegate to vercel-ops

User: "Configure GCP OAuth consent screen"
PM detects: "GCP" + "OAuth" → Delegate to gcp-ops

User: "Fix Clerk authentication redirect loop"
PM detects: "Clerk" + "authentication" → Delegate to clerk-ops

User: "Deploy to production"
PM clarifies: "Which platform? (Vercel/GCP/Railway/Other)"
User: "Railway"
PM detects: "Railway" → Delegate to railway-ops (if deployed) or local-ops (fallback)
```

---

## Conclusion

**Primary Recommendation**: Remove generic `ops` agent and refine PM tool restrictions.

**Agent Structure**:
- Remove `ops` (redundant)
- Keep `local-ops` as default
- Keep platform-specific agents (vercel-ops, gcp-ops, clerk-ops)

**PM Tool Restrictions**:
- Remove verification Bash commands (`curl`, `lsof`, `ps`)
- Keep navigation Bash commands (`ls`, `pwd`, `cd`)
- Keep git tracking Bash commands (`git status`, `git add`, `git commit`)
- Delegate ALL verification to ops/qa agents

**Benefits**:
- ✅ Eliminates redundancy (remove 831-line generic agent)
- ✅ Clearer PM-to-ops boundaries (verification is delegated)
- ✅ Better evidence collection (ops agents provide verification)
- ✅ Consistent logging (all ops commands tracked by agents)
- ✅ Maintains navigation for PM orientation (minimal overhead)

**Migration Path**: Deprecate generic `ops`, update PM instructions, deploy platform routing updates.

---

**Research Complete**: 2025-12-22
**File**: /Users/masa/Projects/claude-mpm/docs/research/ops-agent-consolidation-analysis-2025-12-22.md
