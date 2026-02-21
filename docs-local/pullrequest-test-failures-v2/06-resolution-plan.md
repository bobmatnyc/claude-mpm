# Resolution Plan: 22 Failing Auto-Configure Tests

**Date:** 2026-02-21
**Branch:** `ui-agents-skills-config`
**Status:** FINAL - Synthesized from 5 parallel research streams

---

## Executive Summary

The 22 failing tests were **AI-generated (Claude Sonnet 4) from design specifications** and committed with the acknowledgment that only "33/63 tests passing." They were born broken. The tests target the **wrong module** (CLI command instead of API handler), mock **nonexistent methods** (`_emit_event`, `_emit_phase_event`), and use **incorrect patching strategies** on `@property` attributes.

**Root Verdict:** These are NOT "missing features." The current architecture is correct:
- **CLI path** (`auto_configure.py`): Rich console output, no event emission (correct)
- **API path** (`autoconfig_handler.py`): Full Socket.IO event emission (correct)

The tests demand mixing Socket.IO into the CLI command, which would violate the existing clean separation of concerns.

---

## Root Causes (Prioritized)

| # | Root Cause | Affected Tests | Fix |
|---|-----------|---------------|-----|
| **RC-1** | `_emit_event` method doesn't exist on `RichProgressObserver` | 5 tests | DELETE tests |
| **RC-2** | `_emit_phase_event` method doesn't exist on `AutoConfigureCommand` | 5 tests | DELETE tests |
| **RC-3** | `@property` attributes can't be patched via `patch.object` on instances | 10 tests | FIX mock strategy |
| **RC-4** | `get_socketio_server`/`get_event_emitter` not imported in `auto_configure.py` | 2 tests | DELETE tests |

---

## Resolution: Test-by-Test Plan

### File 1: `tests/services/config_api/test_autoconfig_events.py`

**Current state:** 15 tests total (12 FAIL, 3 PASS)

#### DELETE - 12 tests (all test nonexistent event infrastructure)

| # | Test Name | Root Cause | Why Delete |
|---|-----------|-----------|------------|
| 1 | `test_agent_deployment_started_event_structure` | RC-1 | Mocks `_emit_event` that doesn't exist on observer |
| 2 | `test_agent_deployment_progress_event_payload` | RC-1 | Same - `_emit_event` never implemented |
| 3 | `test_agent_deployment_completed_success_event` | RC-1 | Same |
| 4 | `test_agent_deployment_completed_failure_event` | RC-1 | Same |
| 5 | `test_deployment_completed_summary_event` | RC-1 | Same |
| 6 | `test_phase_0_toolchain_analysis_events` | RC-2, RC-3 | Mocks `_emit_phase_event` + unpatchable property |
| 7 | `test_phase_1_min_confidence_validation_events` | RC-2, RC-3 | Same |
| 8 | `test_phase_2_skill_deployment_events` | RC-2, RC-3 | Same + `skills_deployer` property |
| 9 | `test_phase_3_agent_archiving_events` | RC-2 | Tests deliberately excluded Phase 3 event emission |
| 10 | `test_phase_4_configuration_completion_events` | RC-2 | Mocks `_emit_phase_event` that doesn't exist |
| 11 | `test_full_workflow_event_sequence` | RC-3, RC-4 | `get_socketio_server` not imported + property patching |
| 12 | `test_event_emission_error_handling` | RC-3, RC-4 | Same |

#### KEEP as-is - 3 tests (pass, pure data validation)

| # | Test Name | Status | Note |
|---|-----------|--------|------|
| 13 | `test_event_payload_json_serializable` | PASS | Tests static dict serialization |
| 14 | `test_event_payload_required_fields` | PASS | Tests dict structure - CLEAN UP archiving references |
| 15 | `test_event_payload_field_types` | PASS | Tests dict types - CLEAN UP archiving references |

#### CLEANUP in passing tests

In `test_event_payload_required_fields`:
- Remove `"agent_archiving"` from `required_fields_by_phase` dict
- Remove `archive_count` references

In `test_event_payload_field_types`:
- Remove `"archive_count": int` from `type_constraints`
- Remove `"archive_count": 5` from `sample_payload`

---

### File 2: `tests/services/config_api/test_autoconfig_skill_deployment.py`

**Current state:** 17 tests total (10 FAIL, 7 PASS)

#### KEEP as-is - 7 tests (pass, test real functionality)

| # | Test Name | Status | Tests |
|---|-----------|--------|-------|
| 1 | `test_recommend_skills_with_valid_agents` | PASS | `_recommend_skills()` - real method |
| 2 | `test_recommend_skills_with_no_agents` | PASS | Same |
| 3 | `test_recommend_skills_with_unmapped_agents` | PASS | Same |
| 4 | `test_recommend_skills_deduplication` | PASS | Same |
| 5 | `test_skill_deployment_path_resolution` | PASS | `resolve_skills_dir()` - real function |
| 6 | `test_skill_deployment_directory_creation` | PASS | Filesystem operations |
| 7 | `test_cross_scope_skill_isolation` | PASS | Filesystem operations |

#### FIX - 10 tests (property patching strategy)

All 10 tests fail because they use `patch.object(command, "skills_deployer")` or `patch.object(command, "auto_config_manager")` on `@property` attributes. The fix is to set the private backing attribute directly.

**Fix pattern:**

```python
# BEFORE (fails - property has no setter):
with patch.object(command, "skills_deployer") as mock_deployer:
    mock_deployer.deploy_skills.return_value = {...}
    result = command._deploy_skills(skills)

# AFTER (works - sets backing attribute directly):
mock_deployer = Mock()
mock_deployer.deploy_skills.return_value = {...}
command._skills_deployer = mock_deployer
result = command._deploy_skills(skills)
```

**For full workflow tests, set BOTH:**
```python
command._auto_config_manager = mock_auto_config
command._skills_deployer = mock_deployer
```

| # | Test Name | RC | Fix |
|---|-----------|-----|-----|
| 1 | `test_deploy_skills_success` | RC-3 | `command._skills_deployer = mock` |
| 2 | `test_deploy_skills_partial_failure` | RC-3 | Same |
| 3 | `test_deploy_skills_complete_failure` | RC-3 | Same |
| 4 | `test_deploy_skills_with_force_parameter` | RC-3 | Same |
| 5 | `test_project_scope_skill_deployment` | RC-3 | Same |
| 6 | `test_user_scope_skill_deployment_fallback` | RC-3 | Same |
| 7 | `test_full_workflow_with_skills_success` | RC-3 | Both `_auto_config_manager` + `_skills_deployer` |
| 8 | `test_full_workflow_agents_only` | RC-3 | Same |
| 9 | `test_full_workflow_skills_only` | RC-3 | Same |
| 10 | `test_full_workflow_skill_deployment_failure_handling` | RC-3 | Same |

**Additional concerns for full workflow tests (#7-10):**
- `run()` calls `self.setup_logging(args)` which requires `args.debug`, `args.verbose`, `args.quiet`
- `_review_project_agents()` accesses filesystem paths - may need patching
- `_confirm_deployment()` reads stdin - `skip_confirmation=True`/`yes=True` should bypass

---

## Summary of Actions

| Action | Count | Files |
|--------|-------|-------|
| **DELETE test methods** | 12 | `test_autoconfig_events.py` |
| **FIX mock strategy** | 10 | `test_autoconfig_skill_deployment.py` |
| **KEEP as-is** | 10 | Both files |
| **CLEANUP passing tests** | 2 | `test_autoconfig_events.py` (remove archiving refs) |
| **Total tests after fix** | 20 | (12 deleted + 2 cleanup = 10 remaining + 17 = 27 tests, -12 deleted = ~20) |

---

## Why NOT "Implement Missing Features"

The devil's advocate analysis convincingly argues against implementing the "missing" event system:

1. **Architectural pollution**: Adding Socket.IO to a CLI command violates separation of concerns
2. **The CLI path doesn't need events**: It outputs to terminal via Rich - that's its job
3. **The API path already has events**: `autoconfig_handler.py` has full event emission
4. **Wrong event names**: Test events don't match UI expectations (`autoconfig_progress` vs `toolchain_analysis`)
5. **Tests target wrong module**: Even if features were built, they'd be in the wrong place

The current architecture is correct:
```
CLI: auto_configure.py → RichProgressObserver → Terminal (Rich console)
API: autoconfig_handler.py → ConfigEventHandler → Socket.IO → Dashboard
```

---

## Phase 3 (Agent Archiving) Notes

- Agent archiving code STILL EXISTS in CLI (`auto_configure.py:960-973`)
- Agent archiving was NEVER in the API path
- The design spec (Phase 3) proposed adding it to API but was excluded from scope
- `test_phase_3_agent_archiving_events` tests event emission for archiving - DELETE it
- Passing `TestEventPayloadValidation` tests contain archiving references - CLEAN UP

---

## Implementation Order

### Step 1: Delete 12 failing event tests from `test_autoconfig_events.py`
Delete these test classes/methods:
- `TestProgressObserverEvents` class (5 tests) - entire class
- `TestAutoConfigurePhaseEvents` class (5 tests) - entire class
- `TestSocketIOEventIntegration` class (2 tests) - entire class

### Step 2: Clean up passing tests in `test_autoconfig_events.py`
In `TestEventPayloadValidation`:
- Remove `"agent_archiving"` from phase fields
- Remove `archive_count` references

### Step 3: Fix 10 property-patching tests in `test_autoconfig_skill_deployment.py`
Replace all `patch.object(command, "skills_deployer")` with `command._skills_deployer = mock`
Replace all `patch.object(command, "auto_config_manager")` with `command._auto_config_manager = mock`

### Step 4: Run tests and verify
```bash
uv run pytest tests/services/config_api/ -v
```

Expected: All remaining tests pass (20 tests, 0 failures).

### Step 5: (Optional) Write new API handler tests
If event emission test coverage is desired, write NEW tests targeting:
- `autoconfig_handler.py` (the module that actually emits events)
- Mock `handler.emit_config_event()` (the method that actually exists)
- Use event names the UI expects (`autoconfig_progress`, `autoconfig_completed`, `autoconfig_failed`)

---

## Evidence Sources

| Report | Key Finding |
|--------|-------------|
| `01-backend-analysis.md` | Two execution paths (CLI vs API), event emission only in API |
| `02-test-expectations-analysis.md` | Precise mismatch mapping, 2 root causes cover all 22 failures |
| `03-ui-event-analysis.md` | UI expects `config_event` with `autoconfig_*` operations, not test event names |
| `04-removed-phase3-impact.md` | Archiving still in CLI, tests generated after scope exclusion |
| `05-devils-advocate.md` | AI-hallucinated tests, born broken, wrong module targeted |
