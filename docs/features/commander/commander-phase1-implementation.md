# MPM Commander Phase 1 Implementation

**Issue**: #170 - Project Registry Implementation
**Status**: ✅ Complete
**Tests**: 38 tests, all passing

## Overview

Phase 1 implements the core Project Registry for managing multiple projects with isolated state, work queues, and tool sessions. This provides the foundation for multi-project orchestration.

## Implementation

### Files Created

#### Models (`src/claude_mpm/commander/models/`)

1. **`__init__.py`** - Module exports
2. **`project.py`** - Core data models:
   - `ProjectState` - Enum with 5 states (IDLE, WORKING, BLOCKED, PAUSED, ERROR)
   - `ToolSession` - Tool runtime session (Claude Code, Aider, etc.)
   - `ThreadMessage` - Conversation thread message
   - `Project` - Main state container with:
     - UUID identifier
     - Path and name
     - State machine
     - Session tracking
     - Work queue (Phase 3)
     - Event queues (Phase 2)
     - Conversation thread
     - Activity timestamps

3. **`events.py`** - Placeholder for Phase 2 event models

#### Core Modules (`src/claude_mpm/commander/`)

1. **`registry.py`** - `ProjectRegistry` class:
   - Thread-safe with `threading.RLock`
   - UUID-based project IDs
   - Dual indexing (by ID and path)
   - CRUD operations:
     - `register(path, name)` - Add project
     - `unregister(project_id)` - Remove project
     - `get(project_id)` - Lookup by ID
     - `get_by_path(path)` - Lookup by path
     - `list_all()` - List all projects
     - `list_by_state(state)` - Filter by state
   - State management:
     - `update_state(project_id, state, reason)`
   - Session management:
     - `add_session(project_id, session)`
     - `remove_session(project_id, session_id)`
   - Activity tracking:
     - `touch(project_id)` - Update last_activity

2. **`config_loader.py`** - `load_project_config()` function:
   - Loads `.claude-mpm/configuration.yaml`
   - Detects subdirectories:
     - `agents/`
     - `skills/`
     - `memories/`
   - Returns config dict or None
   - YAML parsing with error handling

3. **`__init__.py`** - Updated to export new components

#### Tests (`tests/commander/`)

1. **`test_project_registry.py`** - 26 tests:
   - Registration validation (valid/invalid paths)
   - Duplicate path detection
   - Unregistration
   - Lookup operations (by ID and path)
   - Listing and filtering by state
   - State updates with reasons
   - Session management (add/remove)
   - Activity tracking (touch)
   - Thread safety (concurrent access)

2. **`test_config_loader.py`** - 12 tests:
   - No config directory
   - Empty config directory
   - YAML file parsing
   - Directory detection (agents, skills, memories)
   - Malformed YAML error handling
   - Empty YAML files
   - File vs directory handling
   - Unicode support

## Usage Example

```python
from claude_mpm.commander import (
    ProjectRegistry,
    ProjectState,
    ToolSession,
    load_project_config,
)

# Create registry
registry = ProjectRegistry()

# Register project
project = registry.register("/path/to/project", name="My Project")
# Returns: Project(id='uuid', path='...', name='My Project', state=IDLE)

# Load configuration
config = load_project_config("/path/to/project")
# Returns: {'configuration': {...}, 'has_agents': True, ...}

# Update state
registry.update_state(
    project.id,
    ProjectState.WORKING,
    reason="Processing ticket #123"
)

# Add tool session
session = ToolSession(
    id="sess-1",
    project_id=project.id,
    runtime="claude-code",
    tmux_target="commander:proj-cc"
)
registry.add_session(project.id, session)

# Query projects
working_projects = registry.list_by_state(ProjectState.WORKING)
found = registry.get_by_path("/path/to/project")
```

## Key Features

### Thread Safety
- All operations protected by `threading.RLock`
- Concurrent registration verified with 5 threads
- Concurrent state updates tested with 500 operations
- Concurrent session management tested with 150 add/remove cycles

### Validation
- Path existence and type validation
- Duplicate path prevention (raises `ValueError`)
- Invalid ID detection (raises `KeyError`)
- Proper exception chaining with `raise ... from err`

### Performance
- Dual indexing for O(1) lookup by ID and path
- Path normalization with `Path.resolve()`
- Minimal locking scope for high concurrency

### Configuration Loading
- Graceful handling of missing `.claude-mpm/` directory
- YAML parsing with `yaml.safe_load()`
- Directory detection with `Path.exists()` and `Path.is_dir()`
- Unicode support verified

## Project State Machine

```
IDLE ──────────────┐
  ↑                ↓
  │            WORKING
  │                ↓
  │            BLOCKED ←──┐
  │                ↓      │
  └────────── PAUSED      │
                  ↓       │
              ERROR ──────┘
```

- **IDLE**: No pending work
- **WORKING**: Executing work item
- **BLOCKED**: Waiting on human input
- **PAUSED**: Manually paused
- **ERROR**: Unrecoverable error

## Test Results

```bash
$ pytest tests/commander/test_project_registry.py tests/commander/test_config_loader.py -v

============================= test session starts ==============================
collected 38 items

test_project_registry.py::...::test_register_valid_path PASSED           [  2%]
test_project_registry.py::...::test_register_with_custom_name PASSED     [  5%]
test_project_registry.py::...::test_register_invalid_path_not_exists PASSED [  7%]
test_project_registry.py::...::test_register_invalid_path_not_directory PASSED [ 10%]
test_project_registry.py::...::test_register_duplicate_path PASSED       [ 13%]
test_project_registry.py::...::test_unregister_success PASSED            [ 15%]
test_project_registry.py::...::test_unregister_invalid_id PASSED         [ 18%]
test_project_registry.py::...::test_get_by_id PASSED                     [ 21%]
test_project_registry.py::...::test_get_by_path PASSED                   [ 23%]
test_project_registry.py::...::test_get_by_path_invalid PASSED           [ 26%]
test_project_registry.py::...::test_list_all_empty PASSED                [ 28%]
test_project_registry.py::...::test_list_all_multiple PASSED             [ 31%]
test_project_registry.py::...::test_list_by_state PASSED                 [ 34%]
test_project_registry.py::...::test_update_state_success PASSED          [ 36%]
test_project_registry.py::...::test_update_state_invalid_id PASSED       [ 39%]
test_project_registry.py::...::test_update_state_without_reason PASSED   [ 42%]
test_project_registry.py::...::test_add_session PASSED                   [ 44%]
test_project_registry.py::...::test_add_session_invalid_project PASSED   [ 47%]
test_project_registry.py::...::test_remove_session PASSED                [ 50%]
test_project_registry.py::...::test_remove_session_invalid_project PASSED [ 52%]
test_project_registry.py::...::test_remove_session_invalid_session PASSED [ 55%]
test_project_registry.py::...::test_touch PASSED                         [ 57%]
test_project_registry.py::...::test_touch_invalid_project PASSED         [ 60%]
test_project_registry.py::...::test_concurrent_registration PASSED       [ 63%]
test_project_registry.py::...::test_concurrent_state_updates PASSED      [ 65%]
test_project_registry.py::...::test_concurrent_session_management PASSED [ 68%]
test_config_loader.py::...::test_no_config_directory PASSED              [ 71%]
test_config_loader.py::...::test_empty_config_directory PASSED           [ 73%]
test_config_loader.py::...::test_load_configuration_yaml PASSED          [ 76%]
test_config_loader.py::...::test_detect_agents_directory PASSED          [ 78%]
test_config_loader.py::...::test_detect_skills_directory PASSED          [ 81%]
test_config_loader.py::...::test_detect_memories_directory PASSED        [ 84%]
test_config_loader.py::...::test_detect_all_directories PASSED           [ 86%]
test_config_loader.py::...::test_full_config_with_all_features PASSED    [ 89%]
test_config_loader.py::...::test_malformed_yaml_raises_error PASSED      [ 92%]
test_config_loader.py::...::test_empty_yaml_file PASSED                  [ 94%]
test_config_loader.py::...::test_file_as_directory PASSED                [ 97%]
test_config_loader.py::...::test_unicode_in_config PASSED                [100%]

============================== 38 passed in 0.17s ==============================
```

## Next Steps

### Phase 2: Event System
- Implement `Event` model in `models/events.py`
- Add event processing to `ProjectRegistry`
- Event history tracking
- Event-driven state transitions

### Phase 3: Work Queue
- Implement `WorkItem` model
- Queue management operations
- Work item execution lifecycle
- Completion tracking

### Phase 4: Integration
- Flask API endpoints for registry
- WebSocket event streaming
- CLI commands for project management
- UI dashboard for multi-project view

## Files Modified

- `src/claude_mpm/commander/__init__.py` - Added new exports
- `src/claude_mpm/commander/models/__init__.py` - New file
- `src/claude_mpm/commander/models/project.py` - New file
- `src/claude_mpm/commander/models/events.py` - New file (placeholder)
- `src/claude_mpm/commander/registry.py` - New file
- `src/claude_mpm/commander/config_loader.py` - New file
- `tests/commander/__init__.py` - New file
- `tests/commander/test_project_registry.py` - New file (26 tests)
- `tests/commander/test_config_loader.py` - New file (12 tests)

## LOC Delta

- **Added**: ~650 lines (implementation + tests)
- **Removed**: 0 lines
- **Net Change**: +650 lines

Breakdown:
- Models: ~150 lines
- Registry: ~200 lines
- Config loader: ~100 lines
- Tests: ~200 lines

## Dependencies

No new dependencies added. Uses standard library:
- `dataclasses` - Data models
- `datetime` - Timestamps
- `enum` - ProjectState enum
- `pathlib` - Path operations
- `threading` - Thread safety (RLock)
- `uuid` - Project IDs
- `yaml` - Configuration parsing (already in project)
- `logging` - Structured logging

## Documentation

- Comprehensive docstrings with examples
- Type hints for all functions and methods
- Inline comments for complex logic
- This implementation document
