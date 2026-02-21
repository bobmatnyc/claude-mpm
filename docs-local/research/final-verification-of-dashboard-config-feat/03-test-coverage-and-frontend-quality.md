# Test Coverage and Frontend Quality Analysis

**Branch:** `ui-agents-skills-config`
**Date:** 2025-02-19
**Analyst:** Claude Opus 4.6 (Research Agent)

---

## Executive Summary

The `ui-agents-skills-config` branch introduces a comprehensive configuration management system spanning **72 new/modified source files** and **20 new/modified test files** across Python backend services, Svelte 5 frontend components, and integration layers. Test quality is generally **strong**, with proper mocking patterns, realistic fixtures, and edge case coverage. The frontend architecture is well-structured with appropriate use of Svelte 5 runes in components and a pragmatic hybrid approach for stores. However, there are several notable gaps: the frontend Svelte components have **no automated test coverage** beyond a single SkillChip.test.ts, the config store's 981-line monolith should be split, and the skillLinks store uses `is_deployed: true` as a hardcoded assumption. Six issues are rated HIGH severity, requiring attention before merge.

---

## Part 1: Test Coverage Matrix

### Source File to Test File Mapping

| Source File | Test File(s) | Coverage |
|---|---|---|
| `src/claude_mpm/core/config_scope.py` | `tests/core/test_config_scope.py` | STRONG - All 4 resolve functions tested for both scopes, backward compat, isolation, real FS |
| `src/claude_mpm/core/config_file_lock.py` | `tests/unit/core/test_config_file_lock.py` | STRONG - Acquire/release, concurrency, timeout, exception safety, PID, mtime, 10-thread contention |
| `src/claude_mpm/services/agents/auto_config_manager.py` | `tests/services/agents/test_auto_config_manager.py` (1-line change) | ADEQUATE - Only modified file; minimal change, existing tests sufficient |
| `src/claude_mpm/services/agents/management/agent_management_service.py` | `tests/test_phase2_agent_manager.py` | GOOD - list_agent_names stems, empty dir, non-.md files, nonexistent dir; _extract_enrichment_fields full/partial/missing/malformed frontmatter |
| `src/claude_mpm/services/config/config_validation_service.py` | `tests/services/test_config_validation_service.py` | STRONG - Agent validation (valid, no frontmatter, invalid YAML, missing name, tiny content), source validation, env override masking, cross-references (short name suffix matching, no partial match), cache behavior |
| `src/claude_mpm/services/config_api/backup_manager.py` | `tests/test_backup_manager.py` | STRONG - Create (metadata, dirs copied), restore (success, nonexistent), list (sorted), prune (keeps 5, removes oldest, noop under limit) |
| `src/claude_mpm/services/config_api/deployment_verifier.py` | `tests/test_deployment_verifier.py` | STRONG - Agent deploy/undeploy, skill deploy/undeploy, mode switch, timestamps, missing files, missing frontmatter, missing fields, empty file |
| `src/claude_mpm/services/config_api/operation_journal.py` | `tests/test_operation_journal.py` | STRONG - Begin/complete/fail lifecycle, incomplete detection, rollback marking, file auto-creation, corrupt journal reset, concurrent operations, mixed statuses |
| `src/claude_mpm/services/config_api/agent_deployment_handler.py` | `tests/test_config_api_business_rules.py`, `tests/test_config_api_deployment.py` | GOOD - Core agent protection (BR-01, all 7 agents), immutable skill protection, user skill undeploy, mode business rules |
| `src/claude_mpm/services/config_api/skill_deployment_handler.py` | `tests/test_config_api_business_rules.py`, `tests/test_config_api_deployment.py` | GOOD - PM_CORE_SKILLS immutable, CORE_SKILLS immutable, user skill undeploy, empty list blocking, already-in-mode 409 |
| `src/claude_mpm/services/config_api/autoconfig_handler.py` | `tests/services/config_api/test_autoconfig_integration.py` | GOOD - Singleton creation, caching, failure non-caching, preview succeeds, reset |
| `src/claude_mpm/services/monitor/config_routes.py` | `tests/test_config_routes.py` | GOOD - Project summary (success, error, empty), deployed agents (success, error, empty), available agents (success, search, error, cache-control header) |
| `src/claude_mpm/services/monitor/routes/config_sources.py` | `tests/unit/services/monitor/routes/test_config_sources.py` | STRONG - 16 test cases: add agent/skill source (success, invalid URL, duplicate, priority range), no token in response, remove (success, not found, system protected), update priority, disable system blocked, sync (202, missing ID), sync-all, sync-status |
| `src/claude_mpm/services/monitor/handlers/skill_link_handler.py` | `tests/dashboard/test_config_skill_links.py` | GOOD - SkillToAgentMapper (empty, frontmatter, content markers, dict skills, bidirectional index, stats, cache), pagination, HTTP endpoints |
| `src/claude_mpm/services/config_api/validation.py` | `tests/dashboard/test_config_validate.py` | GOOD - Clean config, errors, issue format, service error 500, env override detection |
| `src/claude_mpm/cli/commands/auto_configure.py` | `tests/services/config_api/test_autoconfig_defaults.py`, `tests/services/config_api/test_autoconfig_skill_deployment.py`, `tests/e2e/test_autoconfig_full_flow.py` | STRONG - Defaults (0.5, explicit, boundary, None), async/sync boundary propagation, skill recommendation (valid, no agents, unmapped, dedup), deployment (success, partial, complete failure, force), full workflow (preview, JSON, confirmation, agents-only, skills-only, validation issues, deployment failures, lazy singletons, cross-scope) |
| Rollback integration | `tests/test_config_api_rollback.py` | STRONG - Deploy creates backup, failed deploy rollback, journal records, incomplete detection, pruning, mode switch rollback, multiple operations with rollback |
| Auto-configure events | `tests/services/config_api/test_autoconfig_events.py` | GOOD - Progress observer events, phase 0-4 events, payload validation (JSON serializable, required fields, type constraints), Socket.IO integration (full workflow sequence, error resilience) |

### Source Files WITHOUT Dedicated Tests

| Source File | Risk Level | Notes |
|---|---|---|
| `src/claude_mpm/services/config_api/session_detector.py` | MEDIUM | No dedicated test file. Sessions are used in frontend (checkActiveSessions) but backend detection logic untested. |
| `src/claude_mpm/services/monitor/handlers/config_handler.py` | LOW | Socket.IO event handler; tested indirectly via event integration tests |
| `src/claude_mpm/services/monitor/pagination.py` | LOW | Tested indirectly via skill_links pagination tests |
| `src/claude_mpm/services/monitor/server.py` | LOW | Server bootstrap; not directly testable in unit context |
| `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py` | MEDIUM | No dedicated test file visible for this service |
| `src/claude_mpm/services/skills_deployer.py` | LOW | Existing service; tested indirectly via deployment handler tests |
| `src/claude_mpm/config/agent_sources.py` | LOW | Tested indirectly via config_sources route tests |
| All Svelte components (47 files) | **HIGH** | Only `SkillChip.test.ts` exists. No tests for ConfigView, AgentsList, SkillsList, AgentDetailPanel, AutoConfigPreview, SourcesList, etc. |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | **HIGH** | 981-line store with 30+ functions. No unit tests for store logic, fetch error handling, cache eviction, or Socket.IO event processing. |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config/skillLinks.svelte.ts` | MEDIUM | No tests for backend-to-frontend data transformation logic |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/toast.svelte.ts` | LOW | Simple store; low risk |

---

## Part 2: Test Quality Assessment

### Strengths

1. **Consistent mocking patterns**: Tests uniformly use `MagicMock`, `AsyncMock`, `patch`, and `pytest.fixture` with proper cleanup. Singleton resets (`_reset_agent_singletons()`, `_reset_skill_singletons()`) prevent state leakage between tests.

2. **Realistic fixtures**: `backup_env`, `rollback_env`, and `realistic_project_structure` create proper directory structures with real YAML frontmatter, simulating production-like conditions.

3. **Edge case coverage**: Tests explicitly cover empty directories, missing files, corrupt YAML, nonexistent backup IDs, concurrent operations, falsy 0.0 confidence values, and partial deployment failures.

4. **Documented bugs**: `test_autoconfig_defaults.py` line 70-79 explicitly documents the 0.0 falsy bug with expected current behavior, creating a test-documented regression contract.

5. **Security testing**: Token masking in env var validation, no-token-in-response for skill sources, path traversal protection in agent/skill detail endpoints.

6. **Business rule enforcement**: BR-01 core agent protection tested for all 7 agents. PM_CORE_SKILLS and CORE_SKILLS immutability tested. Protected source deletion blocked.

7. **Async/sync boundary testing**: Explicit tests for `min_confidence` default propagation across `asyncio.run` boundaries and `asyncio.to_thread` patterns.

8. **Integration test markers**: `@pytest.mark.integration` properly separates integration tests from unit tests, allowing targeted test execution.

### Weaknesses

1. **Incomplete aiohttp test reading**: `test_config_routes.py` and `test_config_api_deployment.py` are large files (1100+ and 800+ lines respectively); only partial reads were performed. Full coverage of their endpoint tests cannot be verified at the same confidence level.

2. **No negative path tests for config store**: The 981-line config store has zero automated tests. Network errors, timeout scenarios, race conditions between Socket.IO events and REST fetches, and LRU cache eviction edge cases are all untested.

3. **Missing concurrent deployment tests**: While `test_config_file_lock.py` tests concurrent file access, there are no tests simulating concurrent deployment operations (e.g., two agents being deployed simultaneously through the API).

4. **No property-based testing**: For components like pagination, skill matching, and path resolution, property-based tests (using hypothesis) would catch edge cases that parametric tests miss.

5. **Hardcoded test data**: Some tests use hardcoded timestamps (e.g., `"2026-02-13T10:00:00+00:00"`) which, while functional, could be more robust with relative time generation.

---

## Part 3: Coverage Gaps Requiring Attention

### GAP-01: Frontend Component Testing (HIGH)

**47 Svelte components have zero automated tests** (except SkillChip.test.ts). Critical components lacking tests:

- **ConfigView.svelte**: Orchestrator for all config sub-components; manages panel selection, shared state, and sub-tab routing. A single integration test could catch regressions in the component wiring.
- **AgentsList.svelte**: Multi-field search, sort, category grouping, deploy/undeploy state tracking, force redeploy confirmation. Search and sort logic are good candidates for unit testing.
- **SkillsList.svelte**: Toolchain grouping, immutable skill detection, version comparison with `compareVersions`, outdated count derivation. Complex derived state logic.
- **AutoConfigPreview.svelte**: Two-step wizard (Detect+Recommend / Review+Apply), real-time pipeline progress via Socket.IO, confirmation typing gate. State machine behavior should be tested.
- **AgentDetailPanel.svelte**: Lazy-loaded detail fetching with cancellation (`cancelled` flag pattern), suffix-matching for skill deployment status, fallback to list data when 404.

**Recommendation**: Add at minimum a Vitest suite for the config store functions and for component-level logic (search, sort, filtering) extracted into testable utility modules.

### GAP-02: Config Store Monolith (HIGH)

The config store at **981 lines** contains:
- 20+ TypeScript interface definitions
- 10+ writable stores
- 15+ fetch functions
- 10+ mutation functions
- An auto-config event system
- A Socket.IO event handler with 14 operation types
- An LRU cache implementation

This is a "God Module" anti-pattern. Splitting it would:
- Enable focused unit testing of each concern
- Reduce cognitive load for maintainers
- Allow independent imports (tree shaking)

**Recommendation**: Split into `config-types.ts`, `config-stores.ts`, `config-fetchers.ts`, `config-mutations.ts`, `config-events.ts`, and `config-cache.ts`.

### GAP-03: Session Detector Untested (MEDIUM)

`session_detector.py` has no dedicated test file. The frontend calls `checkActiveSessions()` before and after deploy/undeploy operations. If session detection fails silently, users could modify configuration during active Claude Code sessions without proper warnings.

### GAP-04: SkillLinks Store Hardcoded `is_deployed: true` (MEDIUM)

In `skillLinks.svelte.ts` line 84 and 104, `is_deployed` is hardcoded to `true` for all skills in the transformation logic. The backend does not return deployment status per-skill in the skill-links response, so the frontend assumes all referenced skills are deployed. This is incorrect -- the whole point of cross-reference validation is to detect undeployed skills.

### GAP-05: 0.0 min_confidence Falsy Bug (MEDIUM)

Documented in `test_autoconfig_defaults.py` line 70-79: `0.0` is treated as falsy and defaults to `0.5`. While the bug is documented in tests, it remains in production code. A user explicitly requesting `--min-confidence 0.0` (accept all recommendations) would get 0.5 instead.

### GAP-06: No Error Boundary in AutoConfigPreview (LOW)

`AutoConfigPreview.svelte` has try/catch in `handleApply()` but if the `waitForAutoConfigCompletion` promise rejects with a non-Error object, the `e.message` access could fail silently. The catch block should handle arbitrary rejection values.

---

## Part 4: Frontend Architecture Review

### Store Design Evaluation

| Store | Size | Pattern | Assessment |
|---|---|---|---|
| `config.svelte.ts` | 981 lines | Svelte 4 `writable()` stores | **NEEDS REFACTORING** - Monolith with types, stores, fetchers, mutations, events, cache all in one file. Uses Svelte 4 pattern (writable stores) despite being in a Svelte 5 project. Functional but not idiomatic. |
| `skillLinks.svelte.ts` | 135 lines | Svelte 4 `writable()` store | **ADEQUATE** - Focused single concern. Has backend-to-frontend data transformation. Hardcoded `is_deployed: true` is a logic bug. |
| `toast.svelte.ts` | 45 lines | Svelte 5 class with `$state` rune | **GOOD** - Clean, small, uses Svelte 5 runes properly. Auto-dismiss with configurable durations. |

### Component Quality Analysis

#### ConfigView.svelte

- **Pattern**: Uses `$props()`, `$state`, `$effect` (Svelte 5 runes).
- **Hybrid approach**: Subscribes to Svelte 4 writable stores inside `$effect()` blocks with cleanup (`return unsub`). This is correct but creates friction between paradigms.
- **Concern**: Orchestrates 11+ sub-components with shared state. The component is doing too much coordination; a composition-based approach with a dedicated controller store would be cleaner.

#### AgentsList.svelte (estimated ~350 lines from first 100 lines read)

- **Props**: Well-typed `Props` interface using `$props()`.
- **Search**: Multi-field search across name, description, tags, category. Correct lowercase comparison.
- **Sort**: 4 sort modes (name-asc/desc, version, status) with generic sort function.
- **State tracking**: `deployingAgents` and `undeployingAgents` as `Set<string>` with proper add/remove via Set reconstruction (Svelte 5 reactivity requires new reference).
- **Accessibility**: Confirm dialogs for destructive actions (undeploy, force redeploy).
- **Issue**: Category grouping logic uses `$derived.by()` which is correct for Svelte 5.

#### SkillsList.svelte (641 lines)

- **Feature-rich**: Filter bar, sort controls, toolchain grouping toggle, version update detection, immutable skill protection, deployed/available sections with expand/collapse.
- **Version comparison**: Uses external `compareVersions` utility for outdated detection.
- **Deployment matching**: `findAvailableForDeployed()` uses three-tier matching: manifest_name, exact name, suffix match. Good fallback strategy.
- **Immutable detection**: `IMMUTABLE_COLLECTIONS = ['PM_CORE_SKILLS', 'CORE_SKILLS']` matches backend business rules.
- **Loading states**: Proper skeleton/spinner states per section.
- **Empty states**: Differentiated messages for "no items" vs "no matches for filters".
- **Accessibility**: `aria-label` on sort select, `aria-pressed` on group toggle, `title` attributes on buttons.
- **Issue**: `normalizeToolchain()` uppercases first letter but maps empty/universal to 'Universal'. This could cause inconsistent grouping if backend sends mixed casing.

#### AgentDetailPanel.svelte (438 lines)

- **Lazy loading**: Fetches detail on agent change with cancellation pattern (`let cancelled = false; return () => { cancelled = true; }`). Correct approach for preventing stale updates.
- **Progressive enhancement**: Shows list-level data immediately (name, description, version, tags), then upgrades to full detail when API response arrives.
- **Skill deployment status**: `isSkillDeployed()` uses exact match then suffix match (`-${shortName}`). Same pattern as backend validation service.
- **Error handling**: Differentiates 404 (informational blue banner) from actual errors (red banner). Non-fatal -- still shows basic info from list data.
- **Navigation**: Agent handoff links are navigable only if the target agent exists in `allAgentNames`. Non-navigable agents render as plain text.
- **Collapsible sections**: Expertise, Skills, Dependencies, Collaborators, Constraints, Best Practices. Skills section defaults to expanded.
- **Deploy/Undeploy actions**: Core agents show lock icon with "cannot be undeployed" text.

#### AutoConfigPreview.svelte (421 lines)

- **Two-step wizard**: Step 1 (Detect & Recommend) -> Step 2 (Review & Apply).
- **Deployment pipeline**: Uses `DeploymentPipeline` component with 6 stages, updated via Socket.IO progress events.
- **Phase mapping**: `phaseToStageMap` maps backend phases to pipeline stage indices. Clean separation.
- **Confirmation gate**: Type "apply" to confirm -- prevents accidental execution.
- **Timeout**: `waitForAutoConfigCompletion` uses 120-second timeout.
- **Skill recommendations**: Displays recommended skills with scope target information (".claude/skills/ (project-scoped)").
- **Error recovery**: Retry button for detection failures.
- **Result display**: Shows backup ID, deployed agent/skill counts, restart warning.
- **Issue**: No way to cancel a running auto-configure operation. Once apply starts, user must wait for completion or timeout.

### Svelte 5 Runes Usage Assessment

| File | Pattern | Correct? |
|---|---|---|
| `toast.svelte.ts` | `$state` in class | YES - Idiomatic Svelte 5 |
| `config.svelte.ts` | `writable()` stores | NO - Svelte 4 pattern, but functional. Migration to `$state` class would be breaking change. |
| `skillLinks.svelte.ts` | `writable()` store | NO - Same as above; Svelte 4 pattern |
| `ConfigView.svelte` | `$props()`, `$state`, `$effect` | YES - Proper Svelte 5 runes |
| `AgentsList.svelte` | `$props()`, `$state`, `$derived.by()` | YES - Proper Svelte 5 runes |
| `SkillsList.svelte` | `$props()`, `$state`, `$derived.by()` | YES - Proper Svelte 5 runes |
| `AgentDetailPanel.svelte` | `$props()`, `$state`, `$derived`, `$effect` | YES - Proper Svelte 5 runes |
| `AutoConfigPreview.svelte` | `$props()`, `$state`, `$derived` | YES - Proper Svelte 5 runes |

**Verdict**: Components correctly use Svelte 5 runes. Stores use Svelte 4 writable pattern. This hybrid is pragmatic but should converge to one paradigm over time. The `$effect(() => { const unsub = store.subscribe(...); return unsub; })` bridge pattern in ConfigView.svelte is the correct way to consume Svelte 4 stores from Svelte 5 components.

### XSS Risk Assessment

- **HighlightedText component**: Used in AgentsList and SkillsList for search term highlighting. If this component uses `{@html}`, it could be an XSS vector. The search query comes from user input and is used in rendering. **Requires inspection of HighlightedText.svelte implementation**.
- **Agent/skill names**: Rendered via `{text}` interpolation (not `{@html}`), which is safe.
- **Description text**: Rendered via `{text}` interpolation. Safe.
- **Badge component**: Renders text via props. Safe.
- **No `{@html}` usage detected** in the reviewed components. Risk is LOW.

### Feature Flags

Feature flags in `features.ts` are well-designed:
- `RICH_DETAIL_PANELS`, `FILTER_DROPDOWNS`, `VERSION_MISMATCH`, `COLLABORATION_LINKS`, `SKILL_LINKS_MERGE`, `SEARCH_ENHANCEMENTS`
- All currently set to `true` (all features enabled)
- Used with `{#if FEATURES.X}` conditional rendering in components
- `as const` ensures type safety
- Provides clean rollback mechanism per feature

---

## Part 5: Change Coherence Check

### Backend API Endpoints vs Frontend Consumers

| Backend Endpoint | Frontend Consumer | Status |
|---|---|---|
| `GET /api/config/project/summary` | `fetchProjectSummary()` | MATCHED |
| `GET /api/config/agents/deployed` | `fetchDeployedAgents()` | MATCHED |
| `GET /api/config/agents/available` | `fetchAvailableAgents()` | MATCHED |
| `GET /api/config/skills/deployed` | `fetchDeployedSkills()` | MATCHED |
| `GET /api/config/skills/available` | `fetchAvailableSkills()` | MATCHED |
| `GET /api/config/sources` | `fetchSources()` | MATCHED |
| `GET /api/config/agents/{name}` | `fetchAgentDetail()` | MATCHED |
| `GET /api/config/skills/{name}` | `fetchSkillDetail()` | MATCHED |
| `POST /api/config/sources/agent` | `addSource()` | MATCHED |
| `POST /api/config/sources/skill` | `addSource()` | MATCHED |
| `PATCH /api/config/sources/{type}` | `updateSource()` | MATCHED |
| `DELETE /api/config/sources/{type}` | `removeSource()` | MATCHED |
| `POST /api/config/sources/{type}/sync` | `syncSource()` | MATCHED |
| `POST /api/config/sources/sync-all` | `syncAllSources()` | MATCHED |
| `POST /api/config/agents/{name}` | `deployAgent()` | MATCHED |
| `DELETE /api/config/agents/{name}` | `undeployAgent()` | MATCHED |
| `POST /api/config/agents/batch` | `batchDeployAgents()` | MATCHED |
| `POST /api/config/skills/{name}` | `deploySkill()` | MATCHED |
| `DELETE /api/config/skills/{name}` | `undeploySkill()` | MATCHED |
| `GET /api/config/skills/deployment-mode` | `getDeploymentMode()` | MATCHED |
| `PUT /api/config/skills/deployment-mode` | `switchDeploymentMode()` | MATCHED |
| `GET /api/config/toolchain/detect` | `detectToolchain()` | MATCHED |
| `GET /api/config/autoconfig/preview` | `previewAutoConfig()` | MATCHED |
| `POST /api/config/autoconfig/apply` | `applyAutoConfig()` | MATCHED |
| `GET /api/config/validate` | Consumed by ValidationPanel | MATCHED |
| `GET /api/config/skill-links/` | `loadSkillLinks()` (skillLinks store) | MATCHED |
| `GET /api/config/sessions/active` | `checkActiveSessions()` | MATCHED |
| Socket.IO `config_event` | `handleConfigEvent()` | MATCHED |

**Result**: All backend endpoints have frontend consumers. No orphaned backend endpoints detected.

### Frontend API Calls vs Backend Handlers

All `fetch()` calls in `config.svelte.ts` and `skillLinks.svelte.ts` map to registered backend routes. The Socket.IO `config_event` handler processes 14 operation types, all of which correspond to backend emission points in the deployment handlers.

**No orphaned frontend API calls detected.**

### Orphaned Code Check

- All feature flag references (`FEATURES.FILTER_DROPDOWNS`, `FEATURES.VERSION_MISMATCH`, etc.) are actively used in component conditional rendering.
- The `skillLinks.svelte.ts` store is consumed by `SkillLinksView.svelte` (imported in ConfigView).
- `toast.svelte.ts` is consumed by SkillsList, AutoConfigPreview, and other components.
- All shared components (Badge, ConfirmDialog, Modal, CollapsibleSection, MetadataGrid, etc.) are imported by at least one config component.

**No orphaned code detected** in the reviewed files.

---

## Part 6: Issues Found

### HIGH Severity

| ID | Category | Description | Location |
|---|---|---|---|
| H-01 | Coverage | **No automated tests for 47 Svelte frontend components** (only SkillChip.test.ts exists). ConfigView, AgentsList, SkillsList, AgentDetailPanel, AutoConfigPreview have complex logic (search, sort, filter, state machines) that is entirely untested. | `src/claude_mpm/dashboard-svelte/src/lib/components/config/` |
| H-02 | Coverage | **Config store (981 lines) has zero unit tests.** Fetch error handling, LRU cache eviction, Socket.IO event processing, auto-config event system, and mutation functions are all untested. | `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` |
| H-03 | Architecture | **Config store is a God Module.** 981 lines combining types, stores, fetchers, mutations, events, and cache in a single file. Violates single responsibility principle and prevents focused testing. | `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` |
| H-04 | Logic Bug | **`is_deployed: true` hardcoded** in skillLinks store transformation. All skills from agents are assumed deployed, which defeats the purpose of cross-reference validation that identifies undeployed skills. | `src/claude_mpm/dashboard-svelte/src/lib/stores/config/skillLinks.svelte.ts:84,104` |
| H-05 | Logic Bug | **0.0 min_confidence treated as falsy.** User requesting `--min-confidence 0.0` gets 0.5 instead. Documented in tests but unfixed in production code. | `src/claude_mpm/cli/commands/auto_configure.py` (via `test_autoconfig_defaults.py:70-79`) |
| H-06 | Coverage | **Session detector has no tests.** `session_detector.py` provides active session warnings during deployment, a safety-critical feature. Silent failures could lead to configuration corruption during active Claude Code sessions. | `src/claude_mpm/services/config_api/session_detector.py` |

### MEDIUM Severity

| ID | Category | Description | Location |
|---|---|---|---|
| M-01 | Architecture | **Svelte 4/5 hybrid pattern** in stores. `config.svelte.ts` and `skillLinks.svelte.ts` use Svelte 4 `writable()` while components use Svelte 5 runes, requiring `$effect` bridge pattern. Should converge. | Stores vs components |
| M-02 | Resilience | **No cancellation for auto-configure apply.** Once `handleApply()` starts, user cannot cancel. Only timeout (120s) or completion ends the operation. | `AutoConfigPreview.svelte:78-113` |
| M-03 | Coverage | **Remote agent discovery service untested.** `remote_agent_discovery_service.py` has no dedicated test file. | `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py` |
| M-04 | Consistency | **normalizeToolchain()** uppercases first letter but maps empty/universal to 'Universal'. Backend may send varying cases causing inconsistent grouping keys. | `SkillsList.svelte:92-95` |
| M-05 | Coverage | **No concurrent deployment API tests.** File lock tests verify concurrency at the filesystem level, but no tests simulate two simultaneous API deployment requests through aiohttp handlers. | Backend test gap |

### LOW Severity

| ID | Category | Description | Location |
|---|---|---|---|
| L-01 | Robustness | **AutoConfigPreview catch block** uses `e.message` without null check. Non-Error rejection values would produce "undefined" error message. | `AutoConfigPreview.svelte:105` |
| L-02 | Performance | **LRU cache has no expiration.** Agent/skill detail cache entries persist until evicted by size (50 entries) or explicitly invalidated. Stale data may be shown if backend data changes without Socket.IO notification. | `config.svelte.ts` LRU cache |
| L-03 | Accessibility | **Missing aria-label** on some interactive elements in SkillsList (expand/collapse buttons) and AgentDetailPanel (collapsible sections). | Various components |
| L-04 | Testing | **Hardcoded dates in test data** (e.g., "2026-02-13T10:00:00"). While functional, using relative time helpers would be more maintainable. | `test_backup_manager.py`, `test_config_api_rollback.py` |

---

## Part 7: Recommendations

### Priority 1: Before Merge

1. **Fix H-05 (0.0 falsy bug)**: Change `getattr(args, 'min_confidence', None) or 0.5` to use explicit `None` check: `getattr(args, 'min_confidence', None); if min_confidence is None: min_confidence = 0.5`. This is a one-line fix with a documented test already expecting the correct behavior.

2. **Fix H-04 (hardcoded is_deployed)**: In `skillLinks.svelte.ts`, either pass deployment status from the backend response or cross-reference with the deployed skills store to determine actual deployment status.

### Priority 2: Post-Merge Sprint

3. **Address H-01/H-02 (Frontend testing)**: Create a Vitest test suite for:
   - Config store fetch functions (mock fetch, verify store updates)
   - Config store Socket.IO event handler (verify state transitions)
   - Search/sort/filter logic extracted from AgentsList and SkillsList
   - AutoConfigPreview state machine transitions

4. **Address H-03 (Store refactoring)**: Split `config.svelte.ts` into focused modules. Start with extracting types, then cache logic, then event handling.

5. **Address H-06 (Session detector tests)**: Write tests for active session detection, focusing on edge cases (no sessions, expired sessions, detection failures).

### Priority 3: Future Improvement

6. **Converge store patterns (M-01)**: When next modifying stores, migrate from Svelte 4 writable to Svelte 5 `$state` class pattern (as demonstrated by `toast.svelte.ts`).

7. **Add auto-configure cancellation (M-02)**: Implement an abort mechanism for the auto-configure apply operation, either via AbortController on the fetch or a backend cancellation endpoint.

8. **Add concurrent deployment tests (M-05)**: Test simultaneous deployment API requests to verify file locking and journal consistency under real API concurrency.

---

## Appendix: File Inventory

### Test Files Reviewed (20)

| # | File | Lines | Status |
|---|---|---|---|
| 1 | `tests/services/agents/test_auto_config_manager.py` | ~1 line change | Modified |
| 2 | `tests/core/test_config_scope.py` | 312 | New |
| 3 | `tests/dashboard/test_config_skill_links.py` | 495 | New |
| 4 | `tests/dashboard/test_config_validate.py` | 173 | New |
| 5 | `tests/e2e/test_autoconfig_full_flow.py` | 838 | New |
| 6 | `tests/services/config_api/test_autoconfig_defaults.py` | 417 | New |
| 7 | `tests/services/config_api/test_autoconfig_events.py` | 584 | New |
| 8 | `tests/services/config_api/test_autoconfig_integration.py` | 81 | New |
| 9 | `tests/services/config_api/test_autoconfig_skill_deployment.py` | 501 | New |
| 10 | `tests/services/test_config_validation_service.py` | 579 | New |
| 11 | `tests/test_backup_manager.py` | 341 | New |
| 12 | `tests/test_config_api_business_rules.py` | 248 | New |
| 13 | `tests/test_config_api_deployment.py` | ~832 | New |
| 14 | `tests/test_config_api_rollback.py` | 259 | New |
| 15 | `tests/test_config_routes.py` | ~1176 | New |
| 16 | `tests/test_deployment_verifier.py` | 261 | New |
| 17 | `tests/test_operation_journal.py` | 217 | New |
| 18 | `tests/test_phase2_agent_manager.py` | 194 | New |
| 19 | `tests/unit/core/test_config_file_lock.py` | 238 | New |
| 20 | `tests/unit/services/monitor/routes/test_config_sources.py` | 498 | New |

### Frontend Files Reviewed

| File | Lines | Description |
|---|---|---|
| `config.svelte.ts` | 981 | Primary config store |
| `skillLinks.svelte.ts` | 135 | Skill links store |
| `toast.svelte.ts` | 45 | Toast notification store |
| `features.ts` | 28 | Feature flags |
| `ConfigView.svelte` | ~400 | Main config orchestrator |
| `AgentsList.svelte` | ~350 | Agent list with search/sort |
| `SkillsList.svelte` | 641 | Skill list with grouping/filters |
| `AgentDetailPanel.svelte` | 438 | Agent detail with lazy loading |
| `AutoConfigPreview.svelte` | 421 | Auto-configure wizard |
| `+page.svelte` | ~200 | Page-level integration |

### Backend Source Files (non-build, changed from main)

72 files total (including 53 Svelte dashboard files and 19 Python backend files).

---

*Analysis generated by Claude Opus 4.6 Research Agent on 2026-02-19.*
