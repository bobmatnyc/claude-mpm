# Auto-Configure v2: Feature Parity and Scope Abstraction

## Executive Summary

The auto-configure feature has two execution paths -- CLI (`auto_configure.py`) and API (`autoconfig_handler.py`). Both share core detection and recommendation services, but the API path has three feature parity gaps compared to the CLI:

1. **min_confidence default mismatch** -- API uses `0.8`, CLI uses `0.5` (missed in commit `62ba0f42`)
2. **Skill deployment absent from API** -- hardcoded `deployed_skills: []` at lines 430 and 548
3. **No restart notification in dashboard** -- no equivalent of CLI's `_show_restart_notification()`

This initiative closes all three gaps across five phases, starting with a scope abstraction foundation that eliminates hardcoded paths and enables future extensibility.

> **Note:** Phase 3 (Agent Archiving API) was evaluated and deliberately excluded from this plan. It introduces unwanted complexity and risks to the auto-configure flow. Agent archiving can be revisited as a standalone feature in the future.

---

## Phase Dependency Diagram

```
Phase 0: Scope Abstraction (Foundation)
    |
    +----> Phase 1: min_confidence Fix (Independent, quick win)
    |
    +----> Phase 2: Skill Deployment API
    |          |
    |          +----> Phase 4: UI Messaging (depends on 2)
    |
    +-------------------------------------------> Phase 5: Testing (depends on all)
```

**Critical path:** Phase 0 -> Phase 2 -> Phase 4 -> Phase 5

Phase 1 can be done at any time (no dependencies, 5-minute fix).
Phase 4 requires Phase 2 to be complete.
Phase 5 runs after all implementation phases.

---

## Phase Summary

| Phase | Title | Effort | Risk | Dependencies |
|-------|-------|--------|------|--------------|
| 0 | Scope Abstraction | S (1-2 hrs) | None (additive) | None |
| 1 | min_confidence Fix | XS (5 min) | None | None |
| 2 | Skill Deployment API | M (2-4 hrs) | Low-Medium | Phase 0 |
| 4 | UI Messaging | M (2-4 hrs) | Low (frontend) | Phase 2 |
| 5 | Testing | S-M (2-3 hrs) | None | Phases 0-2, 4 |

**Total estimated effort:** ~10-16 hours (roughly 2 development days)

---

## Risk Summary

| Risk | Severity | Phase | Mitigation |
|------|----------|-------|------------|
| Skill deployment is user-scoped; concurrent projects could conflict | Medium | 2 | Match existing CLI behavior; document scope in UI |
| Race condition on concurrent auto-configure runs | Low | 2 | Add module-level job guard (already has `_active_jobs` dict) |
| Skill deployment failures silently swallowed | Medium | 2 | Include `skill_errors` in completion event; check `overall_success` |
| Regression in CLI scope handling from new enum | Low | 0 | `ConfigScope(str, Enum)` ensures backward compatibility |
| Dashboard pipeline progress is simulated, not real | Low | 4 | Wire Socket.IO events; degrade gracefully if backend slow |

---

## Success Criteria

The initiative is complete when ALL of the following hold:

1. `ConfigScope` enum and resolver functions exist in `core/config_scope.py` and are used by API handlers
2. API preview endpoint returns the same number of recommendations as CLI for the same project and confidence
3. `POST /api/config/auto-configure/apply` deploys skills to `~/.claude/skills/` and returns non-empty `deployed_skills`
4. Dashboard `AutoConfigPreview.svelte` displays skill recommendations and restart warning
5. All existing CLI tests pass without modification (no regression)
6. New unit tests cover `ConfigScope`, API skill deployment, and min_confidence default
7. E2E test verifies full API auto-configure flow: detect -> preview -> apply -> verify files on disk

---

## Key Files (Reference Index)

| File | Role |
|------|------|
| `src/claude_mpm/services/config_api/autoconfig_handler.py` (581 lines) | API auto-configure handler -- PRIMARY modification target |
| `src/claude_mpm/cli/commands/auto_configure.py` (1052 lines) | CLI auto-configure -- REFERENCE implementation |
| `src/claude_mpm/cli/commands/configure_paths.py` (104 lines) | Existing scope-based path resolver (MPM dirs only) |
| `src/claude_mpm/services/skills_deployer.py` (1220 lines) | `SkillsDeployerService` -- deploys to `~/.claude/skills/` |
| `src/claude_mpm/services/config_api/skill_deployment_handler.py` (587 lines) | Individual skill deploy/undeploy API routes |
| `src/claude_mpm/services/config_api/deployment_verifier.py` (375 lines) | Post-deployment verification |
| `src/claude_mpm/cli/interactive/skills_wizard.py` (~200 lines) | `AGENT_SKILL_MAPPING` definition |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/AutoConfigPreview.svelte` (339 lines) | Dashboard auto-configure modal |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` (~800 lines) | Dashboard config store |

---

## Research References

- `docs/research/auto-configure-backend-implementation-analysis-v2.md` -- Primary research document
- `docs/research/scope-abstraction-existing-code-analysis-2026-02-17.md` -- Supplementary scope analysis
