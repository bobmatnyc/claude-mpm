# Investigation: 811 False-Positive Skill Warnings

**Date:** 2026-02-13
**Status:** Root causes identified, fix partially in place

## Summary

The UI shows 811 cross-reference warnings ("Agent X references skill Y which is not deployed"). A suffix-matching fix was committed (`ed0b4303`) but the warnings persist due to two root causes:

1. **The running server was not restarted** after the fix was committed
2. **The fix only resolves 646 of 811 warnings** -- 165 warnings are genuine (79 skills truly not deployed)
3. **A second code path** (`skill_link_handler.py`) also performs deployment checks without suffix matching

## Root Cause Analysis

### Root Cause 1: Server Not Restarted (PRIMARY)

- **Server process** PID 73278 started at **18:24:48** on Feb 13
- **Fix commit** `ed0b4303` created at **19:31:22** on Feb 13
- The server is running old code that uses simple `skill_name not in deployed_skill_names` without suffix matching
- This accounts for ALL 811 warnings showing in the dashboard

**Fix:** Restart the server: `claude-mpm monitor restart`

### Root Cause 2: Fix Only Covers 646 of 811 Warnings

The `_skill_name_matches_deployed()` method uses segment-suffix matching:
- `"software-patterns"` matches `"universal-architecture-software-patterns"` (suffix `-software-patterns`)
- This resolves **646 warnings** where short agent names match long deployed directory names

But **165 warnings remain** for **79 unique skills** that are genuinely NOT deployed:

| Category | Examples | Count |
|----------|----------|-------|
| UI frameworks | daisyui, headlessui, shadcn-ui, tailwind | ~10 |
| JS frameworks | react, nextjs, nextjs-core, nextjs-v16, vue, svelte, sveltekit | ~20 |
| ORMs/DB | drizzle-orm, prisma-orm, kysely, sqlalchemy, neon, supabase | ~15 |
| Testing | jest-typescript, pytest, vitest | ~5 |
| Python tools | asyncio, celery, django, flask, pydantic, mypy, pyright | ~15 |
| Build tools | vite, turborepo, biome | ~5 |
| Other | graphql, trpc, zod, zustand, tanstack-query, etc. | ~9 |

These are skills referenced in agent frontmatter but never deployed to `~/.claude/skills/`.

### Root Cause 3: Second Validation Path in skill_link_handler.py

`/Users/mac/workspace/claude-mpm-fork/src/claude_mpm/services/monitor/handlers/skill_link_handler.py` also checks `is_deployed` using direct set membership (line 159):

```python
"is_deployed": skill_name in self._deployed_skill_names,
```

This does NOT use suffix matching. The `by_skill` mapping in the `/api/config/skill-links/` response marks skills as not deployed using simple name equality.

However, this is partially masked in the Svelte frontend: `skillLinks.svelte.ts` line 84 **hardcodes `is_deployed: true`** for all skills in the store transformation, ignoring the backend's actual `is_deployed` field from `by_skill`.

## Pipeline Trace

```
Dashboard ValidationPanel.svelte
    |
    v
GET /api/config/validate  (config_routes.py:586)
    |
    v
ConfigValidationService.validate_cached()  (60s TTL cache)
    |
    v
_validate_cross_references()
    |
    +-- Gets deployed skills from SkillsDeployerService.check_deployed_skills()
    |   Returns: directory names from ~/.claude/skills/ (e.g., "universal-architecture-software-patterns")
    |
    +-- Gets agent skills from frontmatter + content markers
    |   Returns: short names (e.g., "software-patterns", "daisyui")
    |
    +-- NEW: _skill_name_matches_deployed() with suffix matching
    |   (But running server has OLD code: simple `not in` check)
    |
    v
Returns 811 ValidationIssue objects with severity="warning"
```

## Deployed Skills vs Referenced Skills

**Deployed (60 directories in ~/.claude/skills/):**
- Long names like `toolchains-ai-frameworks-langgraph`, `universal-architecture-software-patterns`

**Referenced by agents (116 unique names):**
- Short names like `langgraph`, `software-patterns`, `daisyui`

**After fix is active:**
- 37 skills matched by exact name (e.g., `mpm`, `mpm-config`)
- 646 checks resolved by suffix matching (e.g., `software-patterns` -> `universal-architecture-software-patterns`)
- 165 checks remain as genuine warnings (79 unique skills not deployed anywhere)

## Specific Skill Lookups

| Referenced Name | Deployed Directory | Match After Fix? |
|----------------|-------------------|-----------------|
| `daisyui` | (none) | NO - not deployed |
| `sveltekit` | (none) | NO - not deployed |
| `software-patterns` | `universal-architecture-software-patterns` | YES - suffix match |

## Fix Actions Required

### Immediate: Restart the server
```bash
claude-mpm monitor restart
# or
kill 73278 && claude-mpm monitor start --background --port 8765 --host localhost
```
This will reduce warnings from 811 to 165.

### Short-term: Apply suffix matching to skill_link_handler.py
The `SkillToAgentMapper._load_deployed_skills()` method stores raw directory names, but `is_deployed` checks use simple `in` membership. Need to add the same suffix-matching logic or share a common utility.

**File:** `/Users/mac/workspace/claude-mpm-fork/src/claude_mpm/services/monitor/handlers/skill_link_handler.py`
**Lines:** 159, 201

### Medium-term: Address the 165 genuine warnings
Options:
1. Deploy the missing 79 skills
2. Change severity from "warning" to "info" for cross-reference mismatches
3. Add a "suppress" mechanism for known undeployed skills
4. Only warn for skills in `required` lists, not `optional`

### Fix the Svelte store hardcoding
**File:** `skillLinks.svelte.ts` lines 84, 95
Currently hardcodes `is_deployed: true` for all skills. Should use the `by_skill` response data to get actual deployment status.

## Files Involved

| File | Role | Has Fix? |
|------|------|----------|
| `config_validation_service.py` | Validation endpoint logic | YES (suffix matching) |
| `skill_link_handler.py` | Skill-agent linking | NO (simple `in` check) |
| `skills_deployer.py` | `check_deployed_skills()` returns dir names | N/A (data source) |
| `config_routes.py` | API endpoint handler | OK (delegates correctly) |
| `skillLinks.svelte.ts` | Frontend store | BUG (hardcodes is_deployed) |
| `AgentSkillPanel.svelte` | UI component | OK (uses store data) |
| `SkillChipList.svelte` | UI component | OK (uses store data) |
| `ValidationPanel.svelte` | Validation display | OK (uses API data) |
