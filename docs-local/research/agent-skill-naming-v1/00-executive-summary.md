# Executive Summary: Agent Naming Inconsistency Investigation

**Date**: 2026-02-19
**Status**: Investigation Complete
**Severity**: Medium (UX confusion, broken feature flags)
**Affects**: Dashboard Config tab - Agents sub-tab

---

## Problem Statement

The Dashboard Config tab displays deployed and available agents with **inconsistent naming conventions**, causing users to perceive two different agents where only one exists:

- **Deployed agents** appear as: `svelte-engineer`, `python-engineer` (kebab-case file stems)
- **Available agents** appear as: `Svelte Engineer`, `Python Engineer` (human-readable display names)

This naming mismatch also **breaks the `is_deployed` flag** on available agents, meaning agents that are actually deployed still show a "Deploy" button in the Available section.

## Root Cause

The root cause is a **data structure mismatch between the two API endpoints** combined with **incorrect field selection** in the comparison logic:

1. **`/api/config/agents/deployed`** returns agent names derived from **filesystem stems** (e.g., `svelte-engineer.md` -> `"svelte-engineer"`)
2. **`/api/config/agents/available`** promotes `metadata.name` (human-readable, e.g., `"Svelte Engineer"`) as the root-level `name` field
3. **The `is_deployed` comparison** in `config_routes.py:391` compares the human-readable `name` against file stems, which **never matches**

## Impact

| Area | Impact |
|------|--------|
| **User confusion** | Same agent appears to be two different agents in Deployed vs Available lists |
| **is_deployed flag** | Always `false` for available agents, even when deployed |
| **Version comparison** | Frontend `outdatedCount` never finds matching deployed/available pairs |
| **Deploy button** | Shows "Deploy" for already-deployed agents (since is_deployed is false) |

## Recommended Solution

**Option A: Normalize at the API level** (Recommended)

In `handle_agents_available()`, use `agent_id` as the primary identifier and add a separate `display_name` field:

```python
# config_routes.py, line ~370
agent["display_name"] = metadata.get("name", agent.get("agent_id", ""))
agent.setdefault("name", agent.get("agent_id", metadata.get("name", "")))
```

Additionally, fix the `is_deployed` comparison to use `agent_id`:

```python
# config_routes.py, line ~391
agent_id = agent.get("agent_id", agent.get("name", ""))
agent["is_deployed"] = agent_id in deployed_names
```

Update the frontend `AvailableAgent` interface to include `display_name` and use it for rendering while using `name`/`agent_id` for matching.

**Estimated effort**: ~2-4 hours (backend + frontend + tests)

## Files Requiring Changes

| File | Change |
|------|--------|
| `src/claude_mpm/services/monitor/config_routes.py` | Fix name promotion and is_deployed comparison |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | Add `display_name` to `AvailableAgent` interface |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte` | Use `display_name` for rendering, `name` for matching |
| `tests/test_config_routes.py` | Update tests for new field behavior |

## Document Index

| Document | Description |
|----------|-------------|
| [01-problem-analysis.md](./01-problem-analysis.md) | Detailed problem breakdown with data flow diagrams |
| [02-backend-investigation.md](./02-backend-investigation.md) | API endpoint analysis and backend code findings |
| [03-frontend-investigation.md](./03-frontend-investigation.md) | UI display logic and component analysis |
| [04-alternative-theories.md](./04-alternative-theories.md) | Devil's advocate analysis of alternative causes |
| [05-verification-results.md](./05-verification-results.md) | End-to-end testing and edge case findings |
| [06-solution-proposals.md](./06-solution-proposals.md) | Detailed solution options with implementation guide |
