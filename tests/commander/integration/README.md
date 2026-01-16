# Commander Integration Tests

Phase 2 integration tests validating end-to-end system behavior.

## Overview

These integration tests verify that all Commander Phase 2 components work together correctly:

- **Daemon lifecycle** - Start, stop, signal handling, state persistence
- **Project workflows** - Full lifecycle from registration to completion
- **Work execution** - Queue management, priority ordering, dependencies
- **Event handling** - Event creation, resolution, pause/resume
- **State persistence** - Recovery after daemon restarts
- **API integration** - REST endpoints with real components

## Running Tests

### Run all integration tests

```bash
pytest tests/commander/integration/ -v
```

### Run specific test modules

```bash
# Daemon lifecycle tests
pytest tests/commander/integration/test_daemon_lifecycle.py -v

# Project workflow tests
pytest tests/commander/integration/test_project_workflow.py -v

# Work execution tests
pytest tests/commander/integration/test_work_execution.py -v

# Persistence/recovery tests
pytest tests/commander/integration/test_persistence_recovery.py -v

# API integration tests
pytest tests/commander/integration/test_api_integration.py -v
```

### Run by markers

```bash
# All integration tests
pytest -m integration

# Only slow tests
pytest -m slow

# Integration tests excluding slow tests
pytest -m "integration and not slow"
```

### Filter by test name

```bash
# Tests related to daemon restart
pytest -k "restart" tests/commander/integration/

# Tests for event handling
pytest -k "event" tests/commander/integration/

# Tests for work queue
pytest -k "work" tests/commander/integration/
```

## Test Structure

### `conftest.py`

Shared fixtures for all integration tests:

- `integration_tmp_path` - Isolated temporary directory
- `integration_config` - Test-friendly daemon configuration
- `daemon_lifecycle` - Managed daemon instance with auto-cleanup
- `sample_project` - Single project for testing
- `multiple_projects` - Multiple projects for concurrency tests

### `test_daemon_lifecycle.py`

Tests daemon lifecycle management:

- ✓ Daemon startup initializes all subsystems
- ✓ Graceful shutdown saves state and cleans up
- ✓ Signal handling (SIGTERM, SIGINT)
- ✓ State recovery after restart (projects, sessions, events)
- ✓ Corrupt file handling
- ✓ Periodic state persistence
- ✓ Idempotent shutdown

### `test_project_workflow.py`

Tests complete project workflows:

- ✓ Full lifecycle: register → start → work → complete
- ✓ Multiple concurrent projects
- ✓ Project isolation (events, work queues)
- ✓ Session state transitions
- ✓ Event workflow (create, resolve, cleanup)
- ✓ Work priority ordering
- ✓ Work dependencies
- ✓ State persistence across restarts

### `test_work_execution.py`

Tests work queue execution:

- Work queue to execution flow
- Dependency chain execution
- Blocking event pauses work
- Resume after event resolution
- Work failure handling
- Multiple work items in sequence
- Priority preemption
- Work state persistence
- Work cancellation
- Informational events don't block

### `test_persistence_recovery.py`

Tests state persistence and recovery:

- ✓ Projects recovered after restart
- ✓ Pending events recovered
- Work queue state recovery (TODO: implement WorkQueue persistence)
- ✓ Corrupt file handling (projects, sessions, events)
- ✓ Missing file handling
- ✓ Atomic file writes
- ✓ Periodic persistence interval
- ✓ Session state persistence (pane, pause_reason)
- ✓ Resolved events not persisted (only pending)

### `test_api_integration.py`

Tests REST API with real components:

- ✓ Health check endpoint
- Project CRUD via registry
- Event creation and resolution
- Work queue operations
- Session lifecycle
- Inbox operations
- Concurrent operations on multiple projects
- Error handling
- State consistency
- Pagination support
- Filter by state

## Known Issues

### Work Queue Tests

Some work execution tests may fail because they attempt to complete work items without calling `queue.start()` first. The WorkQueue API requires:

```python
# Correct workflow
work = queue.add("Task", WorkPriority.HIGH)
queue.start(work.id)  # Must start before completing
queue.complete(work.id, "Result")
```

Not:

```python
# This will fail
work = queue.add("Task", WorkPriority.HIGH)
queue.complete(work.id, "Result")  # Error: not IN_PROGRESS
```

### API Tests

API integration tests use the daemon/registry/event_manager directly rather than making HTTP requests through TestClient. This is intentional for Phase 2 - full HTTP API testing will be added in Phase 3.

### Event Types

Tests use the Phase 2 event model:
- `EventType.APPROVAL` - Blocking events (not BLOCKING)
- `EventType.STATUS` - Informational events (not INFORMATIONAL)
- `EventStatus` - Event lifecycle status (not EventState)

## Test Configuration

All tests use test-friendly configuration:

```python
DaemonConfig(
    host="127.0.0.1",
    port=18765,  # Test port to avoid conflicts
    log_level="DEBUG",
    state_dir=tmp_path / "state",  # Isolated temp directory
    poll_interval=0.1,  # Fast polling for responsive tests
    save_interval=5,  # Frequent saves for testing recovery
)
```

## Markers

Tests are marked for categorization:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.slow` - Tests taking >1s (periodic persistence, restarts)
- `@pytest.mark.asyncio` - Async tests (all integration tests)

## Fixtures

### Common Patterns

**Basic daemon test:**

```python
async def test_something(daemon_lifecycle: CommanderDaemon):
    # daemon_lifecycle is already started and will auto-cleanup
    daemon_lifecycle.registry.register(...)
    # test logic
    # daemon stops automatically after test
```

**Project-based test:**

```python
async def test_project(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project
    # test logic with project
```

**Multi-project test:**

```python
async def test_multiple(
    daemon_lifecycle: CommanderDaemon,
    multiple_projects: list[Project],
):
    for project in multiple_projects:
        daemon_lifecycle.registry._projects[project.id] = project
    # test logic
```

## Debugging Failed Tests

### Enable verbose logging

```bash
pytest tests/commander/integration/ -vv --log-cli-level=DEBUG
```

### Show full stack traces

```bash
pytest tests/commander/integration/ --tb=long
```

### Stop on first failure

```bash
pytest tests/commander/integration/ -x
```

### Run with pdb on failure

```bash
pytest tests/commander/integration/ --pdb
```

### Capture and display output

```bash
pytest tests/commander/integration/ -s  # Don't capture stdout
pytest tests/commander/integration/ --capture=no  # Same as -s
```

## Adding New Tests

### Template for new integration test

```python
import pytest
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project


@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_feature(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test description."""
    # Arrange
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Act
    # ... test logic ...

    # Assert
    assert expected_condition
```

### Guidelines

1. Use descriptive test names: `test_<feature>_<scenario>`
2. Include docstrings explaining what is tested
3. Use appropriate fixtures (`daemon_lifecycle`, `sample_project`, etc.)
4. Mark slow tests: `@pytest.mark.slow`
5. Clean assertions with clear failure messages
6. Test both happy path and error cases

## CI/CD Integration

Integration tests are designed to run in CI:

- No external dependencies (all mocked)
- Isolated state directories (no conflicts)
- Fast execution (<30s for full suite)
- Clear failure messages
- Deterministic (no flaky tests)

### Example CI configuration

```yaml
test-integration:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install -e .[dev]
    - run: pytest tests/commander/integration/ -v --tb=short
```

## Coverage

Integration tests provide coverage for:

- ✓ Daemon startup/shutdown
- ✓ Project registration/lifecycle
- ✓ Session management
- ✓ Work queue operations
- ✓ Event system
- ✓ State persistence
- ✓ Error handling
- ✓ Recovery scenarios

Not covered (requires Phase 3):
- Actual tmux interactions
- Real Claude Code execution
- Full HTTP API requests
- WebSocket connections
- UI interactions

## Related Documentation

- [Usage Guide](../../../docs/commander/usage-guide.md) - User-facing documentation
- [API Reference](../../../docs/commander/api-reference.md) - REST API documentation
- [Architecture](../../../docs/commander/architecture.md) - System design
- [Testing Guide](../../../docs/commander/testing-guide.md) - Testing best practices
