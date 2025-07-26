# Hook System Guide

## Overview

The Claude MPM Hook System provides a powerful extension mechanism that allows you to intercept, modify, and enhance the behavior of the MPM framework at various execution points. Hooks enable custom logic injection without modifying the core framework code, making the system highly extensible and maintainable.

## What are Hooks?

Hooks are Python classes that implement specific interfaces to handle events during the MPM execution lifecycle. They can:

- **Intercept** user prompts before processing
- **Filter** context data before delegation to agents
- **Process** results after agent execution
- **Extract** information like tickets or patterns
- **Modify** data flow between components
- **Add** custom behaviors and side effects

## Hook Types

The MPM framework supports several types of hooks, each designed for specific purposes:

### 1. Submit Hooks (`HookType.SUBMIT`)

Process user prompts before they are delegated to agents.

**Use cases:**
- Command interception (e.g., `/mpm:` commands)
- Priority detection
- Ticket reference extraction
- Input validation and sanitization

**Base class:** `SubmitHook`

### 2. Pre-Delegation Hooks (`HookType.PRE_DELEGATION`)

Filter and enhance context before it's passed to agents.

**Use cases:**
- Sensitive data filtering
- Context enrichment
- Agent capability enhancement
- Access control

**Base class:** `PreDelegationHook`

### 3. Post-Delegation Hooks (`HookType.POST_DELEGATION`)

Process results after agent execution.

**Use cases:**
- Result validation
- Logging and metrics
- Error handling
- Response transformation

**Base class:** `PostDelegationHook`

### 4. Ticket Extraction Hooks (`HookType.TICKET_EXTRACTION`)

Extract and create tickets from content.

**Use cases:**
- TODO extraction
- Issue tracking integration
- Task management
- Documentation generation

**Base class:** `TicketExtractionHook`

### 5. Custom Hooks (`HookType.CUSTOM`)

User-defined hooks for specialized behaviors.

**Base class:** `BaseHook`

## Hook Architecture

### Core Components

1. **BaseHook**: Abstract base class defining the hook interface
2. **HookContext**: Data structure passed to hooks containing event information
3. **HookResult**: Standard result format returned by hooks
4. **HookService**: HTTP-based centralized hook management service
5. **JSONRPCHookClient**: JSON-RPC based hook execution client
6. **HookRunner**: Subprocess-based hook executor

### Hook Lifecycle

```
User Input → Submit Hooks → Agent Selection → Pre-Delegation Hooks 
    ↓                                               ↓
Response ← Post-Delegation Hooks ← Agent Execution
```

## Creating Custom Hooks

### Basic Hook Structure

```python
from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult, HookType

class MyCustomHook(BaseHook):
    """Description of what your hook does."""
    
    def __init__(self):
        # name: unique identifier for your hook
        # priority: 0-100 (lower executes first)
        super().__init__(name="my_custom_hook", priority=50)
    
    def execute(self, context: HookContext) -> HookResult:
        """Execute the hook logic.
        
        Args:
            context: Hook context containing data and metadata
            
        Returns:
            HookResult with execution results
        """
        try:
            # Your hook logic here
            data = context.data
            
            # Process the data
            processed_data = self.process(data)
            
            # Return result
            return HookResult(
                success=True,
                data=processed_data,
                modified=True,  # Set to True if data was modified
                metadata={'processed': True}
            )
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def validate(self, context: HookContext) -> bool:
        """Validate if hook should run for given context.
        
        Override this to add custom validation logic.
        """
        if not super().validate(context):
            return False
        
        # Add your validation logic
        return 'required_field' in context.data
```

### Submit Hook Example

```python
from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult
import re

class CommandInterceptorHook(SubmitHook):
    """Intercepts special commands in user prompts."""
    
    def __init__(self):
        super().__init__(name="command_interceptor", priority=10)
        self.command_pattern = re.compile(r'^/(\w+):\s*(.*)$')
    
    def execute(self, context: HookContext) -> HookResult:
        prompt = context.data.get('prompt', '')
        match = self.command_pattern.match(prompt)
        
        if match:
            command = match.group(1)
            args = match.group(2)
            
            # Handle the command
            response = self.handle_command(command, args)
            
            return HookResult(
                success=True,
                data={
                    'prompt': '',  # Clear prompt to skip LLM
                    'response': response,
                    'skip_llm': True
                },
                modified=True,
                metadata={'command': command, 'handled': True}
            )
        
        # Pass through if not a command
        return HookResult(
            success=True,
            data=context.data,
            modified=False
        )
    
    def handle_command(self, command: str, args: str) -> str:
        """Handle specific commands."""
        if command == "test":
            return f"Test command executed with args: {args}"
        return f"Unknown command: {command}"
```

### Pre-Delegation Hook Example

```python
from claude_mpm.hooks.base_hook import PreDelegationHook, HookContext, HookResult

class SecurityFilterHook(PreDelegationHook):
    """Filters sensitive information before delegation."""
    
    def __init__(self):
        super().__init__(name="security_filter", priority=20)
        self.sensitive_patterns = [
            'password', 'secret', 'token', 'api_key'
        ]
    
    def execute(self, context: HookContext) -> HookResult:
        agent = context.data.get('agent', '')
        agent_context = context.data.get('context', {})
        
        # Filter sensitive data
        filtered_context = self.filter_sensitive(agent_context)
        
        if filtered_context != agent_context:
            return HookResult(
                success=True,
                data={
                    'agent': agent,
                    'context': filtered_context
                },
                modified=True,
                metadata={'filtered': True}
            )
        
        return HookResult(
            success=True,
            data=context.data,
            modified=False
        )
    
    def filter_sensitive(self, data):
        """Recursively filter sensitive data."""
        if isinstance(data, dict):
            return {
                k: "[REDACTED]" if any(p in k.lower() for p in self.sensitive_patterns)
                else self.filter_sensitive(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.filter_sensitive(item) for item in data]
        return data
```

## Built-in Hooks

The MPM framework includes several built-in hooks:

### 1. MPM Command Hook (`mpm_command`)
- **Priority:** 1 (highest)
- **Purpose:** Intercepts `/mpm:` commands for direct execution
- **Location:** `src/claude_mpm/hooks/builtin/mpm_command_hook.py`

### 2. Context Filter Hook (`context_filter`)
- **Priority:** 10
- **Purpose:** Filters sensitive information from context
- **Location:** `src/claude_mpm/hooks/builtin/pre_delegation_hook_example.py`

### 3. Ticket Detection Hook (`ticket_detection`)
- **Priority:** 10
- **Purpose:** Detects ticket references (TSK-123, BUG-456, etc.)
- **Location:** `src/claude_mpm/hooks/builtin/submit_hook_example.py`

### 4. Priority Detection Hook (`priority_detection`)
- **Priority:** 20
- **Purpose:** Detects priority indicators in prompts
- **Location:** `src/claude_mpm/hooks/builtin/submit_hook_example.py`

### 5. TODO Agent Prefix Hook (`todo_agent_prefix`)
- **Priority:** 30
- **Purpose:** Prefixes TODO agent prompts with task list
- **Location:** `src/claude_mpm/hooks/builtin/todo_agent_prefix_hook.py`

## Hook Configuration

### Using .claude/hooks.json

The framework supports JSON-based hook configuration for JavaScript hooks:

```json
{
  "hooks": {
    "userPromptSubmit": [
      {
        "name": "mpm-command-interceptor",
        "enabled": true,
        "priority": 100,
        "conditions": {
          "promptPatterns": ["/mpm:", "Hello World"]
        },
        "handler": "/path/to/hook/handler.js"
      }
    ]
  },
  "global": {
    "timeoutMs": 5000,
    "retryCount": 3,
    "logging": {
      "level": "info",
      "destination": "./logs/hooks.log"
    }
  }
}
```

### Python Hook Registration

Python hooks are automatically discovered and registered from the `src/claude_mpm/hooks/builtin/` directory.

To add a new Python hook:

1. Create a new Python file in `src/claude_mpm/hooks/builtin/`
2. Define your hook class inheriting from the appropriate base class
3. The hook will be automatically discovered and registered on startup

## Hook Service

The Hook Service provides centralized hook management via HTTP API.

### Starting the Hook Service

```bash
python -m claude_mpm.services.hook_service --port 5001
```

### API Endpoints

#### Health Check
```bash
GET /health
```

#### List Hooks
```bash
GET /hooks/list
```

#### Execute Hooks
```bash
POST /hooks/execute
Content-Type: application/json

{
  "hook_type": "submit",
  "context": {
    "prompt": "User input here"
  },
  "metadata": {},
  "hook_name": "specific_hook"  # Optional
}
```

## JSON-RPC Hook Execution

The framework also supports JSON-RPC based hook execution for better subprocess isolation:

```python
from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient

# Create client
client = JSONRPCHookClient()

# Execute submit hooks
results = client.execute_submit_hook("User prompt here")

# Execute specific hook
results = client.execute_hook(
    HookType.SUBMIT,
    context_data={'prompt': 'test'},
    specific_hook='mpm_command'
)

# Get modified data from results
modified_data = client.get_modified_data(results)
```

## Best Practices

### 1. Hook Priority

- Use priorities wisely (0-100, lower executes first)
- Command interceptors: 1-10
- Security filters: 10-30
- Context enhancers: 30-50
- General processors: 50-70
- Logging/metrics: 70-100

### 2. Error Handling

Always handle errors gracefully:

```python
def execute(self, context: HookContext) -> HookResult:
    try:
        # Your logic here
        return HookResult(success=True, data=processed_data)
    except Exception as e:
        logger.error(f"Hook error: {e}")
        # Return failure but don't break the flow
        return HookResult(success=False, error=str(e))
```

### 3. Performance

- Keep hooks lightweight
- Use async operations for I/O bound tasks
- Implement timeouts for external calls
- Cache expensive computations

### 4. Data Modification

- Only set `modified=True` when actually changing data
- Preserve original data structure
- Document what fields your hook modifies
- Consider downstream hooks that may depend on your changes

### 5. Testing

Create unit tests for your hooks:

```python
import unittest
from claude_mpm.hooks.base_hook import HookContext, HookType
from datetime import datetime

class TestMyHook(unittest.TestCase):
    def setUp(self):
        self.hook = MyCustomHook()
    
    def test_execute_success(self):
        context = HookContext(
            hook_type=HookType.SUBMIT,
            data={'prompt': 'test input'},
            metadata={},
            timestamp=datetime.now()
        )
        
        result = self.hook.execute(context)
        
        self.assertTrue(result.success)
        self.assertTrue(result.modified)
        self.assertIn('processed', result.metadata)
```

## Common Patterns

### 1. Command Interception

Intercept and handle special commands without sending to LLM:

```python
if prompt.startswith('/special:'):
    return HookResult(
        success=True,
        data={
            'prompt': '',  # Clear to skip LLM
            'response': handle_special_command(prompt),
            'skip_llm': True
        },
        modified=True
    )
```

### 2. Context Enhancement

Add additional context based on conditions:

```python
if 'security' in prompt.lower():
    enhanced_context = context.data.copy()
    enhanced_context['security_guidelines'] = load_security_guidelines()
    return HookResult(
        success=True,
        data=enhanced_context,
        modified=True
    )
```

### 3. Data Filtering

Remove or redact sensitive information:

```python
filtered_data = {
    k: v if not is_sensitive(k) else "[REDACTED]"
    for k, v in data.items()
}
```

### 4. Conditional Execution

Use validation to control when hooks run:

```python
def validate(self, context: HookContext) -> bool:
    # Only run for specific agents
    return context.data.get('agent') in ['engineer', 'researcher']
```

## Troubleshooting

### Hook Not Executing

1. Check hook is in `src/claude_mpm/hooks/builtin/`
2. Verify hook class inherits from correct base class
3. Ensure hook has unique name
4. Check hook priority (lower executes first)
5. Verify `validate()` method returns True

### Hook Service Issues

1. Check port availability (default 5001)
2. Verify no import errors in hook files
3. Check logs for registration errors
4. Ensure hook service is running

### Data Not Modified

1. Ensure `modified=True` in HookResult
2. Return modified data in `data` field
3. Check hook execution order (priority)
4. Verify downstream hooks aren't overwriting changes

## Advanced Topics

### Async Hooks

For I/O bound operations, implement async hooks:

```python
class AsyncHook(BaseHook):
    def __init__(self):
        super().__init__(name="async_hook", priority=50)
        self._async = True
    
    async def async_execute(self, context: HookContext) -> HookResult:
        # Async operations
        result = await fetch_external_data()
        return HookResult(success=True, data=result)
```

### Hook Chaining

Hooks can build on each other's results:

```python
def execute(self, context: HookContext) -> HookResult:
    # Check if previous hook added data
    if 'previous_hook_data' in context.data:
        # Build on previous result
        enhanced_data = enhance(context.data['previous_hook_data'])
        return HookResult(
            success=True,
            data={**context.data, 'enhanced': enhanced_data},
            modified=True
        )
```

### Dynamic Hook Registration

Register hooks programmatically:

```python
from claude_mpm.services.hook_service import HookRegistry

registry = HookRegistry()
custom_hook = MyCustomHook()
registry.register(custom_hook, HookType.SUBMIT)
```

## Conclusion

The Hook System is a powerful extension mechanism that makes Claude MPM highly customizable. By understanding hook types, implementing them correctly, and following best practices, you can extend the framework's capabilities while maintaining clean, maintainable code.

For more examples, see the built-in hooks in `src/claude_mpm/hooks/builtin/`.