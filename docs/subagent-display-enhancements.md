# Subagent Display Enhancements

## Overview
Enhanced the dashboard's event viewer to properly display subagent_start and subagent_stop events with robust handling of agent types and various data structures.

## Changes Made

### 1. Enhanced Event Viewer (`src/claude_mpm/dashboard/static/js/components/event-viewer.js`)

#### Added Agent Type Formatting Helper
- New `formatAgentType()` method that properly formats agent type strings
- Maps common agent type patterns to display-friendly names
- Handles variations like "research", "research_agent", "Research Agent"
- Provides intelligent fallback for unknown agent types

#### Enhanced Subagent Start Display
- **Lines 412-416**: Improved `subagent_start` handling in `formatEventData()`
  - Tries multiple field locations: `agent_type`, `agent`, `subagent_type`
  - Handles alternative prompt fields: `prompt`, `description`, `task`
  - Properly formats agent type using new helper method
  - Truncates long prompts to 60 characters

#### Enhanced Subagent Stop Display  
- **Lines 418-422**: Improved `subagent_stop` handling
  - Tries multiple field locations for agent type
  - Handles alternative reason fields: `reason`, `stop_reason`
  - Shows task completion status with ✓ or ✗ icons
  - Extracts completion status from `structured_response.task_completed`

#### Enhanced Single-Row Display
- **Lines 507-520**: Improved single-row format for both events
  - Consistent agent type display in collapsed view
  - Shows prompt/description preview
  - Includes completion status indicators
  - Proper truncation for long text

#### Event Categorization
- **Lines 653-654**: Ensures subagent events are properly categorized as "agent_delegation"

### 2. Data Flow Verification

#### Event Handlers (`src/claude_mpm/hooks/claude_hooks/event_handlers.py`)
- Verified `handle_pre_tool_fast()` properly emits `subagent_start` with `agent_type`
- Verified `handle_subagent_stop_fast()` includes `agent_type` in event data
- Both handlers include comprehensive data for proper display

## Robust Fallback Handling

The implementation handles multiple edge cases:

1. **Missing Agent Type**: Falls back to "Unknown" when no agent type field is present
2. **Alternative Field Names**: Checks `agent_type`, `agent`, and `subagent_type` fields
3. **Alternative Prompt Fields**: Checks `prompt`, `description`, and `task` fields  
4. **Alternative Reason Fields**: Checks `reason` and `stop_reason` fields
5. **Long Text Truncation**: Automatically truncates long prompts/descriptions
6. **Task Completion Status**: Shows visual indicators (✓/✗) when available
7. **Custom Agent Types**: Properly capitalizes and formats non-standard agent types
8. **Empty Data**: Provides sensible defaults for missing data

## Agent Type Mapping

The `formatAgentType()` method maps common patterns:
- `research` → "Research"
- `architect` → "Architect"
- `engineer` → "Engineer"
- `qa` → "QA"
- `pm` / `project_manager` → "PM"
- Custom types → Properly capitalized

## Testing

Created comprehensive test scripts:

1. **`scripts/test_subagent_display_simple.py`**
   - Tests basic subagent event display
   - Covers all standard agent types
   - Verifies proper formatting and display

2. **`scripts/test_subagent_edge_cases.py`**
   - Tests edge cases and fallback handling
   - Missing fields, alternative field names
   - Long text truncation
   - Task completion status
   - Custom agent types

3. **`scripts/test_subagent_events_comprehensive.py`**
   - Comprehensive test with various data structures
   - Multiple test cases for each agent type
   - Tests all fallback scenarios

## Visual Improvements

The enhanced display now shows:
- **Agent Type**: Properly formatted and always visible
- **Task Description**: Truncated preview of the task/prompt
- **Completion Status**: Visual indicators (✓/✗) for task completion
- **Consistent Format**: Both expanded and collapsed views show agent information

## Benefits

1. **Better Visibility**: Users can immediately see which agent is being invoked
2. **Robust Handling**: Works with various data structures and field names
3. **Graceful Fallbacks**: Never breaks, always shows meaningful information
4. **Visual Feedback**: Clear indicators for task success/failure
5. **Consistent UX**: Uniform display across different event sources