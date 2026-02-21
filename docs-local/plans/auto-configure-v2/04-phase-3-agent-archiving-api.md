# Phase 3: Wire Agent Archiving into API Auto-Configure

## Objective

Close the agent archiving gap in the API auto-configure path. Currently, the API deploys new agents but never reviews or archives existing unused agents. After this phase, the API will use `AgentReviewService` to categorize existing agents, include `would_archive` data in the preview response, and archive unused agents to `.claude/agents/unused/` during apply.

## Prerequisites

- **Phase 0 (Scope Abstraction)** must be complete. The archiving code will use `resolve_archive_dir()` from `core/config_scope.py` for path resolution.

## Scope

**IN SCOPE:**
- Adding agent review logic to the preview endpoint (returns `would_archive`)
- Adding agent archiving to the apply flow (moves unused agents to `unused/`)
- Adding a "archiving_agents" phase to Socket.IO progress events
- Including archive results in completion event data
- Adding a lazy singleton for `AgentReviewService`

**NOT IN SCOPE:**
- User-scoped agent archiving (only project-scoped for now)
- An `archive_agents` opt-out flag in the API (nice-to-have, can be added later)
- Modifying `AgentReviewService` itself -- it is used as-is
- Dashboard UI changes -- those are in Phase 4

## Current State

### What the CLI does

**File:** `src/claude_mpm/cli/commands/auto_configure.py`

**Step 1: Review existing agents (lines 917-958)**
```python
def _review_project_agents(self, agent_preview):
    review_service = AgentReviewService()
    review = review_service.review_project_agents(
        project_path=Path.cwd(),
        recommended_agent_ids=[rec.agent_id for rec in agent_preview.recommendations]
    )
    return review
```

**File:** `src/claude_mpm/services/agents/agent_review_service.py` (281 lines)

`AgentReviewService.review_project_agents()` categorizes agents into:
- **managed**: Agents tracked by claude-mpm
- **outdated**: Managed agents needing updates
- **custom**: User-created agents (not from managed sources)
- **unused**: Agents not in the recommended set

**Step 2: Archive unused agents (lines 368-377)**
```python
project_agents_dir = Path.cwd() / ".claude" / "agents"
review_service.archive_agents(agents_to_archive, project_agents_dir)
```

`archive_agents()` moves agent files to `.claude/agents/unused/` with a timestamp suffix for recovery. It does NOT delete agents.

### What the API does

The API handler has zero agent review or archive logic. After deployment (Phase 4 in `_run_auto_configure()`), it jumps straight to verification (Phase 5). No existing agents are examined.

### Existing infrastructure that can be reused

**`AgentReviewService`** (`src/claude_mpm/services/agents/agent_review_service.py`, 281 lines):
- No constructor dependencies -- `AgentReviewService()` takes no arguments
- `review_project_agents(project_path, recommended_agent_ids)` returns a dict with categorized agents
- `archive_agents(agents_to_archive, project_agents_dir)` moves files to `unused/` subdirectory
- Fully independent service, safe to import from the API layer

**`DeploymentVerifier`** (`src/claude_mpm/services/config_api/deployment_verifier.py`, line 160):
- Has `verify_agent_undeployed()` method that checks an agent file no longer exists in the agents directory
- Could be adapted for archive verification (checking file exists in `unused/` instead)

## Target State

The auto-configure flow gains an archiving phase:

```
Phase 1: Detecting toolchain
Phase 2: Recommending agents
Phase 2.5: Reviewing existing agents (NEW -- identifies would_archive)
Phase 3: Validating + Backup
Phase 4: Deploying agents
Phase 4.5: Deploying skills (from Phase 2)
Phase 5: Archiving unused agents (NEW -- moves to unused/)
Phase 6: Verifying deployments
Phase 7: Emitting completion event (with archived_agents data)
```

The preview endpoint includes `would_archive` in its response so users see which agents will be archived BEFORE typing "apply".

## Implementation Steps

### Step 1: Add lazy singleton for AgentReviewService

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

Add at the top of the file (near line 26):
```python
_agent_review_service = None
```

Add a new lazy initializer:
```python
def _get_agent_review_service():
    global _agent_review_service
    if _agent_review_service is None:
        from claude_mpm.services.agents.agent_review_service import (
            AgentReviewService,
        )
        _agent_review_service = AgentReviewService()
    return _agent_review_service
```

### Step 2: Add agent review to preview endpoint

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

In the `preview_configuration()` handler (around line 274-281), after getting the preview data and skill recommendations, add agent review:

```python
# After: data["skill_recommendations"] = skill_recs

# Add agent review for archive preview
def _review_agents():
    review_svc = _get_agent_review_service()
    return review_svc.review_project_agents(
        project_path=project_path,
        recommended_agent_ids=data.get("would_deploy", [])
    )

try:
    review = await asyncio.to_thread(_review_agents)
    unused_agents = review.get("unused", [])
    data["would_archive"] = [
        a.get("name", a.get("agent_id", "unknown"))
        for a in unused_agents
    ]
except Exception as e:
    logger.warning("Agent review failed during preview: %s", e)
    data["would_archive"] = []
```

### Step 3: Add archiving phase to `_run_auto_configure()`

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

Update `total_phases` to account for the new archiving phase.

After skill deployment (Phase 4.5) and before verification (Phase 6), add the archiving phase:

```python
# Phase 5: Archiving unused agents
await _emit_progress(
    handler, job_id, "archiving_agents",
    5, total_phases,  # Adjust phase number based on total
    message="Reviewing and archiving unused agents..."
)

archived_agents = []
archive_errors = []

def _review_and_archive():
    from claude_mpm.core.config_scope import ConfigScope, resolve_agents_dir

    review_svc = _get_agent_review_service()
    review = review_svc.review_project_agents(
        project_path=project_path,
        recommended_agent_ids=would_deploy
    )

    unused = review.get("unused", [])
    if not unused:
        return {"archived": [], "errors": []}

    agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_path)
    try:
        review_svc.archive_agents(unused, agents_dir)
        return {
            "archived": [
                a.get("name", a.get("agent_id", "unknown"))
                for a in unused
            ],
            "errors": []
        }
    except Exception as e:
        return {
            "archived": [],
            "errors": [str(e)]
        }

try:
    archive_result = await asyncio.to_thread(_review_and_archive)
    archived_agents = archive_result.get("archived", [])
    archive_errors = archive_result.get("errors", [])
except Exception as e:
    logger.warning("Auto-configure %s: agent archiving failed: %s", job_id, e)
    archive_errors = [str(e)]
```

### Step 4: Update completion event data

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

At the completion event (around line 544), add archive results:

```python
data={
    "job_id": job_id,
    "deployed_agents": deployed_agents,
    "failed_agents": failed_agents,
    "deployed_skills": deployed_skills,
    "skill_errors": skill_errors,
    "archived_agents": archived_agents,        # NEW
    "archive_errors": archive_errors,          # NEW
    "backup_id": backup_id,
    "duration_ms": duration_ms,
    "verification": verification,
    "needs_restart": bool(deployed_agents or deployed_skills),
},
```

### Step 5: Update logging

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

Update the completion log message to include archive results:

```python
logger.info(
    "Auto-configure %s completed: %d agents deployed, %d failed, "
    "%d skills deployed, %d archived (%dms)",
    job_id,
    len(deployed_agents), len(failed_agents),
    len(deployed_skills), len(archived_agents),
    duration_ms,
)
```

## Devil's Advocate Analysis

### "CLI archiving is interactive (prompts user) -- API cannot prompt. How to handle confirmation?"

The CLI's interactivity is in the TUI layer (`auto_configure.py` lines 368-377), not in `AgentReviewService` itself. The service's `archive_agents()` method takes a list of agents and archives them without prompting. The API can call it directly.

**The confirmation happens BEFORE apply, not during:** The preview endpoint returns `would_archive`, and the dashboard displays this in Step 2 (review & apply). The user sees "2 agents will be archived" and must type "apply" to confirm. This is equivalent to the CLI's interactive confirmation -- the mechanism is different (UI preview vs. terminal prompt) but the user still explicitly opts in.

### "Should auto-configure archive without asking?"

No. The preview must show `would_archive` data, and the dashboard must display it. The user's act of typing "apply" in the dashboard is the confirmation. If we wanted an opt-out, we could add `archive_agents: boolean` to the apply request body (default `true`), but this is a nice-to-have, not a blocker.

### "What if AgentReviewService categorizes a user's custom agent as 'unused'?"

`AgentReviewService.review_project_agents()` categorizes agents as "unused" if they are NOT in the recommended agent list. A user's custom agent (one they created manually, not via claude-mpm) would be categorized as "custom", NOT "unused", because the service distinguishes between managed and custom agents.

**Verification needed:** Confirm that the service's categorization logic correctly identifies custom agents. If a custom agent happens to have the same name format as a managed agent, it might be miscategorized.

### "What if archiving fails mid-operation (some agents archived, some not)?"

The `archive_agents()` method processes agents sequentially. If it fails on the third agent, the first two are already in `unused/`. This is acceptable because:
1. The backup was created before any deployment (Phase 3)
2. Archived agents can be manually moved back from `unused/`
3. The completion event reports `archive_errors` so the user knows what happened

### "The archive directory (.claude/agents/unused/) might not exist"

`archive_agents()` creates the `unused/` directory if it does not exist (`mkdir(parents=True, exist_ok=True)`). No pre-creation step is needed.

### "Review runs twice -- once in preview, once in apply. Is this wasteful?"

Yes, there is duplication. The preview call reviews agents to populate `would_archive`, and the apply call reviews again to get the list for archiving. Two mitigations:
1. The review operation is fast (scanning a directory and comparing filenames), so the overhead is minimal
2. The review must be fresh at apply time because the state might have changed between preview and apply (user might have manually added/removed agents)

Running it twice is the correct approach. Do NOT cache the preview result for use during apply.

### "What happens if the user runs auto-configure multiple times? Agents get archived repeatedly?"

On the second run, the agents that were archived in the first run are no longer in `.claude/agents/` (they are in `.claude/agents/unused/`), so `review_project_agents()` will not see them. They cannot be double-archived.

New agents deployed in the first run would be in the recommended set for the second run (assuming the same project config), so they would NOT be categorized as unused.

## Acceptance Criteria

1. API preview endpoint returns `would_archive` field with a list of agent names that would be archived
2. API apply endpoint moves unused agents to `.claude/agents/unused/` directory
3. Socket.IO `autoconfig_progress` event includes an `"archiving_agents"` phase
4. Socket.IO `autoconfig_completed` event includes `archived_agents` and `archive_errors` fields
5. Archived agent files exist in `<project_path>/.claude/agents/unused/` after apply
6. Custom agents (not managed by claude-mpm) are NOT archived
7. Archive failures are captured in `archive_errors` and do not crash the overall auto-configure
8. The `AgentReviewService` singleton is lazy-initialized

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Custom agents miscategorized as unused | Verify `AgentReviewService` categorization logic in unit tests |
| User surprised by archiving | Preview MUST show `would_archive`; dashboard MUST display it (Phase 4) |
| Partial archive failure | Report errors in completion event; backup exists for recovery |
| Archive directory creation fails | `mkdir(parents=True, exist_ok=True)` handles this |

## Estimated Effort

**S-M (2-3 hours)**

- 20 minutes to add lazy singleton and verify `AgentReviewService` interface
- 45 minutes to add review to preview endpoint
- 45 minutes to add archiving phase to `_run_auto_configure()`
- 30 minutes to update completion events and logging
- 30 minutes to write unit tests
- Buffer for categorization edge cases
