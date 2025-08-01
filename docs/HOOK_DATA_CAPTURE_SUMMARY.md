# Hook Data Capture Summary

## Overview

The Claude MPM monitoring system now captures comprehensive data from all Claude Code hook events, with special enhancements for agent delegations and PM interactions.

## Captured Hook Events

### 1. User Prompts (`hook.user_prompt`)
- **prompt_text**: Full text of user's prompt
- **prompt_preview**: First 200 characters for quick viewing
- **session_id**: Unique session identifier
- **is_command**: Whether prompt starts with `/`
- **contains_code**: Detects code blocks or programming language mentions
- **urgency**: Inferred from keywords (urgent, error, bug, fix, broken)

### 2. Pre-Tool Events (`hook.pre_tool`)
- **tool_name**: Name of the tool being invoked
- **operation_type**: Classification (read, write, execute, network, task_management, delegation, etc.)
- **tool_parameters**: Extracted parameters specific to each tool
- **is_delegation**: Boolean flag for Task tool invocations
- **security_risk**: Risk assessment (low, medium, high)

#### Special Task Tool Parameters
When `tool_name` is "Task" (agent delegations):
- **subagent_type**: Type of agent (research, engineer, pm, etc.)
- **prompt**: Full prompt text sent to the agent
- **description**: Task description
- **delegation_details**: Object containing:
  - agent_type
  - prompt (full text)
  - description
  - task_preview (first 100 chars)

#### TodoWrite Tool Parameters
When `tool_name` is "TodoWrite" (task management):
- **todo_count**: Total number of todos
- **todos**: Complete array of todo objects with:
  - content: Task description
  - status: pending, in_progress, or completed
  - priority: high, medium, or low
  - id: Unique identifier
- **todo_summary**: Summary object containing:
  - total: Total count
  - status_counts: Count by status
  - priority_counts: Count by priority
  - summary: Text summary (e.g., "2 completed, 1 in progress")
- **has_in_progress**: Boolean for active tasks
- **has_pending**: Boolean for pending tasks
- **has_completed**: Boolean for completed tasks
- **priorities**: List of all priority levels in use

### 3. Post-Tool Events (`hook.post_tool`)
- **tool_name**: Name of the completed tool
- **exit_code**: 0 for success, non-zero for failure
- **success**: Boolean success indicator
- **status**: "success", "error", or "blocked"
- **result_summary**: Summary of tool output
- **has_output**: Whether tool produced output
- **output_size**: Size of output in characters

### 4. SubagentStop Events (`hook.subagent_stop`)
- **agent_type**: Type of agent that stopped
- **agent_id**: Unique agent instance ID
- **reason**: Why the agent stopped (completed, error, timeout, etc.)
- **is_successful_completion**: Boolean for successful completion
- **is_error_termination**: Boolean for error termination
- **has_results**: Whether agent produced results

### 5. Stop Events (`hook.stop`)
- **reason**: Why Claude stopped
- **stop_type**: Type of stop (normal, error, etc.)
- **is_user_initiated**: Whether user triggered the stop
- **is_error_stop**: Whether stop was due to error
- **is_completion_stop**: Whether task completed normally

## Monitoring Agent Delegations

The system now provides complete visibility into agent delegations:

1. **Pre-delegation**: Captured in `pre_tool` events when Task tool is invoked
   - Full prompt text sent to agent
   - Target agent type
   - Task description

2. **Post-delegation**: Captured in `post_tool` events
   - Success/failure status
   - Execution results

3. **Agent completion**: Captured in `subagent_stop` events
   - Completion reason
   - Whether results were produced

## Dashboard Features

The Socket.IO dashboard displays all captured data with:
- Real-time event streaming
- Chronological ordering (newest at bottom)
- Auto-scroll to latest events
- Event filtering by type
- Full event data inspection
- Export to JSON

## Usage Examples

### Viewing Delegated Prompts
```python
# In pre_tool events where tool_name == "Task"
delegation_details = event_data['delegation_details']
print(f"Agent: {delegation_details['agent_type']}")
print(f"Prompt: {delegation_details['prompt']}")
```

### Tracking PM Delegations
```python
# Filter for PM delegations
if event_data['tool_parameters']['is_pm_delegation']:
    pm_prompt = event_data['tool_parameters']['prompt']
```

### Security Monitoring
```python
# Check high-risk operations
if event_data['security_risk'] == 'high':
    alert_security_team(event_data)
```

### Task List Monitoring
```python
# Track TodoWrite updates
if event_data['tool_name'] == 'TodoWrite':
    todos = event_data['tool_parameters']['todos']
    summary = event_data['tool_parameters']['todo_summary']
    
    print(f"Task update: {summary['summary']}")
    
    # Find high-priority in-progress tasks
    urgent_tasks = [
        todo for todo in todos 
        if todo['status'] == 'in_progress' and todo['priority'] == 'high'
    ]
    
    # Alert on stalled tasks
    for todo in todos:
        if todo['status'] == 'pending' and is_overdue(todo):
            notify_task_overdue(todo)
```

## Implementation Notes

1. **Hook Handler**: Enhanced to extract tool-specific parameters
2. **Task Tool**: Special handling to capture delegation prompts
3. **Socket.IO**: Real-time broadcasting of all hook events
4. **Dashboard**: Browser-based monitoring interface

## Future Enhancements

1. Add execution duration tracking
2. Enhance SubagentStop with more agent metadata
3. Add prompt similarity analysis
4. Create delegation flow visualization
5. Add alert rules for specific patterns