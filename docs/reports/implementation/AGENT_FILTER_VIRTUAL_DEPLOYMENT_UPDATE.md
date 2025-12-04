# Agent Filter Virtual Deployment State Detection - Implementation Summary

## Overview
Updated `get_deployed_agent_ids()` in `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/agent_filters.py` to check virtual deployment state (`.mpm_deployment_state` files) in addition to physical `.md` files. This fixes the checkbox interface in configure showing all agents as "○ [Available]" when they should be "● [Installed]".

## Problem
- The checkbox interface uses `get_deployed_agent_ids()` to determine which agents are deployed
- The old implementation only checked for physical `.md` files
- Virtual deployments tracked in `.mpm_deployment_state` were not detected
- This caused all agents to show as "○ [Available]" even when deployed

## Solution
Updated `get_deployed_agent_ids()` to:
1. **Check virtual deployment state FIRST** (primary method)
   - Reads `.claude/agents/.mpm_deployment_state` in project directory
   - Reads `~/.claude/agents/.mpm_deployment_state` in user home (only when using default project dir)
   - Parses JSON and extracts agent IDs from `last_check_results.agents`

2. **Check physical files** (fallback/backward compatibility)
   - `.claude-mpm/agents/*.md` (new architecture)
   - `.claude/agents/*.md` (legacy architecture)
   - `~/.claude/agents/*.md` (user-level, only when using default project dir)

3. **Combine both detection methods**
   - Returns set of all deployed agent IDs (leaf names)
   - No duplicates (set ensures uniqueness)
   - Graceful error handling for malformed state files

## Key Changes

### Detection Priority
```python
# NEW: Virtual deployment state (primary)
deployment_state_paths = [
    project_dir / ".claude" / "agents" / ".mpm_deployment_state",
]

# Only check user-level state if using default project directory
if not explicit_project_dir:
    deployment_state_paths.append(
        Path.home() / ".claude" / "agents" / ".mpm_deployment_state"
    )

# Parse JSON and extract agent IDs
agents = state.get("last_check_results", {}).get("agents", {})
deployed.update(agents.keys())

# EXISTING: Physical files (fallback)
# ... check .md files in various directories
```

### Test Isolation Fix
- Added `explicit_project_dir` flag to track if `project_dir` was provided
- Only checks user-level directories (`~/.claude/agents/`) when using default project directory
- This prevents test isolation issues where tests would read actual deployment state

### Error Handling
- Gracefully handles malformed JSON files
- Continues checking other paths if one fails
- Logs errors at debug level without breaking functionality

## Test Coverage

### New Tests Added (3)
1. **test_virtual_deployment_state_detection**: Verifies agents in `.mpm_deployment_state` are detected
2. **test_virtual_and_physical_combined**: Verifies both virtual and physical agents are detected together
3. **test_malformed_deployment_state_graceful**: Verifies malformed state files don't break detection

### Existing Tests (All Pass - 38 total)
- All previous tests continue to pass
- Test isolation works correctly with explicit `project_dir`

## Benefits

### User Experience
✅ Checkbox interface correctly shows agents as "● [Installed]" when deployed virtually
✅ Agents deployed via `.mpm_deployment_state` are properly recognized
✅ Backward compatible with physical file deployments

### Architecture
✅ Matches detection logic from `_is_agent_deployed()` in `agent_state_manager.py`
✅ Supports both old (physical files) and new (virtual state) deployment methods
✅ Single source of truth via `.mpm_deployment_state` (primary)
✅ Graceful fallback to physical files for backward compatibility

### Testing
✅ All 38 tests pass (35 existing + 3 new)
✅ Test isolation properly maintained
✅ Error handling verified with malformed state file test

## Related Files

### Modified
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/agent_filters.py`
  - Updated `get_deployed_agent_ids()` function (lines 83-188)

### Test Files
- `/Users/masa/Projects/claude-mpm/tests/test_agent_filters.py`
  - Added 3 new tests (lines 282-365)

### Related Code
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/agent_state_manager.py`
  - Reference implementation: `_is_agent_deployed()` (lines 265-310)

## Documentation Updates

### Docstring Improvements
- Updated function docstring with clear design rationale
- Added examples for both virtual and physical detection
- Documented related tickets and fixes
- Explained test isolation behavior

### Code Comments
- Added clear section markers: "NEW:" and "EXISTING:"
- Explained why user-level checks are conditional
- Documented agent ID format (leaf names)
- Added error handling explanations

## Verification

### Test Results
```bash
$ python -m pytest tests/test_agent_filters.py -v
38 passed in 0.15s
```

### Success Criteria Met
✅ Function returns agent IDs from virtual deployment state
✅ Function still returns agent IDs from physical files
✅ Checkbox interface shows agents as "● [Installed]" when deployed
✅ All existing tests pass (no regressions)
✅ No duplicate agent IDs in returned set
✅ Graceful error handling for malformed state files
✅ Test isolation maintained

## Implementation Notes

### Agent ID Format
- Virtual state uses **leaf names**: `"python-engineer"`, `"qa"`, `"gcp-ops"`
- Physical files use **stem names**: `"ENGINEER"`, `"PM"`, `"QA"`
- Both formats supported in returned set
- Checkbox comparison works: `agent_leaf_name in deployed_ids`

### Path Priority
1. `{project_dir}/.claude/agents/.mpm_deployment_state` (project-level virtual)
2. `~/.claude/agents/.mpm_deployment_state` (user-level virtual, conditional)
3. `{project_dir}/.claude-mpm/agents/*.md` (project-level new arch)
4. `{project_dir}/.claude/agents/*.md` (project-level legacy arch)
5. `~/.claude/agents/*.md` (user-level, conditional)

### Error Handling Strategy
- JSON parsing errors: Log and continue to next path
- Missing files: Skip silently (expected)
- Malformed state: Continue to physical file detection
- No exceptions propagated to caller

## Migration Impact

### Backward Compatibility
- ✅ Existing physical file detection still works
- ✅ No breaking changes to function signature
- ✅ No breaking changes to return type
- ✅ All existing code continues to work

### Future Considerations
- Virtual deployment state is now the **primary** detection method
- Physical files remain as **fallback** for backward compatibility
- Consider deprecating physical file support in future version
- `.mpm_deployment_state` is the single source of truth going forward

## Related Tickets
- **1M-502**: Virtual deployment state detection
- Agent status detection issue documented in `/Users/masa/Projects/claude-mpm/docs/research/agent-status-detection-issue-2025-12-02.md`

## Conclusion
Successfully updated `get_deployed_agent_ids()` to support both virtual deployment state (primary) and physical files (fallback), fixing the checkbox interface issue while maintaining backward compatibility and test isolation.
