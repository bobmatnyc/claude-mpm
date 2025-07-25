# Hook Service

The Hook Service provides a powerful extensibility mechanism for Claude MPM, allowing developers to intercept and modify behavior at key points in the application lifecycle. This document covers the hook architecture, implementation, and usage.

## Overview

The Hook Service enables:
- **Event Interception**: Capture events at critical points
- **Behavior Modification**: Transform messages, responses, and actions
- **Plugin Architecture**: Easy integration of third-party extensions
- **Async Support**: Non-blocking hook execution
- **Priority System**: Control hook execution order

## Architecture

### Hook System Design

```
┌──────────────────────────────────────────────────┐
│                 Hook Service                      │
├──────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │    Hook     │  │    Hook     │  │   Hook   │ │
│  │  Registry   │  │  Executor   │  │  Manager │ │
│  └──────┬──────┘  └──────┬──────┘  └─────┬────┘ │
│         │                 │                │      │
│         ▼                 ▼                ▼      │
│  ┌─────────────────────────────────────────────┐ │
│  │           Hook Processing Pipeline          │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Core Components

```python
class HookService:
    """Main hook service managing all hooks"""
    
    def __init__(self, config: dict):
        self.config = config
        self.registry = HookRegistry()
        self.executor = HookExecutor()
        self.manager = HookManager()
        self.server = None
        
    def start(self):
        """Start hook service"""
        if self.config.get('enabled', True):
            # Start HTTP server for external hooks
            if self.config.get('http_enabled', False):
                self.server = HookServer(
                    port=self.config.get('port', 8080)
                )
                self.server.start()
            
            # Load built-in hooks
            self._load_builtin_hooks()
            
            # Load user hooks
            self._load_user_hooks()
            
            logger.info("Hook service started")
    
    def register_hook(self, event: str, hook: Hook):
        """Register a hook for an event"""
        self.registry.register(event, hook)
    
    def execute_hooks(self, event: str, data: Any) -> Any:
        """Execute all hooks for an event"""
        return self.executor.execute(event, data, self.registry)
```

## Hook Types

### 1. Pre-Message Hooks

Execute before messages are sent to Claude:

```python
class PreMessageHook(BaseHook):
    """Base class for pre-message hooks"""
    
    def execute(self, message: str) -> str:
        """Process message before sending to Claude"""
        raise NotImplementedError

# Example implementation
class ValidationHook(PreMessageHook):
    """Validates message before sending"""
    
    def execute(self, message: str) -> str:
        # Validate message length
        if len(message) > 10000:
            raise ValueError("Message too long")
        
        # Validate content
        if self._contains_sensitive_data(message):
            message = self._redact_sensitive_data(message)
        
        return message
```

### 2. Post-Message Hooks

Execute after receiving responses from Claude:

```python
class PostMessageHook(BaseHook):
    """Base class for post-message hooks"""
    
    def execute(self, response: str) -> str:
        """Process response from Claude"""
        raise NotImplementedError

# Example implementation
class FormattingHook(PostMessageHook):
    """Formats Claude's response"""
    
    def execute(self, response: str) -> str:
        # Add syntax highlighting to code blocks
        response = self._highlight_code_blocks(response)
        
        # Format tables
        response = self._format_tables(response)
        
        # Add links
        response = self._add_links(response)
        
        return response
```

### 3. Error Hooks

Handle errors and exceptions:

```python
class ErrorHook(BaseHook):
    """Base class for error hooks"""
    
    def execute(self, error: Exception, context: dict) -> Optional[str]:
        """Handle error, optionally return recovery message"""
        raise NotImplementedError

# Example implementation
class ErrorRecoveryHook(ErrorHook):
    """Attempts to recover from errors"""
    
    def execute(self, error: Exception, context: dict) -> Optional[str]:
        if isinstance(error, TimeoutError):
            # Suggest retry with longer timeout
            return "The operation timed out. Try breaking down your request into smaller parts."
        
        elif isinstance(error, MemoryError):
            # Suggest resource reduction
            return "Memory limit exceeded. Try a simpler approach."
        
        # Log error for debugging
        logger.error(f"Unhandled error: {error}", exc_info=True)
        return None
```

### 4. Session Hooks

Lifecycle hooks for session management:

```python
class SessionHook(BaseHook):
    """Base class for session hooks"""
    
    def on_start(self, session: Session):
        """Called when session starts"""
        pass
    
    def on_end(self, session: Session):
        """Called when session ends"""
        pass
    
    def on_pause(self, session: Session):
        """Called when session is paused"""
        pass
    
    def on_resume(self, session: Session):
        """Called when session resumes"""
        pass

# Example implementation
class SessionLoggerHook(SessionHook):
    """Logs session events"""
    
    def on_start(self, session: Session):
        logger.info(f"Session started: {session.id}")
        
        # Initialize session storage
        self.storage = SessionStorage(session.id)
        self.storage.initialize()
    
    def on_end(self, session: Session):
        # Save session data
        self.storage.save_session(session)
        
        # Generate summary
        summary = self.generate_summary(session)
        logger.info(f"Session ended: {summary}")
```

### 5. Pattern Hooks

Execute when patterns are detected:

```python
class PatternHook(BaseHook):
    """Base class for pattern hooks"""
    
    def execute(self, pattern: Pattern, context: dict) -> Any:
        """Handle detected pattern"""
        raise NotImplementedError

# Example implementation  
class CodePatternHook(PatternHook):
    """Handles code patterns"""
    
    def execute(self, pattern: Pattern, context: dict) -> Any:
        if pattern.type == 'code_block':
            language = pattern.data.get('language')
            code = pattern.data.get('code')
            
            # Save to file
            filename = f"generated_{language}_{timestamp()}.{language}"
            Path(filename).write_text(code)
            
            # Run linter
            if language == 'python':
                self._run_python_linter(filename)
            
            return {'saved_to': filename}
```

## Hook Registration

### Programmatic Registration

```python
# Create hook service
hook_service = HookService(config)

# Register hooks programmatically
hook_service.register_hook('pre_message', ValidationHook())
hook_service.register_hook('post_message', FormattingHook())
hook_service.register_hook('error', ErrorRecoveryHook())
hook_service.register_hook('pattern_detected', CodePatternHook())

# Register with priority
hook_service.register_hook('pre_message', AuthenticationHook(), priority=10)
hook_service.register_hook('pre_message', RateLimitHook(), priority=20)
```

### File-Based Registration

Create hooks in `.claude/hooks/` directory:

```python
# .claude/hooks/my_hook.py
from claude_mpm.hooks import PreMessageHook

class MyCustomHook(PreMessageHook):
    """Custom pre-message hook"""
    
    # Hook metadata
    name = "my_custom_hook"
    description = "Adds custom header to messages"
    priority = 50
    
    def execute(self, message: str) -> str:
        return f"[Project: MyApp] {message}"

# Export hook
hook = MyCustomHook()
```

### Configuration-Based Registration

```yaml
# .claude/hooks/config.yaml
hooks:
  pre_message:
    - class: ValidationHook
      enabled: true
      priority: 10
      config:
        max_length: 10000
    
    - class: ContextEnhancerHook
      enabled: true
      priority: 20
      config:
        include_timestamp: true
        include_user: true
  
  post_message:
    - class: FormattingHook
      enabled: true
      config:
        highlight_code: true
        format_tables: true
  
  error:
    - class: ErrorRecoveryHook
      enabled: true
      config:
        retry_timeouts: true
        max_retries: 3
```

## Hook Execution

### Execution Flow

```python
class HookExecutor:
    """Executes hooks in order"""
    
    def execute(self, event: str, data: Any, registry: HookRegistry) -> Any:
        """Execute all hooks for an event"""
        
        # Get hooks for event
        hooks = registry.get_hooks(event)
        
        # Sort by priority (lower number = higher priority)
        hooks.sort(key=lambda h: h.priority)
        
        # Execute hooks in order
        result = data
        for hook in hooks:
            if not hook.enabled:
                continue
                
            try:
                # Execute hook
                result = self._execute_single(hook, result)
                
                # Check if hook stops propagation
                if hasattr(hook, 'stop_propagation') and hook.stop_propagation:
                    break
                    
            except Exception as e:
                # Handle hook errors
                self._handle_hook_error(hook, e)
                
                # Continue with other hooks unless fatal
                if not self._is_fatal_error(e):
                    continue
                raise
        
        return result
    
    def _execute_single(self, hook: Hook, data: Any) -> Any:
        """Execute a single hook with timeout"""
        
        # Set timeout for hook execution
        timeout = getattr(hook, 'timeout', 5.0)
        
        # Execute with timeout
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(hook.execute, data)
            
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise HookTimeoutError(f"Hook {hook.name} timed out")
```

### Async Hook Support

```python
class AsyncHook(BaseHook):
    """Base class for async hooks"""
    
    async def execute_async(self, data: Any) -> Any:
        """Async hook execution"""
        raise NotImplementedError

class AsyncHookExecutor:
    """Executes async hooks"""
    
    async def execute(self, event: str, data: Any, registry: HookRegistry) -> Any:
        """Execute hooks asynchronously"""
        
        hooks = registry.get_hooks(event)
        
        # Separate sync and async hooks
        sync_hooks = [h for h in hooks if not isinstance(h, AsyncHook)]
        async_hooks = [h for h in hooks if isinstance(h, AsyncHook)]
        
        # Execute sync hooks first
        result = data
        for hook in sync_hooks:
            result = hook.execute(result)
        
        # Execute async hooks concurrently
        if async_hooks:
            tasks = [
                hook.execute_async(result) 
                for hook in async_hooks
            ]
            
            # Wait for all async hooks
            async_results = await asyncio.gather(*tasks)
            
            # Merge results (custom logic needed)
            result = self._merge_results(result, async_results)
        
        return result
```

## HTTP Hook Server

### External Hook Support

```python
class HookServer:
    """HTTP server for external hooks"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        
        @self.app.route('/hooks/<event>', methods=['POST'])
        def execute_hook(event):
            data = request.json
            
            try:
                # Execute registered HTTP hooks
                result = self._execute_http_hooks(event, data)
                
                return jsonify({
                    'success': True,
                    'result': result
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/hooks', methods=['GET'])
        def list_hooks():
            return jsonify({
                'hooks': self._get_hook_info()
            })
    
    def start(self):
        """Start HTTP server"""
        self.thread = threading.Thread(
            target=self.app.run,
            kwargs={'port': self.port, 'debug': False}
        )
        self.thread.daemon = True
        self.thread.start()
```

### Webhook Registration

```python
class WebhookHook(BaseHook):
    """Hook that calls external webhook"""
    
    def __init__(self, url: str, headers: dict = None):
        self.url = url
        self.headers = headers or {}
        self.timeout = 10
    
    def execute(self, data: Any) -> Any:
        """Call webhook with data"""
        
        response = requests.post(
            self.url,
            json={'data': data},
            headers=self.headers,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        
        # Return original data or webhook response
        if response.json().get('transform'):
            return response.json()['result']
        
        return data

# Register webhook
hook_service.register_hook(
    'post_message',
    WebhookHook('https://api.example.com/claude-hook')
)
```

## Built-in Hooks

### 1. Context Enhancer Hook

```python
class ContextEnhancerHook(PreMessageHook):
    """Adds context to messages"""
    
    def execute(self, message: str) -> str:
        context_parts = []
        
        # Add timestamp
        if self.config.get('include_timestamp', True):
            context_parts.append(f"[{datetime.now().isoformat()}]")
        
        # Add user info
        if self.config.get('include_user', True):
            context_parts.append(f"[User: {os.getenv('USER')}]")
        
        # Add project info
        if self.config.get('include_project', True):
            context_parts.append(f"[Project: {self._get_project_name()}]")
        
        # Add git info
        if self.config.get('include_git', True):
            branch = self._get_git_branch()
            if branch:
                context_parts.append(f"[Branch: {branch}]")
        
        # Combine context with message
        context = ' '.join(context_parts)
        return f"{context}\n\n{message}" if context else message
```

### 2. Rate Limiter Hook

```python
class RateLimiterHook(PreMessageHook):
    """Implements rate limiting"""
    
    def __init__(self, config: dict):
        self.max_requests = config.get('max_requests', 100)
        self.window_seconds = config.get('window_seconds', 3600)
        self.cache = TTLCache(maxsize=1000, ttl=self.window_seconds)
    
    def execute(self, message: str) -> str:
        user_id = self._get_user_id()
        
        # Check rate limit
        count = self.cache.get(user_id, 0)
        
        if count >= self.max_requests:
            raise RateLimitExceeded(
                f"Rate limit exceeded: {self.max_requests} requests per {self.window_seconds}s"
            )
        
        # Increment counter
        self.cache[user_id] = count + 1
        
        return message
```

### 3. Security Scanner Hook

```python
class SecurityScannerHook(PreMessageHook):
    """Scans messages for security issues"""
    
    def __init__(self):
        self.patterns = [
            # API keys
            re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+', re.I),
            # Passwords
            re.compile(r'password["\']?\s*[:=]\s*["\']?[\w-]+', re.I),
            # AWS credentials
            re.compile(r'AKIA[0-9A-Z]{16}'),
            # JWT tokens
            re.compile(r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*')
        ]
    
    def execute(self, message: str) -> str:
        for pattern in self.patterns:
            if pattern.search(message):
                # Log security warning
                logger.warning("Potential sensitive data detected in message")
                
                # Optionally redact
                if self.config.get('redact_sensitive', True):
                    message = pattern.sub('[REDACTED]', message)
        
        return message
```

## Hook Development

### Creating Custom Hooks

```python
# custom_hook.py
from claude_mpm.hooks import BaseHook
import json

class CustomTransformHook(BaseHook):
    """Custom hook that transforms data"""
    
    # Metadata
    name = "custom_transform"
    description = "Transforms messages using custom logic"
    version = "1.0.0"
    author = "Developer Name"
    
    # Configuration schema
    config_schema = {
        'type': 'object',
        'properties': {
            'transform_type': {
                'type': 'string',
                'enum': ['uppercase', 'lowercase', 'title']
            },
            'add_prefix': {
                'type': 'string',
                'default': ''
            }
        }
    }
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.transform_type = config.get('transform_type', 'none')
        self.prefix = config.get('add_prefix', '')
    
    def execute(self, data: str) -> str:
        # Add prefix
        if self.prefix:
            data = f"{self.prefix} {data}"
        
        # Apply transformation
        if self.transform_type == 'uppercase':
            data = data.upper()
        elif self.transform_type == 'lowercase':
            data = data.lower()
        elif self.transform_type == 'title':
            data = data.title()
        
        return data
    
    def validate_config(self, config: dict) -> bool:
        """Validate hook configuration"""
        # Use jsonschema for validation
        from jsonschema import validate
        try:
            validate(config, self.config_schema)
            return True
        except Exception:
            return False
```

### Hook Testing

```python
# test_custom_hook.py
import pytest
from custom_hook import CustomTransformHook

def test_transform_hook_uppercase():
    hook = CustomTransformHook({
        'transform_type': 'uppercase',
        'add_prefix': 'TEST:'
    })
    
    result = hook.execute("hello world")
    assert result == "TEST: HELLO WORLD"

def test_transform_hook_validation():
    hook = CustomTransformHook()
    
    # Valid config
    assert hook.validate_config({
        'transform_type': 'uppercase'
    })
    
    # Invalid config
    assert not hook.validate_config({
        'transform_type': 'invalid'
    })

def test_hook_metadata():
    hook = CustomTransformHook()
    
    assert hook.name == "custom_transform"
    assert hook.version == "1.0.0"
    assert hasattr(hook, 'config_schema')
```

## Hook Debugging

### Debug Mode

```python
# Enable hook debugging
hook_service.debug_mode = True

# Or via environment
export CLAUDE_MPM_HOOK_DEBUG=true
```

### Hook Profiling

```python
class HookProfiler:
    """Profiles hook execution"""
    
    def profile_hook(self, hook: Hook, data: Any) -> ProfileResult:
        """Profile single hook execution"""
        
        import cProfile
        import pstats
        import io
        
        pr = cProfile.Profile()
        pr.enable()
        
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            result = hook.execute(data)
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            pr.disable()
            
            # Get profile stats
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats(10)  # Top 10 functions
            
            return ProfileResult(
                hook_name=hook.name,
                execution_time=end_time - start_time,
                memory_delta=end_memory - start_memory,
                profile_stats=s.getvalue(),
                result=result
            )
            
        except Exception as e:
            pr.disable()
            raise
```

### Hook Monitoring

```python
class HookMonitor:
    """Monitors hook performance"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'executions': 0,
            'failures': 0,
            'total_time': 0,
            'timeouts': 0
        })
    
    def record_execution(self, hook_name: str, execution_time: float, success: bool):
        """Record hook execution metrics"""
        
        metrics = self.metrics[hook_name]
        metrics['executions'] += 1
        metrics['total_time'] += execution_time
        
        if not success:
            metrics['failures'] += 1
    
    def get_hook_stats(self) -> dict:
        """Get statistics for all hooks"""
        
        stats = {}
        for hook_name, metrics in self.metrics.items():
            if metrics['executions'] > 0:
                stats[hook_name] = {
                    'average_time': metrics['total_time'] / metrics['executions'],
                    'failure_rate': metrics['failures'] / metrics['executions'],
                    'total_executions': metrics['executions']
                }
        
        return stats
```

## Best Practices

### 1. Hook Design

```python
# Good: Focused, single-purpose hook
class TimestampHook(PreMessageHook):
    def execute(self, message: str) -> str:
        return f"[{datetime.now()}] {message}"

# Bad: Hook doing too much
class KitchenSinkHook(PreMessageHook):
    def execute(self, message: str) -> str:
        # Timestamp
        # Validate
        # Transform
        # Log
        # Send webhooks
        # ... 100 lines of code
```

### 2. Error Handling

```python
class RobustHook(BaseHook):
    def execute(self, data: Any) -> Any:
        try:
            # Main logic
            return self._process(data)
            
        except ValueError as e:
            # Handle expected errors
            logger.warning(f"Invalid data: {e}")
            return data  # Return original
            
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Hook error: {e}", exc_info=True)
            
            # Don't break the chain
            if self.config.get('fail_gracefully', True):
                return data
            raise
```

### 3. Performance

```python
class EfficientHook(BaseHook):
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Pre-compile patterns
        self.patterns = [
            re.compile(p) for p in config.get('patterns', [])
        ]
        
        # Cache expensive operations
        self.cache = LRUCache(maxsize=100)
    
    def execute(self, data: str) -> str:
        # Check cache first
        cache_key = hashlib.md5(data.encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Process
        result = self._process(data)
        
        # Cache result
        self.cache[cache_key] = result
        
        return result
```

### 4. Configuration

```python
class ConfigurableHook(BaseHook):
    # Define clear configuration schema
    config_schema = {
        'type': 'object',
        'properties': {
            'enabled': {'type': 'boolean', 'default': True},
            'timeout': {'type': 'number', 'default': 5.0},
            'options': {
                'type': 'object',
                'additionalProperties': True
            }
        },
        'required': []
    }
    
    def __init__(self, config: dict = None):
        # Validate configuration
        self._validate_config(config)
        super().__init__(config)
```

## Next Steps

- See [Orchestrators](orchestrators.md) for hook integration
- Review [Extending Claude MPM](../05-extending/) for creating plugins
- Check [API Reference](../04-api-reference/services-api.md#hook-service) for complete API