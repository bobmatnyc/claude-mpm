# Creating Custom Hooks

This guide explains how to create custom hooks for Claude MPM to intercept and modify behavior at key points in the execution lifecycle.

## Overview

Hooks provide a powerful way to extend Claude MPM without modifying core code. They can:
- Intercept user input before it reaches Claude
- Process Claude's output before display
- React to delegation events
- Extract and process tickets
- Add custom logging, metrics, or integrations

## Hook Types

Claude MPM supports several hook types:

```python
from claude_mpm.hooks.base_hook import HookType

# Available hook types
HookType.SUBMIT           # Before user input is sent to Claude
HookType.PRE_DELEGATION   # Before delegating to an agent
HookType.POST_DELEGATION  # After agent delegation completes
HookType.TICKET_EXTRACTION # When tickets are extracted
HookType.CUSTOM           # For custom event types
```

## Base Hook Classes

### BaseHook

All hooks inherit from `BaseHook`:

```python
from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult

class CustomHook(BaseHook):
    def __init__(self, name: str, priority: int = 50):
        super().__init__(name=name, priority=priority)
    
    async def execute(self, context: HookContext) -> HookResult:
        """Execute hook logic."""
        # Your implementation
        return HookResult(success=True)
```

### Specialized Hook Classes

Use specialized base classes for specific hook types:

```python
from claude_mpm.hooks.base_hook import (
    SubmitHook,
    PreDelegationHook,
    PostDelegationHook,
    TicketExtractionHook
)
```

## Creating a Simple Hook

### Example: Logging Hook

```python
from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult
import logging

class LoggingHook(SubmitHook):
    """Log all user submissions with metadata."""
    
    def __init__(self, log_file: str = "submissions.log"):
        super().__init__(name="logging-hook", priority=10)
        
        # Set up dedicated logger
        self.logger = logging.getLogger("submissions")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def execute(self, context: HookContext) -> HookResult:
        """Log the submission."""
        try:
            message = context.data.get("message", "")
            session_id = context.metadata.get("session_id", "unknown")
            
            self.logger.info(
                f"Session {session_id}: {message}"
            )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=f"Logging failed: {e}"
            )
```

## Advanced Hook Examples

### Input Transformation Hook

```python
class InputTransformationHook(SubmitHook):
    """Transform user input before sending to Claude."""
    
    def __init__(self, transformations: Dict[str, str]):
        super().__init__(name="input-transformer", priority=20)
        self.transformations = transformations
    
    async def execute(self, context: HookContext) -> HookResult:
        """Apply transformations to input."""
        message = context.data.get("message", "")
        
        # Apply transformations
        for pattern, replacement in self.transformations.items():
            message = message.replace(pattern, replacement)
        
        # Return modified message
        return HookResult(
            success=True,
            data={"message": message}
        )

# Usage
hook = InputTransformationHook({
    "TODO": "[TASK]",
    "FIXME": "[BUG]",
    "@claude": "Claude,"
})
```

### Validation Hook

```python
class ValidationHook(SubmitHook):
    """Validate input before processing."""
    
    def __init__(self, max_length: int = 10000, blocked_words: List[str] = None):
        super().__init__(name="validation-hook", priority=5)
        self.max_length = max_length
        self.blocked_words = blocked_words or []
    
    async def execute(self, context: HookContext) -> HookResult:
        """Validate the input."""
        message = context.data.get("message", "")
        
        # Check length
        if len(message) > self.max_length:
            return HookResult(
                success=False,
                error=f"Message too long ({len(message)} > {self.max_length})"
            )
        
        # Check blocked words
        message_lower = message.lower()
        for word in self.blocked_words:
            if word.lower() in message_lower:
                return HookResult(
                    success=False,
                    error=f"Message contains blocked word: {word}"
                )
        
        return HookResult(success=True)
```

### Metrics Collection Hook

```python
import time
from datetime import datetime
from collections import defaultdict

class MetricsHook(BaseHook):
    """Collect metrics about Claude usage."""
    
    def __init__(self):
        super().__init__(name="metrics-hook", priority=90)
        self.metrics = defaultdict(int)
        self.session_starts = {}
    
    async def execute(self, context: HookContext) -> HookResult:
        """Collect metrics based on hook type."""
        session_id = context.metadata.get("session_id")
        
        if context.hook_type == HookType.SUBMIT:
            self.metrics["total_submissions"] += 1
            self.metrics[f"submissions_{datetime.now().strftime('%Y-%m-%d')}"] += 1
            
            # Track session duration
            if session_id not in self.session_starts:
                self.session_starts[session_id] = time.time()
        
        elif context.hook_type == HookType.PRE_DELEGATION:
            agent = context.data.get("agent")
            self.metrics[f"delegations_{agent}"] += 1
        
        elif context.hook_type == HookType.TICKET_EXTRACTION:
            ticket_type = context.data.get("type")
            self.metrics[f"tickets_{ticket_type}"] += 1
        
        return HookResult(success=True)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get collected metrics."""
        return dict(self.metrics)
    
    def get_session_duration(self, session_id: str) -> float:
        """Get session duration in seconds."""
        if session_id in self.session_starts:
            return time.time() - self.session_starts[session_id]
        return 0.0
```

## Delegation Hooks

### Pre-Delegation Hook

```python
class AgentAuthorizationHook(PreDelegationHook):
    """Authorize agent delegations based on rules."""
    
    def __init__(self, authorized_agents: List[str], admin_mode: bool = False):
        super().__init__(name="agent-auth", priority=10)
        self.authorized_agents = authorized_agents
        self.admin_mode = admin_mode
    
    async def execute(self, context: HookContext) -> HookResult:
        """Check if delegation is authorized."""
        agent = context.data.get("agent")
        task = context.data.get("task")
        
        # Admin mode bypasses all checks
        if self.admin_mode:
            return HookResult(success=True)
        
        # Check authorization
        if agent not in self.authorized_agents:
            return HookResult(
                success=False,
                error=f"Agent '{agent}' is not authorized"
            )
        
        # Additional checks could go here
        # e.g., task complexity, time restrictions, etc.
        
        return HookResult(success=True)
```

### Post-Delegation Hook

```python
class DelegationNotificationHook(PostDelegationHook):
    """Send notifications after delegations complete."""
    
    def __init__(self, webhook_url: str):
        super().__init__(name="delegation-notifier", priority=80)
        self.webhook_url = webhook_url
    
    async def execute(self, context: HookContext) -> HookResult:
        """Send webhook notification."""
        import aiohttp
        
        agent = context.data.get("agent")
        task = context.data.get("task")
        result = context.data.get("result")
        
        payload = {
            "event": "delegation_complete",
            "agent": agent,
            "task": task,
            "success": result.get("success", False),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        return HookResult(success=True)
                    else:
                        return HookResult(
                            success=False,
                            error=f"Webhook returned {resp.status}"
                        )
        except Exception as e:
            return HookResult(
                success=False,
                error=f"Webhook failed: {e}"
            )
```

## Ticket Extraction Hooks

```python
class TicketEnrichmentHook(TicketExtractionHook):
    """Enrich extracted tickets with additional metadata."""
    
    def __init__(self, project_id: str, default_assignee: str = None):
        super().__init__(name="ticket-enricher", priority=30)
        self.project_id = project_id
        self.default_assignee = default_assignee
    
    async def execute(self, context: HookContext) -> HookResult:
        """Enrich ticket data."""
        ticket = context.data
        
        # Add project information
        ticket["project_id"] = self.project_id
        
        # Add creation metadata
        ticket["created_by"] = "claude-mpm"
        ticket["created_at"] = datetime.now().isoformat()
        
        # Add default assignee if not set
        if "assignee" not in ticket and self.default_assignee:
            ticket["assignee"] = self.default_assignee
        
        # Add priority based on type
        if "priority" not in ticket:
            ticket["priority"] = self._determine_priority(ticket["type"])
        
        return HookResult(
            success=True,
            data=ticket
        )
    
    def _determine_priority(self, ticket_type: str) -> str:
        """Determine ticket priority based on type."""
        priority_map = {
            "BUG": "high",
            "SECURITY": "critical",
            "FEATURE": "medium",
            "TASK": "low"
        }
        return priority_map.get(ticket_type, "medium")
```

## Async Hooks

Hooks support async operations:

```python
import asyncio
import aiofiles

class AsyncFileHook(SubmitHook):
    """Asynchronously log submissions to file."""
    
    def __init__(self, log_dir: Path):
        super().__init__(name="async-file-hook", priority=50)
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
    
    async def execute(self, context: HookContext) -> HookResult:
        """Async file write."""
        session_id = context.metadata.get("session_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        file_path = self.log_dir / f"{session_id}_{timestamp}.json"
        
        try:
            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps({
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "data": context.data,
                    "metadata": context.metadata
                }, indent=2))
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=f"Failed to write log: {e}"
            )
```

## Hook Composition

Combine multiple hooks:

```python
class CompositeHook(BaseHook):
    """Compose multiple hooks into one."""
    
    def __init__(self, name: str, hooks: List[BaseHook]):
        # Use lowest priority among composed hooks
        min_priority = min(h.priority for h in hooks)
        super().__init__(name=name, priority=min_priority)
        self.hooks = hooks
    
    async def execute(self, context: HookContext) -> HookResult:
        """Execute all composed hooks."""
        results = []
        
        for hook in self.hooks:
            result = await hook.execute(context)
            results.append(result)
            
            # Stop on first failure
            if not result.success:
                return result
            
            # Update context data with results
            if result.data:
                context.data.update(result.data)
        
        # Aggregate results
        return HookResult(
            success=True,
            data={"composite_results": results}
        )

# Usage
composite = CompositeHook("validation-and-logging", [
    ValidationHook(max_length=5000),
    LoggingHook(),
    MetricsHook()
])
```

## Testing Hooks

### Unit Testing

```python
import pytest
from claude_mpm.hooks.base_hook import HookContext, HookType

@pytest.mark.asyncio
async def test_logging_hook():
    hook = LoggingHook(log_file="test.log")
    
    context = HookContext(
        hook_type=HookType.SUBMIT,
        data={"message": "Test message"},
        metadata={"session_id": "test-123"}
    )
    
    result = await hook.execute(context)
    
    assert result.success == True
    assert os.path.exists("test.log")
    
    # Verify log content
    with open("test.log") as f:
        content = f.read()
        assert "Test message" in content
        assert "test-123" in content
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_hook_chain():
    # Create hook chain
    validator = ValidationHook(blocked_words=["spam"])
    transformer = InputTransformationHook({"test": "TEST"})
    
    # Test valid input
    context = HookContext(
        hook_type=HookType.SUBMIT,
        data={"message": "This is a test"}
    )
    
    # Run through chain
    result1 = await validator.execute(context)
    assert result1.success == True
    
    result2 = await transformer.execute(context)
    assert result2.success == True
    assert result2.data["message"] == "This is a TEST"
    
    # Test invalid input
    context.data["message"] = "This is spam"
    result3 = await validator.execute(context)
    assert result3.success == False
```

## Hook Registration

### Programmatic Registration

```python
from claude_mpm.services.hook_service import HookRegistry

registry = HookRegistry()

# Register hooks
registry.register(LoggingHook())
registry.register(ValidationHook(max_length=10000))
registry.register(MetricsHook())
```

### Configuration-Based Registration

```yaml
# hooks.yaml
hooks:
  - type: submit
    class: my_package.LoggingHook
    config:
      log_file: submissions.log
  
  - type: pre_delegation
    class: my_package.AgentAuthorizationHook
    config:
      authorized_agents:
        - engineer
        - qa
        - documentation
```

### Entry Point Registration

In your package's `setup.py`:

```python
setup(
    name="my-claude-hooks",
    entry_points={
        "claude_mpm.hooks": [
            "logging = my_package:LoggingHook",
            "validation = my_package:ValidationHook",
            "metrics = my_package:MetricsHook",
        ],
    },
)
```

## Best Practices

1. **Keep hooks fast** - They run in the critical path
2. **Handle errors gracefully** - Don't crash the main application
3. **Use appropriate priorities** - Lower numbers run first
4. **Make hooks configurable** - Avoid hardcoded values
5. **Log appropriately** - Use debug for verbose output
6. **Test thoroughly** - Including error cases
7. **Document behavior** - Especially side effects
8. **Avoid blocking operations** - Use async where possible
9. **Respect the contract** - Return appropriate HookResult
10. **Consider performance** - Hooks run frequently

## Performance Considerations

### Caching

```python
class CachedHook(BaseHook):
    """Hook with caching for expensive operations."""
    
    def __init__(self):
        super().__init__(name="cached-hook", priority=50)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def execute(self, context: HookContext) -> HookResult:
        cache_key = self._get_cache_key(context)
        
        # Check cache
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry["time"] < self._cache_ttl:
                return entry["result"]
        
        # Perform expensive operation
        result = await self._expensive_operation(context)
        
        # Cache result
        self._cache[cache_key] = {
            "time": time.time(),
            "result": result
        }
        
        return result
```

### Batching

```python
class BatchingHook(BaseHook):
    """Hook that batches operations."""
    
    def __init__(self, batch_size: int = 10, flush_interval: float = 1.0):
        super().__init__(name="batching-hook", priority=60)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._batch = []
        self._last_flush = time.time()
    
    async def execute(self, context: HookContext) -> HookResult:
        self._batch.append(context)
        
        # Check if we should flush
        should_flush = (
            len(self._batch) >= self.batch_size or
            time.time() - self._last_flush > self.flush_interval
        )
        
        if should_flush:
            await self._flush_batch()
        
        return HookResult(success=True)
    
    async def _flush_batch(self):
        """Process the batch."""
        if not self._batch:
            return
        
        # Process all items in batch
        await self._process_batch(self._batch)
        
        # Clear batch
        self._batch.clear()
        self._last_flush = time.time()
```