# TodoWrite Agent Prefix Hook Guide

This guide explains how to use the TodoAgentPrefixHook to enforce agent name prefixes in TodoWrite tool calls.

## Overview

The TodoAgentPrefixHook ensures that all todo items created with the TodoWrite tool include proper agent name prefixes. This helps maintain consistency in task delegation and makes it clear which agent should handle each task.

## Features

### 1. **TodoAgentPrefixHook** (Auto-fixing)
- Automatically adds appropriate agent prefixes based on content analysis
- Uses pattern matching to determine the most suitable agent
- Allows the tool call to proceed with modified parameters

### 2. **TodoAgentPrefixValidatorHook** (Validation-only)
- Strictly validates that all todos have proper agent prefixes
- Blocks tool calls that don't meet requirements
- Provides helpful error messages

## Installation

The hooks are already included in the claude-mpm project at:
```
src/claude_mpm/hooks/builtin/todo_agent_prefix_hook.py
```

## Integration Steps

### 1. Basic Integration in Orchestrator

```python
from claude_mpm.hooks.builtin.todo_agent_prefix_hook import TodoAgentPrefixHook
from claude_mpm.hooks.tool_call_interceptor import ToolCallInterceptor, SimpleHookRunner

# Create hook runner
hook_runner = SimpleHookRunner()

# Register the auto-prefix hook
prefix_hook = TodoAgentPrefixHook()
hook_runner.register_hook(prefix_hook)

# Create tool call interceptor
interceptor = ToolCallInterceptor(hook_runner)

# In your tool execution flow:
def execute_tool(tool_name, parameters):
    # Intercept tool calls
    result = interceptor.intercept_tool_call_sync(tool_name, parameters)
    
    if not result['allowed']:
        raise ValueError(f"Tool call blocked: {result['error']}")
    
    # Continue with execution using potentially modified parameters
    return original_tool_executor(tool_name, result['parameters'])
```

### 2. Integration with Hook Service

If using the centralized hook service:

```python
# The hook will be automatically loaded from the builtin directory
# when the hook service starts

# To use via JSON-RPC:
import requests

response = requests.post('http://localhost:5001/hooks/execute', json={
    'hook_type': 'custom',
    'context': {
        'tool_name': 'TodoWrite',
        'parameters': {
            'todos': [
                {'content': 'implement new feature', 'status': 'pending', ...}
            ]
        }
    }
})
```

### 3. Configuration Options

You can customize the hook behavior:

```python
# Use validation-only mode
from claude_mpm.hooks.builtin.todo_agent_prefix_hook import TodoAgentPrefixValidatorHook

validator = TodoAgentPrefixValidatorHook()
validator.priority = 10  # Run before other hooks
hook_runner.register_hook(validator)

# Or combine both for flexibility
auto_hook = TodoAgentPrefixHook()
auto_hook.priority = 20  # Run after validator
hook_runner.register_hook(auto_hook)
```

## Agent Prefix Mapping

The hook recognizes these standard agent prefixes:

| Agent | Example Tasks | Auto-detection Keywords |
|-------|--------------|------------------------|
| **Engineer** | Code implementation, bug fixes | implement, code, fix, refactor, debug |
| **Researcher** | Technical research, analysis | research, investigate, analyze, evaluate |
| **Documentater** | Documentation, guides | document, readme, changelog, guide |
| **QA** | Testing, validation | test, validate, verify, check, lint |
| **Security** | Security audits, protection | security, vulnerability, encrypt, audit |
| **Ops** | Deployment, infrastructure | deploy, configure, setup, pipeline |
| **Data Engineer** | Data pipelines, databases | data pipeline, etl, database, schema |
| **Versioner** | Version control, releases | version, release, tag, branch, git |

## Usage Examples

### Example 1: Auto-prefix Addition

```python
# Input todos without prefixes
todos = [
    {'content': 'implement user authentication', ...},
    {'content': 'write tests for auth module', ...}
]

# After hook processing
todos = [
    {'content': 'Engineer: implement user authentication', ...},
    {'content': 'QA: write tests for auth module', ...}
]
```

### Example 2: Validation Error

```python
# With validation-only hook
todos = [
    {'content': 'update documentation', ...}  # Missing prefix
]

# Result: Tool call blocked with error:
# "Todo #1 missing required agent prefix. Please use format: '[Agent]: [task description]'"
```

### Example 3: Mixed Content

```python
# Some with prefixes, some without
todos = [
    {'content': 'Engineer: fix login bug', ...},  # Already has prefix - unchanged
    {'content': 'research OAuth2 implementation', ...}  # Auto-prefixed
]

# After processing
todos = [
    {'content': 'Engineer: fix login bug', ...},
    {'content': 'Researcher: research OAuth2 implementation', ...}
]
```

## Testing

Run the example to see the hook in action:

```bash
python examples/todo_prefix_hook_example.py
```

## Troubleshooting

### Hook Not Running
- Ensure the hook is registered with the HookRunner
- Check that HookType.CUSTOM is being used
- Verify tool_name is exactly 'TodoWrite'

### Wrong Agent Assignment
- The auto-detection uses keyword matching
- You can extend the patterns in `agent_patterns` dict
- Consider using validation-only mode if auto-detection isn't suitable

### Performance Considerations
- Pattern matching is done with compiled regex for efficiency
- Hook runs synchronously by default
- Consider async execution for high-volume scenarios

## Best Practices

1. **Choose the Right Mode**:
   - Use auto-prefix for convenience and speed
   - Use validation-only for strict enforcement

2. **Priority Management**:
   - Set appropriate priorities when using multiple hooks
   - Lower priority numbers execute first

3. **Error Handling**:
   - Always check the `allowed` field in results
   - Provide clear feedback to users about prefix requirements

4. **Extensibility**:
   - Add new agent types by extending `agent_patterns`
   - Create custom hooks for specific workflows