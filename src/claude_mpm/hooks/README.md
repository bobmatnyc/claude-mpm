# Claude MPM Hook System

The Claude MPM hook system provides extensibility points for customizing behavior at key stages of execution.

## Current Implementation (v0.5.0+)

As of version 0.5.0, the hook system uses JSON-RPC for all hook executions. The previous HTTP-based implementation is deprecated and will be removed in a future release.

## Overview

The hook system allows you to intercept and modify behavior at various points in the orchestration workflow:

- **Submit Hooks**: Process user prompts before orchestration
- **Pre-Delegation Hooks**: Filter/enhance context before delegating to agents  
- **Post-Delegation Hooks**: Validate/process results from agents
- **Ticket Extraction Hooks**: Automatically extract and create tickets from conversations

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Orchestrator  │────▶│ JSON-RPC Client  │────▶│   Hook Types    │
│                 │     │                  │     ├─────────────────┤
│ - Process prompt│     │ - No server req. │     │ - SubmitHook    │
│ - Delegate work │     │ - Direct exec    │     │ - PreDelegation │
│ - Create tickets│     │ - Auto discovery │     │ - PostDelegation│
└─────────────────┘     └──────────────────┘     │ - TicketExtract │
                                                  └─────────────────┘
```

## Usage

### Basic Client Usage
```python
from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient

# Create client
client = JSONRPCHookClient()

# Check system health
health = client.health_check()
print(f"Status: {health['status']}")
print(f"Hooks available: {health['hook_count']}")

# List available hooks
hooks = client.list_hooks()
for hook_type, hook_list in hooks.items():
    print(f"{hook_type}: {len(hook_list)} hooks")
```

### Executing Hooks
```python
# Execute submit hooks
results = client.execute_submit_hook(
    prompt="URGENT: Fix the login bug",
    user_id="user123"
)

# Get modified data
modified_data = client.get_modified_data(results)
if modified_data.get('priority') == 'high':
    print("High priority task detected!")

# Execute pre-delegation hooks
results = client.execute_pre_delegation_hook(
    agent="engineer",
    context={"task": "implement feature"}
)

# Execute ticket extraction
results = client.execute_ticket_extraction_hook(
    content="TODO: Add tests\nFIXME: Memory leak"
)
tickets = client.get_extracted_tickets(results)
```

## Hook Types

### 1. Submit Hooks
Process user prompts before they're sent to the orchestrator:
```python
from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult

class TicketDetectionSubmitHook(SubmitHook):
    name = "ticket_detection"
    priority = 10
    
    def execute(self, context: HookContext) -> HookResult:
        prompt = context.data.get('prompt', '')
        # Detect ticket references like TSK-001
        tickets = self.ticket_pattern.findall(prompt)
        return HookResult(
            success=True,
            data={'tickets': tickets},
            modified=True
        )
```

### 2. Pre-Delegation Hooks
Modify agent context before delegation:
```python
from claude_mpm.hooks.base_hook import PreDelegationHook

class ContextFilterHook(PreDelegationHook):
    name = "context_filter"
    priority = 20
    
    def execute(self, context: HookContext) -> HookResult:
        # Filter sensitive information
        filtered_context = self._filter_sensitive(context.data['context'])
        return HookResult(
            success=True,
            data={'context': filtered_context},
            modified=True
        )
```

### 3. Post-Delegation Hooks
Process agent results:
```python
from claude_mpm.hooks.base_hook import PostDelegationHook

class ResultValidatorHook(PostDelegationHook):
    name = "result_validator"
    priority = 30
    
    def execute(self, context: HookContext) -> HookResult:
        result = context.data.get('result', {})
        # Validate result quality
        issues = self._validate_result(result)
        return HookResult(
            success=True,
            data={'validation_issues': issues},
            modified=bool(issues)
        )
```

### 4. Ticket Extraction Hooks
Extract actionable items from conversations:
```python
from claude_mpm.hooks.base_hook import TicketExtractionHook

class AutoTicketExtractionHook(TicketExtractionHook):
    name = "auto_ticket_extraction"
    priority = 40
    
    def execute(self, context: HookContext) -> HookResult:
        content = context.data.get('content', '')
        # Extract TODO, FIXME, etc.
        tickets = self._extract_tickets(content)
        return HookResult(
            success=True,
            data={'tickets': tickets},
            modified=True
        )
```

## Creating Custom Hooks

### 1. Create Hook File
Create a new Python file in the `builtin/` directory:

```python
# builtin/my_custom_hook.py
from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult

class MyCustomHook(SubmitHook):
    name = "my_custom_hook"
    priority = 25  # 0-100, lower executes first
    
    def execute(self, context: HookContext) -> HookResult:
        # Your hook logic here
        prompt = context.data.get('prompt', '')
        
        # Process prompt
        processed = self._process(prompt)
        
        return HookResult(
            success=True,
            data={'prompt': processed},
            modified=True
        )
    
    def _process(self, prompt: str) -> str:
        # Your processing logic
        return prompt.upper()
```

### 2. Hook Discovery
Hooks are automatically discovered from the `builtin/` directory when the client is initialized. No manual registration required!

### 3. Hook Priority
Hooks execute in priority order (0-100, lower first):
- 0-20: Critical preprocessing (security, validation)
- 21-40: Data transformation
- 41-60: Enhancement and enrichment
- 61-80: Analytics and metrics
- 81-100: Low priority post-processing

## Migration from HTTP-based Hooks

If you're migrating from the old HTTP-based hook system, see `/docs/hook_system_migration_guide.md` for detailed instructions.

Key changes:
- No server startup required
- Import from `json_rpc_hook_client` instead of `hook_client`
- Automatic hook discovery from `builtin/` directory
- Better error handling and performance

## Best Practices

1. **Keep Hooks Fast**: Hooks run synchronously, so keep execution time minimal
2. **Handle Errors Gracefully**: Always return a HookResult, even on failure
3. **Use Appropriate Priority**: Consider hook dependencies when setting priority
4. **Validate Input**: Always validate context data before processing
5. **Log Important Events**: Use logging for debugging and monitoring
6. **Make Hooks Idempotent**: Hooks should produce same result if run multiple times

## Troubleshooting

### Hooks Not Discovered
- Verify hook file is in `builtin/` directory
- Check file has `.py` extension
- Ensure hook class inherits from correct base type
- Check for Python syntax errors

### Hook Execution Errors
- Enable debug logging to see detailed errors
- Check hook's execute method returns HookResult
- Verify context data structure matches expectations

### Performance Issues
- Check hook execution times in results
- Consider caching expensive operations
- Profile hooks with `cProfile` if needed

## Examples

See the `builtin/` directory for example implementations:
- `submit_hook_example.py`: Ticket and priority detection
- `pre_delegation_hook_example.py`: Context filtering and enhancement  
- `post_delegation_hook_example.py`: Result validation and metrics
- `ticket_extraction_hook_example.py`: Automatic ticket extraction