# Claude Code Hook Agent Identification System

Claude Code's hook system provides deterministic control over agent behavior through JSON payloads containing standardized fields for identifying which agent (main Claude vs subagents) triggers specific hook events. Based on comprehensive research of official documentation, implementation examples, and community practices, here's exactly what you need to implement effective agent identification in your Claude MPM hook system.

## Core agent identification fields in hook payloads

Claude Code includes three primary fields in hook payloads for agent identification:

**session_id** - The universal session identifier present in all hook payloads. This UUID-style string (e.g., "eb5b0174-0555-4601-804e-672d68069c89") uniquely identifies each Claude Code session and persists across the entire conversation lifecycle.

**hook_event_name** - The discriminator field that explicitly identifies the hook type and by extension the triggering agent. Critical values include "Stop" (main agent completion) and "SubagentStop" (subagent/Task tool completion).

**tool_name** - Available in PreToolUse and PostToolUse hooks, this field helps identify subagent actions. When the value is "Task", it indicates subagent execution. MCP tools follow the pattern `mcp__<server>__<tool>`.

## Detecting main agent vs subagents

The most reliable method for differentiating between agents relies on the **hook_event_name** field:

- **Main Claude Agent** triggers the "Stop" hook when finishing responses
- **Subagents** trigger the "SubagentStop" hook when Task tool calls complete
- **Tool execution patterns** show subagents often use the "Task" tool name in PreToolUse/PostToolUse hooks

Here's a production-ready detection implementation:

```python
def identify_agent_context(payload):
    session_id = payload.get("session_id")
    event_type = payload.get("hook_event_name") 
    tool_name = payload.get("tool_name", "")
    
    if event_type == "SubagentStop":
        return f"subagent:{session_id}"
    elif event_type == "Stop":
        return f"main_agent:{session_id}"
    elif tool_name == "Task":
        return f"subagent_task:{session_id}"
    elif tool_name.startswith("mcp__"):
        return f"mcp_tool:{tool_name}:{session_id}"
    else:
        return f"agent:{session_id}"
```

## Standard fields across all hook events

Every hook payload contains these standard fields:

```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
  "cwd": "/Users/...",
  "hook_event_name": "EventName"
}
```

Additional fields appear based on the specific hook type. The **transcript_path** provides access to the complete conversation history, enabling deeper context analysis when standard fields aren't sufficient.

## Hook event differences for agent identification

Each hook event type provides different agent identification capabilities:

### UserPromptSubmit
```json
{
  "session_id": "abc123",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "User's input text"
}
```
Limited agent identification - only session_id available. However, analyzing the prompt content can predict whether subagents will be spawned.

### PreToolUse
```json
{
  "session_id": "abc123",
  "hook_event_name": "PreToolUse",
  "tool_name": "Task",
  "tool_input": { /* tool-specific data */ }
}
```
Strong agent identification through **tool_name** field. "Task" indicates subagent execution.

### PostToolUse
```json
{
  "session_id": "abc123",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": { /* input data */ },
  "tool_response": { /* execution results */ }
}
```
Includes both tool context and results, enabling behavior-based agent fingerprinting.

### Stop vs SubagentStop
The critical differentiator:
- **Stop**: `{"hook_event_name": "Stop", "stop_hook_active": false}` - Main agent completion
- **SubagentStop**: `{"hook_event_name": "SubagentStop", "stop_hook_active": false}` - Subagent completion

## Real-world payload examples

### Main Agent Writing Code:
```json
{
  "session_id": "main-789",
  "transcript_path": "/Users/dev/.claude/projects/api/main-session.jsonl",
  "cwd": "/Users/dev/project",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/src/auth.py",
    "content": "def authenticate(user, password):..."
  }
}
```

### Subagent Task Execution:
```json
{
  "session_id": "subagent-456",
  "transcript_path": "/Users/dev/.claude/projects/api/subagent-session.jsonl",
  "cwd": "/Users/dev/project",
  "hook_event_name": "PreToolUse",
  "tool_name": "Task",
  "tool_input": {
    "command": "Research authentication best practices"
  }
}
```

### MCP Tool Usage:
```json
{
  "session_id": "abc123",
  "hook_event_name": "PostToolUse",
  "tool_name": "mcp__memory__create_entities",
  "tool_input": { /* MCP-specific data */ },
  "tool_response": { /* MCP response */ }
}
```

## Best practices for production agent detection

### Primary detection strategy
1. **Always check hook_event_name first** - "SubagentStop" definitively identifies subagent completion
2. **Use tool_name as secondary indicator** - "Task" reliably indicates subagent activity
3. **Track session_id patterns** - Some implementations use prefixes like "subagent-" or "task-"
4. **Implement comprehensive logging** - Store all hook payloads with agent classification for debugging

### Advanced detection patterns
```python
def classify_agent_advanced(payload):
    """Production-ready agent classification with multiple signals"""
    
    # Direct event detection (highest confidence)
    if payload.get("hook_event_name") == "SubagentStop":
        return {"type": "subagent", "confidence": "definitive"}
    
    # Tool-based detection (high confidence)
    tool_name = payload.get("tool_name", "")
    if tool_name == "Task":
        return {"type": "subagent", "confidence": "high"}
    
    # Session pattern analysis (medium confidence)
    session_id = payload.get("session_id", "")
    if any(pattern in session_id.lower() for pattern in ["subagent", "task", "agent-"]):
        return {"type": "subagent", "confidence": "medium"}
    
    # Default to main agent
    return {"type": "main_agent", "confidence": "default"}
```

### Context enhancement for ambiguous cases
When standard fields don't provide clear identification:

1. **Parse transcript files** - The transcript_path points to JSONL files containing complete conversation history
2. **Analyze tool sequences** - Subagents often follow predictable tool usage patterns
3. **Monitor working directories** - Different agents may operate in different project contexts
4. **Track timing patterns** - Subagents typically complete faster than main agents

### Implementation considerations

- **Parallel hook execution** - All matching hooks run simultaneously, requiring thread-safe agent tracking
- **60-second timeout** - Hook commands must complete within this limit
- **Performance impact** - Each hook adds 50-200ms latency; optimize detection logic for speed
- **Session persistence** - Agent state doesn't automatically carry between sessions; implement external state management

The Claude Code hook system provides robust agent identification through the combination of hook_event_name, session_id, and tool_name fields. The SubagentStop event offers definitive subagent identification, while tool patterns and session analysis provide additional detection signals. By implementing these patterns, your Claude MPM hook system can reliably differentiate between main Claude agents and subagents for effective context filtering and workflow automation.