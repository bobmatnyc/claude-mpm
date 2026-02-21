# Test Expectations Analysis: Exact Mismatches

## Executive Summary

**22 tests total across 2 files. 12 FAIL, 10 PASS.**

All failures fall into exactly **2 root causes**:

| Root Cause | Count | Error Message |
|---|---|---|
| **RC-1**: `patch.object` on `_emit_event` method that doesn't exist on `RichProgressObserver` | 5 | `AttributeError: ...does not have the attribute '_emit_event'` |
| **RC-2**: `patch.object` on Python `@property` attributes (`auto_config_manager`, `skills_deployer`) which cannot be patched on instances | 17 (7 unique failures) | `AttributeError: property '...' of 'AutoConfigureCommand' object has no setter` |

The tests were written against a **planned/speculative API** that was never implemented. The actual implementation has no Socket.IO event emission, no `_emit_event` method, and no `_emit_phase_event` method.

---

## File 1: `tests/services/config_api/test_autoconfig_events.py`

**15 tests total: 10 FAIL, 3 PASS, 2 FAIL (integration)**

### PASSING Tests (3)

| Test | Why It Passes |
|---|---|
| `test_event_payload_json_serializable` | Tests only `json.dumps/loads` on hardcoded dicts. No dependency on implementation. |
| `test_event_payload_required_fields` | Tests only dict structure assertions on hardcoded dicts. No dependency on implementation. |
| `test_event_payload_field_types` | Tests only `isinstance` checks on hardcoded dicts. No dependency on implementation. |

**Key insight**: All 3 passing tests are in `TestEventPayloadValidation` class and are purely data-structure tests. They never import or instantiate any production class.

---

### FAILING Tests: `TestProgressObserverEvents` (5 tests)

All 5 tests share the **identical root cause**: They attempt `patch.object(progress_observer, "_emit_event")` but `RichProgressObserver` has no `_emit_event` method.

#### Test 1: `test_agent_deployment_started_event_structure`
- **Line**: 48
- **Patch target**: `patch.object(progress_observer, "_emit_event")`
- **What test expects**:
  - `RichProgressObserver` has a `_emit_event` method
  - When `on_agent_deployment_started(agent_id, agent_name, index, total)` is called, it internally calls `_emit_event` with a dict containing:
    ```python
    {"phase": "agent_deployment_started", "agent_id": "python-engineer",
     "agent_name": "Python Engineer", "progress": {"current": 1, "total": 3}}
    ```
- **Actual implementation** (`auto_configure.py:56-70`):
  - `on_agent_deployment_started` creates a Rich `Progress` bar and adds a task. No event emission whatsoever.
  - No `_emit_event` method exists on `RichProgressObserver` or any of its parent classes (`NullObserver`, `IDeploymentObserver`).
- **Exact error**: `AttributeError: <...RichProgressObserver object...> does not have the attribute '_emit_event'`
- **Root cause**: **Missing method** - `_emit_event` was never implemented
- **Fix category**: `DELETE_TEST` (tests a feature that was designed but never built)

#### Test 2: `test_agent_deployment_progress_event_payload`
- **Line**: 69
- **Patch target**: `patch.object(progress_observer, "_emit_event")`
- **What test expects**:
  - Calling `on_agent_deployment_progress(agent_id, progress, message)` emits event:
    ```python
    {"phase": "agent_deployment_progress", "agent_id": "python-engineer",
     "progress": 45, "message": "Downloading agent files..."}
    ```
- **Actual implementation** (`auto_configure.py:72-77`):
  - `on_agent_deployment_progress` just calls `self.progress.update(self.task_id, completed=progress)`. No event emission.
- **Exact error**: `AttributeError: ...does not have the attribute '_emit_event'`
- **Root cause**: **Missing method** - `_emit_event` never implemented
- **Fix category**: `DELETE_TEST`

#### Test 3: `test_agent_deployment_completed_success_event`
- **Line**: 87
- **Patch target**: `patch.object(progress_observer, "_emit_event")`
- **What test expects**:
  - Calling `on_agent_deployment_completed(agent_id, agent_name, success=True, error=None)` emits event:
    ```python
    {"phase": "agent_deployment_completed", "agent_id": "python-engineer",
     "agent_name": "Python Engineer", "success": True, "error": None}
    ```
- **Actual implementation** (`auto_configure.py:79-89`):
  - Calls `self.progress.update(...)` and `self.console.print(...)`. No event emission.
- **Exact error**: `AttributeError: ...does not have the attribute '_emit_event'`
- **Root cause**: **Missing method**
- **Fix category**: `DELETE_TEST`

#### Test 4: `test_agent_deployment_completed_failure_event`
- **Line**: 107
- **Patch target**: `patch.object(progress_observer, "_emit_event")`
- **What test expects**:
  - Same as test 3 but with `success=False, error="Agent not found in registry"`.
- **Actual implementation**: Same as above - no event emission.
- **Exact error**: `AttributeError: ...does not have the attribute '_emit_event'`
- **Root cause**: **Missing method**
- **Fix category**: `DELETE_TEST`

#### Test 5: `test_deployment_completed_summary_event`
- **Line**: 126
- **Patch target**: `patch.object(progress_observer, "_emit_event")`
- **What test expects**:
  - Calling `on_deployment_completed(success_count=2, failure_count=1, duration_ms=15432.5)` emits:
    ```python
    {"phase": "deployment_completed", "summary": {"success_count": 2,
     "failure_count": 1, "total_count": 3, "duration_ms": 15432.5}}
    ```
- **Actual implementation** (`auto_configure.py:91-96`):
  - Just calls `self.progress.stop()`. No event emission.
- **Exact error**: `AttributeError: ...does not have the attribute '_emit_event'`
- **Root cause**: **Missing method**
- **Fix category**: `DELETE_TEST`

---

### FAILING Tests: `TestAutoConfigurePhaseEvents` (5 tests)

All 5 tests share **two compounding root causes**:
1. They try to `patch.object(command, "auto_config_manager")` or `patch.object(command, "skills_deployer")` on an instance, but these are `@property` attributes that cannot be patched on instances via `patch.object`.
2. They expect a `_emit_phase_event` method on `AutoConfigureCommand` that doesn't exist.

#### Test 6: `test_phase_0_toolchain_analysis_events`
- **Line**: 156-199
- **Patch targets**:
  1. `patch.object(command, "auto_config_manager")` - **FAILS** (property, no setter)
  2. `patch("claude_mpm.cli.commands.auto_configure.get_event_emitter")` - `get_event_emitter` is NOT imported in `auto_configure.py`
  3. `patch.object(command, "_emit_phase_event")` - method doesn't exist on `AutoConfigureCommand`
- **What test expects**:
  - `command.run(args)` emits phase events via `_emit_phase_event("toolchain_analysis", {...})`
  - Event data includes `detected_components` list
- **Actual implementation**:
  - `AutoConfigureCommand` has no `_emit_phase_event` method
  - `auto_config_manager` is a `@property` (line 118-147) - cannot be patched on instance
  - `get_event_emitter` is not imported in `auto_configure.py`
- **Exact error**: `AttributeError: property 'auto_config_manager' of 'AutoConfigureCommand' object has no setter`
- **Root cause**: **Property can't be patched** + **missing methods** + **missing imports**
- **Fix category**: `DELETE_TEST`

#### Test 7: `test_phase_1_min_confidence_validation_events`
- **Line**: 201-241
- **Patch targets**:
  1. `patch.object(command, "auto_config_manager")` - **FAILS** (property)
  2. `patch.object(command, "_emit_phase_event")` - doesn't exist
- **What test expects**:
  - Phase event `"min_confidence_validation"` emitted with `min_confidence`, `filtered_recommendations`, `filtered_count`
- **Actual implementation**: No such event emission exists
- **Exact error**: `AttributeError: property 'auto_config_manager' of 'AutoConfigureCommand' object has no setter`
- **Root cause**: **Property can't be patched** + **missing method**
- **Fix category**: `DELETE_TEST`

#### Test 8: `test_phase_2_skill_deployment_events`
- **Line**: 243-269
- **Patch targets**:
  1. `patch.object(command, "skills_deployer")` - **FAILS** (property)
  2. `patch.object(command, "_emit_phase_event")` - doesn't exist
- **What test expects**:
  - `command._deploy_skills(recommended_skills)` emits `"skill_deployment"` event with `recommended_skills` and `deployment_result`
- **Actual implementation** (`auto_configure.py:900-915`):
  - `_deploy_skills` just calls `self.skills_deployer.deploy_skills(...)` and returns result. No event emission.
- **Exact error**: `AttributeError: property 'skills_deployer' of 'AutoConfigureCommand' object has no setter`
- **Root cause**: **Property can't be patched** + **missing method**
- **Fix category**: `DELETE_TEST`

#### Test 9: `test_phase_3_agent_archiving_events`
- **Line**: 271-294
- **Patch targets**:
  1. `patch.object(command, "_archive_agents")` - `_archive_agents` **EXISTS** (line 960), but patching it also patches `_emit_phase_event` which doesn't exist
  2. `patch.object(command, "_emit_phase_event")` - doesn't exist
- **What test expects**:
  - Calling `_archive_agents(agents_to_archive)` emits `"agent_archiving"` event with `agents_to_archive` and `archive_count`
- **Actual implementation** (`auto_configure.py:960-973`):
  - `_archive_agents` delegates to `AgentReviewService.archive_agents(...)`. No event emission.
- **Exact error**: `AttributeError: <...AutoConfigureCommand object...> does not have the attribute '_emit_phase_event'`
  - Note: This one gets past the `_archive_agents` patch (it exists!) but fails on `_emit_phase_event` patch.
- **Root cause**: **Missing method** (`_emit_phase_event`)
- **Fix category**: `DELETE_TEST`

#### Test 10: `test_phase_4_configuration_completion_events`
- **Line**: 296-319
- **Patch targets**:
  1. `patch.object(command, "_emit_phase_event")` - doesn't exist
- **What test expects**:
  - `command._show_restart_notification(agent_result, skills_result)` emits `"configuration_completion"` event with `total_agents_deployed`, `total_skills_deployed`, `restart_required`
- **Actual implementation** (`auto_configure.py:1016-1051`):
  - `_show_restart_notification` takes 3 args (agent_result, skills_result, archive_result) and just does `self.console.print(...)`. No event emission.
  - Note: Test calls it with 2 args, actual signature takes 3 (with `archive_result=None` default).
- **Exact error**: `AttributeError: <...AutoConfigureCommand object...> does not have the attribute '_emit_phase_event'`
- **Root cause**: **Missing method** (`_emit_phase_event`)
- **Fix category**: `DELETE_TEST`

---

### FAILING Tests: `TestSocketIOEventIntegration` (2 tests)

#### Test 11: `test_full_workflow_event_sequence`
- **Line**: 461-549
- **Patch targets**:
  1. `patch("claude_mpm.cli.commands.auto_configure.get_socketio_server")` - `get_socketio_server` is NOT imported in `auto_configure.py`
  2. `patch.object(command, "auto_config_manager")` - **FAILS** (property)
  3. `patch.object(command, "skills_deployer")` - **FAILS** (property)
- **What test expects**:
  - Full workflow emits Socket.IO events in sequence: `toolchain_analysis` -> `min_confidence_validation` -> `configuration_completion`
  - Events captured via `mock_socketio_server.emit.side_effect`
- **Actual implementation**:
  - No Socket.IO integration in `auto_configure.py` at all
  - `get_socketio_server` is not imported
  - Properties can't be patched
- **Exact error**: `AttributeError: property 'auto_config_manager' of 'AutoConfigureCommand' object has no setter`
- **Root cause**: **Property can't be patched** + **no Socket.IO integration exists**
- **Fix category**: `DELETE_TEST`

#### Test 12: `test_event_emission_error_handling`
- **Line**: 551-584
- **Patch targets**:
  1. `patch("claude_mpm.cli.commands.auto_configure.get_socketio_server")` - not imported
  2. `patch.object(command, "auto_config_manager")` - **FAILS** (property)
- **What test expects**:
  - Socket.IO errors don't break workflow
  - `result.success` is True despite Socket.IO exceptions
- **Actual implementation**: No Socket.IO integration exists
- **Exact error**: `AttributeError: property 'auto_config_manager' of 'AutoConfigureCommand' object has no setter`
- **Root cause**: **Property can't be patched** + **no Socket.IO integration exists**
- **Fix category**: `DELETE_TEST`

---

## File 2: `tests/services/config_api/test_autoconfig_skill_deployment.py`

**17 tests total: 10 FAIL, 7 PASS**

### PASSING Tests (7)

| Test | Class | Why It Passes |
|---|---|---|
| `test_recommend_skills_with_valid_agents` | `TestSkillRecommendationLogic` | Calls `command._recommend_skills(preview)` directly - `_recommend_skills` exists and works correctly |
| `test_recommend_skills_with_no_agents` | `TestSkillRecommendationLogic` | Same - calls `_recommend_skills` directly |
| `test_recommend_skills_with_unmapped_agents` | `TestSkillRecommendationLogic` | Same - calls `_recommend_skills` directly |
| `test_recommend_skills_deduplication` | `TestSkillRecommendationLogic` | Same - calls `_recommend_skills` directly |
| `test_skill_deployment_path_resolution` | `TestSkillDeploymentIntegration` | Tests `resolve_skills_dir()` from `config_scope` module directly - no `AutoConfigureCommand` needed |
| `test_skill_deployment_directory_creation` | `TestSkillDeploymentIntegration` | Tests filesystem operations with `resolve_skills_dir()` directly |
| `test_cross_scope_skill_isolation` | `TestSkillDeploymentIntegration` | Tests filesystem operations with `resolve_skills_dir()` directly |

**Key insight**: All passing tests either (a) call `_recommend_skills` method directly (which is a plain method, not a property), or (b) test standalone functions from `config_scope` module.

---

### FAILING Tests: `TestSkillDeploymentExecution` (4 tests)

All 4 tests share the **identical root cause**: They attempt `patch.object(command, "skills_deployer")` but `skills_deployer` is a `@property` on `AutoConfigureCommand` (line 149-156) and cannot be patched on an instance via `patch.object`.

#### Test 1: `test_deploy_skills_success`
- **Line**: 136-155
- **Patch target**: `patch.object(command, "skills_deployer")`
- **What test expects**:
  - Can mock `skills_deployer` on instance
  - `command._deploy_skills(recommended_skills)` calls `skills_deployer.deploy_skills(skill_names=recommended_skills, force=False)`
  - Returns `{"deployed": [...], "errors": []}`
- **Actual implementation** (`auto_configure.py:900-915`):
  - `_deploy_skills` does exactly what the test expects functionally - BUT the property can't be patched on instances.
  - `skills_deployer` is `@property` at line 149-156
- **Exact error**: `AttributeError: property 'skills_deployer' of 'AutoConfigureCommand' object has no setter`
- **Root cause**: **Test patches property incorrectly** - should patch `command._skills_deployer` directly or use `PropertyMock`
- **Fix category**: `FIX_TEST` - The tested behavior IS correct; only the mock strategy is wrong

#### Test 2: `test_deploy_skills_partial_failure`
- **Line**: 157-172
- **Patch target**: `patch.object(command, "skills_deployer")`
- **Same root cause as Test 1**
- **Fix category**: `FIX_TEST`

#### Test 3: `test_deploy_skills_complete_failure`
- **Line**: 174-188
- **Patch target**: `patch.object(command, "skills_deployer")`
- **Same root cause as Test 1**
- **Fix category**: `FIX_TEST`

#### Test 4: `test_deploy_skills_with_force_parameter`
- **Line**: 190-206
- **Patch target**: `patch.object(command, "skills_deployer")`
- **Same root cause as Test 1**
- **Fix category**: `FIX_TEST`

---

### FAILING Tests: `TestCrossScopeSkillDeployment` (2 tests)

#### Test 5: `test_project_scope_skill_deployment`
- **Line**: 216-234
- **Patch target**: `patch.object(command, "skills_deployer")`
- **Same root cause** - property can't be patched on instance
- **Fix category**: `FIX_TEST`

#### Test 6: `test_user_scope_skill_deployment_fallback`
- **Line**: 236-254
- **Patch target**: `patch.object(command, "skills_deployer")`
- **Same root cause** - property can't be patched on instance
- **Fix category**: `FIX_TEST`

---

### FAILING Tests: `TestFullWorkflowSkillIntegration` (4 tests)

All 4 tests use `patch.object(command, "auto_config_manager", ...)` and/or `patch.object(command, "skills_deployer", ...)` which are both `@property` attributes.

#### Test 7: `test_full_workflow_with_skills_success`
- **Line**: 298-333
- **Patch targets**:
  1. `patch.object(command, "auto_config_manager", mock_services["auto_config"])` - **FAILS** (property)
  2. `patch.object(command, "skills_deployer", mock_services["skills_deployer"])` - **FAILS** (property)
- **What test expects**:
  - Full workflow: preview -> confirm -> deploy agents -> deploy skills -> success
  - `result.success` is True
  - Both `auto_configure` and `deploy_skills` are called
- **Actual implementation**: The logic IS correct but properties can't be patched
- **Exact error**: `AttributeError: property 'auto_config_manager' of 'AutoConfigureCommand' object has no setter`
- **Root cause**: **Test patches properties incorrectly**
- **Fix category**: `FIX_TEST` - Should set `command._auto_config_manager = mock` and `command._skills_deployer = mock` directly

#### Test 8: `test_full_workflow_agents_only`
- **Line**: 335-358
- **Patch targets**: Same property-patching issue
- **What test expects**:
  - With `agents_only=True`, skills deployment is skipped
  - `deploy_skills.assert_not_called()`
- **Root cause**: **Property patching**
- **Fix category**: `FIX_TEST`

#### Test 9: `test_full_workflow_skills_only`
- **Line**: 360-389
- **Patch targets**: Same property-patching issue
- **What test expects**:
  - With `skills_only=True`, agent deployment is skipped
  - `auto_configure.assert_not_called()`
  - `deploy_skills.assert_called_once()`
- **Root cause**: **Property patching**
- **Fix category**: `FIX_TEST`

#### Test 10: `test_full_workflow_skill_deployment_failure_handling`
- **Line**: 391-427
- **Patch targets**: Same property-patching issue
- **What test expects**:
  - Skills deployment fails -> overall result is failure
  - `result.success` is False, `result.exit_code` is 1
- **Root cause**: **Property patching**
- **Fix category**: `FIX_TEST`

---

## Summary: Root Cause Classification

### Root Cause 1: Missing `_emit_event` method (5 failures)
- **Location**: `RichProgressObserver` class
- **Details**: Tests expect a `_emit_event(event_name, event_data)` method that bridges observer callbacks to Socket.IO event emission. This method was never implemented.
- **Affected tests**: All 5 in `TestProgressObserverEvents`

### Root Cause 2: Missing `_emit_phase_event` method (5 failures)
- **Location**: `AutoConfigureCommand` class
- **Details**: Tests expect a `_emit_phase_event(phase_name, event_data)` method that emits phase-level Socket.IO events during workflow execution. This method was never implemented.
- **Affected tests**: All 5 in `TestAutoConfigurePhaseEvents`
- **Note**: 3 of these also hit the property-patching issue (RC-3) BEFORE they reach the missing method

### Root Cause 3: Property patching on instances (12 failures)
- **Location**: `AutoConfigureCommand.auto_config_manager` (line 118) and `AutoConfigureCommand.skills_deployer` (line 149)
- **Details**: Both are `@property` with lazy initialization via `_auto_config_manager` / `_skills_deployer` private attributes. Python's `patch.object()` cannot patch `@property` attributes on instances - it can only patch on the class or the test must set the backing attribute directly.
- **Affected tests**: All 10 in `test_autoconfig_skill_deployment.py` + 4 in `test_autoconfig_events.py`

### Root Cause 4: Missing imports/functions (`get_event_emitter`, `get_socketio_server`)
- **Location**: `auto_configure.py` module scope
- **Details**: Tests patch `claude_mpm.cli.commands.auto_configure.get_event_emitter` and `get_socketio_server` but these are never imported in the module.
- **Affected tests**: 3 in `TestAutoConfigurePhaseEvents` and `TestSocketIOEventIntegration`

---

## Fix Strategy by Category

### `DELETE_TEST` - 12 tests (all from `test_autoconfig_events.py`)

These test Socket.IO event emission features that were **designed but never implemented**:

| Test | Reason to Delete |
|---|---|
| `test_agent_deployment_started_event_structure` | Tests `_emit_event` - never built |
| `test_agent_deployment_progress_event_payload` | Tests `_emit_event` - never built |
| `test_agent_deployment_completed_success_event` | Tests `_emit_event` - never built |
| `test_agent_deployment_completed_failure_event` | Tests `_emit_event` - never built |
| `test_deployment_completed_summary_event` | Tests `_emit_event` - never built |
| `test_phase_0_toolchain_analysis_events` | Tests `_emit_phase_event` + `get_event_emitter` - never built |
| `test_phase_1_min_confidence_validation_events` | Tests `_emit_phase_event` - never built |
| `test_phase_2_skill_deployment_events` | Tests `_emit_phase_event` - never built |
| `test_phase_3_agent_archiving_events` | Tests `_emit_phase_event` - never built |
| `test_phase_4_configuration_completion_events` | Tests `_emit_phase_event` - never built |
| `test_full_workflow_event_sequence` | Tests Socket.IO integration - never built |
| `test_event_emission_error_handling` | Tests Socket.IO error handling - never built |

**Alternative**: If Socket.IO event emission is desired, these tests define the spec for what should be built (`FIX_BACKEND`). But building the feature is a separate task.

### `FIX_TEST` - 10 tests (all from `test_autoconfig_skill_deployment.py`)

These test **real, existing functionality** but use incorrect mocking strategy:

| Test | Fix Required |
|---|---|
| `test_deploy_skills_success` | Replace `patch.object(command, "skills_deployer")` with `command._skills_deployer = mock_deployer` |
| `test_deploy_skills_partial_failure` | Same fix |
| `test_deploy_skills_complete_failure` | Same fix |
| `test_deploy_skills_with_force_parameter` | Same fix |
| `test_project_scope_skill_deployment` | Same fix |
| `test_user_scope_skill_deployment_fallback` | Same fix |
| `test_full_workflow_with_skills_success` | Replace both `patch.object(command, "auto_config_manager")` with `command._auto_config_manager = mock` and `command._skills_deployer = mock` |
| `test_full_workflow_agents_only` | Same fix |
| `test_full_workflow_skills_only` | Same fix |
| `test_full_workflow_skill_deployment_failure_handling` | Same fix |

**Correct pattern** (example for `test_deploy_skills_success`):
```python
def test_deploy_skills_success(self, command):
    mock_deployer = Mock()
    mock_deployer.deploy_skills.return_value = {
        "deployed": ["python-testing", "react", "systematic-debugging"],
        "errors": [],
    }
    command._skills_deployer = mock_deployer  # Set backing attribute directly

    result = command._deploy_skills(recommended_skills)
    # ... assertions same as before
```

For full workflow tests, set both:
```python
command._auto_config_manager = mock_services["auto_config"]
command._skills_deployer = mock_services["skills_deployer"]
```

---

## Cross-Reference: Implementation Methods That Exist

| Method | Exists | Tested by Passing Tests? |
|---|---|---|
| `RichProgressObserver.__init__(console)` | Yes (line 46) | Yes (fixture) |
| `RichProgressObserver.on_agent_deployment_started(...)` | Yes (line 56) | No (tests fail due to `_emit_event`) |
| `RichProgressObserver.on_agent_deployment_progress(...)` | Yes (line 72) | No |
| `RichProgressObserver.on_agent_deployment_completed(...)` | Yes (line 79) | No |
| `RichProgressObserver.on_deployment_completed(...)` | Yes (line 91) | No |
| `RichProgressObserver._emit_event(...)` | **NO** | N/A |
| `AutoConfigureCommand.__init__()` | Yes (line 111) | Yes (fixture) |
| `AutoConfigureCommand.auto_config_manager` | Yes, `@property` (line 118) | Indirectly |
| `AutoConfigureCommand.skills_deployer` | Yes, `@property` (line 149) | Indirectly |
| `AutoConfigureCommand.run(args)` | Yes (line 176) | Attempted but blocked by property patching |
| `AutoConfigureCommand._recommend_skills(preview)` | Yes (line 875) | **Yes - 4 passing tests** |
| `AutoConfigureCommand._deploy_skills(skills)` | Yes (line 900) | Attempted but blocked by property patching |
| `AutoConfigureCommand._archive_agents(agents)` | Yes (line 960) | Attempted but blocked by `_emit_phase_event` |
| `AutoConfigureCommand._show_restart_notification(...)` | Yes (line 1016) | Attempted but blocked by `_emit_phase_event` |
| `AutoConfigureCommand._emit_phase_event(...)` | **NO** | N/A |
| `get_event_emitter()` | **NO** (not in auto_configure.py) | N/A |
| `get_socketio_server()` | **NO** (not in auto_configure.py) | N/A |

---

## Additional Notes

### Property vs Direct Attribute Pattern

The `AutoConfigureCommand` uses a common Python pattern for lazy-loaded dependencies:

```python
class AutoConfigureCommand(BaseCommand):
    def __init__(self):
        self._auto_config_manager = None   # Private backing attribute
        self._skills_deployer = None       # Private backing attribute

    @property
    def auto_config_manager(self):         # Public property accessor
        if self._auto_config_manager is None:
            self._auto_config_manager = AutoConfigManagerService(...)
        return self._auto_config_manager

    @property
    def skills_deployer(self):             # Public property accessor
        if self._skills_deployer is None:
            self._skills_deployer = SkillsDeployerService()
        return self._skills_deployer
```

**Why `patch.object(command, "skills_deployer")` fails**: `patch.object` on an instance tries to `setattr` the property name, which Python rejects because there's no setter defined. The correct approach is to set the **backing attribute** (`command._skills_deployer = mock`) since the property getter will return it.

### Full Workflow Tests: Additional Concerns

Even if the property patching is fixed for `test_full_workflow_*` tests, they may encounter additional issues:
1. The `run()` method calls `self.setup_logging(args)` which requires `args` to have `debug`, `verbose`, `quiet` attributes
2. The `_review_project_agents()` call tries to access filesystem paths (`~/.claude-mpm/cache/agents`)
3. The `_confirm_deployment()` call tries to read from stdin (but `skip_confirmation=True` / `yes=True` should bypass this)

These issues would need to be addressed in the test fixes (likely by patching `_review_project_agents` to return `None`).
