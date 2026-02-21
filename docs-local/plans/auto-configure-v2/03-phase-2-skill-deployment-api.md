# Phase 2: Wire Skill Deployment into API Auto-Configure

## Objective

Close the skill deployment gap in the API auto-configure path. Currently, the API handler hardcodes `deployed_skills: []` at lines 430 and 548 of `autoconfig_handler.py`. After this phase, the API will recommend skills based on deployed agents (using the same `AGENT_SKILL_MAPPING` as the CLI), deploy them via `SkillsDeployerService`, and return real deployment results.

## Prerequisites

- **Phase 0 (Scope Abstraction)** must be complete. The skill deployment code will use `resolve_skills_dir()` from `core/config_scope.py` for path resolution, even though skills are currently always user-scoped.

## Scope

**IN SCOPE:**
- Adding skill recommendation logic to the API auto-configure flow
- Deploying recommended skills via `SkillsDeployerService`
- Adding a "deploying_skills" phase to Socket.IO progress events
- Updating completion event data with real `deployed_skills` and `skill_errors`
- Adding `skill_recommendations` to the preview endpoint response
- Adding a lazy singleton for `SkillsDeployerService` in the handler

**NOT IN SCOPE:**
- Using `SkillRecommendationEngine` (tech-stack matching) -- future enhancement
- Adding project-scoped skill deployment -- skills are always user-scoped for now
- Modifying `skill_deployment_handler.py` -- its individual deploy routes are separate
- Dashboard UI changes -- those are in Phase 4

## Current State

### What the CLI does

**File:** `src/claude_mpm/cli/commands/auto_configure.py`

**Step 1: Recommend skills (lines 875-898)**
```python
def _recommend_skills(self, agent_preview):
    from claude_mpm.cli.interactive.skills_wizard import get_skills_for_agent

    recommended_skills = set()
    for rec in agent_preview.recommendations:
        agent_skills = get_skills_for_agent(rec.agent_id)
        recommended_skills.update(agent_skills)

    return list(recommended_skills) if recommended_skills else None
```

This uses `AGENT_SKILL_MAPPING` from `skills_wizard.py` (line 52) which maps agent types to skill sets. For example, `"engineer"` maps to `ENGINEER_CORE_SKILLS`, `"python-engineer"` maps to `PYTHON_SKILLS`.

**Step 2: Deploy skills (lines 900-915)**
```python
def _deploy_skills(self, recommended_skills):
    return self.skills_deployer.deploy_skills(
        skill_names=recommended_skills, force=False
    )
```

This calls `SkillsDeployerService.deploy_skills()` which deploys to `~/.claude/skills/`.

### What the API does

**File:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

The completion events at lines 430 and 548 both return:
```python
"deployed_skills": [],  # Always empty
```

There is no code path that calls `SkillsDeployerService` or maps agents to skills.

### Existing infrastructure that can be reused

1. **`SkillsDeployerService`** (`src/claude_mpm/services/skills_deployer.py`) -- Already handles multi-skill deployment with error collection. Its `deploy_skills(skill_names, force)` method returns `{"deployed": [...], "errors": [...]}`.

2. **`get_skills_for_agent()`** (`src/claude_mpm/cli/interactive/skills_wizard.py`) -- Pure function that maps agent IDs to skill names via `AGENT_SKILL_MAPPING`. No side effects, safe to import from the API layer.

3. **`skill_deployment_handler.py`** (`src/claude_mpm/services/config_api/skill_deployment_handler.py`) -- Has patterns for backup-before-deploy, operation journal, async wrapping, and Socket.IO events. These patterns should be followed but the handler itself does not need modification.

## Target State

The `_run_auto_configure()` function in `autoconfig_handler.py` gains a new phase (Phase 4.5: Skill Deployment) between agent deployment (Phase 4) and verification (Phase 5). The flow becomes:

```
Phase 1: Detecting toolchain
Phase 2: Recommending agents
Phase 3: Validating + Backup
Phase 4: Deploying agents
Phase 4.5: Recommending and deploying skills (NEW)
Phase 5: Verifying deployments
Phase 6: Emitting completion event (with real deployed_skills data)
```

The preview endpoint also gains a `skill_recommendations` field in its response.

## Implementation Steps

### Step 1: Add lazy singleton for SkillsDeployerService

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

Add at the top of the file (near line 26, after the existing `_backup_manager` declaration):
```python
_skills_deployer = None
```

Add a new lazy initializer function (after `_get_backup_manager()`):
```python
def _get_skills_deployer():
    global _skills_deployer
    if _skills_deployer is None:
        from claude_mpm.services.skills_deployer import SkillsDeployerService
        _skills_deployer = SkillsDeployerService()
    return _skills_deployer
```

### Step 2: Add skill recommendation to preview endpoint

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

In the `preview_configuration()` handler (around line 274-281), after getting the preview data, add skill recommendation:

```python
# After: data = _preview_to_dict(preview)

# Add skill recommendations
def _recommend_skills():
    from claude_mpm.cli.interactive.skills_wizard import get_skills_for_agent
    recommended = set()
    for rec in preview.recommendations:
        agent_skills = get_skills_for_agent(rec.agent_id)
        recommended.update(agent_skills)
    return list(recommended)

skill_recs = await asyncio.to_thread(_recommend_skills)
data["skill_recommendations"] = skill_recs
data["would_deploy_skills"] = skill_recs
```

### Step 3: Add skill deployment phase to `_run_auto_configure()`

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

Update the `total_phases` variable (currently 5) to 6 to account for the new skill phase.

After the agent deployment loop (after line 509, before Phase 5: Verifying), insert the skill deployment phase:

```python
# Phase 4.5: Skill Deployment
await _emit_progress(
    handler, job_id, "deploying_skills",
    5, total_phases,
    message="Recommending and deploying skills..."
)

deployed_skills = []
skill_errors = []

def _recommend_and_deploy_skills():
    from claude_mpm.cli.interactive.skills_wizard import get_skills_for_agent

    recommended_skills = set()
    for agent_id in would_deploy:
        agent_skills = get_skills_for_agent(agent_id)
        recommended_skills.update(agent_skills)

    if not recommended_skills:
        return {"deployed": [], "errors": []}

    svc = _get_skills_deployer()
    return svc.deploy_skills(skill_names=list(recommended_skills), force=False)

try:
    skills_result = await asyncio.to_thread(_recommend_and_deploy_skills)
    deployed_skills = skills_result.get("deployed", [])
    skill_errors = skills_result.get("errors", [])
except Exception as e:
    logger.warning("Auto-configure %s: skill deployment failed: %s", job_id, e)
    skill_errors = [str(e)]
```

### Step 4: Update completion event data

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

At lines 544-552 (the completion event), replace `"deployed_skills": []` with the real data:

```python
data={
    "job_id": job_id,
    "deployed_agents": deployed_agents,
    "failed_agents": failed_agents,
    "deployed_skills": deployed_skills,      # Was: []
    "skill_errors": skill_errors,            # NEW
    "backup_id": backup_id,
    "duration_ms": duration_ms,
    "verification": verification,
    "needs_restart": bool(deployed_agents or deployed_skills),  # NEW
},
```

Also update the early-exit completion event at lines 426-435 to include `skill_errors: []`.

### Step 5: Update the phase numbering

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

The verification phase (currently Phase 5) becomes Phase 6. Update the `_emit_progress` call for verifying to use the new phase number.

### Step 6: Determine overall success including skills

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

After the completion event, the log message at line 556 should reflect skill results:

```python
logger.info(
    "Auto-configure %s completed: %d agents deployed, %d failed, "
    "%d skills deployed, %d skill errors (%dms)",
    job_id,
    len(deployed_agents), len(failed_agents),
    len(deployed_skills), len(skill_errors),
    duration_ms,
)
```

## Devil's Advocate Analysis

### "Skill deployment is currently always user-scoped -- adding it to project-based auto-configure means one project's auto-configure affects ALL projects"

This is correct and is the existing behavior in the CLI path. Skills deploy to `~/.claude/skills/` because Claude Code loads skills from the user home directory at startup. There is no project-scoped skill deployment in Claude Code.

**The API should match CLI behavior for consistency.** The dashboard UI (Phase 4) should clearly communicate: "Skills will be deployed to ~/.claude/skills/ and will be available in all projects."

If this is considered unacceptable, the alternative is to skip skill deployment entirely in the API path and only show recommendations. But that creates a worse parity gap.

### "Using AGENT_SKILL_MAPPING from skills_wizard.py creates an import from cli/ into services/"

The `skills_wizard.py` file lives in `cli/interactive/`, which is technically a CLI-layer module. Importing from it into `services/config_api/` crosses a layer boundary.

**Mitigations:**
1. The import is a lazy import (inside a function), not a top-level import
2. `get_skills_for_agent()` is a pure function with no side effects or UI dependencies
3. A cleaner long-term solution is to move `AGENT_SKILL_MAPPING` to a shared location (e.g., `services/skills/agent_skill_mapping.py`), but that is a refactoring task outside this phase's scope

### "What if SkillsDeployerService fails mid-deployment (some skills deployed, some not)?"

`SkillsDeployerService.deploy_skills()` already handles partial failures. It returns `{"deployed": [...], "errors": [...]}` with separate lists for successes and failures. The API handler captures both and includes them in the completion event.

The `overall_success` determination should consider skill errors:
```python
overall_success = (len(failed_agents) == 0) and (len(skill_errors) == 0)
```

### "Could concurrent auto-configure runs deploy conflicting skills?"

Yes. If two projects trigger auto-configure simultaneously, both might try to deploy skills to `~/.claude/skills/`. The `SkillsDeployerService` already handles this at the individual skill level (if a skill already exists and `force=False`, it skips it). The risk is low but not zero.

**Mitigation:** The existing `_active_jobs` dict in `autoconfig_handler.py` tracks in-flight jobs but does not prevent concurrent runs. A module-level guard should be added (see research doc Section 8.2). This can be done in this phase or as a separate quick fix.

### "Why not use SkillRecommendationEngine instead of AGENT_SKILL_MAPPING?"

`SkillRecommendationEngine` uses technology-stack-based matching (language, framework, database weights) which is more sophisticated than the agent-to-skill mapping. However:
- It may recommend DIFFERENT skills than the CLI path, breaking parity
- The CLI uses `AGENT_SKILL_MAPPING`, so the API should too
- `SkillRecommendationEngine` can be added as an optional enhancement later
- Consistency between CLI and API is more important than sophistication

### "The skills_wizard import may fail if skills_wizard has heavy dependencies"

The `skills_wizard.py` module imports `questionary` (a terminal UI library) at the top level. However, `get_skills_for_agent()` does not USE questionary -- it only accesses the `AGENT_SKILL_MAPPING` dictionary. The import should succeed even in a headless API context.

**Verification needed:** Check if `skills_wizard.py` has any top-level code that executes on import and might fail without a terminal. If so, the `AGENT_SKILL_MAPPING` dictionary should be extracted to a standalone module.

## Acceptance Criteria

1. API preview endpoint returns `skill_recommendations` and `would_deploy_skills` fields with non-empty data for a project with detected agents
2. API apply endpoint deploys skills to `~/.claude/skills/` and returns real `deployed_skills` data (not empty array)
3. Socket.IO `autoconfig_progress` event includes a `"deploying_skills"` phase
4. Socket.IO `autoconfig_completed` event includes `deployed_skills`, `skill_errors`, and `needs_restart` fields
5. Skill deployment failures are captured in `skill_errors` and do not crash the overall auto-configure
6. Given the same project and min_confidence, the API and CLI recommend identical skills
7. The `SkillsDeployerService` singleton is lazy-initialized (not created at module load)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| `skills_wizard.py` import fails in headless context | Verify import works; extract `AGENT_SKILL_MAPPING` if needed |
| Concurrent skill deployments | Add module-level job guard (recommended in research doc) |
| Skill deployment takes long (GitHub downloads) | Emit per-skill progress events; set reasonable timeout |
| User-scoped skills affect other projects | Match CLI behavior; document in UI messaging (Phase 4) |

## Estimated Effort

**M (2-4 hours)**

- 30 minutes to add lazy singleton and import verification
- 45 minutes to implement skill recommendation in preview endpoint
- 45 minutes to implement skill deployment phase in `_run_auto_configure()`
- 30 minutes to update completion events and phase numbering
- 30 minutes to write unit tests for the new code paths
- Buffer for import issues or unexpected `skills_wizard.py` dependencies
