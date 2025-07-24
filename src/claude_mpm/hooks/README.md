# Claude MPM Hook Service

The Hook Service provides a centralized, extensible system for processing events throughout the claude-mpm orchestration pipeline.

## Overview

The hook service runs as a separate process and provides a REST API for executing hooks at various points in the orchestration workflow:

- **Submit Hooks**: Process user prompts before orchestration
- **Pre-Delegation Hooks**: Filter/enhance context before delegating to agents  
- **Post-Delegation Hooks**: Validate/process results from agents
- **Ticket Extraction Hooks**: Automatically extract and create tickets from conversations

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Orchestrator  │────▶│   Hook Service   │────▶│   Hook Types    │
│                 │     │   (REST API)     │     ├─────────────────┤
│ - Process prompt│     │                  │     │ - SubmitHook    │
│ - Delegate work │     │ - /execute_hook  │     │ - PreDelegation │
│ - Create tickets│     │ - /list_hooks    │     │ - PostDelegation│
└─────────────────┘     │ - /register_hook │     │ - TicketExtract │
                        └──────────────────┘     └─────────────────┘
```

## Starting the Hook Service

```bash
# Using the shell script (recommended)
./bin/claude-mpm-hooks

# With custom port
./bin/claude-mpm-hooks --port 5002

# With debug logging
./bin/claude-mpm-hooks --log-level DEBUG

# Direct Python execution (for development)
python -m src.services.hook_service --port 5001
```

## Hook Types

### 1. Submit Hooks
Process user prompts before they're sent to the orchestrator:
```python
class TicketDetectionSubmitHook(SubmitHook):
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
class ContextFilterHook(PreDelegationHook):
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
class ResultValidatorHook(PostDelegationHook):
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
class AutoTicketExtractionHook(TicketExtractionHook):
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

## Client Usage

### Basic Client Usage
```python
from src.hooks.hook_client import get_hook_client

# Create client
client = get_hook_client()

# Check service health
health = client.health_check()
print(f"Service status: {health['status']}")

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

### Integration with Orchestrator
```python
from src.orchestration.hook_enabled_orchestrator import HookEnabledOrchestrator

# Create hook-enabled orchestrator
orchestrator = HookEnabledOrchestrator()

# Process prompt (hooks are called automatically)
response = await orchestrator.process_prompt(
    "Create ticket: Implement user dashboard"
)
```

## Creating Custom Hooks

### 1. Create Hook Class
```python
from src.hooks.base_hook import SubmitHook, HookContext, HookResult

class CustomSubmitHook(SubmitHook):
    def __init__(self):
        super().__init__(name="custom_hook", priority=25)
        
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
```

### 2. Register Hook
```python
# In your hook module or service startup
from src.services.hook_service import HookRegistry

registry = HookRegistry()
registry.register(CustomSubmitHook())
```

### 3. Hook Priority
Hooks execute in priority order (0-100, lower first):
- 0-20: Critical preprocessing (security, validation)
- 21-40: Data transformation
- 41-60: Enhancement and enrichment
- 61-80: Analytics and metrics
- 81-100: Low priority post-processing

## REST API Reference

### Health Check
```
GET /health
Response: {
    "status": "healthy",
    "timestamp": "2025-01-23T10:00:00",
    "hooks_count": 8
}
```

### List Hooks
```
GET /hooks/list
Response: {
    "status": "success",
    "hooks": {
        "submit": [
            {"name": "ticket_detection", "priority": 10, "enabled": true}
        ],
        "pre_delegation": [...],
        "post_delegation": [...],
        "ticket_extraction": [...]
    }
}
```

### Execute Hooks
```
POST /hooks/execute
Body: {
    "hook_type": "submit",
    "context": {
        "prompt": "User input here"
    },
    "metadata": {
        "session_id": "abc123"
    },
    "hook_name": "specific_hook"  // Optional
}
Response: {
    "status": "success",
    "results": [
        {
            "hook_name": "ticket_detection",
            "success": true,
            "data": {...},
            "modified": true,
            "execution_time_ms": 5.2
        }
    ]
}
```

## Environment Variables

- `CLAUDE_MPM_HOOKS_URL`: Hook service URL (default: http://localhost:5001)
- `CLAUDE_MPM_HOOKS_PORT`: Port for hook service (default: 5001)
- `CLAUDE_MPM_LOG_LEVEL`: Logging level (default: INFO)

## Best Practices

1. **Keep Hooks Fast**: Hooks run synchronously, so keep execution time minimal
2. **Handle Errors Gracefully**: Always return a HookResult, even on failure
3. **Use Appropriate Priority**: Consider hook dependencies when setting priority
4. **Validate Input**: Always validate context data before processing
5. **Log Important Events**: Use logging for debugging and monitoring
6. **Make Hooks Idempotent**: Hooks should produce same result if run multiple times

## Troubleshooting

### Service Won't Start
- Check if port is already in use: `lsof -i :5001`
- Verify virtual environment is activated
- Check Flask is installed: `pip install flask flask-cors`

### Hooks Not Executing
- Verify service is running: `curl http://localhost:5001/health`
- Check hook is registered: `curl http://localhost:5001/hooks/list`
- Enable debug logging: `--log-level DEBUG`

### Performance Issues
- Check hook execution times in results
- Consider making heavy hooks async
- Use caching for expensive operations
- Profile hooks with `cProfile`

## Examples

See the `builtin/` directory for example implementations:
- `submit_hook_example.py`: Ticket and priority detection
- `pre_delegation_hook_example.py`: Context filtering and enhancement  
- `post_delegation_hook_example.py`: Result validation and metrics
- `ticket_extraction_hook_example.py`: Automatic ticket extraction