# Hook Routing Regression Test

## Overview

This test suite prevents regression of the hook routing logic fix in the Socket.IO event system.

## The Bug

Previously, the hook routing logic in `ConnectionEventHandler.claude_event()` used exact string matching:

```python
# BROKEN - exact match
if event_type == "hook":
    # Route to HookEventHandler
```

This caused hook events with types like `hook.user_prompt`, `hook.pre_tool`, and `hook.post_tool` to NOT be routed to the `HookEventHandler`, breaking the hook system integration with the dashboard.

## The Fix

The logic was changed to use prefix matching:

```python
# FIXED - prefix match
if isinstance(event_type, str) and event_type.startswith("hook."):
    # Route to HookEventHandler
```

This ensures that all hook events with the `hook.` prefix are properly routed to the `HookEventHandler`.

## Test Coverage

### Regression Tests (`TestHookRoutingRegression`)
- ✅ Hook events with prefixes like `hook.user_prompt` ARE routed to HookEventHandler
- ✅ Events with exactly `hook` type are NOT routed (they're not real hook events)
- ✅ Non-hook events are not routed to HookEventHandler
- ✅ Edge cases are handled gracefully (empty type, non-string type, missing type, etc.)
- ✅ Missing HookEventHandler is handled gracefully
- ✅ Missing event_registry is handled gracefully
- ✅ The exact `startswith()` logic is tested directly

### Integration Tests (`TestHookRoutingIntegration`)
- ✅ Real HookEventHandler instances process events correctly
- ✅ Different hook event types are processed with correct event names
- ✅ Events are properly stored in history with correct format

## Running the Tests

### Run all hook routing tests:
```bash
python -m pytest tests/socketio/test_hook_routing_regression.py -v
```

### Run only regression tests:
```bash
python -m pytest tests/socketio/test_hook_routing_regression.py -m "regression" -v
```

### Run only integration tests:
```bash
python -m pytest tests/socketio/test_hook_routing_regression.py -m "integration" -v
```

### Use the convenience script:
```bash
./scripts/test_hook_routing_regression.sh
```

## Test Markers

The tests use pytest markers for organization:

- `@pytest.mark.regression` - Regression tests to prevent the bug from reoccurring
- `@pytest.mark.integration` - Integration tests with real handler instances  
- `@pytest.mark.socketio` - Socket.IO related tests
- `@pytest.mark.hook` - Hook system tests

## Hook Event Types Tested

The tests verify routing for these common hook event types:

- `hook.user_prompt` - User input prompts
- `hook.pre_tool` - Before tool execution
- `hook.post_tool` - After tool execution  
- `hook.subagent_start` - When a subagent starts
- `hook.subagent_stop` - When a subagent stops
- `hook.custom_event` - Custom hook events

## Key Edge Cases Covered

- Empty event type: `{"type": "", ...}`
- Non-string type: `{"type": 123, ...}`
- Missing type: `{"data": {...}}`
- Exact "hook" type: `{"type": "hook", ...}` (should NOT be routed)
- Case sensitivity: `{"type": "Hook.user_prompt", ...}` (should NOT be routed)
- Missing event data: `{}`
- Non-dict event data: `"not a dict"`

## CI/CD Integration

This test is part of the Socket.IO test suite and runs automatically:

- In local development via `pytest`
- In CI/CD pipelines
- As part of the full test suite: `./scripts/run_all_tests.sh`
- As part of Socket.IO tests: `python -m pytest tests/socketio/ -v`

## Importance

This regression test is **CRITICAL** because:

1. **Hook System Integration**: Without proper routing, hook events don't reach the dashboard
2. **Real-Time Monitoring**: The dashboard relies on hook events to show Claude activity
3. **Session Tracking**: Hook events provide session start/stop information
4. **Tool Monitoring**: Pre/post tool events enable tool usage tracking
5. **Agent Delegation**: Subagent start/stop events track delegation flow

## Test Structure

```
tests/socketio/test_hook_routing_regression.py
├── TestHookRoutingRegression (Unit tests with mocks)
│   ├── test_hook_event_routing_with_prefix()
│   ├── test_exact_hook_not_routed()
│   ├── test_non_hook_events_not_routed()
│   ├── test_edge_cases()
│   ├── test_hook_routing_logic_startswith()
│   ├── test_missing_hook_handler_graceful_failure()
│   └── test_missing_event_registry_graceful_failure()
└── TestHookRoutingIntegration (Integration tests with real handlers)
    ├── test_real_hook_handler_integration()
    └── test_hook_event_types_processing()
```

## Developer Notes

When modifying the hook routing logic:

1. **Always run this test first**: Ensure your changes don't break hook routing
2. **Update tests if needed**: If you change the routing logic, update the tests accordingly
3. **Add new test cases**: If you find new edge cases, add them to the test suite
4. **Test manually**: Use the dashboard to verify hook events appear in real-time

## Related Files

- `src/claude_mpm/services/socketio/handlers/connection.py` - Contains the hook routing logic
- `src/claude_mpm/services/socketio/handlers/hook.py` - HookEventHandler implementation
- `scripts/test_hook_routing_regression.sh` - Convenience script to run these tests
- `tests/socketio/test_event_flow.py` - General Socket.IO event flow tests