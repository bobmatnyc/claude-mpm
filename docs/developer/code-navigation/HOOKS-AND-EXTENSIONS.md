# Hooks and Extensions Documentation

## Hook System Overview

Claude MPM's hook system provides extensibility points for:
- **Pre-tool execution** - Modify context before tool runs
- **Post-tool execution** - Process results after tool completes
- **Session lifecycle** - Handle session start/end events
- **Memory integration** - Inject context from memory systems

## Hook Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Hook Manager                         │
│  (core/hook_manager.py)                                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Pre-Tool Hooks              Post-Tool Hooks            │
│  ┌──────────────────┐        ┌──────────────────┐       │
│  │ Kuzu Enrichment  │        │ Kuzu Response    │       │
│  │ Memory Injection │        │ Learning Extract │       │
│  │ Inst. Reinforce  │        │ Fix Detection    │       │
│  └──────────────────┘        └──────────────────┘       │
│                                                          │
│  Session Hooks                                           │
│  ┌──────────────────┐                                   │
│  │ Session Resume   │                                   │
│  │ Context Preserve │                                   │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

## Hook Directory Structure

```
src/claude_mpm/hooks/
├── __init__.py              # Hook exports
├── README.md                # Hook documentation
├── base_hook.py             # BaseHook, HookContext, HookResult
├── failure_learning/        # Failure detection hooks
│   ├── __init__.py
│   ├── failure_detection_hook.py
│   ├── fix_detection_hook.py
│   └── learning_extraction_hook.py
├── kuzu_enrichment_hook.py  # Context enrichment
├── kuzu_memory_hook.py      # Memory integration
├── kuzu_response_hook.py    # Response processing
├── memory_integration_hook.py
├── instruction_reinforcement.py
├── session_resume_hook.py   # Session resume
├── templates/               # Hook templates
├── tool_call_interceptor.py # Tool interception
└── validation_hooks.py      # Validation hooks
```

## Base Hook Classes

### BaseHook
```python
# hooks/base_hook.py
class BaseHook(ABC):
    """Abstract base class for all hooks"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique hook identifier"""
    
    @property
    def priority(self) -> int:
        """Execution priority (higher = earlier)"""
        return 0
    
    @abstractmethod
    async def execute(self, context: HookContext) -> HookResult:
        """Execute the hook"""
```

### HookContext
```python
class HookContext:
    """Context passed to hooks"""
    tool_name: str
    tool_args: Dict[str, Any]
    session_id: str
    agent_id: Optional[str]
    metadata: Dict[str, Any]
    
    # For post-tool hooks
    tool_result: Optional[Any]
    error: Optional[Exception]
```

### HookResult
```python
class HookResult:
    """Result returned from hook execution"""
    success: bool
    modified_context: Optional[HookContext]
    data: Dict[str, Any]
    should_continue: bool = True  # False stops hook chain
    error: Optional[str]
```

### HookType
```python
class HookType(Enum):
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR = "error"
```

## Built-in Hooks

### 1. Kuzu Memory Hook
```python
# hooks/kuzu_memory_hook.py
class KuzuMemoryHook(BaseHook):
    """Injects relevant memories into context"""
    
    @property
    def name(self) -> str:
        return "kuzu_memory"
    
    async def execute(self, context: HookContext) -> HookResult:
        # Query kuzu-memory for relevant context
        memories = await self.query_memories(context.session_id)
        # Inject into context
        context.metadata["memories"] = memories
        return HookResult(success=True, modified_context=context)
```

### 2. Kuzu Enrichment Hook
```python
# hooks/kuzu_enrichment_hook.py
class KuzuEnrichmentHook(BaseHook):
    """Enriches prompts with project context"""
    
    @property
    def name(self) -> str:
        return "kuzu_enrichment"
    
    async def execute(self, context: HookContext) -> HookResult:
        # Get project-specific context
        project_context = await self.get_project_context()
        # Enrich the tool arguments
        if "prompt" in context.tool_args:
            context.tool_args["prompt"] = self.enrich(
                context.tool_args["prompt"],
                project_context
            )
        return HookResult(success=True, modified_context=context)
```

### 3. Kuzu Response Hook
```python
# hooks/kuzu_response_hook.py
class KuzuResponseHook(BaseHook):
    """Processes responses for learning extraction"""
    
    @property
    def name(self) -> str:
        return "kuzu_response"
    
    async def execute(self, context: HookContext) -> HookResult:
        if context.tool_result:
            # Extract learnings from response
            learnings = self.extract_learnings(context.tool_result)
            # Store in kuzu-memory
            await self.store_learnings(learnings)
        return HookResult(success=True, data={"learnings": learnings})
```

### 4. Session Resume Hook
```python
# hooks/session_resume_hook.py
class SessionResumeStartupHook(BaseHook):
    """Handles session resume on startup"""
    
    @property
    def name(self) -> str:
        return "session_resume"
    
    async def execute(self, context: HookContext) -> HookResult:
        # Check for resume log
        resume_log = self.find_resume_log()
        if resume_log:
            # Load previous session context
            context.metadata["resume_context"] = self.load_resume(resume_log)
        return HookResult(success=True, modified_context=context)
```

### 5. Failure Learning Hooks
```python
# hooks/failure_learning/failure_detection_hook.py
class FailureDetectionHook(BaseHook):
    """Detects failures in tool execution"""
    
    async def execute(self, context: HookContext) -> HookResult:
        if context.error:
            failure_info = self.analyze_failure(context.error)
            await self.store_failure(failure_info)
        return HookResult(success=True, data={"failure_info": failure_info})

# hooks/failure_learning/fix_detection_hook.py
class FixDetectionHook(BaseHook):
    """Detects when a fix is applied"""
    
    async def execute(self, context: HookContext) -> HookResult:
        if self.is_fix_attempt(context):
            fix_info = self.analyze_fix(context)
            await self.correlate_with_failure(fix_info)
        return HookResult(success=True, data={"fix_info": fix_info})
```

## Hook Manager

### Core Hook Manager (`core/hook_manager.py`)
```python
class HookManager:
    def __init__(self, container: DIContainer):
        self._hooks: Dict[HookType, List[BaseHook]] = defaultdict(list)
        self._container = container
    
    def register_hook(self, hook: BaseHook, hook_type: HookType) -> None:
        """Register a hook for a specific type"""
        self._hooks[hook_type].append(hook)
        # Sort by priority (higher first)
        self._hooks[hook_type].sort(key=lambda h: h.priority, reverse=True)
    
    async def execute_pre_tool_hooks(self, context: HookContext) -> HookContext:
        """Execute all pre-tool hooks"""
        for hook in self._hooks[HookType.PRE_TOOL]:
            result = await hook.execute(context)
            if not result.should_continue:
                break
            if result.modified_context:
                context = result.modified_context
        return context
    
    async def execute_post_tool_hooks(self, context: HookContext) -> List[HookResult]:
        """Execute all post-tool hooks"""
        results = []
        for hook in self._hooks[HookType.POST_TOOL]:
            result = await hook.execute(context)
            results.append(result)
            if not result.should_continue:
                break
        return results
```

### Hook Service (`services/hook_service.py`)
```python
class HookService(HookServiceInterface):
    """Service wrapper for hook management"""
    
    def __init__(self, container: DIContainer):
        self._manager = HookManager(container)
        self._register_default_hooks()
    
    def _register_default_hooks(self):
        """Register built-in hooks"""
        self._manager.register_hook(
            get_kuzu_memory_hook(), HookType.PRE_TOOL
        )
        self._manager.register_hook(
            get_kuzu_enrichment_hook(), HookType.PRE_TOOL
        )
        self._manager.register_hook(
            get_kuzu_response_hook(), HookType.POST_TOOL
        )
        self._manager.register_hook(
            get_session_resume_hook(), HookType.SESSION_START
        )
```

## Creating Custom Hooks

### 1. Create Hook Class
```python
# my_custom_hook.py
from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult

class MyCustomHook(BaseHook):
    @property
    def name(self) -> str:
        return "my_custom_hook"
    
    @property
    def priority(self) -> int:
        return 10  # Higher priority = runs earlier
    
    async def execute(self, context: HookContext) -> HookResult:
        # Your custom logic
        modified_data = self.process(context.tool_args)
        
        # Modify context if needed
        context.tool_args["custom_data"] = modified_data
        
        return HookResult(
            success=True,
            modified_context=context,
            data={"processed": True}
        )

# Factory function
def get_my_custom_hook() -> MyCustomHook:
    return MyCustomHook()
```

### 2. Register Hook
```python
# In your startup or configuration
from claude_mpm.hooks import get_hook_service

hook_service = get_hook_service()
hook_service.register_hook(get_my_custom_hook())
```

### 3. Export Hook
```python
# hooks/__init__.py
from .my_custom_hook import MyCustomHook, get_my_custom_hook

__all__ = [
    # ... existing exports
    "MyCustomHook",
    "get_my_custom_hook",
]
```

## Hook Execution Flow

### Pre-Tool Flow
```
Tool Call Initiated
    │
    ├── Create HookContext
    │       tool_name, tool_args, session_id
    │
    ├── Execute Pre-Tool Hooks (by priority)
    │   ├── KuzuMemoryHook (priority 20)
    │   ├── KuzuEnrichmentHook (priority 15)
    │   ├── InstructionReinforcementHook (priority 10)
    │   └── Custom hooks...
    │
    ├── Modified Context
    │
    └── Tool Execution with Modified Args
```

### Post-Tool Flow
```
Tool Execution Complete
    │
    ├── Update HookContext
    │       tool_result, error (if any)
    │
    ├── Execute Post-Tool Hooks (by priority)
    │   ├── KuzuResponseHook (priority 20)
    │   ├── FailureDetectionHook (priority 15)
    │   ├── LearningExtractionHook (priority 10)
    │   └── Custom hooks...
    │
    └── Collect Results
```

## Hook Configuration

### Configuration File (`.claude-mpm/configuration.yaml`)
```yaml
hooks:
  enabled: true
  
  kuzu_memory:
    enabled: true
    query_limit: 10
    
  kuzu_enrichment:
    enabled: true
    max_context_tokens: 2000
    
  kuzu_response:
    enabled: true
    extract_learnings: true
    
  failure_learning:
    enabled: true
    correlation_window: 300  # seconds
    
  session_resume:
    enabled: true
    auto_load: true
```

### Runtime Configuration
```python
# Get hook service
hook_service = container.get(IHookService)

# Enable/disable specific hook
hook_service.set_hook_enabled("kuzu_memory", False)

# Get hook status
status = hook_service.get_hook_status()
```

## Hook Performance

### Performance Optimizations
1. **Async execution** - Non-blocking I/O
2. **Priority ordering** - Critical hooks first
3. **Early termination** - `should_continue=False`
4. **Caching** - Cached memory queries

### Metrics
```python
# core/hook_performance_config.py
HOOK_PERFORMANCE_CONFIG = {
    "max_execution_time_ms": 500,
    "enable_timing": True,
    "log_slow_hooks": True,
    "slow_threshold_ms": 100
}
```

## Extension Points

### Tool Interception
```python
# hooks/tool_call_interceptor.py
class ToolCallInterceptor:
    """Intercept and modify tool calls"""
    
    def intercept(self, tool_name: str, args: dict) -> dict:
        """Modify tool arguments"""
    
    def post_process(self, tool_name: str, result: Any) -> Any:
        """Modify tool results"""
```

### Validation Hooks
```python
# hooks/validation_hooks.py
class ValidationHook(BaseHook):
    """Validate tool inputs/outputs"""
    
    async def execute(self, context: HookContext) -> HookResult:
        validation_result = self.validate(context.tool_args)
        if not validation_result.valid:
            return HookResult(
                success=False,
                should_continue=False,
                error=validation_result.errors
            )
        return HookResult(success=True)
```

## Debugging Hooks

### Enable Debug Logging
```python
import logging
logging.getLogger("claude_mpm.hooks").setLevel(logging.DEBUG)
```

### Hook Inspection
```python
# Get all registered hooks
hooks = hook_service.get_registered_hooks()
for hook_type, hook_list in hooks.items():
    print(f"{hook_type}: {[h.name for h in hook_list]}")
```

### Hook Error Memory
```python
# core/hook_error_memory.py
class HookErrorMemory:
    """Track hook errors for debugging"""
    
    def record_error(self, hook_name: str, error: Exception)
    def get_recent_errors(self, limit: int = 10) -> List[HookError]
```

---
See also:
- [SERVICE-LAYER.md](SERVICE-LAYER.md) for hook service details
- [CODE-PATHS.md](CODE-PATHS.md) for execution flows
